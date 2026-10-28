"""Explicit migration of a recurrent V1 actor to measured road telemetry.

New rival channels initially have zero weights. The old duplicate speed
channels are folded into the retained speed input, preserving the policy on
the V1 unsaturated speed domain (0..30 m/s). No teacher is called here.
"""
from copy import deepcopy
import numpy as np
from game_direct import FEATURES,ROAD_FEATURES


def road_policy(policy):
    if policy['features']!=FEATURES or policy['architecture'] not in ('gru','gru-skip'):
        raise ValueError('Road sensor migration requires a V1 GRU')
    result=deepcopy(policy);w=result['weights'];norm=result['normalization']
    mean=np.asarray(norm['mean']);scale=np.asarray(norm['scale'])
    input_w=np.asarray(w['core.weight_ih_l0']);bias=np.asarray(w['core.bias_ih_l0'])
    skip=np.asarray(w.get('skip.weight',np.zeros((2,90))));head_bias=np.asarray(w['head.bias'])
    for j in (32,64,65,66,67,72):
        a=(scale[5]/2)/scale[j] if j in (32,72) else 0.
        b=((mean[5]/2 if j in (32,72) else 0.)-mean[j])/scale[j]
        input_w[:,5]+=input_w[:,j]*a;bias+=input_w[:,j]*b
        skip[:,5]+=skip[:,j]*a;head_bias+=skip[:,j]*b
        input_w[:,j]=0.;skip[:,j]=0.;mean[j]=0.;scale[j]=1.
    mean[5]/=2;scale[5]/=2
    for name,value in (('core.weight_ih_l0',input_w),('core.bias_ih_l0',bias),('head.bias',head_bias)):
        w[name]=value.tolist()
    if 'skip.weight' in w:w['skip.weight']=skip.tolist()
    norm.update(mean=mean.tolist(),scale=scale.tolist());result['features']=ROAD_FEATURES
    result['origin']={**(result.get('origin') or {}),'sensorMigration':'road-v2-exact-unsaturated-speed'}
    return result
