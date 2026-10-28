"""Fixed-budget private experiment: complete outcome/cost and immutable models."""
from pathlib import Path
import argparse,json,time,hashlib,statistics
import numpy as np
from game_direct_bootstrap import direct_profile,initial_policy
from game_direct_trainer import DirectTrainer
from game_learning import Policy
from game_rewards import specification
from game_academy import Episode

p=argparse.ArgumentParser()
p.add_argument('--method',required=True);p.add_argument('--seed',type=int,required=True)
p.add_argument('--variant',default='baseline');p.add_argument('--budget',type=int,default=98304)
p.add_argument('--output',required=True);p.add_argument('--resume')
a=p.parse_args();profile=direct_profile(a.seed,a.method)
PROFILE_KEYS=('racingObjective','racingCurriculum','expertLearning','racingAnchor','episodeExploration','racingBackup','racingHorizon','raceValidationEvery')
profile={k:v for k,v in profile.items() if k not in PROFILE_KEYS}
if a.variant=='production':
    from game_racing_presets import production_profile
    profile=production_profile(profile)
else:
    if a.variant=='baseline':profile['racingObjective']='legacy'
    if a.variant!='baseline':profile['racingObjective']='valid-time-1'
    if a.variant not in ('baseline','reward-only'):profile['racingCurriculum']='graduated-1'
    if a.variant in ('routed','final','multi-step','retained','circuit-fixed','episode-noise','episode-retained','ppo-horizon'):profile['expertLearning']='routed-1'
    if a.variant=='multi-step':profile['racingBackup']=3
    if a.variant in ('retained','episode-retained','ppo-horizon'):profile['racingAnchor']='steering-retained-1'
    if a.variant in ('episode-noise','episode-retained'):profile['episodeExploration']='coherent-pedal-1'
    if a.variant=='ppo-horizon':profile['racingHorizon']=4.
start=time.monotonic();cpu_start=time.process_time();checkpoint=json.loads(Path(a.resume).read_text()) if a.resume else None
if checkpoint and len(Path(a.resume).stem)==64:checkpoint['migrationSource']=Path(a.resume).stem
t=DirectTrainer(profile,'oval-1',checkpoint);initial=t.state['champion']['policy'];start_steps=t.steps
start_decisions=t.decisions
while t.steps<start_steps+a.budget or t.check or t.iterator:t.tick()
learning_seconds=time.monotonic()-start
results={}
for role,policy in (('initial',initial),('candidate',t.learner.policy()),('champion',t.state['champion']['policy'])):
    driver=Policy(policy);cases=[]
    for seed in (991001,991002,991003,991004,991005):
        e=Episode('oval-1','pace',seed,protocol='driving-memory-1',single_lap=False,
                  reward_spec=specification(profile),pace_pressure=1.)
        while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
        flying=[row['time'] for row in e.world.lap_times[0][1:] if row['clean']]
        cases.append(dict(seed=seed,reason=e.reason,seconds=e.age,
            flyingMedian=statistics.median(flying) if len(flying)==2 else None,
            laps=e.world.lap_times[0],contacts=e.contact_count,limits=int(e.world.track_limits[0])))
    results[role]=cases
source=Path(__import__('game_direct').__file__).parent
hashes={n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in
        ('game_direct.py','game_direct_trainer.py','game_rewards.py','game_residual_trainer.py',
         'game_learning.py','game_residual_learning.py','game_neural_mixture.py','game_school_lessons.py','game_academy.py')}
out=dict(method=a.method,seed=a.seed,variant=a.variant,physicalSteps=t.steps-start_steps,
    decisions=t.decisions,updates=t.learner.update_index,learningSeconds=learning_seconds,
    totalWallSeconds=time.monotonic()-start,evaluationSeconds=t.state.get('evaluationSeconds',0),
    processCpuSeconds=time.process_time()-cpu_start,collectedDecisions=t.decisions-start_decisions,
    stats=t.state['stats'],schoolStats=t.state.get('schoolStats',{}),evaluations=t.state['evaluations'],
    champion=t.state['champion']['policy'],candidate=t.learner.policy(),recipe=t.spec,results=results,
    state={k:v for k,v in t.state.items() if k not in ('champion','verifiedBest','evaluations')},
    teacherOverridesEgo=0,teacherLabelsInRL=0,sourceHashes=hashes)
Path(a.output).write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k] for k in ('method','seed','variant','physicalSteps','updates','learningSeconds')})+
      ' champion='+str([r['flyingMedian'] for r in results['champion']]),flush=True)
