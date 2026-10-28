"""Frozen diagnosis, no learning or production writes. Run with PYTHONPATH=dashboard."""
from pathlib import Path
from copy import deepcopy
import json,time,hashlib
import numpy as np
from game_academy import Episode
from game_direct import snapshot,features
from game_direct_bootstrap import base_asset,direct_profile
from game_learning import Policy,forward
from game_rewards import specification
from game_residual_trainer import reward_profile
from game_residual import key

HERE=Path(__file__).parent
private=Path('/tmp/smartpc-overtaking-study-20261022/snapshot.json')
if private.exists():
 data=json.loads(private.read_text());origin=data['capturedAt'];models=data['models'];drivers=data['drivers']
else:
 root=Path('/tmp/smartpc-pilot-menu-20261021/saved')
 data=json.loads((root/'metadata.json').read_text());origin=data['capturedAt'];drivers=data['drivers']
 models={d['profile']['algorithm']:json.loads((root/(d['profile']['algorithm']+'.json')).read_text()) for d in drivers if d['checkpoint']}
policies=[]
for d in drivers:
 if not d['checkpoint']:continue
 c=models[d['profile']['algorithm']]
 policies.append((d['name'],'candidate',snapshot(d['profile'],c['learner']['actor'])))
 policies.append((d['name'],'raceChampion',c['curriculum'].get('raceChampion',c['curriculum']['champion'])['policy']))
for role in ('driving','traffic'):
 policies.append(('Base '+role,'factory',base_asset(role)['policy']))

def run(name,role,policy,seed,traffic):
 p=reward_profile(policy);reward={**specification(p),'evaluationRules':'spatial-rules-2'}
 e=Episode('oval-1','overtake' if traffic else 'pace',seed,objective='impara_sorpasso' if traffic else 'impara_infinito',bots=2,protocol='driving-memory-1',reward_spec=reward,pace_pressure=1.)
 driver=Policy(policy);traces=[];samples=[];along=0;queue=0;stall_along=0
 start=time.monotonic()
 while not e.reason:
  w=e.world;action=driver.act(None,world=w,index=0)
  if round(w.time*60)%6==0:
   z=features(w);_,cache=forward(np.asarray(policy['weights']),z,policy['hidden'],cache=True)
   gates=float(cache['gate']) if cache.get('neuralMixture') else None
   gaps=(w.progress[1:]-w.progress[0]+w.track.length/2)%w.track.length-w.track.length/2
   offsets=w.coordinates()[0];j=int(np.argmin(np.abs(gaps)))+1 if traffic else None
   gap=float(gaps[j-1]) if j else None
   lateral=float(offsets[j]-offsets[0]) if j else None
   beside=bool(j and abs(gap)<w.vehicle.length+1 and np.linalg.norm(w.state[j,:2]-w.state[0,:2])<15)
   behind=bool(j and w.vehicle.length<gap<25 and abs(lateral)<w.vehicle.width+1)
   along+=int(beside);queue+=int(behind);stall_along+=int(beside and w.state[0,3]<1)
   row=dict(t=round(w.time,3),speedKmh=float(w.state[0,3]*3.6),pedal=float(action[1]),steer=float(action[0]),gap=gap,lateral=lateral,gate=gates,passes=e.passes,contact=e.contact_count,
       soloPedal=float(np.tanh(cache['first'][1])) if gates is not None else None,trafficPedal=float(np.tanh(cache['second'][1])) if gates is not None else None)
   samples.append(row)
   if round(w.time*60)%60==0:traces.append(row)
  e.step(action,return_observation=False)
 speeds=[s['speedKmh'] for s in samples if s['t']>=5]
 out=dict(name=name,role=role,policyHash=key(policy),seed=seed,traffic=traffic,reason=e.reason,seconds=e.age,passes=e.passes,attempts=e.pass_attempts,
  contacts=e.contact_count,limits=int(w.track_limits[0]),violations=getattr(e,'racecraft',{}).get('violations',0),ruleCounts={k:v for k,v in getattr(e,'racecraft',{}).items() if k in ('weaves','unnecessaryBrake','spaceViolations')},
  reward=e.return_total,rewardTerms=e.term_totals,progress=float(w.progress[0]),alongsideSeconds=along*.1,queueSeconds=queue*.1,stoppedAlongsideSeconds=stall_along*.1,
  meanSpeedAfter5=float(np.mean(speeds)) if speeds else None,meanGate=float(np.mean([s['gate'] for s in samples])) if samples[0]['gate'] is not None else None,
  meanPedal=float(np.mean([s['pedal'] for s in samples])),meanSoloShadowPedal=float(np.mean([s['soloPedal'] for s in samples])) if samples[0]['gate'] is not None else None,
  meanTrafficShadowPedal=float(np.mean([s['trafficPedal'] for s in samples])) if samples[0]['gate'] is not None else None,
  laps=[dict(time=l['time'],clean=l['clean']) for l in w.lap_times[0]],wallSeconds=time.monotonic()-start,trace=traces)
 return out

if __name__=='__main__':
 rows=[]
 for name,role,policy in policies:
  for seed in (961101,961102,961103):
   for traffic in ([True,False] if role in ('candidate','factory') else [True]):
    row=run(name,role,policy,seed,traffic);rows.append(row)
    (HERE/'frozen-probes.json').write_text(json.dumps(dict(status='diagnostic-only',capturedAt=origin,productionChanges=False,teacherAtLearnerInference=False,newTraining=False,scope='Three fixed scenario seeds, frozen checkpoints; not convergence or a default selection',shadowScope='Expert shadow commands recomputed after the real command updates previous-action inputs; not exact actuator decompositions',rows=rows),indent=2)+'\n')
    print(name,role,seed,'traffic' if traffic else 'solo','passes',row['passes'],'queue',round(row['queueSeconds'],1),'v',round(row['meanSpeedAfter5'] or 0,1),'contacts',row['contacts'],'reason',row['reason'],flush=True)
