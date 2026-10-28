"""Explicit geometric teacher: lookahead steering and curvature speed budget."""
import numpy as np


def pursuit_actions(world, indices=None, speed_factor=1., lateral_targets=None):
    rows = np.arange(world.count) if indices is None else np.atleast_1d(indices)
    state = world.state[rows]
    phase = world.coordinates()[2][rows]
    if world.track.oval:
        from game_catalog import TRACK
        phase=phase-TRACK.half_straight
    speed = np.maximum(0, state[:,3])
    look=np.clip(3. + speed*.35, 4., 12.)
    if getattr(world,'modern',False):
        probe=world.track.poses(phase[:,None]+np.array([0.,10.])[None,:])[:,:,2]
        nearby=np.abs((probe[:,1]-probe[:,0]+np.pi)%(2*np.pi)-np.pi)/10.
        look=np.minimum(look,np.maximum(3.,.35/np.maximum(nearby,1e-5)))
    target = world.track.poses(phase+look)
    if lateral_targets is not None:
        lane=np.asarray(lateral_targets)
        around=world.track.poses(phase[:,None]+look[:,None]+np.array([-3.,3.])[None,:])[:,:,:2]
        tangent=around[:,1]-around[:,0];tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-6)
        target[:,:2]+=np.column_stack((-tangent[:,1],tangent[:,0]))*lane[:,None]
    delta = target[:,:2]-state[:,:2]
    side = -np.sin(state[:,2])*delta[:,0]+np.cos(state[:,2])*delta[:,1]
    steer = np.arctan2(2*world.vehicle.wheelbase*side, np.maximum(1.,np.sum(delta*delta,axis=1))) / world.vehicle.max_steer
    # Probe the approaching curve, then propagate braking limits backwards.
    distances = np.arange(0.,105.,5.)
    angles = world.track.poses(phase[:,None]+distances[None,:])[:,:,2]
    signed=(np.diff(angles,axis=1)+np.pi)%(2*np.pi)-np.pi
    curvature = np.abs(signed)/np.diff(distances)
    if lateral_targets is not None:
        curvature=curvature/np.maximum(.25,1-signed/np.diff(distances)*np.asarray(lateral_targets)[:,None])
    mu = world.surface.grip*world.condition.grip_factor*world.tire.grip_factor
    corner_speed = np.sqrt((.30 if getattr(world,'modern',False) else .45)*mu*9.81 / np.maximum(curvature,1e-5))
    maximum = 24. if world.track.length>600 else 10.
    target_speed = float(speed_factor)*np.minimum(maximum,np.min(np.sqrt(corner_speed**2+2*(2. if getattr(world,'modern',False) else 4.)*distances[:-1]),axis=1))
    accel = np.clip((target_speed-speed)*.4,-1,1)
    return np.column_stack((np.clip(steer,-1,1),accel))


def racing_actions(world,indices=None,speed_factor=1.,preferred_offset=0.):
    """Named traffic teacher/reference: corridor choice + geometric follower.

    Uses current states only. It never corrects neural learner actions.
    The selected lane is part of the world's reproducible checkpoint.
    """
    rows=np.arange(world.count) if indices is None else np.atleast_1d(indices)
    w=world;offset,_,_=w.coordinates();offset=-offset  # lane targets are positive to the driver's left
    if not hasattr(w,'racing_lane'):w.racing_lane=offset.copy()
    targets=[];speed_caps=[]
    margin=max(0.,w.track.width/2-w.vehicle.width/2-.9)
    for i in rows:
        lane=float(np.clip(w.racing_lane[i],-margin,margin))
        front=[j for j in range(w.count) if j!=i and w.active[j] and 0<w.progress[j]-w.progress[i]<85]
        near=[j for j in range(w.count) if j!=i and w.active[j] and abs(w.progress[j]-w.progress[i])<45]
        if front and w.shared:
            lead=min(front,key=lambda j:w.progress[j]-w.progress[i])
            gap=w.progress[lead]-w.progress[i]
            if getattr(w,'training_phase','')!='follow' and gap<60 and (w.state[i,3]>w.state[lead,3]+.5 or gap<18):
                choices=[float(np.clip(preferred_offset,-margin,margin)), -min(2.7,margin),min(2.7,margin)]
                def cost(c):
                    result=.15*abs(c-preferred_offset)+.25*abs(c-lane)
                    for j in near:
                        d=w.progress[j]-w.progress[i]
                        separation=abs(c-offset[j])
                        if separation<w.vehicle.width+.7:
                            result+=20*(1-separation/(w.vehicle.width+.7))*(1-abs(d)/60)
                        # Reject crossing into a rapidly approaching rear car.
                        if -20<d<0 and w.state[j,3]>w.state[i,3]+2 and min(offset[i],c)-1<offset[j]<max(offset[i],c)+1:
                            result+=30
                    return result
                lane=min(choices,key=cost)
        elif not near or all(w.progress[j]-w.progress[i]<-8 for j in near):lane=float(preferred_offset)
        # Limit lateral target motion to avoid a discontinuous cut across lanes.
        w.racing_lane[i]+=np.clip(lane-w.racing_lane[i],-.9/60,.9/60)
        targets.append(w.racing_lane[i]);cap=np.inf
        for j in front:
            gap=w.progress[j]-w.progress[i]
            angle=w.state[j,2]-w.state[i,2]
            clearance=w.vehicle.width+.8+w.vehicle.length*.5*abs(np.sin(angle))
            if abs(offset[j]-offset[i])<clearance:
                cap=min(cap,max(0.,w.state[j,3]+.5*(gap-(8.+.5*w.state[i,3]))))
        speed_caps.append(cap)
    if getattr(w,'training_phase','')=='recovery':
        speed_caps=[min(cap,6.) for cap in speed_caps]
    actions=pursuit_actions(w,rows,speed_factor,np.array(targets))
    actions[:,1]=np.minimum(actions[:,1],np.clip((np.array(speed_caps)-w.state[rows,3])*.4,-1,1))
    return actions


def frozen_actions(world,policies):
    """Share geometry for a reference grid; neural controls retain observations."""
    controllers={p.snapshot.get('controller') for p in policies}
    if (all(p.kind=='geometric' and p.snapshot.get('track')==world.track.id for p in policies)
            and len(controllers)==1 and controllers<= {'pure-pursuit-1','traffic-pursuit-2'}):
        return (racing_actions if 'traffic-pursuit-2' in controllers else pursuit_actions)(world)
    from game_catalog import observation_version
    observed=world.observations(version=observation_version(max(p.inputs for p in policies)))
    return np.array([p.act(obs,world=world,index=i) for i,(p,obs) in enumerate(zip(policies,observed,strict=True))])
