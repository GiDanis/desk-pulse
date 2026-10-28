"""Direct-control learning with a prepared base and bounded exploration trials.

    Teacher imitation is a separate preparation step. This trainer performs
    reinforcement learning on actual actuator outputs, never teacher blending.
    Existing recipes migrate at an explicit episode boundary, with provenance.
"""
from copy import deepcopy
import math
import numpy as np
from game_direct import features, controls, snapshot, DirectPolicy
from game_residual import recipe as residual_recipe
from game_residual_trainer import ResidualTrainer
from game_residual_learning import ResidualPPO, OffPolicy
from game_rewards import specification


def recipe(profile):
    result = residual_recipe(profile)
    result.update(version='direct-driving-3', base=None,
        features='direct-physical-90-v1', action='direct-steer-pedal-v1',
        scales=[1., 1.], lineMap=None, teacherAtInference=False,
        exploration=[.008, .12], minStd=[.004, .05], maxStd=[.05, .30],
        reward='direct-driving-2', criticContext='task-context-1', criticInputs=94,
        potentialPrior=True,criticWarmup=512,actorRateScale=.1,anchorSteps=4096,anchorWeight=2.,
        targetNoise=.015,targetClip=.03,domainRandomization='vehicle-grip-1',candidateRestart='failed-or-two-no-gain-all-methods-1',
        explorationBlock=dict(decisions=12,pedalStd=.35,zeroEvery=3),school='driving-school-1',raceGate='five-car-retention-1',
        shaping='bounded-time-speed-potential-1')
    if profile.get('racingObjective')=='valid-time-1':
        result.update(reward='direct-driving-3',objective='valid-lap-time-1')
    if profile.get('racingCurriculum')=='graduated-1':
        result.update(version='direct-driving-4',school='mastery-then-rehearsal-1',
            evaluation='flying-pace-and-race-1',candidateRestart='safety-or-six-no-gain-1',
            verificationDecisions=4096,schoolSuccesses=2,rehearsalEvery=16,
            rollingStarts='distributed-quarter-lap-1')
        result['rehearsalOffset']=14 if profile['algorithm']=='residual_tactic' else 15
    if profile.get('expertLearning')=='routed-1':result['expertLearning']='presence-separated-1'
    if profile.get('racingAnchor')=='steering-retained-1':
        result.update(anchorSteps=32768,anchorWeight=2.,anchorAxes=[16.,0.],
            rollingStarts='standing-1',candidateRestart='failed-or-two-no-gain-all-methods-1',
            verificationDecisions=2048,noGainRestart=2)
    if profile.get('episodeExploration')=='coherent-pedal-1':
        result['explorationBlock']=dict(decisions=0,pedalStd=.10,zeroEvery=3,scope='episode')
    if profile.get('racingHorizon') in (4.,8.):result['gaeLambda']=math.exp(-.1/profile['racingHorizon'])
    if profile.get('raceValidationEvery') in (2,3,4):result['raceValidationEvery']=profile['raceValidationEvery']
    if profile.get('trafficLearning')=='attack-1':
        result.update(version='direct-driving-attack-1',trafficLearning='attack-1',
            reward='direct-driving-attack-1',relativeAdvantage=float(profile.get('relativeAdvantage',.25)),
            evaluation='flying-pace-and-attack-1',trafficCollection='bounded-family-24s-1',verificationDecisions=8192)
    if profile.get('directExperiment')=='prior-only':result.update(criticWarmup=0,actorRateScale=1.,anchorSteps=0,anchorWeight=0.)
    elif profile.get('directExperiment')=='slow':result.update(criticWarmup=512,actorRateScale=.01,anchorSteps=0,anchorWeight=0.)
    elif profile.get('directExperiment')=='warm':result.update(criticWarmup=2048,actorRateScale=.1,anchorSteps=0,anchorWeight=0.)
    return result


def value_potential(obs):
    x=np.asarray(obs)
    reference=9*np.sqrt(np.maximum(.1,x[...,73])/.95)
    speed=np.maximum(0,x[...,72]*60*np.cos(x[...,10]*math.pi))
    return -.25*x[...,91]+.05*np.clip(speed/reference,0,2)


