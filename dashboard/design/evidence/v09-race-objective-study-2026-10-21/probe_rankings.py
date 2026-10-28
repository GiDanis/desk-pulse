"""Reward ordering audit on frozen private networks; no training or installation."""
from pathlib import Path
from copy import deepcopy
import json
import numpy as np
from game_learning import Policy
from game_direct import controls
from game_direct_bootstrap import direct_profile, initial_policy
from game_academy import Episode
from game_rewards import specification
from game_residual import learning_potential
from game_driving_memory import current_context
from game_catalog import TRACK

OUT = Path(__file__).parent
PRIVATE = Path('/tmp/smartpc-race-objective-private-2026-10-21')
meta = json.loads((PRIVATE/'private-meta.json').read_text())
rows = []
for name in ('Base', 'Crono', 'Memoria'):
    profile = next((d['profile'] for d in meta['drivers'] if d['name']==name), direct_profile(2,'residual_ppo'))
    data = initial_policy(profile) if name=='Base' else json.loads((PRIVATE/(name+'-candidate.json')).read_text())
    for grip_factor in (1., .85):
        for variant in ('unchanged', 'straight_full_gas', 'curve_pedal_plus_015', 'always_full_gas'):
            context = deepcopy(current_context('oval-1'))
            context['condition']['grip_factor'] *= grip_factor
            e = Episode('oval-1','pace',981017,protocol='driving-memory-1',single_lap=False,
                        reward_spec=specification(profile),pace_pressure=1.,context=context)
            driver=Policy(data); discount=1.; ticks=0; previous=learning_potential(e)
            discounted_terms={}; block_terms={}; shaping=0.
            while not e.reason:
                w=e.world; action=driver.act(None,world=w,index=0); x,y=w.state[0,:2]
                straight=abs(x)<TRACK.half_straight-10 and abs(y)>TRACK.radius-7 and abs(w.state[0,5])<.12
                curve=abs(x)>TRACK.half_straight+10 and abs(w.state[0,5])>.15
                if variant=='always_full_gas' or (variant=='straight_full_gas' and straight): action[1]=1.
                elif variant=='curve_pedal_plus_015' and curve: action[1]=min(1.,action[1]+.15)
                controls(w,action,[0])
                _,_,done,terminated=e.step(action,return_observation=False); ticks+=1
                for k,v in e.last_reward_terms.items(): block_terms[k]=block_terms.get(k,0.)+v
                if ticks==6 or done:
                    potential=0. if terminated else learning_potential(e)
                    shaping+=discount*(profile['gamma']*potential-previous)
                    for k,v in block_terms.items(): discounted_terms[k]=discounted_terms.get(k,0.)+discount*v
                    discount*=profile['gamma']; ticks=0; block_terms={}; previous=potential
            discount_total=sum(discounted_terms.values())+shaping
            row=dict(name=name,role='initial' if name=='Base' else 'candidate',gripFactor=grip_factor,seed=981017,
                     variant=variant,seconds=e.age,reason=e.reason,contacts=e.contact_count,
                     limits=int(w.track_limits[0]),laps=w.lap_times[0],returnTotal=e.return_total,
                     terms=e.term_totals,discountedTerms=discounted_terms,discountedShaping=shaping,
                     discountedShapedReturn=discount_total,
                     rescored=[dict(understeerWeight=weight,
                         returnTotal=e.return_total+(weight-1.)*e.term_totals['understeer'],
                         discountedShapedReturn=discount_total+(weight-1.)*discounted_terms['understeer'])
                         for weight in (0.,.05,.1,.25,1.)])
            rows.append(row)
            print(name,grip_factor,variant,e.reason,round(e.age,3),round(e.return_total,6),flush=True)
OUT.joinpath('reward-ordering-audit.json').write_text(json.dumps(dict(
    capturedAt=meta['capturedAt'],scope='Frozen network diagnostics and rescoring, not retraining. Seed 981017 changes initial lateral/heading perturbations; it is not an independent training seed. Grip 0.85 is a changed physical context. Interventions only alter copied simulation commands.',
    rows=rows),indent=2)+'\n')
