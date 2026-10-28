"""Migrate a private recurrent preparation to the versioned road sensors."""
from pathlib import Path
import argparse,json,hashlib
import torch
from game_lab.models import Actor
from game_lab.sensors import road_policy
from game_lab.artifacts import atomic_report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();c=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
    actor=Actor(c['architecture'],c['hidden'],c['history']);actor.load_state_dict({k:v for k,v in c['state'].items() if not k.startswith('aux_')})
    data=road_policy(actor.export(origin=c['origin']));state={k:torch.as_tensor(v,dtype=torch.float32) for k,v in data['weights'].items()}
    state.update(mean=torch.tensor(data['normalization']['mean']),scale=torch.tensor(data['normalization']['scale']))
    origin={**data['origin'],'parentCheckpointHash':hashlib.sha256(a.checkpoint.read_bytes()).hexdigest()};data['origin']=origin
    a.output.mkdir(parents=True,exist_ok=True);atomic_report(a.output/'policy.json',data)
    torch.save(dict(architecture=c['architecture'],hidden=c['hidden'],history=c['history'],state=state,featureVersion=data['features'],origin=origin),a.output/'model.pt')