class BlockExploration:
    """Exogenous pedal option; PPO stores the conditional unshifted latent.

    Given block b, raw_actual = Normal(mean, std) + b. In PPO likelihood
    ratios the same fixed b and action Jacobian cancel. The stored raw is
    raw_actual-b, so existing Gaussian gradients remain the exact conditional
    likelihood. Steering noise stays independent and small.
    """
    def configure_blocks(self,checkpoint):
        self.block=deepcopy((checkpoint or {}).get('explorationBlock')) or dict(left=0,pedal=0.,number=0)

    def pedal_bias(self):
        spec=recipe(self.public_profile if hasattr(self,'public_profile') else self.profile)['explorationBlock']
        if self.block['left']<=0:
            self.block['number']+=1;self.block['left']=1000000000 if spec.get('scope')=='episode' else spec['decisions']
            self.block['pedal']=0. if self.block['number']%spec['zeroEvery']==0 else float(np.clip(self.rng.normal(0,spec['pedalStd']),-.7,.7))
            profile=self.public_profile if hasattr(self,'public_profile') else self.profile
            if profile.get('trafficLearning')=='attack-1':self.block['steer']=float(np.clip(self.rng.normal(0,.01),-.025,.025))
        self.block['left']-=1
        return self.block['pedal']


class DirectPPO(BlockExploration,ResidualPPO):
    def __init__(self, profile, checkpoint=None):
        inner={k:v for k,v in profile.items() if k!='controlMode'}
        super().__init__(inner, checkpoint)
        self.public_profile=deepcopy(profile)
        self.direct_spec = recipe(profile)
        self.configure_runtime(dict(self.tuning,gaeLambda=self.direct_spec['gaeLambda'],minLogStd=np.log(self.direct_spec['minStd']).tolist(),
                                    maxLogStd=np.log(self.direct_spec['maxStd']).tolist()))
        if not checkpoint:
            self.log_std = np.log(self.direct_spec['exploration'])
        self.configure_blocks(checkpoint)
        if profile.get('expertLearning')=='routed-1' and (checkpoint or {}).get('actorAdam',{}).get('expertBlocks'):
            from game_racing_learning import RoutedAdam
            self.actor_adam=RoutedAdam(checkpoint['actorAdam'])

    def actor_backward(self,cache,derivative):
        if self.public_profile.get('expertLearning')=='routed-1':
            from game_racing_learning import routed_backward
            return routed_backward(cache,derivative)
        return super().actor_backward(cache,derivative)

    def apply_actor_gradient(self,gradient,obs,rate):
        if self.public_profile.get('expertLearning')=='routed-1':
            from game_racing_learning import apply
            self.actor_adam=apply(self.actor_adam,self.actor,gradient,rate,obs)
        else:super().apply_actor_gradient(gradient,obs,rate)

    def sample(self,obs):
        _,raw,logp,value=super().sample(obs)
        pedal=self.pedal_bias()
        return np.tanh(raw+np.array([self.block.get('steer',0.),pedal])),raw,logp,value

    def checkpoint(self):
        result=super().checkpoint();result['explorationBlock']=deepcopy(self.block);return result

    def value_offset(self, obs):
        return value_potential(obs)

    def policy(self):
        return snapshot(self.public_profile, self.actor)

    candidate_policy = policy


