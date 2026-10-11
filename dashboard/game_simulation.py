"""Deterministic 2D single-track dynamics and shared race worlds, no Qt."""
from __future__ import annotations

import math
import numpy as np

from game_catalog import TRACK, VEHICLE, SURFACE, CONDITION, TIRE, OBSERVATION_SIZE

DT = 1 / 60
LAP_LENGTH = 4 * TRACK.half_straight + 2 * math.pi * TRACK.radius
RAY_ANGLES = np.array([-1.2, -0.6, 0.0, 0.6, 1.2])


def track_coordinates(x, y):
    """Signed offset, tangent and progress on a counterclockwise capsule."""
    a, r = TRACK.half_straight, TRACK.radius
    cx = np.clip(x, -a, a)
    distance = np.hypot(x - cx, y)
    angle = np.arctan2(y, x - cx)
    tangent = angle + math.pi / 2
    # Progress origin is the lower-left tangent; no nearest-traguardo shortcut.
    lower = (x >= -a) & (x <= a) & (y < 0)
    upper = (x >= -a) & (x <= a) & (y >= 0)
    right = x > a
    phase = np.where(lower, x + a,
             np.where(right, 2*a + r * (angle + math.pi/2),
             np.where(upper, 2*a + math.pi*r + a-x,
                      4*a + math.pi*r + r * ((angle-math.pi/2) % (2*math.pi)))))
    return distance-r, tangent, phase % LAP_LENGTH


def road_distance(points):
    return np.hypot(points[..., 0] - np.clip(points[..., 0], -TRACK.half_straight,
                                           TRACK.half_straight), points[..., 1])


def ray_distances(states):
    """Analytic intersections of rays with both capsule boundaries."""
    origin = states[:, None, :2]
    angles = states[:, 2, None] + RAY_ANGLES
    direction = np.stack((np.cos(angles), np.sin(angles)), axis=-1)
    result = np.full(angles.shape, 50.0)
    a = TRACK.half_straight
    for radius in (TRACK.radius - TRACK.road_width/2, TRACK.radius + TRACK.road_width/2):
        for y in (-radius, radius):
            dy = direction[..., 1]
            t = np.divide(y-origin[..., 1], dy, out=np.full_like(dy, 1e6), where=np.abs(dy)>1e-9)
            x = origin[..., 0] + t*direction[..., 0]
            result = np.minimum(result, np.where((t>0) & (np.abs(x)<=a), t, 50))
        for center in (-a, a):
            relative = origin - np.array([center, 0.0])
            b = np.sum(relative*direction, axis=-1)
            c = np.sum(relative*relative, axis=-1) - radius*radius
            disc = b*b-c
            root = np.sqrt(np.maximum(disc, 0))
            for t in (-b-root, -b+root):
                hit_x = origin[..., 0] + t*direction[..., 0]
                valid = (disc>=0) & (t>1e-6) & ((hit_x>=a) if center>0 else (hit_x<=-a))
                result = np.minimum(result, np.where(valid, t, 50))
    return result


def vertices(states, vehicle=VEHICLE):
    local = np.array([[1, 1], [1, -1], [-1, -1], [-1, 1]]) * [vehicle.length/2, vehicle.width/2]
    c, s = np.cos(states[:, 2]), np.sin(states[:, 2])
    rotation = np.stack((c, -s, s, c), axis=1).reshape(-1, 2, 2)
    return np.einsum('nij,kj->nki', rotation, local) + states[:, None, :2]


def overlap(a, b):
    """Separating-axis test for oriented convex rectangles."""
    for poly in (a, b):
        for i in (0, 1):
            edge = poly[i+1]-poly[i]
            axis = np.array([-edge[1], edge[0]])
            pa, pb = a @ axis, b @ axis
            if pa.max() < pb.min() or pb.max() < pa.min():
                return False
    return True


