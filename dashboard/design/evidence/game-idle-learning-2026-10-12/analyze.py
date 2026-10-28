"""Isolated reward probes; no driver stores, learned checkpoints or training.

Fixed commands are counterexamples to inspect the current objective. They do
not represent trained pilots or demonstrate a solution to stationary policies.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

HERE=Path(__file__).resolve().parent
DASHBOARD=HERE.parents[2]
sys.path.insert(0,str(DASHBOARD))
import numpy as np
from game_simulation import World, DT
from game_profiles import preset
from game_protocol import training_task
from game_learning import PPO, forward

gamma=preset()['gamma']
probes=[]
commands={'idle':[0.,0.], 'brake_at_rest':[0.,-1.], 'tiny_gas':[0.,.02],
          'gentle_gas':[0.,.05], 'launch':[0.,.2], 'strong_gas':[0.,.7],
          'hard_turn':[.8,1.]}
for track_id in ('oval-1','mallory-oval-1'):
    for phase,pace in (('control',0.),('pace',1.)):
        for name,command in commands.items():
            w=World(1,track_id=track_id)
            total,discounted=0.,0.
            for k in range(round(15/DT)):
                _,r,done=w.step(np.array([command]),pace=pace,return_observations=False)
                total+=float(r[0]);discounted+=gamma**k*float(r[0])
                if done[0]:break
            probes.append(dict(track=track_id,phase=phase,command=name,action=command,
                               simulated_s=w.time,progress_m=float(w.progress[0]),
                               speed_m_s=float(w.state[0,3]),retired=bool(w.retired[0]),
                               finished=bool(np.isfinite(w.finish[0])),
                               cumulative_reward=total,discounted_reward=discounted))

budgets=[]
for t in ('oval-1','technical-1','mallory-oval-1','varano-short-1'):
    for phase,pace in (('control',0.),('pace',1.)):
        task=training_task(t,phase)
        c=.02+.28*pace
        budgets.append(dict(track=t,phase=phase,**task,
                            stationary_undiscounted_reward=-c*task['limitSeconds'],
                            stationary_discounted_infinite_reward=-c*DT/(1-gamma)))

initial_samples=[]
obs=World(1,track_id='mallory-oval-1').observations()
for seed in range(1,6):
    p=preset(seed,'ppo'); learner=PPO(p)
    repeated=np.repeat(obs,2048,axis=0)
    actions,_,_,_=learner.sample(repeated)
    mean=forward(learner.actor,obs,p['hidden'])[0]
    initial_samples.append(dict(seed=seed,raw_mean=mean.tolist(),
                                raw_std=np.exp(learner.log_std).tolist(),
                                deterministic_action=np.tanh(mean).tolist(),
                                positive_gas_fraction=float(np.mean(actions[:,1]>0)),
                                gas_above_0_1_fraction=float(np.mean(actions[:,1]>.1))))

sources=('game_simulation.py','game_profiles.py','game_protocol.py',
         'game_curriculum.py','game_learning.py','game_worker.py','game_neat.py')
data=dict(date='2026-10-12',scope='PC fixed-command probes and untrained PPO initial sampling only',
          gamma=gamma,decision_hz=1/DT,rollout_seconds=preset()['rollout']*DT,
          discount_e_fold_s=-DT/math.log(gamma),
          gae_coefficient=gamma*.95,gae_e_fold_s=-DT/math.log(gamma*.95),
          future_reward_weights={str(s):gamma**round(s/DT) for s in (1,5,10,30,60)},
          candidate_gamma_by_tau_s={str(s):math.exp(-DT/s) for s in (20,40,60)},
          budgets=budgets,probes=probes,untrained_ppo_initial_samples=initial_samples,
          source_sha256={p:hashlib.sha256((DASHBOARD/p).read_bytes()).hexdigest() for p in sources})
(HERE/'audit.json').write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:v for k,v in data.items() if k not in ('probes','source_sha256')},indent=2))
print('Fixed-command probes:')
for p in probes:
    print(p['track'],p['phase'],p['command'],round(p['progress_m'],3),round(p['cumulative_reward'],3),round(p['discounted_reward'],3),'retired',p['retired'])
