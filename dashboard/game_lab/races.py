"""Measured frozen-policy qualifying/races using the production World/control.

Headless results prove physics/arrival only. They explicitly do not certify
screen visibility, independent preparations, or reinforcement learning gains.
"""
import time
import numpy as np
from game_catalog import configuration
from game_control import frozen_actions
from game_learning import Policy
from game_simulation import World,DT
from game_residual import key


def run(policies,*,qualifying=False,laps=3,seed=1,track='oval-1',limit=240.,qualifying_times=None):
    if not policies or (qualifying and len(policies)!=1) or (not qualifying and not 2<=len(policies)<=5):raise ValueError('Frozen grid size')
    if type(laps) is not int or laps<3:raise ValueError('Full multi-lap evaluation required')
    config=configuration(track,'race-68-v3');actors=[Policy(p) for p in policies]
    from game_protocol import finish_window
    if qualifying_times is not None and len(qualifying_times)!=len(policies):raise ValueError('Grid qualifying identities')
    window=finish_window(qualifying_times or [],laps)
    if any(p.inputs!=68 or p.snapshot['observation']!='race-68-v3' for p in actors):raise ValueError('Race physics contract')
    w=World(len(policies),seed,shared=not qualifying,laps=laps,track_id=track,physics=config['physics'],telemetry=True)
    if qualifying:w.reset(varied=False)
    else:w.race_lap_target=True
    ids=['car-'+str(i) for i in range(w.count)]
    w.enable_timing('qualifica' if qualifying else 'gara')
    for i,p in enumerate(policies):w.timing.bind(i,ids[i],key(p))
    started=time.monotonic();deadline=float(limit);frames=0;represented=True
    while w.active.any() and w.time<deadline:
        w.training_phase='control'
        w.training_context[:,0]=np.minimum(1,w.episode_time/2)
        w.training_context[:,1]=np.clip((w.episode_time-w.credit_age)/15,0,1)
        w.training_context[:,2]=np.clip(w.safe_distance-w.progress_credit,0,1)
        w.training_context[:,3]=1/9
        w.step(frozen_actions(w,actors),return_observations=False)
        if not qualifying and np.isfinite(w.finish).any():deadline=min(deadline,float(np.nanmin(w.finish))+window)
        if round(w.time/DT)%2==0:
            rows=w.rows(ids);represented=represented and len(rows)==len(policies) and {r['id'] for r in rows}==set(ids);frames+=1
        # Headless timing is drained as the production writer does; no
        # unbounded event backlog is accumulated during long evaluation.
        w.timing.drain()
    rows=w.rows(ids)
    for i,row in enumerate(rows):
        if w.active[i]:row['status']='tempo scaduto'
    arrived=[r['status']=='arrivato' and r['lap']>=laps for r in rows]
    return dict(kind='measured-headless-qualifying' if qualifying else 'measured-headless-race',cars=w.count,laps=laps,
        seed=seed,configuration=config,policies=[key(p) for p in policies],results=rows,events=w.events,
        complete=all(arrived),allCarsRepresented=represented,framesChecked=frames,allCarsVisible=False,
        visibilityQualification='requires actual GUI scene/render verification',
        finishWindowSeconds=window,simulatedSeconds=w.time,wallSeconds=time.monotonic()-started,qualified=False,installed=False)
