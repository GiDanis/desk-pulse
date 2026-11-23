"""Offline actuator coverage on sampled physical states, never race evidence.

This supplements clean rollouts with recovery, close-rival braking and launch
states. No teacher input is added to the deployed observation contract.
"""
from pathlib import Path
import argparse,time
import numpy as np
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_direct import features,ROAD_FEATURES
from game_lab.teacher import Teacher
from game_lab.artifacts import atomic_report,digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--samples',type=int,default=50000);a=p.parse_args()
    if a.output.exists():raise ValueError('Coverage is immutable')
    a.output.parent.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(a.seed);started=time.monotonic()
    w=World(4,a.seed,shared=True,physics=RACE_PHYSICS_VERSION,lazy_sensors=True);w.native_sensors=True
    xs=[];ys=[];plans=[]
    for number in range(a.samples):
        phase=float(rng.uniform(0,w.track.length));lanes=rng.uniform(-4.4,4.4,4);gaps=rng.uniform(-50,80,4);gaps[0]=0
        # Frequent approaching traffic includes braking before an occupied
        # lane. Exclude overlapping bodies; these are pre-contact states.
        if number%2:gaps[1]=rng.uniform(6,35);lanes[1]=lanes[0]+rng.uniform(-.5,.5)
        for i in range(1,4):
            if abs(gaps[i])<6 and abs(lanes[i]-lanes[0])<2.8:gaps[i]=np.copysign(6.,gaps[i])
        w.active[:]=True;w.active[1+number%4:]=False
        for i in range(4):w.state[i,:3]=w.track.pose(phase+gaps[i],float(lanes[i]))
        w.state[:,2]+=rng.uniform(-.12,.12,4);w.state[:,3]=rng.uniform(3,23,4)
        if number%5==0:w.state[0,3]=rng.uniform(0,3)
        w.state[:,4]=rng.uniform(-.3,.3,4);w.state[:,5]=rng.uniform(-.3,.6,4);w.state[:,6]=rng.uniform(-.2,.3,4)
        w.progress[:]=gaps;w.acceleration[:,0]=rng.uniform(-3,3,4);w.acceleration[:,1]=rng.uniform(-2,2,4)
        w.direct_previous[:]=rng.uniform(-1,1,(4,2));w.time=number*.1
        teacher=Teacher();teacher.lane=float(np.round(rng.uniform(-3.7,3.7),1));teacher.target=teacher.lane
        label=teacher.label(w)
        xs.append(features(w,version=ROAD_FEATURES));ys.append(label);plans.append(teacher.last_intent)
        if number%5000==0:print('coverage',a.seed,number,flush=True)
    with a.output.open('xb') as stream:np.savez_compressed(stream,x=np.asarray(xs,dtype=np.float32),y=np.asarray(ys,dtype=np.float32),intent=np.asarray(plans,dtype=np.float32),featureVersion=ROAD_FEATURES)
    atomic_report(a.output.with_suffix('.json'),dict(kind='sampled-physical-state-supervision',seed=a.seed,samples=a.samples,
        teacherVersion=Teacher.VERSION,featureVersion=ROAD_FEATURES,sha256=digest(a.output),wallSeconds=time.monotonic()-started,
        episodeEvidence=False,qualified=False))

if __name__=='__main__':main()
