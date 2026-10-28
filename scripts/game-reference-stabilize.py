"""Fit a learned instantaneous steering path alongside recurrent decisions.

All coefficients are fitted from demonstrations. Inference remains a neural
actor with direct steering/pedal outputs; no teacher or tracking controller.
"""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
import torch
from game_lab.models import Actor
from game_lab.dataset import load_sequences
from game_lab.artifacts import atomic_report


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--dataset',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ridge',type=float,default=.01);a=p.parse_args()
    torch.set_num_threads(1);started=time.monotonic()
    c=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
    if c['architecture'] not in ('gru','gru-skip'):raise ValueError('Compatible recurrent base required')
    actor=Actor('gru-skip',c['hidden']);loaded=actor.load_state_dict(c['state'],strict=False)
    if loaded.unexpected_keys or set(loaded.missing_keys)-{'skip.weight'}:raise ValueError('Recurrent source mismatch')
    sequences=[s for s in load_sequences(a.dataset) if s['rolloutClean']]
    inputs=[];targets=[];old=[]
    with torch.no_grad():
        for s in sequences:
            x=torch.as_tensor(s['x'][None,:,:],dtype=torch.float32)
            value,_=actor(x)
            z=((x-actor.mean)/actor.scale)[0].numpy()
            inputs.append(np.c_[actor.last_latent[0].numpy(),z,np.ones(len(z))])
            targets.append(s['y'][:,0]);old.append(value[0,:,0].numpy())
    x=np.concatenate(inputs);y=np.concatenate(targets);old=np.concatenate(old)
    target=np.arctanh(np.clip(y,-.9999,.9999))
    gram=x.T@x;ridge=np.eye(gram.shape[0])*a.ridge;ridge[-1,-1]=0.
    solution=np.linalg.solve(gram+ridge,x.T@target)
    with torch.no_grad():
        actor.head.weight[0].copy_(torch.as_tensor(solution[:actor.hidden],dtype=torch.float32))
        actor.skip.weight[0].copy_(torch.as_tensor(solution[actor.hidden:-1],dtype=torch.float32))
        actor.head.bias[0].copy_(torch.tensor(solution[-1],dtype=torch.float32))
    new=np.tanh(x@solution)
    a.output.mkdir(parents=True,exist_ok=True)
    origin={**c['origin'],'stage':'learned-steering-skip-regression','parentHash':hashlib.sha256(a.checkpoint.read_bytes()).hexdigest()}
    policy=actor.export(origin=origin);atomic_report(a.output/'policy.json',policy)
    torch.save(dict(architecture=actor.architecture,hidden=actor.hidden,history=1,state=actor.state_dict(),origin=origin),a.output/'model.pt')
    report=dict(examples=len(y),sequences=len(sequences),ridge=a.ridge,steeringErrorPercentiles=[50,95,99,100],
        before=np.percentile(np.abs(y-old),[50,95,99,100]).tolist(),after=np.percentile(np.abs(y-new),[50,95,99,100]).tolist(),
        wallSeconds=time.monotonic()-started,teacherAtInference=False,qualified=False)
    atomic_report(a.output/'stabilization.json',report);print(json.dumps(report))


if __name__=='__main__':main()
