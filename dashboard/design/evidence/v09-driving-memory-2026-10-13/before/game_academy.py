"""Explicit driving tasks, stationary-policy diagnostics and frozen traffic.

The academy is an environment curriculum, shared by all learning methods.
No controller modifies a learner's actions. Deterministic controllers are used
only by named opponents and by the imitation teacher.
"""
from copy import deepcopy
import math
import numpy as np

from game_catalog import ACADEMY_OBSERVATION_VERSION, observation_size, scope_hash,RACE_PHYSICS_VERSION
from game_simulation import World, DT
from game_curriculum import digest, summary
from game_control import racing_actions

VERSION='academy-1'
REWARD_VERSION='academy-progress-1'
EVALUATION_VERSION='academy-skills-1'
PHASES=('launch','control','pace','follow','overtake','corner','defend','duel','grid','race4')
LABELS=dict(zip(PHASES,('Partenza','Controllo','Passo','Inseguimento','Sorpasso',
                       'Affiancamento','Difesa','Gara 2','Partenza in gruppo','Gara 4')))
TRAFFIC=set(PHASES[3:])


def academy_profile(profile):
    result={**profile,'version':2,'observation':ACADEMY_OBSERVATION_VERSION}
    if profile['algorithm'] in ('ppo','ppo_smooth'):
        result['gamma']=math.exp(-DT/40.)
    return result


def task_spec(track_id,phase):
    from game_protocol import academy_task
    return academy_task(track_id,phase)


def expand_weights(weights,old_inputs,new_inputs,hidden,outputs=2):
    old=np.asarray(weights,dtype=float)
    old_split=(old_inputs+1)*hidden
    a=np.zeros((new_inputs+1,hidden))
    matrix=old[:old_split].reshape(old_inputs+1,hidden)
    a[:old_inputs]=matrix[:-1];a[-1]=matrix[-1]
    return np.r_[a.ravel(),old[old_split:]]


def upgrade_learner(checkpoint,profile):
    """Copy/expand a legacy learner; originals remain immutable artifacts.

    New channels start at zero weights. Training objective-dependent memories
    are discarded, actor/topology, population and random state are retained.
    """
    if not checkpoint:return None
    data=deepcopy(checkpoint['learner'])
    old=observation_size(checkpoint['configuration']['observation'])
    new=observation_size(profile['observation']);hidden=profile['hidden']
    for key,outputs in (('actor',2),('critic',1),('weights',2),('best',2),('candidate',2)):
        if key in data and isinstance(data[key],list):data[key]=expand_weights(data[key],old,new,hidden,outputs).tolist()
    if 'population' in data and data['algorithm']=='evolution':
        data['population']=[expand_weights(w,old,new,hidden).tolist() for w in data['population']]
    for key in ('actorAdam','criticAdam','stdAdam','adam','optimizer'):
        data.pop(key,None)
    data.update(buffer=[],pending=None)
    if data['algorithm'] in ('ppo','ppo_smooth'):
        from game_learning import random_weights
        data['critic']=random_weights(np.random.default_rng(profile['seed']+1201),hidden,1,inputs=new).tolist()
    if data['algorithm']=='imitation':
        data['examples']=[];data['sampleCount']=0
    if data['algorithm']=='neat':
        data['best']=None
        data.pop('candidate',None)
        for row in data['population']:row['fitness']=None
        for species in data['species']:species['fitness_history']=[]
    if 'bestScore' in data:data['bestScore']=None
    return data


