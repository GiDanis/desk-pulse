"""Small NumPy policies, evolutionary search and clipped Gaussian PPO.

Geometric reference and imitation are explicit methods; reinforcement and evolution act independently.
"""
from __future__ import annotations

import numpy as np
from game_numeric import RolloutBuffer,checkpoint_value

from game_catalog import OBSERVATION_SIZE, OBSERVATION_VERSION, LEGACY_OBSERVATION_VERSION, ACADEMY_OBSERVATION_VERSION, ACTION_VERSION, observation_size, observation_version


def parameters(inputs=OBSERVATION_SIZE, hidden=16, outputs=2):
    return (inputs+1)*hidden+(hidden+1)*outputs


def forward(weights, obs, hidden, outputs=2, cache=False):
    weights = np.asarray(weights)
    obs = np.asarray(obs)
    n = obs.shape[-1]
    split = (n+1)*hidden
    a = weights[..., :split].reshape(*weights.shape[:-1], n+1, hidden)
    b = weights[..., split:].reshape(*weights.shape[:-1], hidden+1, outputs)
    x = np.concatenate((obs, np.ones((*obs.shape[:-1], 1))), axis=-1)
    h = np.tanh(np.einsum('...i,...ij->...j', x, a))
    hb = np.concatenate((h, np.ones((*h.shape[:-1], 1))), axis=-1)
    y = np.einsum('...i,...ij->...j', hb, b)
    return (y, (x,h,hb,a,b)) if cache else y


def backward(cache, dy):
    x,h,hb,a,b = cache
    db = hb.T @ dy
    dh = (dy @ b[:-1].T)*(1-h*h)
    da = x.T @ dh
    return np.concatenate((da.ravel(),db.ravel()))


def random_weights(rng, hidden, outputs=2, inputs=OBSERVATION_SIZE):
    w = rng.normal(0,0.5,parameters(inputs=inputs,hidden=hidden,outputs=outputs))
    # Fan-in normalization, with randomly sampled biases as well.
    w[:(inputs+1)*hidden] /= np.sqrt(inputs)
    w[(inputs+1)*hidden:] /= np.sqrt(hidden)
    return w


def policy_snapshot(weights, hidden, algorithm='evolution'):
    inputs=int((len(weights)-(hidden+1)*2)/hidden-1)
    version=observation_version(inputs)
    return {'schema':1,'kind':'dense','algorithm':algorithm,'observation':version,
            'action':ACTION_VERSION,'inputs':inputs,'hidden':hidden,
            'weights':np.asarray(weights).tolist()}


