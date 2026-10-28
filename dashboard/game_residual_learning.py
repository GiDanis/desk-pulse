"""Small residual PPO/SAC/TD3 with explicit replay, targets and RNG checkpoints."""
from copy import deepcopy
import math
import base64
import zlib
import numpy as np
from game_learning import PPO,Adam,forward,backward,random_weights
from game_residual import initial_weights,snapshot,recipe
from game_numeric import checkpoint_value


def input_gradient(cache):
    x,h,hb,a,b=cache
    return ((np.ones((len(x),1))@b[:-1].T)*(1-h*h))@a[:-1].T


def critic_gradient(weights,inputs,targets,hidden):
    value,cache=forward(weights,inputs,hidden,1,cache=True)
    error=value[:,0]-targets
    return float(np.mean(error**2)),backward(cache,(2*error/len(inputs))[:,None])


def sac_actor_gradient(actor,log_std,q1,q2,obs,epsilon,hidden,alpha,actor_inputs=None,actor_backward=None):
    mean,cache=forward(actor,obs[...,:actor_inputs],hidden,cache=True)
    std=np.exp(log_std);raw=mean+epsilon*std;action=np.tanh(raw)
    inputs=np.c_[obs,action]
    v1,c1=forward(q1,inputs,hidden,1,cache=True);v2,c2=forward(q2,inputs,hidden,1,cache=True)
    dq=np.where(v1<=v2,input_gradient(c1)[:,-2:],input_gradient(c2)[:,-2:])
    derivative=alpha*2*action-dq*(1-action**2)
    ga=(actor_backward or backward)(cache,derivative/len(obs))
    gs=np.mean(derivative*epsilon*std-alpha,axis=0)
    logp=(-.5*(epsilon**2+math.log(2*math.pi))-log_std-np.log(1-action**2+1e-8)).sum(axis=1)
    return float(np.mean(alpha*logp-np.minimum(v1[:,0],v2[:,0]))),ga,gs


class ResidualPPO(PPO):
    def __init__(self,profile,checkpoint=None):
        self.public_profile=deepcopy(profile)
        inner={**profile,'observation':'race-residual-90-v1'}
        super().__init__(inner,checkpoint)
        spec=recipe(profile);modern=spec['version']=='race-residual-4'
        self.potential_prior=spec.get('potentialPrior',False)
        self.critic_inputs=94 if modern else 90
        self.configure_runtime(dict(gaeLambda=spec['gaeLambda'],batchSize=64,clip=.1,
            entropy=spec.get('ppoEntropy',0.),targetKL=.025,
            minLogStd=np.log(spec['minStd']).tolist() if modern else -6.,
            maxLogStd=np.log(spec['maxStd']).tolist() if modern else -1.5))
        if not checkpoint:
            self.actor=initial_weights(profile);self.log_std=np.log(spec['exploration'])
            if modern:
                self.critic=random_weights(np.random.default_rng(profile['seed']+9107),self.hidden,1,inputs=94)
                self.critic_adam=Adam(len(self.critic))
            self.critic[(self.critic_inputs+1)*self.hidden:]=0

    def sample(self,obs):
        obs=np.asarray(obs)
        if obs.shape[-1]==90 and self.critic_inputs==94:obs=np.pad(obs,((0,0),(0,4)))
        return super().sample(obs)

    def value_offset(self,obs):
        if not self.potential_prior:return 0.
        from game_residual import potential_from_value_features
        return potential_from_value_features(obs)

    def remember(self,obs,raw,logp,value,reward,done,next_obs,terminated=None):
        if self.critic_inputs==94 and np.asarray(obs).shape[-1]==90:
            obs=np.pad(obs,((0,0),(0,4)));next_obs=np.pad(next_obs,((0,0),(0,4)))
        return super().remember(obs,raw,logp,value,reward,done,next_obs,terminated)

    def policy(self):return snapshot(self.public_profile,self.actor)
    candidate_policy=policy


