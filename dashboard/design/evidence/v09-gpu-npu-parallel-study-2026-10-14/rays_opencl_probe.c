/* Synthetic ray/segment microbenchmark, NOT the production sensor algorithm.
 * gcc -O2 -ffp-contract=off rays_opencl_probe.c -lOpenCL -lm -o rays_probe
 * Static polygon buffers persist; each batch transfers rays and reads distances.
 * CPU baseline is native scalar FP32 on the same inputs, not current NumPy FP64.
 * No scene, trained policy, service, checkpoint or driver configuration is changed.
 */
#define CL_TARGET_OPENCL_VERSION 120
#define _POSIX_C_SOURCE 200809L
#include <CL/cl.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

typedef struct { float x,y,z,w; } V4;
static volatile float sink;
static double clock_us(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
    return t.tv_sec*1e6+t.tv_nsec/1e3;
}
static void check(cl_int status, const char *where) {
    if(status!=CL_SUCCESS) {fprintf(stderr,"%s: OpenCL error %d\n",where,status);exit(2);}
}
static int compare(const void *a,const void *b) {
    double x=*(const double*)a,y=*(const double*)b;return (x>y)-(x<y);
}
static void reference(const V4 *r,const V4 *s,float *out,int n,int k) {
    for(int i=0;i<n;i++) {
        float best=150;
        for(int j=0;j<k;j++) {
            float sx=s[j].z-s[j].x,sy=s[j].w-s[j].y;
            float qx=s[j].x-r[i].x,qy=s[j].y-r[i].y;
            float den=r[i].z*sy-r[i].w*sx;
            if(fabsf(den)<1e-7f)continue;
            float t=(qx*sy-qy*sx)/den;
            float u=(qx*r[i].w-qy*r[i].z)/den;
            if(t>=0 && u>=0 && u<=1 && t<best)best=t;
        }
        out[i]=best;
    }
}
static const char *kernel_source=
"__kernel void rays(__global const float4 *r,__global const float4 *s,"
"__global float *out,int k){int i=get_global_id(0);float4 a=r[i];float best=150.0f;"
"for(int j=0;j<k;j++){float4 b=s[j];float sx=b.z-b.x,sy=b.w-b.y;"
"float qx=b.x-a.x,qy=b.y-a.y;float den=a.z*sy-a.w*sx;"
"if(fabs(den)<1e-7f)continue;float t=(qx*sy-qy*sx)/den;"
"float u=(qx*a.w-qy*a.z)/den;"
"if(t>=0 && u>=0 && u<=1 && t<best)best=t;}out[i]=best;}";