class Episode:
    """One shared scenario, with one primary learner and frozen opponents."""
    def __init__(self,track_id,phase,seed,opponent_policies=(),saved=None,launch_distance=None):
        self.track_id,self.phase,self.seed=track_id,phase,seed
        self.spec=task_spec(track_id,phase)
        distance=saved['spec']['distance'] if saved and phase=='launch' and saved['spec']!=self.spec else launch_distance
        if distance is not None:
            if phase!='launch' or distance not in (1.,3.,8.,20.):raise ValueError('Compito Partenza sconosciuto')
            self.spec={**self.spec,'distance':float(distance),'label':'Partenza · '+str(int(distance))+' m'}
        self.world=World(1+self.spec['opponents'],seed,shared=bool(self.spec['opponents']),
                         laps=self.spec['laps'],track_id=track_id,physics=RACE_PHYSICS_VERSION)
        self.opponent_policies=list(opponent_policies)
        self.reset()
        if saved:self.restore(saved)

    def reset(self):
        w=self.world;w.reset(varied=False)
        self.age=0.;self.credit=0.;self.credit_time=0.;self.slow_since=None
        self.reason='';self.terminated=False;self.truncated=False
        self.reward=0.;self.return_total=0.;self.passes=0;self.contact_count=0
        self.follow_good=0;self.ticks=0;self.blocked_seconds=0.;self.first_meter=None
        self.ten_meters=None;self.stationary_seconds=0.;self.brake_at_rest=0
        self.gas_total=0.;self.term_totals={k:0. for k in ('progress','time','contact','offroad','finish','control','task','stall')}
        # Variation is from this world's RNG, never a learner's or evaluator's.
        offset=float(w.rng.uniform(-.45,.45));heading=float(w.rng.uniform(-.035,.035))
        w.perturb(0,offset,heading)
        if self.phase=='corner' and not w.track.oval:
            # First side-by-side drill uses a moderate bend with room ahead;
            # the whole-circuit retention trial still includes every corner.
            distances=np.linspace(0,w.track.length,256,endpoint=False)
            samples=w.track.poses(distances[:,None]+np.array([-5.,5.])[None,:])[:,:,2]
            curvature=np.abs((samples[:,1]-samples[:,0]+math.pi)%(2*math.pi)-math.pi)/10
            span=max(1,int(160/w.track.length*256))
            ahead=np.max(np.stack([np.roll(curvature,-i) for i in range(span)]),axis=0)
            score=ahead+2*np.abs(curvature-.025)+(curvature<.008)*100
            start=float(distances[np.argmin(score)]-40)
            w.state[0,:3]=w.track.pose(start,offset)
            w.previous_phase[0]=w.coordinates()[2][0];w.progress[0]=0
            w.progress_origin[0]=w.previous_phase[0]
            self.start_distance=start
        else:self.start_distance=0.
        self.style=float(w.rng.uniform(.55,.75))
        self.opponent_offsets=[float(w.rng.choice((-.6,0.,.6))) for _ in range(w.count-1)]
        for i in range(1,w.count):
            distance=-6*i if self.phase in ('duel','grid','race4') else -16. if self.phase=='defend' else (20. if self.phase=='corner' else 12.)+8*(i-1)
            if w.track.oval:
                w.state[i,:3]=w.track.pose(self.start_distance+distance,
                    (1.8 if i%2 else -1.8) if w.count>2 else self.opponent_offsets[i-1])
            else:w.state[i,:3]=w.track.pose(self.start_distance+distance,
                    (1.8 if i%2 else -1.8) if w.count>2 else self.opponent_offsets[i-1])
            w.previous_phase[i]=w.coordinates()[2][i]
            w.progress_origin[i]=w.previous_phase[i];w.progress[i]=distance
            if self.phase not in ('duel','grid','race4'):
                w.state[i,3]=4.;w.state[0,3]=3. if self.phase=='corner' else 0.
        self.was_ahead=[bool(w.progress[j]-w.progress[0]>w.vehicle.length+1) for j in range(1,w.count)]
        self.passed=[False]*(w.count-1)
        if hasattr(w,'_segments'):del w._segments
        w.previous_phase=w.coordinates()[2].copy();w.progress_origin=w.previous_phase.copy()
        w.training_phase=self.phase
        w.training_context[0]=[0,0,0,PHASES.index(self.phase)/(len(PHASES)-1)]

    def blocked(self):
        w=self.world
        if not w.shared:return False
        for i in range(1,w.count):
            gap=w.progress[i]-w.progress[0]
            if w.active[i] and 3.<gap<10. and w.state[i,3]<1.:
                own=w.coordinates()[0]
                if abs(own[i]-own[0])<w.vehicle.width+1:return True
        return False

    def opponent_actions(self):
        w=self.world;result=[];observed={}
        for i in range(1,w.count):
            if self.opponent_policies and self.phase in ('duel','grid','race4'):
                p=self.opponent_policies[(self.seed+i)%len(self.opponent_policies)]
                version=p.snapshot['observation']
                if p.kind=='geometric':result.append(p.act(None,world=w,index=i))
                else:
                    if version not in observed:observed[version]=w.observations(version=version)
                    result.append(p.act(observed[version][i],world=w,index=i))
            else:
                factor=self.style if self.phase not in ('defend','duel','grid','race4') else .85+.1*(i%2)
                result.append(racing_actions(w,[i],speed_factor=factor,
                                             preferred_offset=self.opponent_offsets[i-1])[0])
        return result

    def observations(self):return self.world.observations(version=ACADEMY_OBSERVATION_VERSION)[0]

    def step(self,action,smooth=False):
        if self.reason:return self.observations(),0.,True,not self.truncated
        w=self.world;was_active=w.active[0];before=float(w.progress[0]);old_events=len(w.events)
        actions=np.array([action,*self.opponent_actions()])
        pace=0. if self.phase in ('launch','control') else 1.
        _,r,_=w.step(actions,pace=pace,return_observations=False,control_cost=.03 if smooth else 0.)
        self.age+=DT;self.ticks+=1;self.gas_total+=float(action[1])
        progress=float(w.progress[0]);delta=progress-before
        if self.first_meter is None and progress>=1:self.first_meter=self.age
        if self.ten_meters is None and progress>=10:self.ten_meters=self.age
        if w.state[0,3]<.5:
            self.stationary_seconds+=DT;self.brake_at_rest+=int(action[1]<0)
        events=w.events[old_events:]
        contacts=sum(e.get('type')=='contact' and 0 in e.get('cars',[]) for e in events)
        self.contact_count+=contacts
        for key,value in w.reward_terms.items():self.term_totals[key]+=float(value[0])
        reward=float(r[0])
        if self.phase=='launch':
            # Distance-normalised progress provides a learnable short task.
            # At 20 m it is exactly the ordinary progress/10 objective.
            correction=(2./self.spec['distance']-.1)*float(w.reward_terms['progress'][0])*10
            reward+=correction;self.term_totals['progress']+=correction
        blocked=self.blocked()
        if blocked:self.blocked_seconds+=DT;self.credit_time=self.age
        if progress>=self.credit+1:
            self.credit=progress;self.credit_time=self.age;self.slow_since=None
        slow=self.age>2 and w.state[0,3]<.5 and self.age-self.credit_time>=3 and not blocked
        self.slow_since=(self.age if self.slow_since is None else self.slow_since) if slow else None
        # Three temporal inputs make the terminal no-progress rule observable.
        w.training_context[0]=[min(1,self.age/2),min(1,(self.age-self.credit_time)/15),
                               np.clip(progress-self.credit,0,1),PHASES.index(self.phase)/(len(PHASES)-1)]
        for i in range(1,w.count):
            gap=w.progress[i]-progress
            if gap>w.vehicle.length+1:self.was_ahead[i-1]=True
            if self.was_ahead[i-1] and not self.passed[i-1] and gap<-w.vehicle.length-1 and self.contact_count==0 and w.track_limits[0]==0:
                self.passed[i-1]=True;self.passes+=1;reward+=.5;self.term_totals['task']+=.5
        gap=w.progress[1]-progress if w.count>1 else 0
        if self.phase=='follow' and 5<gap<35:self.follow_good+=1
        if w.retired[0]:self.reason='contact';self.terminated=True
        elif (self.slow_since is not None and self.age-self.slow_since>=4) or (not blocked and self.age-self.credit_time>=15):
            self.reason='no_progress';self.terminated=True;reward-=.5;self.term_totals['stall']-=.5
        elif progress>=self.spec['distance']:
            self.reason='success' if self.skill_valid() else 'skill_failed';self.terminated=True
            if self.reason=='success' and not np.isfinite(w.finish[0]):reward+=2.;self.term_totals['task']+=2.
        elif not w.active[0]:self.reason='skill_failed';self.terminated=True
        elif self.age>=self.spec['limitSeconds']:
            self.reason='blocked' if blocked else 'timeout';self.truncated=True
        self.reward=reward;self.return_total+=reward
        return self.observations(),reward,bool(self.reason),self.terminated

    def skill_valid(self):
        if self.world.retired[0] or self.contact_count or self.world.track_limits[0]:return False
        if self.phase in ('overtake','corner') and self.passes<1:return False
        if self.phase=='follow' and self.follow_good/max(self.ticks,1)<.65:return False
        if self.phase=='defend' and self.world.progress[1]>self.world.progress[0]-4.4:return False
        if self.phase in ('control','pace','duel','race4'):
            return bool(self.world.checkpoint[0]>=4*self.spec['laps'])
        return True

    def result(self):
        return {'seed':self.seed,'time':self.age if self.reason=='success' else None,
                'goalMeters':self.spec['distance'],
                'progress':float(self.world.progress[0]),'status':'arrivato' if self.reason=='success' else 'ritirato' if self.reason=='contact' else self.reason or 'in corso',
                'reason':self.reason,'passes':self.passes,'contacts':self.contact_count,
                'trackLimits':int(self.world.track_limits[0]),
                'firstMeter':self.first_meter,'tenMeters':self.ten_meters,
                'stationarySeconds':self.stationary_seconds,'blockedSeconds':self.blocked_seconds,
                'brakeAtRest':self.brake_at_rest,'meanPedal':self.gas_total/max(self.ticks,1),
                'rewardTerms':deepcopy(self.term_totals)}

    def snapshot(self):
        return {k:deepcopy(v) for k,v in self.__dict__.items() if k not in ('world','opponent_policies')} | {'world':self.world.snapshot()}

    def restore(self,saved):
        if saved['spec']!=self.spec:raise ValueError('Compito Accademia incompatibile')
        for key,value in saved.items():
            if key!='world':setattr(self,key,deepcopy(value))
        self.world.restore(saved['world'])
        self.world.training_phase=self.phase


