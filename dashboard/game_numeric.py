"""Owned numeric work buffers; JSON conversion happens at checkpoint boundaries."""
from copy import deepcopy
import numpy as np


def checkpoint_value(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:checkpoint_value(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [checkpoint_value(v) for v in value]
    return deepcopy(value)


class RolloutBuffer:
    """Time-major PPO fields, allocated once and reused after each update."""
    def __init__(self,capacity,saved=()):
        self.capacity=max(1,int(capacity),len(saved));self.fields=None;self.count=0
        for row in saved:self.append((*row,row[5]) if len(row)==7 else row)

    def __len__(self):return self.count
    def __bool__(self):return self.count>0
    def __eq__(self,other):
        if isinstance(other,list) and not other:return self.count==0
        if isinstance(other,RolloutBuffer):return self.snapshot()==other.snapshot()
        return NotImplemented
    def __iter__(self):
        for i in range(self.count):yield tuple(field[i] for field in self.fields)
    def clear(self):self.count=0
    def append(self,row):
        arrays=tuple(np.asarray(x) for x in row)
        if self.fields is None:
            self.fields=tuple(np.empty((self.capacity,*x.shape),dtype=x.dtype) for x in arrays)
        if len(arrays)!=len(self.fields) or any(x.shape!=f.shape[1:] for x,f in zip(arrays,self.fields)):
            raise ValueError('Dimensioni del rollout incompatibili')
        if self.count==self.capacity:
            self.capacity*=2
            grown=tuple(np.empty((self.capacity,*f.shape[1:]),dtype=f.dtype) for f in self.fields)
            for old,new in zip(self.fields,grown):new[:self.count]=old[:self.count]
            self.fields=grown
        for value,field in zip(arrays,self.fields):field[self.count]=value
        self.count+=1
    def arrays(self):return tuple(f[:self.count] for f in self.fields)
    def snapshot(self):return [[x.tolist() for x in row] for row in self]


class ExampleBuffer:
    """Bounded, chronological teacher replay; physical ring order is private."""
    def __init__(self,inputs,rows=(),capacity=2048,stratified=False):
        self.strata=[ExampleBuffer(inputs,capacity=capacity//4) for _ in range(4)] if stratified else None
        self.x=np.empty((capacity,inputs));self.y=np.empty((capacity,2))
        self.capacity=capacity;self.count=0;self.end=0
        for x,y in rows:
            if len(x)==inputs:self.append(x,y)

    @staticmethod
    def maneuver(x,y):
        if len(x)>=48 and min(x[46],x[47])<0:return 3
        if y[1]<-.05:return 0
        if abs(y[0])>.08:return 1
        return 2

    def append(self,x,y):
        if self.strata is not None:
            self.strata[self.maneuver(x,y)].append(x,y);self.count=sum(b.count for b in self.strata);return
        self.x[self.end]=x;self.y[self.end]=y
        self.end=(self.end+1)%self.capacity;self.count=min(self.capacity,self.count+1)

    def order(self):return (self.end-self.count+np.arange(self.count))%self.capacity

    def sample(self,rng,size=128):
        if self.strata is not None:
            pools=[b for b in self.strata if b.count]
            batches=[b.sample(rng,size//len(pools)+int(i<size%len(pools))) for i,b in enumerate(pools)]
            return tuple(np.concatenate([b[k] for b in batches]) for k in (0,1))
        order=self.order();size=min(size,self.count)
        selected=rng.integers(0,self.count,size)
        braking=np.flatnonzero(self.y[order,1]<-.05)
        if len(braking):
            n=max(1,size//4);selected[:n]=braking[rng.integers(0,len(braking),n)]
        slots=order[selected]
        return self.x[slots],self.y[slots]

    def snapshot(self):
        if self.strata is not None:return [row for b in self.strata for row in b.snapshot()]
        return [[self.x[i].tolist(),self.y[i].tolist()] for i in self.order()]
