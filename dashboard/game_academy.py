"""Explicit driving tasks, stationary-policy diagnostics and frozen traffic.

The academy is an environment curriculum, shared by all learning methods.
No controller modifies a learner's actions. Deterministic controllers are used
only by named opponents and by the imitation teacher.
"""
from copy import deepcopy
import math
import numpy as np

from game_catalog import ACADEMY_OBSERVATION_VERSION, observation_size, RACE_PHYSICS_VERSION
from game_simulation import World, DT
from game_driving_memory import PROTOCOL as MEMORY_PROTOCOL
from game_curriculum import summary
from game_control import racing_actions

VERSION='academy-1'
REWARD_VERSION='academy-progress-1'
EVALUATION_VERSION='academy-skills-1'
PHASES=('launch','control','pace','follow','overtake','corner','defend','duel','grid','race4')
LABELS=dict(zip(PHASES,('Partenza','Controllo','Passo','Inseguimento','Sorpasso',
                       'Affiancamento','Difesa','Gara 2','Partenza in gruppo','Gara 4')))
LABELS['recovery']='Rientro'
LABELS['bend']='Ingresso curva'
LABELS['straight']='Rettilineo'
TRAFFIC=set(PHASES[3:])


def academy_profile(profile):
    result={**profile,'version':2,'observation':ACADEMY_OBSERVATION_VERSION}
    if profile['algorithm'] in ('ppo','ppo_smooth','clone_ppo'):
        result['gamma']=math.exp(-DT/40.)
    return result


