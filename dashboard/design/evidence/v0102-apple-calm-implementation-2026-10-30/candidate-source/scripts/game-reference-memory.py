"""Maneuver-memory ablation with fixed, already prepared actuator networks.

Private recurrent state is distinct from its two-dimensional learned intent.
Its bounded neural projection is a latent representation; direct actuator
outputs remain unconstrained beyond the physical steering/pedal contract.
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
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--updates',type=int,default=8000);p.add_argument('--units',type=int,default=32);p.add_argument('--scale',type=float,default=.7)
    p.add_argument('--priority-seed',type=int);a=p.parse_args()
    if not 4<=a.units<=128 or not .5<=a.scale<=1.:p.error('Memory descriptor')
    torch.set_num_threads(1);torch.manual_seed(a.seed);rng=np.random.default_rng(a.seed);started=time.monotonic()
    c=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
    if c['architecture']!='gru-maneuver':raise ValueError('Prepared dual actuator controller required')
    actor=Actor('gru-maneuver',c['hidden'],maneuver_hidden=a.units,maneuver_scale=a.scale);actor.feature_version=c['featureVersion']
    weights=actor.state_dict();actor.load_state_dict({k:v for k,v in c['state'].items() if k in weights and v.shape==weights[k].shape},strict=False)
    for name,value in actor.named_parameters():value.requires_grad_(name.startswith(('intent_features.','intent_core.','intent_projection.')))
    a.output.mkdir(parents=True,exist_ok=False);manifest=freeze_dataset(a.dataset,a.output/'dataset');families={}
    from game_geometry import get_track
    from game_catalog import RACE_VEHICLE
    half_width=get_track('oval-1').width/2;lane_limit=(half_width-RACE_VEHICLE.width/2-1.)/half_width
    with torch.no_grad():
        for s in load_sequences(a.output/'dataset'):
            if not len(s['x']):continue
            if s['featureVersion']!=actor.feature_version or s.get('intent') is None:raise ValueError('Memory supervision contract')
            raw=torch.as_tensor(s['x']);z=(raw-actor.mean)/actor.scale;h,_=actor.core(z[None]);target=torch.as_tensor(s['intent']).clone()
            target[:,0].clamp_(-lane_limit,lane_limit)
            families.setdefault(s['family'],[]).append(dict(x=torch.cat((h[0],z),-1),target=target,
                priority=s['source'].startswith('train-'+str(a.priority_seed)+'-') if a.priority_seed is not None else False))
    names=sorted(families);parameters=[v for v in actor.parameters() if v.requires_grad];optimizer=torch.optim.Adam(parameters,lr=.0003)
    losses=[];batch=8;length=128
    for update in range(a.updates):
        selected=[]
        for name in rng.choice(names,batch):
            preferred=[s for s in families[name] if s['priority']]
            group=preferred if preferred and rng.random()<.5 else families[name]
            selected.append(group[int(rng.integers(len(group)))])
        starts=[0 if rng.random()<.2 else int(rng.integers(max(1,len(s['x'])-length+1))) for s in selected]
        initial=torch.zeros((1,batch,a.units));count=max(starts)
        if count:
            prefix=torch.zeros((batch,count,actor.hidden+90))
            for i,(s,n) in enumerate(zip(selected,starts)):
                if n:prefix[i,:n]=s['x'][:n]
            with torch.no_grad():
                encoded,_=actor.intent_core(actor.intent_features(prefix),initial)
                for i,n in enumerate(starts):
                    if n:initial[0,i]=encoded[i,n-1]
        xs=[];targets=[];masks=[]
        for s,start in zip(selected,starts):
            n=min(length,len(s['x'])-start);pad=length-n
            xs.append(torch.cat((s['x'][start:start+n],s['x'][start+n-1:start+n].expand(pad,-1))))
            targets.append(torch.cat((s['target'][start:start+n],s['target'][start+n-1:start+n].expand(pad,-1))))
            masks.append(torch.arange(length)<n)
        latent,_=actor.intent_core(actor.intent_features(torch.stack(xs)),initial);prediction=actor.project_maneuver(latent)
        target=torch.stack(targets);mask=torch.stack(masks).float();den=mask.sum().clamp_min(1)
        loss=1000.*(((prediction-target)**2)*mask[:,:,None]).sum()/den
        loss+=100.*(((torch.diff(prediction,dim=1)-torch.diff(target,dim=1))**2)*mask[:,1:,None]).sum()/mask[:,1:].sum().clamp_min(1)
        centers=torch.tensor([-.6166667,0.,.6166667]);distance=abs(target[:,:,1,None]-centers);labels=distance.argmin(-1)
        logits=-((prediction[:,:,1,None]-centers)**2)/.04
        ce=torch.nn.functional.cross_entropy(logits.flatten(0,1),labels.flatten(),reduction='none').reshape_as(mask)
        discrete=(distance.min(-1).values<.05)*mask;loss+=3*(ce*discrete).sum()/discrete.sum().clamp_min(1)
        for group in optimizer.param_groups:group['lr']=.0003 if update<a.updates*3//4 else .0001
        optimizer.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(parameters,10.);optimizer.step()
        if update%500==0:print('memory',a.seed,update,float(loss.detach()),flush=True);losses.append(dict(update=update,loss=float(loss.detach())))
    for name,value in actor.state_dict().items():
        if not name.startswith(('intent_features.','intent_core.','intent_projection.')):
            torch.testing.assert_close(value,c['state'][name],rtol=0,atol=0)
    origin={**c['origin'],'stage':'separate-private-neural-maneuver-memory','memorySeed':a.seed,'datasetHash':manifest['hash'],
        'sourceModelHash':hashlib.sha256(a.checkpoint.read_bytes()).hexdigest(),'actuatorControllersChanged':False,'teacherAtInference':False,'prioritySeed':a.priority_seed}
    atomic_report(a.output/'policy.json',actor.export(origin=origin))
    torch.save(dict(architecture=actor.architecture,hidden=actor.hidden,history=1,maneuverHidden=a.units,intentScale=a.scale,
        state=actor.state_dict(),featureVersion=actor.feature_version,origin=origin),a.output/'model.pt')
    atomic_report(a.output/'training.json',dict(seed=a.seed,updates=a.updates,losses=losses,wallSeconds=time.monotonic()-started,
        sampling='uniform-family-and-episode',prefix='exact-current-network-detached',sequenceLength=length,
        families={k:len(v) for k,v in families.items()},qualified=False))

if __name__=='__main__':main()
