"""Oriented body contact response, SI units; no training or display policy."""
import numpy as np


def manifold(a,b):
    depth=float('inf');normal=None
    for p in (a,b):
        for i in (0,1):
            edge=p[i+1]-p[i];axis=np.array([-edge[1],edge[0]])
            axis/=np.linalg.norm(axis)
            pa,pb=a@axis,b@axis
            overlap=min(pa.max(),pb.max())-max(pa.min(),pb.min())
            if overlap<0:return None
            if overlap<depth:depth=float(overlap);normal=axis
    if np.dot(b.mean(axis=0)-a.mean(axis=0),normal)<0:normal=-normal
    pa=a@normal;pb=b@normal
    point=(a[pa>=pa.max()-1e-7].mean(axis=0)+b[pb<=pb.min()+1e-7].mean(axis=0))/2
    return normal,depth,point


def resolve(states,i,j,a,b,vehicle):
    contact=manifold(a,b)
    if contact is None:return None
    n,depth,point=contact;v=vehicle
    def cross(x,y):return x[0]*y[1]-x[1]*y[0]
    def velocity(index):
        x=states[index];c,s=np.cos(x[2]),np.sin(x[2])
        return np.array([c*x[3]-s*x[4],s*x[3]+c*x[4]])
    ra,rb=point-states[i,:2],point-states[j,:2]
    va=velocity(i)+states[i,5]*np.array([-ra[1],ra[0]])
    vb=velocity(j)+states[j,5]*np.array([-rb[1],rb[0]])
    closing=max(0.,-float(np.dot(vb-va,n)))
    impulse=closing*(1+v.restitution)/(2/v.mass+(cross(ra,n)**2+cross(rb,n)**2)/v.yaw_inertia)
    for index,r,sign in ((i,ra,-1),(j,rb,1)):
        vector=velocity(index)+sign*impulse*n/v.mass
        c,s=np.cos(states[index,2]),np.sin(states[index,2])
        states[index,3:5]=[c*vector[0]+s*vector[1],-s*vector[0]+c*vector[1]]
        states[index,5]+=sign*impulse*cross(r,n)/v.yaw_inertia
        states[index,:2]+=sign*n*(depth+1e-6)/2
    return {'impactSpeed':closing,'depth':depth,'normal':n.tolist(),'impulse':impulse}