def task_spec(track_id,phase):
    if phase in ('recovery','bend'):
        from game_driving_memory import task
        return task(track_id,phase)
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
    if data['algorithm'] in ('ppo','ppo_smooth','clone_ppo'):
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
    def __init__(self,track_id,phase,seed,opponent_policies=(),saved=None,launch_distance=None,protocol=None,context=None,objective="impara",bots=2,single_lap=False,reward_spec=None,pace_pressure=0.,approach=False,scenario=None):
        self.track_id,self.phase,self.seed=track_id,phase,seed
        self.objective=(saved or {}).get("objective",objective)
        self.bots=(saved or {}).get("bots",bots)
        self.single_lap=(saved or {}).get("single_lap",single_lap)
        self.revision=0
        self.protocol=(saved or {}).get('protocol',protocol)
        self.reward_spec=deepcopy((saved or {}).get('reward_spec',reward_spec))
        self.pace_pressure=float((saved or {}).get('pace_pressure',pace_pressure))
        self.approach=bool((saved or {}).get('approach',approach))
        self.scenario=deepcopy((saved or {}).get('scenario',scenario))
        if self.protocol==MEMORY_PROTOCOL:
            from game_driving_memory import task
            self.spec=task(track_id,phase)
        else:self.spec=task_spec(track_id,phase)
        if self.reward_spec and self.reward_spec.get('version')=='residual-racing-2' and phase=='corner':
            self.spec={**self.spec,'distance':240.,'label':'Sorpasso in curva · 240 m'}
        if self.single_lap and phase in ('control','pace','duel','race4'):
            from game_geometry import get_track
            from game_protocol import race_budget
            self.spec={**self.spec,'laps':1,'distance':get_track(track_id).length,'label':'Un giro · '+LABELS[phase],
                       'limitSeconds':race_budget(track_id,1)}
        if (self.reward_spec or {}).get('version','').startswith('direct-driving-') and phase in ('overtake','corner'):
            from game_geometry import get_track
            from game_protocol import race_budget
            self.spec={**self.spec,'laps':1,'distance':get_track(track_id).length,
                'limitSeconds':race_budget(track_id,1),'label':'Un giro · '+LABELS[phase]}
        if (self.reward_spec or {}).get('version','').startswith('direct-driving-') and phase in ('grid','race4'):
            self.spec={**self.spec,'opponents':4}
        if self.objective!='impara':
            from game_protocol import race_budget
            self.single_lap=False
            self.spec={**self.spec,'distance':None,'laps':1,'continuous':True,
                'opponents':self.bots if self.objective=='impara_sorpasso' else 0,
                'limitSeconds':60.,
                'label':'Sorpassi continui' if self.objective=='impara_sorpasso' else 'Giri continui'}
        distance=saved['spec']['distance'] if saved and phase=='launch' and saved['spec']!=self.spec else launch_distance
        if distance is not None and self.objective=='impara':
            if phase!='launch' or distance not in (1.,3.,8.,20.):raise ValueError('Compito Partenza sconosciuto')
            self.spec={**self.spec,'distance':float(distance),'label':'Partenza · '+str(int(distance))+' m'}
        if saved and saved.get('spec'):self.spec=deepcopy(saved['spec'])
        if self.scenario and self.objective=='impara':
            self.spec={**self.spec,**{k:self.scenario[k] for k in ('distance','label','limitSeconds')},
                **({'practiceCircuit':True} if self.scenario.get('practiceCircuit') else {})}
        import game_catalog as catalog
        self.context_config=(saved or {}).get('context_config',context)
        options=dict(vehicle=catalog.RACE_VEHICLE,surface=catalog.SURFACE,condition=catalog.CONDITION,tire=catalog.TIRE)
        if self.protocol==MEMORY_PROTOCOL:
            from game_driving_memory import current_context
            if self.context_config is None:self.context_config=current_context(track_id)
            expected=self.context_config['track'];actual=catalog.track_data(track_id)
            if any(expected.get(k)!=actual.get(k) for k in ('id','revision','geometryHash')):raise ValueError('Geometria del ripasso non più disponibile')
            options=dict(vehicle=catalog.RaceVehicleSpec(**self.context_config['vehicle']),surface=catalog.SurfaceProfile(**self.context_config['surface']),
                condition=catalog.ConditionProfile(**self.context_config['condition']),tire=catalog.TireProfile(**self.context_config['tire']))
        self.world=World(1+self.spec['opponents'],seed,shared=bool(self.spec['opponents']),
                         **options,
                         laps=self.spec['laps'],track_id=track_id,physics=RACE_PHYSICS_VERSION,telemetry=self.objective!="impara" or bool(self.reward_spec),lazy_sensors=bool(self.reward_spec))
        self.world.native_sensors=bool(self.reward_spec)
        self.opponent_policies=list(opponent_policies)
        self.reset()
        if saved:self.restore(saved)

    def reset(self):
        self.revision+=1
        w=self.world;w.reset(varied=False,return_observations=not bool(self.reward_spec))
        w.continuous=self.objective!="impara" or (self.reward_spec or {}).get('cutoff')=='collection-boundary-1'
        self.reported_passes=0;self.reported_attempts=0;self.reported_stationary=0.;self.reported_age=0.;self.window_started=0.;self.reported_milestones=False;self.reported_distances=[]
        if hasattr(self,'racecraft'):del self.racecraft
        for field in ('attack','last_pass'):
            if hasattr(self,field):delattr(self,field)
        self.age=0.;self.credit=0.;self.credit_time=0.;self.slow_since=None
        self.reason='';self.terminated=False;self.truncated=False
        self.command_diagnostics=dict(initialSamples=0,initialSteerSaturated=0,initialSteerAbs=0.)
        self.reward=0.;self.return_total=0.;self.passes=0;self.contact_count=0
        self.follow_good=0;self.ticks=0;self.blocked_seconds=0.;self.first_meter=None
        self.ten_meters=None;self.stationary_seconds=0.;self.brake_at_rest=0
        self.valid_progress=0.;self.progress_frontier=0.;self.safe_seconds=0.;self.reentry_time=None
        self.gas_total=0.;self.term_totals={k:0. for k in ('progress','time','contact','offroad','finish','control','task','stall')}
        if self.reward_spec:
            from game_rewards import TERMS
            self.term_totals={key:0. for key in TERMS}
        self.pedal_counts={'gas':0,'coast':0,'brake':0};self.understeer_seconds=0.;self.risk_seconds=0.
        self.reported_pedals={};self.reported_understeer=0.
        self.reported_epoch_progress=0.
        if hasattr(self,'risk_margin'):del self.risk_margin
        # Variation is from this world's RNG, never a learner's or evaluator's.
        offset=float(w.rng.uniform(-.45,.45));heading=float(w.rng.uniform(-.035,.035))
        w.perturb(0,offset,heading)
        if self.scenario:
            w.state[0,:3]=w.track.pose(self.scenario['start'],offset)
            w.state[0,2]+=heading;w.state[0,3]=self.scenario['speed']
            self.start_distance=self.scenario['start']
            if hasattr(w,'_segments'):del w._segments
        elif self.phase=='bend' or self.approach:
            # A physically solvable approaching bend, not a controller override.
            from game_geometry import bend_scenario
            start,goal,speed=bend_scenario(w.track,self.seed)
            w.state[0,:3]=w.track.pose(start,offset)
            w.state[0,2]+=heading;w.state[0,3]=speed
            if hasattr(w,'_segments'):del w._segments
            self.start_distance=start
        elif self.phase=='corner' and not w.track.oval:
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
        if (self.reward_spec or {}).get('version','').startswith('direct-driving-') and self.phase in ('grid','race4'):
            slot=self.seed%w.count
            if slot:
                w.state[[0,slot]]=w.state[[slot,0]]
                w.progress[[0,slot]]=w.progress[[slot,0]]
                w.progress-=w.progress[0]
        self.was_ahead=[bool(w.progress[j]-w.progress[0]>w.vehicle.length+1) for j in range(1,w.count)]
        self.passed=[False]*(w.count-1)
        self.encounters=[dict(armed=False,alongside=False,contacts=0,limits=0,held=0.,cooldown=0.,lapBand=0) for _ in range(w.count-1)]
        self.pass_attempts=0;self.lappings=0;self.clean_series=0;self.best_series=0;self.lap_seen=0
        if hasattr(w,'_segments'):del w._segments
        if self.phase=='recovery':
            side=1 if self.seed%2 else -1
            w.state[0,:3]=w.track.pose(0,side*(w.track.width/2+1.1));w.state[0,3]=4.
            w.was_offroad[0]=True;w.track_limits[0]=1
            if hasattr(w,'_segments'):del w._segments
        w.previous_phase=w.coordinates()[2].copy();w.progress_origin=w.previous_phase.copy()
        w.initialize_gates()
        w.training_phase=self.phase
        w.training_context[0]=[0,0,0,PHASES.index('control' if self.phase in ('recovery','bend','straight') else self.phase)/(len(PHASES)-1)]
        if getattr(self,'input_contract',None):w.training_context[0,3]=self.input_contract['constantCue']
        self.initial_speed=float(w.state[0,3])

    def blocked(self):
        w=self.world
        if not w.shared:return False
        for i in range(1,w.count):
            gap=w.progress[i]-w.progress[0]
            if getattr(w,'continuous',False):gap=(gap+w.track.length/2)%w.track.length-w.track.length/2
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
                if self.phase=='defend' and (self.reward_spec or {}).get('version','').startswith(('residual-racing-','direct-driving-')):factor=1.05+.03*(i%2)
                result.append(racing_actions(w,[i],speed_factor=factor,
                                             preferred_offset=self.opponent_offsets[i-1])[0])
        return result

    def observations(self):
        from game_observation_contract import adapt
        return adapt(self.world.observations(version=ACADEMY_OBSERVATION_VERSION)[0],getattr(self,'input_contract',None))

    def teacher_actions(self):
        return racing_actions(self.world,[0],speed_factor=1.+.35*self.pace_pressure)[0]

    def step(self,action,smooth=False,physics=None,return_observation=True):
        if self.reason:return self.observations() if return_observation else None,0.,True,not self.truncated
        w=self.world;before=float(w.progress[0]);old_events=len(w.events)
        old_offroad=float(w.offroad_seconds[0]);was_outside=bool(w.was_offroad[0])
        reward_before={'valid':self.valid_progress,'progress':before,'passes':self.passes}
        from game_overtaking import before_step
        relative_before=before_step(self) if (self.reward_spec or {}).get('relativeAdvantage') else None
        old_totals=self.term_totals.copy();old_limits=int(w.track_limits[0]);old_laps=int(w.lap_count[0])
        actions=np.array([action,*self.opponent_actions()])
        pace=0. if self.phase in ('launch','control','bend') else 1.
        if physics is None:_,r,_=w.step(actions,pace=pace,return_observations=False,control_cost=.03 if smooth else 0.)
        else:
            from game_batch import apply
            apply(w,physics);r=np.array([physics['reward']])
        self.age+=DT;self.ticks+=1;self.gas_total+=float(action[1])
        if self.age<=2. and hasattr(self,'command_diagnostics'):
            self.command_diagnostics['initialSamples']+=1
            self.command_diagnostics['initialSteerSaturated']+=int(abs(action[0])>.9)
            self.command_diagnostics['initialSteerAbs']+=float(abs(action[0]))
        progress=float(w.progress[0]);delta=progress-before
        if self.protocol==MEMORY_PROTOCOL:
            touched=was_outside or float(w.offroad_seconds[0])>old_offroad
            earned=max(0.,progress-max(self.progress_frontier,before)) if not touched and not w.retired[0] else 0.
            desired=(earned+min(0.,delta))/10.
            r[0]+=desired-float(w.reward_terms['progress'][0]);w.reward_terms['progress'][0]=desired
            self.progress_frontier=max(self.progress_frontier,progress);self.valid_progress+=earned
            self.safe_seconds=0. if touched else self.safe_seconds+DT
            if self.phase=='recovery' and self.reentry_time is None and self.safe_seconds>=2.:self.reentry_time=self.age
        if w.telemetry and int(w.lap_count[0])>self.lap_seen:
            self.lap_seen=int(w.lap_count[0])
            self.clean_series=self.clean_series+1 if w.lap_times[0][-1]['clean'] else 0
            self.best_series=max(self.best_series,self.clean_series)
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
        credited=self.valid_progress if self.protocol==MEMORY_PROTOCOL else progress
        if credited>=self.credit+1:
            self.credit=credited;self.credit_time=self.age;self.slow_since=None
        slow=self.age>2 and w.state[0,3]<.5 and self.age-self.credit_time>=3 and not blocked
        self.slow_since=(self.age if self.slow_since is None else self.slow_since) if slow else None
        # Three temporal inputs make the terminal no-progress rule observable.
        if not getattr(self,'input_contract',None):
            w.training_context[0]=[min(1,self.age/2),min(1,(self.age-self.credit_time)/15),
                                   np.clip(credited-self.credit,0,1),PHASES.index('control' if self.phase in ('recovery','bend','straight') else self.phase)/(len(PHASES)-1)]
        if getattr(self,'input_contract',None):
            w.training_context[0,3]=self.input_contract['constantCue']
        for i in range(1,w.count):
            gap=w.progress[i]-progress
            if self.objective=='impara_sorpasso' or (self.reward_spec or {}).get('version','').startswith(('residual-racing-','direct-driving-')):
                encounter=self.encounters[i-1]
                # Encounter-local cleanliness; modulo distance only finds proximity.
                near_gap=(gap+w.track.length/2)%w.track.length-w.track.length/2
                encounter['cooldown']=max(0.,encounter['cooldown']-DT)
                margin=w.vehicle.length+1
                # Balanced protocol: one reward per opponent/lap band. A deliberate
                # slowdown cannot create a second credited pass in the same band.
                band=math.floor((progress-w.progress[i])/w.track.length)
                fresh=not self.reward_spec or band!=encounter.get('creditedBand')
                if w.active[i] and margin<near_gap<40 and not encounter['armed'] and encounter['cooldown']==0 and fresh:
                    encounter.update(armed=True,contacts=self.contact_count,limits=int(w.track_limits[0]),held=0.,alongside=False,lapBand=math.floor((progress-w.progress[i])/w.track.length))
                    self.pass_attempts+=1
                if encounter['armed']:
                    if abs(near_gap)<=margin and np.linalg.norm(w.state[i,:2]-w.state[0,:2])<15:encounter['alongside']=True
                    clean=self.contact_count==encounter['contacts'] and w.track_limits[0]==encounter['limits']
                    encounter['held']=encounter['held']+DT if near_gap<-margin and encounter['alongside'] and clean and w.active[i] else 0.
                    if not clean or not w.active[i] or abs(near_gap)>50:
                        encounter.update(armed=False,cooldown=5.,held=0.)
                    elif encounter['held']>=.5:
                        if self.reward_spec:encounter['creditedBand']=encounter['lapBand']
                        encounter.update(armed=False,cooldown=8.,held=0.)
                        self.passes+=1;self.last_pass=dict(rival=i,time=self.age);self.lappings+=int(progress-w.progress[i]>w.track.length/2)
                        reward+=.5;self.term_totals['task']+=.5
                continue
            if gap>w.vehicle.length+1:self.was_ahead[i-1]=True
            if self.was_ahead[i-1] and not self.passed[i-1] and gap<-w.vehicle.length-1 and self.contact_count==0 and w.track_limits[0]==0:
                self.passed[i-1]=True;self.passes+=1;reward+=.5;self.term_totals['task']+=.5
        gap=w.progress[1]-progress if w.count>1 else 0
        if self.phase=='follow' and 5<gap<35:self.follow_good+=1
        if (self.reward_spec or {}).get('version','').startswith(('residual-racing-','direct-driving-')):
            from game_racecraft import observe
            observe(self,action)
        if w.retired[0]:self.reason='contact';self.terminated=True
        elif (self.slow_since is not None and self.age-self.slow_since>=4) or (not blocked and self.age-self.credit_time>=15):
            self.reason='no_progress';self.terminated=True;reward-=.5;self.term_totals['stall']-=.5
        elif self.spec['distance'] is not None and credited>=self.spec['distance'] and (self.phase!='recovery' or self.safe_seconds>=2.):
            self.reason='success' if self.skill_valid() else 'skill_failed';self.terminated=True
            if (self.reward_spec or {}).get('cutoff')=='collection-boundary-1':self.terminated=False;self.truncated=True
            if self.reason=='success' and not np.isfinite(w.finish[0]):reward+=2.;self.term_totals['task']+=2.
        elif not w.active[0]:self.reason='skill_failed';self.terminated=True
        elif self.age-getattr(self,'window_started',0.)>=self.spec['limitSeconds']:
            self.reason='window' if self.objective!='impara' else 'blocked' if blocked else 'timeout';self.truncated=True
        if self.protocol==MEMORY_PROTOCOL and self.reason=='skill_failed':
            reward-=2.;self.term_totals['task']-=2.
        if self.reward_spec:
            from game_rewards import step_terms
            reward=step_terms(self,action,reward_before,old_offroad,old_limits,old_laps,old_totals,events,smooth)
            if relative_before is not None:
                from game_overtaking import relative_step
                relative=relative_step(self,relative_before)
                reward+=relative;self.term_totals['task']+=relative
                self.last_reward_terms['task']+=relative
        if w.count>1:
            from game_overtaking import observe
            observe(self)
        if getattr(self,'attack_training',False) and not w.retired[0]:
            family=self.spec['attackFamily']
            good=not self.contact_count and w.track_limits[0]<=(1 if family=='recover' else 0) and not getattr(self,'racecraft',{}).get('violations',0)
            achieved=(self.passes>0 if family in ('complete','attack','corner') else self.age>=12 and self.skill_valid() if family=='defend' else self.age>=self.spec['limitSeconds']-.1 and self.passes>0 if family=='traffic' else self.reentry_time is not None and self.safe_seconds>=2 if family=='recover' else w.clean_laps[0]>0)
            if good and achieved:self.reason='success';self.terminated=True;self.truncated=False
        self.reward=reward;self.return_total+=reward
        if len(w.events)>512:w.events=w.events[-256:]
        if not return_observation:return None,reward,bool(self.reason),self.terminated
        if physics is not None:
            obs=np.asarray(physics['observations']).copy();obs[64:68]=np.clip(w.training_context[0],-1,1)
            w._observed_cache=((False,w.native_sensors,w.observation_key()),obs[None,:].copy())
        else:obs=self.observations()
        return obs,reward,bool(self.reason),self.terminated

    def next_window(self):
        self.reason='';self.truncated=False;self.terminated=False;self.recorded=False
        self.window_started=self.age
        self.return_total=0.;self.term_totals={k:0. for k in self.term_totals}
        # Physics, lap gates, encounters and revision continue unchanged.

    def skill_valid(self):
        if getattr(self,'racecraft',{}).get('violations',0):return False
        allowed=1 if self.phase=='recovery' else 0
        if self.world.retired[0] or self.contact_count or self.world.track_limits[0]>allowed:return False
        if self.phase=='recovery':return self.reentry_time is not None and self.safe_seconds>=2.
        if self.phase in ('overtake','corner') and self.passes<1:return False
        if self.phase=='follow' and self.follow_good/max(self.ticks,1)<.65:return False
        if self.phase=='defend' and self.world.progress[1]>self.world.progress[0]-4.4:return False
        if self.phase in ('control','pace','duel','race4'):
            if (self.spec.get('practiceCircuit') and self.objective=='impara'
                    and (self.phase=='pace' and self.scenario or self.phase in ('duel','race4') and self.spec.get('practiceGrid'))):
                # A full circuit from a distributed spawn is a training segment.
                # It must cross four ordered gates, but is never a flying record:
                # World keeps the initial partial lap invalid until the finish.
                return bool(self.valid_progress>=self.spec['distance'] and self.world.checkpoint[0]>=4)
            return bool(self.world.clean_laps[0]>=self.spec['laps'])
        return True

    def manoeuvre_status(self):
        """Human-readable encounter phase; no extra reward or forced re-entry."""
        labels={'contact':'Contatto','no_progress':'Fermo · ripartenza','blocked':'Traffico bloccato'}
        if self.reason in labels:return labels[self.reason]
        if self.reason=='skill_failed':
            return {'vehicle_contact':'Contatto nella prova','incomplete_pass':'Sorpasso incompleto','race_rule':'Manovra irregolare',
                'track_limits':'Fuori dai limiti','defense_lost':'Posizione persa'}.get(self.termination_cause(),'Esercizio non riuscito')
        if not self.world.count>1:return 'Traiettorie e passo'
        w=self.world
        for j,enc in enumerate(self.encounters,1):
            if enc.get('armed'):
                if enc.get('held',0)>0:return 'Conferma sorpasso'
                if enc.get('alongside'):return 'Affiancato'
                return 'Avvicinamento'
        if self.passes:
            gaps=w.progress[0]-w.progress[1:]
            if getattr(w,'continuous',False):gaps=(gaps+w.track.length/2)%w.track.length-w.track.length/2
            if any(w.vehicle.length+1<g<w.vehicle.length+3 for g in gaps):return 'Rientro con spazio'
            return 'Sorpasso completato'
        return 'Difendi posizione' if self.phase=='defend' else 'Cerca un passaggio'

    def termination_cause(self):
        if self.reason=='skill_failed' and (self.reward_spec or {}).get('version','').startswith(('residual-racing-','direct-driving-')):
            if self.contact_count:return 'vehicle_contact'
            if getattr(self,'racecraft',{}).get('violations',0):return 'race_rule'
            if self.world.track_limits[0]:return 'track_limits'
            if self.phase in ('overtake','corner') and not self.passes:return 'incomplete_pass'
            if self.phase=='defend':return 'defense_lost'
            return 'invalid_exercise'
        if self.reason=='contact':
            code=int(getattr(self.world,'retirement_cause',[4])[0])
            return {1:'road_boundary',2:'vehicle_contact',3:'geometry_guard'}.get(code,'retirement_unknown')
        return {'no_progress':'stall','timeout':'time_limit','window':'collection_window',
                'skill_failed':'invalid_exercise','success':'success','blocked':'traffic_blocked'}.get(self.reason,'running')

    def result(self):
        from game_overtaking import metrics
        return {'seed':self.seed,'time':self.age if self.reason=='success' else None,'attack':metrics(self),
                'goalMeters':self.spec['distance'],'manoeuvre':self.manoeuvre_status(),
                'progress':float(self.world.progress[0]),'status':'arrivato' if self.reason=='success' else 'ritirato' if self.reason=='contact' else self.reason or 'in corso',
                'reason':self.reason,'terminationCause':self.termination_cause(),'passes':self.passes,'passAttempts':self.pass_attempts,'cleanSeries':self.clean_series,'bestSeries':self.best_series,'laps':int(self.world.lap_count[0]),'lapTimes':self.world.lap_times[0] if self.world.telemetry else [],'contacts':self.contact_count,
                'trackLimits':int(self.world.track_limits[0]),'validProgress':self.valid_progress,
                'reentryTime':self.reentry_time,'offroadSeconds':float(self.world.offroad_seconds[0]),
                'firstMeter':self.first_meter,'tenMeters':self.ten_meters,
                'stationarySeconds':self.stationary_seconds,'blockedSeconds':self.blocked_seconds,
                'brakeAtRest':self.brake_at_rest,'meanPedal':self.gas_total/max(self.ticks,1),
                'rewardTerms':deepcopy(self.term_totals),
                'rewardVersion':(self.reward_spec or {}).get('version',REWARD_VERSION),
                'racecraft':deepcopy(getattr(self,'racecraft',{})),'commandDiagnostics':deepcopy(getattr(self,'command_diagnostics',{})),'pedalCounts':self.pedal_counts.copy(),'understeerSeconds':self.understeer_seconds}

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
    def __init__(self,candidate,champion,phase,track_id,round_number,opponents=(),saved=None,protocol=None):
        from game_learning import Policy
        self.protocol=(saved or {}).get('protocol',protocol)
        self.candidate=deepcopy(candidate);self.champion=deepcopy(champion)
        self.phase,self.track_id,self.round=phase,track_id,round_number
        self.policies=[Policy(candidate)]+([Policy(champion)] if champion else [])
        self.skills=[phase]
        if phase in TRAFFIC:self.skills+=['pace']
        if phase in TRAFFIC:
            self.skills += [skill for skill in PHASES[3:PHASES.index(phase)] if skill not in self.skills]
        if self.protocol==MEMORY_PROTOCOL:
            prerequisites=() if phase=='launch' else ('launch',) if phase in ('control','bend') else ('launch','control') if phase=='recovery' else ('launch','control','recovery')
            for skill in prerequisites:
                if skill not in self.skills:self.skills.append(skill)
        self.scenarios=[100001+round_number*100+i for i in range(10)]
        if self.protocol==MEMORY_PROTOCOL or phase=='pace' or phase in TRAFFIC:self.scenarios += [1000001+round_number*100+i for i in range(10)]
        self.episodes=[Episode(track_id,skill,seed,opponents,protocol=self.protocol) for _ in self.policies for skill in self.skills for seed in self.scenarios]
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
        return {'version':EVALUATION_VERSION,'protocol':self.protocol,'candidate':self.candidate,'champion':self.champion,
                'skills':self.skills,'phase':self.phase,'track':self.track_id,'round':self.round,
                'cancelled':self.cancelled,
                'cursor':self.cursor,'episodes':[e.snapshot() for e in self.episodes]}
