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
