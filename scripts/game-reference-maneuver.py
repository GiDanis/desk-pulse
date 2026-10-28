"""Prepare explicit neural maneuver memory and independent actuator heads.

The offline controller labels condition on the expert's current path intent.
The exported actor always predicts intent with its own two-unit GRU memory.
Startup, braking and coasting receive explicit sampling coverage; steering
precision cannot starve the pedal head's gradients.
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
    p.add_argument('--coverage',type=Path);p.add_argument('--resume',action='store_true')
    p.add_argument('--memory-updates',type=int);p.add_argument('--control-updates',type=int);p.add_argument('--intent-noise',type=float,default=0.)
    p.add_argument('--priority-seed',type=int)
    p.add_argument('--conditioning',choices=('teacher','predicted'),default='teacher')
    p.add_argument('--control-rate',type=float,default=.0003)
    a=p.parse_args();torch.set_num_threads(1);torch.manual_seed(a.seed);rng=np.random.default_rng(a.seed);started=time.monotonic()
    memory_updates=a.updates if a.memory_updates is None else a.memory_updates
    control_updates=a.updates*2 if a.control_updates is None else a.control_updates
    if min(memory_updates,control_updates)<0 or not 0<=a.intent_noise<=.1:p.error('Preparation budget/augmentation')
    if not 0<a.control_rate<=.001:p.error('Actuator learning rate')
    if a.conditioning=='predicted' and (not a.resume or memory_updates):p.error('Predicted conditioning requires a frozen prepared memory')
    c=torch.load(a.checkpoint,map_location='cpu',weights_only=True);actor=Actor('gru-maneuver',c['hidden'],maneuver_hidden=c.get('maneuverHidden',2),maneuver_scale=c.get('intentScale',1.));actor.feature_version=c['featureVersion']
    actor.load_state_dict({k:v for k,v in c['state'].items() if k.startswith('core.') or k in ('mean','scale')},strict=False)
    if a.resume:
        if c['architecture']!=actor.architecture:raise ValueError('Resume architecture mismatch')
        actor.load_state_dict(c['state'])
    for parameter in actor.core.parameters():parameter.requires_grad_(False)
    a.output.mkdir(parents=True,exist_ok=True);manifest=freeze_dataset(a.dataset,a.output/'dataset');seqs=load_sequences(a.output/'dataset')
    from game_geometry import get_track
    from game_catalog import RACE_VEHICLE
    lane_limit=(get_track('oval-1').width/2-RACE_VEHICLE.width/2-1.)/(get_track('oval-1').width/2)
    sequences=[]
    with torch.no_grad():
        for s in seqs:
            if not len(s['x']):continue
            if s['featureVersion']!=actor.feature_version or s.get('intent') is None:raise ValueError('Maneuver sequence contract')
            raw=torch.as_tensor(s['x']);z=(raw-actor.mean)/actor.scale;target=torch.as_tensor(s['intent']).clone()
            # The expert clips its physical path at this same boundary. Its
            # internal recovery accumulator can temporarily lie outside it.
            target[:,0].clamp_(-lane_limit,lane_limit)
            if memory_updates:
                h,_=actor.core(z[None]);_,current_plan,_=actor.encode_maneuver(raw[None])
                hard_plan=torch.nonzero(abs(current_plan[0]-target).amax(-1)>.1,as_tuple=False).flatten().numpy();latent=torch.cat((h[0],z),-1)
            else:hard_plan=np.empty(0,dtype=int);latent=None
            condition=actor.encode_maneuver(raw[None])[1][0].clone() if a.conditioning=='predicted' else target
            sequences.append(dict(x=latent,own=z,y=torch.as_tensor(s['y']),plan=target,initial=-float(raw[0,9]),
                condition=condition,proposed=torch.as_tensor(s['proposed']),hardPlan=hard_plan,priority=s['source'].startswith('train-'+str(a.priority_seed)+'-') if a.priority_seed is not None else False))
    parameters=list(actor.intent_features.parameters())+list(actor.intent_core.parameters())
    if actor.maneuver_hidden!=2:parameters+=list(actor.intent_projection.parameters())
    optimizer=torch.optim.Adam(parameters,lr=.0003);losses=[]
    batch=8;length=64
    for step in range(memory_updates):
        selected=[sequences[int(rng.integers(len(sequences)))] for _ in range(batch)]
        starts=[]
        for s in selected:
            if len(s['hardPlan']) and rng.random()<.5:
                starts.append(max(0,min(len(s['x'])-length,int(rng.choice(s['hardPlan']))-int(rng.integers(length)))))
            else:starts.append(0 if rng.random()<.2 else int(rng.integers(max(1,len(s['x'])-length+1))))
        prefix_length=max(starts);memory=torch.tensor([s['initial'] for s in selected]).reshape(1,batch,1).expand(-1,-1,2).contiguous() if actor.maneuver_hidden==2 else torch.zeros((1,batch,actor.maneuver_hidden))
        if prefix_length:
            prefix=torch.zeros((batch,prefix_length,actor.hidden+90))
            for i,(s,n) in enumerate(zip(selected,starts)):
                if n:prefix[i,:n]=s['x'][:n]
            with torch.no_grad():
                encoded,_=actor.intent_core(actor.intent_features(prefix),memory)
                for i,n in enumerate(starts):
                    if n:memory[0,i]=encoded[i,n-1]
        xs=[];targets=[];masks=[]
        for s,start in zip(selected,starts):
            n=min(length,len(s['x'])-start);pad=length-n
            xs.append(torch.cat((s['x'][start:start+n],s['x'][start+n-1:start+n].expand(pad,-1))))
            targets.append(torch.cat((s['plan'][start:start+n],s['plan'][start+n-1:start+n].expand(pad,-1))))
            masks.append(torch.arange(length)<n)
        latent,_=actor.intent_core(actor.intent_features(torch.stack(xs)),memory);prediction=actor.project_maneuver(latent);target=torch.stack(targets);mask=torch.stack(masks).float()
        loss=1000.*(((prediction-target)**2)*mask[:,:,None]).sum()/mask.sum().clamp_min(1)
        loss+=100.*(((torch.diff(prediction,dim=1)-torch.diff(target,dim=1))**2)*mask[:,1:,None]).sum()/mask[:,1:].sum().clamp_min(1)
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(parameters,10.);optimizer.step()
        if step%500==0:print('maneuver',a.seed,step,float(loss.detach()),flush=True);losses.append(dict(stage='memory',update=step,loss=float(loss.detach())))
    own=torch.cat([torch.cat((s['own'],s['condition']),-1) for s in sequences]);y=torch.cat([s['y'] for s in sequences])
    proposed=torch.cat([s['proposed'] for s in sequences])
    hard=[torch.nonzero(abs(proposed[:,k]-y[:,k])>(.005 if k==0 else .2),as_tuple=False).flatten() for k in (0,1)]
    priority=torch.cat([torch.full((len(s['y']),),s['priority'],dtype=torch.bool) for s in sequences])
    priority_hard=[torch.nonzero(priority&(abs(proposed[:,k]-y[:,k])>(.005 if k==0 else .2)),as_tuple=False).flatten() for k in (0,1)]
    coverage_hash=None;coverage_start=len(own)
    if a.coverage:
        import shutil
        from game_lab.artifacts import digest
        target=a.output/'coverage.npz';shutil.copy2(a.coverage,target);coverage_hash=digest(target)
        with np.load(target,allow_pickle=False) as f:
            if str(f['featureVersion'])!=actor.feature_version:raise ValueError('Coverage sensor mismatch')
            own=torch.cat((own,torch.cat(((torch.as_tensor(f['x'])-actor.mean)/actor.scale,torch.as_tensor(f['intent'])),-1)))
            y=torch.cat((y,torch.as_tensor(f['y'])))
    speed=own[:,5]*actor.scale[5]+actor.mean[5]
    groups=[torch.nonzero(condition,as_tuple=False).flatten() for condition in
        (speed<.05,y[:,1]>.5,y[:,1]<-.2,abs(y[:,1])<.2,abs(y[:,0])>.08)]
    for channel,name in enumerate(('steer','pedal')):
        controller=getattr(actor,name+'_controller');head=getattr(actor,name+'_head');skip=getattr(actor,name+'_skip')
        parameters=[*controller.parameters(),*head.parameters(),*skip.parameters()];optimizer=torch.optim.Adam(parameters,lr=a.control_rate)
        for step in range(control_updates):
            indices=torch.randint(len(own),(512,))
            if coverage_hash:indices[384:]=torch.randint(coverage_start,len(own),(128,))
            selected_groups=(groups[0],groups[4]) if channel==0 else groups[:4]
            portion=80 if channel==1 else 128
            for k,g in enumerate(selected_groups):
                if len(g):indices[k*portion:(k+1)*portion]=g[torch.randint(len(g),(portion,))]
            if len(hard[channel]):indices[256:384]=hard[channel][torch.randint(len(hard[channel]),(128,))]
            if len(priority_hard[channel]):indices[128:256]=priority_hard[channel][torch.randint(len(priority_hard[channel]),(128,))]
            v=own[indices].clone()
            if a.intent_noise:v[:,-2:]+=torch.randn_like(v[:,-2:])*a.intent_noise
            prediction=torch.tanh(head(controller(v))+skip(v)).flatten()
            loss=((prediction-y[indices,channel])**2).mean()*(1000. if channel==0 else 1.)
            if a.memory_updates is not None or a.control_updates is not None:
                for group in optimizer.param_groups:group['lr']=a.control_rate if step<control_updates*3//4 else a.control_rate/3
            optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(parameters,10.);optimizer.step()
            if step%1000==0:print(name,a.seed,step,float(loss.detach()),flush=True);losses.append(dict(stage=name,update=step,loss=float(loss.detach())))
    origin={**c['origin'],'stage':'neural-maneuver-memory-dual-control','preparationSeed':a.seed,'datasetHash':manifest['hash'],
        'sourceModelHash':hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),'teacherIntentAtInference':False,
        'controllerPreparationInput':'supervised-current-intent','balancedActuatorRegimes':True}
    origin.update(coverageHash=coverage_hash,resumedFromPreparation=a.resume,intentNoise=a.intent_noise,prioritySeed=a.priority_seed,
        controllerConditioning=a.conditioning,controllerLearningRate=a.control_rate)
    atomic_report(a.output/'policy.json',actor.export(origin=origin))
    torch.save(dict(architecture=actor.architecture,hidden=actor.hidden,history=1,state=actor.state_dict(),featureVersion=actor.feature_version,maneuverHidden=actor.maneuver_hidden,intentScale=actor.maneuver_scale,origin=origin),a.output/'model.pt')
    atomic_report(a.output/'training.json',dict(seed=a.seed,updates=dict(memory=memory_updates,steer=control_updates,pedal=control_updates),examples=len(own),
        losses=losses,wallSeconds=time.monotonic()-started,qualified=False))

if __name__=='__main__':main()
