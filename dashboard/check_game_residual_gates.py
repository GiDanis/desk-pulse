"""Headless actual-physics gates, with explicit training/evaluation provenance."""
import argparse,json,time
from pathlib import Path
import numpy as np
from game_residual import profile,snapshot,initial_weights
from game_learning import Policy
from game_academy import Episode
from game_rewards import specification


def run(policy,track,phase,seed,laps=1,spatial_rules=False):
    spec=specification(profile(seed,'residual_ppo'))
    if spatial_rules:spec['evaluationRules']='spatial-rules-2'
    mode='impara_infinito' if laps>1 else 'impara'
    e=Episode(track,phase,seed,launch_distance=20. if phase=='launch' else None,
        objective=mode,protocol='driving-memory-1',single_lap=True,reward_spec=spec)
    p=Policy(policy)
    for _ in range(180000):
        if e.reason=='window':e.next_window()
        if e.reason:break
        e.step(p.act(None,world=e.world,index=0))
        if laps>1 and e.clean_series>=laps:e.reason='success';break
    result=e.result();result['success']=e.reason=='success';result['age']=e.age
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--policy',type=Path)
    p.add_argument('--track',default='oval-1');p.add_argument('--full',action='store_true');p.add_argument('--tactics',action='store_true')
    p.add_argument('--seed-start',type=int,default=81001);p.add_argument('--spatial-rules',action='store_true');a=p.parse_args()
    policy=json.loads(a.policy.read_text()) if a.policy else snapshot(profile(1,'race_master'))
    start=time.monotonic();rows=[]
    phases=('overtake','defend','corner') if a.tactics else ('launch','pace')
    for phase in phases:
        for seed in range(a.seed_start,a.seed_start+(20 if a.full else 3)):
            r=run(policy,a.track,phase,seed,spatial_rules=a.spatial_rules);rows.append(dict(r,phase=phase,seed=seed))
    if not a.tactics:
        for seed in range(82001,82001+(5 if a.full else 1)):
            rows.append(dict(run(policy,a.track,'pace',seed,5),phase='endurance',seed=seed))
    groups={phase:dict(valid=sum(r['success'] for r in rows if r['phase']==phase),total=sum(r['phase']==phase for r in rows)) for phase in {r['phase'] for r in rows}}
    report=dict(kind='frozen-physical-gate',track=a.track,policy=policy,groups=groups,results=rows,seconds=time.monotonic()-start,
        allPassed=all(r['success'] for r in rows),trainingTransitions=0,seedStart=a.seed_start,evaluationRules='spatial-rules-2' if a.spatial_rules else 'legacy')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('policy','results')}))


if __name__=='__main__':main()
