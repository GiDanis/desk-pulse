"""Small temporal actors for controlled ablations, trained only in the lab.

Original implementation inspired by recurrent imitation, not copied upstream.
The inputs/outputs are SmartPC's physical telemetry and direct actuators.
"""
import numpy as np
import torch
from torch import nn


class Actor(nn.Module):
    def __init__(self,architecture='gru',hidden=64,history=4,auxiliary=False,*,maneuver_hidden=2,maneuver_scale=1.):
        super().__init__()
        if architecture not in ('dense','history','gru','set-gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep','gru-maneuver'):raise ValueError('Actor architecture')
        self.architecture=architecture;self.hidden=hidden
        self.maneuver_hidden=maneuver_hidden;self.maneuver_scale=maneuver_scale
        self.feature_version='direct-physical-90-v1'
        self.history=history if architecture=='history' else 1
        self.register_buffer('mean',torch.zeros(90))
        self.register_buffer('scale',torch.ones(90))
        if architecture in ('gru','set-gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep','gru-maneuver'):
            if architecture=='set-gru':
                self.ego=nn.Linear(60,64);self.rivals=nn.Linear(10,32)
            self.core=nn.GRU(128 if architecture=='set-gru' else 90,hidden,batch_first=True)
            self.head=nn.Linear(hidden,2)
        else:
            self.core=nn.Linear(90*self.history,hidden)
            self.head=nn.Linear(hidden,2)
        if architecture in ('gru-skip','gru-adapter'):
            self.skip=nn.Linear(90,2,bias=False)
            nn.init.zeros_(self.skip.weight)
        if architecture=='gru-adapter':
            self.adapter=nn.Linear(hidden+90,128)
            self.adapter_head=nn.Linear(128,2,bias=False)
            nn.init.zeros_(self.adapter_head.weight)
        if architecture in ('gru-intent','gru-intent-deep'):
            self.intent=nn.Sequential(nn.Linear(hidden+90,128),nn.Tanh(),nn.Linear(128,2))
            self.intent_skip=nn.Linear(hidden+90,2)
            self.controller=nn.Linear(92,128);self.head=nn.Linear(128,2)
            self.skip=nn.Linear(92,2,bias=False);nn.init.zeros_(self.skip.weight)
            if architecture=='gru-intent-deep':
                self.controller=nn.Sequential(nn.Linear(92,256),nn.Tanh(),nn.Linear(256,256),nn.Tanh())
                self.head=nn.Linear(256,2)
        if architecture=='gru-maneuver':
            del self.head
            self.intent_features=nn.Sequential(nn.Linear(hidden+90,64),nn.Tanh())
            self.intent_core=nn.GRU(64,maneuver_hidden,batch_first=True)
            if maneuver_hidden!=2:self.intent_projection=nn.Linear(maneuver_hidden,2)
            for name in ('steer','pedal'):
                setattr(self,name+'_controller',nn.Sequential(nn.Linear(92,128),nn.Tanh(),nn.Linear(128,128),nn.Tanh()))
                setattr(self,name+'_head',nn.Linear(128,1))
                setattr(self,name+'_skip',nn.Linear(92,1,bias=False))
                nn.init.zeros_(getattr(self,name+'_skip').weight)
        self.auxiliary=bool(auxiliary);self.intent_supervision=auxiliary=='intent'
        if auxiliary:self.aux_head=nn.Linear(hidden,2 if self.intent_supervision else 1)
        if self.intent_supervision:self.aux_classifier=nn.Linear(hidden,3)

    def forward(self,x,state=None):
        if self.architecture=='gru-maneuver':
            latent,plan,state=self.encode_maneuver(x,state);self.last_latent=latent;self.last_plan=plan
            own=torch.cat(((x-self.mean)/self.scale,plan),-1)
            actions=[getattr(self,k+'_head')(getattr(self,k+'_controller')(own))+getattr(self,k+'_skip')(own) for k in ('steer','pedal')]
            return torch.tanh(torch.cat(actions,-1)),state
        z=(x-self.mean)/self.scale
        normalized=z
        if self.architecture in ('gru','set-gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep'):
            if self.architecture=='set-gru':z=self.encode_set(x,z)
            z,state=self.core(z,state)
        else:
            if self.history>1:
                # Left padding repeats the first causal observation.
                prefix=z[:,:1].expand(-1,self.history-1,-1) if state is None else state
                combined=torch.cat((prefix,z),1)
                state=combined[:,-(self.history-1):]
                z=combined.unfold(1,self.history,1).transpose(-1,-2).flatten(-2)
            z=torch.tanh(self.core(z))
        self.last_latent=z
        if self.architecture in ('gru-intent','gru-intent-deep'):
            latent=torch.cat((z,normalized),-1)
            self.last_plan=torch.tanh(self.intent(latent)+self.intent_skip(latent))
            own=torch.cat((normalized,self.last_plan),-1)
            control=self.controller(own) if self.architecture=='gru-intent-deep' else torch.tanh(self.controller(own))
            return torch.tanh(self.head(control)+self.skip(own)),state
        raw=self.head(z)
        if self.architecture in ('gru-skip','gru-adapter'):raw=raw+self.skip(normalized)
        if self.architecture=='gru-adapter':raw=raw+self.adapter_head(torch.tanh(self.adapter(torch.cat((z,normalized),-1))))
        return torch.tanh(raw),state

    def encode_maneuver(self,x,state=None):
        z=(x-self.mean)/self.scale;h,core=self.core(z,None if state is None else state[0])
        initial=self.initial_maneuver(x) if state is None else state[1]
        latent,memory=self.intent_core(self.intent_features(torch.cat((h,z),-1)),initial)
        self.last_maneuver_sequence=latent
        plan=self.project_maneuver(latent)
        return h,plan,(core,memory)

    def initial_maneuver(self,x):
        if self.maneuver_hidden==2:return (-x[:,0,9]).reshape(1,-1,1).expand(-1,-1,2).contiguous()
        return torch.zeros((1,x.shape[0],self.maneuver_hidden),device=x.device,dtype=x.dtype)

    def project_maneuver(self,latent):
        return self.maneuver_scale*torch.tanh(self.intent_projection(latent)) if self.maneuver_hidden!=2 else latent

    def encode_set(self,raw,z):
        own=[*range(11),*range(32,55),*range(64,90)]
        rivals=torch.stack([torch.cat((z[...,11+7*k:18+7*k],z[...,55+3*k:58+3*k]),dim=-1) for k in range(3)],dim=-2)
        present=torch.stack([raw[...,17+7*k]>.5 for k in range(3)],dim=-1)
        encoded=torch.tanh(self.rivals(rivals));masked=encoded*present[...,None]
        maximum=encoded.masked_fill(~present[...,None],-1e9).max(-2).values
        maximum=torch.where(present.any(-1)[...,None],maximum,torch.zeros_like(maximum))
        return torch.cat((torch.tanh(self.ego(z[...,own])),masked.sum(-2)/3,maximum),dim=-1)

    def export(self,*,origin=None,algorithm='residual_td3'):
        def array(x):return x.detach().cpu().numpy().astype(float).tolist()
        weights={k:array(v) for k,v in self.state_dict().items() if k.startswith(('core.','head.','ego.','rivals.','skip.','adapter.','adapter_head.','intent.','intent_skip.','controller.','intent_core.','intent_features.','intent_projection.','steer_controller.','pedal_controller.'))}
        if self.architecture=='gru-maneuver':
            combined=torch.zeros((2,256));combined[0,:128]=self.steer_head.weight[0];combined[1,128:]=self.pedal_head.weight[0]
            weights.update({'head.weight':array(combined),'head.bias':array(torch.cat((self.steer_head.bias,self.pedal_head.bias))),
                'skip.weight':array(torch.cat((self.steer_skip.weight,self.pedal_skip.weight)))})
        from game_direct import ACTION,FEATURES
        result=dict(schema=1,kind='temporal-direct',algorithm=algorithm,observation='race-68-v3',
            action=ACTION,features=self.feature_version,featureInputs=90,inputs=68,decisionHz=10,physicsHz=60,
            teacherAtInference=False,architecture=self.architecture,hidden=self.hidden,history=self.history,
            normalization=dict(mean=array(self.mean),scale=array(self.scale)),weights=weights,origin=origin)
        if self.architecture=='gru-maneuver' and self.maneuver_hidden!=2:result.update(maneuverHidden=self.maneuver_hidden,intentScale=self.maneuver_scale)
        return result


