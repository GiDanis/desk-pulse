"""Observable attack diagnostics and versioned competitive reward, no control."""
from copy import deepcopy
import numpy as np

VERSION='attack-1'
FAMILIES=('complete','attack','corner','defend','pace','recover','traffic')


def enabled(profile):return profile.get('trafficLearning')==VERSION


def prepared_policy(profile):
    """Experimental neural preparation, isolated from released factory assets."""
    from game_direct_bootstrap import base_asset
    from game_direct import snapshot
    from game_neural_mixture import EXPERT_SIZE
    weights=np.asarray(base_asset('traffic')['policy']['weights'],dtype=float).copy()
    # Warm, non-saturated gate; no rule is consulted during inference. This
    # candidate must qualify before any production profile can select it.
    weights[-91:]*=.5
    return snapshot(profile,weights,dict(kind='attack-experimental-preparation',version=VERSION,
        source=base_asset('traffic')['policyHash'],teacherAtInference=False))


def observe(e):
    w=e.world
    if w.count<2:return
    state=getattr(e,'attack',None)
    if state is None:
        state=dict(version=VERSION,ticks=0,opportunities=0,attacks=0,passes=0,
            queueSeconds=0.,alongsideSeconds=0.,idleAlongsideSeconds=0.,
            passTimes=[],rivals={},relativeReward=0.)
        e.attack=state
    state['ticks']+=1
    if state['ticks']%6!=1:return
    offset,_,_=w.coordinates();own=-float(offset[0]);margin=w.track.width/2-w.vehicle.width/2
    for j in range(1,w.count):
        if not w.active[j]:continue
        raw=float(w.progress[0]-w.progress[j]);gap=(-raw+w.track.length/2)%w.track.length-w.track.length/2
        lateral=float(offset[j]-offset[0]);distance=float(np.linalg.norm(w.state[j,:2]-w.state[0,:2]))
        r=state['rivals'].setdefault(str(j),dict(offered=False,attacked=False,started=None,lane=own))
        room=max(margin+float(offset[j]),margin-float(offset[j]))>w.vehicle.width+.7
        available=(w.vehicle.length+1<gap<40 and distance<50 and room and not w.was_offroad[0])
        if available and not r['offered']:
            r.update(offered=True,started=e.age,lane=own);state['opportunities']+=1
        beside=abs(gap)<w.vehicle.length+1 and distance<15
        if r['offered'] and not r['attacked'] and (abs(own-r['lane'])>.8 or beside):
            r['attacked']=True;state['attacks']+=1
        if 0<gap<25 and abs(lateral)<w.vehicle.width+.8:state['queueSeconds']+=.1
        if beside:
            state['alongsideSeconds']+=.1
            if abs(float(w.state[0,3]-w.state[j,3]))<.25:state['idleAlongsideSeconds']+=.1
        if e.passes>state['passes']:
            if r['attacked'] and gap<-w.vehicle.length-1:
                state['passTimes'].append(e.age-r['started']);state['passes']=e.passes
        if abs(gap)>55 and r['offered']:r.update(offered=False,attacked=False,started=None)


def relative_step(e,before):
    """Bounded signed advantage per fixed rival; no positive-only accumulation.

    Unwrapped progress and persistent opponents avoid a finish-line/nearest-car
    reset. Reward is zero for a transition with ego limits/contact/offroad.
    This is a competitive objective, not invariant potential shaping.
    """
    w=e.world
    if before is None or w.count<2:return 0.
    old,contacts,limits,outside=before
    current=np.clip((w.progress[0]-w.progress[1:])/40.,-1,1)
    delta=current-old
    if e.contact_count!=contacts or int(w.track_limits[0])!=limits or outside or w.was_offroad[0]:delta=np.minimum(delta,0.)
    # An inactive rival cannot be used as a source of passing reward.
    return float(np.sum(delta*w.active[1:]))*float(e.reward_spec.get('relativeAdvantage',0.))


def before_step(e):
    w=e.world
    return (np.clip((w.progress[0]-w.progress[1:])/40.,-1,1),e.contact_count,int(w.track_limits[0]),bool(w.was_offroad[0]))


def metrics(e):
    state=getattr(e,'attack',{})
    return {k:deepcopy(v) for k,v in state.items() if k!='rivals'}


def scenario(track_id,family,seed,profile):
    """Finite exercises in collection; visible preview is never reset by this."""
    from game_academy import Episode
    from game_rewards import specification
    from game_geometry import get_track
    track=get_track(track_id);rng=np.random.default_rng(seed)
    phase={'complete':'corner','attack':'overtake','corner':'corner','defend':'defend','pace':'pace','recover':'recovery','traffic':'overtake'}[family]
    e=Episode(track_id,phase,seed,protocol='driving-memory-1',single_lap=True,reward_spec=specification(profile),objective='impara_sorpasso' if family=='traffic' else 'impara',bots=1+seed%3 if family=='traffic' else 2)
    if family=='traffic':e.objective='impara'  # bounded collection, continuous physical world
    w=e.world
    start=0. if family in ('attack','complete','defend','pace','recover') else track.length*.18
    if family not in ('pace','recover','traffic'):
        ego_lane=float(rng.choice((-2.9,2.9))) if family=='complete' else 0.
        gap=0. if family=='complete' else -14. if family=='defend' else float(rng.uniform(12,24))
        w.state[0,:3]=track.pose(start,ego_lane);w.state[0,3]=8.
        w.state[1,:3]=track.pose(start+gap,0.);w.state[1,3]=6.
        w.previous_phase=w.coordinates()[2].copy();w.progress_origin=w.previous_phase.copy();w.progress[:]=[0.,gap]
        w.initialize_gates()
        e.initial_speed=8.
        if hasattr(w,'_segments'):del w._segments
        # Arm alongside drills from a real recent approach; no success credited.
        if family=='complete':e.encounters[0].update(armed=True,alongside=True,contacts=0,limits=0,held=0.,lapBand=0)
    e.spec.update(distance=None,limitSeconds=60. if family=='traffic' else 24.,attackFamily=family,label={'complete':'Completa il passaggio','attack':'Attacco sul rettilineo','corner':'Attacco in curva','defend':'Difendi e riparti','pace':'Ripasso del passo','recover':'Recupero','traffic':'Traffico e passo dopo il sorpasso'}[family])
    e.attack_training=True
    return e
