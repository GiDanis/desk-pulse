"""Small NumPy policies, evolutionary search and clipped Gaussian PPO.

No reference controller is used to initialize or override learned actions.
"""
from __future__ import annotations

import numpy as np

from game_catalog import OBSERVATION_SIZE, OBSERVATION_VERSION, ACTION_VERSION


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


def random_weights(rng, hidden, outputs=2):
    w = rng.normal(0,0.5,parameters(hidden=hidden,outputs=outputs))
    # Fan-in normalization, with randomly sampled biases as well.
    w[:(OBSERVATION_SIZE+1)*hidden] /= np.sqrt(OBSERVATION_SIZE)
    w[(OBSERVATION_SIZE+1)*hidden:] /= np.sqrt(hidden)
    return w


def policy_snapshot(weights, hidden, algorithm='evolution'):
    return {'schema':1,'kind':'dense','algorithm':algorithm,'observation':OBSERVATION_VERSION,
            'action':ACTION_VERSION,'inputs':OBSERVATION_SIZE,'hidden':hidden,
            'weights':np.asarray(weights).tolist()}


class Policy:
    def __init__(self, snapshot):
        if snapshot.get('schema')!=1 or snapshot.get('observation')!=OBSERVATION_VERSION or snapshot.get('action')!=ACTION_VERSION:
            raise ValueError('Modello incompatibile con pista/sensori')
        self.snapshot = snapshot
        self.kind = snapshot['kind']
        if self.kind=='dense':
            self.hidden = snapshot['hidden']
            self.weights = np.asarray(snapshot['weights'],dtype=float)
            if self.weights.shape!=(parameters(hidden=self.hidden),) or not np.isfinite(self.weights).all():
                raise ValueError('Pesi non validi')
        elif self.kind!='neat':
            raise ValueError('Rete sconosciuta')

    def act(self, observation):
        obs = np.asarray(observation, dtype=float)
        if obs.shape[-1]!=OBSERVATION_SIZE or not np.isfinite(obs).all():
            raise ValueError('Osservazione non valida')
        if self.kind=='dense':
            return np.tanh(forward(self.weights,obs,self.hidden))
        result=[]
        for row in np.atleast_2d(obs):
            values = {-i-1:float(v) for i,v in enumerate(row)}
            for node in self.snapshot['nodes']:
                total = sum(values[source]*weight for source,weight in node['links'])
                values[node['id']] = float(np.tanh(2.5*(node['bias']+node['response']*total)))
            result.append([values.get(0,0),values.get(1,0)])
        result=np.asarray(result)
        return result[0] if obs.ndim==1 else result