class DirectOffPolicy(BlockExploration,OffPolicy):
    def __init__(self, profile, checkpoint=None):
        inner={k:v for k,v in profile.items() if k!='controlMode'}
        super().__init__(inner, checkpoint)
        self.profile=deepcopy(profile)
        self.spec = recipe(profile)
        self.anchor_actor=np.asarray(checkpoint['anchorActor'],dtype=float) if checkpoint and checkpoint.get('anchorActor') else None
        if not checkpoint:
            self.log_std = np.log(self.spec['exploration'])
        self.configure_blocks(checkpoint)
        self.family_tags=np.zeros(self.capacity,dtype=np.int8)
        if checkpoint and 'familyTags' in checkpoint:
            tags=np.asarray(checkpoint['familyTags'],dtype=np.int8)
            if tags.shape!=(self.count,) or np.any((tags<0)|(tags>7)):raise ValueError('Replay tattico danneggiato')
            self.family_tags[:self.count]=tags
        if profile.get('expertLearning')=='routed-1' and (checkpoint or {}).get('actorAdam',{}).get('expertBlocks'):
            from game_racing_learning import RoutedAdam
            self.actorAdam=RoutedAdam(checkpoint['actorAdam'])

    def actor_backward(self,cache,derivative):
        if self.profile.get('expertLearning')=='routed-1':
            from game_racing_learning import routed_backward
            return routed_backward(cache,derivative)
        return super().actor_backward(cache,derivative)

    def write_transition(self,*args):
        from game_overtaking import FAMILIES
        family=getattr(self,'collection_family','')
        tag=FAMILIES.index(family)+1 if family in FAMILIES else 0
        self.family_tags[self.cursor]=tag
        return super().write_transition(*args)

    def sample_indices(self):
        if self.profile.get('trafficLearning')!='attack-1':return super().sample_indices()
        # complete/attack/corner/defend/pace/recover. Empty strata fall back
        # explicitly to the full live buffer, never to stale rows.
        counts=(8,8,12,8,16,6,6);indices=[]
        for tag,count in enumerate(counts,1):
            pool=np.flatnonzero(self.family_tags[:self.count]==tag)
            indices.extend(self.rng.choice(pool,count).tolist() if len(pool) else self.rng.integers(0,self.count,count).tolist())
        return np.asarray(indices[:self.spec['batchSize']])

    def apply_actor_gradient(self,gradient,obs,rate):
        if self.profile.get('expertLearning')=='routed-1':
            from game_racing_learning import apply
            self.actorAdam=apply(self.actorAdam,self.actor,gradient,rate,obs)
        else:super().apply_actor_gradient(gradient,obs,rate)

    def sample(self,obs):
        from game_learning import forward
        mean=forward(self.actor,np.atleast_2d(obs)[...,:90],self.hidden)
        noise=self.rng.normal(size=mean.shape)*np.exp(self.log_std);pedal=self.pedal_bias()
        return np.tanh(mean+noise+np.array([self.block.get('steer',0.),pedal]))

    def value_offset(self,obs):return value_potential(obs)

    def actor_update_ready(self):return self.transitions>=self.spec['criticWarmup']

    def actor_learning_rate(self):return self.profile['learningRate']*self.spec['actorRateScale']

    def actor_gradient(self,gradient,obs):
        if self.anchor_actor is None:return gradient
        strength=self.spec['anchorWeight']*max(0.,1-self.transitions/max(1,self.spec['anchorSteps']))
        if not strength:return gradient
        from game_learning import forward,backward
        raw,cache=forward(self.actor,obs,self.hidden,cache=True);action=np.tanh(raw)
        base=np.tanh(forward(self.anchor_actor,obs,self.hidden))
        derivative=strength*(action-base)*(1-action*action)*np.array(self.spec.get('anchorAxes',[16.,1.]))/len(obs)
        return gradient+self.actor_backward(cache,derivative)

    def checkpoint(self,deferred=False):
        result=super().checkpoint(deferred)
        if self.profile.get('trafficLearning')=='attack-1':result['familyTags']=self.family_tags[:self.count].tolist()
        result['anchorActor']=self.anchor_actor.tolist() if self.anchor_actor is not None else None
        result['explorationBlock']=deepcopy(self.block)
        return result

    def policy(self):
        return snapshot(self.profile, self.actor)

    candidate_policy = policy


