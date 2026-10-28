"""Explicit preparation teacher: compare paths, then respect tyre/drive budgets.

Only the offline school and the named Maestro may call this module. Neural
policies receive local observations and directly drive their own actuators.
"""
from dataclasses import asdict
from functools import lru_cache
import json
import math
import numpy as np
from game_geometry import get_track

VERSION='driving-school-1'


@lru_cache(maxsize=96)
def build_plan(track_id,vehicle_json,mu,rolling,lane=0.,apex=0.,utilization=.60):
    v=json.loads(vehicle_json);track=get_track(track_id)
    count=max(128,int(math.ceil(track.length/2.)))
    phase=np.linspace(0,track.length,count,endpoint=False)
    poses=track.poses(phase);offset=np.full(count,lane)
    if track.oval and apex:
        from game_catalog import TRACK
        p=(phase+TRACK.half_straight)%track.length;a=TRACK.half_straight;r=TRACK.radius
        for begin in (2*a,4*a+math.pi*r):
            q=(p-begin)/(math.pi*r);mask=(q>=0)&(q<=1)
            offset[mask]+=apex*np.sin(q[mask]*math.pi)**2
    offset=np.clip(offset,-track.width/2+v['width']/2+1.,track.width/2-v['width']/2-1.)
    points=poses[:,:2]+np.c_[-np.sin(poses[:,2]),np.cos(poses[:,2])]*offset[:,None]
    segments=np.roll(points,-1,axis=0)-points;ds=np.linalg.norm(segments,axis=1)
    heading=np.arctan2(segments[:,1],segments[:,0])
    angle=(heading-np.roll(heading,1)+np.pi)%(2*np.pi)-np.pi
    curvature=angle/np.maximum(.1,(ds+np.roll(ds,1))/2)
    # Smooth the sampled tangent discontinuity without hiding a tight corner.
    curvature=(np.roll(curvature,1)+2*curvature+np.roll(curvature,-1))/4
    limit=np.minimum(45.,np.sqrt(utilization*mu*9.81/np.maximum(abs(curvature),1e-5)))
    speed=limit.copy()
    for _ in range(5):
        for i in range(count-1,-1,-1):
            j=(i+1)%count
            lateral=min(.95,abs(curvature[i])*speed[j]**2/max(.1,mu*9.81))
            brake=min(v['brake_force']/v['mass'],.60*mu*9.81)*math.sqrt(max(.05,1-lateral*lateral))
            speed[i]=min(speed[i],math.sqrt(speed[j]**2+2*brake*ds[i]))
        for i in range(count):
            j=(i+1)%count
            resistance=rolling*v['mass']*9.81+.5*v['air_density']*v['drag_area']*speed[i]**2
            accel=max(.1,(min(v['drive_force'],v['power']/max(3.,speed[i]))-resistance)/v['mass'])
            speed[j]=min(speed[j],math.sqrt(speed[i]**2+2*accel*ds[i]))
    return dict(phase=phase,points=points,curvature=curvature,speed=speed,
                estimatedSeconds=float(np.sum(2*ds/(speed+np.roll(speed,-1)))),
                lane=lane,apex=apex,utilization=utilization)


def plan(world,lane=0.,apex=0.,utilization=.60):
    mu=world.surface.grip*world.condition.grip_factor*world.tire.grip_factor
    return build_plan(world.track.id,json.dumps(asdict(world.vehicle),sort_keys=True),
                      float(mu),world.surface.rolling,float(lane),float(apex),float(utilization))


def actions(world,indices=None,lane=0.,apex=0.,utilization=.60,traffic=True,follow=False):
    rows=np.arange(world.count) if indices is None else np.atleast_1d(indices)
    if traffic and world.shared and world.count>1:
        from game_control import racing_actions
        if not getattr(world,'school_lane_initialized',False):
            world.racing_lane[rows]=-world.coordinates()[0][rows]
            world.school_lane_initialized=True
        phase=getattr(world,'training_phase','')
        if follow:world.training_phase='follow'
        for _ in range(6):racing_actions(world,rows,speed_factor=2.,preferred_offset=lane)
        world.training_phase=phase
        result=[]
        offset=world.coordinates()[0]
        for i in rows:
            command=actions(world,[i],float(world.racing_lane[i]),0.,utilization,False)[0]
            for j in range(world.count):
                gap=world.progress[j]-world.progress[i]
                if world.continuous:gap=(gap+world.track.length/2)%world.track.length-world.track.length/2
                if i!=j and world.active[j] and 0<gap<60 and abs(offset[j]-offset[i])<world.vehicle.width+.8:
                    target=max(0.,world.state[j,3]+.5*(gap-(6.+.4*world.state[i,3])))
                    command[1]=min(command[1],np.clip((target-world.state[i,3])*.4,-1,1))
            result.append(command)
        return np.asarray(result)
    p=plan(world,lane,apex,utilization);w=world;v=w.vehicle
    phase=w.coordinates()[2][rows].copy()
    if w.track.oval:
        from game_catalog import TRACK
        phase-=TRACK.half_straight
    speed=np.maximum(0,w.state[rows,3]);look=np.clip(5.+speed*.30,5.,12.)
    # Periodic interpolation along the selected physical path.
    xp=np.r_[p['phase'],w.track.length]
    def sample(values,s):return np.interp(s%w.track.length,xp,np.r_[values,values[0]])
    target=np.c_[sample(p['points'][:,0],phase+look),sample(p['points'][:,1],phase+look)]
    delta=target-w.state[rows,:2];yaw=w.state[rows,2]
    side=-np.sin(yaw)*delta[:,0]+np.cos(yaw)*delta[:,1]
    k=sample(p['curvature'],phase+look*.5)
    understeer=v.mass*(v.wheelbase-2*v.cg_front)/(v.corner_stiffness*v.wheelbase)
    steer=np.arctan2(2*v.wheelbase*side,np.maximum(1.,np.sum(delta*delta,axis=1)))+understeer*speed**2*k
    target_speed=sample(p['speed'],phase+2.)
    # Feedforward for acceleration/braking from the selected speed envelope.
    ahead=sample(p['speed'],phase+4.)
    acceleration=(ahead**2-target_speed**2)/8.+1.2*(target_speed-speed)
    resistance=w.surface.rolling*v.mass*9.81+.5*v.air_density*v.drag_area*speed**2
    force=v.mass*acceleration+resistance
    pedal=np.where(force>=0,force/np.minimum(v.drive_force,v.power/np.maximum(speed,3)),force/v.brake_force)
    return np.c_[np.clip(steer/v.max_steer,-1,1),np.clip(pedal,-1,1)]
