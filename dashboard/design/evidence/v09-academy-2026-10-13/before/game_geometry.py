"""Immutable, validated track geometry shared by physics, sensors and rendering.

The existing capsule keeps its analytic kernel. General circuits use exact
closed polygon boundaries derived from the catalog's sampled centerline.
"""
from functools import lru_cache
import math
import numpy as np
from game_catalog import TRACK, track_data


def cross(a,b):return a[...,0]*b[...,1]-a[...,1]*b[...,0]


def ring_contains(points,ring):
    p=np.asarray(points);shape=p.shape[:-1];flat=p.reshape(-1,2);out=[]
    a=ring;b=np.roll(a,-1,axis=0)
    for start in range(0,len(flat),256):
        q=flat[start:start+256,None,:]
        dy=b[:,1]-a[:,1]
        at=a[:,0]+(q[...,1]-a[:,1])*np.divide(b[:,0]-a[:,0],dy,out=np.zeros_like(dy),where=abs(dy)>1e-12)
        hits=((a[:,1]>q[...,1])!=(b[:,1]>q[...,1])) & (q[...,0]<at)
        out.extend((hits.sum(axis=1)%2).tolist())
    return np.asarray(out,dtype=bool).reshape(shape)


def validate_rings(rings):
    # Inclusive crossing/tangency test, including collinear overlaps; adjacent
    # segments of the same ring share their one endpoint by construction.
    for ri,a in enumerate(rings):
        if not np.isfinite(a).all() or np.min(np.linalg.norm(np.roll(a,-1,axis=0)-a,axis=1))<1e-6:
            raise ValueError('Segmenti degeneri nel circuito')
        for rj in range(ri,len(rings)):
            b=rings[rj];aa=a[:,None,:];ab=np.roll(a,-1,axis=0)[:,None,:]
            ba=b[None,:,:];bb=np.roll(b,-1,axis=0)[None,:,:]
            u=ab-aa;v=bb-ba;den=cross(u,v)
            t=np.divide(cross(ba-aa,v),den,out=np.zeros_like(den),where=abs(den)>1e-12)
            s=np.divide(cross(ba-aa,u),den,out=np.zeros_like(den),where=abs(den)>1e-12)
            hit=(abs(den)>1e-12)&(t>=-1e-9)&(t<=1+1e-9)&(s>=-1e-9)&(s<=1+1e-9)
            parallel=(abs(den)<=1e-12)&(abs(cross(ba-aa,u))<=1e-10)
            overlap=(np.minimum(ab,aa)<=np.maximum(ba,bb)+1e-9).all(axis=-1)&(np.minimum(ba,bb)<=np.maximum(aa,ab)+1e-9).all(axis=-1)
            hit |= parallel&overlap
            if ri==rj:
                ii,jj=np.indices(hit.shape)
                hit &= (jj>ii)&((jj-ii)>1)&((jj-ii)<len(a)-1)
            if hit.any():raise ValueError('Incrocio o tangenza nel circuito')


