"""Private direct-driving feasibility. Never opens the production GameStore."""
import argparse,json,time
from pathlib import Path
import numpy as np
from game_learning import Adam,random_weights,forward,backward
from game_direct import features,controls,snapshot,DirectPolicy
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import pursuit_actions
from game_residual import profile

def direct_profile(hidden):
    return {**profile(31,"residual_ppo"), "hidden":hidden, "controlMode":"direct"}
from game_academy import Episode


def dataset(count=6144,seed=61001):
    rng=np.random.default_rng(seed);xs=[];ys=[]
    w=World(128,seed,shared=False,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True)
    w.native_sensors=True
    for _ in range(count//128):
        phase=rng.uniform(0,w.track.length,w.count)
        w.state[:,:3]=w.track.poses(phase)
        offsets=rng.uniform(-3.,3.,w.count)
        heading=w.state[:,2].copy()
        w.state[:,0]-=np.sin(heading)*offsets;w.state[:,1]+=np.cos(heading)*offsets
        w.state[:,2]+=rng.uniform(-.23,.23,w.count)
        w.state[:,3]=rng.uniform(0,19,w.count)
        w.state[:,4]=rng.uniform(-.5,.5,w.count)
        angles=w.track.poses(phase[:,None]+np.array([0.,1.])[None,:])[:,:,2]
        curvature=(angles[:,1]-angles[:,0]+np.pi)%(2*np.pi)-np.pi
        w.state[:,5]=curvature*w.state[:,3]+rng.uniform(-.05,.05,w.count)
        w.state[:,6]=np.clip(np.arctan(curvature*w.vehicle.wheelbase)+rng.uniform(-.04,.04,w.count),-.52,.52)
        # Independent label calculation: pursuit has no traffic/lane arbitration.
        ys.extend(pursuit_actions(w))
        xs.extend(features(w,i) for i in range(w.count))
    return np.asarray(xs),np.asarray(ys)


def fit(weights,hidden,x,y,rng,iterations,optimizer=None):
    adam=optimizer or Adam(len(weights))
    for j in range(iterations):
        rows=rng.integers(0,len(x),128)
        raw,cache=forward(weights,x[rows],hidden,cache=True);pred=np.tanh(raw)
        diff=(pred-y[rows])*np.array([4.,1.])
        grad=backward(cache,diff*(1-pred*pred)/len(rows))
        adam.step(weights,grad,.001 if j<iterations*2/3 else .0003)
    error=np.mean((np.tanh(forward(weights,x,hidden))-y)**2,axis=0)
    return adam,error


def rollout(weights,hidden,seed,collect=False,phase='pace'):
    e=Episode('oval-1',phase,seed,protocol='driving-memory-1',single_lap=True)
    e.world.native_sensors=True
    p=DirectPolicy(snapshot(direct_profile(hidden),weights))
    xs=[];ys=[];pedals=[];vmax=0.
    for tick in range(8000):
        if collect and tick%6==0:
            xs.append(features(e.world));ys.append(pursuit_actions(e.world,[0])[0])
        action=p.act(e.world,0)
        e.step(action,return_observation=False)
        vmax=max(vmax,float(e.world.state[0,3])*3.6);pedals.append(float(action[1]))
        if e.reason:break
    return dict(seed=seed,reason=e.reason,seconds=e.age,progress=e.valid_progress,
        limits=int(e.world.track_limits[0]),contacts=e.contact_count,vmax=vmax,
        fullThrottleFraction=float(np.mean(np.array(pedals)>.95))),xs,ys


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seed',type=int,default=31);parser.add_argument('--rounds',type=int,default=4);parser.add_argument('--iterations',type=int,default=4000);parser.add_argument('--output',required=True)
    a=parser.parse_args();start=time.monotonic();x,y=dataset();rng=np.random.default_rng(a.seed);hidden=64
    weights=random_weights(rng,hidden,inputs=90);adam,error=fit(weights,hidden,x,y,rng,a.iterations)
    trace=[]
    for r in range(a.rounds):
        results=[];new_x=[];new_y=[]
        for j in range(4):
            result,xx,yy=rollout(weights,hidden,62000+r*10+j,True)
            results.append(result);new_x.extend(xx);new_y.extend(yy)
        x=np.r_[x,np.asarray(new_x)];y=np.r_[y,np.asarray(new_y)]
        trace.append(dict(round=r,results=results,mse=error.tolist(),samples=len(x)))
        print(json.dumps(trace[-1]),flush=True)
        adam,error=fit(weights,hidden,x,y,rng,a.iterations//2,adam)
    results=[rollout(weights,hidden,s)[0] for s in (710001,710002,710003,710004,710005)]
    p=Path(a.output);p.with_suffix('.weights.json').write_text(json.dumps(snapshot(direct_profile(hidden),weights,dict(kind='teacher-imitation',trainingSeed=a.seed))))
    p.write_text(json.dumps(dict(seed=a.seed,hidden=hidden,trace=trace,results=results,mse=error.tolist(),wallSeconds=time.monotonic()-start,teacherAtInference=False),indent=2)+'\n')
    print(json.dumps(dict(final=results,seconds=time.monotonic()-start)),flush=True)
if __name__=='__main__':main()