def fit(actor,sequences,*,seed=1,updates=1500,batch=16,length=32,rate=.001,steer_weight=25.):
    """Sample sequences wholly within episodes. Retain causal GRU burn-in."""
    torch.manual_seed(seed);rng=np.random.default_rng(seed)
    optimizer=torch.optim.Adam(actor.parameters(),lr=rate)
    valid=[s for s in sequences if len(s['x'])>=2]
    if not valid:raise ValueError('No complete training sequences')
    all_x=np.concatenate([s['x'] for s in valid])
    with torch.no_grad():
        actor.mean.copy_(torch.as_tensor(np.mean(all_x,axis=0),dtype=torch.float32))
        actor.scale.copy_(torch.as_tensor(np.maximum(.1,np.std(all_x,axis=0)),dtype=torch.float32))
    if actor.architecture=='set-gru':
        with torch.no_grad():
            for coordinates in ([11+7*k+j for k in range(3)] for j in range(7)):
                m=actor.mean[coordinates].mean();v=actor.scale[coordinates].max()
                actor.mean[coordinates]=m;actor.scale[coordinates]=v
            for coordinates in ([55+3*k+j for k in range(3)] for j in range(3)):
                m=actor.mean[coordinates].mean();v=actor.scale[coordinates].max()
                actor.mean[coordinates]=m;actor.scale[coordinates]=v
    losses=[]
    for step in range(updates):
        xs=[];ys=[];masks=[]
        for _ in range(batch):
            s=valid[int(rng.integers(len(valid)))];start=int(rng.integers(max(1,len(s['x'])-length+1)))
            x=s['x'][start:start+length];y=s['y'][start:start+length];n=len(x)
            xs.append(np.pad(x,((0,length-n),(0,0)),mode='edge'))
            ys.append(np.pad(y,((0,length-n),(0,0)),mode='edge'))
            mask=np.arange(length)<n
            # Zero hidden state at a sampled fragment is not the real episode
            # state. Exclude a burn-in prefix; full-episode eval is mandatory.
            if actor.architecture in ('gru','set-gru','gru-skip','gru-adapter') and start>0:mask[:min(8,n-1)]=False
            masks.append(mask)
        x=torch.as_tensor(np.stack(xs),dtype=torch.float32);y=torch.as_tensor(np.stack(ys),dtype=torch.float32)
        mask=torch.as_tensor(np.stack(masks),dtype=torch.float32)
        prediction,_=actor(x)
        loss=(((prediction-y)**2*torch.tensor([steer_weight,1.])).mean(-1)*mask).sum()/mask.sum().clamp_min(1)
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(actor.parameters(),1.)
        optimizer.step()
        if step%100==0:losses.append(dict(update=step,loss=float(loss.detach())))
    return dict(updates=updates,losses=losses,steerWeight=steer_weight,optimizer=optimizer.state_dict())