class TrackRuntime:
    def __init__(self,identity):
        self.id=identity;self.spec=track_data(identity);self.width=self.spec['road_width']
        self.oval=identity=='oval-1'
        if self.oval:
            self.length=4*TRACK.half_straight+2*math.pi*TRACK.radius
            self.bounds=np.array([[-72.,-36.],[72.,36.]])
            return
        self.points=np.asarray(self.spec['centerline'],dtype=float)
        if self.points.ndim!=2 or self.points.shape[1]!=2 or not 32<=len(self.points)<=2048:
            raise ValueError('Geometria del circuito non valida')
        self.segments=np.roll(self.points,-1,axis=0)-self.points
        self.segment_lengths=np.linalg.norm(self.segments,axis=1)
        self.distances=np.r_[0,np.cumsum(self.segment_lengths)]
        self.length=float(self.distances[-1]);self.start=float(self.spec['startDistance'])
        tangent=np.roll(self.points,-1,axis=0)-np.roll(self.points,1,axis=0)
        tangent/=np.linalg.norm(tangent,axis=1)[:,None]
        normal=np.column_stack((-tangent[:,1],tangent[:,0]))
        left=self.points+normal*self.width/2;right=self.points-normal*self.width/2
        def area(p):return abs(float(np.sum(cross(p,np.roll(p,-1,axis=0)))))
        self.outer,self.inner=sorted((left,right),key=area,reverse=True)
        validate_rings((self.points,));validate_rings((self.outer,self.inner))
        if not ring_contains(self.inner,self.outer).all():raise ValueError('Bordi non annidati')
        self.boundaries=np.concatenate((self.outer,self.inner))
        self.boundary_delta=np.concatenate((np.roll(self.outer,-1,axis=0)-self.outer,np.roll(self.inner,-1,axis=0)-self.inner))
        self.boundary_lo=np.minimum(self.boundaries,self.boundaries+self.boundary_delta)
        self.boundary_hi=np.maximum(self.boundaries,self.boundaries+self.boundary_delta)
        self.bounds=np.array([self.outer.min(axis=0),self.outer.max(axis=0)])
        # Index for nearest-point recovery. Include neighbors of the cell to
        # preserve continuous projection at cell boundaries and on the road.
        self.grid={};self.cell=8.
        for i,(a,b) in enumerate(zip(self.points,np.roll(self.points,-1,axis=0))):
            lo=np.floor(np.minimum(a,b)/self.cell).astype(int);hi=np.floor(np.maximum(a,b)/self.cell).astype(int)
            for ix in range(lo[0]-1,hi[0]+2):
                for iy in range(lo[1]-1,hi[1]+2):self.grid.setdefault((ix,iy),[]).append(i)
        self.gates=[self.pose(self.length*(i+1)/4) for i in range(4)]
        for a in (self.points,self.segments,self.distances,self.outer,self.inner,self.boundaries,self.boundary_delta):a.flags.writeable=False

    def pose(self,distance,lateral=0.):
        if self.oval:
            # Distance zero remains the historic lower-straight x=0 spawn.
            phase=(distance+TRACK.half_straight)%self.length;a=TRACK.half_straight;r=TRACK.radius
            if phase<2*a:x,y,angle=phase-a,-r,0.
            elif phase<2*a+math.pi*r:
                q=(phase-2*a)/r-math.pi/2;x,y,angle=a+r*math.cos(q),r*math.sin(q),q+math.pi/2
            elif phase<4*a+math.pi*r:x,y,angle=a-(phase-2*a-math.pi*r),r,math.pi
            else:
                q=(phase-4*a-math.pi*r)/r+math.pi/2;x,y,angle=-a+r*math.cos(q),r*math.sin(q),q+math.pi/2
            return np.array([x-math.sin(angle)*lateral,y+math.cos(angle)*lateral,angle])
        s=(distance+self.start)%self.length;i=min(len(self.points)-1,int(np.searchsorted(self.distances,s,side='right')-1))
        t=(s-self.distances[i])/self.segment_lengths[i];p=self.points[i]+t*self.segments[i]
        direction=self.segments[i]/self.segment_lengths[i]
        return np.array([p[0]-direction[1]*lateral,p[1]+direction[0]*lateral,math.atan2(direction[1],direction[0])])

    def poses(self,distances):
        d=np.asarray(distances)
        if self.oval:
            a,r=TRACK.half_straight,TRACK.radius;p=(d+a)%self.length
            x=np.empty_like(p);y=np.empty_like(p);angle=np.empty_like(p)
            m=p<2*a;x[m]=p[m]-a;y[m]=-r;angle[m]=0
            m=(p>=2*a)&(p<2*a+np.pi*r);q=(p[m]-2*a)/r-np.pi/2
            x[m]=a+r*np.cos(q);y[m]=r*np.sin(q);angle[m]=q+np.pi/2
            m=(p>=2*a+np.pi*r)&(p<4*a+np.pi*r)
            x[m]=a-(p[m]-2*a-np.pi*r);y[m]=r;angle[m]=np.pi
            m=p>=4*a+np.pi*r;q=(p[m]-4*a-np.pi*r)/r+np.pi/2
            x[m]=-a+r*np.cos(q);y[m]=r*np.sin(q);angle[m]=q+np.pi/2
            return np.stack((x,y,angle),axis=-1)
        s=(d+self.start)%self.length
        i=np.clip(np.searchsorted(self.distances,s,side="right")-1,0,len(self.points)-1)
        f=(s-self.distances[i])/self.segment_lengths[i]
        v=self.segments[i]/self.segment_lengths[i,None]
        p=self.points[i]+f[...,None]*self.segments[i]
        return np.concatenate((p,np.arctan2(v[...,1],v[...,0])[...,None]),axis=-1)

    def project(self,points,hints=None):
        p=np.asarray(points).reshape(-1,2);offset=[];angle=[];phase=[];indices=[]
        if hints is not None:
            candidates=(np.asarray(hints)[:,None]+np.arange(-16,17))%len(self.points)
            a=self.points[candidates];v=self.segments[candidates]
            frac=np.clip(np.sum((p[:,None,:]-a)*v,axis=-1)/np.sum(v*v,axis=-1),0,1)
            relative=p[:,None,:]-(a+frac[:,:,None]*v)
            choice=np.argmin(np.sum(relative*relative,axis=-1),axis=1);rows=np.arange(len(p))
            i=candidates[rows,choice];direction=v[rows,choice]/self.segment_lengths[i,None]
            return (-cross(direction,relative[rows,choice]),np.arctan2(direction[:,1],direction[:,0]),
                    (self.distances[i]+frac[rows,choice]*self.segment_lengths[i]-self.start)%self.length,i)
        for row,q in enumerate(p):
            if hints is not None:
                candidates=(int(hints[row])+np.arange(-16,17))%len(self.points)
            else:
                key=tuple(np.floor(q/self.cell).astype(int))
                candidates=np.array(self.grid.get(key,list(range(len(self.points)))),dtype=int)
            a=self.points[candidates];v=self.segments[candidates]
            frac=np.clip(np.sum((q-a)*v,axis=1)/np.sum(v*v,axis=1),0,1)
            relative=q-(a+frac[:,None]*v);k=int(np.argmin(np.sum(relative*relative,axis=1)));i=int(candidates[k])
            direction=v[k]/self.segment_lengths[i]
            # Positive outside a counterclockwise road, like the capsule kernel.
            offset.append(-cross(direction,relative[k]));angle.append(math.atan2(direction[1],direction[0]))
            phase.append((self.distances[i]+frac[k]*self.segment_lengths[i]-self.start)%self.length);indices.append(i)
        return np.array(offset),np.array(angle),np.array(phase),np.array(indices)

    def contains(self,points):return ring_contains(points,self.outer)&~ring_contains(points,self.inner)

    def contact(self,body):
        if not self.contains(body).all():return True
        a=body[:,None,:];u=(np.roll(body,-1,axis=0)-body)[:,None,:]
        b=self.boundaries[None,:,:];v=self.boundary_delta[None,:,:]
        den=cross(u,v);relative=b-a
        t=np.divide(cross(relative,v),den,out=np.zeros_like(den),where=abs(den)>1e-12)
        s=np.divide(cross(relative,u),den,out=np.zeros_like(den),where=abs(den)>1e-12)
        hit=(abs(den)>1e-12)&(t>=-1e-9)&(t<=1+1e-9)&(s>=-1e-9)&(s<=1+1e-9)
        parallel=(abs(den)<=1e-12)&(abs(cross(relative,u))<=1e-10)
        overlap=(np.minimum(a,a+u)<=np.maximum(b,b+v)+1e-9).all(axis=-1)&(np.minimum(b,b+v)<=np.maximum(a,a+u)+1e-9).all(axis=-1)
        hit |= parallel&overlap
        return bool(hit.any())

    def swept_contact(self,before,after):
        # Convex hull covers the translation between poses. Adaptive angular
        # substeps in World bound rotation between the sampled orientations.
        points=sorted(set(map(tuple,np.vstack((before,after)))))
        lower=[];upper=[]
        for chain,order in ((lower,points),(upper,points[::-1])):
            for q in order:
                while len(chain)>1 and cross(np.array(chain[-1])-chain[-2],np.array(q)-chain[-1])<=0:chain.pop()
                chain.append(q)
        return self.contact(np.array(lower[:-1]+upper[:-1]))

    def rays(self,states,angles):
        origin=np.repeat(states[:,:2],len(angles),axis=0)
        direction_angle=(states[:,2,None]+angles).ravel()
        direction=np.column_stack((np.cos(direction_angle),np.sin(direction_angle)))
        result=[]
        for start in range(0,len(origin),128):
            o=origin[start:start+128];d=direction[start:start+128];end=o+d*50
            lo=np.minimum(o,end);hi=np.maximum(o,end)
            mask=(self.boundary_hi[None,:,0]>=lo[:,None,0])&(self.boundary_lo[None,:,0]<=hi[:,None,0])
            mask &= (self.boundary_hi[None,:,1]>=lo[:,None,1])&(self.boundary_lo[None,:,1]<=hi[:,None,1])
            ray,segment=np.nonzero(mask);v=self.boundary_delta[segment]
            relative=self.boundaries[segment]-o[ray];den=cross(d[ray],v)
            t=np.divide(cross(relative,v),den,out=np.full_like(den,51.),where=abs(den)>1e-12)
            u=np.divide(cross(relative,d[ray]),den,out=np.full_like(den,2.),where=abs(den)>1e-12)
            valid=(t>1e-6)&(t<=50)&(u>=0)&(u<=1)
            distance=np.full(len(o),50.);np.minimum.at(distance,ray,np.where(valid,t,50))
            result.extend(distance.tolist())
        return np.array(result).reshape(len(states),len(angles))

    def gate_crossings(self,old,new,checkpoints):
        gate=np.asarray(self.gates)[np.asarray(checkpoints)%4]
        direction=np.column_stack((np.cos(gate[:,2]),np.sin(gate[:,2])))
        a=np.sum((old-gate[:,:2])*direction,axis=1);b=np.sum((new-gate[:,:2])*direction,axis=1)
        fractions=np.divide(-a,b-a,out=np.ones(len(a)),where=abs(b-a)>1e-12)
        q=old+fractions[:,None]*(new-old)
        return (a<0)&(b>=0)&(b>a)&(abs(cross(direction,q-gate[:,:2]))<=self.width/2),fractions

    def render(self):
        if self.oval:return {'id':self.id,'kind':'oval','bounds':self.bounds.tolist(),'length':self.length}
        return {'id':self.id,'kind':'polygon','bounds':self.bounds.tolist(),'length':self.length,
                'outer':self.outer.tolist(),'inner':self.inner.tolist(),'start':self.pose(0).tolist()}


@lru_cache(maxsize=4)
def get_track(identity='oval-1'):return TrackRuntime(identity)
