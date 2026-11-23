"""Product gates for residual rewards, clean races and base policies."""
import argparse,json,time
from pathlib import Path
import numpy as np
from game_academy import Episode
from game_rewards import specification
from game_residual import profile,snapshot,controls,initial_weights
from game_learning import Policy
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import frozen_actions


def rewards():
    rows={}
    for name in ('base','faster','stopped','straight-gas','full-gas'):
        e=Episode('oval-1','pace',83001,protocol='driving-memory-1',single_lap=True,reward_spec=specification(profile(1,'residual_ppo')))
        for _ in range(15000):
            action=controls(e.world,[[0.,1. if name=='faster' else 0.]],[0])[0]
            if name=='stopped':action[:]=[0.,-1.]
            if name=='straight-gas':action[:]=[0.,1.]
            if name=='full-gas':action[1]=1.
            e.step(action)
            if e.reason:break
        assert abs(sum(e.term_totals.values())-e.return_total)<1e-8
        rows[name]=dict(reason=e.reason,seconds=e.age,reward=e.return_total,terms=e.term_totals,clean=e.skill_valid(),brake=e.pedal_counts['brake'])
    assert rows['base']['reason']==rows['faster']['reason']=='success'
    assert rows['faster']['seconds']<rows['base']['seconds'] and rows['faster']['reward']>rows['base']['reward']
    assert all(rows[n]['reward']<rows['base']['reward'] and rows[n]['reason']!='success' for n in ('stopped','straight-gas','full-gas'))
    assert rows['base']['brake']>0
    return rows


def races():
    result=[]
    for count,laps,reverse in ((2,3,False),(4,5,True),(5,3,False),(5,5,True)):
        ps=[profile(i,m) for i,m in enumerate(('race_master','residual_ppo','residual_sac','residual_td3','residual_tactic')[:count],1)]
        policies=[Policy(snapshot(p,None if p['algorithm']=='race_master' else initial_weights(p))) for p in ps]
        w=World(count,47,shared=True,laps=laps,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True)
        w.reset(varied=False);w.race_lap_target=True
        if reverse:policies.reverse()
        start=time.monotonic();ticks=0
        while w.active.any() and ticks<50000:
            w.step(frozen_actions(w,policies),return_observations=False);ticks+=1
        assert not w.retired.any() and (w.lap_count==laps).all(),w.rows()
        result.append(dict(cars=count,laps=laps,reverse=reverse,ticks=ticks,seconds=time.monotonic()-start,results=w.rows()))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--rewards-only',action='store_true');a=p.parse_args()
    report=dict(status='passed',rewards=rewards(),races=[] if a.rewards_only else races())
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(status='passed',rewardBehaviors=len(report['rewards']),races=len(report['races']))))

if __name__=='__main__':main()
