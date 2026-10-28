/* Float64 geometric rays, explicit optional backend; never fast-math.
 * Build: gcc -O3 -ffp-contract=off -fPIC -shared game_native.c -lm -o libsmartpc_game_native.so
 * Callers prepare directions with NumPy to preserve its sin/cos conventions.
 */
#include <math.h>
#include <stddef.h>
#include <stdint.h>

void smartpc_neat(double *values,const int64_t *destination,const int64_t *starts,
 const int64_t *sources,const double *weights,const double *bias,const double *response,
 size_t nodes,const int64_t *outputs,size_t output_count,double *result) {
 for(size_t i=0;i<nodes;i++) {
  double sum=0.;for(int64_t k=starts[i];k<starts[i+1];k++)sum+=values[sources[k]]*weights[k];
  double z=2.5*(bias[i]+response[i]*sum);z=fmax(-60.,fmin(60.,z));
  values[destination[i]]=tanh(z);
 }
 for(size_t i=0;i<output_count;i++)result[i]=values[outputs[i]];
}

void smartpc_polygon_rays(const double *origins,const double *directions,
 const double *starts,const double *deltas,const double *lo,const double *hi,
 size_t rays,size_t segments,double limit,double *result) {
 for(size_t i=0;i<rays;i++) {
  double ox=origins[2*i],oy=origins[2*i+1],dx=directions[2*i],dy=directions[2*i+1];
  double ex=ox+dx*limit,ey=oy+dy*limit;
  double minx=fmin(ox,ex),maxx=fmax(ox,ex),miny=fmin(oy,ey),maxy=fmax(oy,ey),best=limit;
  for(size_t j=0;j<segments;j++) {
   size_t k=2*j;
   if(hi[k]<minx||lo[k]>maxx||hi[k+1]<miny||lo[k+1]>maxy)continue;
   double sx=deltas[k],sy=deltas[k+1],qx=starts[k]-ox,qy=starts[k+1]-oy;
   double den=dx*sy-dy*sx;if(fabs(den)<=1e-12)continue;
   double t=(qx*sy-qy*sx)/den,u=(qx*dy-qy*dx)/den;
   if(t>1e-6&&t<=limit&&u>=0&&u<=1&&t<best)best=t;
  }
  result[i]=best;
 }
}

void smartpc_oval_rays(const double *origins,const double *directions,size_t rays,
 double half_straight,double radius,double width,double limit,double *result) {
 double a=half_straight;
 for(size_t i=0;i<rays;i++) {
  double ox=origins[2*i],oy=origins[2*i+1],dx=directions[2*i],dy=directions[2*i+1],best=limit;
  for(int ri=0;ri<2;ri++) {
   double r=radius+(ri?width/2:-width/2);
   for(int side=0;side<2;side++) {
    double y=side?r:-r,t=fabs(dy)>1e-9?(y-oy)/dy:1e6;
    double x=ox+t*dx;if(t>0&&fabs(x)<=a&&t<best)best=t;
   }
   for(int ci=0;ci<2;ci++) {
    double center=ci?a:-a,rx=ox-center,b=rx*dx+oy*dy,c=rx*rx+oy*oy-r*r;
    double disc=b*b-c,root=sqrt(fmax(disc,0.));
    for(int root_index=0;root_index<2;root_index++) {
     double t=-b+(root_index?root:-root),x=ox+t*dx;
     if(disc>=0&&t>1e-6&&(ci?x>=a:x<=-a)&&t<best)best=t;
    }
   }
  }
  result[i]=best;
 }
}
