"""Portable NumPy inference for qualified laboratory temporal actor exports.

No Torch dependency, teacher, target speed or lane correction. Hidden state is
owned by each World/car and persisted with that physical episode.
"""
from copy import deepcopy
import numpy as np
from game_direct import ACTION,FEATURES,ROAD_FEATURES,features,controls
from game_residual import key,DECISION_STEPS


class TemporalPolicy:
    def __init__(self,data):
        if (data.get('schema')!=1 or data.get('kind')!='temporal-direct' or data.get('action')!=ACTION
            or data.get('features') not in (FEATURES,ROAD_FEATURES) or data.get('featureInputs')!=90 or data.get('inputs')!=68
            or data.get('observation')!='race-68-v3' or data.get('teacherAtInference') is not False
            or data.get('decisionHz')!=10 or data.get('physicsHz')!=60):raise ValueError('Temporal actor contract')
        self.data=deepcopy(data);self.key=key(data);self.arch=data['architecture'];self.hidden=data['hidden'];self.history=data['history']
        mode=data.get('readoutMode')
        if mode is not None and (mode!='plastic-actuators-1' or self.arch!='gru-maneuver'):raise ValueError('Temporal control training mode')
        immutable=('core.','ego.','rivals.','adapter.','intent.','intent_skip.','controller.','intent_features.','intent_core.','intent_projection.')
        if mode is None:immutable+=('steer_controller.','pedal_controller.')
        self.encoder_key=key({k:v for k,v in data.items() if k in ('architecture','hidden','history','normalization','features','observation','maneuverHidden','intentScale','readoutMode')}|{'weights':{k:v for k,v in data['weights'].items() if k.startswith(immutable)}})
        self.activation=data.get('outputActivation','tanh')
        self.maneuver_hidden=data.get('maneuverHidden',2);self.maneuver_scale=data.get('intentScale',1.)
        if type(self.maneuver_hidden) is not int or not 2<=self.maneuver_hidden<=128 or not .1<=self.maneuver_scale<=2.:raise ValueError('Neural maneuver descriptor')
        if self.activation not in ('tanh','clip'):raise ValueError('Temporal output activation')
        if self.arch not in ('dense','history','gru','set-gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep','gru-maneuver') or type(self.hidden) is not int or not 8<=self.hidden<=420:
            raise ValueError('Temporal actor architecture')
        if type(self.history) is not int or not 1<=self.history<=16 or self.arch!='history' and self.history!=1:
            raise ValueError('Temporal actor history')
        self.mean=np.asarray(data['normalization']['mean'],dtype=float)
        self.scale=np.asarray(data['normalization']['scale'],dtype=float)
        self.weights={k:np.asarray(v,dtype=float) for k,v in data['weights'].items()}
        shapes={'head.weight':(2,256 if self.arch in ('gru-intent-deep','gru-maneuver') else 128 if self.arch=='gru-intent' else self.hidden),'head.bias':(2,)}
        if self.arch in ('gru','set-gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep','gru-maneuver'):shapes.update({'core.weight_ih_l0':(3*self.hidden,128 if self.arch=='set-gru' else 90),'core.weight_hh_l0':(3*self.hidden,self.hidden),'core.bias_ih_l0':(3*self.hidden,),'core.bias_hh_l0':(3*self.hidden,)})
        else:shapes.update({'core.weight':(self.hidden,90*self.history),'core.bias':(self.hidden,)})
        if self.arch=='set-gru':shapes.update({'ego.weight':(64,60),'ego.bias':(64,),'rivals.weight':(32,10),'rivals.bias':(32,)})
        if self.arch in ('gru-skip','gru-adapter'):shapes['skip.weight']=(2,90)
        if self.arch=='gru-adapter':shapes.update({'adapter.weight':(128,self.hidden+90),'adapter.bias':(128,),'adapter_head.weight':(2,128)})
        if self.arch in ('gru-intent','gru-intent-deep'):shapes.update({'skip.weight':(2,92),'intent.0.weight':(128,self.hidden+90),'intent.0.bias':(128,),
            'intent.2.weight':(2,128),'intent.2.bias':(2,),'intent_skip.weight':(2,self.hidden+90),'intent_skip.bias':(2,),
            'controller.weight':(128,92),'controller.bias':(128,)})
        if self.arch=='gru-intent-deep':
            shapes.pop('controller.weight');shapes.pop('controller.bias')
            shapes.update({'controller.0.weight':(256,92),'controller.0.bias':(256,),'controller.2.weight':(256,256),'controller.2.bias':(256,)})
        if self.arch=='gru-maneuver':
            shapes.update({'skip.weight':(2,92),'intent_features.0.weight':(64,self.hidden+90),'intent_features.0.bias':(64,),
                'intent_core.weight_ih_l0':(3*self.maneuver_hidden,64),'intent_core.weight_hh_l0':(3*self.maneuver_hidden,self.maneuver_hidden),'intent_core.bias_ih_l0':(3*self.maneuver_hidden,),'intent_core.bias_hh_l0':(3*self.maneuver_hidden,)})
            if self.maneuver_hidden!=2:shapes.update({'intent_projection.weight':(2,self.maneuver_hidden),'intent_projection.bias':(2,)})
            for name in ('steer','pedal'):
                shapes.update({name+'_controller.0.weight':(128,92),name+'_controller.0.bias':(128,),
                    name+'_controller.2.weight':(128,128),name+'_controller.2.bias':(128,)})
        if self.mean.shape!=(90,) or self.scale.shape!=(90,) or not np.isfinite(self.mean).all() or not np.isfinite(self.scale).all() or (self.scale<=0).any():raise ValueError('Temporal normalization')
        if set(shapes)!=set(self.weights) or any(self.weights[k].shape!=s or not np.isfinite(self.weights[k]).all() for k,s in shapes.items()):
            raise ValueError('Temporal actor weights')

    def forward(self,observation,state=None,*,encode_only=False):
        z=(np.asarray(observation,dtype=float)-self.mean)/self.scale;w=self.weights
        if z.shape!=(90,) or not np.isfinite(z).all():raise ValueError('Temporal observation')
        if self.arch in ('gru','set-gru','gru-skip','gru-adapter','gru-intent','gru-intent-deep','gru-maneuver'):
            if self.arch=='set-gru':
                raw=np.asarray(observation,dtype=float)
                own=[*range(11),*range(32,55),*range(64,90)]
                rivals=np.stack([np.r_[z[11+7*k:18+7*k],z[55+3*k:58+3*k]] for k in range(3)])
                present=np.array([raw[17+7*k]>.5 for k in range(3)])
                encoded=np.tanh(rivals@w['rivals.weight'].T+w['rivals.bias'])
                maximum=encoded[present].max(0) if present.any() else np.zeros(32)
                z=np.r_[np.tanh(w['ego.weight']@z[own]+w['ego.bias']),(encoded*present[:,None]).sum(0)/3,maximum]
            saved=state['core'] if self.arch=='gru-maneuver' and state is not None else state
            h=np.zeros(self.hidden) if saved is None else np.asarray(saved,dtype=float)
            if h.shape!=(self.hidden,) or not np.isfinite(h).all():raise ValueError('Temporal hidden state')
            ir,iz,inn=np.split(w['core.weight_ih_l0']@z+w['core.bias_ih_l0'],3)
            hr,hz,hn=np.split(w['core.weight_hh_l0']@h+w['core.bias_hh_l0'],3)
            r=1/(1+np.exp(-np.clip(ir+hr,-60,60)));gate=1/(1+np.exp(-np.clip(iz+hz,-60,60)))
            n=np.tanh(inn+r*hn);h=(1-gate)*n+gate*h;next_state=h.tolist()
            if self.arch=='gru-maneuver':
                previous=(np.full(2,-float(observation[9])) if self.maneuver_hidden==2 else np.zeros(self.maneuver_hidden)) if state is None else np.asarray(state['intent'],dtype=float)
                if previous.shape!=(self.maneuver_hidden,) or not np.isfinite(previous).all():raise ValueError('Maneuver memory')
                z=(np.asarray(observation)-self.mean)/self.scale
                encoded=np.tanh(w['intent_features.0.weight']@np.r_[h,z]+w['intent_features.0.bias'])
                ir,iz,inn=np.split(w['intent_core.weight_ih_l0']@encoded+w['intent_core.bias_ih_l0'],3)
                hr,hz,hn=np.split(w['intent_core.weight_hh_l0']@previous+w['intent_core.bias_hh_l0'],3)
                reset=1/(1+np.exp(-np.clip(ir+hr,-60,60)));gate=1/(1+np.exp(-np.clip(iz+hz,-60,60)))
                plan=(1-gate)*np.tanh(inn+reset*hn)+gate*previous
                next_state=dict(core=h.tolist(),intent=plan.tolist())
                if encode_only:return None,next_state
                latent=self.readout_features(observation,next_state)
                return np.tanh(w['head.weight']@latent[:256]+w['skip.weight']@latent[256:]+w['head.bias']),next_state
        else:
            history=[z.tolist() for _ in range(self.history)] if state is None else state[1:]+[z.tolist()]
            array=np.asarray(history,dtype=float)
            if array.shape!=(self.history,90) or not np.isfinite(array).all():raise ValueError('Temporal history state')
            h=np.tanh(w['core.weight']@array.ravel()+w['core.bias']);next_state=history
        if encode_only:return None,next_state
        if self.arch in ('gru-intent','gru-intent-deep'):
            latent=self.readout_features(observation,h)
            n=256 if self.arch=='gru-intent-deep' else 128
            raw=w['head.weight']@latent[:n]+w['skip.weight']@latent[n:]+w['head.bias']
            return np.tanh(raw),next_state
        raw=w['head.weight']@h+w['head.bias']
        if self.arch in ('gru-skip','gru-adapter'):raw+=w['skip.weight']@((np.asarray(observation)-self.mean)/self.scale)
        if self.arch=='gru-adapter':
            latent=np.r_[h,(np.asarray(observation)-self.mean)/self.scale]
            raw+=w['adapter_head.weight']@np.tanh(w['adapter.weight']@latent+w['adapter.bias'])
        action=np.tanh(raw) if self.activation=='tanh' else np.clip(raw,-1,1)
        return action,next_state

    def readout_features(self,observation,state):
        w=self.weights
        if self.arch=='gru-maneuver':
            own=self.maneuver_inputs(observation,state);parts=[]
            for name in ('steer','pedal'):
                parts.append(np.tanh(w[name+'_controller.2.weight']@np.tanh(w[name+'_controller.0.weight']@own+w[name+'_controller.0.bias'])+w[name+'_controller.2.bias']))
            return np.r_[*parts,own]
        z=(np.asarray(observation)-self.mean)/self.scale
        latent=np.r_[state,z]
        if self.arch in ('gru-intent','gru-intent-deep'):
            plan=np.tanh(w['intent.2.weight']@np.tanh(w['intent.0.weight']@latent+w['intent.0.bias'])+w['intent.2.bias']+
                w['intent_skip.weight']@latent+w['intent_skip.bias'])
            own=np.r_[z,plan]
            if self.arch=='gru-intent-deep':return np.r_[np.tanh(w['controller.2.weight']@np.tanh(w['controller.0.weight']@own+w['controller.0.bias'])+w['controller.2.bias']),own]
            return np.r_[np.tanh(w['controller.weight']@own+w['controller.bias']),own]
        if self.arch=='gru-adapter':return np.r_[latent,np.tanh(w['adapter.weight']@latent+w['adapter.bias'])]
        return latent

    def maneuver_inputs(self,observation,state):
        """Frozen sensor/intent inputs without evaluating unused controls."""
        if self.arch!='gru-maneuver':raise ValueError('Maneuver features required')
        plan=np.asarray(state['intent']);w=self.weights
        if self.maneuver_hidden!=2:plan=self.maneuver_scale*np.tanh(w['intent_projection.weight']@plan+w['intent_projection.bias'])
        return np.r_[(np.asarray(observation)-self.mean)/self.scale,plan]

    def act(self,world,index=None):
        rows=np.arange(world.count) if index is None else np.atleast_1d(index)
        tick=int(round(world.time*60));cache=getattr(world,'temporal_cache',{});actions=[]
        for i in rows:
            old=cache.get(int(i))
            compatible=old is not None and (old.get('encoderKey')==self.encoder_key or old.get('key')==self.key)
            if not compatible or tick<old['tick']:
                old=None
            if old is None or tick-old['tick']>=DECISION_STEPS:
                action,state=self.forward(features(world,i,version=self.data['features']),None if old is None else old['state'])
                old=dict(key=self.key,encoderKey=self.encoder_key,tick=tick,action=action.tolist(),state=state)
                cache[int(i)]=old
            actions.append(old['action'])
        world.temporal_cache=cache
        result=controls(world,actions,rows)
        return result[0] if index is not None else result
