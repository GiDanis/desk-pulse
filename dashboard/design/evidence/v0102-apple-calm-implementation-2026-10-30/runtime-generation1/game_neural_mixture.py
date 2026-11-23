"""Trainable neural experts for free driving and traffic; no controller in inference."""
import numpy as np

ARCHITECTURE='neural-experts-2x64-v1'
EXPERT_SIZE=91*64+65*2
SIZE=2*EXPERT_SIZE+91


def matches(weights,hidden,outputs,inputs):
    return hidden==128 and outputs==2 and inputs==90 and np.shape(weights)==(SIZE,)


def forward(weights,obs,cache=False):
    from game_learning import forward as dense
    first,c1=dense(weights[:EXPERT_SIZE],obs,64,cache=True)
    second,c2=dense(weights[EXPERT_SIZE:2*EXPERT_SIZE],obs,64,cache=True)
    x=np.concatenate((obs,np.ones((*obs.shape[:-1],1))),axis=-1)
    gate=1/(1+np.exp(-np.clip(x@weights[-91:],-40,40)))
    result=(1-gate[...,None])*first+gate[...,None]*second
    saved=dict(neuralMixture=True,first=first,second=second,c1=c1,c2=c2,gate=gate,x=x)
    return (result,saved) if cache else result


def backward(cache,dy):
    from game_learning import backward as dense
    g=cache['gate'][:,None]
    a=dense(cache['c1'],dy*(1-g));b=dense(cache['c2'],dy*g)
    dg=np.sum(dy*(cache['second']-cache['first']),axis=1)*g[:,0]*(1-g[:,0])
    return np.r_[a,b,cache['x'].T@dg]
