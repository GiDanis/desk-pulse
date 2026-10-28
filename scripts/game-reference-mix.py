"""Development ablation of two modules from the SAME independent preparation."""
from pathlib import Path
import argparse,hashlib,os,sys
import torch
from game_lab.models import Actor
from game_lab.artifacts import atomic_report

def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--refined',type=Path,required=True)
    p.add_argument('--variant',choices=('base-memory','refined-memory','calibrated-steer','calibrated-pedal','calibrated-controls'),required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--fraction',type=float,default=1.)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--evaluate',action='store_true');a=p.parse_args();torch.set_num_threads(1)
    if not 0<a.fraction<=1 or (a.fraction!=1 and not a.variant.startswith('calibrated-')):p.error('Calibration interpolation fraction')
    b=torch.load(a.base,map_location='cpu',weights_only=True);r=torch.load(a.refined,map_location='cpu',weights_only=True)
    for k in ('architecture','hidden','history','featureVersion','maneuverHidden','intentScale'):
        if b.get(k)!=r.get(k):raise ValueError('Module descriptors differ')
    for k in ('mean','scale',*[k for k in b['state'] if k.startswith('core.')]):torch.testing.assert_close(b['state'][k],r['state'][k],rtol=0,atol=0)
    memory=b if a.variant=='base-memory' else r;actuators=r if a.variant=='base-memory' else b
    actor=Actor(b['architecture'],b['hidden'],maneuver_hidden=b.get('maneuverHidden',2),maneuver_scale=b.get('intentScale',1.));actor.feature_version=b['featureVersion']
    if a.variant.startswith('calibrated-'):
        channel=('steer_','pedal_') if a.variant=='calibrated-controls' else 'steer_' if a.variant=='calibrated-steer' else 'pedal_'
        for k in b['state']:
            if not k.startswith(('steer_','pedal_')):torch.testing.assert_close(b['state'][k],r['state'][k],rtol=0,atol=0)
        state={k:((1-a.fraction)*b['state'][k]+a.fraction*r['state'][k] if k.startswith(channel) else b['state'][k]) for k in b['state']}
    else:state={k:(memory if k.startswith(('intent_features.','intent_core.','intent_projection.')) else actuators)['state'][k] for k in b['state']}
    actor.load_state_dict(state)
    origin={**r['origin'],'stage':'same-preparation-module-retention','preparationSeed':a.seed,'variant':a.variant,
        'baseCheckpointHash':hashlib.sha256(a.base.read_bytes()).hexdigest(),'refinedCheckpointHash':hashlib.sha256(a.refined.read_bytes()).hexdigest(),
        'teacherAtInference':False,'calibrationFraction':a.fraction}
    a.output.mkdir(parents=True,exist_ok=False);atomic_report(a.output/'policy.json',actor.export(origin=origin))
    torch.save(dict(architecture=actor.architecture,hidden=actor.hidden,history=1,maneuverHidden=actor.maneuver_hidden,intentScale=actor.maneuver_scale,
        featureVersion=actor.feature_version,state=actor.state_dict(),origin=origin),a.output/'model.pt')
    if a.evaluate:
        args=[sys.executable,str(Path(__file__).with_name('game-reference-evaluate.py')),'--policy',str(a.output/'policy.json'),'--output',str(a.output/'development.json'),'--split','development']
        os.execv(sys.executable,args)

if __name__=='__main__':main()
