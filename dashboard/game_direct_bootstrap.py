"""Offline teacher preparation and versioned, immutable neural-base loading.

Training helpers are explicit; importing this module never collects or trains.
The asset contains a neural policy only. The teacher is absent from inference.
"""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import hashlib,json
import numpy as np
from game_direct import snapshot,features,DirectPolicy
from game_learning import Adam,forward,backward,random_weights
from game_residual import profile

ASSET=Path(__file__).with_name('game-direct-base.json')
TACTICAL_ASSET=Path(__file__).with_name('game-direct-tactical-base.json')


def direct_profile(seed,method):
    from game_racing_presets import production_profile
    return production_profile({**profile(seed,method),'controlMode':'direct','hidden':128})


@lru_cache(maxsize=2)
def base_asset(role='driving'):
    if role not in ('driving','traffic'):raise ValueError('Ruolo della base sconosciuto')
    data=json.loads((TACTICAL_ASSET if role=='traffic' else ASSET).read_text())
    if data.get('version')!='direct-base-2' or data.get('status')!='qualified':
        raise ValueError('Base neurale non qualificata')
    if data.get('role','driving')!=role:raise ValueError('Base neurale di un ruolo diverso')
    policy=data['policy'];DirectPolicy(policy)
    digest=hashlib.sha256(json.dumps(policy,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    if digest!=data['policyHash']:raise ValueError('Base neurale danneggiata')
    return data


def initial_weights(profile):
    data=base_asset('traffic' if profile['algorithm']=='residual_tactic' else 'driving');weights=np.asarray(data['policy']['weights'],dtype=float)
    if profile['hidden']!=data['policy']['hidden']:raise ValueError('Rete incompatibile con la base')
    return weights.copy()


def initial_policy(profile):
    if profile.get('trafficLearning')=='attack-1':
        from game_overtaking import prepared_policy
        return prepared_policy(profile)
    role='traffic' if profile['algorithm']=='residual_tactic' else 'driving'
    data=base_asset(role)
    return snapshot(profile,initial_weights(profile),dict(kind='prepared-neural-base',version=data['version'],
        policyHash=data['policyHash'],trainingSeed=data['trainingSeed'],role=role,teacherAtInference=False))


def physical_context(rng,randomized=False):
    from game_driving_memory import current_context
    c=deepcopy(current_context('oval-1'))
    if randomized:
        mass=float(rng.uniform(.9,1.1));power=float(rng.uniform(.85,1.15))
        c['vehicle']['mass']*=mass;c['vehicle']['yaw_inertia']*=mass
        c['vehicle']['power']*=power;c['vehicle']['drive_force']*=power
        c['condition']['grip_factor']=float(rng.uniform(.75,1.05))
        c['tire']['grip_factor']=float(rng.uniform(.9,1.05))
    if randomized:
        from game_catalog import configuration
        from game_driving_memory import physical_context as describe
        config=configuration('oval-1','race-68-v3')
        for name in ('vehicle','condition','tire'):config[name]=deepcopy(c[name])
        c=describe(config)
    return c


def fit(weights,x,y,rng,iterations,optimizer=None):
    optimizer=optimizer or Adam(len(weights))
    # A feature never observed during preparation must not retain a random
    # hidden-layer contribution when it first appears (e.g. a second rival).
    inactive=np.max(np.abs(x),axis=0)<1e-12
    weights[:90*64].reshape(90,64)[inactive]=0.
    for step in range(iterations):
        indices=rng.integers(0,len(x),128)
        raw,cache=forward(weights,x[indices],64,cache=True);action=np.tanh(raw)
        gradient=backward(cache,(action-y[indices])*(1-action*action)*np.array([4.,1.])/len(indices))
        optimizer.step(weights,gradient,.001 if step<iterations*2/3 else .0003)
    return optimizer,np.mean((np.tanh(forward(weights,x,64))-y)**2,axis=0)


def random_examples(seed,count=8192,factor=1.35,teacher_fn=None):
    from game_simulation import World
    from game_catalog import RACE_PHYSICS_VERSION,RaceVehicleSpec,ConditionProfile,TireProfile
    from game_control import pursuit_actions
    rng=np.random.default_rng(seed);x=[];y=[]
    w=World(128,seed,shared=False,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True);w.native_sensors=True
    for _ in range(count//128):
        context=physical_context(rng,True)
        w.vehicle=RaceVehicleSpec(**context['vehicle']);w.condition=ConditionProfile(**context['condition']);w.tire=TireProfile(**context['tire'])
        phase=rng.uniform(0,w.track.length,w.count);w.state[:,:3]=w.track.poses(phase)
        offset=rng.uniform(-3.,3.,w.count);heading=w.state[:,2].copy()
        w.state[:,0]-=np.sin(heading)*offset;w.state[:,1]+=np.cos(heading)*offset
        w.state[:,2]+=rng.uniform(-.23,.23,w.count);w.state[:,3]=rng.uniform(0,24,w.count)
        w.state[:,4]=rng.uniform(-.5,.5,w.count)
        angles=w.track.poses(phase[:,None]+np.array([0.,1.])[None,:])[:,:,2]
        curvature=(angles[:,1]-angles[:,0]+np.pi)%(2*np.pi)-np.pi
        w.state[:,5]=curvature*w.state[:,3]+rng.uniform(-.05,.05,w.count)
        w.state[:,6]=np.clip(np.arctan(curvature*w.vehicle.wheelbase)+rng.uniform(-.04,.04,w.count),-.52,.52)
        y.extend(teacher_fn(w) if teacher_fn else pursuit_actions(w,speed_factor=factor));x.extend(features(w,i) for i in range(w.count))
    return np.asarray(x),np.asarray(y)


def rollout(weights,seed,phase='pace',teacher=False,collect=False,factor=1.35,context=None,teacher_style='passing',teacher_fn=None):
    from game_academy import Episode
    from game_control import racing_actions
    from game_rewards import specification
    p=direct_profile(seed,'residual_ppo')
    from game_learning import Policy
    rivals=[Policy(snapshot(p,weights))] if weights is not None and phase in ('grid','race4') else []
    e=Episode('oval-1',phase,seed,rivals,protocol='driving-memory-1',single_lap=True,
        context=context,reward_spec=specification(p),pace_pressure=1.)
    driver=DirectPolicy(snapshot(p,weights)) if weights is not None else None
    x=[];y=[];maximum=0.;teacher_lane=e.world.racing_lane.copy()
    for tick in range(10000):
        # Copy labels before allowing the stateful teacher to update its own lane.
        if teacher:
            observation=features(e.world) if tick%6==0 else None
            actual_phase=e.world.training_phase
            if teacher_style=='following':e.world.training_phase='follow'
            if teacher_fn:
                if tick%6==0:held=teacher_fn(e.world,[0])[0]
                action=held
            else:action=racing_actions(e.world,[0],speed_factor=factor)[0]
            e.world.training_phase=actual_phase
            if observation is not None:x.append(observation);y.append(action.copy())
        else:
            if collect and tick%6==0:
                observation=features(e.world)
                lane=e.world.racing_lane.copy();e.world.racing_lane[:]=teacher_lane
                # Six physical ticks elapsed between labels. Advance only the
                # separate teacher memory, never the learner's actuators.
                actual_phase=e.world.training_phase
                if teacher_style=='following':e.world.training_phase='follow'
                if teacher_fn:label=teacher_fn(e.world,[0])[0]
                else:
                    for _ in range(6):label=racing_actions(e.world,[0],speed_factor=factor)[0]
                e.world.training_phase=actual_phase
                teacher_lane=e.world.racing_lane.copy();e.world.racing_lane[:]=lane
                x.append(observation);y.append(label)
            action=driver.act(e.world,0)
        e.step(action,return_observation=False);maximum=max(maximum,float(e.world.state[0,3])*3.6)
        if e.reason:break
    result=dict(seed=seed,phase=phase,reason=e.reason,seconds=e.age,valid=e.reason=='success',
        limits=int(e.world.track_limits[0]),contacts=e.contact_count,passes=e.passes,vmax=maximum,
        violations=getattr(e,'racecraft',{}).get('violations',0),context=deepcopy(e.context_config))
    return result,np.asarray(x),np.asarray(y)
