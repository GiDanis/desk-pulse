"""Frozen-policy counterfactuals only; never touches the installed game store."""
from pathlib import Path
import json,hashlib,math
import numpy as np
from game_learning import Policy,Adam
from game_direct import controls,features
from game_direct_bootstrap import direct_profile,initial_policy
from game_academy import Episode
from game_rewards import specification,reference_time
from game_residual import learning_potential
from game_neural_mixture import EXPERT_SIZE
from game_learning import forward,backward
P=Path(__file__).parent;private=Path('/tmp/smartpc-race-objective-private-2026-10-21');meta=json.loads((private/'private-meta.json').read_text());rows=[]
policies=[('Base','initial',initial_policy(direct_profile(2,'residual_ppo')))]
for d in meta['drivers'][1:]:
 for role in ('policy','candidate'):
  f=private/(d['name']+'-'+role+'.json')
  if f.exists():policies.append((d['name'],role,json.loads(f.read_text())))
for name,role,data in policies:
 for variant in ('unchanged','straight_full_gas','curve_pedal_plus_015'):
  profile=next((d['profile'] for d in meta['drivers'] if d['name']==name),direct_profile(2,'residual_ppo'))
  e=Episode('oval-1','pace',981001,protocol='driving-memory-1',single_lap=False,reward_spec=specification(profile),pace_pressure=1.)
  driver=Policy(data);trace=[];discounted=0.;discount=1.;shaped=0.;decision_reward=0.;ticks=0;previous=learning_potential(e);all_gate=[]
  while not e.reason:
   w=e.world;a=driver.act(None,world=w,index=0);x,y=w.state[0,:2];from game_catalog import TRACK
   straight=bool(abs(x)<TRACK.half_straight-10 and abs(y)>TRACK.radius-7 and abs(w.state[0,5])<.12)
   curve=bool(abs(x)>TRACK.half_straight+10 and abs(w.state[0,5])>.15)
   if variant=='straight_full_gas' and straight:a[1]=1.;controls(w,a,[0])
   if variant=='curve_pedal_plus_015' and curve:a[1]=min(1.,a[1]+.15);controls(w,a,[0])
   _,reward,done,terminated=e.step(a,return_observation=False);decision_reward+=reward;ticks+=1
   if ticks==6 or done:
    next_potential=0. if terminated else learning_potential(e);r=decision_reward+profile['gamma']*next_potential-previous
    discounted+=discount*r;shaped+=r;discount*=profile['gamma'];ticks=0;decision_reward=0.;previous=next_potential
   if round(w.time*60)%6==0:
    obs=features(w);_,cache=forward(np.array(data['weights']),obs[None,:],data['hidden'],cache=True)
    gate=float(cache['gate'][0]) if isinstance(cache,dict) else None;all_gate.append(gate)
    mu=w.surface.grip*w.condition.grip_factor*w.tire.grip_factor
    trace.append(dict(time=w.time,progress=float(w.progress[0]),lap=int(w.lap_count[0]),x=float(w.state[0,0]),y=float(w.state[0,1]),speedKmh=float(w.state[0,3]*3.6),pedal=float(a[1]),steer=float(a[0]),straight=straight,curve=curve,offset=float(w.coordinates()[0][0]),lateralUse=abs(float(w.acceleration[0,1]))/(mu*9.81),totalUse=float(np.linalg.norm(w.acceleration[0]))/(mu*9.81),gate=gate))
  flying=[r for r in trace if r['lap']>=1];ss=[r for r in flying if r['straight']];cs=[r for r in flying if r['curve']]
  row=dict(name=name,role=role,variant=variant,policyHash=hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest(),reason=e.reason,seconds=e.age,contacts=e.contact_count,limits=int(w.track_limits[0]),laps=w.lap_times[0],environmentReturn=e.return_total,terms=e.term_totals,shapedReturn=shaped,discountedShapedReturn=discounted,referenceSeconds=reference_time(w,e.reward_spec),flyingMeanStraightSpeed=float(np.mean([r['speedKmh'] for r in ss])) if ss else None,flyingMeanCurveSpeed=float(np.mean([r['speedKmh'] for r in cs])) if cs else None,meanStraightPedal=float(np.mean([r['pedal'] for r in ss])) if ss else None,meanCurvePedal=float(np.mean([r['pedal'] for r in cs])) if cs else None,meanCurveLateralUse=float(np.mean([r['lateralUse'] for r in cs])) if cs else None,peakLateralUse=max((r['lateralUse'] for r in flying),default=0.),meanSoloTrafficGate=float(np.mean(all_gate)),trace=trace)
  rows.append(row);print(name,role,variant,round(e.age,3),e.reason,round(row['meanCurveLateralUse'] or 0,3),flush=True)
# The optimizer experiment changes private arrays only, and uses the actual optimizer.
base=policies[0][2];w=np.array(base['weights']);e=Episode('oval-1','pace',981001,protocol='driving-memory-1',single_lap=True,reward_spec=specification(direct_profile(2,'residual_ppo')),pace_pressure=1.)
obs=features(e.world)[None,:];raw,cache=forward(w,obs,128,cache=True);g=backward(cache,np.array([[.2,-.3]]));before=w.copy();optimizer=Adam(len(w));optimizer.step(w,g,1e-5)
blocks={}
for label,part in [('solo',slice(0,EXPERT_SIZE)),('traffic',slice(EXPERT_SIZE,2*EXPERT_SIZE)),('gate',slice(2*EXPERT_SIZE,None))]:
 blocks[label]=dict(gradientNorm=float(np.linalg.norm(g[part])),updateNorm=float(np.linalg.norm(w[part]-before[part])),changedParameters=int(np.count_nonzero(w[part]-before[part])))
P.joinpath('frozen-objective-probes.json').write_text(json.dumps(dict(capturedAt=meta['capturedAt'],scope='Frozen saved networks; nominal oval, same seed 981001, three laps. Pedal interventions are diagnostics in private simulation, never installed assists. Returns implement current six-tick reward accumulation and shaping, not training gains.',rows=rows,optimizerProbe=dict(purpose='Mechanism demonstration on a synthetic output derivative; not a measured SAC/PPO training gradient',gate=float(cache['gate'][0]),blocks=blocks)),indent=2)+'\n')
