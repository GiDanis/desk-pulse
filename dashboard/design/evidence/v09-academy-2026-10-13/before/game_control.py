"""Explicit geometric teacher: lookahead steering and curvature speed budget."""
import numpy as np


def pursuit_actions(world, indices=None, speed_factor=1.):
    rows = np.arange(world.count) if indices is None else np.atleast_1d(indices)
    state = world.state[rows]
    phase = world.coordinates()[2][rows]
    if world.track.oval:
        from game_catalog import TRACK
        phase=phase-TRACK.half_straight
    speed = np.maximum(0, state[:,3])
    look = np.clip(3. + speed*.35, 4., 12.)
    target = world.track.poses(phase+look)
    delta = target[:,:2]-state[:,:2]
    side = -np.sin(state[:,2])*delta[:,0]+np.cos(state[:,2])*delta[:,1]
    steer = np.arctan2(2*world.vehicle.wheelbase*side, np.maximum(1.,np.sum(delta*delta,axis=1))) / world.vehicle.max_steer
    # Probe the approaching curve, then propagate braking limits backwards.
    distances = np.arange(0.,105.,5.)
    angles = world.track.poses(phase[:,None]+distances[None,:])[:,:,2]
    curvature = np.abs((np.diff(angles,axis=1)+np.pi)%(2*np.pi)-np.pi)/np.diff(distances)
    mu = world.surface.grip*world.condition.grip_factor*world.tire.grip_factor
    corner_speed = np.sqrt(.45*mu*9.81 / np.maximum(curvature,1e-5))
    maximum = 24. if world.track.length>600 else 10.
    target_speed = float(speed_factor)*np.minimum(maximum,np.min(np.sqrt(corner_speed**2+2*4.*distances[:-1]),axis=1))
    accel = np.clip((target_speed-speed)*.4,-1,1)
    return np.column_stack((np.clip(steer,-1,1),accel))
