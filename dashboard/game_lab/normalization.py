"""Frozen causal telemetry normalization shared by actor and reference critic."""
import numpy as np
import torch
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor


class PhysicalFeatures(BaseFeaturesExtractor):
    def __init__(self,observation_space,mean,scale):
        super().__init__(observation_space,features_dim=int(np.prod(observation_space.shape)))
        history=self.features_dim//90
        self.register_buffer('mean',torch.tensor(list(mean)*history,dtype=torch.float32))
        self.register_buffer('scale',torch.tensor(list(scale)*history,dtype=torch.float32))

    def forward(self,observations):return (observations-self.mean)/self.scale