class Policy:
    def __init__(self, snapshot):
        if snapshot.get('schema')!=1 or snapshot.get('observation') not in (OBSERVATION_VERSION,LEGACY_OBSERVATION_VERSION,ACADEMY_OBSERVATION_VERSION) or snapshot.get('action')!=ACTION_VERSION:
            raise ValueError('Modello incompatibile con pista/sensori')
        self.snapshot = snapshot
        self.kind = snapshot['kind']
        self.inputs=observation_size(snapshot['observation'])
        if self.kind=='dense':
            self.hidden = snapshot['hidden']
            self.weights = np.asarray(snapshot['weights'],dtype=float)
            if self.weights.shape!=(parameters(inputs=self.inputs,hidden=self.hidden),) or not np.isfinite(self.weights).all():
                raise ValueError('Pesi non validi')
        elif self.kind in ('reference','geometric'):
            pass
        elif self.kind!='neat':
            raise ValueError('Rete sconosciuta')

    def act(self, observation, world=None, index=None):
        if self.kind=='geometric' and observation is None:
            if world is None or self.snapshot.get('track')!=world.track.id:
                raise ValueError('Il controllore geometrico richiede il circuito proprio')
            from game_control import pursuit_actions,racing_actions
            result=(racing_actions if self.snapshot.get('controller')=='traffic-pursuit-2' else pursuit_actions)(world,index)
            return result[0] if index is not None else result
        obs = np.asarray(observation, dtype=float)
        if obs.shape[-1]<self.inputs or not np.isfinite(obs).all():
            raise ValueError('Osservazione non valida')
        obs=obs[...,:self.inputs]
        if self.kind=='geometric':
            if world is None:raise ValueError('Il controllore geometrico richiede il mondo fisico')
            if self.snapshot.get('track')!=world.track.id:raise ValueError('Controllore di un altro circuito')
            from game_control import pursuit_actions,racing_actions
            result=(racing_actions if self.snapshot.get('controller')=='traffic-pursuit-2' else pursuit_actions)(world,index)
            return result[0] if obs.ndim==1 else result
        if self.kind=='dense':
            return np.tanh(forward(self.weights,obs,self.hidden))
        if self.kind in ('reference','geometric'):
            single = (obs.ndim == 1)
            rows = np.atleast_2d(obs)
            steer = np.clip(rows[:, 10]*2.6 + rows[:, 9]*0.7, -1, 1)
            accel = np.clip((10 - rows[:, 5]*30)*0.3, -1, 1)
            res = np.column_stack((steer, accel))
            return res[0] if single else res
        result=[]
        for row in np.atleast_2d(obs):
            values = {-i-1:float(v) for i,v in enumerate(row)}
            for node in self.snapshot['nodes']:
                total = sum(values[source]*weight for source,weight in node['links'])
                values[node['id']] = float(np.tanh(2.5*(node['bias']+node['response']*total)))
            result.append([values.get(0,0),values.get(1,0)])
        result=np.asarray(result)
        return result[0] if obs.ndim==1 else result


class PurePursuit:
    """Reference controller; it has no optimizer or training counters."""
    def __init__(self, profile, checkpoint=None, track_id='oval-1'):
        self.profile=profile
        self.track_id=track_id
        self.generation=0
        self.best_score=None

    def act(self, observations, world=None):
        return Policy(self.policy()).act(observations,world=world)

    def policy(self):
        from game_profiles import reference_policy
        return reference_policy(self.track_id)

    candidate_policy=policy

    def update(self, scores):
        raise ValueError('Il riferimento geometrico non si allena')

    def checkpoint(self):
        return {'algorithm':'pure_pursuit','controller':'pure-pursuit-1','track':self.track_id}


