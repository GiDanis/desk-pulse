"""Training-only expert routing with independent Adam moments and clocks.

Inference remains the same trainable neural mixture. No actuator is overridden.
"""
import numpy as np
from game_neural_mixture import EXPERT_SIZE,SIZE
from game_learning import Adam,backward


def traffic_rows(obs):
    return np.any(np.asarray(obs)[...,[17,24,31]]>.5,axis=-1)


def routed_backward(cache,derivative):
    if not isinstance(cache,dict) or not cache.get('neuralMixture'):
        return backward(cache,derivative)
    traffic=traffic_rows(cache['x'])
    gate=cache['gate'][:,None]
    solo=backward(cache['c1'],derivative*(1-gate)*(~traffic)[:,None])
    rivals=backward(cache['c2'],derivative*gate*traffic[:,None])
    dg=np.sum(derivative*(cache['second']-cache['first']),axis=1)
    dg*=gate[:,0]*(1-gate[:,0])*traffic
    return np.r_[solo,rivals,cache['x'].T@dg]


class RoutedAdam:
    parts=(slice(0,EXPERT_SIZE),slice(EXPERT_SIZE,2*EXPERT_SIZE),slice(2*EXPERT_SIZE,SIZE))

    def __init__(self,checkpoint=None):
        saved=(checkpoint or {}).get('expertBlocks')
        self.blocks=[]
        for index,part in enumerate(self.parts):
            state=saved[index] if saved else None
            if state is None and checkpoint and len(checkpoint.get('m',[]))==SIZE:
                state=dict(m=checkpoint['m'][part],v=checkpoint['v'][part],t=checkpoint['t'])
            self.blocks.append(Adam(part.stop-part.start,state))

    def step(self,params,gradient,rate,obs):
        traffic=traffic_rows(obs)
        active=(bool(np.any(~traffic)),bool(np.any(traffic)),bool(np.any(traffic)))
        for part,optimizer,enabled in zip(self.parts,self.blocks,active):
            if enabled:optimizer.step(params[part],gradient[part],rate)

    def snapshot(self):
        states=[optimizer.snapshot() for optimizer in self.blocks]
        # Common keys keep the ordinary loader compatible before routing is set.
        return dict(m=sum((s['m'] for s in states),[]),v=sum((s['v'] for s in states),[]),
                    t=max(s['t'] for s in states),expertBlocks=states,routing='presence-separated-1')


def apply(optimizer,params,gradient,rate,obs):
    if len(params)!=SIZE:
        optimizer.step(params,gradient,rate)
        return optimizer
    if not isinstance(optimizer,RoutedAdam):optimizer=RoutedAdam(optimizer.snapshot())
    optimizer.step(params,gradient,rate,obs)
    return optimizer