def fit_with_episode_context(actor,sequences,*,seed=1,updates=2000,batch=8,length=64,rate=.0003,steer_weight=25.,critical_sampling=False):
    """TBPTT with exact current-network hidden state from the episode prefix.

    The prefix is causal and detached; gradients cover the selected chunk.
    Normalizers stay frozen. Zeroing memory at an arbitrary three-second
    fragment is not equivalent to the uninterrupted actor used in racing.
    """
    if actor.architecture not in ('gru','set-gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep','gru-maneuver'):raise ValueError('GRU context refit only')
    torch.manual_seed(seed);rng=np.random.default_rng(seed)
    optimizer=torch.optim.Adam(actor.parameters(),lr=rate);losses=[]
    valid=[s for s in sequences if len(s['x'])>=2]
    clean=[s for s in valid if s.get('teacherClean')];corrections=[s for s in valid if not s.get('teacherClean')]
    critical={}
    if critical_sampling:
        for s in valid:
            n=len(s['x']);future=np.minimum(np.arange(n)+20,n-1)
            changes=np.abs(s['x'][future,9]-s['x'][:,9])>.12
            correction=np.abs(s['y'][:,0]-s.get('proposed',s.get('u',s['y']))[:,0])>.01
            critical[id(s)]=np.flatnonzero(changes|correction)
    for update in range(updates):
        selected=[];starts=[]
        for _ in range(batch):
            group=(clean if rng.random()<.5 else corrections) if critical_sampling and clean and corrections else valid
            s=group[int(rng.integers(len(group)))];selected.append(s)
            choices=critical.get(id(s),[])
            if len(choices) and rng.random()<.65:
                center=int(choices[int(rng.integers(len(choices)))]);start=max(0,min(len(s['x'])-length,center-length//2))
            else:start=int(rng.integers(max(1,len(s['x'])-length+1)))
            starts.append(start)
        prefix_length=max(starts);initial=torch.zeros((1,batch,actor.hidden))
        initial_intent=actor.initial_maneuver(torch.as_tensor(np.stack([s['x'][:1] for s in selected]))) if actor.architecture=='gru-maneuver' else None
        if prefix_length:
            prefix=np.zeros((batch,prefix_length,90),dtype=np.float32)
            for i,(s,n) in enumerate(zip(selected,starts)):
                if n:prefix[i,:n]=s['x'][:n]
            with torch.no_grad():
                if actor.architecture=='gru-maneuver':
                    encoded,_,_=actor.encode_maneuver(torch.as_tensor(prefix));predicted_intent=actor.last_maneuver_sequence
                else:
                    z=(torch.as_tensor(prefix)-actor.mean)/actor.scale
                    if actor.architecture=='set-gru':z=actor.encode_set(torch.as_tensor(prefix),z)
                    encoded,_=actor.core(z)
                for i,n in enumerate(starts):
                    if n:
                        initial[0,i]=encoded[i,n-1]
                        if actor.architecture=='gru-maneuver':initial_intent[0,i]=predicted_intent[i,n-1]
        xs=[];ys=[];masks=[]
        for s,start in zip(selected,starts):
            x=s['x'][start:start+length];y=s['y'][start:start+length];n=len(x)
            xs.append(np.pad(x,((0,length-n),(0,0)),mode='edge'))
            ys.append(np.pad(y,((0,length-n),(0,0)),mode='edge'));masks.append(np.arange(length)<n)
        x=torch.as_tensor(np.stack(xs));y=torch.as_tensor(np.stack(ys));mask=torch.as_tensor(np.stack(masks),dtype=torch.float32)
        prediction,_=actor(x,(initial,initial_intent) if actor.architecture=='gru-maneuver' else initial)
        loss=(((prediction-y)**2*torch.tensor([steer_weight,1.])).mean(-1)*mask).sum()/mask.sum().clamp_min(1)
        if actor.architecture in ('gru-intent','gru-intent-deep','gru-maneuver'):
            target=[]
            for s,start in zip(selected,starts):
                if s.get('intent') is None:raise ValueError('Intent sequence supervision missing')
                indices=np.minimum(np.arange(start,start+length),len(s['x'])-1);target.append(s['intent'][indices])
            target=torch.as_tensor(np.stack(target),dtype=torch.float32)
            loss+=1000.*(((actor.last_plan-target)**2)*mask[:,:,None]).sum()/mask.sum().clamp_min(1)
        elif actor.intent_supervision:
            target=[];available=[]
            for s,start in zip(selected,starts):
                indices=np.minimum(np.arange(start,start+length),len(s['x'])-1)
                target.append(s['intent'][indices] if s.get('intent') is not None else np.zeros((length,2),dtype=np.float32))
                available.append(float(s.get('intent') is not None))
            target=torch.as_tensor(np.stack(target),dtype=torch.float32)
            am=mask*torch.as_tensor(available)[:,None]
            lane=torch.tanh(actor.aux_head(actor.last_latent))
            logits=actor.aux_classifier(actor.last_latent)
            classes=(target[:,:,1,None]-torch.tensor([-.6166667,0.,.6166667])).abs().argmin(-1)
            ce=torch.nn.functional.cross_entropy(logits.flatten(0,1),classes.flatten(),reduction='none').reshape_as(am)
            loss+=2*((lane-target)**2*am[:,:,None]).sum()/am.sum().clamp_min(1)
            loss+=(ce*am).sum()/am.sum().clamp_min(1)
        elif actor.auxiliary:
            target=[];auxmask=[]
            for s,start in zip(selected,starts):
                future=np.minimum(np.arange(start,start+length)+20,len(s['x'])-1)
                target.append(s['x'][future,9]);auxmask.append(float(s.get('teacherClean',False)))
            target=torch.as_tensor(np.stack(target),dtype=torch.float32)
            am=mask*torch.as_tensor(auxmask)[:,None]
            auxiliary=torch.tanh(actor.aux_head(actor.last_latent)).squeeze(-1)
            loss+=.2*(((auxiliary-target)**2)*am).sum()/am.sum().clamp_min(1)
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(actor.parameters(),1.);optimizer.step()
        if update%100==0:
            losses.append(dict(update=update,loss=float(loss.detach())))
            print('context-refit',seed,update,losses[-1]['loss'],flush=True)
    return dict(updates=updates,losses=losses,steerWeight=steer_weight,batch=batch,length=length,
        stateInitialization='exact-detached-current-network-episode-prefix',normalizer='frozen',optimizer=optimizer.state_dict(),
        sampling='balanced-clean-and-dagger-with-critical-windows' if critical_sampling else 'uniform-episode-and-time',
        auxiliary='structured-neural-intent-training-supervision' if actor.architecture in ('gru-intent','gru-intent-deep','gru-maneuver') else 'teacher-lane-intent-training-only' if actor.intent_supervision else 'teacher-future-lateral-2s-training-only' if actor.auxiliary else None,
        rng=deepcopy_rng(rng))


def deepcopy_rng(rng):
    from copy import deepcopy
    return deepcopy(rng.bit_generator.state)
