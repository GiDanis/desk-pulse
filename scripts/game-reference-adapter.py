"""Controlled nonlinear-readout ablation over a frozen causal GRU encoder.

Exact episode features are precomputed once because the encoder never changes.
The adapter is neural; no desired path or teacher action is an inference input.
"""
from pathlib import Path
import argparse,json,time,hashlib
import numpy as np
import torch
from game_lab.models import Actor
from game_lab.dataset import load_sequences
from game_lab.artifacts import freeze_dataset,atomic_report

def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--updates',type=int,default=6000)
    a=p.parse_args();torch.set_num_threads(1);torch.manual_seed(a.seed);started=time.monotonic()
    c=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
    if c['architecture'] not in ('gru','gru-skip','gru-adapter'):raise ValueError('Recurrent base required')
    actor=Actor('gru-adapter',c['hidden']);actor.feature_version=c.get('featureVersion','direct-physical-90-v1')
    loaded=actor.load_state_dict({k:v for k,v in c['state'].items() if not k.startswith('aux_')},strict=False)
    if loaded.unexpected_keys or set(loaded.missing_keys)-{'skip.weight','adapter.weight','adapter.bias','adapter_head.weight'}:raise ValueError('Adapter source mismatch')
    a.output.mkdir(parents=True,exist_ok=True);manifest=freeze_dataset(a.dataset,a.output/'dataset');sequences=load_sequences(a.output/'dataset')
    if any(s['featureVersion']!=actor.feature_version for s in sequences):raise ValueError('Readout sensors mismatch')
    latent=[];targets=[];critical=[]
    for parameter in actor.core.parameters():parameter.requires_grad_(False)
    with torch.no_grad():
        for s in sequences:
            if not len(s['x']):continue
            x=torch.as_tensor(s['x'][None]);z=(x-actor.mean)/actor.scale;h,_=actor.core(z)
            latent.append(torch.cat((h,z),-1)[0]);targets.append(torch.as_tensor(s['y']))
            critical.append(torch.as_tensor(np.abs(s['y'][:,0]-s['u'][:,0])>.01))
    x=torch.cat(latent);y=torch.cat(targets);critical=torch.nonzero(torch.cat(critical),as_tuple=False).flatten()
    optimizer=torch.optim.Adam([p for p in actor.parameters() if p.requires_grad],lr=.0003);losses=[]
    for step in range(a.updates):
        indices=torch.randint(len(x),(512,))
        if len(critical):indices[:128]=critical[torch.randint(len(critical),(128,))]
        z=x[indices];target=y[indices]
        raw=actor.head(z[:,:actor.hidden])+actor.skip(z[:,actor.hidden:])+actor.adapter_head(torch.tanh(actor.adapter(z)))
        prediction=torch.tanh(raw);loss=((prediction-target)**2*torch.tensor([1000.,1.])).mean()
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_([p for p in actor.parameters() if p.requires_grad],1.);optimizer.step()
        if step%100==0:
            losses.append(dict(update=step,loss=float(loss.detach())));print('adapter',a.seed,step,losses[-1]['loss'],flush=True)
    origin={**c['origin'],'stage':'frozen-recurrent-nonlinear-readout','adapterSeed':a.seed,'additionalUpdates':a.updates,
        'sourceModelHash':hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),'datasetHash':manifest['hash'],'encoderTrainable':False}
    atomic_report(a.output/'policy.json',actor.export(origin=origin))
    torch.save(dict(architecture=actor.architecture,hidden=actor.hidden,history=1,state=actor.state_dict(),featureVersion=actor.feature_version,origin=origin),a.output/'model.pt')
    atomic_report(a.output/'training.json',dict(seed=a.seed,updates=a.updates,examples=len(x),losses=losses,wallSeconds=time.monotonic()-started,qualified=False))

if __name__=='__main__':main()
