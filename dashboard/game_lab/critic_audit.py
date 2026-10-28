"""Paired action probes of a frozen critic, never a qualification result.

Every counterfactual starts from the exact same physical/memory/RNG snapshot.
Finite-horizon deterministic returns are diagnostics, not the true infinite-
horizon stochastic SAC value. No teacher is called during the probes.
"""
from pathlib import Path
import json
import numpy as np
import torch
from game_lab.skills import SkillEnv,readout_weights
from game_lab.actuators import MODE,NeuralActuators,specification
from game_lab.checkpoint import load
from game_lab.artifacts import atomic_report,digest
from game_residual import key


def audit(checkpoint,base,*,output,seed=13004105,horizon=40):
    if 980000<=seed<=990000 or 1980000<=seed<=1990000:raise ValueError('Training diagnostic seed required')
    if not 1<=horizon<=100:raise ValueError('Finite diagnostic horizon')
    path=Path(checkpoint);manifest=json.loads((path/'manifest.json').read_text());contract=manifest['contract']
    if manifest['method'] not in ('sac','td3'):raise ValueError('Off-policy critic required')
    opts=dict(family=contract['family'],bots=contract['bots'],duration=contract['duration'],single_lap=contract.get('singleLap',False))
    model,_=load(path,SkillEnv(base,**opts),contract=contract)
    if base.get('readoutMode')==MODE:fixed=NeuralActuators(specification(base)).eval()
    else:
        w=torch.as_tensor(readout_weights(base),dtype=torch.float32);b=torch.as_tensor(base['weights']['head.bias'],dtype=torch.float32)
        fixed=lambda x:torch.nn.functional.linear(x,w,b)
    def base_action(observation):
        with torch.no_grad():return torch.tanh(fixed(torch.as_tensor(observation[None],dtype=torch.float32)))[0].numpy()
    def value(observation,action):
        with torch.no_grad():
            values=model.critic(torch.as_tensor(observation[None],dtype=torch.float32),torch.as_tensor(action[None],dtype=torch.float32))
            return min(float(v.item()) for v in values)
    rows=[]
    for family in ('solo','traffic'):
        env=SkillEnv(base,family=family,bots=3,duration=120.)
        observation,_=env.reset(seed=seed+(family=='traffic'))
        for decision in range(281):
            command=base_action(observation)
            if decision in (40,80,120,160,200,240,280):
                state=env.snapshot();start_observation=observation.copy();probes=[]
                speed=float(env.episode.world.state[0,3])
                for pedal in (-1.,-.5,0.,.5,1.):
                    env.restore(state);obs=start_observation.copy();action=np.array([command[0],pedal],dtype=np.float32)
                    predicted=value(obs,action);total=0.;discount=1.;terminal=truncated=False;count=0
                    for step in range(horizon):
                        applied=action if step==0 else model.predict(obs,deterministic=True)[0]
                        obs,reward,terminal,truncated,_=env.step(applied);total+=discount*reward;discount*=model.gamma;count+=1
                        if terminal or truncated:break
                    tail=0. if terminal else value(obs,model.predict(obs,deterministic=True)[0])
                    probes.append(dict(pedal=pedal,predictedQ=predicted,finiteReturn=total,bootstrappedReturn=total+discount*tail,
                        decisions=count,terminated=terminal,truncated=truncated,contacts=env.episode.contact_count,limits=int(env.episode.world.track_limits[0])))
                env.restore(state);observation=start_observation
                rows.append(dict(family=family,decision=decision,speed=speed,baseAction=command.tolist(),probes=probes))
            if decision<280:
                observation,_,terminated,truncated,_=env.step(command)
                if terminated or truncated:break
        env.close()
    comparisons=[]
    for row in rows:
        for i,a in enumerate(row['probes']):
            for b in row['probes'][i+1:]:
                difference=a['finiteReturn']-b['finiteReturn'];q=a['predictedQ']-b['predictedQ']
                if abs(difference)>1e-5 and abs(q)>1e-7:comparisons.append(difference*q>0)
    report=dict(version='paired-finite-critic-probe-1',checkpointHash=digest(path/'manifest.json'),baseHash=key(base),
        method=manifest['method'],seed=seed,horizonDecisions=horizon,rows=rows,
        finiteReturnRankAgreement=sum(comparisons)/len(comparisons) if comparisons else None,rankPairs=len(comparisons),
        caveat='Finite deterministic continuation is not ground truth for the full stochastic critic objective',
        qualified=False,finalBankUsed=False,teacherCallsDuringProbes=0)
    atomic_report(output,report);return report