class OffPolicy:
    def __init__(self,profile,checkpoint=None):
        self.profile=deepcopy(profile);self.hidden=profile['hidden'];self.inputs=90
        self.method='td3' if profile['algorithm'] in ('residual_td3','residual_tactic') else 'sac'
        self.spec=recipe(profile);self.rng=np.random.default_rng(profile['seed'])
        self.context=self.spec['version']=='race-residual-4';self.value_inputs=94 if self.context else 90
        self.row_width=192 if self.context else 184
        self.backup_steps=self.spec.get('backupSteps',1)
        if self.backup_steps>1:self.row_width+=1
        self.pending_transitions=deepcopy((checkpoint or {}).get('pendingTransitions',[]))
        self.actor=initial_weights(profile)
        self.q1=random_weights(self.rng,self.hidden,1,inputs=self.value_inputs+2)
        self.q2=random_weights(self.rng,self.hidden,1,inputs=self.value_inputs+2)
        self.q1[(self.value_inputs+3)*self.hidden:]=0;self.q2[(self.value_inputs+3)*self.hidden:]=0
        self.target1=self.q1.copy();self.target2=self.q2.copy();self.target_actor=self.actor.copy()
        self.log_std=np.log(self.spec['exploration']);self.update_index=0;self.count=0;self.cursor=0;self.transitions=0
        self.capacity=self.spec['replayCapacity'];self.replay=np.empty((self.capacity,self.row_width))
        self.pending=None
        if checkpoint:
            if checkpoint.get('method')!=self.method:raise ValueError('Algoritmo del checkpoint incompatibile')
            for name in ('actor','q1','q2','target1','target2','target_actor','log_std'):
                setattr(self,name,np.asarray(checkpoint[name],dtype=float))
            self.update_index=checkpoint['update'];self.transitions=checkpoint['transitions']
            if 'replayBinary' in checkpoint:
                data=checkpoint['replayBinary']
                count=data['count']
                if type(count) is not int or not 0<=count<=self.capacity:raise ValueError('Dimensioni replay non valide')
                packed=zlib.decompress(base64.b64decode(data['data']))
                if data.get('width',184)!=self.row_width or len(packed)!=count*self.row_width*8:raise ValueError('Replay binario danneggiato o vecchio contesto')
                rows=np.frombuffer(packed,dtype='<f8').reshape(count,self.row_width).copy()
            else:rows=np.asarray(checkpoint['replay'],dtype=float)
            if rows.size:
                if rows.shape[1]!=self.row_width or len(rows)>self.capacity:raise ValueError('Replay incompatibile')
                self.replay[:len(rows)]=rows
            self.count=len(rows);self.cursor=checkpoint.get('cursor',self.count%self.capacity);self.rng.bit_generator.state=checkpoint['rng']
        for name,weights in (('actorAdam',self.actor),('q1Adam',self.q1),('q2Adam',self.q2),('stdAdam',self.log_std)):
            setattr(self,name,Adam(len(weights),(checkpoint or {}).get(name)))

    def sample(self,obs):
        mean=forward(self.actor,np.atleast_2d(obs)[...,:90],self.hidden)
        return np.tanh(mean+self.rng.normal(size=mean.shape)*np.exp(self.log_std))

    def write_transition(self,obs,action,reward,next_obs,terminated,discount):
        row=np.r_[np.asarray(obs)[:90],action,reward,np.asarray(next_obs)[:90],float(terminated)]
        if self.context:
            row=np.r_[row,np.asarray(obs)[90:94] if len(obs)>=94 else np.zeros(4),np.asarray(next_obs)[90:94] if len(next_obs)>=94 else np.zeros(4)]
        if self.backup_steps>1:row=np.r_[row,discount]
        self.replay[self.cursor]=row
        self.cursor=(self.cursor+1)%self.capacity;self.count=min(self.count+1,self.capacity)

    def remember(self,obs,action,reward,next_obs,terminated,episode_done=False):
        self.transitions+=1
        if self.backup_steps==1:
            self.write_transition(obs,action,reward,next_obs,terminated,self.spec['gamma'])
            return
        self.pending_transitions.append(dict(obs=np.asarray(obs).tolist(),action=np.asarray(action).tolist(),
            reward=float(reward),next=np.asarray(next_obs).tolist(),terminal=bool(terminated)))
        while self.pending_transitions and (len(self.pending_transitions)>=self.backup_steps or terminated or episode_done):
            group=self.pending_transitions[:self.backup_steps]
            total=0.;discount=1.
            for item in group:
                total+=discount*item['reward'];discount*=self.spec['gamma']
                if item['terminal']:break
            first=self.pending_transitions[0]
            self.write_transition(first['obs'],first['action'],total,item['next'],item['terminal'],discount)
            self.pending_transitions.pop(0)

    def value_offset(self,obs):return 0.

    def actor_update_ready(self):return True

    def actor_gradient(self,gradient,obs):return gradient

    def actor_learning_rate(self):return self.profile['learningRate']

    def actor_backward(self,cache,derivative):return backward(cache,derivative)

    def apply_actor_gradient(self,gradient,obs,rate):
        self.actorAdam.step(self.actor,gradient,rate)

    def sample_indices(self):
        return self.rng.integers(0,self.count,self.spec['batchSize'])

    def update(self):
        if self.count<128 or self.transitions%self.spec['gradientEvery']:return None
        batch=self.replay[self.sample_indices()]
        obs=batch[:,:90];action=batch[:,90:92];reward=batch[:,92];nxt=batch[:,93:183];terminal=batch[:,183]
        value_obs=np.c_[obs,batch[:,184:188]] if self.context else obs
        value_next=np.c_[nxt,batch[:,188:192]] if self.context else nxt
        if self.method=='sac':
            epsilon=self.rng.normal(size=action.shape);raw=forward(self.actor,nxt,self.hidden)+epsilon*np.exp(self.log_std)
            target_action=np.tanh(raw)
            logp=(-.5*(epsilon**2+math.log(2*math.pi))-self.log_std-np.log(1-target_action**2+1e-8)).sum(axis=1)
        else:
            target_action=np.clip(np.tanh(forward(self.target_actor,nxt,self.hidden))+np.clip(self.rng.normal(0,self.spec.get('targetNoise',.05),action.shape),-self.spec.get('targetClip',.1),self.spec.get('targetClip',.1)),-1,1)
            logp=0.
        q=np.minimum(forward(self.target1,np.c_[value_next,target_action],self.hidden,1)[:,0],
                     forward(self.target2,np.c_[value_next,target_action],self.hidden,1)[:,0])
        discount=batch[:,-1] if self.backup_steps>1 else self.spec['gamma']
        target=reward+self.value_offset(value_obs)+discount*(1-terminal)*(q-self.value_offset(value_next)-(self.spec['entropy']*logp if self.method=='sac' else 0))
        inputs=np.c_[value_obs,action];losses=[]
        for weights,optimizer in ((self.q1,self.q1Adam),(self.q2,self.q2Adam)):
            loss,gradient=critic_gradient(weights,inputs,target,self.hidden)
            if not np.isfinite(gradient).all():raise RuntimeError('Critic non finito')
            optimizer.step(weights,gradient,self.profile['learningRate']);losses.append(loss)
        self.update_index+=1;actor_loss=None
        if self.method=='sac' and self.actor_update_ready():
            actor_loss,ga,gs=sac_actor_gradient(self.actor,self.log_std,self.q1,self.q2,value_obs,self.rng.normal(size=action.shape),self.hidden,self.spec['entropy'],actor_inputs=90,actor_backward=self.actor_backward)
            self.stdAdam.step(self.log_std,gs,self.profile['learningRate']);self.log_std=np.clip(self.log_std,np.log(self.spec['minStd']) if self.context else -6,np.log(self.spec['maxStd']) if self.context else -1.5)
        elif self.method=='td3' and self.actor_update_ready() and self.update_index%self.spec['policyDelay']==0:
            act,cache=forward(self.actor,obs,self.hidden,cache=True);act=np.tanh(act)
            values,qcache=forward(self.q1,np.c_[value_obs,act],self.hidden,1,cache=True)
            ga=self.actor_backward(cache,-input_gradient(qcache)[:,-2:]*(1-act**2)/len(obs))
            actor_loss=-float(values.mean())
        if actor_loss is not None:
            if not np.isfinite(ga).all():raise RuntimeError('Actor non finito')
            self.apply_actor_gradient(self.actor_gradient(ga,obs),obs,self.actor_learning_rate())
        if self.method=='sac' or actor_loss is not None:
            for target_weights,source in ((self.target1,self.q1),(self.target2,self.q2),(self.target_actor,self.actor)):
                target_weights+=(source-target_weights)*self.spec['tau']
        return dict(update=self.update_index,valueLoss=float(np.mean(losses)),actorLoss=actor_loss,replay=self.count)

    def policy(self):return snapshot(self.profile,self.actor)
    candidate_policy=policy

    def checkpoint(self,deferred=False):
        result=dict(method=self.method,**{n:getattr(self,n).tolist() for n in ('actor','q1','q2','target1','target2','target_actor','log_std')},
            update=self.update_index,transitions=self.transitions,cursor=self.cursor,
            rng=deepcopy(self.rng.bit_generator.state),
            **(dict(pendingTransitions=deepcopy(self.pending_transitions),backupSteps=self.backup_steps) if self.backup_steps>1 else {}),
            **{n:getattr(self,n).snapshot() for n in ('actorAdam','q1Adam','q2Adam','stdAdam')})

        if deferred:result['_replaySnapshot']=self.replay[:self.count].astype('<f8',copy=deferred!='writer')
        else:result['replayBinary']=encode_replay(self.replay[:self.count])
        return result


def encode_replay(rows):
    return dict(encoding='zlib-f64-le-1',count=len(rows),width=rows.shape[1],
        data=base64.b64encode(zlib.compress(rows.astype('<f8',copy=False).tobytes(),1)).decode())


def encode_checkpoint(checkpoint):
    """Consume a detached snapshot, never the live replay or learner."""
    learner=checkpoint.get('learner',{})
    if '_replaySnapshot' in learner:learner['replayBinary']=encode_replay(learner.pop('_replaySnapshot'))
    return checkpoint
