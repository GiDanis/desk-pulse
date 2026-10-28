"""Development diagnosis on frozen policies; no GameStore, learning or board IO."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import argparse,hashlib,json,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'dashboard'))
from game_academy import Episode
from game_rewards import specification
from game_residual import profile,snapshot,key
from game_learning import Policy
from game_control import pursuit_actions
R=Path(__file__).resolve().parent


def run(job):
    name,data,seed,distance=job
    spec={**specification(profile(1,'residual_tactic')),'evaluationRules':'spatial-rules-2'}
    e=Episode('oval-1','corner',seed,protocol='driving-memory-1',single_lap=True,reward_spec=spec)
    e.spec=dict(e.spec,distance=float(distance));p=Policy(data);prefix=hashlib.sha256();rows=[];pass_at=None;caps=0;line_error=0.;samples=0;before_progress=0.
    while not e.reason and e.age<80:
        w=e.world;u=p.act(None,world=w,index=0)
        factor=1+getattr(w,'residual_previous',np.zeros((w.count,2)))[0,1]*.25
        free=pursuit_actions(w,[0],factor,np.array([w.racing_lane[0]]))[0]
        caps+=int(u[1]<free[1]-1e-8)
        target=getattr(w,'residual_rules',{}).get(0,{}).get('requestedLine',float(w.racing_lane[0]))
        offset=-float(w.coordinates()[0][0]);line_error+=abs(target-offset);samples+=1
        old=e.passes;e.step(u)
        if old<e.passes and pass_at is None:pass_at=dict(seconds=e.age,progress=float(w.progress[0]))
        if samples==1 or before_progress<160.:
            prefix.update(np.asarray(w.state,dtype='<f8').tobytes())
        before_progress=e.valid_progress
        if samples%60==1:
            rows.append(dict(seconds=e.age,progress=float(w.progress[0]),speed=float(w.state[0,3]),gap=float(w.progress[1]-w.progress[0]),
                requestedLine=float(target),executedLine=offset,pedal=float(u[1]),unlimitedPedal=float(free[1]),passes=e.passes))
    r=e.result();r.update(policyName=name,policyHash=key(data),distance=distance,success=e.reason=='success',age=e.age,firstPass=pass_at,
        trafficCapSeconds=caps/60,meanLineErrorMeters=line_error/max(1,samples),prefixThrough160Sha256=prefix.hexdigest(),trace=rows)
    return r


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=R/'drill-results.json');a=p.parse_args()
    old=R.parent/'v09-timing-improvements-2026-10-16'
    neural=json.loads((old/'tactic-11.json').read_text())['champion']
    pilots=[('Maestro',snapshot(profile(1,'race_master'))),('Tattico-seed11-frozen',neural)]
    jobs=[(name,data,seed,distance) for name,data in pilots for seed in range(95201,95211) for distance in (160,240)]
    start=time.monotonic()
    with ProcessPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,jobs))
    for name,_ in pilots:
        for seed in range(95201,95211):
            pair=[r for r in results if r['policyName']==name and r['seed']==seed]
            assert pair[0]['prefixThrough160Sha256']==pair[1]['prefixThrough160Sha256'],(name,seed)
    result=dict(kind='development-frozen-drill-length-ablation',sourceHashes={n:hashlib.sha256((ROOT/'dashboard'/n).read_bytes()).hexdigest() for n in ('game_academy.py','game_control.py','game_residual.py','game_racecraft.py','game_simulation.py','game_rewards.py')},
        trainingTransitions=0,productionWrites=0,boardAccess=False,seedBank=[95201,95210],distances=[160,240],limitSeconds=50,identicalPhysicalPrefixThrough160=True,
        seconds=time.monotonic()-start,results=results)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    for name,_ in pilots:
        for distance in (160,240):
            rows=[r for r in results if r['policyName']==name and r['distance']==distance]
            print(name,distance,sum(r['success'] for r in rows),'/',len(rows),flush=True)

if __name__=='__main__':main()