int main(void) {
    cl_platform_id platform;cl_device_id device;cl_int status;
    double cold=clock_us();
    check(clGetPlatformIDs(1,&platform,NULL),"platform");
    check(clGetDeviceIDs(platform,CL_DEVICE_TYPE_GPU,1,&device,NULL),"GPU device");
    char name[256]={0},driver[256]={0};
    check(clGetDeviceInfo(device,CL_DEVICE_NAME,sizeof(name),name,NULL),"name");
    check(clGetDeviceInfo(device,CL_DRIVER_VERSION,sizeof(driver),driver,NULL),"driver");
    cl_context context=clCreateContext(NULL,1,&device,NULL,NULL,&status);check(status,"context");
    cl_command_queue queue=clCreateCommandQueue(context,device,CL_QUEUE_PROFILING_ENABLE,&status);check(status,"queue");
    cl_program program=clCreateProgramWithSource(context,1,&kernel_source,NULL,&status);check(status,"program");
    status=clBuildProgram(program,1,&device,"-cl-std=CL1.2",NULL,NULL);
    if(status!=CL_SUCCESS) {
        char log[8192]={0};clGetProgramBuildInfo(program,device,CL_PROGRAM_BUILD_LOG,sizeof(log),log,NULL);
        fprintf(stderr,"%s\n",log);check(status,"build");
    }
    cl_kernel kernel=clCreateKernel(program,"rays",&status);check(status,"kernel");
    printf("{\"scope\":\"Synthetic rays against polygon; no production integration\","
           "\"device\":\"%s\",\"driver\":\"%s\",\"precision\":\"FP32 CPU and GPU\","
           "\"coldContextAndBuildMs\":%.3f,\"samplesPerCase\":64,\"warmupPerCase\":5,\"cases\":[\n",
           name,driver,(clock_us()-cold)/1000.);
    int first=1;int cars_list[]={4,32,128};int segment_list[]={128,512};
    for(int ci=0;ci<3;ci++)for(int si=0;si<2;si++) {
        int cars=cars_list[ci],n=cars*9,k=segment_list[si];
        V4 *r=calloc(n,sizeof(V4)),*s=calloc(k,sizeof(V4));
        float *cpu=calloc(n,sizeof(float)),*gpu=calloc(n,sizeof(float));
        if(!r||!s||!cpu||!gpu){fprintf(stderr,"allocation failed\n");return 3;}
        for(int j=0;j<k;j++) {
            double a=6.283185307179586*j/k,b=6.283185307179586*(j+1)/k;
            s[j]=(V4){(float)(100*cos(a)),(float)(45*sin(a)),(float)(100*cos(b)),(float)(45*sin(b))};
        }
        for(int i=0;i<n;i++) {
            double a=6.283185307179586*(i/9)/(cars+1),q=a+.15*(i%9-4);
            r[i]=(V4){(float)(75*cos(a)),(float)(30*sin(a)),(float)cos(q),(float)sin(q)};
        }
        cl_mem rb=clCreateBuffer(context,CL_MEM_READ_ONLY,n*sizeof(V4),NULL,&status);check(status,"rays buffer");
        cl_mem sb=clCreateBuffer(context,CL_MEM_READ_ONLY|CL_MEM_COPY_HOST_PTR,k*sizeof(V4),s,&status);check(status,"segments buffer");
        cl_mem ob=clCreateBuffer(context,CL_MEM_WRITE_ONLY,n*sizeof(float),NULL,&status);check(status,"output buffer");
        check(clSetKernelArg(kernel,0,sizeof(rb),&rb),"arg0");
        check(clSetKernelArg(kernel,1,sizeof(sb),&sb),"arg1");
        check(clSetKernelArg(kernel,2,sizeof(ob),&ob),"arg2");
        check(clSetKernelArg(kernel,3,sizeof(k),&k),"arg3");
        check(clFinish(queue),"static upload");
        double ct[64],gt[64],kt[64];float error=0;size_t global=(size_t)n;
        for(int t=0;t<69;t++) {
            r[0].x+=.0001f;
            double start=clock_us();reference(r,s,cpu,n,k);sink=cpu[0];double elapsed=clock_us()-start;
            start=clock_us();
            check(clEnqueueWriteBuffer(queue,rb,CL_FALSE,0,n*sizeof(V4),r,0,NULL,NULL),"upload rays");
            cl_event event;
            check(clEnqueueNDRangeKernel(queue,kernel,1,NULL,&global,NULL,0,NULL,&event),"enqueue");
            check(clEnqueueReadBuffer(queue,ob,CL_TRUE,0,n*sizeof(float),gpu,0,NULL,NULL),"read distances");
            double full=clock_us()-start;
            cl_ulong begin,end;
            check(clGetEventProfilingInfo(event,CL_PROFILING_COMMAND_START,sizeof(begin),&begin,NULL),"profiling start");
            check(clGetEventProfilingInfo(event,CL_PROFILING_COMMAND_END,sizeof(end),&end,NULL),"profiling end");
            clReleaseEvent(event);
            for(int i=0;i<n;i++) {
                if(!isfinite(gpu[i])){fprintf(stderr,"nonfinite distance\n");return 4;}
                error=fmaxf(error,fabsf(cpu[i]-gpu[i]));
            }
            if(t>=5){ct[t-5]=elapsed;gt[t-5]=full;kt[t-5]=(end-begin)/1000.;}
        }
        qsort(ct,64,sizeof(double),compare);qsort(gt,64,sizeof(double),compare);qsort(kt,64,sizeof(double),compare);
        printf("%s{\"cars\":%d,\"rays\":%d,\"segments\":%d,\"cpuMedianUs\":%.3f,\"cpuP95Us\":%.3f,"
               "\"gpuFullMedianUs\":%.3f,\"gpuFullP95Us\":%.3f,\"gpuFullMaxUs\":%.3f,"
               "\"gpuKernelMedianUs\":%.3f,\"maxDistanceErrorMeters\":%.9g}",
               first?"":",\n",cars,n,k,ct[32],ct[60],gt[32],gt[60],gt[63],kt[32],error);
        first=0;clReleaseMemObject(rb);clReleaseMemObject(sb);clReleaseMemObject(ob);free(r);free(s);free(cpu);free(gpu);
    }
    printf("\n]}\n");
    clReleaseKernel(kernel);clReleaseProgram(program);clReleaseCommandQueue(queue);clReleaseContext(context);
    return 0;
}
