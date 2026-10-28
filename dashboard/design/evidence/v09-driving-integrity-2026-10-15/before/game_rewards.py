"""Versioned driving objective; no action is overridden or rewarded directly."""
from copy import deepcopy
import hashlib
import json
import math

VERSION = 'balanced-driving-1'
CURRICULUM = 'corner-control-1'
TERMS = ('progress', 'time', 'finish', 'contact', 'offroad', 'exit',
         'retirement', 'understeer', 'control', 'task', 'stall', 'recovery')


def specification(profile=None):
    spec=dict(version=VERSION, curriculum=CURRICULUM, progressPerLap=10.,
                cleanLap=3., timeControl=.5, timePace=2., exit=.5,
                outside=2., retirement=3., understeer=1.,
                stall=.5, drillProgress=2., drillSuccess=2., recovery=.5,
                passReward=.5, smooth=.1, referenceSpeed=9.)
    if profile and profile.get('algorithm')=='evolution':
        spec.update(version='balanced-driving-2',curriculum='evo-progressive-1',evoVersion='evo-progressive-1',stall=3.)
    return spec


def digest(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def migrate(checkpoint, profile, objective):
    """Start-only migration: keep personal weights/topology/RNG and source intact.

    Old fitness/critic returns are not comparable. A new rollout starts from a
    declared episode boundary; the original checkpoint remains an immutable file.
    """
    original = checkpoint or {}
    target=specification(profile);version=target['version']
    if (original.get('rewardSpec') or {}).get('version') == version:
        return deepcopy(original)
    result = deepcopy(original)
    backend = result.get('learner')
    if backend:
        backend.update(bestScore=None, buffer=[], pending=None)
        if profile['algorithm']=='evolution':backend.update(bestKey=None,currentKey=None,stagnation=0,mutationScale=1.)
        if profile['algorithm'] in ('ppo', 'ppo_smooth'):
            import numpy as np
            from game_learning import random_weights
            from game_catalog import observation_size
            # Separate deterministic RNG: do not consume the actor's saved stream.
            backend['critic'] = random_weights(np.random.default_rng(profile['seed']+8101),
                profile['hidden'], 1, inputs=observation_size(profile['observation'])).tolist()
            backend.pop('criticAdam', None)
        elif profile['algorithm']=='neat':
            backend['best']=None
            for genome in backend.get('population', []):genome['fitness']=None
            for species in backend.get('species', []):
                species.update(fitness_history=[], fitness=None, adjusted_fitness=None)
        # Clone's labelled examples remain valid; they are not reward targets.
    state = result.get('curriculum')
    if state:
        state.update(rewardVersion=version, rewardSpec=target, pending=None,
                     reliableWindows=0, phaseUpdates=0, pacePressure=0., curveReady=False)
        if objective=='impara' and state.get('phase')!='launch':state['phase']='bend'
        if target.get('evoVersion') and objective=='impara':
            state.update(phase='launch',launchGoal=1.,launchWindow=[],phaseUpdates=0)
            state.pop('evoTraining',None)
        if target.get('evoVersion'):state['epochStats']=dict(version=version,startedSteps=original.get('steps',0),episodes=0,byTask={})
        state['stats']={**state.get('stats',{}), 'rewardTerms':{}}
    result.update(rewardSpec=target, rewardEpoch=target['curriculum'],
                  episodes=None, fitness=None, inflight=None, observationRows=[],
                  collectorResults=None, physicsResults=None, visibleEpisodes=None, memoryReview=None,
                  previousReward=(original.get('curriculum') or {}).get('rewardVersion', 'legacy'),
                  rewardMigration=dict(version=version, kept='weights-topology-rng-history',
                                      boundary='new-episode', previousSteps=original.get('steps',0)))
    tuning = dict(result.get('tuning') or {})
    if profile['algorithm'] in ('ppo','ppo_smooth'):
        # About 1.59 s GAE decay at 60 Hz, gamma still has its 40 s scale.
        tuning['gaeLambda']=.99
    result['tuning']=tuning
    return result


def reference_time(world, spec):
    mu=world.surface.grip*world.condition.grip_factor*world.tire.grip_factor
    speed=spec['referenceSpeed']*math.sqrt(max(.1,mu)/.95)
    return max(20.,world.track.length/max(3.,speed))


def driving_risk(episode):
    """Over-demand plus worsening trajectory; normal limit driving is allowed."""
    w=episode.world;u,lateral,yaw,steer=w.state[0,3:7]
    offset,tangent,_=w.coordinates()
    heading=abs((float(tangent[0])-float(w.state[0,2])+math.pi)%(2*math.pi)-math.pi)
    footprint=(w.vehicle.width*abs(math.cos(heading))+w.vehicle.length*abs(math.sin(heading)))/2
    margin=w.track.width/2-abs(float(offset[0]))-footprint
    last=getattr(episode,'risk_margin',margin)
    episode.risk_margin=margin
    alpha=steer-math.atan2(lateral+w.vehicle.cg_front*yaw,max(u,2.))
    mu=w.surface.grip*w.condition.grip_factor*w.tire.grip_factor
    if w.was_offroad[0]:mu*=.45/.95
    normal=min(.85*w.vehicle.mass*9.81,max(.15*w.vehicle.mass*9.81,
        w.vehicle.mass*9.81*(w.vehicle.wheelbase-w.vehicle.cg_front)/w.vehicle.wheelbase
        -w.vehicle.mass*w.acceleration[0,0]*w.vehicle.cg_height/w.vehicle.wheelbase))
    demand=abs(w.vehicle.corner_stiffness*alpha)/max(mu*normal,1.)
    harmful=(u>3 and abs(alpha)>.14 and demand>.9 and
             (margin<last-.001 or heading>.18) and not w.was_offroad[0])
    episode.risk_seconds=(getattr(episode,'risk_seconds',0.)+1/60) if harmful else 0.
    return min(1.,max(0.,demand-.9)) if episode.risk_seconds>=.25 else 0.


def step_terms(e, action, before, old_outside_seconds, old_limits, old_laps, old_totals, events, smooth):
    """Replace legacy reward, reconcile named terms, charge each outcome once."""
    w=e.world;s=e.reward_spec;dt=1/60;ref=reference_time(w,s)
    terms={key:0. for key in TERMS}
    drill=e.phase in ('launch','bend','straight','recovery','follow','overtake','corner','defend','grid') and e.objective=='impara'
    delta_credit=e.valid_progress-before['valid']
    reverse=min(0.,float(w.progress[0])-before['progress'])
    scale=s['drillProgress']/e.spec['distance'] if drill else s['progressPerLap']/w.track.length
    terms['progress']=scale*(delta_credit+reverse)
    pressure=e.pace_pressure if not drill else 0.
    terms['time']=-(s['timeControl']+(s['timePace']-s['timeControl'])*pressure)*dt/ref
    terms['exit']=-s['exit']*max(0,int(w.track_limits[0])-old_limits)
    terms['offroad']=-s['outside']*max(0.,float(w.offroad_seconds[0])-old_outside_seconds)/ref
    laps=int(w.checkpoint[0]//4)-old_laps
    if laps and not drill:
        terms['finish']=s['cleanLap']*sum(row['clean'] for row in w.lap_times[0][-laps:])
    contact_events=[row for row in events if row.get('type')=='contact' and 0 in row.get('cars',[])]
    if w.retired[0]:terms['retirement']=-s['retirement']
    else:
        terms['contact']=-sum(.2+1.8*min(1.,row.get('impactSpeed',0.)/12.) for row in contact_events)
    risk=driving_risk(e)
    terms['understeer']=-s['understeer']*risk*dt/ref
    e.understeer_seconds=getattr(e,'understeer_seconds',0.)+dt*(risk>0)
    if smooth and not risk and not w.retired[0]:
        gap=float(action[0])-float(w.state[0,6])/w.vehicle.max_steer
        terms['control']=-s['smooth']*gap*gap*dt/ref
    terms['task']=s['passReward']*max(0,e.passes-before['passes'])
    if e.reason=='success' and drill:terms['task']+=s['drillSuccess']
    if e.reason=='success' and e.phase=='recovery':terms['recovery']=s['recovery']
    if e.reason=='skill_failed' and not w.retired[0]:terms['task']-=1.
    if e.reason=='no_progress' and not w.retired[0]:terms['stall']=-s['stall']
    for key in TERMS:e.term_totals[key]=old_totals.get(key,0.)+terms[key]
    e.pedal_counts['brake' if action[1]<-.05 else 'gas' if action[1]>.05 else 'coast']+=1
    e.last_reward_terms=terms
    return sum(terms.values())
