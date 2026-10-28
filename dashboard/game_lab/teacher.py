"""Private planner memory for causal teacher labels, never actor inference."""
from copy import deepcopy
import numpy as np
from game_driving_school import actions


class Teacher:
    VERSION='causal-corridor-teacher-2'
    fields=('racing_lane','racing_base_lane','school_lane_initialized','training_phase')

    def __init__(self,utilization=.55):
        self.memory={};self.utilization=float(utilization);self.calls=0
        self.lane=None;self.target=None;self.rival=None

    def corridor(self,w):
        """Commit to one pass until clear; distant staggered bots do not veto
        both sides before the nearest vehicle has actually been passed.
        """
        offset=-w.coordinates()[0];own=float(offset[0]);speed=float(w.state[0,3])
        if self.lane is None:self.lane=own;self.target=own
        gap=(w.progress-w.progress[0]+w.track.length/2)%w.track.length-w.track.length/2
        margin=min(3.7,w.track.width/2-w.vehicle.width/2-1.2)
        if self.rival is not None and (not w.active[self.rival] or gap[self.rival]<-12. or gap[self.rival]>65.):self.rival=None
        fronts=[j for j in range(1,w.count) if w.active[j] and 0<gap[j]<65.]
        if self.rival is None and fronts:
            lead=min(fronts,key=lambda j:gap[j])
            if speed>w.state[lead,3]+.2 or gap[lead]<22.:
                choices=(-margin,0.,margin)
                def cost(lane):
                    value=.2*abs(lane-self.lane)
                    for j in range(1,w.count):
                        if not w.active[j]:continue
                        d=float(gap[j]);sep=abs(lane-offset[j])
                        if j==lead:weight=100.
                        elif -12.<d<max(8.,speed-w.state[j,3])*2:weight=130.
                        else:weight=2.*max(0.,1-abs(d)/50.)
                        value+=weight*max(0.,1-sep/(w.vehicle.width+1.))
                        if -18.<d<6. and min(own,lane)-w.vehicle.width<offset[j]<max(own,lane)+w.vehicle.width:
                            value+=150.
                    return value
                chosen=min(choices,key=cost)
                if abs(chosen-offset[lead])>w.vehicle.width+.7:self.target=chosen;self.rival=lead
        if self.rival is None and not fronts:
            rear=[j for j in range(1,w.count) if w.active[j] and -20.<gap[j]<0 and w.state[j,3]>speed]
            if not rear:self.target=0.
        self.lane+=float(np.clip(self.target-self.lane,-.09,.09))
        command=actions(w,[0],lane=self.lane,utilization=self.utilization,traffic=False)[0]
        for j in fronts:
            # Charge the whole current body corridor, including heading and
            # closing speed; lateral progress alone is not clearance.
            clearance=w.vehicle.width+.9+.5*w.vehicle.length*abs(np.sin(w.state[j,2]-w.state[0,2]))
            if abs(offset[j]-own)<clearance:
                closing=max(0.,speed-float(w.state[j,3]))
                safe=7.+.35*speed+closing*closing/6.
                target=max(0.,float(w.state[j,3])+.4*(float(gap[j])-safe))
                command[1]=min(command[1],np.clip((target-speed)*.6,-1,1))
        # Match the simulator's axle friction circles. On a front-wheel-drive
        # car, saturating longitudinal front force removes the front lateral
        # budget even below the whole-car lateral speed limit.
        if command[1]>0 and abs(command[0])>.025 and speed>3.:
            v=w.vehicle;mu=w.surface.grip*w.condition.grip_factor*w.tire.grip_factor
            normal=np.clip(v.mass*9.81*(v.wheelbase-v.cg_front)/v.wheelbase
                -v.mass*w.acceleration[0,0]*v.cg_height/v.wheelbase,.15*v.mass*9.81,.85*v.mass*9.81)
            curvature=abs(np.tan(command[0]*v.max_steer)/v.wheelbase)
            lateral=v.mass*speed*speed*curvature
            budgets=[]
            for load,share,lat in ((normal,v.drive_front,(v.wheelbase-v.cg_front)/v.wheelbase),
                                  (v.mass*9.81-normal,1-v.drive_front,v.cg_front/v.wheelbase)):
                if share>0:
                    available=np.sqrt(max(0.,(mu*load)**2-(lateral*lat/.8)**2))/share
                    budgets.append(available)
            drive=min(v.drive_force,v.power/max(3.,speed))
            command[1]=min(command[1],min(budgets)/drive)
        return command

    def label(self,world):
        original={k:deepcopy(getattr(world,k)) for k in self.fields if hasattr(world,k)}
        try:
            for k in self.fields:
                if k in self.memory:setattr(world,k,deepcopy(self.memory[k]))
                elif k=='school_lane_initialized' and hasattr(world,k):delattr(world,k)
            value=self.corridor(world).copy()
            self.memory={k:deepcopy(getattr(world,k)) for k in self.fields if hasattr(world,k)}
            self.last_intent=[float(self.lane)/(world.track.width/2),float(self.target)/(world.track.width/2)]
            self.calls+=1
        finally:
            for k in self.fields:
                if k in original:setattr(world,k,original[k])
                elif hasattr(world,k):delattr(world,k)
        if not np.isfinite(value).all():raise ValueError('Nonfinite teacher label')
        return value
