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
    def __init__(self,profile,track_id,checkpoint=None,opponents=()):
        self.profile,self.track_id=profile,track_id
        checkpoint=checkpoint or {}
        if checkpoint and checkpoint.get('configuration')!=configuration(track_id,profile['observation']):
            raise ValueError('Checkpoint fisico Accademia incompatibile')
        from game_driving_memory import PROTOCOL,PHASES as MEMORY_PHASES,Review
        self.protocol=checkpoint.get('protocol')
        self.modern=self.protocol==PROTOCOL;self.phases=MEMORY_PHASES if self.modern else PHASES
        self.memory=deepcopy(checkpoint.get('memory') or {});self.review=None;self.memory_reviews=deepcopy(checkpoint.get('memoryReviews',[]))
        self.display_episodes=[];self.display_generation=0;self.replay_context=None;self.reward_context=checkpoint.get('rewardContext')
        backend=checkpoint.get('learner')
        cls={'evolution':Evolution,'ppo':PPO,'ppo_smooth':PPOSmooth,'imitation':Imitation}.get(profile['algorithm'])
        if cls is None:
            from game_neat import NEAT
            cls=NEAT
        self.learner=cls(profile,backend)
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
        if self.modern:self.state.update(protocol=self.protocol,rewardVersion=driving_memory.REWARD)
        self.state['stats'].setdefault('recoveries',0);self.state['stats'].setdefault('recoverySuccess',0)
        self.state['stats'].setdefault('recoveryTimes',[])
        self.state['stats'].setdefault('warmups',0);self.state['stats'].setdefault('warmupSuccess',0)
        self.state.setdefault('launchGoal',1.);self.state.setdefault('launchWindow',[])
        if self.state.get('academyVersion')!=VERSION:raise ValueError('Curriculum Accademia incompatibile')
        snapshots=checkpoint.get('frozenOpponents')
        self.opponents=[Policy(p) for p in snapshots] if snapshots is not None else list(opponents)
        self.episodes=[];self.fitness=np.zeros(profile['population']);self.inflight=None;self._buffers=None
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
        pending=self.state.get('pending')
        if pending:
            self.evaluation=SkillEvaluation(pending['candidate'],pending['champion'],pending['phase'],
                track_id,pending['round'],self.opponents,pending)
        if isinstance(self.learner,PPO) and self.learner.pending is not None:self.iterator=self.learner.updates()
        visible=checkpoint.get('visibleEpisodes')
        if visible:self.display_episodes=[Episode(s['track_id'],s['phase'],s['seed'],self.opponents,s) for s in visible]
        else:self.display_episodes=[e for e in self.episodes if e.track_id==track_id]
        self.display_generation=checkpoint.get('visibleGeneration',getattr(self.learner,'generation',0)+1)
        self.replay_context=checkpoint.get('replayContext')
        saved_review=checkpoint.get('memoryReview')
        if saved_review:self.review=Review(saved_review['candidate'],saved_review['baseline'],saved_review['contexts'],saved_review['revision'],saved_review['kind'],saved_review)
        elif self.modern and self.memory.get('fresh') and not self.memory.get('familiarized'):
            policy=self.learner.policy()
            self.review=Review(policy,None,[dict(track=track_id,phase='launch')],0,'familiarization')

    @property
    def phase(self):return self.state['phase']

    @property
    def task(self):
        spec=driving_memory.task(self.track_id,self.phase) if self.modern else task_spec(self.track_id,self.phase)
        if self.phase=='launch':spec={**spec,'distance':self.launch_goal,'label':'Partenza · '+str(int(self.launch_goal))+' m'}
        return spec

    @property
    def launch_goal(self):return self.state['launchGoal']

    def reset_episodes(self):
        if self.modern and self.episodes:
            visible=[e for e in self.episodes if e.track_id==self.track_id]
            if visible:self.display_episodes=visible;self.display_generation=max(1,getattr(self.learner,'generation',0))
        self.episodes=[];common=self.phase;self.replay_context=None
        evolutionary=isinstance(self.learner,Evolution) or self.profile['algorithm']=='neat'
        coverage=[c for c in self.memory.get('coverage',[]) if c['track']!=self.track_id]
        if evolutionary and self.state['updates']%5==4 and self.phase!='launch':
            if self.modern and coverage:self.replay_context=coverage[(self.state['updates']//5)%len(coverage)];common=self.replay_context['phase']
            else:common='pace' if self.phase in TRAFFIC else 'launch'
        seed=int(self.rng.integers(1,90000)) if self.modern and evolutionary else None
        for i in range(self.profile['population']):
            phase=common;track=self.track_id
            if self.replay_context:track=self.replay_context['track']
            if (isinstance(self.learner,PPO) or isinstance(self.learner,Imitation)) and i%5==4 and self.phase!='launch':
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
                launch_distance=self.launch_goal if phase=='launch' else None,protocol=self.protocol,context=context))
        if self.modern and evolutionary:
            context=(self.episodes[0].track_id,common,self.launch_goal if common=='launch' else None)
            if self.reward_context is not None and tuple(self.reward_context)!=context:self.learner.change_reward()
            self.reward_context=context
        if not self.replay_context:self.display_episodes=[e for e in self.episodes if e.track_id==self.track_id]
        self.fitness[:]=0;self.inflight=None;self._buffers=None

    def record_episode(self,e):
        if not e.reason or getattr(e,'recorded',False):return
        e.recorded=True;row=e.result();stats=self.state['stats']
        stats['episodes']+=1;stats[e.reason]+=1;stats['passes']+=row['passes']
        stats['stationarySeconds']+=row['stationarySeconds'];stats['simulatedSeconds']+=e.age
        if e.phase=='recovery':
            stats['recoveries']+=1;stats['recoverySuccess']+=int(e.reason=='success')
            if row['reentryTime'] is not None:stats['recoveryTimes']=(stats['recoveryTimes']+[row['reentryTime']])[-256:]
        if e.phase=='launch':
            if e.spec['distance']==20:stats['launches']+=1;stats['launchSuccess']+=int(e.reason=='success')
            else:stats['warmups']+=1;stats['warmupSuccess']+=int(e.reason=='success')
            if e.spec['distance']==self.launch_goal:self.state['launchWindow']=(self.state['launchWindow']+[int(e.reason=='success')])[-32:]
        for field,name in (('firstMeter','firstMeterTimes'),('tenMeters','tenMeterTimes')):
            if row[field] is not None:stats[name]=(stats[name]+[row[field]])[-256:]
        for name,value in row['rewardTerms'].items():stats['rewardTerms'][name]=stats['rewardTerms'].get(name,0)+value

    def schedule(self):
        old_goal=self.launch_goal
        self.state['updates']+=1;self.state['phaseUpdates']+=1
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
            self.state['phase']=self.phases[self.phases.index(self.phase)+1]
            self.state['reliableWindows']=0;self.state['phaseUpdates']=0
            if hasattr(self.learner,'change_reward'):self.learner.change_reward()
            if isinstance(self.learner,PPO):
                self.learner.buffer=[];self.learner.pending=None;self.iterator=None
                self.learner.critic=random_weights(self.learner.rng,self.learner.hidden,1,inputs=self.learner.inputs)
                self.learner.critic_adam=Adam(len(self.learner.critic))
            self.reset_episodes();self.preview=None

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
            next_phase={'launch':'control','control':'recovery','recovery':'pace'}[phase]
            self.state['phase']=next_phase if result['passed'] else phase
            if result['passed']:
                self.state['launchGoal']=20.
                if phase!='recovery':self.review=Review(result['policy'],None,[dict(track=self.track_id,phase=next_phase)],0,'familiarization')
            if self.review is None:self.memory['familiarized']=True;self.memory['fresh']=False
            self.reset_episodes();self.preview=None
        else:
            self.memory_reviews=(self.memory_reviews+[result])[-20:]
            if result['passed']:
                self.memory['coverage']=result['coverage'];self.memory['baseline']=result['policy']
                self.memory['reviewRevision']=result['revision']+1
                self.memory['status']=driving_memory.base_status(result['coverage'])

    def enable_collectors(self,count=2):
        from game_collectors import EpisodePool
        if self.collectors is None:self.collectors=EpisodePool(count)

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
            if self.review.tick():self.accept_review()
            return
        if self.evaluation:
            start=time.monotonic();finished=self.evaluation.tick()
            self.state['evaluationSeconds']=self.state.get('evaluationSeconds',0)+time.monotonic()-start
            if finished:self.accept_evaluation()
            return
        if self.iterator is not None:
            try:self.metric=next(self.iterator)
            except StopIteration:self.iterator=None;self.schedule()
            return
        if self.inflight is None:
            obs=np.array([e.observations() for e in self.episodes])
            if isinstance(self.learner,PPO):actions,raw,logp,values=self.learner.sample(obs)
            else:actions=self.learner.act(obs);raw=logp=values=None
            self.inflight=self.prepare_batch(obs,actions,raw,logp,values)
            if self.collectors:
                self.collectors.start(self.episodes,actions,self.profile['algorithm'],self.opponents)
        if self.collecting:
            self.collected=self.collectors.poll()
            if self.collected is None:return
        batch=self.inflight;i=batch['cursor'];e=self.episodes[i]
        if not e.reason:
            if self.collected is not None:
                state,obs,r,done,terminated,teacher=self.collected[i]
                e.restore(state);batch['teacher'][i]=teacher
            else:
                if isinstance(self.learner,Imitation):batch['teacher'][i]=racing_actions(e.world,[0])[0]
                obs,r,done,terminated=e.step(batch['actions'][i],self.profile['algorithm']=='ppo_smooth')
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
        self.inflight=None;self.collected=None
        if isinstance(self.learner,PPO) or isinstance(self.learner,Imitation):
            for e in self.episodes:
                if e.reason:e.reset();e.recorded=False
            if isinstance(self.learner,PPO) and len(self.learner.buffer)>=self.profile['rollout']:
                self.iterator=self.learner.updates()
            elif isinstance(self.learner,Imitation) and self.steps//(self.profile['population']*self.profile['rollout'])>self.state['updates']:
                self.metric=self.learner.update(self.fitness);self.fitness[:]=0;self.schedule()
        elif all(e.reason for e in self.episodes):
            self.metric=self.learner.update(self.fitness);self.schedule();self.reset_episodes()
        if isinstance(self.learner,PPO):
            self.metric.update(rawStd=np.exp(self.learner.log_std).tolist(),
                entropy=float(np.sum(self.learner.log_std+.5*np.log(2*np.pi*np.e))))

    def checkpoint(self,seconds):
        self.quiesce()
        self.state['pending']=self.evaluation.snapshot() if self.evaluation else None
        result={'schema':2,'academyVersion':VERSION,'configuration':configuration(self.track_id,self.profile['observation']),
                'learner':self.learner.checkpoint(),'curriculum':deepcopy(self.state),
                'episodes':[e.snapshot() for e in self.episodes],'fitness':self.fitness.tolist(),
                'steps':self.steps,'seconds':seconds,'rng':deepcopy(self.rng.bit_generator.state),
                'collectorResults':checkpoint_value(self.collected),'inflight':checkpoint_value(self.inflight),'metric':deepcopy(self.metric),
                'frozenOpponents':[deepcopy(p.snapshot) for p in self.opponents], 'task':self.task}
        if self.modern:
            result.update(schema=3,protocol=self.protocol,memory=deepcopy(self.memory),memoryReview=self.review.snapshot() if self.review else None,
                memoryReviews=deepcopy(self.memory_reviews),visibleEpisodes=[e.snapshot() for e in self.display_episodes] if self.replay_context else None,replayContext=deepcopy(self.replay_context),
                visibleGeneration=self.display_generation,rewardContext=self.reward_context,tuning=getattr(self.learner,'tuning',{}),contextHash=scope_hash(self.track_id,self.profile['observation']))
        return result

    def prepare_preview(self):
        if self.preview is None:
            self.preview=Episode(self.track_id,self.phase,self.profile['seed']+500000,self.opponents)
            self.preview_remaining=0.;self.preview_hold=0.;self.last_preview=time.monotonic()
        now=time.monotonic()
        if self.preview_policy is None or now-self.last_preview_policy>=1/25:
            self.preview_policy=Policy(self.learner.candidate_policy() if hasattr(self.learner,'candidate_policy') else self.learner.policy())
            self.last_preview_policy=now

    def advance_preview(self):
        """One physical step between command polls; publishing never catches up.

        Independent from training/evaluation RNG and fixed at DT. A late loop
        keeps a bounded preview backlog rather than blocking scene publication.
        """
        if self.profile['algorithm'] in ('evolution','neat'):return
        self.prepare_preview()
        now=time.monotonic();elapsed=min(.1,max(0,now-self.last_preview));self.last_preview=now
        if self.preview.reason:
            self.preview_hold+=elapsed
            if self.preview_hold>=1.:
                self.preview.reset();self.preview_hold=0.;self.preview_remaining=0.
            return
        self.preview_remaining=min(.1,self.preview_remaining+elapsed)
        if self.preview_remaining>=DT:
            e=self.preview;e.step(self.preview_policy.act(e.observations(),world=e.world,index=0))
            self.preview_remaining-=DT

    def frame(self,name,number,selected,paused=False):
        if self.profile['algorithm'] in ('evolution','neat'):
            check=self.review or self.evaluation
            if self.modern and check:
                index=(check.cursor-1)%len(check.episodes);e=check.episodes[index]
                if e.track_id==self.track_id:return self.verification_frame(name,number,selected,check,index)
            return self.population_frame(name,selected)
        self.prepare_preview()
        if paused:self.last_preview=time.monotonic()
        w=self.preview.world;rows=w.rows()
        for i,row in enumerate(rows):row.update(id='preview' if i==0 else 'preview-rival-'+str(i),name=name if i==0 else 'Rivale '+str(i),number=number if i==0 else i+number)
        selected%=len(rows)
        meta={'driverName':name,'algorithm':self.profile['algorithm'],'count':len(rows),'selected':selected,
              'steps':self.steps,'metric':deepcopy(self.metric),'phase':self.activity,
              'curriculumPhase':LABELS[self.phase],'exercise':LABELS[self.preview.phase],
              'evaluationRound':self.state['round'],'presentation':'preview','trainingCount':self.profile['population'],
              'previewState':{'success':'Esercizio completato','no_progress':'Nuovo tentativo','contact':'Ripartenza','timeout':'Nuovo tentativo','blocked':'Traffico fermo','skill_failed':'Nuovo tentativo'}.get(self.preview.reason,'running'),'time':w.time,'sensorRange':150,
              'trainingGoalMeters':self.task['distance'],
              'learningStats':{k:self.state['stats'].get(k,0) for k in ('episodes','success','no_progress','passes','launches','launchSuccess','warmups','warmupSuccess')}}
        return rows,w.observations(version=self.profile['observation'])[selected],meta

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
                       result=e.reason,position=None)
            rows.append(row)
        e=visible[selected]
        # Traffic belongs to this attempt's independent world. Only its
        # frozen rivals are shown; other attempts never collide with them.
        for i,row in enumerate(e.world.rows()[1:],1):
            row.update(id='attempt-'+str(selected)+'-rival-'+str(i),
                       name='Rivale '+str(i),number=i,contextRival=True)
            rows.append(row)
        meta={'driverName':name,'algorithm':self.profile['algorithm'],
              'count':len(visible),'selected':selected,'steps':self.steps,
              'metric':deepcopy(self.metric),'generation':generation,
              'completedAttempts':sum(bool(e.reason) for e in visible),
              'phase':self.activity,
              'curriculumPhase':LABELS[self.phase],
              'exercise':LABELS[e.phase]+(' · '+str(int(e.spec['distance']))+' m' if e.phase=='launch' else ''),
              'evaluationRound':self.state['round'],'presentation':'population',
              'trainingCount':len(visible),'time':e.world.time,'sensorRange':150,
              'trainingGoalMeters':e.spec['distance'],
              'learningStats':{k:self.state['stats'].get(k,0) for k in ('episodes','success','no_progress','passes','launches','launchSuccess','warmups','warmupSuccess')}}
        check=self.review or self.evaluation
        if check:meta.update(activityDone=sum(bool(x.reason) and x.reason!='not_run' for x in check.episodes),activityTotal=len(check.episodes))
        return rows,e.observations(),meta
