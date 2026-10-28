"""Direct neural driving contract. The teacher is never part of inference.

Two actuator commands: normalized steering and signed pedal (positive throttle,
negative brake). Actuator dynamics, tyres and collisions belong to World.
This contract deliberately cannot reinterpret line/pace residual weights.
"""
from copy import deepcopy
import numpy as np
from game_learning import forward, parameters
from game_residual import key, DECISION_STEPS

ACTION = 'direct-steer-pedal-v1'
FEATURES = 'direct-physical-90-v1'
ROAD_FEATURES = 'direct-physical-90-road-v2'


def features(world, index=0,version=FEATURES):
    """Causal telemetry, local road geometry and declared vehicle parameters.

    No teacher commands, target speed, ideal line or absolute track position.
    Road samples are local navigation observations, not steering targets.
    Grip is the simulator's known surface parameter, not an inferred sensor.
    """
    w = world
    i = int(index)
    obs = w.observations(version='race-68-v3')[i].copy()
    obs[64:68] = 0.  # training task labels are not driving sensors
    phase = float(w.coordinates()[2][i])
    if w.track.oval:
        from game_catalog import TRACK
        phase -= TRACK.half_straight
    distances = np.array([4., 8.])
    points = w.track.poses(phase + distances)[:, :2] - w.state[i, :2]
    c, s = np.cos(w.state[i, 2]), np.sin(w.state[i, 2])
    near = np.column_stack(((c*points[:, 0]+s*points[:, 1])/distances,
                            (-s*points[:, 0]+c*points[:, 1])/distances)).ravel()
    v = w.vehicle
    previous = getattr(w, 'direct_previous', np.zeros((w.count, 2)))[i]
    extra = np.r_[near, w.state[i, 3]/60.,
        w.surface.grip*w.condition.grip_factor*w.tire.grip_factor,
        v.mass/1200., v.power/85000., v.drive_force/6500., v.brake_force/10000.,
        v.corner_stiffness/38000., v.wheelbase/2.65, v.cg_front/v.wheelbase,
        v.cg_height/.53, v.yaw_inertia/1700., v.max_steer/.52,
        v.steer_rate/1.8, w.surface.rolling/.015, v.drive_front, v.brake_front,
        previous]
    result = np.r_[obs, extra]
    if version==ROAD_FEATURES:
        # Current road-relative GPS/rival telemetry. No task labels, desired
        # line, teacher action or future opponent state enters these channels.
        result[5]=w.state[i,3]/60.
        slots=(32,64,65,66,67,72);result[list(slots)]=0.
        distance=np.linalg.norm(w.state[:,:2]-w.state[i,:2],axis=1)
        rivals=[j for j in np.argsort(distance,kind='stable') if j!=i and w.active[j] and distance[j]<=150.][:3]
        lateral=-w.coordinates()[0]
        for k,j in enumerate(rivals):
            gap=(w.progress[j]-w.progress[i]+w.track.length/2)%w.track.length-w.track.length/2
            result[slots[2*k]]=gap/80.
            result[slots[2*k+1]]=lateral[j]/(w.track.width/2)
    elif version!=FEATURES:raise ValueError('Contratto sensori diretti sconosciuto')
    if result.shape != (90,) or not np.isfinite(result).all():
        raise ValueError('Telemetria di guida diretta non valida')
    return np.clip(result, -10., 10.)


def controls(world, actions, indices=None):
    """Map network outputs to actuators; no speed/lane/traffic intervention."""
    rows = np.arange(world.count) if indices is None else np.atleast_1d(indices)
    actions = np.atleast_2d(np.asarray(actions, dtype=float))
    if actions.shape != (len(rows), 2) or not np.isfinite(actions).all():
        raise ValueError('Comando diretto non valido')
    actions = np.clip(actions, -1., 1.)
    if not hasattr(world, 'direct_previous'):
        world.direct_previous = np.zeros((world.count, 2))
    if 0 in rows:
        world.direct_control = True
    world.direct_previous[rows] = actions
    return actions.copy()


def snapshot(profile, weights, origin=None):
    from game_direct_trainer import recipe
    from game_neural_mixture import matches,ARCHITECTURE
    return dict(schema=1, kind='direct', algorithm=profile['algorithm'],
        observation='race-68-v3', inputs=68, featureInputs=90,
        action=ACTION, features=FEATURES, hidden=profile['hidden'],
        decisionHz=10, physicsHz=60, teacherAtInference=False, recipe=recipe(profile),
        weights=np.asarray(weights, dtype=float).tolist(), origin=deepcopy(origin),
        architecture=ARCHITECTURE if matches(weights,profile['hidden'],2,90) else 'dense')


class DirectPolicy:
    def __init__(self, data):
        if (data.get('kind') != 'direct' or data.get('action') != ACTION
                or data.get('features') != FEATURES or data.get('featureInputs') != 90
                or data.get('observation') != 'race-68-v3'
                or data.get('decisionHz') != 10 or data.get('physicsHz') != 60
                or data.get('teacherAtInference') is not False):
            raise ValueError('Contratto di guida diretta incompatibile')
        self.data = deepcopy(data)
        self.key = key(data)
        self.hidden = data['hidden']
        self.weights = np.asarray(data['weights'], dtype=float)
        from game_neural_mixture import matches,ARCHITECTURE
        compatible=self.weights.shape==(parameters(90,self.hidden),) if data.get('architecture','dense')=='dense' else data.get('architecture')==ARCHITECTURE and matches(self.weights,self.hidden,2,90)
        if (not compatible
                or not np.isfinite(self.weights).all()):
            raise ValueError('Pesi di guida diretta non validi')

    def commands(self, world, index=None):
        rows = np.arange(world.count) if index is None else np.atleast_1d(index)
        cache = getattr(world, 'direct_cache', {})
        tick = int(round(world.time*60))
        commands = []
        for i in rows:
            old = cache.get(int(i))
            if (old is None or old['key'] != self.key or tick < old['tick']
                    or tick-old['tick'] >= DECISION_STEPS):
                action = np.tanh(forward(self.weights, features(world, i), self.hidden))
                old = dict(key=self.key, tick=tick, action=action.tolist())
                cache[int(i)] = old
            commands.append(old['action'])
        world.direct_cache = cache
        return np.asarray(commands), rows

    def act(self, world, index=None):
        command, rows = self.commands(world, index)
        result = controls(world, command, rows)
        return result[0] if index is not None else result
