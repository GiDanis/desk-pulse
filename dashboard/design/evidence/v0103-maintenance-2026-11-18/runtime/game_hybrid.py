"""Explicit imitation-to-PPO recipe and interruptible frozen readiness gate."""
from copy import deepcopy
import math
import numpy as np
from game_learning import PPO, Imitation, Adam, forward, random_weights, Policy
from game_curriculum import digest

RECIPE='clone-ppo-1'


class ClonePPO(PPO):
    def __init__(self,profile,checkpoint=None):
        super().__init__(profile,checkpoint)
        saved=(checkpoint or {}).get('hybrid') or {}
        self.phase=saved.get('phase','imitation')
        if self.phase not in ('imitation','reinforcement'):raise ValueError('Fase ibrida sconosciuta')
        self.hybrid=deepcopy(saved) or dict(version=RECIPE,phase=self.phase,proof=None,
            teacher='traffic-pursuit-2',imitationSteps=0,reinforcementSteps=0,checks=0)
        if self.hybrid['version']!=RECIPE:raise ValueError('Ricetta ibrida incompatibile')
        self.teacher=Imitation(profile,(checkpoint or {}).get('imitation'))
        self.teacher.driving_balance=True
        if self.uses_teacher:self.actor=self.teacher.weights

    @property
    def uses_teacher(self):return self.phase=='imitation'

    def sample(self,obs):
        if not self.uses_teacher:return super().sample(obs)
        mean=forward(self.actor,obs,self.hidden)
        return np.tanh(mean),mean,np.zeros(len(obs)),np.zeros(len(obs))

    def learn_step(self,obs,targets,active):
        self.teacher.driving_balance=True;self.teacher.input_contract=self.input_contract
        self.teacher.learn_step(obs,targets,active)
        self.actor=self.teacher.weights
        self.hybrid['imitationSteps']+=int(np.sum(active))

    def update(self,scores):
        result=self.teacher.update(scores)
        result['recipePhase']='Imitazione'
        return result

    def remember(self,*args):
        if self.uses_teacher:raise RuntimeError('Dimostrazioni non ammesse nel rollout PPO')
        self.hybrid['reinforcementSteps']+=len(args[0])
        return super().remember(*args)

    def transition(self,proof):
        self.hybrid['checks']+=1;self.hybrid['proof']=deepcopy(proof)
        if not proof['passed'] or not self.uses_teacher:return False
        if proof.get('launches',0)<18 or proof.get('laps',0)<18 or proof.get('endurance',0)<4:
            raise ValueError('Prove ibride insufficienti')
        source=self.policy()
        if proof['policyHash']!=digest(source):raise ValueError('Verifica di un altro modello')
        self.hybrid.update(phase='reinforcement',imitationPolicy=deepcopy(source),
            sourceHash=digest(source),initialActionStd=.1)
        self.phase='reinforcement'
        # Preserve actor exactly. Critic, optimizer moments and on-policy data start afresh.
        self.actor=self.actor.copy();self.critic=random_weights(self.rng,self.hidden,1,inputs=self.inputs)
        self.actor_adam=Adam(len(self.actor));self.critic_adam=Adam(len(self.critic));self.std_adam=Adam(2)
        self.log_std=np.full(2,math.log(.1));self.buffer=[];self.pending=None
        return True

    def candidate_policy(self):return self.policy()

    def policy(self):
        p=super().policy()
        p['recipe']=dict(version=RECIPE,phase=self.phase,teacher='traffic-pursuit-2',
            sourceHash=self.hybrid.get('sourceHash'),variant=self.profile.get('variant','standard'))
        return p

    def change_reward(self):
        self.teacher.change_reward()

    def checkpoint(self):
        result=super().checkpoint()
        result.update(algorithm='clone_ppo',hybrid=deepcopy(self.hybrid),
            imitation=self.teacher.checkpoint())
        return result


class HybridGate:
    """20 launches, 20 laps, 5 endurance episodes; no optimization or model changes."""
    def __init__(self,policy,track,saved=None):
        from game_academy import Episode
        self.policy=deepcopy(policy);self.track=track;self.cursor=0;self.steps=0
        self.episodes=[]
        for i in range(45):
            mode='impara_infinito' if i>=40 else 'impara'
            self.episodes.append(Episode(track,'launch' if i<20 else 'control',11200100+i,
                protocol='driving-memory-1',launch_distance=20. if i<20 else None,
                objective=mode,single_lap=i<40))
        if saved:
            self.cursor=saved['cursor'];self.steps=saved['steps']
            self.episodes=[Episode(s['track_id'],s['phase'],s['seed'],saved=s) for s in saved['episodes']]
        self.controller=Policy(policy)
        for e in self.episodes:e.world.native_sensors=True

    def tick(self):
        for _ in self.episodes:
            index=self.cursor%45;self.cursor+=1;e=self.episodes[index]
            if e.reason:continue
            e.step(self.controller.act(e.observations(),world=e.world,index=0));self.steps+=1
            if index>=40:
                if e.clean_series>=5:e.reason='success';e.terminated=True
                elif e.age>=max(180.,e.world.track.length*2):e.reason='timeout';e.truncated=True
                elif e.reason=='window':e.next_window()
            break
        return all(e.reason for e in self.episodes)

    def result(self):
        counts=[sum(e.reason=='success' for e in rows) for rows in (
            self.episodes[:20],self.episodes[20:40],self.episodes[40:])]
        return dict(version='hybrid-readiness-1',policyHash=digest(self.policy),
            launches=counts[0],laps=counts[1],endurance=counts[2],steps=self.steps,
            passed=counts[0]>=18 and counts[1]>=18 and counts[2]>=4,
            track=self.track,required=dict(launches=18,laps=18,endurance=4,consecutiveLaps=5))

    def snapshot(self):
        return dict(policy=deepcopy(self.policy),track=self.track,cursor=self.cursor,steps=self.steps,
            episodes=[e.snapshot() for e in self.episodes])
