"""Trainable neural controls over stable causal sensor/maneuver features.

Only the feedforward controls are plastic. Recurrent perception and maneuver
memory remain outside SB3 replay, with the same semantics at collection and
update time. These policies are laboratory options, not a qualified default.
"""
from copy import deepcopy
import torch
import numpy as np
from torch import nn
from stable_baselines3.sac.policies import SACPolicy
from stable_baselines3.td3.policies import TD3Policy

MODE='plastic-actuators-1'
CRITIC_CONTEXT='frozen-base-actuators-1'


def configure(base,mode=None):
    mode=mode or ('plastic-context' if base.get('criticFeatureContext')==CRITIC_CONTEXT else 'plastic' if base.get('readoutMode')==MODE else 'readout')
    if mode not in ('readout','plastic','plastic-context'):raise ValueError('Actuator training mode')
    data=deepcopy(base)
    if mode in ('plastic','plastic-context'):
        if base['architecture']!='gru-maneuver':raise ValueError('Plastic controls require maneuver architecture')
        data['readoutMode']=MODE
        if mode=='plastic-context':data['criticFeatureContext']=CRITIC_CONTEXT
    elif data.get('readoutMode')==MODE:
        # Changing feature/optimizer contracts must be an explicit new
        # preparation, never a silent downgrade on resume/new objectives.
        raise ValueError('Cannot silently freeze plastic controls')
    return data


def specification(base):
    # SB3 stores constructor arguments too. Compact numeric arrays avoid a
    # second, multi-megabyte textual rendering of every control coefficient.
    return {k:np.asarray(v,dtype=np.float32).copy() for k,v in base['weights'].items()
        if k.startswith(('steer_controller.','pedal_controller.')) or k in ('head.weight','head.bias','skip.weight')}


class NeuralActuators(nn.Module):
    def __init__(self,weights):
        super().__init__()
        for name in ('steer_controller','pedal_controller'):
            setattr(self,name,nn.Sequential(nn.Linear(92,128),nn.Tanh(),nn.Linear(128,128),nn.Tanh()))
        self.head=nn.Linear(256,2);self.skip=nn.Linear(92,2,bias=False)
        self.load_state_dict({k:torch.as_tensor(v,dtype=torch.float32) for k,v in weights.items()},strict=True)

    def forward(self,x):
        # The optional critic context contains the original frozen actuator
        # embeddings followed by these same 92 causal sensor/intent values.
        # Trainable controls consume only the latter; their command is exact.
        x=x[...,-92:]
        return self.head(torch.cat((self.steer_controller(x),self.pedal_controller(x)),dim=-1))+self.skip(x)


class NeuralSACPolicy(SACPolicy):
    def __init__(self,*args,neural_base,**kwargs):
        self.neural_base=neural_base
        super().__init__(*args,**kwargs)

    def _build(self,lr_schedule):
        super()._build(lr_schedule)
        self.actor.mu=NeuralActuators(self.neural_base).to(self.device)
        self.actor.optimizer=self.optimizer_class(self.actor.parameters(),lr=lr_schedule(1),**self.optimizer_kwargs)


class NeuralTD3Policy(TD3Policy):
    def __init__(self,*args,neural_base,**kwargs):
        self.neural_base=neural_base
        super().__init__(*args,**kwargs)

    def _build(self,lr_schedule):
        super()._build(lr_schedule)
        self.actor.mu=nn.Sequential(NeuralActuators(self.neural_base),nn.Tanh()).to(self.device)
        self.actor_target.mu=nn.Sequential(NeuralActuators(self.neural_base),nn.Tanh()).to(self.device)
        self.actor_target.load_state_dict(self.actor.state_dict());self.actor_target.set_training_mode(False)
        self.actor.optimizer=self.optimizer_class(self.actor.parameters(),lr=lr_schedule(1),**self.optimizer_kwargs)
