"""Neural maneuver representation followed by a learned direct controller.

Teacher intent is a supervision label. The optional control-only supervised
stage uses that label; deployed inference always predicts its own intent.
The frozen recurrent encoder makes cached causal features exact.
"""
from pathlib import Path
import argparse,hashlib,time
import numpy as np
import torch
from game_lab.models import Actor
from game_lab.dataset import load_sequences
from game_lab.artifacts import freeze_dataset,atomic_report

def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--updates',type=int,default=6000)
    p.add_argument('--deep-control',action='store_true');p.add_argument('--teacher-control',action='store_true')
    a=p.parse_args();torch.set_num_threads(1);torch.manual_seed(a.seed);started=time.monotonic()
    c=torch.load(a.checkpoint,map_location='cpu',weights_only=True);actor=Actor('gru-intent-deep' if a.deep_control else 'gru-intent',c['hidden'])
    if c['hidden']!=128 or 'aux_head.weight' not in c['state']:raise ValueError('Prepared recurrent intent supervision required')
    actor.feature_version=c['featureVersion']
    actor.load_state_dict({k:v for k,v in c['state'].items() if k.startswith('core.') or k in ('mean','scale')},strict=False)
    with torch.no_grad():
        actor.intent[2].weight.zero_();actor.intent[2].bias.zero_();actor.intent_skip.weight.zero_()
        actor.intent_skip.weight[:,:actor.hidden].copy_(c['state']['aux_head.weight']);actor.intent_skip.bias.copy_(c['state']['aux_head.bias'])
    for parameter in actor.core.parameters():parameter.requires_grad_(False)
    a.output.mkdir(parents=True,exist_ok=True);manifest=freeze_dataset(a.dataset,a.output/'dataset');seqs=load_sequences(a.output/'dataset')
    xs=[];ys=[];plans=[];critical=[]
    with torch.no_grad():
        for s in seqs:
            if not len(s['x']):continue
            if s['featureVersion']!=actor.feature_version or s['intent'] is None:raise ValueError('Intent dataset contract')
            x=torch.as_tensor(s['x'][None]);z=(x-actor.mean)/actor.scale;h,_=actor.core(z)
            xs.append(torch.cat((h,z),-1)[0]);ys.append(torch.as_tensor(s['y']));plans.append(torch.as_tensor(s['intent']))
            changes=np.r_[False,np.abs(np.diff(s['intent'][:,1]))>.1]
            critical.append(torch.as_tensor(changes|(np.abs(s['y'][:,0]-s.get('proposed',s['u'])[:,0])>.01)))
    x=torch.cat(xs);y=torch.cat(ys);target_plan=torch.cat(plans);critical=torch.nonzero(torch.cat(critical),as_tuple=False).flatten()
    def sample():
        indices=torch.randint(len(x),(512,))
        if len(critical):indices[:128]=critical[torch.randint(len(critical),(128,))]
        return indices
    parameters=list(actor.intent.parameters())+list(actor.intent_skip.parameters());optimizer=torch.optim.Adam(parameters,lr=.0003);losses=[]
    for step in range(a.updates):
        indices=sample();v=x[indices];prediction=torch.tanh(actor.intent(v)+actor.intent_skip(v))
        loss=1000*((prediction-target_plan[indices])**2).mean()
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(parameters,10.);optimizer.step()
        if step%500==0:print('intent',a.seed,step,float(loss.detach()),flush=True);losses.append(dict(stage='intent',update=step,loss=float(loss.detach())))
    with torch.no_grad():
        predicted=torch.cat([torch.tanh(actor.intent(chunk)+actor.intent_skip(chunk)) for chunk in x.split(2048)])
        own=torch.cat((x[:,actor.hidden:],target_plan if a.teacher_control else predicted),-1)
    parameters=list(actor.controller.parameters())+list(actor.head.parameters())+list(actor.skip.parameters())
    optimizer=torch.optim.Adam(parameters,lr=.0003)
    for step in range(a.updates*2):
        indices=sample();v=own[indices]
        encoded=actor.controller(v) if a.deep_control else torch.tanh(actor.controller(v))
        prediction=torch.tanh(actor.head(encoded)+actor.skip(v))
        loss=((prediction-y[indices])**2*torch.tensor([1000.,1.])).mean()
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(parameters,10.);optimizer.step()
        if step%500==0:print('control',a.seed,step,float(loss.detach()),flush=True);losses.append(dict(stage='control',update=step,loss=float(loss.detach())))
    origin={**c['origin'],'stage':'neural-intent-and-direct-control','intentSeed':a.seed,'additionalUpdates':a.updates*3,
        'sourceModelHash':hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),'datasetHash':manifest['hash'],
        'encoderTrainable':False,'teacherIntentAtInference':False,'controllerPreparationInput':'supervised-intent' if a.teacher_control else 'neural-intent'}
    atomic_report(a.output/'policy.json',actor.export(origin=origin))
    torch.save(dict(architecture=actor.architecture,hidden=actor.hidden,history=1,state=actor.state_dict(),featureVersion=actor.feature_version,origin=origin),a.output/'model.pt')
    atomic_report(a.output/'training.json',dict(seed=a.seed,updates=a.updates*3,examples=len(x),losses=losses,
        intentErrorMetres=np.percentile(abs(predicted.numpy()-target_plan.numpy())*6,[50,95,99,100],axis=0).tolist(),
        wallSeconds=time.monotonic()-started,qualified=False))

if __name__=='__main__':main()