class SkillEvaluation:
    """Paired, frozen evaluation including solo/traffic retention, resumable."""
    def __init__(self,candidate,champion,phase,track_id,round_number,opponents=(),saved=None):
        from game_learning import Policy
        self.candidate=deepcopy(candidate);self.champion=deepcopy(champion)
        self.phase,self.track_id,self.round=phase,track_id,round_number
        self.policies=[Policy(candidate)]+([Policy(champion)] if champion else [])
        self.skills=[phase]
        if phase in TRAFFIC:self.skills+=['pace']
        if phase in TRAFFIC:
            self.skills += [skill for skill in PHASES[3:PHASES.index(phase)] if skill not in self.skills]
        self.scenarios=[100001+round_number*100+i for i in range(10)]
        if phase=='pace' or phase in TRAFFIC:self.scenarios += [1000001+round_number*100+i for i in range(10)]
        self.episodes=[Episode(track_id,skill,seed,opponents) for _ in self.policies for skill in self.skills for seed in self.scenarios]
        self.cursor=0;self.cancelled=False
        if saved:
            if saved['version']!=EVALUATION_VERSION or saved['skills']!=self.skills:raise ValueError('Valutazione Accademia incompatibile')
            self.cursor=saved['cursor']
            self.cancelled=saved.get('cancelled',False)
            for episode,state in zip(self.episodes,saved['episodes'],strict=True):episode.restore(state)

    def tick(self):
        # One scenario per call keeps UI/stop responsive even on metric tracks.
        remaining=[i for i,e in enumerate(self.episodes) if not e.reason]
        if not remaining:return True
        n=len(self.scenarios)
        for k in range(len(self.skills)):
            candidates=self.episodes[k*n:(k+1)*n]
            failures=sum(bool(e.reason) and e.reason!='success' for e in candidates)
            if failures>n-math.ceil(.9*n):
                # A frozen candidate cannot reach the acceptance threshold.
                # Untested scenarios remain explicitly untested, never valid.
                self.cancelled=True
                for e in self.episodes:
                    if not e.reason:e.reason='not_run';e.truncated=True
                return True
        for _ in range(len(self.episodes)):
            i=self.cursor%len(self.episodes);self.cursor+=1
            e=self.episodes[i]
            if e.reason:continue
            policy=self.policies[i//(len(self.scenarios)*len(self.skills))]
            e.step(policy.act(e.observations(),world=e.world,index=0));break
        return all(e.reason for e in self.episodes)

    def results(self):
        groups=[]
        for p in range(len(self.policies)):
            results={}
            for k,skill in enumerate(self.skills):
                n=len(self.scenarios);start=(p*len(self.skills)+k)*n
                rows=[e.result() for e in self.episodes[start:start+n]]
                result=summary(rows);result.update(laps=task_spec(self.track_id,skill)['laps'],skill=skill,
                    passes=sum(r['passes'] for r in rows),stalls=sum(r['reason']=='no_progress' for r in rows),
                    tested=sum(r['reason']!='not_run' for r in rows))
                results[skill]=result
            primary={**results[self.phase],'skills':results}
            primary['retained']=all(r['valid']>=math.ceil(.9*r['total']) for r in results.values())
            groups.append(primary)
        return groups[0],groups[1] if len(groups)>1 and not self.cancelled else None

    def snapshot(self):
        return {'version':EVALUATION_VERSION,'candidate':self.candidate,'champion':self.champion,
                'skills':self.skills,'phase':self.phase,'track':self.track_id,'round':self.round,
                'cancelled':self.cancelled,
                'cursor':self.cursor,'episodes':[e.snapshot() for e in self.episodes]}
