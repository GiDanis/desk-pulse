"""Interruptible academy orchestrator; one learning pilot, frozen opponents."""
from copy import deepcopy
import time
import math
import numpy as np

from game_academy import (Episode,SkillEvaluation,PHASES,LABELS,TRAFFIC,VERSION,
                          REWARD_VERSION,EVALUATION_VERSION,task_spec)
from game_catalog import configuration,scope_hash
from game_curriculum import digest
from game_learning import Evolution,PPO,PPOSmooth,Imitation,Policy,Adam,random_weights
from game_numeric import checkpoint_value
from game_control import racing_actions
import game_driving_memory as driving_memory
from game_simulation import DT


class AcademyTrainer:
    def __init__(self,profile,track_id,checkpoint=None,opponents=(),objective="impara",view="pilot",bots=2,balanced=False,batched=False):
        self.profile,self.track_id=profile,track_id
        self.objective=objective;self.view=view;self.bots=bots;self.population_revision=0
        self.rate_samples={};self.preview_revision=0
        checkpoint=checkpoint or {}
        if balanced:
            from game_rewards import migrate
            checkpoint=migrate(checkpoint,profile,objective)
            checkpoint.setdefault('configuration',configuration(track_id,profile['observation']))
            checkpoint.setdefault('protocol','driving-memory-1')
        self.reward_spec=deepcopy(checkpoint.get('rewardSpec'))
        self.balanced=bool(self.reward_spec)
        self.evo_v2=bool(self.reward_spec and self.reward_spec.get('evoVersion'))
        self.next_observations=None
        self.batched=bool(batched and self.balanced)
        self.physics_results=deepcopy(checkpoint.get('physicsResults'))
        from game_batch import BatchPhysics
        self.batch_physics=BatchPhysics() if self.batched else None
        self.migration=deepcopy(checkpoint.get('rewardMigration'))
        self.source_checkpoint=checkpoint.get('sourceCheckpoint')
        if checkpoint and checkpoint.get('configuration')!=configuration(track_id,profile['observation']):
            raise ValueError('Checkpoint fisico Accademia incompatibile')
        from game_driving_memory import PROTOCOL,PHASES as MEMORY_PHASES,Review
        self.protocol=checkpoint.get('protocol')
        self.modern=self.protocol==PROTOCOL;self.phases=MEMORY_PHASES if self.modern else PHASES
        if self.balanced:self.phases=('launch','bend',*tuple(x for x in self.phases if x!='launch'))
        self.memory=deepcopy(checkpoint.get('memory') or {});self.review=None;self.memory_reviews=deepcopy(checkpoint.get('memoryReviews',[]))
        self.display_episodes=[];self.display_generation=0;self.replay_context=None;self.reward_context=checkpoint.get('rewardContext')
        backend=checkpoint.get('learner')
        cls={'evolution':Evolution,'ppo':PPO,'ppo_smooth':PPOSmooth,'imitation':Imitation}.get(profile['algorithm'])
        if cls is None:
            from game_neat import NEAT
            cls=NEAT
        self.learner=cls(profile,backend,evo_v2=self.evo_v2) if cls is Evolution else cls(profile,backend)
        if self.balanced:self.learner.driving_balance=True
        if isinstance(self.learner,Evolution):self.learner.evo_v2=self.evo_v2
        if self.modern and isinstance(self.learner,PPO):self.learner.configure_runtime(checkpoint.get('tuning') or {})
        self.rng=np.random.default_rng(profile['seed']+701)
        self.steps=checkpoint.get('steps',0)
        self.state=checkpoint.get('curriculum') or {
            'version':2,'academyVersion':VERSION,'rewardVersion':REWARD_VERSION,
            'evaluationVersion':EVALUATION_VERSION,'phase':'launch','phaseUpdates':0,
            'updates':0,'round':0,'reliableWindows':0,'champion':None,'baseline':None,
            'evaluations':[],'qualifications':{},'pending':None,
            'stats':{'episodes':0,'success':0,'no_progress':0,'contact':0,'timeout':0,
                     'blocked':0,'skill_failed':0,'passes':0,'launches':0,'launchSuccess':0,
                     'stationarySeconds':0.,'firstMeterTimes':[],'tenMeterTimes':[],
                     'rewardTerms':{},'simulatedSeconds':0.}}
        if self.objective!='impara' and not self.state.get('objective'):
            self.state.update(phase='overtake' if self.objective=='impara_sorpasso' else 'control',objective=self.objective)
        if self.modern:self.state.update(protocol=self.protocol,rewardVersion=driving_memory.REWARD)
        if self.balanced:self.state.update(rewardVersion=self.reward_spec['version'],rewardSpec=deepcopy(self.reward_spec))
        self.state.setdefault('pacePressure',0.);self.state.setdefault('curveReady',False)
        if self.balanced:
            from game_native import available
            self.state['execution']=dict(backend='serial',collectors=0,selection='balanced-cpu-1')
            self.state['execution']['nativeSensors']=available()
            self.state['execution']['batchedPhysics']=self.batched
            self.state['execution']['method']=self.profile['algorithm']
            if isinstance(self.learner,PPO):self.state['tuning']=dict(self.learner.tuning)
        self.state["stats"].setdefault("window",0)
        self.state["stats"].setdefault("passAttempts",0)
        self.state["stats"].setdefault("laps",0)
        self.state['stats'].setdefault('recoveries',0);self.state['stats'].setdefault('recoverySuccess',0)
        self.state['stats'].setdefault('recoveryTimes',[])
        self.state['stats'].setdefault('warmups',0);self.state['stats'].setdefault('warmupSuccess',0)
        self.state.setdefault('launchGoal',1.);self.state.setdefault('launchWindow',[])
        self.evo_plan=None
        if self.evo_v2:
            self.state.setdefault('epochStats',dict(version=self.reward_spec['version'],startedSteps=self.steps,episodes=0,byTask={}))
            if self.objective=='impara':
                from game_evo_plan import EvoPlan
                self.evo_plan=EvoPlan(self.state,profile,track_id,self.memory.get('coverage',[]))
        if self.state.get('academyVersion')!=VERSION:raise ValueError('Curriculum Accademia incompatibile')
        snapshots=checkpoint.get('frozenOpponents')
        self.opponents=[Policy(p) for p in snapshots] if snapshots is not None else list(opponents)
        self.episodes=[];self.fitness=np.zeros(profile['population']);self.inflight=None;self._buffers=None;self.observation_rows=[]
        self.iterator=None;self.evaluation=None;self.metric={};self.saved_metric=[]
        self.collectors=None;self.collected=deepcopy(checkpoint.get('collectorResults'))
        self.preview=None;self.preview_hold=0.;self.preview_remaining=0.
        self.last_preview=time.monotonic();self.preview_policy=None;self.last_preview_policy=0.
        if checkpoint.get('rng'):self.rng.bit_generator.state=checkpoint['rng']
        states=checkpoint.get('episodes')
        if states:
            self.episodes=[Episode(s.get('track_id',track_id),s['phase'],s['seed'],self.opponents,s) for s in states]
            self.fitness=np.asarray(checkpoint['fitness'])
            self.inflight=self.numeric_batch(checkpoint.get('inflight'))
            self._buffers=self.inflight
            self.metric=deepcopy(checkpoint.get('metric',{}))
        else:self.reset_episodes()
        self.observation_rows=[np.asarray(row) for row in checkpoint.get('observationRows',[])]
        pending=self.state.get('pending')
        if pending:
            if pending.get('kind')=='evo-stage-check-1':
                from game_evo_plan import EvoStageCheck
                self.evaluation=EvoStageCheck(self.evo_plan,pending['candidate'],pending)
            else:self.evaluation=SkillEvaluation(pending['candidate'],pending['champion'],pending['phase'],
                    track_id,pending['round'],self.opponents,pending)
        if isinstance(self.learner,PPO) and self.learner.pending is not None:self.iterator=self.learner.updates()
        visible=checkpoint.get('visibleEpisodes')
        if visible:self.display_episodes=[Episode(s['track_id'],s['phase'],s['seed'],self.opponents,s) for s in visible]
        else:self.display_episodes=[e for e in self.episodes if e.track_id==track_id]
        self.display_generation=checkpoint.get('visibleGeneration',getattr(self.learner,'generation',0)+1)
        self.replay_context=checkpoint.get('replayContext')
        saved_review=checkpoint.get('memoryReview')
        if saved_review:self.review=Review(saved_review['candidate'],saved_review['baseline'],saved_review['contexts'],saved_review['revision'],saved_review['kind'],saved_review)
        elif not self.evo_plan and self.objective=='impara' and self.modern and self.memory.get('fresh') and not self.memory.get('familiarized'):
            policy=self.learner.policy()
            self.review=Review(policy,None,[dict(track=track_id,phase='launch')],0,'familiarization')

    @property
    def phase(self):return self.state['phase']

    @property
    def task(self):
        if self.episodes:return self.episodes[0].spec
        spec=driving_memory.task(self.track_id,self.phase) if self.modern else task_spec(self.track_id,self.phase)
        if self.phase=='launch':spec={**spec,'distance':self.launch_goal,'label':'Partenza · '+str(int(self.launch_goal))+' m'}
        return spec

    @property
    def launch_goal(self):return self.state['launchGoal']

    def reset_episodes(self):
        if self.evo_plan:
            self.reset_evo_episodes();return
        if self.modern and self.episodes:
            visible=[e for e in self.episodes if e.track_id==self.track_id]
            if visible:self.display_episodes=visible;self.display_generation=max(1,getattr(self.learner,'generation',0))
        self.population_revision+=1
        self.episodes=[];common=self.phase;self.replay_context=None
        evolutionary=isinstance(self.learner,Evolution) or self.profile['algorithm']=='neat'
        coverage=[c for c in self.memory.get('coverage',[]) if c['track']!=self.track_id]
        if self.objective=='impara' and evolutionary and self.state['updates']%5==4 and self.phase!='launch':
            if self.modern and coverage:self.replay_context=coverage[(self.state['updates']//5)%len(coverage)];common=self.replay_context['phase']
            else:common='pace' if self.phase in TRAFFIC else 'launch'
        seed=(self.profile['seed']+1800000) if self.evo_v2 else int(self.rng.integers(1,90000)) if self.modern and evolutionary else None
        for i in range(self.profile['population']):
            phase=common;track=self.track_id
            if self.replay_context:track=self.replay_context['track']
            if self.objective=='impara' and (isinstance(self.learner,PPO) or isinstance(self.learner,Imitation)) and i%5==4 and self.phase!='launch':
                if self.modern and coverage:
                    c=coverage[(i//5+self.state['updates'])%len(coverage)];track=c['track'];phase=c['phase']
                else:phase='pace' if self.phase in TRAFFIC else 'launch'
            context=None
            if self.modern:
                from game_driving_memory import current_context
                context=current_context(track,self.profile['observation'])
                if self.replay_context:context=self.replay_context.get('configuration',context)
                elif track!=self.track_id:context=c.get('configuration',context)
            self.episodes.append(Episode(track,phase,seed if seed is not None else int(self.rng.integers(1,90000)),self.opponents,
                launch_distance=self.launch_goal if phase=='launch' else None,protocol=self.protocol,context=context,objective=self.objective,bots=self.bots,single_lap=True,
                reward_spec=self.reward_spec,pace_pressure=self.state['pacePressure'],
                approach=self.balanced and not self.evo_v2 and self.objective!='impara' and self.state['updates']%3==0))
        if self.modern and evolutionary:
            context=(self.episodes[0].track_id,common,self.launch_goal if common=='launch' else None,self.objective,self.episodes[0].spec['laps'],self.state['pacePressure']) if self.balanced else (self.episodes[0].track_id,common,self.launch_goal if common=='launch' else None,self.objective,self.episodes[0].spec['laps'])
            if self.reward_context is not None and tuple(self.reward_context)!=context:self.learner.change_reward()
            self.reward_context=context
        if not self.replay_context:self.display_episodes=[e for e in self.episodes if e.track_id==self.track_id]
        self.fitness[:]=0;self.inflight=None;self._buffers=None;self.observation_rows=[];self.next_observations=None;self.physics_results=None

    def reset_evo_episodes(self):
        self.population_revision+=1;self.replay_context=None
        case=self.evo_plan.cases()[self.evo_plan.data['case']]
        track=case.get('track',self.track_id)
        if track!=self.track_id:
            visible=[e for e in self.episodes if e.track_id==self.track_id]
            if visible:self.display_episodes=visible;self.display_generation=self.learner.generation+1
            self.replay_context=dict(track=track,phase=case['phase'])
        self.episodes=[Episode(track,case['phase'],case['seed'],self.opponents,
            protocol=self.protocol,objective=self.objective,bots=self.bots,single_lap=True,
            reward_spec=self.reward_spec,pace_pressure=self.state['pacePressure'],scenario=case['scenario'],context=case.get('context'),
            launch_distance=20. if case['phase']=='launch' and case['scenario'] is None else None) for _ in range(self.profile['population'])]
        context=self.evo_plan.context()
        if self.reward_context is not None and tuple(self.reward_context)!=context:self.learner.change_reward()
        self.reward_context=context
        if not self.replay_context:self.display_episodes=self.episodes
        self.fitness[:]=0;self.inflight=None;self._buffers=None;self.observation_rows=[];self.next_observations=None;self.physics_results=None

    def record_episode(self,e):
        if not e.reason or getattr(e,'recorded',False):return
        e.recorded=True;row=e.result();stats=self.state['stats']
        if self.evo_v2:
            from game_evo_plan import record_epoch
            record_epoch(self.state,e,row)
        stats['episodes']+=int(e.reason!='window');stats[e.reason]=stats.get(e.reason,0)+1;stats['passes']+=row['passes']-getattr(e,'reported_passes',0);e.reported_passes=row['passes']
        stats['bestSeries']=max(stats.get('bestSeries',0),row.get('bestSeries',0))
        stats['passAttempts']+=row.get('passAttempts',0)-getattr(e,'reported_attempts',0);e.reported_attempts=row.get('passAttempts',0);stats['laps']=max(stats['laps'],row.get('laps',0))
        stats['stationarySeconds']+=row['stationarySeconds']-getattr(e,'reported_stationary',0);e.reported_stationary=row['stationarySeconds'];stats['simulatedSeconds']+=e.age-getattr(e,'reported_age',0.);e.reported_age=e.age
        if e.phase=='recovery':
            stats['recoveries']+=1;stats['recoverySuccess']+=int(e.reason=='success')
            if row['reentryTime'] is not None:stats['recoveryTimes']=(stats['recoveryTimes']+[row['reentryTime']])[-256:]
        if e.phase=='launch':
            if e.spec['distance']==20:stats['launches']+=1;stats['launchSuccess']+=int(e.reason=='success')
            else:stats['warmups']+=1;stats['warmupSuccess']+=int(e.reason=='success')
            if e.spec['distance']==self.launch_goal:self.state['launchWindow']=(self.state['launchWindow']+[int(e.reason=='success')])[-32:]
        for field,name in (('firstMeter','firstMeterTimes'),('tenMeters','tenMeterTimes')):
            if field not in getattr(e,'reported_distances',[]) and row[field] is not None:
                stats[name]=(stats[name]+[row[field]])[-256:];e.reported_distances.append(field)
        e.reported_milestones=True
        for name,value in row['rewardTerms'].items():stats['rewardTerms'][name]=stats['rewardTerms'].get(name,0)+value
        if self.balanced:
            counts=row['pedalCounts'];old=getattr(e,'reported_pedals',{})
            target=stats.setdefault('pedalCounts',dict(gas=0,coast=0,brake=0))
            for name,value in counts.items():target[name]+=value-old.get(name,0)
            e.reported_pedals=counts.copy()
            previous=getattr(e,'reported_understeer',0.)
            stats['understeerSeconds']=stats.get('understeerSeconds',0.)+row['understeerSeconds']-previous
            e.reported_understeer=row['understeerSeconds']

    def schedule(self):
        if self.objective!='impara':
            self.state['updates']+=1;self.state['phaseUpdates']+=1
            if self.modern and self.state['updates']%5==0:
                from game_driving_memory import Review
                candidate=self.learner.candidate_policy() if hasattr(self.learner,'candidate_policy') else self.learner.policy()
                contexts=[{k:c[k] for k in ('track','phase','configuration','contextHash') if k in c} for c in self.memory.get('coverage',[])]
                for phase in ('launch','control','recovery',self.phase):
                    if not any(c['track']==self.track_id and c['phase']==phase for c in contexts):contexts.append(dict(track=self.track_id,phase=phase))
                self.review=Review(candidate,self.memory.get('baseline'),contexts,self.memory.get('reviewRevision',0))
            return
        old_goal=self.launch_goal
        self.state['updates']+=1;self.state['phaseUpdates']+=1
        if self.balanced and self.state['curveReady'] and self.phase not in ('launch','bend','control','recovery'):
            self.state['pacePressure']=min(1.,self.state['pacePressure']+.125)
        if self.phase=='launch' and len(self.state['launchWindow'])==32 and sum(self.state['launchWindow'])>=20 and old_goal<20:
            goals=(1.,3.,8.,20.);self.state['launchGoal']=goals[goals.index(old_goal)+1];self.state['launchWindow']=[]
        if self.phase=='launch' and self.launch_goal!=old_goal:
            self.reset_episodes()
            if hasattr(self.learner,'change_reward'):self.learner.change_reward()
            if isinstance(self.learner,PPO):self.learner.buffer=[]
        if (self.state['updates']-1)%(8 if isinstance(self.learner,PPO) else 5):return
        self.state['round']+=1
        candidate=self.learner.candidate_policy() if hasattr(self.learner,'candidate_policy') else self.learner.policy()
        champion=self.state['champion']
        self.evaluation=SkillEvaluation(candidate,champion['policy'] if champion else None,
                                        self.phase,self.track_id,self.state['round'],self.opponents,protocol=self.protocol)

    def accept_evaluation(self):
        if self.evo_plan and not self.evo_plan.graduated:
            self.accept_evo_check();return
        ev=self.evaluation;candidate,old=ev.results()
        reliable=candidate['valid']>=math.ceil(.9*candidate['total']) and candidate['retained']
        improved=reliable and (old is None or not old['retained'] or candidate['valid']>old['valid'] or
                               candidate['median']<old['median']-.05)
        scope=scope_hash(self.track_id,self.profile['observation'])
        proof={'round':self.state['round'],'phase':self.phase,'rewardVersion':self.state['rewardVersion'],
               'evaluationVersion':EVALUATION_VERSION,'scope':scope,'scenarios':ev.scenarios,
               'candidateHash':digest(ev.candidate),'candidate':candidate,'champion':old,
               'championHash':digest(ev.champion) if ev.champion else '', 'promoted':False}
        if reliable:
            skills=candidate['skills'];qualifications={}
            def certificate(result):
                return {'scope':scope,'candidateHash':proof['candidateHash'],'valid':result['valid'],
                        'total':result['total'],'laps':result['laps'],'round':self.state['round']}
            solo=skills.get('pace')
            if solo and solo['valid']>=18:qualifications['solo']=certificate(solo)
            if qualifications.get('solo') and skills.get('duel',{}).get('valid',0)>=18:
                qualifications['race2']=certificate(skills['duel'])
            if qualifications.get('race2') and self.phase=='race4' and candidate['retained']:
                qualifications['race4']=certificate(candidate)
            # Launch/drill success alone never replaces the previous race model.
            new_skill=any(k not in self.state['qualifications'] for k in qualifications)
            if qualifications.get('solo') and (improved or new_skill or self.state['champion'] is None):
                proof['promoted']=True;self.state['qualifications']=qualifications
                self.state['champion']={'policy':deepcopy(ev.candidate),'proof':deepcopy(proof),'profile':deepcopy(self.profile)}
                if self.state['baseline'] is None:self.state['baseline']=deepcopy(solo)
        self.state['evaluations']=(self.state['evaluations']+[proof])[-40:]
        self.state['reliableWindows']=self.state['reliableWindows']+1 if reliable else 0
        if self.modern and reliable:
            from game_driving_memory import Review
            contexts=[{k:c[k] for k in ('track','phase','configuration','contextHash') if k in c} for c in self.memory.get('coverage',[])]
            for skill,result in candidate['skills'].items():
                from game_driving_memory import current_context
                c=dict(track=self.track_id,phase=skill,configuration=current_context(self.track_id,self.profile['observation']),contextHash=scope)
                if result['valid']>=18 and not any((x['track'],x['phase'],x.get('contextHash'))==(c['track'],c['phase'],scope) for x in contexts):contexts.append(c)
            self.review=Review(ev.candidate,self.memory.get('baseline'),contexts,self.memory.get('reviewRevision',0))
        self.evaluation=None;self.state['pending']=None
        if self.state['reliableWindows']>=2 and self.phase!='race4':
            if self.balanced and self.phase=='bend':self.state['curveReady']=True
            self.state['phase']=self.phases[self.phases.index(self.phase)+1]
            self.state['reliableWindows']=0;self.state['phaseUpdates']=0
            if hasattr(self.learner,'change_reward'):self.learner.change_reward()
            if isinstance(self.learner,PPO):
                self.learner.buffer=[];self.learner.pending=None;self.iterator=None
                self.learner.critic=random_weights(self.learner.rng,self.learner.hidden,1,inputs=self.learner.inputs)
                self.learner.critic_adam=Adam(len(self.learner.critic))
            self.reset_episodes()

    def accept_evo_check(self):
        from game_evo_plan import CHECK_VERSION
        ev=self.evaluation;candidate,_=ev.results()
        self.state['evaluations']=(self.state['evaluations']+[dict(round=self.state['round'],phase=self.phase,
            rewardVersion=self.state['rewardVersion'],evaluationVersion=CHECK_VERSION,scenarios=ev.scenarios,
            candidateHash=digest(ev.candidate),candidate=candidate,champion=None,promoted=False,
            scope=scope_hash(self.track_id,self.profile['observation']),stage=self.evo_plan.data['level'],
            stageLabel=ev.scenarios[0]['scenario']['label'],initialSpeedKmh=ev.scenarios[0]['scenario']['speed']*3.6)])[-40:]
        advanced=self.evo_plan.accept(candidate)
        self.evaluation=None;self.state['pending']=None
        if advanced:
            self.state['phaseUpdates']=0
            if self.evo_plan.graduated:
                contexts=[{k:c[k] for k in ('track','phase','configuration','contextHash') if k in c} for c in self.memory.get('coverage',[])]
                for phase in ('launch','control'):
                    if not any(c['track']==self.track_id and c['phase']==phase for c in contexts):contexts.append(dict(track=self.track_id,phase=phase))
                self.review=driving_memory.Review(ev.candidate,self.memory.get('baseline'),contexts,self.memory.get('reviewRevision',0))
            self.reset_episodes()

    @property
    def activity(self):
        if self.review:return 'familiarizzazione' if self.review.kind=='familiarization' else 'consolidamento'
        if self.evaluation:return 'valutazione'
        if self.replay_context:return 'ripasso'
        return 'aggiornamento' if self.iterator else 'raccolta'

    def accept_review(self):
        from game_driving_memory import Review
        result=self.review.result();self.review=None
        if result['kind']=='familiarization':
            phase=result['coverage'][0]['phase']
            self.memory.setdefault('familiarization',[]).append({k:v for k,v in result.items() if k!='policy'})
            next_phase=({'launch':'bend','bend':'control','control':'recovery','recovery':'pace'} if self.balanced else {'launch':'control','control':'recovery','recovery':'pace'})[phase]
            self.state['phase']=next_phase if result['passed'] else phase
            if result['passed']:
                self.state['launchGoal']=20.
                if self.balanced and phase=='bend':self.state['curveReady']=True
                if phase!='recovery':self.review=Review(result['policy'],None,[dict(track=self.track_id,phase=next_phase)],0,'familiarization')
            if self.review is None:self.memory['familiarized']=True;self.memory['fresh']=False
            self.reset_episodes()
        else:
            self.memory_reviews=(self.memory_reviews+[result])[-20:]
            if self.balanced and self.objective!='impara':
                solo=[c for c in result['coverage'] if c['track']==self.track_id and c['phase']=='control']
                reliable=bool(solo) and all(c['result']['valid']>=18 for c in solo) and result['passed']
                self.state['continuousReliable']=self.state.get('continuousReliable',0)+1 if reliable else 0
                if self.state['continuousReliable']>=2:
                    self.state['curveReady']=True
                    self.state['pacePressure']=min(1.,self.state['pacePressure']+.125)
                elif not reliable:self.state['pacePressure']=max(0.,self.state['pacePressure']-.125)
            if result['passed']:
                self.memory['coverage']=result['coverage'];self.memory['baseline']=result['policy']
                self.memory['reviewRevision']=result['revision']+1
                self.memory['status']=driving_memory.base_status(result['coverage'])

    def enable_collectors(self,count=2,persistent=False):
        if persistent:
            from game_parallel import PersistentEpisodePool as EpisodePool
        else:from game_collectors import EpisodePool
        if self.collectors is None:self.collectors=EpisodePool(count,batched=self.batched) if persistent else EpisodePool(count)
        if self.balanced:self.state['execution'].update(backend='persistent' if persistent else 'snapshot',collectors=count)

    @property
    def collecting(self):return bool(self.collectors and self.collectors.pending)

    def quiesce(self):
        if self.collecting:
            result=self.collectors.poll(timeout=5.)
            if result is None:raise RuntimeError('Collector non fermato')
            self.collected=result

    def close(self):
        if self.collectors:self.collectors.close();self.collectors=None

    @staticmethod
    def numeric_batch(saved):
        if saved is None:return None
        result={}
        for key,value in saved.items():
            result[key]=(np.asarray(value,dtype=bool if key in ('done','terminated','active') else float)
                         if isinstance(value,list) else deepcopy(value))
        return result

    def prepare_batch(self,obs,actions,raw,logp,values):
        n=len(obs)
        if self._buffers is None:
            self._buffers={'obs':np.empty_like(obs),'actions':np.empty_like(actions),
                'reward':np.zeros(n),'done':np.zeros(n,dtype=bool),'terminated':np.zeros(n,dtype=bool),
                'next':np.empty_like(obs),'active':np.zeros(n,dtype=bool),'teacher':np.zeros((n,2)),
                **{k:np.empty_like(v) if v is not None else None for k,v in (('raw',raw),('logp',logp),('values',values))}}
        b=self._buffers;b['cursor']=0
        for key,value in (('obs',obs),('actions',actions),('raw',raw),('logp',logp),('values',values),('next',obs)):
            if value is not None:b[key][:]=value
        for key in ('reward','done','terminated','teacher'):b[key][:]=0
        b['active'][:]=[not e.reason for e in self.episodes]
        return b

    def tick(self):
        if self.review:
            if self.balanced and not getattr(self.review,'native_sensors',False):
                for e in self.review.episodes:e.world.native_sensors=True
                self.review.native_sensors=True
            if self.review.tick():self.accept_review()
            return
        if self.evaluation:
            if self.balanced and not getattr(self.evaluation,'native_sensors',False):
                for e in self.evaluation.episodes:e.world.native_sensors=True
                self.evaluation.native_sensors=True
            start=time.monotonic();finished=self.evaluation.tick()
            self.state['evaluationSeconds']=self.state.get('evaluationSeconds',0)+time.monotonic()-start
            if finished:self.accept_evaluation()
            return
        if self.iterator is not None:
            try:self.metric=next(self.iterator)
            except StopIteration:self.iterator=None;self.schedule()
            return
        if self.inflight is None:
            if self.balanced and self.next_observations is not None:
                obs=self.next_observations;self.next_observations=None
            else:
                # Bound initial geometry work; subsequent balanced batches reuse
                # the exact post-step observation, never a stale/reset observation.
                e=self.episodes[len(self.observation_rows)]
                self.observation_rows.append(e.observations())
                if len(self.observation_rows)<len(self.episodes):return
                obs=np.array(self.observation_rows);self.observation_rows=[]
            if isinstance(self.learner,PPO):actions,raw,logp,values=self.learner.sample(obs)
            else:actions=self.learner.act(obs);raw=logp=values=None
            self.inflight=self.prepare_batch(obs,actions,raw,logp,values)
            if self.collectors:
                self.collectors.start(self.episodes,actions,self.profile['algorithm'],self.opponents)
            elif self.batched:self.physics_results=self.batch_physics.prepare(self.episodes,actions,self.profile['algorithm']=='ppo_smooth')
        if self.collecting:
            self.collected=self.collectors.poll()
            if self.collected is None:return
        batch=self.inflight;i=batch['cursor'];e=self.episodes[i]
        if not e.reason:
            if self.collected is not None:
                state,obs,r,done,terminated,teacher=self.collected[i]
                if state.get('packet'):
                    from game_parallel import apply_packet
                    apply_packet(e,state)
                else:e.restore(state)
                batch['teacher'][i]=teacher
            else:
                if isinstance(self.learner,Imitation):batch['teacher'][i]=e.teacher_actions() if self.balanced else racing_actions(e.world,[0])[0]
                obs,r,done,terminated=e.step(batch['actions'][i],self.profile['algorithm']=='ppo_smooth',
                    physics=self.physics_results[i] if self.physics_results else None)
            batch['reward'][i]=r;batch['done'][i]=done;batch['terminated'][i]=terminated;batch['next'][i]=obs
            self.steps+=1;self.record_episode(e)
        else:batch['done'][i]=True;batch['terminated'][i]=not e.truncated
        batch['cursor']+=1
        if batch['cursor']<len(self.episodes):return
        self.fitness+=batch['reward']
        if isinstance(self.learner,PPO):
            self.learner.remember(*[batch[k] for k in ('obs','raw','logp','values','reward','done','next','terminated')])
        elif isinstance(self.learner,Imitation):
            self.learner.learn_step(batch['obs'],batch['teacher'],batch['active'])
        self.inflight=None;self.collected=None;self.observation_rows=[];self.physics_results=None
        if self.balanced:self.next_observations=batch['next'].copy()
        if isinstance(self.learner,PPO) or isinstance(self.learner,Imitation):
            for index,e in enumerate(self.episodes):
                if e.reason:
                    if self.balanced:e.pace_pressure=self.state['pacePressure']
                    if self.objective=='impara' and not e.single_lap and e.spec['laps']>1:
                        self.episodes[index]=Episode(e.track_id,e.phase,int(self.rng.integers(1,90000)),self.opponents,protocol=self.protocol,context=e.context_config,single_lap=True)
                        continue
                    if e.reason=='window':e.next_window()
                    else:e.reset();e.recorded=False
                    if self.balanced:self.next_observations[index]=e.observations()
            if isinstance(self.learner,PPO) and len(self.learner.buffer)>=self.profile['rollout']:
                self.iterator=self.learner.updates()
            elif isinstance(self.learner,Imitation) and self.steps//(self.profile['population']*self.profile['rollout'])>self.state['updates']:
                self.metric=self.learner.update(self.fitness);self.fitness[:]=0;self.schedule()
        elif all(e.reason for e in self.episodes):
            if self.balanced:
                from game_rewards import reference_time
                unused_time=[]
                for i,e in enumerate(self.episodes):
                    adjustment=0.
                    if e.reason not in ('success','window'):
                        weight=self.reward_spec['timeControl']+(self.reward_spec['timePace']-self.reward_spec['timeControl'])*e.pace_pressure
                        adjustment=weight*max(0.,e.spec['limitSeconds']-(e.age-e.window_started))/reference_time(e.world,self.reward_spec)
                        self.fitness[i]-=adjustment
                    unused_time.append(adjustment)
            if self.evo_plan:
                suite=self.evo_plan.take_results(self.episodes,self.fitness)
                if suite is None:self.reset_episodes();return
                scores,ranks=suite
                self.metric=self.learner.update(scores,ranks)
                self.metric['selectionKind']='suite-success-retention-reward'
                self.evo_plan.save_archive(self.learner)
            else:self.metric=self.learner.update(self.fitness)
            if self.balanced:self.metric['selectionUnusedTime']=dict(mean=float(np.mean(unused_time)),max=max(unused_time))
            if self.evo_plan and not self.evo_plan.graduated:
                self.state['updates']+=1;self.state['phaseUpdates']+=1
                if self.evo_plan.should_check():
                    from game_evo_plan import EvoStageCheck
                    self.state['round']+=1
                    self.evaluation=EvoStageCheck(self.evo_plan,self.learner.candidate_policy())
            else:self.schedule()
            self.reset_episodes()
        if isinstance(self.learner,PPO):
            self.metric.update(rawStd=np.exp(self.learner.log_std).tolist(),
                entropy=float(np.sum(self.learner.log_std+.5*np.log(2*np.pi*np.e))))

    def checkpoint(self,seconds):
        self.quiesce()
        from game_parallel import durable_results as durable_collectors
        from game_batch import durable_results as durable_physics
        self.state['pending']=self.evaluation.snapshot() if self.evaluation else None
        result={'schema':2,'academyVersion':VERSION,'configuration':configuration(self.track_id,self.profile['observation']),
                'learner':self.learner.checkpoint(),'curriculum':deepcopy(self.state),
                'episodes':[e.snapshot() for e in self.episodes],'fitness':self.fitness.tolist(),
                'objective':self.objective,'bots':self.bots,'steps':self.steps,'seconds':seconds,'rng':deepcopy(self.rng.bit_generator.state),
                'observationRows':checkpoint_value(self.observation_rows),'collectorResults':durable_collectors(self.collected),'inflight':checkpoint_value(self.inflight),'metric':deepcopy(self.metric),
                'frozenOpponents':[deepcopy(p.snapshot) for p in self.opponents], 'task':self.task}
        if self.modern:
            result.update(schema=3,protocol=self.protocol,memory=deepcopy(self.memory),memoryReview=self.review.snapshot() if self.review else None,
                memoryReviews=deepcopy(self.memory_reviews),visibleEpisodes=[e.snapshot() for e in self.display_episodes] if self.replay_context else None,replayContext=deepcopy(self.replay_context),
                visibleGeneration=self.display_generation,rewardContext=self.reward_context,tuning=getattr(self.learner,'tuning',{}),contextHash=scope_hash(self.track_id,self.profile['observation']))
        if self.balanced:
            result.update(rewardSpec=deepcopy(self.reward_spec),rewardMigration=self.migration,
                          sourceCheckpoint=self.source_checkpoint,physicsResults=durable_physics(self.physics_results))
        return result

    def prepare_preview(self):
        if self.preview is None:
            self.preview_revision+=1
            phase='overtake' if self.objective=='impara_sorpasso' else 'control'
            self.preview=Episode(self.track_id,phase,self.profile['seed']+500000,self.opponents,
                protocol=self.protocol,objective=self.objective,bots=self.bots,single_lap=True)
            self.preview.world.native_sensors=self.balanced
            self.preview.world.telemetry=True;self.preview.world.reset(varied=False);self.preview.reset()
            self.preview_remaining=0.;self.preview_hold=0.;self.last_preview=time.monotonic()
            self.preview_policy=None
        # Freeze each watched attempt. A policy update cannot teleport/control-jump it.
        if self.preview_policy is None:
            self.preview_policy=Policy(self.learner.candidate_policy() if hasattr(self.learner,'candidate_policy') else self.learner.policy())

    def advance_preview(self):
        if self.view=='attempts' and self.profile['algorithm'] in ('evolution','neat'):return
        self.prepare_preview()
        now=time.monotonic();elapsed=min(.1,max(0,now-self.last_preview));self.last_preview=now
        if self.preview.reason:
            if self.preview.reason=='window':
                self.preview.next_window();self.preview_policy=None;self.prepare_preview()
            else:
                self.preview_hold+=elapsed
                if self.preview_hold>=1.5:
                    self.preview.reset();self.preview_hold=0.;self.preview_remaining=0.;self.preview_policy=None
                    self.prepare_preview()
                return
        self.preview_remaining=min(.1,self.preview_remaining+elapsed)
        # Bounded catch-up at unchanged DT; yields to commands after this call.
        for _ in range(min(4,int(self.preview_remaining/DT))):
            e=self.preview
            if e.reason:break
            e.step(self.preview_policy.act(e.observations(),world=e.world,index=0))
            self.preview_remaining-=DT

    def rates(self,rows):
        now=time.monotonic()
        for row in rows:
            key=row.get('resetKey',row['id']);sim=row.get('simulatedTime',0.)
            previous=self.rate_samples.get(row['id'])
            rate=None
            if previous and previous[0]==key and now-previous[1]>=.5:
                rate=max(0.,(sim-previous[2])/(now-previous[1]))
                self.rate_samples[row['id']]=(key,now,sim,rate)
            elif previous and previous[0]==key:rate=previous[3]
            else:self.rate_samples[row['id']]=(key,now,sim,None)
            row['simRate']=rate
        self.rate_samples={k:v for k,v in self.rate_samples.items() if k in {r['id'] for r in rows}}

    def frame(self,name,number,selected,paused=False):
        if self.view=='attempts' and self.profile['algorithm'] in ('evolution','neat'):
            return self.population_frame(name,selected)
        self.prepare_preview()
        if paused:self.last_preview=time.monotonic()
        e=self.preview;w=e.world;rows=w.rows()
        for i,row in enumerate(rows):
            row.update(cleanSeries=e.clean_series,bestSeries=e.best_series,passes=e.passes,passAttempts=e.pass_attempts)
            row.update(id='preview' if i==0 else 'preview-rival-'+str(i),
                name=name if i==0 else 'Bot '+str(i),number=number if i==0 else i,
                resetKey=str(self.preview_revision)+':'+str(e.revision),simulatedTime=w.time,
                completed=bool(e.reason) and e.reason!='window',result=e.reason)
        self.rates(rows);selected%=len(rows)
        meta={'driverName':name,'algorithm':self.profile['algorithm'],'count':len(rows),'selected':selected,
              'steps':self.steps,'metric':deepcopy(self.metric),'phase':self.activity,
              'curriculumPhase':LABELS[self.phase],'exercise':'Pilota · dimostrazione',
              'trainingExercise':self.task['label'],'objective':self.objective,
              'evaluationRound':self.state['round'],'presentation':'preview','trainingCount':self.profile['population'],
              'previewState':e.reason or 'running','time':w.time,'sensorRange':150,
              'trainingGoalMeters':self.task['distance'],'learningStats':deepcopy(self.state['stats'])}
        if self.balanced:meta.update(rewardVersion=self.reward_spec['version'],execution=deepcopy(self.state['execution']),pacePressure=self.state['pacePressure'])
        if self.evo_v2:
            from game_evo_plan import progress_meta
            meta['epochProgress']=progress_meta(self.state,self.task,self.track_id,self.steps)
            if self.evo_plan:meta['evoTraining']=self.evo_plan.meta()
        check=self.review or self.evaluation
        if check:meta.update(activityDone=sum(bool(x.reason) and x.reason!='not_run' for x in check.episodes),activityTotal=len(check.episodes))
        return rows,e.observations() if selected==0 else w.observations(version=self.profile['observation'])[selected],meta

    def verification_frame(self,name,number,selected,check,index):
        e=check.episodes[index];rows=e.world.rows();selected%=len(rows)
        for i,row in enumerate(rows):row.update(id='verification-'+str(index)+'-'+str(i),name=name if i==0 else 'Rivale '+str(i),number=number if i==0 else i)
        meta=dict(driverName=name,algorithm=self.profile['algorithm'],count=len(rows),selected=selected,
            steps=self.steps,metric=deepcopy(self.metric),phase=self.activity,curriculumPhase=LABELS[self.phase],
            exercise=LABELS[e.phase],presentation='verification',trainingCount=self.profile['population'],
            generation=getattr(self.learner,'generation',0)+1,time=e.world.time,sensorRange=150,
            activityDone=sum(bool(x.reason) and x.reason!='not_run' for x in check.episodes),activityTotal=len(check.episodes))
        return rows,e.world.observations(version=self.profile['observation'])[selected],meta

    def population_frame(self,name,selected):
        """Actual independent learner episodes, never a shared race or preview.

        Publication consumes no learning RNG, physics steps or policy refresh.
        Completed attempts stay on track until the next population is created.
        """
        generation=self.display_generation if self.replay_context else self.learner.generation+1
        visible=self.display_episodes if self.replay_context else self.episodes
        selected%=len(visible)
        rows=[]
        for i,e in enumerate(visible):
            row=e.world.rows()[0]
            row.update(id='generation-'+str(generation)+'-attempt-'+str(i),
                       name=name,number=i+1,attempt=i+1,completed=bool(e.reason),
                       result=e.reason,position=None,resetKey=str(self.population_revision)+':'+str(e.seed)+':'+str(e.revision),simulatedTime=e.world.time)
            if e.reason and not e.world.retired[0]:row['status']='concluso'
            rows.append(row)
        e=visible[selected]
        # Traffic belongs to this attempt's independent world. Only its
        # frozen rivals are shown; other attempts never collide with them.
        for i,row in enumerate(e.world.rows()[1:],1):
            row.update(id='attempt-'+str(selected)+'-rival-'+str(i),
                       name='Rivale '+str(i),number=i,contextRival=True)
            rows.append(row)
        self.rates(rows)
        meta={'driverName':name,'algorithm':self.profile['algorithm'],
              'count':len(visible),'selected':selected,'steps':self.steps,
              'metric':deepcopy(self.metric),'generation':generation,
              'completedAttempts':sum(bool(e.reason) for e in visible),
              'phase':self.activity,
              'curriculumPhase':LABELS[self.phase],
              'exercise':e.spec['label'],
              'evaluationRound':self.state['round'],'presentation':'population',
              'trainingCount':len(visible),'time':e.world.time,'sensorRange':150,
              'trainingGoalMeters':e.spec['distance'],
              'learningStats':{k:self.state['stats'].get(k,0) for k in ('episodes','success','no_progress','passes','launches','launchSuccess','warmups','warmupSuccess')}}
        if self.balanced:meta.update(rewardVersion=self.reward_spec['version'],execution=deepcopy(self.state['execution']),pacePressure=self.state['pacePressure'])
        if self.evo_v2:
            from game_evo_plan import progress_meta
            meta['epochProgress']=progress_meta(self.state,self.task,self.track_id,self.steps)
            if self.evo_plan:meta['evoTraining']=self.evo_plan.meta()
        check=self.review or self.evaluation
        if check:meta.update(activityDone=sum(bool(x.reason) and x.reason!='not_run' for x in check.episodes),activityTotal=len(check.episodes))
        return rows,e.observations(),meta