class Evolution:
    def __init__(self, profile, checkpoint=None):
        self.profile = profile
        self.hidden = profile['hidden']
        self.rng = np.random.default_rng(profile['seed'])
        self.generation = 0
        self.best_score = None
        self.best = random_weights(self.rng,self.hidden)
        self.population = np.array([random_weights(self.rng,self.hidden) for _ in range(profile['population'])])
        if checkpoint:
            self.population = np.asarray(checkpoint['population'])
            self.best = np.asarray(checkpoint['best'])
            self.best_score, self.generation = checkpoint['bestScore'], checkpoint['generation']
            self.rng.bit_generator.state = checkpoint['rng']

    def act(self, observations):
        return np.tanh(forward(self.population,observations,self.hidden))

    def update(self, scores):
        order = np.argsort(-np.asarray(scores),kind='stable')
        current = float(scores[order[0]])
        self.candidate = self.population[order[0]].copy()
        if self.best_score is None or current>self.best_score:
            self.best, self.best_score = self.population[order[0]].copy(), current
        count=len(self.population)
        elite=max(2,count//8)
        parents=self.population[order[:elite]].copy()
        population=parents[self.rng.integers(0,elite,count)].copy()
        noise=self.rng.normal(0,self.profile['mutation'],population.shape)
        population+=noise*(self.rng.random(population.shape)<0.25)
        population[:elite]=parents
        population[0]=self.best
        # A few independent starts preserve exploration when the population stagnates.
        population[-1]=random_weights(self.rng,self.hidden)
        self.population=population
        self.generation+=1
        return {'generation':self.generation,'fitness':current,'bestFitness':self.best_score}

    def policy(self):
        return policy_snapshot(self.best,self.hidden)

    def candidate_policy(self):
        return policy_snapshot(getattr(self,'candidate',self.best),self.hidden)

    def change_reward(self):
        self.best_score=None

    def checkpoint(self):
        return {'algorithm':'evolution','generation':self.generation,'bestScore':self.best_score,
                'best':self.best.tolist(),'population':self.population.tolist(),
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
        self.rng=np.random.default_rng(profile['seed'])
        self.actor=random_weights(self.rng,self.hidden)
        self.critic=random_weights(self.rng,self.hidden,1)
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

    def sample(self, obs):
        mean=forward(self.actor,obs,self.hidden)
        raw=mean+self.rng.normal(size=mean.shape)*np.exp(self.log_std)
        value=forward(self.critic,obs,self.hidden,1)[:,0]
        return np.tanh(raw),raw,log_probability(raw,mean,self.log_std),value

    def remember(self, obs, raw, logp, value, reward, done, next_obs):
        next_value=forward(self.critic,next_obs,self.hidden,1)[:,0]
        self.buffer.append([x.tolist() for x in (obs,raw,logp,value,reward,done,next_value)])

    def updates(self):
        if self.pending is None:
            data=[np.array([step[i] for step in self.buffer]) for i in range(7)]
            obs,raw,old_log,value,reward,done,next_value=data
            gae=np.zeros(reward.shape[1]); advantage=np.zeros_like(reward)
            for t in range(len(reward)-1,-1,-1):
                cont=1-done[t]
                delta=reward[t]+self.profile['gamma']*next_value[t]*cont-value[t]
                gae=delta+self.profile['gamma']*0.95*cont*gae
                advantage[t]=gae
            returns=advantage+value
            advantage=(advantage-advantage.mean())/(advantage.std()+1e-8)
            self.pending={'flat':[x.reshape((-1,*x.shape[2:])).tolist() for x in (obs,raw,old_log,advantage,returns)],
                          'epoch':0,'start':0,'order':None,'epochs':self.profile['epochs']}
            self.buffer=[]
        flat=[np.asarray(x) for x in self.pending['flat']]
        count=len(flat[0]);pending=self.pending
        while pending['epoch']<pending['epochs']:
            if pending['order'] is None:pending['order']=self.rng.permutation(count).tolist()
            start=pending['start'];order=np.asarray(pending['order'][start:start+64])
            batch=[x[order] for x in flat]
            loss,vl,ga,gv,gs=ppo_gradient(self.actor,self.critic,self.log_std,self.hidden,*batch)
            if not all(np.isfinite(x).all() for x in (ga,gv,gs)):
                raise RuntimeError('Gradiente PPO non finito')
            rate=self.profile['learningRate']
            self.actor_adam.step(self.actor,ga,rate)
            self.critic_adam.step(self.critic,gv,rate)
            self.std_adam.step(self.log_std,gs,rate)
            self.log_std=np.clip(self.log_std,-3,0.5)
            pending['start']+=64
            if pending['start']>=count:
                pending['epoch']+=1;pending['start']=0;pending['order']=None
            yield {'update':self.update_index+1,'loss':loss,'valueLoss':vl}
        self.buffer=[]
        self.pending=None
        self.update_index+=1

    def policy(self):
        return policy_snapshot(self.actor,self.hidden,'ppo')

    def checkpoint(self):
        return {'algorithm':'ppo','actor':self.actor.tolist(),'critic':self.critic.tolist(),
                'logStd':self.log_std.tolist(),'update':self.update_index,'buffer':self.buffer,'pending':self.pending,
                'rng':self.rng.bit_generator.state,'actorAdam':self.actor_adam.snapshot(),
                'criticAdam':self.critic_adam.snapshot(),'stdAdam':self.std_adam.snapshot()}