class Imitation:
    def __init__(self, profile, checkpoint=None):
        self.profile = profile
        self.hidden = profile['hidden']
        self.inputs=observation_size(profile['observation'])
        self.rng = np.random.default_rng(profile['seed'])
        self.generation = 0
        self.best_score = None
        self.weights = random_weights(self.rng, self.hidden, inputs=self.inputs)
        self.best = self.weights.copy()
        self.samples=[]
        self.sample_count=0
        self.adam = Adam(len(self.weights), checkpoint.get('adam') if checkpoint else None)
        if checkpoint:
            self.weights = np.asarray(checkpoint['weights'])
            self.best = np.asarray(checkpoint.get('best', self.weights))
            self.generation = checkpoint.get('generation', 0)
            self.best_score = checkpoint.get('bestScore')
            self.rng.bit_generator.state = checkpoint['rng']
            self.samples=[(np.asarray(x,dtype=float),np.asarray(y,dtype=float)) for x,y in checkpoint.get('examples',[])]
            self.sample_count=checkpoint.get('sampleCount',0)

    def act(self, observations):
        obs = np.asarray(observations, dtype=float)
        y = forward(self.weights, obs, self.hidden)
        return np.tanh(y)

    def learn_step(self, observations, targets=None, active=None):
        """Bounded DAgger-style aggregation, labeled by an explicit teacher."""
        rows=np.atleast_2d(np.asarray(observations,dtype=float))
        if targets is None:raise ValueError('Servono azioni del maestro')
        target=np.atleast_2d(np.asarray(targets,dtype=float))
        mask=np.ones(len(rows),dtype=bool) if active is None else np.asarray(active,dtype=bool)
        if getattr(self,'driving_balance',False):
            from game_numeric import ExampleBuffer
            if not hasattr(self,'_examples'):self._examples=ExampleBuffer(self.inputs,self.samples)
            for x,y in zip(rows[mask],target[mask]):self._examples.append(x,y)
            self.sample_count+=int(mask.sum())
            if not mask.any() or self.sample_count//128==(self.sample_count-int(mask.sum()))//128:return
            x,target=self._examples.sample(self.rng)
            y,cache=forward(self.weights,x,self.hidden,cache=True);pred=np.tanh(y)
            dy=(pred-target)*(1-pred**2)/len(x)
            self.adam.step(self.weights,backward(cache,dy),self.profile['learningRate'])
            return
        for x,y in zip(rows[mask],target[mask]):self.samples.append((x.copy(),y.copy()))
        self.samples=self.samples[-2048:]
        self.sample_count+=int(mask.sum())
        if not mask.any() or self.sample_count//128==(self.sample_count-int(mask.sum()))//128:return
        selected=self.rng.integers(0,len(self.samples),min(128,len(self.samples)))
        batch=[self.samples[i] for i in selected]
        x=np.array([r[0] for r in batch]);target=np.array([r[1] for r in batch])
        y,cache=forward(self.weights,x,self.hidden,cache=True);pred=np.tanh(y)
        dy=(pred-target)*(1-pred**2)/len(x)
        self.adam.step(self.weights,backward(cache,dy),self.profile['learningRate'])

    def update(self, scores):
        self.generation += 1
        current = float(np.max(scores)) if len(scores) else 0.0
        if self.best_score is None or current > self.best_score:
            self.best = self.weights.copy()
            self.best_score = current
        return {'generation': self.generation, 'fitness': current, 'bestFitness': self.best_score}

    def policy(self):
        return policy_snapshot(self.best, self.hidden, 'imitation')

    def candidate_policy(self):
        return policy_snapshot(self.weights, self.hidden, 'imitation')

    def change_reward(self):
        self.best_score = None

    def checkpoint(self):
        return {'algorithm': 'imitation', 'generation': self.generation, 'bestScore': self.best_score,
                'weights': self.weights.tolist(), 'best': self.best.tolist(),
                'adam': self.adam.snapshot(), 'rng': self.rng.bit_generator.state,
                'examples':self._examples.snapshot() if hasattr(self,'_examples') else checkpoint_value(self.samples),'sampleCount':self.sample_count,'teacher':'traffic-pursuit-2' if self.profile.get('version')==2 else 'pure-pursuit-1'}


