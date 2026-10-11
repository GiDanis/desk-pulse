/* Offline VIPLite qualification: persistent network, including host copies/cache sync.
 * gcc -O2 game-npu-benchmark.c -o game-npu-benchmark -lNBGlinker -lVIPhal
 * Inputs: A733 NBG, little-endian float32 observations; outputs: float32 actions.
 * This executable is a qualification tool, not an enabled dashboard engine.
 */
#include <vip_lite.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define CHECK(call) do { vip_status_e s=(call); if(s!=VIP_SUCCESS) { \
    fprintf(stderr,"%s failed: %d\n",#call,s); exit(2); } } while(0)
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t); return t.tv_sec+t.tv_nsec*1e-9; }
static vip_buffer buffer(vip_network network, int input, unsigned count) {
    vip_buffer_create_params_t p={0}; vip_buffer b;
    #define QUERY(prop,value) CHECK(input ? vip_query_input(network,0,prop,value) : vip_query_output(network,0,prop,value))
    QUERY(VIP_BUFFER_PROP_NUM_OF_DIMENSION,&p.num_of_dims);
    QUERY(VIP_BUFFER_PROP_SIZES_OF_DIMENSION,p.sizes);
    QUERY(VIP_BUFFER_PROP_DATA_FORMAT,&p.data_format);
    QUERY(VIP_BUFFER_PROP_QUANT_FORMAT,&p.quant_format);
    unsigned elements=1;
    if(p.num_of_dims>6) exit(3);
    for(unsigned i=0;i<p.num_of_dims;i++) elements*=p.sizes[i];
    if(elements!=count || p.data_format!=VIP_BUFFER_FORMAT_FP32 || p.quant_format!=VIP_BUFFER_QUANTIZE_NONE) {
        fprintf(stderr,"Unexpected tensor: %u elements, format %d, quant %d\n",elements,p.data_format,p.quant_format); exit(3);
    }
    CHECK(vip_create_buffer(&p,sizeof(p),&b)); return b;
}
int main(int argc,char **argv) {
    if(argc!=4) { fprintf(stderr,"Usage: %s model.nb observations.f32 actions.f32\n",argv[0]); return 1; }
    FILE *in=fopen(argv[2],"rb"),*out=fopen(argv[3],"wb");
    if(!in || !out) return 1;
    double cold=now(); CHECK(vip_init()); vip_network network;
    CHECK(vip_create_network(argv[1],0,VIP_CREATE_NETWORK_FROM_FILE,&network));
    CHECK(vip_prepare_network(network));
    vip_buffer input=buffer(network,1,32),output=buffer(network,0,2);
    CHECK(vip_set_input(network,0,input)); CHECK(vip_set_output(network,0,output));
    float *ip=vip_map_buffer(input),*op=vip_map_buffer(output);
    if(!ip || !op) return 2;
    cold=now()-cold;
    float observation[32],action[2]; unsigned count=0;
    while(fread(observation,sizeof(float),32,in)==32) {
        double start=now(); memcpy(ip,observation,sizeof(observation));
        CHECK(vip_flush_buffer(input,VIP_BUFFER_OPER_TYPE_FLUSH)); CHECK(vip_run_network(network));
        CHECK(vip_flush_buffer(output,VIP_BUFFER_OPER_TYPE_INVALIDATE)); memcpy(action,op,sizeof(action));
        double elapsed=now()-start;
        if(fwrite(action,sizeof(float),2,out)!=2) return 1;
        printf("sample %u %.9f\n",count++,elapsed);
    }
    fprintf(stderr,"coldSeconds %.9f samples %u\n",cold,count);
    CHECK(vip_unmap_buffer(input)); CHECK(vip_unmap_buffer(output));
    CHECK(vip_finish_network(network)); CHECK(vip_destroy_buffer(input)); CHECK(vip_destroy_buffer(output));
    CHECK(vip_destroy_network(network)); CHECK(vip_destroy()); fclose(in); fclose(out); return 0;
}