class World:
    """N independent trials, or N interacting participants in one race."""
    def __init__(self, count=1, seed=1, shared=False, laps=1, substeps=2,
                 vehicle=VEHICLE, surface=SURFACE, condition=CONDITION, tire=TIRE):
        if not 1 <= count <= 256 or substeps not in (1, 2, 4):
            raise ValueError('Profilo fisico non valido')
        self.count, self.shared, self.laps, self.substeps = count, shared, laps, substeps
        self.vehicle, self.surface, self.condition, self.tire = vehicle, surface, condition, tire
        self.rng = np.random.default_rng(seed)
        self.reset()

    def reset(self, varied=False):
        self.state = np.zeros((self.count, 7))  # x,y,yaw,u,v,yaw_rate,steer
        self.state[:, 1] = -TRACK.radius
        if self.shared:
            for i in range(self.count):
                self.state[i, 0] = -7 * (i//2)
                self.state[i, 1] += -1.8 if i%2 else 1.8
        elif varied:
            self.state[:, 1] += self.rng.uniform(-0.7, 0.7, self.count)
            self.state[:, 2] = self.rng.uniform(-0.08, 0.08, self.count)
        self.time = 0.0
        self.active = np.ones(self.count, dtype=bool)
        self.retired = np.zeros(self.count, dtype=bool)
        self.finish = np.full(self.count, np.nan)
        self.progress = np.zeros(self.count)
        self.previous_phase = track_coordinates(self.state[:, 0], self.state[:, 1])[2]
        self.checkpoint = np.zeros(self.count, dtype=np.int64)
        self.events = []
        self.reward = np.zeros(self.count)
        return self.observations()

    def observations(self):
        x = self.state
        rays = ray_distances(x) / 50
        offset, tangent, _ = track_coordinates(x[:, 0], x[:, 1])
        heading = (tangent-x[:, 2]+math.pi) % (2*math.pi)-math.pi
        obs = np.zeros((self.count, OBSERVATION_SIZE))
        obs[:, :9] = np.column_stack((rays, x[:, 3]/30, x[:, 4]/10,
                                     x[:, 5]/3, x[:, 6]/self.vehicle.max_steer))
        obs[:, 9] = np.clip(offset/5, -1, 1)
        obs[:, 10] = heading/math.pi
        if self.shared:
            for i in range(self.count):
                relative = x[:, :2]-x[i, :2]
                distances = np.hypot(relative[:, 0], relative[:, 1])
                choices = [j for j in np.argsort(distances, kind='stable') if j!=i and self.active[j] and distances[j]<=40][:3]
                c, s = math.cos(x[i, 2]), math.sin(x[i, 2])
                rot = np.array([[c, s], [-s, c]])
                own_vel = np.array([c*x[i, 3]-s*x[i, 4], s*x[i, 3]+c*x[i, 4]])
                for k, j in enumerate(choices):
                    cj, sj = math.cos(x[j, 2]), math.sin(x[j, 2])
                    vel = np.array([cj*x[j, 3]-sj*x[j, 4], sj*x[j, 3]+cj*x[j, 4]])-own_vel
                    angle = x[j, 2]-x[i, 2]
                    obs[i, 11+k*7:18+k*7] = [*(rot@relative[j]/40), *(rot@vel/30),
                                             math.sin(angle), math.cos(angle), 1]
        return np.clip(obs, -1, 1)

    def snapshot(self):
        return {'schema':1,'count':self.count,'shared':self.shared,'laps':self.laps,
                'substeps':self.substeps,'time':self.time,'rng':self.rng.bit_generator.state,
                'state':self.state.tolist(),'active':self.active.tolist(),
                'retired':self.retired.tolist(),'finish':[float(x) if np.isfinite(x) else None for x in self.finish],
                'progress':self.progress.tolist(),'previousPhase':self.previous_phase.tolist(),
                'checkpoint':self.checkpoint.tolist(),'events':self.events}

    def restore(self, data):
        if data['schema']!=1 or (data['count'],data['shared'],data['laps'],data['substeps'])!=(self.count,self.shared,self.laps,self.substeps):
            raise ValueError('Mondo salvato incompatibile')
        self.time=data['time']
        self.rng.bit_generator.state=data['rng']
        self.state=np.asarray(data['state'],dtype=float)
        self.active=np.asarray(data['active'],dtype=bool)
        self.retired=np.asarray(data['retired'],dtype=bool)
        self.finish=np.array([np.nan if x is None else x for x in data['finish']])
        self.progress=np.asarray(data['progress'],dtype=float)
        self.previous_phase=np.asarray(data['previousPhase'],dtype=float)
        self.checkpoint=np.asarray(data['checkpoint'],dtype=np.int64)
        self.events=data['events']
        if self.state.shape!=(self.count,7) or not np.isfinite(self.state).all():
            raise ValueError('Stato salvato non valido')

    def reset_trials(self, mask):
        """Reset only completed independent PPO episodes, preserving other trials."""
        if self.shared:
            raise ValueError('Reset parziale vietato in Gara')
        mask=np.asarray(mask,dtype=bool)
        self.state[mask]=0
        self.state[mask,1]=-TRACK.radius+self.rng.uniform(-0.7,0.7,int(mask.sum()))
        self.state[mask,2]=self.rng.uniform(-0.08,0.08,int(mask.sum()))
        self.active[mask]=True
        self.retired[mask]=False
        self.finish[mask]=np.nan
        self.progress[mask]=0
        self.previous_phase[mask]=track_coordinates(self.state[mask,0],self.state[mask,1])[2]
        self.checkpoint[mask]=0

    def step(self, actions, pace=0.0):
        actions = np.asarray(actions, dtype=float)
        if actions.shape != (self.count, 2) or not np.isfinite(actions).all():
            raise ValueError('Azioni non valide')
        actions = np.clip(actions, -1, 1)
        reward = np.zeros(self.count)
        # Bound motion between contact samples, including opposing cars. This
        # prevents a fast car from crossing another between the nominal ticks.
        speed = np.hypot(self.state[:, 3], self.state[:, 4])
        samples = max(self.substeps, int(np.ceil(float(speed.max())*DT/0.25)),
                      int(np.ceil(float(np.abs(self.state[:, 5]).max())*DT/0.025)))
        if samples > 512:
            raise ValueError('Velocità fuori dal dominio della simulazione')
        for _ in range(samples):
            h = DT/samples
            v = self.vehicle
            x = self.state
            alive = self.active.copy()
            previous = self.progress.copy()
            old_time = self.time
            x[:, 6] += np.clip(actions[:, 0]*v.max_steer-x[:, 6], -v.steer_rate*h, v.steer_rate*h)*alive
            u, lateral, yaw = x[:, 3].copy(), x[:, 4].copy(), x[:, 5].copy()
            mu = self.surface.grip*self.condition.grip_factor*self.tire.grip_factor
            normal = v.mass*9.81/2
            drive = np.minimum(v.drive_force, v.power/np.maximum(np.abs(u), 3))
            fx = np.where(actions[:, 1]>=0, actions[:, 1]*drive, actions[:, 1]*v.brake_force)
            fx -= self.surface.rolling*v.mass*9.81*np.tanh(u*3)+0.4*u*np.abs(u)
            lf = lr = v.wheelbase/2
            front = v.corner_stiffness*(x[:, 6]-np.arctan2(lateral+lf*yaw, np.maximum(u, 2)))
            rear = v.corner_stiffness*(-np.arctan2(lateral-lr*yaw, np.maximum(u, 2)))
            combined = np.sqrt(np.maximum((mu*normal)**2-(fx/2)**2, 0))
            fx = np.clip(fx, -2*mu*normal, 2*mu*normal)
            front, rear = np.clip(front, -combined, combined), np.clip(rear, -combined, combined)
            du = (fx-front*np.sin(x[:, 6]))/v.mass + lateral*yaw
            dv = (front*np.cos(x[:, 6])+rear)/v.mass - u*yaw
            dr = (lf*front*np.cos(x[:, 6])-lr*rear)/v.yaw_inertia
            x[:, 3] = np.maximum(0, u+h*du*alive)
            dynamic_v = lateral+h*dv
            dynamic_r = yaw+h*dr
            # Continuous low-speed blend avoids singular tyre slip at standstill.
            blend = np.clip((u-1)/2, 0, 1)
            kinetic_r = x[:, 3]*np.tan(x[:, 6])/v.wheelbase
            x[:, 4] = np.where(alive, blend*dynamic_v, lateral)
            x[:, 5] = np.where(alive, blend*dynamic_r+(1-blend)*kinetic_r, yaw)
            x[:, 2] += h*x[:, 5]*alive
            c, s = np.cos(x[:, 2]), np.sin(x[:, 2])
            x[:, 0] += h*(c*x[:, 3]-s*x[:, 4])*alive
            x[:, 1] += h*(s*x[:, 3]+c*x[:, 4])*alive
            self.time += h
            corners = vertices(x, v)
            # The inner capsule is concave from the road's perspective: corners
            # alone miss an edge cutting through the grass. Sample each edge at
            # 0.2 m as well as the vertices, conservatively including contact.
            fractions = np.linspace(0, 1, int(np.ceil(v.length/0.2))+1)
            edge_points = corners[:, :, None, :] + (np.roll(corners,-1,axis=1)-corners)[:, :, None, :]*fractions[None,None,:,None]
            road = road_distance(edge_points).reshape(self.count,-1)
            hit = ((road < TRACK.radius-TRACK.road_width/2) | (road > TRACK.radius+TRACK.road_width/2)).any(axis=1) & alive
            if self.shared:
                for i in range(self.count):
                    for j in range(i+1, self.count):
                        if alive[i] and alive[j] and overlap(corners[i], corners[j]):
                            hit[i] = hit[j] = True
                            self.events.append({'type':'contact', 'time':self.time, 'cars':[i,j]})
            _, _, phase = track_coordinates(x[:, 0], x[:, 1])
            delta = (phase-self.previous_phase+LAP_LENGTH/2) % LAP_LENGTH-LAP_LENGTH/2
            delta = np.where(alive & ~hit, delta, 0)
            self.progress += delta
            self.previous_phase = phase
            # A quarter-lap gate is credited only on a forward sequential crossing.
            next_gate = (self.checkpoint+1)*LAP_LENGTH/4
            cross = alive & ~hit & (previous < next_gate) & (self.progress >= next_gate)
            self.checkpoint[cross] += 1
            finished = cross & (self.checkpoint>=4*self.laps)
            fraction = np.divide(self.laps*LAP_LENGTH-previous, delta,
                                 out=np.ones(self.count), where=delta>0)
            self.finish[finished] = old_time + h*np.clip(fraction[finished], 0, 1)
            self.retired |= hit
            self.active &= ~(hit | finished)
            # Pace changes the training objective, never the vehicle physics.
            # The finish-time bonus is bounded and only paid for a valid lap.
            reward += delta/10 + finished*10 - hit*5 - alive*h*(0.02+0.28*pace)
            reward += finished*pace*5*np.clip(1-(old_time+h)/60,0,1)
            reward -= alive*np.abs(actions[:, 0])*h*0.005
            x[~self.active, 3:6] = 0
        self.reward = reward
        if not np.isfinite(self.state).all():
            raise RuntimeError('Dinamica non finita')
        return self.observations(), reward, ~self.active

    def rows(self, ids=None):
        ids = ids or [str(i) for i in range(self.count)]
        keys = [(0, round(float(self.finish[i]),6)) if np.isfinite(self.finish[i]) else (1, -round(float(self.progress[i]),6)) for i in range(self.count)]
        rank = sorted(range(self.count), key=lambda i: keys[i])
        positions={};previous=None
        for place,i in enumerate(rank):
            if keys[i]!=previous:position=place+1
            positions[i]=position;previous=keys[i]
        return [{'id':ids[i], 'position':positions[i], 'x':float(self.state[i, 0]),
                 'y':float(self.state[i, 1]), 'yaw':float(self.state[i, 2]),
                 'speed':float(self.state[i, 3]), 'lap':int(self.checkpoint[i]//4),
                 'progress':float(self.progress[i]),
                 'finishTime':float(self.finish[i]) if np.isfinite(self.finish[i]) else None,
                 'status':'arrivato' if np.isfinite(self.finish[i]) else 'ritirato' if self.retired[i] else 'in corsa'}
                for i in range(self.count)]


def reference_actions(world):
    """Geometry controller for physics qualification only; never a learned pilot."""
    obs = world.observations()
    return np.column_stack((np.clip(obs[:, 10]*2.6+obs[:, 9]*0.7, -1, 1),
                            np.clip((10-world.state[:, 3])*0.3, -1, 1)))
