"""Bounded CPU benchmark; private worlds, no production pilot writes."""
import argparse
import cProfile
import io
import json
import os
from pathlib import Path
import pstats
import sys
import time

os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
p=argparse.ArgumentParser()
p.add_argument('--runtime',required=True)
p.add_argument('--output',required=True)
p.add_argument('--optimized',action='store_true')
a=p.parse_args()
sys.path.insert(0,a.runtime)
import numpy as np
from game_simulation import World,DT
from game_learning import Policy,policy_snapshot,random_weights

policy=Policy(policy_snapshot(random_weights(np.random.default_rng(11),16),16))
results=[]
for count,shared in [(1,False),(4,True),(10,False),(32,False),(128,False),(256,False)]:
    w=World(count,shared=shared)
    components=dict(sensors=0.,network=0.,physics=0.)
    ticks=0;start=time.perf_counter()
    while time.perf_counter()-start<2:
        t=time.perf_counter();obs=w.observations();components['sensors']+=time.perf_counter()-t
        t=time.perf_counter();actions=policy.act(obs);components['network']+=time.perf_counter()-t
        # Fixed acceleration exercises road checks throughout a lap; network
        # is still measured separately. Reset before leaving the lower straight.
        actions[:,0]=0;actions[:,1]=1
        t=time.perf_counter()
        if a.optimized:w.step(actions,return_observations=False)
        else:w.step(actions)
        components['physics']+=time.perf_counter()-t
        ticks+=1
        if w.time>4:w.reset()
    wall=time.perf_counter()-start
    results.append(dict(count=count,shared=shared,ticks=ticks,wallSeconds=wall,
                        simulatedSecondsPerWallSecond=ticks*DT/wall,
                        tickMilliseconds=wall/ticks*1000,
                        componentMilliseconds={k:v/ticks*1000 for k,v in components.items()}))
w=World(32)
actions=np.tile([0.,1.],(32,1))
prof=cProfile.Profile();prof.enable()
for i in range(1000):
    w.observations()
    if a.optimized:w.step(actions,return_observations=False)
    else:w.step(actions)
    if w.time>4:w.reset()
prof.disable();out=io.StringIO();pstats.Stats(prof,stream=out).sort_stats('cumulative').print_stats(18)
Path(a.output).write_text(json.dumps(dict(optimized=a.optimized,results=results,profile=out.getvalue()),indent=2)+'\n')
print(json.dumps(results,indent=2),flush=True)