class DirectTrainer(ResidualTrainer):
    protocol = 'direct-driving-3'
    recipe = staticmethod(recipe)
    observe = staticmethod(features)
    drive = staticmethod(controls)

    def __init__(self, profile, track_id, checkpoint=None, opponents=(), **kwargs):
        from game_racing_presets import production_profile
        p = production_profile({**profile, 'controlMode': 'direct'})
        c = deepcopy(checkpoint or {})
        retained_learner=None
        previous=(c.get('curriculum') or {}).get('effectiveParameters') or {}
        if c.get('protocol')=='direct-driving-2' or (not c.get('learner') and not c.get('initialPolicy')) or c.get('initialPolicy',{}).get('recipe',{}).get('version')=='direct-driving-2':
            from game_direct_bootstrap import base_asset
            p['hidden']=base_asset('traffic' if p['algorithm']=='residual_tactic' else 'driving')['policy']['hidden']
        elif c.get('protocol')==self.protocol and previous.get('hidden'):p['hidden']=previous['hidden']
        if c.get('protocol')=='direct-driving-2' and previous.get('version')=='direct-driving-2':
            from game_direct_bootstrap import initial_policy
            from game_residual import key
            state=c.get('curriculum') or {};old=state.get('champion',{}).get('policy')
            archive=dict(recipe=previous,sourceCheckpoint=c.get('migrationSource') or c.get('sourceCheckpoint'),
                steps=c.get('steps',0),decisions=c.get('decisions',0),updates=state.get('updates',0),
                stats=deepcopy(state.get('stats',{})),championHash=key(old) if old else None)
            c={k:v for k,v in c.items() if k in ('steps','decisions','seconds','configuration','sourceCheckpoint','migrationSource','rng','objective')}
            c.update(protocol=self.protocol,initialPolicy=initial_policy(p),origin='Scuola guida · nuova preparazione verificata',
                lastCheck=c.get('decisions',0))
            c['curriculum']=dict(version=1,residualVersion=self.protocol,phase='pace',round=0,updates=0,
                champion=dict(policy=c['initialPolicy'],profile=p),evaluations=[],
                stats=dict(episodes=0,success=0,passes=0,contacts=0,trackLimits=0),
                execution=dict(backend='numpy',physicsHz=60,decisionHz=10),effectiveParameters=recipe(p),
                origin=c['origin'],status='Nuova scuola · storia conservata',recipeArchives=[archive],
                epochStart=dict(steps=c.get('steps',0),decisions=c.get('decisions',0)),
                migration=dict(version='direct-driving-3',actor='new-qualified-school-base',replay='archived',critics='reset'))
        elif not c.get('learner') and c.get('initialPolicy',{}).get('recipe',{}).get('version')=='direct-driving-2':
            from game_direct_bootstrap import initial_policy
            c['initialPolicy']=initial_policy(p);c['origin']='Scuola guida · base aggiornata'
        if c.get('protocol') not in (None, self.protocol):
            raise ValueError('I pesi corsia/passo non sono comandi diretti: occorre una base neurale distinta')
        if c.get('learner') and previous.get('version')=='direct-driving-4' and p.get('trafficLearning')=='attack-1':
            legacy={k:v for k,v in p.items() if k not in ('trafficLearning','relativeAdvantage')}
            if previous!=recipe(legacy):raise ValueError('Ricetta di provenienza tattica sconosciuta')
            retained_learner=c.pop('learner');state=c['curriculum']
            state.setdefault('recipeArchives',[]).append(dict(recipe=deepcopy(previous),sourceCheckpoint=c.get('migrationSource') or c.get('sourceCheckpoint'),
                steps=c.get('steps',0),decisions=c.get('decisions',0),evaluations=deepcopy(state.get('evaluations',[])),stats=deepcopy(state.get('stats',{}))))
            from game_direct import snapshot as direct_snapshot
            c['initialPolicy']=direct_snapshot(p,retained_learner['actor'],dict(kind='personal-weights-preserved'))
            state.update(effectiveParameters=recipe(p),evaluations=[],updates=0,epochStart=dict(steps=c.get('steps',0),decisions=c.get('decisions',0)),
                stats=dict(episodes=0,success=0,passes=0,contacts=0,trackLimits=0),
                migration=dict(version='attack-1',actor='preserved',replay='archived',critics='reset',actorOptimizer='solo-preserved-traffic-and-gate-reset'))
            c['lastCheck']=c.get('decisions',0)
            for field in ('episode','preview','previewPolicy','previewTrial','previewUpdate','previewCommand','inflight','check','metric','checkCache'):c.pop(field,None)
        if c.get('learner') and previous.get('version')=='direct-driving-3' and recipe(p).get('version')=='direct-driving-4':
            from game_direct import snapshot as direct_snapshot
            from game_racing_presets import PROFILE_KEYS
            legacy={k:v for k,v in p.items() if k not in PROFILE_KEYS}
            if previous not in (recipe(legacy),recipe({**legacy,'racingObjective':'valid-time-1'})):
                raise ValueError('Ricetta precedente sconosciuta: memoria originale conservata')
            retained_learner=c.pop('learner')
            state=c['curriculum'];source=c.get('migrationSource') or c.get('sourceCheckpoint')
            archive=dict(recipe=deepcopy(previous),sourceCheckpoint=source,steps=c.get('steps',0),
                decisions=c.get('decisions',0),seconds=c.get('seconds',0),updates=state.get('updates',0),
                evaluations=deepcopy(state.get('evaluations',[])),stats=deepcopy(state.get('stats',{})))
            state.setdefault('recipeArchives',[]).append(archive)
            state.setdefault('raceChampion',deepcopy(state['champion']))
            from game_neural_mixture import EXPERT_SIZE,SIZE
            source_actor=np.asarray(retained_learner['actor'],dtype=float)
            stable_actor=np.asarray(state['raceChampion']['policy']['weights'],dtype=float)
            restore_traffic=p.get('expertLearning')=='routed-1' and len(source_actor)==SIZE and len(stable_actor)==SIZE
            if restore_traffic:
                # Keep the pilot's current solo experience, consolidate traffic
                # from its own stable champion. Both original files stay archived.
                source_actor[EXPERT_SIZE:]=stable_actor[EXPERT_SIZE:]
                retained_learner['actor']=source_actor.tolist()
            state.update(effectiveParameters=recipe(p),evaluations=[],updates=0,
                stats=dict(episodes=0,success=0,passes=0,contacts=0,trackLimits=0,cleanLaps=0,windows=0),
                evaluationSeconds=0.,evaluationSteps=0,noGainChecks=0,
                epochStart=dict(steps=c.get('steps',0),decisions=c.get('decisions',0)),
                migration=dict(version='direct-racing-1',actor='preserved',actorOptimizer='preserved',
                    sourceCheckpoint=source,replay='archived',critics='reset',qualifications='preserved-exact-policies'),
                status='Guida conservata · nuovo obiettivo sul tempo')
            if restore_traffic:
                state['migration'].update(actor='solo-preserved-traffic-from-own-champion',
                    actorOptimizer='solo-preserved-traffic-and-gate-reset')
            state.pop('baseMedian',None)
            c['initialPolicy']=direct_snapshot(p,retained_learner['actor'],dict(kind='preserved-driver',sourceCheckpoint=source))
            c['lastCheck']=c.get('decisions',0);c['sourceCheckpoint']=source
            for field in ('episode','preview','previewPolicy','previewTrial','previewUpdate','previewCommand','inflight','check','metric','checkCache'):
                c.pop(field,None)
        if c.get('learner'):
            if (c.get('curriculum') or {}).get('effectiveParameters') != recipe(p):
                raise ValueError('Checkpoint diretto di un’altra ricetta')
        else:
            policy = c.get('initialPolicy')
            if not policy:
                from game_direct_bootstrap import initial_policy
                policy=initial_policy(p);c['initialPolicy']=policy
            DirectPolicy(policy)
            if policy['hidden'] != p['hidden']:
                raise ValueError('Dimensione della base neurale incompatibile')
        saved_check=c.pop('check',None)
        if c and c.get('objective','impara')!=kwargs.get('objective','impara'):saved_check=None
        super().__init__(p, track_id, c, opponents=opponents, **kwargs)
        if not c.get('learner'):
            from game_learning import Adam
            if isinstance(self.learner,DirectOffPolicy):self.learner.actorAdam=Adam(len(self.learner.actor))
            else:self.learner.actor_adam=Adam(len(self.learner.actor))
        if retained_learner:
            from game_learning import Adam
            from game_racing_learning import RoutedAdam
            from game_neural_mixture import SIZE
            optimizer=retained_learner.get('actorAdam')
            restored=RoutedAdam(optimizer) if p.get('expertLearning')=='routed-1' and len(self.learner.actor)==SIZE else Adam(len(self.learner.actor),optimizer)
            if self.state.get('migration',{}).get('actorOptimizer')=='solo-preserved-traffic-and-gate-reset':
                for index in (1,2):restored.blocks[index]=Adam(len(restored.blocks[index].m))
            if isinstance(self.learner,DirectOffPolicy):self.learner.actorAdam=restored
            else:self.learner.actor_adam=restored
            self.learner.log_std=np.asarray(retained_learner.get('logStd',retained_learner.get('log_std')),dtype=float).copy()
            self.learner.rng.bit_generator.state=deepcopy(retained_learner['rng'])
        if saved_check and saved_check.get('version')=='flying-pace-and-race-1':
            from game_racing_objective import RacingCheck
            self.check=RacingCheck(saved_check['candidate'],saved_check['champion'],track_id,saved_check,
                cache=self.check_cache,race_champion=saved_check['raceChampion'])
        elif saved_check and self.profile.get('racingCurriculum')!='graduated-1' and saved_check.get('version') in ('school-gates-1','school-gates-2'):
            from game_school_lessons import make_check
            self.check=make_check(saved_check['candidate'],saved_check['champion'],track_id,saved=saved_check,cache=self.check_cache)
        if isinstance(self.learner,DirectOffPolicy) and self.learner.anchor_actor is None:
            self.learner.anchor_actor=self.learner.actor.copy()
        if retained_learner and isinstance(self.learner,DirectOffPolicy) and self.spec.get('anchorAxes')==[16.,0.]:
            # The archived candidate can be exploratory. Retain steering around
            # the stable neural champion, not around an unverified candidate.
            self.learner.anchor_actor=np.asarray(self.state['champion']['policy']['weights'],dtype=float).copy()
        if self.profile.get('racingCurriculum')=='graduated-1':
            self.state.setdefault('raceChampion',deepcopy(self.state['champion']))
            self.state.pop('lapBest',None)  # champion already is the solo best
            self.state['trainingProfile']=deepcopy(self.profile)
            self.state['trainingObjective']=self.objective
            self.state['rewardVersion']=self.reward_spec['version']
        self.state['execution']['control'] = 'network-actuators'
        self.state['execution']['teacherAtInference'] = False

    def make_learner(self, profile, checkpoint):
        return (DirectPPO if profile['algorithm']=='residual_ppo' else DirectOffPolicy)(profile, checkpoint)

    def initial_policy(self, profile, checkpoint):
        if checkpoint.get('initialPolicy'):
            return snapshot(profile,checkpoint['initialPolicy']['weights'],checkpoint['initialPolicy'].get('origin'))
        return snapshot(profile, self.learner.actor)

    def reward(self, profile):
        return specification({**profile, 'controlMode': 'direct'})

    def curriculum_decisions(self):
        if self.profile.get('racingCurriculum')=='graduated-1':
            return max(0,self.decisions-self.state.get('epochStart',{}).get('decisions',0))
        return self.decisions

    def new_episode(self,saved=None):
        if self.profile.get('trafficLearning')=='attack-1' and not saved and (self.objective=='impara_sorpasso' or self.profile['algorithm']=='residual_tactic'):
            from game_overtaking import scenario
            # Explicit balanced collection, independent of continuous preview.
            order=('complete','attack','corner','pace','traffic','complete','defend','pace','corner','recover')
            number=self.state['stats']['episodes']
            e=scenario(self.track_id,order[number%len(order)],int(self.rng.integers(200000,300000)),self.profile)
            self.state['phase']=e.phase
            if self.profile.get('episodeExploration')=='coherent-pedal-1':self.learner.block['left']=0
            return e
        if not saved and self.profile.get('episodeExploration')=='coherent-pedal-1':
            self.learner.block['left']=0
        episode=super().new_episode(saved)
        if saved:
            if saved.get('spec',{}).get('schoolSkill'):
                from game_school_lessons import Lesson
                return Lesson(self.track_id,saved['spec']['schoolSkill'],saved['seed'],self.profile,saved=saved)
            return episode
        number=self.state['stats']['episodes'];phase=episode.phase
        racing=self.profile.get('racingCurriculum')=='graduated-1'
        from game_racing_objective import graduated
        ready=graduated(self.state.get('schoolStats',{}),self.state.get('schoolGraduated',False))
        if racing:self.state['schoolGraduated']=ready
        rehearsal=14 if self.profile['algorithm']=='residual_tactic' and racing else 15
        lesson=(number%6<4 if not racing or not ready else number%16==rehearsal)
        if self.objective=='impara' and self.track_id=='oval-1' and lesson:
            from game_school_lessons import Lesson,SKILLS
            return Lesson(self.track_id,SKILLS[(number//16)%4 if racing and ready else number%6],episode.seed,self.profile)
        if self.profile['algorithm']=='residual_tactic' and self.curriculum_decisions()>=8192 and number%8==7:
            phase='grid' if number%16==7 else 'race4'
        from game_direct_bootstrap import physical_context
        from game_academy import Episode
        from game_learning import Policy
        context=physical_context(self.rng,True) if number%4==3 else None
        if racing and self.spec.get('rollingStarts')!='standing-1' and phase=='pace' and self.objective=='impara' and ready and number%2:
            # Physical rolling starts expose braking and exits without spending
            # every attempt relearning the same launch. No target enters the actor.
            from game_geometry import get_track
            track=get_track(self.track_id);start=(number//2%4)*track.length/4
            scenario=dict(start=start,speed=8.,distance=track.length,label='Passo · circuito da partenza variata',limitSeconds=100.,practiceCircuit=True)
            from game_academy import Episode
            return Episode(self.track_id,'pace',episode.seed,protocol='driving-memory-1',
                single_lap=True,reward_spec=self.reward_spec,pace_pressure=1.,context=context,scenario=scenario)
        if phase==episode.phase and context is None:
            if racing and phase in ('duel','race4') and self.objective=='impara':
                episode.spec.update(practiceCircuit=True,practiceGrid=True)
            return episode
        opponents=self.opponents
        if phase in ('grid','race4') and not opponents:opponents=[Policy(self.state['champion']['policy'])]
        self.state['phase']=phase
        episode=Episode(self.track_id,phase,episode.seed,opponents,
            protocol='driving-memory-1',objective=self.objective,bots=self.bots,
            single_lap=True,reward_spec=self.reward_spec,pace_pressure=1.,context=context)
        if racing and phase in ('duel','race4') and self.objective=='impara':
            episode.spec.update(practiceCircuit=True,practiceGrid=True)
        return episode

    def tick(self):
        if isinstance(self.learner,DirectOffPolicy):self.learner.collection_family=self.episode.spec.get('attackFamily','pace' if self.episode.world.count==1 else 'attack')
        checking=self.check is not None
        checked_candidate=self.check.candidate if checking else None
        old_episode=self.episode;episodes=self.state['stats']['episodes']
        super().tick()
        if self.state['stats']['episodes']>episodes and old_episode.spec.get('schoolSkill'):
            skill=old_episode.spec['schoolSkill'];stats=self.state.setdefault('schoolStats',{}).setdefault(skill,dict(total=0,valid=0))
            stats['total']+=1;stats['valid']+=int(old_episode.reason=='success')
        if self.state['stats']['episodes']>episodes and self.profile.get('racingCurriculum')=='graduated-1':
            from game_racing_objective import graduated
            self.state['schoolGraduated']=graduated(self.state.get('schoolStats',{}),self.state.get('schoolGraduated',False))
        if not checking or self.check is not None:return
        latest=self.state['evaluations'][-1]
        if self.profile.get('racingCurriculum')=='graduated-1':
            self.state['champion']['flyingMedian']=latest['candidate']['median'] if latest['accepted'] else latest['champion']['median']
            if latest.get('gridRetention'):self.state['lastRaceRound']=self.state['round']
            if latest.get('raceAccepted'):
                self.state['raceChampion']=dict(policy=deepcopy(checked_candidate),
                    profile=deepcopy(self.profile),proof=deepcopy(latest),flyingMedian=latest['candidate']['median'])
                self.state['status']='Giro e versione gara verificati' if latest['accepted'] else 'Versione gara migliorata'
            elif latest.get('raceReferenceMedian') is not None:
                self.state['raceChampion']['flyingMedian']=latest['raceReferenceMedian']
            if latest.get('attackAccepted'):
                self.state['attackChampion']=dict(policy=deepcopy(checked_candidate),profile=deepcopy(self.profile),proof=deepcopy(latest))
            if latest['accepted'] and not latest.get('raceAccepted'):self.state['status']='Giro migliorato · gara precedente conservata'
            self.state['lapBestHash']=self.champion_key
        streak=0 if latest['accepted'] or latest.get('raceAccepted') or latest.get('attackAccepted') else self.state.get('noGainChecks',0)+1
        self.state['noGainChecks']=streak
        failed=latest['candidate']['valid']<3 or (not self.profile.get('racingCurriculum') and bool(latest.get('regressions')))
        if not latest['accepted'] and not latest.get('raceAccepted') and (failed or streak>=self.spec.get('noGainRestart',6 if self.profile.get('racingCurriculum')=='graduated-1' else 2)):
            from game_learning import Adam
            reference=self.state.get('attackChampion',self.state['champion']) if self.objective=='impara_sorpasso' else self.state['champion']
            self.learner.actor=np.asarray(reference['policy']['weights'],dtype=float).copy()
            if isinstance(self.learner,DirectOffPolicy):
                self.learner.target_actor=self.learner.actor.copy();self.learner.actorAdam=Adam(len(self.learner.actor))
            else:
                self.learner.actor_adam=Adam(len(self.learner.actor));self.learner.buffer=[];self.learner.pending=None
            self.state['noGainChecks']=0
            self.state['candidateRestarts']=self.state.get('candidateRestarts',0)+1
            self.state['status']='Nuovo tentativo dal campione · esperienze conservate'

    def schedule_check(self):
        if self.decisions-self.last_check<self.spec.get('verificationDecisions',2048):return
        if self.profile.get('racingCurriculum')=='graduated-1':
            from game_racing_objective import RacingCheck
            self.last_check=self.decisions;candidate=self.learner.policy()
            self.check=RacingCheck(candidate,self.state['champion']['policy'],self.track_id,cache=self.check_cache,
                race_champion=self.state.get('raceChampion'),race_due=self.state['round']-self.state.get('lastRaceRound',0)>=self.spec.get('raceValidationEvery',1)-1)
            self.state['status']='Verifica giri lanciati · gara separata'
            return
        from game_school_lessons import make_check
        self.last_check=self.decisions
        self.check=make_check(self.learner.policy(),self.state['champion']['policy'],self.track_id,cache=self.check_cache)
        self.state['status']='Verifica giro e fondamenti'

    def frame(self, name, number, selected, paused=False):
        rows, rays, meta = super().frame(name, number, selected, paused)
        meta['controlMode'] = 'direct'
        meta['curriculumPhase'] = 'Guida neurale diretta'
        if isinstance(self.learner,DirectOffPolicy) and not self.learner.actor_update_ready():
            meta['curriculumPhase']='Preparazione dei critic · rete alla guida'
        info = meta['residual']
        info.pop('requestedLine', None)
        info.pop('explorationMeters', None)
        info.update(base=None, control='network-actuators', teacherAtInference=False,
            explorationSteerDegrees=float(np.exp(self.learner.log_std[0])*self.preview.world.vehicle.max_steer*180/math.pi),
            explorationPedal=float(np.exp(self.learner.log_std[1])),candidateRestarts=self.state.get('candidateRestarts',0),
            stage='critic_preparation' if isinstance(self.learner,DirectOffPolicy) and not self.learner.actor_update_ready() else 'refinement')
        latest=(self.state.get('evaluations') or [{}])[-1]
        info.update(previewRole='candidate',championSeconds=self.state['champion'].get('proof',{}).get('candidate',{}).get('median') or latest.get('champion',{}).get('median'),candidateSeconds=latest.get('candidate',{}).get('median'),
            schoolSkill=self.episode.spec.get('schoolSkill','giro completo'),schoolStats=deepcopy(self.state.get('schoolStats',{})),
            pedalBlockSeconds=self.spec['explorationBlock']['decisions']/self.spec['decisionHz'])
        if self.profile.get('racingCurriculum')=='graduated-1':
            ready=self.state.get('schoolGraduated',False) or self.objective!='impara'
            solo=self.state['champion'];proof=solo.get('proof',{})
            measured=solo.get('flyingMedian')
            if measured is None and proof.get('evaluationVersion')=='flying-pace-and-race-1':measured=proof.get('candidate',{}).get('median')
            stage='Sorpassi e difesa' if self.objective=='impara_sorpasso' else 'Passo continuo' if self.objective=='impara_infinito' else 'Ricerca del passo' if ready else 'Scuola guida'
            info.update(timingProtocol='flying-pace-and-race-1',championSeconds=measured,schoolGraduated=ready,
                objectiveStage=stage,
                raceReadySeconds=self.state.get('raceChampion',{}).get('flyingMedian'),
                raceStatus=latest.get('raceDecisionLabel','Versione gara conservata'),
                lastDecisionLabel=latest.get('decisionLabel','Prima verifica da eseguire'))
            meta['curriculumPhase']=info['objectiveStage']
        from game_overtaking import metrics
        info['attack']=metrics(self.episode)
        info['collectionFamily']=self.episode.spec.get('attackFamily',self.episode.phase)
        info['collectionLabel']=self.episode.spec.get('label',self.episode.phase)
        if self.check and getattr(self.check,'races',None):
            proofs=self.check.races
            meta.update(activityDone=sum(bool(r.reason) for r in proofs),activityTotal=len(proofs),
                exercise='Verifica gara · cinque auto su tre giri')
            info['status']=meta['exercise'];info['schoolSkill']='verifica gara a cinque'
        return rows, rays, meta
