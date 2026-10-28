"""One pilot learns; each visible lap tests a frozen snapshot of its candidate."""
from copy import deepcopy
import math
import time
import hashlib
from pathlib import Path
import numpy as np
from game_academy import Episode
from game_residual import profile as make_profile,recipe,legacy_recipe,snapshot,features,value_features,learning_potential,controls,key,DECISION_STEPS
from game_residual_learning import ResidualPPO,OffPolicy
from game_learning import Policy,PPO
from game_catalog import configuration,scope_hash
from game_rewards import specification


def reward_profile(policy):
    result={'algorithm':policy['algorithm']}
    if policy.get('kind')=='direct':result['controlMode']='direct'
    if policy.get('recipe',{}).get('reward')=='direct-driving-3':result['racingObjective']='valid-time-1'
    if policy.get('recipe',{}).get('trafficLearning')=='attack-1':
        result.update(racingObjective='valid-time-1',trafficLearning='attack-1',relativeAdvantage=policy['recipe']['relativeAdvantage'])
    if policy.get('recipe',{}).get('reward')=='residual-racing-2':result['rewardExperiment']='common-units-1'
    elif policy.get('recipe',{}).get('reward')=='residual-racing-1':result['rewardExperiment']='legacy-1'
    return result


def verification_key(policy,track,cases):
    # The key covers implementation, policy/base, physics, rules and exact bank.
    files=('game_residual.py','game_control.py','game_simulation.py','game_academy.py',
        'game_racecraft.py','game_rewards.py','game_geometry.py','game_contacts.py','game_residual_trainer.py','game_catalog.py',
        'game_learning.py','game_residual_learning.py','game_numeric.py','game_native.py','game_direct.py','game_direct_trainer.py',
        'game_school_lessons.py','game_driving_school.py','game_neural_mixture.py','game_racing_objective.py','game_racing_learning.py','game_racing_presets.py','game_overtaking.py')
    if not hasattr(verification_key,'code'):
        import platform
        optional=('game_native.c','libsmartpc_game_native.so')
        sources={f:hashlib.sha256(Path(__file__).with_name(f).read_bytes()).hexdigest() for f in files}
        for f in optional:
            path=Path(__file__).with_name(f);sources[f]=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
        verification_key.code=key(dict(sources=sources,numpy=np.__version__,python=platform.python_version(),architecture=platform.machine()))
    return key(dict(code=verification_key.code,policy=policy,configuration=configuration(track,policy['observation']),
        cases=cases,reward=specification(reward_profile(policy)),bank='skill-gates-3'))


