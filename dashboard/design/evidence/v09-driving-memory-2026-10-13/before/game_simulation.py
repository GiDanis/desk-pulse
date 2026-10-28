"""Deterministic 2D single-track dynamics and shared race worlds, no Qt."""
from __future__ import annotations

import math
import numpy as np

from game_catalog import (TRACK, VEHICLE, SURFACE, CONDITION, TIRE, OBSERVATION_SIZE,
                          PHYSICS_VERSION,RACE_PHYSICS_VERSION,RACE_VEHICLE)
from game_geometry import get_track

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


def ray_distances(states,angles=RAY_ANGLES,max_distance=50.):
    """Analytic intersections of rays with both capsule boundaries."""
    origin = states[:, None, :2]
    angles = states[:, 2, None] + angles
    direction = np.stack((np.cos(angles), np.sin(angles)), axis=-1)
    result = np.full(angles.shape, float(max_distance))
    a = TRACK.half_straight
    for radius in (TRACK.radius - TRACK.road_width/2, TRACK.radius + TRACK.road_width/2):
        for y in (-radius, radius):
            dy = direction[..., 1]
            t = np.divide(y-origin[..., 1], dy, out=np.full_like(dy, 1e6), where=np.abs(dy)>1e-9)
            x = origin[..., 0] + t*direction[..., 0]
            result = np.minimum(result, np.where((t>0) & (np.abs(x)<=a), t, max_distance))
        for center in (-a, a):
            relative = origin - np.array([center, 0.0])
            b = np.sum(relative*direction, axis=-1)
            c = np.sum(relative*relative, axis=-1) - radius*radius
            disc = b*b-c
            root = np.sqrt(np.maximum(disc, 0))
            for t in (-b-root, -b+root):
                hit_x = origin[..., 0] + t*direction[..., 0]
                valid = (disc>=0) & (t>1e-6) & ((hit_x>=a) if center>0 else (hit_x<=-a))
                result = np.minimum(result, np.where(valid, t, max_distance))
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
                 vehicle=VEHICLE, surface=SURFACE, condition=CONDITION, tire=TIRE, track_id='oval-1',physics=PHYSICS_VERSION):
        if not 1 <= count <= 256 or substeps not in (1, 2, 4):
            raise ValueError('Profilo fisico non valido')
        self.count, self.shared, self.laps, self.substeps = count, shared, laps, substeps
        if physics not in (PHYSICS_VERSION,RACE_PHYSICS_VERSION):raise ValueError('Fisica sconosciuta')
        self.physics=physics;self.modern=physics==RACE_PHYSICS_VERSION
        self.vehicle, self.surface, self.condition, self.tire = (RACE_VEHICLE if self.modern and vehicle is VEHICLE else vehicle), surface, condition, tire
        vehicle=self.vehicle
        self.track=get_track(track_id)
        self._edge_fractions = np.linspace(0, 1, int(np.ceil(vehicle.length/0.2))+1)
        self._body_radius = math.hypot(vehicle.length/2, vehicle.width/2)
        self.rng = np.random.default_rng(seed)
        self.reset()

    def reset(self, varied=False):
        if hasattr(self,'_segments'):del self._segments
        self.state = np.zeros((self.count, 7))  # x,y,yaw,u,v,yaw_rate,steer
        self.state[:, 1] = -TRACK.radius
        if self.shared:
            for i in range(self.count):
                self.state[i, 0] = -7 * (i//2)
                self.state[i, 1] += -1.8 if i%2 else 1.8
        elif varied:
            self.state[:, 1] += self.rng.uniform(-0.7, 0.7, self.count)
            self.state[:, 2] = self.rng.uniform(-0.08, 0.08, self.count)
        if not self.track.oval:
            for i in range(self.count):
                self.state[i,:3]=self.track.pose(-(6 if self.modern else 4)*i if self.shared else 0,
                    (-1.8 if i%2 else 1.8) if self.shared else self.rng.uniform(-.7,.7) if varied else 0)
                if varied and not self.shared:self.state[i,2]+=self.rng.uniform(-.08,.08)
        elif self.modern and self.shared:
            for i in range(self.count):self.state[i,:3]=self.track.pose(-6*i,-1.8 if i%2 else 1.8)
        self.time = 0.0
        self.episode_time=np.zeros(self.count)
        self.active = np.ones(self.count, dtype=bool)
        self.retired = np.zeros(self.count, dtype=bool)
        self.finish = np.full(self.count, np.nan)
        self.progress = np.zeros(self.count)
        self.previous_phase = self.coordinates()[2]
        self.progress_origin=self.previous_phase.copy()
        if self.shared and not self.track.oval:
            self.progress=(self.previous_phase+self.track.length/2)%self.track.length-self.track.length/2
        elif self.shared and self.modern:self.progress=-6.*np.arange(self.count)
        self.checkpoint = np.zeros(self.count, dtype=np.int64)
        self.events = []
        self.reward = np.zeros(self.count)
        self.acceleration=np.zeros((self.count,2))
        self.training_context=np.zeros((self.count,4))
        self.racing_lane=np.zeros(self.count)
        self.track_limits=np.zeros(self.count,dtype=int)
        self.offroad_seconds=np.zeros(self.count)
        self.was_offroad=np.zeros(self.count,dtype=bool)
        self.contact_times={}
        self.progress_credit=np.zeros(self.count);self.credit_age=np.zeros(self.count)
        self.training_context[:,3]=1.
        return self.observations()

    def observation_key(self):
        # Public worlds allow direct state edits in fixtures/controllers. Keys
        # include every observed mutable array, so those edits cannot leave a
        # stale cache even when they bypass step/reset/restore.
        return (self.state.tobytes(),self.active.tobytes(),self.acceleration.tobytes(),
                self.training_context.tobytes(),getattr(self,'_segments',np.empty(0)).tobytes())

    def observations(self,active_only=False,version=None):
        from game_catalog import observation_size, OBSERVATION_VERSION
        size=observation_size(version or OBSERVATION_VERSION)
        key=(active_only,self.observation_key()) if size==68 else None
        cached=getattr(self,'_observed_cache',None)
        if key is not None and cached is not None and cached[0]==key:return cached[1].copy()
        x = self.state
        max_distance=150. if size==68 else 50.
        if active_only:
            rays=np.zeros((self.count,5))
            rays[self.active]=(ray_distances(x[self.active],max_distance=max_distance) if self.track.oval else self.track.rays(x[self.active],RAY_ANGLES,max_distance))/max_distance
        else:rays=(ray_distances(x,max_distance=max_distance) if self.track.oval else self.track.rays(x,RAY_ANGLES,max_distance))/max_distance
        offset, tangent, phase = self.coordinates()
        heading = (tangent-x[:, 2]+math.pi) % (2*math.pi)-math.pi
        obs = np.zeros((self.count,size))
        obs[:, :9] = np.column_stack((rays, x[:, 3]/30, x[:, 4]/10,
                                     x[:, 5]/3, x[:, 6]/self.vehicle.max_steer))
        obs[:, 9] = np.clip(offset/(self.track.width/2), -1, 1)
        obs[:, 10] = heading/math.pi
        if self.shared:
            for i in range(self.count):
                relative = x[:, :2]-x[i, :2]
                distances = np.hypot(relative[:, 0], relative[:, 1])
                choices = [j for j in np.argsort(distances, kind='stable') if j!=i and self.active[j] and distances[j]<=(150 if size==68 else 40)][:3]
                c, s = math.cos(x[i, 2]), math.sin(x[i, 2])
                rot = np.array([[c, s], [-s, c]])
                own_vel = np.array([c*x[i, 3]-s*x[i, 4], s*x[i, 3]+c*x[i, 4]])
                for k, j in enumerate(choices):
                    cj, sj = math.cos(x[j, 2]), math.sin(x[j, 2])
                    vel = np.array([cj*x[j, 3]-sj*x[j, 4], sj*x[j, 3]+cj*x[j, 4]])-own_vel
                    angle = x[j, 2]-x[i, 2]
                    body_relative=rot@relative[j]
                    body_velocity=rot@vel
                    obs[i, 11+k*7:18+k*7] = [*(body_relative/(150 if size==68 else 40)), *(body_velocity/30),
                                             math.sin(angle), math.cos(angle), 1]
                    if size==68:
                        longitudinal_half=(self.vehicle.length*(1+abs(math.cos(angle)))+self.vehicle.width*abs(math.sin(angle)))/2
                        lateral_half=(self.vehicle.width*(1+abs(math.cos(angle)))+self.vehicle.length*abs(math.sin(angle)))/2
                        gx=abs(body_relative[0])-longitudinal_half
                        gy=abs(body_relative[1])-lateral_half
                        closing=-math.copysign(1,body_relative[0])*body_velocity[0]
                        risk=max(0.,1-max(gx,0)/max(closing,1e-6)/5) if closing>0 and gy<2 else 0.
                        obs[i,55+3*k:58+3*k]=[math.copysign(max(gx,0),body_relative[0])/150,
                                                             math.copysign(max(gy,0),body_relative[1])/20,risk]
        if size>32:
            obs[:,32]=x[:,3]/60
            obs[:,33]=self.track.width/20
            phase=self.coordinates()[2]
            if self.track.oval:phase=phase-TRACK.half_straight
            c,s=np.cos(x[:,2]),np.sin(x[:,2])
            distances=(15.,40.,80.,150.)
            points=self.track.poses(phase[:,None]+np.asarray(distances)[None,:]) if size==68 else None
            for j,distance in enumerate(distances):
                delta=(points[:,j,:2] if points is not None else self.track.poses(phase+distance)[:,:2])-x[:,:2]
                obs[:,34+j*2]=(c*delta[:,0]+s*delta[:,1])/distance
                obs[:,35+j*2]=(-s*delta[:,0]+c*delta[:,1])/distance
        if size==68:
            side_angles=np.array([-math.pi/2,math.pi/2,-5*math.pi/6,5*math.pi/6])
            obs[:,42:46]=(ray_distances(x,side_angles) if self.track.oval else self.track.rays(x,side_angles))/50
            body=vertices(x,self.vehicle)
            if self.track.oval:
                body_offset=road_distance(body)-TRACK.radius
            else:
                hints=np.repeat(self._segments,4) if hasattr(self,'_segments') else None
                body_offset=self.track.project(body.reshape(-1,2),hints)[0].reshape(self.count,4)
            obs[:,46]=(self.track.width/2-body_offset.max(axis=1))/10
            obs[:,47]=(self.track.width/2+body_offset.min(axis=1))/10
            obs[:,48:50]=self.acceleration/10
            lf=self.vehicle.cg_front if self.modern else self.vehicle.wheelbase/2
            lr=self.vehicle.wheelbase-lf
            obs[:,50]=(x[:,6]-np.arctan2(x[:,4]+lf*x[:,5],np.maximum(x[:,3],2)))/(math.pi/2)
            obs[:,51]=-np.arctan2(x[:,4]-lr*x[:,5],np.maximum(x[:,3],2))/(math.pi/2)
            probes=np.array([[18.,22.],[58.,62.],[118.,122.]])
            curvature_angles=self.track.poses(phase[:,None,None]+probes[None,:,:])[:,:,:,2]
            for k in range(3):
                angles=curvature_angles[:,k,:]
                obs[:,52+k]=((angles[:,1]-angles[:,0]+math.pi)%(2*math.pi)-math.pi)/4*10
            obs[:,64:68]=self.training_context
        if active_only:obs[~self.active]=0
        obs=np.clip(obs,-1,1)
        if key is not None:self._observed_cache=((active_only,self.observation_key()),obs.copy())
        return obs

    def coordinates(self):
        key=(self.state[:,:2].tobytes(),getattr(self,'_segments',np.empty(0)).tobytes()) if self.modern else None
        cached=getattr(self,'_coordinate_cache',None)
        if key is not None and cached is not None and cached[0]==key:return tuple(x.copy() for x in cached[1])
        if self.track.oval:result=track_coordinates(self.state[:,0],self.state[:,1])
        else:
            offset,tangent,phase,self._segments=self.track.project(self.state[:,:2],getattr(self,'_segments',None))
            result=offset,tangent,phase
        if key is not None:
            final=(self.state[:,:2].tobytes(),getattr(self,'_segments',np.empty(0)).tobytes())
            # Hinted projections can settle after a direct fixture teleport.
            # Cache only once its selected segment is stable.
            if key==final:self._coordinate_cache=(key,tuple(x.copy() for x in result))
        return result

    def perturb(self,index,offset,heading):
        tangent=self.coordinates()[1][index]
        self.state[index,0]-=math.sin(tangent)*offset
        self.state[index,1]+=math.cos(tangent)*offset
        self.state[index,2]+=heading
        self.previous_phase[index]=self.coordinates()[2][index]

    def snapshot(self):
        return {'schema':1,'count':self.count,'shared':self.shared,'laps':self.laps,
                'substeps':self.substeps,'time':self.time,'rng':self.rng.bit_generator.state,
                'trackId':self.track.id,'episodeTime':self.episode_time.tolist(),
                'state':self.state.tolist(),'active':self.active.tolist(),
                'retired':self.retired.tolist(),'finish':[float(x) if np.isfinite(x) else None for x in self.finish],
                'progress':self.progress.tolist(),'previousPhase':self.previous_phase.tolist(),
                'checkpoint':self.checkpoint.tolist(),'events':self.events,
                'acceleration':self.acceleration.tolist(),'trainingContext':self.training_context.tolist(),
                'racingLane':self.racing_lane.tolist(),'physics':self.physics,
                'trackLimits':self.track_limits.tolist(),'offroadSeconds':self.offroad_seconds.tolist(),
                'wasOffroad':self.was_offroad.tolist(),'contactTimes':self.contact_times.copy(),
                'progressCredit':self.progress_credit.tolist(),'creditAge':self.credit_age.tolist()}

    def restore(self, data):
        if data['schema']!=1 or (data['count'],data['shared'],data['laps'],data['substeps'])!=(self.count,self.shared,self.laps,self.substeps):
            raise ValueError('Mondo salvato incompatibile')
        if data.get('trackId','oval-1')!=self.track.id:raise ValueError('Circuito salvato incompatibile')
        if data.get('physics',PHYSICS_VERSION)!=self.physics:raise ValueError('Fisica salvata incompatibile')
        self.time=data['time']
        self.episode_time=np.asarray(data.get('episodeTime',[self.time]*self.count),dtype=float)
        if self.episode_time.shape!=(self.count,) or not np.isfinite(self.episode_time).all() or (self.episode_time<0).any():
            raise ValueError('Tempo degli episodi non valido')
        self.rng.bit_generator.state=data['rng']
        self.state=np.asarray(data['state'],dtype=float)
        self.active=np.asarray(data['active'],dtype=bool)
        self.retired=np.asarray(data['retired'],dtype=bool)
        self.finish=np.array([np.nan if x is None else x for x in data['finish']])
        self.progress=np.asarray(data['progress'],dtype=float)
        self.previous_phase=np.asarray(data['previousPhase'],dtype=float)
        self.checkpoint=np.asarray(data['checkpoint'],dtype=np.int64)
        self.events=data['events']
        self.acceleration=np.asarray(data.get('acceleration',np.zeros((self.count,2))),dtype=float)
        self.training_context=np.asarray(data.get('trainingContext',np.zeros((self.count,4))),dtype=float)
        self.racing_lane=np.asarray(data.get('racingLane',np.zeros(self.count)),dtype=float)
        self.track_limits=np.asarray(data.get('trackLimits',np.zeros(self.count)),dtype=int)
        self.offroad_seconds=np.asarray(data.get('offroadSeconds',np.zeros(self.count)),dtype=float)
        self.was_offroad=np.asarray(data.get('wasOffroad',np.zeros(self.count)),dtype=bool)
        self.contact_times=data.get('contactTimes',{}).copy()
        self.progress_credit=np.asarray(data.get('progressCredit',np.zeros(self.count)),dtype=float)
        self.credit_age=np.asarray(data.get('creditAge',np.zeros(self.count)),dtype=float)
        for name,shape in (('acceleration',(self.count,2)),('training_context',(self.count,4)),
                ('racing_lane',(self.count,)),('track_limits',(self.count,)),('offroad_seconds',(self.count,)),
                ('was_offroad',(self.count,)),('progress_credit',(self.count,)),('credit_age',(self.count,)),
                ('active',(self.count,)),('retired',(self.count,)),('progress',(self.count,)),
                ('previous_phase',(self.count,)),('checkpoint',(self.count,))):
            value=getattr(self,name)
            if value.shape!=shape or not np.isfinite(value).all():raise ValueError('Stato salvato non valido: '+name)
        if self.state.shape!=(self.count,7) or not np.isfinite(self.state).all():
            raise ValueError('Stato salvato non valido')
        if not self.track.oval:self._segments=self.track.project(self.state[:,:2])[3]

    def reset_trials(self, mask):
        """Reset only completed independent PPO episodes, preserving other trials."""
        if self.shared:
            raise ValueError('Reset parziale vietato in Gara')
        mask=np.asarray(mask,dtype=bool)
        self.state[mask]=0
        self.state[mask,1]=-TRACK.radius+self.rng.uniform(-0.7,0.7,int(mask.sum()))
        self.state[mask,2]=self.rng.uniform(-0.08,0.08,int(mask.sum()))
        if not self.track.oval:
            for i in np.flatnonzero(mask):
                self.state[i,:3]=self.track.pose(0,self.rng.uniform(-.7,.7))
                self.state[i,2]+=self.rng.uniform(-.08,.08)
            self._segments=self.track.project(self.state[:,:2])[3]
        self.episode_time[mask]=0
        self.active[mask]=True
        self.retired[mask]=False
        self.finish[mask]=np.nan
        self.progress[mask]=0
        self.previous_phase[mask]=self.coordinates()[2][mask]
        self.checkpoint[mask]=0
        self.acceleration[mask]=0;self.training_context[mask]=0
        self.racing_lane[mask]=0
        self.track_limits[mask]=0;self.offroad_seconds[mask]=0;self.was_offroad[mask]=False
        self.progress_credit[mask]=0;self.credit_age[mask]=0;self.training_context[mask,3]=1

    def step(self, actions, pace=0.0, *, return_observations=True, control_cost=0.0):
        """Advance physics; skip next sensors when the caller does not use them."""
        actions = np.asarray(actions, dtype=float)
        if actions.shape != (self.count, 2) or not np.isfinite(actions).all():
            raise ValueError('Azioni non valide')
        actions = np.clip(actions, -1, 1)
        velocity_before=self.state[:,3:5].copy()
        yaw_before=self.state[:,5].copy()
        command_gap=(actions[:,0]-self.state[:,6]/self.vehicle.max_steer)**2
        reward = np.zeros(self.count)
        terms={key:np.zeros(self.count) for key in ('progress','time','contact','offroad','finish','control')}
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
            old_position=x[:,:2].copy()
            old_corners=vertices(x,v) if not self.track.oval else None
            x[:, 6] += np.clip(actions[:, 0]*v.max_steer-x[:, 6], -v.steer_rate*h, v.steer_rate*h)*alive
            u, lateral, yaw = x[:, 3].copy(), x[:, 4].copy(), x[:, 5].copy()
            if self.modern:
                mu=self.surface.grip*self.condition.grip_factor*self.tire.grip_factor*np.where(self.was_offroad,.45/.95,1.)
                lf=v.cg_front;lr=v.wheelbase-lf
                nf=np.clip(v.mass*9.81*lr/v.wheelbase-v.mass*self.acceleration[:,0]*v.cg_height/v.wheelbase,
                           .15*v.mass*9.81,.85*v.mass*9.81)
                nr=v.mass*9.81-nf
                drive=np.minimum(v.drive_force,v.power/np.maximum(np.abs(u),3))
                demand=np.where(actions[:,1]>=0,actions[:,1]*drive,actions[:,1]*v.brake_force)
                share=np.where(actions[:,1]>=0,v.drive_front,v.brake_front)
                fx_front=np.clip(demand*share,-mu*nf,mu*nf)
                fx_rear=np.clip(demand*(1-share),-mu*nr,mu*nr)
                budget_front=np.sqrt(np.maximum((mu*nf)**2-fx_front**2,0))
                budget_rear=np.sqrt(np.maximum((mu*nr)**2-fx_rear**2,0))
                alpha_front=x[:,6]-np.arctan2(lateral+lf*yaw,np.maximum(u,2))
                alpha_rear=-np.arctan2(lateral-lr*yaw,np.maximum(u,2))
                front=budget_front*np.tanh(v.corner_stiffness*alpha_front/np.maximum(budget_front,1e-6))
                rear=budget_rear*np.tanh(v.corner_stiffness*alpha_rear/np.maximum(budget_rear,1e-6))
                resistance=np.where(self.was_offroad,.045,self.surface.rolling)*v.mass*9.81*np.tanh(u*3)
                resistance+=.5*v.air_density*v.drag_area*u*np.abs(u)
                du=(fx_front*np.cos(x[:,6])+fx_rear-front*np.sin(x[:,6])-resistance)/v.mass+lateral*yaw
                dv=(front*np.cos(x[:,6])+rear+fx_front*np.sin(x[:,6]))/v.mass-u*yaw
                dr=(lf*(front*np.cos(x[:,6])+fx_front*np.sin(x[:,6]))-lr*rear)/v.yaw_inertia
            else:
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
            self.episode_time+=h*alive
            corners = vertices(x, v)
            # The inner capsule is concave from the road's perspective: corners
            # alone miss an edge cutting through the grass. Sample each edge at
            # 0.2 m as well as the vertices, conservatively including contact.
            # Distance to the capsule's central segment is 1-Lipschitz. A
            # bounding circle wholly inside the road cannot touch either edge.
            # Keep the original detailed samples for every uncertain body.
            distance = road_distance(x[:, :2]) if self.track.oval else np.abs(self.coordinates()[0])
            inner, outer = TRACK.radius-TRACK.road_width/2, TRACK.radius+TRACK.road_width/2
            uncertain = alive & (((distance-self._body_radius <= inner+1e-9) |
                                 (distance+self._body_radius >= outer-1e-9)) if self.track.oval else
                                 distance+self._body_radius>=self.track.width/2-.1)
            hit = np.zeros(self.count, dtype=bool)
            if uncertain.any():
                body = corners[uncertain]
                edge_points = body[:, :, None, :] + (np.roll(body,-1,axis=1)-body)[:, :, None, :]*self._edge_fractions[None,None,:,None]
                if self.track.oval:
                    road = road_distance(edge_points).reshape(len(body),-1)
                    hit[uncertain] = ((road < inner) | (road > outer)).any(axis=1)
                else:
                    for index in np.flatnonzero(uncertain):
                        hit[index]=self.track.swept_contact(old_corners[index],corners[index])
            offroad=hit.copy() if self.modern else np.zeros(self.count,dtype=bool)
            if self.modern:
                entered=offroad & ~self.was_offroad & alive
                self.track_limits+=entered
                self.offroad_seconds+=h*offroad*alive
                for index in np.flatnonzero(entered):self.events.append({'type':'track_limit','time':self.time,'cars':[int(index)]})
                self.was_offroad=offroad
                edge_distance=np.abs(distance-TRACK.radius) if self.track.oval else distance
                hit=alive & (edge_distance>self.track.width/2+6.)
                terms['offroad']-=h*offroad*alive*.2
                reward-=h*offroad*alive*.2
            if self.shared:
                for i in range(self.count):
                    for j in range(i+1, self.count):
                        if alive[i] and alive[j] and overlap(corners[i], corners[j]):
                            if self.modern:
                                from game_contacts import resolve
                                impact=resolve(x,i,j,corners[i],corners[j],v)
                                key=str(i)+':'+str(j)
                                if self.time-self.contact_times.get(key,-1)>.5:
                                    self.contact_times[key]=self.time
                                    self.events.append({'type':'contact','time':self.time,'cars':[i,j],**impact})
                                    reward[[i,j]]-=.05+.15*min(impact['impactSpeed'],12)
                                    terms['contact'][[i,j]]-=.05+.15*min(impact['impactSpeed'],12)
                                if impact['impactSpeed']>=12:hit[i]=hit[j]=True
                                corners[[i,j]]=vertices(x[[i,j]],v)
                            else:
                                hit[i] = hit[j] = True
                                self.events.append({'type':'contact', 'time':self.time, 'cars':[i,j]})
            _, _, phase = self.coordinates()
            length=self.track.length
            delta = (phase-self.previous_phase+length/2) % length-length/2
            if not self.track.oval:
                plausible=np.linalg.norm(x[:,:2]-old_position,axis=1)*(3 if self.modern else 2)+(v.length*.5 if self.modern else .1)
                hit |= alive & (np.abs(delta)>plausible)
            delta = np.where(alive & ~hit, delta, 0)
            self.progress += delta
            self.previous_phase = phase
            # A quarter-lap gate is credited only on a forward sequential crossing.
            next_gate = (self.checkpoint+1)*length/4
            cross = alive & ~hit & (previous < next_gate) & (self.progress >= next_gate)
            if not self.track.oval:
                physical_cross,gate_fraction=self.track.gate_crossings(old_position,x[:,:2],self.checkpoint)
                cross=alive & ~hit & physical_cross & (np.abs(self.progress-next_gate)<2)
            if self.modern:cross &= ~offroad
            self.checkpoint[cross] += 1
            finished = cross & (self.checkpoint>=4*self.laps)
            fraction = np.divide(self.laps*length-previous, delta,
                                 out=np.ones(self.count), where=delta>0)
            if not self.track.oval:fraction=gate_fraction
            self.finish[finished] = old_time + h*np.clip(fraction[finished], 0, 1)
            self.retired |= hit
            self.active &= ~(hit | finished)
            # Pace changes the training objective, never the vehicle physics.
            # The finish-time bonus is bounded and only paid for a valid lap.
            progress_reward=np.where(offroad,0,delta)/10
            finish_reward=finished*(10+pace*5*np.clip(1-self.episode_time/max(60.,self.track.length/7.*self.laps),0,1))
            if self.modern:finish_reward*=self.track_limits==0
            time_reward=alive*(-h)*(0.02+0.28*pace)
            control_reward=alive*(-h)*(np.abs(actions[:,0])*.005+control_cost*command_gap)
            # Keep legacy addition order unchanged for exact replay compatibility.
            reward+=progress_reward+finished*10-hit*5+time_reward
            reward+=finished*pace*5*np.clip(1-self.episode_time/max(60.,self.track.length/7.*self.laps),0,1)
            reward-=alive*np.abs(actions[:,0])*h*.005
            reward-=alive*h*control_cost*command_gap
            if self.modern:reward-=finished*(self.track_limits>0)*(10+pace*5*np.clip(1-self.episode_time/max(60.,self.track.length/7.*self.laps),0,1))
            for key,value in (('progress',progress_reward),('finish',finish_reward),('contact',hit*(-5)),('time',time_reward),('control',control_reward)):terms[key]+=value
            x[~self.active, 3:6] = 0
        self.reward = reward
        self.reward_terms=terms
        self.acceleration=(self.state[:,3:5]-velocity_before)/DT
        if self.modern:
            mean_velocity=(self.state[:,3:5]+velocity_before)/2
            mean_yaw=(self.state[:,5]+yaw_before)/2
            self.acceleration[:,0]-=mean_velocity[:,1]*mean_yaw
            self.acceleration[:,1]+=mean_velocity[:,0]*mean_yaw
        advanced=self.progress>=self.progress_credit+1
        self.progress_credit[advanced]=self.progress[advanced]
        self.credit_age[advanced]=self.episode_time[advanced]
        self.training_context[:,0]=np.clip(self.episode_time/2,0,1)
        self.training_context[:,1]=np.clip((self.episode_time-self.credit_age)/15,0,1)
        self.training_context[:,2]=np.clip(self.progress-self.progress_credit,0,1)
        if not np.isfinite(self.state).all():
            raise RuntimeError('Dinamica non finita')
        return self.observations() if return_observations else None, reward, ~self.active

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
                 'vehicleLength':self.vehicle.length,'vehicleWidth':self.vehicle.width,
                 'trackLimits':int(self.track_limits[i]),'offroadSeconds':float(self.offroad_seconds[i]),
                 'physics':self.physics,
                 'ghost':bool(self.retired[i]),
                 'finishTime':float(self.finish[i]) if np.isfinite(self.finish[i]) else None,
                 'status':'arrivato' if np.isfinite(self.finish[i]) else 'ritirato' if self.retired[i] else 'in corsa'}
                for i in range(self.count)]


def reference_actions(world, observations=None):
    """Geometry controller for physics qualification only; never a learned pilot."""
    obs = world.observations() if observations is None else observations
    if world.track.oval:
        return np.column_stack((np.clip(obs[:, 10]*2.6+obs[:, 9]*0.7, -1, 1),
                                np.clip((10-world.state[:, 3])*0.3, -1, 1)))
    action=[]
    for i in range(world.count):
        # Pure pursuit is only a diagnostic controller, never learner actions.
        phase=world.coordinates()[2][i];look=max(4.,world.state[i,3]*.7)
        target=world.track.pose(phase+look);relative=target[:2]-world.state[i,:2]
        yaw=world.state[i,2];side=-math.sin(yaw)*relative[0]+math.cos(yaw)*relative[1]
        steer=math.atan2(2*world.vehicle.wheelbase*side,max(1.,float(relative@relative)))/world.vehicle.max_steer
        action.append([np.clip(steer,-1,1),np.clip((7-world.state[i,3])*.3,-1,1)])
    return np.array(action)
