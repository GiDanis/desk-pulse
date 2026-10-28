"""Independent frozen bank. Personal weights stay outside the evidence tree."""
from pathlib import Path
import hashlib,json,statistics,time
import numpy as np
from game_learning import Policy
from game_academy import Episode
from game_rewards import specification
from game_control import frozen_actions
from game_catalog import RACE_PHYSICS_VERSION
from game_simulation import World
from game_direct import features
from game_neural_mixture import SIZE
from game_residual import profile,snapshot,key

P=Path(__file__).parent
PRIVATE=Path('/tmp/smartpc-racing-implementation-private-20261021/snapshot/continued')
names=('Crono','Memoria','Linea','Tattico');start=time.monotonic();rows=[];policies=[]
for name in names:
    raw=json.loads((PRIVATE/(name+'.json')).read_text());versions={
        'solo':raw['champion'],'race':raw['state']['raceChampion']['policy']}
    policies.append(versions['race']);cached=P/('independent-'+name+'.json')
    if cached.exists():
        rows.append(json.loads(cached.read_text()));continue
    cases=[]
    for role,policy in versions.items():
        for seed in range(995101,995106):
            e=Episode('oval-1','pace',seed,protocol='driving-memory-1',single_lap=False,
                reward_spec=specification({'algorithm':policy['algorithm'],'controlMode':'direct','racingObjective':'valid-time-1'}),pace_pressure=1.)
            driver=Policy(policy)
            while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
            flying=[x['time'] for x in e.world.lap_times[0][1:] if x['clean']]
            cases.append(dict(role=role,seed=seed,hash=key(policy),reason=e.reason,
                flyingMedian=statistics.median(flying) if len(flying)==2 else None,
                contacts=e.contact_count,limits=int(e.world.track_limits[0]),laps=e.world.lap_times[0]))
    rows.append(dict(name=name,cases=cases));cached.write_text(json.dumps(rows[-1],indent=2)+'\n')
    print(name,'frozen solo/race complete',flush=True)
policies.insert(0,snapshot(profile(1,'race_master')))
races=[]
for rotation in range(5):
    order=list(range(5));order=order[rotation:]+order[:rotation]
    controllers=[Policy(policies[i]) for i in order]
    w=World(5,996101+rotation,shared=True,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True)
    w.native_sensors=True;w.race_lap_target=True;events=set();gate=[[] for _ in order]
    while w.active.any() and w.time<150 and not w.retired.any():
        if int(round(w.time*60))%60==0:
            for j,i in enumerate(order):
                weights=np.asarray(policies[i].get('weights',[]))
                if weights.shape==(SIZE,):
                    z=features(w,j);g=1/(1+np.exp(-np.clip(np.r_[z,1.]@weights[-91:],-40,40)))
                    gate[j].append(float(g))
        w.step(frozen_actions(w,controllers),return_observations=False)
        events.update((e['time'],tuple(e['cars'])) for e in w.events if e.get('type')=='contact')
    cars=[]
    for j,i in enumerate(order):
        cars.append(dict(name=('Maestro',*names)[i],slot=j,policy=key(policies[i]),
            finish=float(w.finish[j]) if np.isfinite(w.finish[j]) else None,
            laps=w.lap_times[j],limits=int(w.track_limits[j]),retired=bool(w.retired[j]),
            trafficExpertGateMean=statistics.mean(gate[j]) if gate[j] else None))
    races.append(dict(seed=996101+rotation,order=order,seconds=w.time,
        finished=int(np.isfinite(w.finish).sum()),contacts=len(events),limits=int(w.track_limits.sum()),cars=cars))
    print('Mixed grid',rotation,'arrivals',races[-1]['finished'],'contacts',len(events),flush=True)
out=dict(status='completed',scope='Independent nominal oval bank, actual continued copies, no production import',
    sourceHashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__import__('game_direct').__file__).parent.glob('game_*.py')},
    rows=rows,races=races,seconds=time.monotonic()-start)
(P/'independent-validation.json').write_text(json.dumps(out,indent=2)+'\n')