class ResidualCheck:
    def __init__(self,candidate,champion,track,saved=None,cache=None):
        self.candidate=deepcopy(candidate);self.champion=deepcopy(champion);self.track=track
        self.policies=[Policy(candidate),Policy(champion)];self.cursor=0
        cases=[('pace',91001),('pace',91002),('pace',91003)]
        if candidate['algorithm']=='residual_tactic':cases += [('overtake',s) for s in (93101,93102)]+[('corner',s) for s in (93201,93202,93203,93204)]+[('defend',s) for s in (93301,93302)]
        self.episodes=[Episode(track,phase,seed,protocol='driving-memory-1',single_lap=True,reward_spec={**specification(reward_profile(candidate)),'evaluationRules':'spatial-rules-2'})
                       for phase,seed in cases*2]
        self.cache=cache if cache is not None else {}
        self.cases=cases;self.reused=0
        cached=self.cache.get(verification_key(champion,track,cases))
        if cached and len(cached)==len(cases):
            self.episodes[len(cases):]=[Episode(track,s['phase'],s['seed'],saved=s) for s in cached]
            self.reused=len(cases)
        if saved:
            self.reused=saved.get('reused',0)
            self.cursor=saved['cursor']
            self.episodes=[Episode(track,s['phase'],s['seed'],saved=s) for s in saved['episodes']]

    def tick(self):
        for _ in self.episodes:
            i=self.cursor%len(self.episodes);self.cursor+=1;e=self.episodes[i]
            if e.reason:continue
            e.step(self.policies[i//(len(self.episodes)//2)].act(None,world=e.world,index=0),return_observation=False);break
        return all(e.reason for e in self.episodes)

    def result(self):
        def collect(rows):
            times=[e.age for e in rows if e.reason=='success']
            return dict(valid=len(times),total=len(rows),best=min(times) if times else None,median=float(np.median(times)) if times else None,
                results=[e.result() for e in rows])
        half=len(self.episodes)//2
        if not all(e.reason for e in self.episodes):raise ValueError('Verifica incompleta')
        for policy,rows in ((self.candidate,self.episodes[:half]),(self.champion,self.episodes[half:])):
            self.cache[verification_key(policy,self.track,self.cases)]=[e.snapshot() for e in rows]
        while len(self.cache)>4:self.cache.pop(next(iter(self.cache)))
        candidate,champion=collect(self.episodes[:3]),collect(self.episodes[half:half+3])
        traffic=sum(e.reason=='success' for e in self.episodes[3:half])
        retained=sum(e.reason=='success' for e in self.episodes[half+3:])
        regressions=[dict(phase=a.phase,seed=a.seed) for a,b in zip(self.episodes[3:half],self.episodes[half+3:]) if (b.reason=='success' and a.reason!='success') or (not b.contact_count and a.contact_count) or (not b.world.track_limits[0] and a.world.track_limits[0])]
        accepted=candidate['valid']==3 and not regressions and traffic>=retained and (champion['valid']<3 or candidate['median']<champion['median']*.999 or (traffic>retained and candidate['median']<=champion['median']*1.005))
        candidate['trafficValid']=traffic;champion['trafficValid']=retained
        if half>3:
            for result,episodes in ((candidate,self.episodes[3:half]),(champion,self.episodes[half+3:])):
                result['trafficResults']=[e.result() for e in episodes]
                result['skills']={phase:dict(valid=sum(e.reason=='success' for e in episodes if e.phase==phase),total=sum(e.phase==phase for e in episodes),tested=sum(e.phase==phase for e in episodes)) for phase in {e.phase for e in episodes}}

        candidate['retained']=accepted
        decision='improved' if accepted else 'solo_invalid' if candidate['valid']<3 else 'safety_regression' if regressions else 'traffic_regression' if traffic<retained else 'no_gain'
        decision_label=dict(improved='Miglioramento verificato',solo_invalid='Giri puliti insufficienti',
            safety_regression='Peggiora una prova o la sicurezza',traffic_regression='Peggiora nel traffico',
            no_gain='Guida valida · nessun guadagno misurato')[decision]
        return dict(rewardVersion=candidate.get('rewardVersion',self.candidate['recipe']['reward']),raceRulesVersion='spatial-rules-2',decision=decision,decisionLabel=decision_label,evaluationVersion='skill-gates-3',reusedChampionCases=self.reused,regressions=regressions,phase='pace',stageLabel='Giri e duelli · confronto col campione' if half>3 else 'Tre giri puliti · confronto col campione',candidate=candidate,champion=champion,accepted=accepted,policyHash=key(self.candidate))

    def snapshot(self):
        return dict(version='skill-gates-3',reused=self.reused,candidate=self.candidate,champion=self.champion,track=self.track,cursor=self.cursor,
                    episodes=[e.snapshot() for e in self.episodes])


class ResidualTrainer:
    protocol='race-residual-1'
    collecting=False
    migration=None
    memory={}
    recipe = staticmethod(recipe)
    observe = staticmethod(features)
    drive = staticmethod(controls)
    reward = staticmethod(specification)

    def make_learner(self, profile, checkpoint):
        return (ResidualPPO if profile['algorithm']=='residual_ppo' else OffPolicy)(profile, checkpoint)

    def initial_policy(self, profile, checkpoint):
        from game_residual import initial_weights
        return snapshot(profile, initial_weights(profile))

    def __new__(cls,profile,*args,**kwargs):
        # Keep the shared public entry point safe: a direct profile must never
        # accidentally run the legacy line/pace observation/action adapters.
        if cls is ResidualTrainer and profile.get('controlMode')=='direct':
            from game_direct_trainer import DirectTrainer
            return object.__new__(DirectTrainer)
        return object.__new__(cls)

    def __init__(self,profile,track_id,checkpoint=None,opponents=(),objective='impara',view='pilot',bots=2,**kwargs):
        self.profile=deepcopy(profile);self.track_id=track_id;self.objective=objective;self.bots=bots
        self.source_checkpoint=(checkpoint or {}).get('sourceCheckpoint');self.spec=self.recipe(profile)
        self.reward_spec=self.reward(profile)
        c=deepcopy(checkpoint or {})
        saved_recipe=(c.get('curriculum') or {}).get('effectiveParameters')
        migrated=None
        if saved_recipe and saved_recipe!=self.spec:
            # Only the known reward/cutoff/rules revision is compatible. Never
            # reinterpret old replay targets, optimizers or an unfinished proof.
            if self.spec['version'] not in ('race-residual-3','race-residual-4'):raise ValueError('Ricetta sperimentale non promossa: originale conservato')
            old_expected=legacy_recipe(profile)
            if saved_recipe!=old_expected:raise ValueError('Ricetta di apprendimento incompatibile: serve un nuovo percorso')
            self.source_checkpoint=c.get('migrationSource') or self.source_checkpoint
            migrated=c.pop('learner',None)
            for field in ('episode','preview','previewPolicy','previewTrial','previewUpdate','inflight','check','metric'):c.pop(field,None)
            state=c['curriculum']
            archive=dict(recipe=deepcopy(saved_recipe),steps=c.get('steps',0),decisions=c.get('decisions',0),
                seconds=c.get('seconds',0),sourceCheckpoint=self.source_checkpoint,
                evaluationCount=len(state.get('evaluations',[])),updates=state.get('updates',0),stats=deepcopy(state.get('stats',{})))
            state.setdefault('recipeArchives',[]).append(archive)
            archive['evaluations']=deepcopy(state.get('evaluations',[]))
            state.update(effectiveParameters=self.spec,evaluations=[],updates=state.get('updates',0) if self.spec['version']=='race-residual-4' else 0,
                stats=deepcopy(state['stats']) if self.spec['version']=='race-residual-4' else dict(episodes=0,success=0,passes=0,contacts=0,trackLimits=0,cleanLaps=0,windows=0),status='Memoria conservata · nuovi premi',
                rewardEpochStart=dict(steps=c.get('steps',0),decisions=c.get('decisions',0)),
                migration=dict(version=self.spec['version'],actor='preserved',replay='archived',critics='reset',actorOptimizer='preserved'))
            # The champion and its old proof stay intact, with their provenance.
            # Only new complete evaluations certify the new training objective.
            c['lastCheck']=c.get('decisions',0)
        changed_mode=bool(c and c.get('objective','impara')!=objective)
        if changed_mode:
            for field in ('episode','preview','inflight','check'):c.pop(field,None)
            if c.get('learner'):c['learner'].pop('pendingTransitions',None)
            if profile['algorithm']=='residual_ppo' and c.get('learner'):c['learner'].update(buffer=[],pending=None)
        if c and c.get('protocol') not in (None,self.protocol):raise ValueError('Esperienza del vecchio percorso incompatibile')
        if c.get('configuration') and c['configuration']!=configuration(track_id,profile['observation']):
            raise ValueError('Il checkpoint appartiene a un altro contesto fisico')
        self.learner=self.make_learner(profile,c.get('learner'))
        if not c.get('learner') and c.get('initialPolicy',{}).get('weights') is not None:
            self.learner.actor=np.asarray(c['initialPolicy']['weights'],dtype=float)
            if hasattr(self.learner,'target_actor'):self.learner.target_actor=self.learner.actor.copy()
        if migrated:
            self.learner.actor=np.asarray(migrated['actor'],dtype=float).copy()
            self.learner.log_std=np.asarray(migrated.get('logStd',migrated.get('log_std')),dtype=float).copy()
            if self.spec['version']=='race-residual-4':
                from game_learning import Adam
                self.learner.log_std=np.maximum(self.learner.log_std,np.log(self.spec['exploration']))
                self.learner.log_std=np.minimum(self.learner.log_std,np.log(self.spec['maxStd']))
                self.learner.update_index=int(migrated['update'])
                optimizer=Adam(len(self.learner.actor),migrated.get('actorAdam'))
                if isinstance(self.learner,PPO):self.learner.actor_adam=optimizer
                else:self.learner.actorAdam=optimizer
            self.learner.rng.bit_generator.state=deepcopy(migrated['rng'])
            if hasattr(self.learner,'target_actor'):self.learner.target_actor=self.learner.actor.copy()
        self.opponents=[Policy(p) for p in c.get('frozenOpponents',[])] if 'frozenOpponents' in c else list(opponents)
        self.rng=np.random.default_rng(profile['seed']+709)
        if c.get('rng'):self.rng.bit_generator.state=c['rng']
        # Keep random feature layer and a zero output layer, not a dead all-zero network.
        from game_residual import initial_weights
        neutral=self.initial_policy(profile,c)
        self.state=deepcopy(c.get('curriculum')) or dict(version=1,residualVersion=self.protocol,
            phase='pace',round=0,updates=0,champion=dict(policy=neutral,profile=profile),
            evaluations=[],stats=dict(episodes=0,success=0,passes=0,contacts=0,trackLimits=0),
            status='Base pronta',execution=dict(backend='numpy',physicsHz=60,decisionHz=10),
            effectiveParameters=self.spec,origin=c.get('origin','Base verificata · correzioni neutre'))
        self.steps=int(c.get('steps',0));self.decisions=int(c.get('decisions',0));self.metric=deepcopy(c.get('metric',{}))
        self.iterator=None
        if isinstance(self.learner,PPO) and self.learner.pending is not None:self.iterator=self.learner.updates()
        self.episode=self.new_episode(c.get('episode'));self.inflight=deepcopy(c.get('inflight'))
        self.check_cache=deepcopy(c.get('checkCache',{}))
        if migrated:self.check_cache={}
        if c.get('check') and c['check'].get('version')!='skill-gates-3':c['check']=None
        self.check=ResidualCheck(c['check']['candidate'],c['check']['champion'],track_id,c['check'],cache=self.check_cache) if c.get('check') else None
        # Old previews drove the champion indefinitely. Discard only that visual
        # episode when upgrading; training, replay, RNG and champion stay intact.
        saved_preview=c.get('preview') if c.get('previewPolicy') else None
        self.preview=self.new_preview(saved_preview)
        self.preview_policy=Policy(c.get('previewPolicy') or self.learner.policy())
        self.preview_trial=int(c.get('previewTrial',1))
        self.preview_update=int(c.get('previewUpdate',self.learner.update_index))
        self.preview_command=np.asarray(c.get('previewCommand',[0.,0.]),dtype=float)
        self.champion_key=key(self.state['champion']['policy'])
        self.last_preview=time.monotonic();self.preview_remaining=0.;self.preview_hold=0.;self.rate_samples={}
        self.episode_serial=int(c.get('episodeSerial',0));self.last_check=int(c.get('lastCheck',0))
        self.context=self.spec.get('criticInputs')==94

    @property
    def task(self):return self.episode.spec

    def curriculum_decisions(self):return self.decisions

    def new_episode(self,saved=None):
        phase='pace'
        if self.objective=='impara_sorpasso' or (self.profile['algorithm']=='residual_tactic' and self.curriculum_decisions()>=8192 and self.state['stats']['episodes']%4):
            choices=('overtake','defend','corner','duel') if self.opponents and self.state['stats']['episodes']>=12 else ('overtake','defend','corner')
            phase=choices[self.state['stats']['episodes']%len(choices)]
        if saved:phase=saved['phase']
        self.state['phase']=phase
        mode=self.objective
        seed=saved['seed'] if saved else int(self.rng.integers(200000,300000))
        e=Episode(self.track_id,phase,seed,self.opponents,saved=saved,
            protocol='driving-memory-1',objective=mode,bots=self.bots,single_lap=True,reward_spec=self.reward_spec,pace_pressure=1.)
        e.world.native_sensors=True
        return e

    def new_preview(self,saved=None):
        traffic=self.objective=='impara_sorpasso'
        e=Episode(self.track_id,'overtake' if traffic else 'pace',719001,saved=saved,objective='impara_sorpasso' if traffic else 'impara_infinito',bots=self.bots,protocol='driving-memory-1',reward_spec=self.reward_spec)
        e.world.enable_timing('preview');return e

    def quiesce(self):pass
    def close(self):pass

    def refresh_preview_candidate(self,previous_lap=None):
        self.preview_policy=Policy(self.learner.policy())
        self.preview_update=self.learner.update_index
        self.preview_trial+=1
        timing=self.preview.world.enable_timing('preview')
        if previous_lap is None:timing.bind(0,'preview',self.preview_policy.racing.key)
        else:timing.bind_preview_boundary(0,'preview',self.preview_policy.racing.key,previous_lap,self.preview.world.time)

    def advance_preview(self):
        self.preview.world.enable_timing('preview').bind(0,'preview',self.preview_policy.racing.key)
        now=time.monotonic();self.preview_remaining+=max(0,min(.1,now-self.last_preview));self.last_preview=now
        if self.preview.reason and self.preview.reason!='window':
            self.preview_hold+=self.preview_remaining;self.preview_remaining=0
            if self.preview_hold>2:
                self.preview=self.new_preview();self.refresh_preview_candidate();self.preview_hold=0
            return
        while self.preview_remaining>=1/60:
            if self.preview.reason=='window':self.preview.next_window()
            previous_lap=self.preview.world.timing.cars[0]['lapId']
            self.preview_command=self.preview_policy.act(None,world=self.preview.world,index=0)
            self.preview.step(self.preview_command,return_observation=False)
            if self.preview.world.timing.cars[0]['lapId']!=previous_lap:
                self.refresh_preview_candidate(previous_lap)
            self.preview_remaining-=1/60
            if self.preview.reason and self.preview.reason!='window':break

    def tick(self):
        if self.check:
            started=time.monotonic()
            done=self.check.tick()
            self.state['evaluationSeconds']=self.state.get('evaluationSeconds',0.)+time.monotonic()-started
            self.state['evaluationSteps']=self.state.get('evaluationSteps',0)+getattr(self.check,'last_steps_advanced',1)
            if done:
                result=self.check.result();self.state['round']+=1
                if not self.state.get('baseMedian'):self.state['baseMedian']=result['champion']['median']
                result.update(round=self.state['round'],scope=scope_hash(self.track_id,self.profile['observation']))
                self.state['evaluations']=(self.state['evaluations']+[result])[-20:]
                if result['accepted']:
                    self.state['champion']=dict(policy=self.check.candidate,profile=self.profile,proof=result)
                    self.state['verifiedBest']=dict(policy=self.check.candidate,profile=self.profile,proof=result)
                    self.champion_key=key(self.check.candidate)
                    self.state['status']='Miglioramento verificato'
                else:self.state['status']='Campione conservato'
                self.check=None
            return
        if self.iterator:
            try:self.metric=next(self.iterator)
            except StopIteration:
                self.iterator=None;self.state['updates']=self.learner.update_index
                self.schedule_check()
            return
        e=self.episode
        if self.inflight is None:
            obs=value_features(e,self.observe(e.world)) if self.context else self.observe(e.world)
            if isinstance(self.learner,PPO):
                action,raw,logp,value=self.learner.sample(obs[None,:])
                self.inflight=dict(obs=obs.tolist(),action=action[0].tolist(),raw=raw[0].tolist(),logp=float(logp[0]),value=float(value[0]),reward=0.,ticks=0)
            else:self.inflight=dict(obs=obs.tolist(),action=self.learner.sample(obs)[0].tolist(),reward=0.,ticks=0)
            if self.context:self.inflight['potential']=learning_potential(e)
        b=self.inflight
        command=self.drive(e.world,b['action'],[0])[0]
        old_laps=int(e.world.clean_laps[0])
        _,reward,done,terminated=e.step(command,return_observation=False)
        self.state['stats']['cleanLaps']=self.state['stats'].get('cleanLaps',0)+int(e.world.clean_laps[0])-old_laps
        self.steps+=1;b['ticks']+=1;b['reward']+=float(reward)
        if b['ticks']<DECISION_STEPS and not done:return
        nxt=value_features(e,self.observe(e.world)) if self.context else self.observe(e.world);self.decisions+=1
        if self.context:
            potential=0. if terminated else learning_potential(e)
            shaping=self.spec['gamma']*potential-b['potential']
            b['reward']+=shaping;e.return_total+=shaping;e.term_totals['shaping']+=shaping
            self.metric['shapingReward']=shaping
        if isinstance(self.learner,PPO):
            self.learner.remember(np.array([b['obs']]),np.array([b['raw']]),np.array([b['logp']]),np.array([b['value']]),
                np.array([b['reward']]),np.array([done]),nxt[None,:],np.array([terminated]))
            if len(self.learner.buffer)>=self.profile['rollout']:self.iterator=self.learner.updates()
        else:
            self.learner.remember(b['obs'],b['action'],b['reward'],nxt,terminated,episode_done=done)
            result=self.learner.update()
            if result:self.metric=result;self.state['updates']=self.learner.update_index
        self.inflight=None
        self.metric.update(decisions=self.decisions,physicalSteps=self.steps,activity='Aggiornamento' if self.iterator else 'Raccolta')
        if done:
            stats=self.state['stats'];stats['episodes']+=1;stats['success']+=int(e.reason=='success')
            stats['windows']=stats.get('windows',0)+int(e.reason=='window')
            stats['passes']+=e.passes;stats['contacts']+=e.contact_count;stats['trackLimits']+=int(e.world.track_limits[0])
            self.state['lastEpisode']=e.result()
            self.state['racecraftViolations']=self.state.get('racecraftViolations',0)+getattr(e,'racecraft',{}).get('violations',0)
            if e.reason=='window':e.next_window()
            else:self.episode=self.new_episode();self.episode_serial+=1
        if self.decisions>=300000 and not self.state.get('verifiedBest'):
            self.state['pauseRequested']='Budget raggiunto senza miglioramento verificato · campione conservato'
        if not self.iterator:self.schedule_check()

    def schedule_check(self):
        # Bound verification overhead; count data and frozen verification separately.
        if self.decisions-self.last_check<(4096 if self.profile['algorithm']=='residual_tactic' else 2048):return
        self.last_check=self.decisions
        self.check=ResidualCheck(self.learner.policy(),self.state['champion']['policy'],self.track_id,cache=self.check_cache)
        self.state['status']='Verifica congelata'

    def checkpoint(self,seconds,deferred=False):
        return dict(schema=1,protocol=self.protocol,objective=self.objective,configuration=configuration(self.track_id,self.profile['observation']),
            learner=self.learner.checkpoint(deferred=deferred) if deferred and isinstance(self.learner,OffPolicy) else self.learner.checkpoint(),sourceCheckpoint=self.source_checkpoint,steps=self.steps,decisions=self.decisions,seconds=seconds,
            curriculum=deepcopy(self.state),metric=deepcopy(self.metric),task=self.task,
            episode=self.episode.snapshot(),preview=self.preview.snapshot(),inflight=deepcopy(self.inflight),
            previewPolicy=deepcopy(self.preview_policy.snapshot),previewTrial=self.preview_trial,previewUpdate=self.preview_update,
            previewCommand=self.preview_command.tolist(),
            check=self.check.snapshot() if self.check else None,checkCache=deepcopy(self.check_cache),rng=deepcopy(self.rng.bit_generator.state),
            episodeSerial=self.episode_serial,lastCheck=self.last_check,rewardSpec=self.reward_spec,
            frozenOpponents=[p.snapshot for p in self.opponents])

    def frame(self,name,number,selected,paused=False):
        e=self.preview;rows=e.world.rows()
        for i,row in enumerate(rows):
            row.update(id='residual-preview-'+str(i),name=name if i==0 else 'Bot '+str(i),number=number if i==0 else i,
                resetKey=str(e.revision),simulatedTime=e.world.time)
        latest=(self.state.get('evaluations') or [{}])[-1]
        candidate_time=latest.get('candidate',{}).get('median');champion_time=latest.get('champion',{}).get('median')
        meta=dict(driverName=name,algorithm=self.profile['algorithm'],count=len(rows),selected=selected%len(rows),
            steps=self.steps,metric=deepcopy(self.metric),phase='valutazione' if self.check else 'aggiornamento' if self.iterator else 'raccolta',
            curriculumPhase='Traiettorie e passo' if self.state['phase']=='pace' else 'Sorpassi e difesa',
            exercise=self.state['status'],evaluationRound=self.state['round'],presentation='preview',trainingCount=1,
            policyVersion=self.preview_policy.racing.key,previewState=e.reason or 'running',manoeuvre=e.manoeuvre_status(),time=e.world.time,sensorRange=150,objective=self.objective,
            learningStats=deepcopy(self.state['stats']),execution=self.state['execution'],
            residual=dict(decisions=self.decisions,updates=self.learner.update_index,episodes=self.state['stats']['episodes'],
                rewardVersion=self.reward_spec['version'],criticContext=self.spec.get('criticContext'),
                requestedLine=getattr(e.world,'residual_rules',{}).get(0,{}).get('requestedLine',0.),
                speedKmh=float(e.world.state[0,3])*3.6,steer=float(self.preview_command[0]),pedal=float(self.preview_command[1]),
                explorationMeters=float(np.exp(self.learner.log_std[0])*(e.world.track.width/2-e.world.vehicle.width/2-.9)),
                rewardTerms=deepcopy(self.episode.term_totals),
                previewRole='candidate',previewTrial=self.preview_trial,previewUpdate=self.preview_update,
                verification=self.state['round'],lastDecision=latest.get('decision'),
                lastDelta=candidate_time-champion_time if candidate_time is not None and champion_time is not None else None,
                base='race-base-1',status=self.state['status'],championHash=self.champion_key,
                bestImprovement=max(0.,1-(self.state['champion'].get('proof',{}).get('candidate',{}).get('median') or self.state.get('baseMedian') or 1)/(self.state.get('baseMedian') or 1))))
        if self.check:meta.update(activityDone=sum(bool(e.reason) for e in self.check.episodes),activityTotal=len(self.check.episodes))
        from game_simulation import RAY_ANGLES
        selected_index=selected%len(rows)
        rays=e.world.sensor_rays(e.world.state[selected_index:selected_index+1],RAY_ANGLES,150.)[0]/150.
        return rows,np.clip(rays,0,1),meta