class Evolution:
    def __init__(self, profile, checkpoint=None):
        self.profile = profile
        self.hidden = profile['hidden']
        self.inputs=observation_size(profile['observation'])
        self.rng = np.random.default_rng(profile['seed'])
        self.generation = 0
        self.best_score = None
        self.stagnation=0
        self.mutation_scale=1.0
        self.diversity=0.0
        self.best = random_weights(self.rng,self.hidden,inputs=self.inputs)
        self.population = np.array([random_weights(self.rng,self.hidden,inputs=self.inputs) for _ in range(profile['population'])])
        if checkpoint:
            self.population = np.asarray(checkpoint['population'])
            self.best = np.asarray(checkpoint['best'])
            self.best_score, self.generation = checkpoint['bestScore'], checkpoint['generation']
            self.stagnation=checkpoint.get('stagnation',0)
            self.mutation_scale=checkpoint.get('mutationScale',1.)
            self.diversity=checkpoint.get('diversity',0.)
            if checkpoint.get('candidate') is not None:self.candidate=np.asarray(checkpoint['candidate'])
            self.rng.bit_generator.state = checkpoint['rng']

    def act(self, observations):
        return np.tanh(forward(self.population,observations,self.hidden))

    def update(self, scores):
        order = np.argsort(-np.asarray(scores),kind='stable')
        current = float(scores[order[0]])
        self.candidate = self.population[order[0]].copy()
        improved=self.best_score is None or current>self.best_score
        self.stagnation=0 if improved else self.stagnation+1
        self.mutation_scale=min(2.,1.+self.stagnation/20.)
        self.diversity=float(np.mean(np.std(self.population,axis=0)))
        if improved:
            self.best, self.best_score = self.population[order[0]].copy(), current
        count=len(self.population)
        elite=max(2,count//8)
        parents=self.population[order[:elite]].copy()
        population=parents[self.rng.integers(0,elite,count)].copy()
        noise=self.rng.normal(0,self.profile['mutation']*self.mutation_scale,population.shape)
        population+=noise*(self.rng.random(population.shape)<0.25)
        population[:elite]=parents
        population[0]=self.best
        # A few independent starts preserve exploration when the population stagnates.
        population[-1]=random_weights(self.rng,self.hidden,inputs=self.inputs)
        if getattr(self,'driving_balance',False) and count>=8:
            # Two actual weight-space candidates explore release/braking. They
            # must earn their own fitness; no pedal is overridden at inference.
            population[-3]=parents[0];population[-3,-1]-=1.
            population[-2]=parents[0];population[-2,-1]-=2.
        self.population=population
        self.generation+=1
        return {'generation':self.generation,'fitness':current,'bestFitness':self.best_score,
                'mutationScale':self.mutation_scale,'stagnation':self.stagnation,'diversity':self.diversity}

    def policy(self):
        return policy_snapshot(self.best,self.hidden)

    def candidate_policy(self):
        return policy_snapshot(getattr(self,'candidate',self.best),self.hidden)

    def change_reward(self):
        self.best_score=None;self.stagnation=0;self.mutation_scale=1.

    def checkpoint(self):
        return {'algorithm':'evolution','generation':self.generation,'bestScore':self.best_score,
                'mutationVersion':'stagnation-1','stagnation':self.stagnation,
                'mutationScale':self.mutation_scale,'diversity':self.diversity,
                'best':self.best.tolist(),'population':self.population.tolist(),
                'candidate':self.candidate.tolist() if hasattr(self,'candidate') else None,
                'rng':self.rng.bit_generator.state}


class Adam:
    def __init__(self, size, checkpoint=None):
        self.m,self.v,self.t = np.zeros(size),np.zeros(size),0
        if checkpoint:
            self.m,self.v,self.t=np.array(checkpoint['m']),np.array(checkpoint['v']),checkpoint['t']

    def step(self, params, gradient, rate):
        norm=np.linalg.norm(gradient)
        gradient=gradient*min(1,0.5/max(norm,1e-12))
        self.t+=1
        self.m=0.9*self.m+0.1*gradient
        self.v=0.999*self.v+0.001*gradient**2
        params-=rate*(self.m/(1-0.9**self.t))/(np.sqrt(self.v/(1-0.999**self.t))+1e-8)

    def snapshot(self):
        return {'m':self.m.tolist(),'v':self.v.tolist(),'t':self.t}


def log_probability(raw, mean, log_std):
    return -0.5*np.sum(((raw-mean)/np.exp(log_std))**2+2*log_std+np.log(2*np.pi),axis=-1)


def ppo_gradient(actor, critic, log_std, hidden, obs, raw, old_log, advantages, returns,
                 clip=0.2, entropy=0.001):
    mean,ac = forward(actor,obs,hidden,cache=True)
    value,vc = forward(critic,obs,hidden,outputs=1,cache=True)
    logp = log_probability(raw,mean,log_std)
    ratio=np.exp(np.clip(logp-old_log,-20,20))
    unclipped=ratio*advantages
    clipped=np.clip(ratio,1-clip,1+clip)*advantages
    mask=((advantages>=0)&(ratio<=1+clip))|((advantages<0)&(ratio>=1-clip))
    coefficient=-advantages*ratio*mask/len(obs)
    delta=raw-mean
    variance=np.exp(2*log_std)
    ga=backward(ac,coefficient[:,None]*delta/variance)
    gs=np.sum(coefficient[:,None]*(delta**2/variance-1),axis=0)-entropy
    gv=backward(vc,(value-returns[:,None])/len(obs))
    loss=-float(np.mean(np.minimum(unclipped,clipped)))-entropy*float(np.sum(log_std+0.5*np.log(2*np.pi*np.e)))
    value_loss=float(np.mean((value[:,0]-returns)**2)/2)
    return loss,value_loss,ga,gv,gs


class PPO:
    def __init__(self, profile, checkpoint=None):
        self.profile,self.hidden = profile,profile['hidden']
        self.inputs=observation_size(profile['observation'])
        self.rng=np.random.default_rng(profile['seed'])
        self.actor=random_weights(self.rng,self.hidden,inputs=self.inputs)
        self.critic=random_weights(self.rng,self.hidden,1,inputs=self.inputs)
        self.log_std=np.array([-0.8,-0.8])
        self.update_index=0
        self.buffer=[]
        self.pending=None
        if checkpoint:
            self.actor,self.critic,self.log_std=map(np.array,(checkpoint['actor'],checkpoint['critic'],checkpoint['logStd']))
            self.update_index=checkpoint['update']
            self.rng.bit_generator.state=checkpoint['rng']
            self.buffer=checkpoint.get('buffer',[])
            self.pending=checkpoint.get('pending')
        self.actor_adam=Adam(len(self.actor),checkpoint.get('actorAdam') if checkpoint else None)
        self.critic_adam=Adam(len(self.critic),checkpoint.get('criticAdam') if checkpoint else None)
        self.std_adam=Adam(2,checkpoint.get('stdAdam') if checkpoint else None)
        self.tuning=dict(gaeLambda=.95,batchSize=64,clip=.2,entropy=.001,targetKL=None)
        self.configured=False
        if checkpoint and checkpoint.get('tuning'):self.configure_runtime(checkpoint['tuning'])

    def configure_runtime(self,values):
        from game_driving_memory import PPO_DEFAULTS
        q={**PPO_DEFAULTS,**values}
        if not 0<q['gaeLambda']<=1 or q['batchSize'] not in (32,64,128,256,512) or not 0<q['clip']<1 or not 0<=q['entropy']<1 or (q['targetKL'] is not None and not 0<q['targetKL']<1):
            raise ValueError('Configurazione PPO non valida')
        self.tuning=q;self.configured=True

    @property
    def buffer(self):return self._buffer

    @buffer.setter
    def buffer(self,value):
        if not len(value) and hasattr(self,'_buffer'):
            self._buffer.clear()
        else:self._buffer=RolloutBuffer(self.profile['rollout'],value)

    def sample(self, obs):
        mean=forward(self.actor,obs,self.hidden)
        raw=mean+self.rng.normal(size=mean.shape)*np.exp(self.log_std)
        value=forward(self.critic,obs,self.hidden,1)[:,0]
        return np.tanh(raw),raw,log_probability(raw,mean,self.log_std),value

    def remember(self, obs, raw, logp, value, reward, done, next_obs, terminated=None):
        next_value=forward(self.critic,np.asarray(next_obs)[...,:self.inputs],self.hidden,1)[:,0]
        terminated=done if terminated is None else terminated
        self.buffer.append((obs,raw,logp,value,reward,done,next_value,terminated))

    def updates(self):
        if self.pending is None:
            obs,raw,old_log,value,reward,done,next_value,terminated=self.buffer.arrays()
            gae=np.zeros(reward.shape[1]); advantage=np.zeros_like(reward)
            for t in range(len(reward)-1,-1,-1):
                cont=1-done[t]
                delta=reward[t]+self.profile['gamma']*next_value[t]*(1-terminated[t])-value[t]
                gae=delta+self.profile['gamma']*self.tuning['gaeLambda']*cont*gae
                advantage[t]=gae
            returns=advantage+value
            advantage=(advantage-advantage.mean())/(advantage.std()+1e-8)
            self.pending={'flat':[x.reshape((-1,*x.shape[2:])) for x in (obs,raw,old_log,advantage,returns)],
                          'epoch':0,'start':0,'order':None,'epochs':self.profile['epochs']}
            self.buffer=[]
        flat=[np.asarray(x) for x in self.pending['flat']]
        count=len(flat[0]);pending=self.pending
        while pending['epoch']<pending['epochs']:
            if pending['order'] is None:pending['order']=self.rng.permutation(count)
            start=pending['start'];size=self.tuning['batchSize'];order=np.asarray(pending['order'][start:start+size])
            batch=[x[order] for x in flat]
            loss,vl,ga,gv,gs=ppo_gradient(self.actor,self.critic,self.log_std,self.hidden,*batch,clip=self.tuning['clip'],entropy=self.tuning['entropy'])
            diagnostics={}
            if self.configured:
                mean=forward(self.actor,batch[0],self.hidden)
                log_ratio=log_probability(batch[1],mean,self.log_std)-batch[2]
                kl=float(np.mean(np.exp(np.clip(log_ratio,-20,20))-1-log_ratio))
                values=forward(self.critic,batch[0],self.hidden,1)[:,0]
                diagnostics=dict(approxKL=kl,clipFraction=float(np.mean(np.abs(np.exp(np.clip(log_ratio,-20,20))-1)>self.tuning['clip'])),
                    explainedVariance=float(1-np.var(batch[4]-values)/max(np.var(batch[4]),1e-12)))
                if self.tuning['targetKL'] is not None and kl>self.tuning['targetKL']:
                    pending['epoch']=pending['epochs']
                    yield dict(update=self.update_index+1,loss=loss,valueLoss=vl,earlyStop=True,**diagnostics)
                    break
            if not all(np.isfinite(x).all() for x in (ga,gv,gs)):
                raise RuntimeError('Gradiente PPO non finito')
            rate=self.profile['learningRate']
            self.actor_adam.step(self.actor,ga,rate)
            self.critic_adam.step(self.critic,gv,rate)
            self.std_adam.step(self.log_std,gs,rate)
            self.log_std=np.clip(self.log_std,-3,0.5)
            pending['start']+=size
            if pending['start']>=count:
                pending['epoch']+=1;pending['start']=0;pending['order']=None
            yield {'update':self.update_index+1,'loss':loss,'valueLoss':vl,**diagnostics}
        self.buffer=[]
        self.pending=None
        self.update_index+=1

    def policy(self):
        return policy_snapshot(self.actor,self.hidden,'ppo')

    def checkpoint(self):
        result={'algorithm':'ppo','actor':self.actor.tolist(),'critic':self.critic.tolist(),
                'logStd':self.log_std.tolist(),'update':self.update_index,'buffer':self.buffer.snapshot(),'pending':checkpoint_value(self.pending),
                'rng':self.rng.bit_generator.state,'actorAdam':self.actor_adam.snapshot(),
                'criticAdam':self.critic_adam.snapshot(),'stdAdam':self.std_adam.snapshot()}
        if self.configured:result['tuning']=dict(self.tuning)
        return result


class PPOSmooth(PPO):
    """PPO with standard exact Gaussian likelihood and a physical control cost.

    Historical OU experience is discarded on migration; actor weights survive.
    Smoothness comes from the environment objective, not biased likelihoods.
    """
    def __init__(self,profile,checkpoint=None):
        if checkpoint and checkpoint.get('explorationVersion')!='gaussian-control-cost-2':
            checkpoint={**checkpoint,'buffer':[],'pending':None}
        super().__init__(profile,checkpoint)

    def policy(self):return policy_snapshot(self.actor,self.hidden,'ppo_smooth')

    def checkpoint(self):
        result=super().checkpoint()
        result.update(algorithm='ppo_smooth',explorationVersion='gaussian-control-cost-2')
        return result
