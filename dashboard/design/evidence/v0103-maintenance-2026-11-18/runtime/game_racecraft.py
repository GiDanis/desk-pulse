"""Observable game rules, not an attribution of intent or real sporting law."""
import math
import numpy as np


def observe(episode,action):
    w=episode.world
    state=getattr(episode,'racecraft',None)
    if state is None:
        state=dict(version='racecraft-1',violations=0,weaves=0,unnecessaryBrake=0,
            moveDirection=0,lastTarget=0.,armed=False,brakeSeconds=0.,reported=0)
        episode.racecraft=state
    offset,_,phase=w.coordinates();ego=w.state[0]
    rear=[];front=[]
    for j in range(1,w.count):
        if not w.active[j]:continue
        gap=w.progress[j]-w.progress[0]
        if getattr(w,'continuous',False):gap=(gap+w.track.length/2)%w.track.length-w.track.length/2
        if -45<gap<-w.vehicle.length and w.state[j,3]>ego[3]+.1:rear.append(j)
        if 0<gap<60:front.append(j)
    if rear:
        if getattr(w,'direct_control',False):
            # Direct control has no requested lane. Observe actual lateral
            # reversals in road coordinates; this only records game rules.
            own=-float(offset[0])
            if not state['armed']:
                state.update(armed=True,lastTarget=own,moveDirection=0)
            elif abs(own-state['lastTarget'])>.8:
                direction=1 if own>state['lastTarget'] else -1
                if state['moveDirection'] and direction!=state['moveDirection']:
                    state['weaves']+=1;state['violations']+=1
                state.update(lastTarget=own,moveDirection=direction)
        rule=getattr(w,'residual_rules',{}).get(0,{})
        new_weaves=max(0,rule.get('weaves',0)-state['weaves'])
        state['weaves']+=new_weaves;state['violations']+=new_weaves
        s=float(phase[0])-(36. if w.track.oval else 0.)
        stricter=spatial(episode)
        mu=w.surface.grip*w.condition.grip_factor*w.tire.grip_factor
        horizon=float(np.clip(ego[3]**2/(max(.1,mu)*9.81)+ego[3]*.5+5,12,150)) if stricter else 100.
        distances=np.linspace(0,horizon,11)
        angles=w.track.poses(s+distances)[:,2]
        turns=np.abs((np.diff(angles)+math.pi)%(2*math.pi)-math.pi)/(horizon/10)
        unnecessary=(ego[3]>3 or not stricter) and action[1]<-.5 and not front and np.max(turns)<.005 and not w.was_offroad[0]
        state['brakeSeconds']=state['brakeSeconds']+1/60 if unnecessary else 0.
        if state['brakeSeconds']>=.5:
            state['unnecessaryBrake']+=1;state['violations']+=1;state['brakeSeconds']=0.
    else:state.update(armed=False,moveDirection=0,brakeSeconds=0.)
    if spatial(episode):
        squeezed=False
        target=getattr(w,'residual_rules',{}).get(0,{}).get('requestedLine',float(-offset[0]))
        own=-float(offset[0]);margin=w.track.width/2-w.vehicle.width/2
        # Bounded diagnostic samples, never an observation or reward input.
        state['diagnosticTicks']=state.get('diagnosticTicks',0)+1
        if state['diagnosticTicks']%60==1 and (episode.reward_spec or {}).get('evaluationRules'):
            rivals=[j for j in range(1,w.count) if w.active[j]]
            rival=min(rivals,key=lambda j:float(np.linalg.norm(w.state[j,:2]-ego[:2]))) if rivals else None
            sample=dict(time=float(episode.age),speed=float(ego[3]),pedal=float(action[1]),steer=float(action[0]),
                requestedLine=float(target),executedLine=own,lineError=float(target-own),
                longitudinalGap=float(w.progress[rival]-w.progress[0]) if rival is not None else None,
                lateralGap=float(-offset[rival]-own) if rival is not None else None,
                relativeSpeed=float(w.state[rival,3]-ego[3]) if rival is not None else None,
                offroad=bool(w.was_offroad[0]),contacts=int(episode.contact_count))
            state['decisionTrace']=(state.get('decisionTrace',[])+[sample])[-20:]
        for j in range(1,w.count):
            if not w.active[j] or abs(w.progress[j]-w.progress[0])>=w.vehicle.length:continue
            other=-float(offset[j]);distance=float(np.linalg.norm(w.state[j,:2]-ego[:2]))
            if distance>15 or abs(other)>margin:continue
            side=1 if own>other else -1
            space_to_edge=margin+side*other
            requested_separation=side*(target-other)
            if space_to_edge<w.vehicle.width+.25 and requested_separation<w.vehicle.width+.25:squeezed=True
        state['spaceSeconds']=state.get('spaceSeconds',0.)+1/60 if squeezed else 0.
        if state['spaceSeconds']>=.25 and not state.get('spaceReported',False):
            state['violations']+=1;state['spaceViolations']=state.get('spaceViolations',0)+1;state['spaceReported']=True
        if not squeezed:state['spaceReported']=False
    return state


def spatial(episode):
    spec=episode.reward_spec or {}
    return spec.get('raceRulesVersion',spec.get('evaluationRules'))=='spatial-rules-2'
