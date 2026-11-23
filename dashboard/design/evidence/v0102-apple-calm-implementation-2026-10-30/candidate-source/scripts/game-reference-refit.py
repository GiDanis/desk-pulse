from pathlib import Path
import argparse,hashlib,json,time
import torch
from game_lab.models import Actor,fit_with_episode_context
from game_lab.dataset import load_sequences


def main():
    p=argparse.ArgumentParser();p.add_argument('--preparation',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--updates',type=int,default=2000)
    p.add_argument('--auxiliary',action='store_true');p.add_argument('--checkpoint',type=Path);p.add_argument('--critical-sampling',action='store_true');p.add_argument('--clean-only',action='store_true');p.add_argument('--steer-weight',type=float,default=25.);p.add_argument('--rate',type=float,default=.0003);p.add_argument('--intent-supervision',action='store_true');p.add_argument('--dataset',type=Path);p.add_argument('--intent-only',action='store_true')
    a=p.parse_args();torch.set_num_threads(1);a.output.mkdir(parents=True,exist_ok=True)
    source=a.checkpoint or a.preparation/'round-2.pt';c=torch.load(source,map_location='cpu',weights_only=True)
    torch.manual_seed(a.seed)
    actor=Actor(c['architecture'],c['hidden'],c['history'],auxiliary='intent' if a.intent_supervision else a.auxiliary,maneuver_hidden=c.get('maneuverHidden',2),maneuver_scale=c.get('intentScale',1.))
    actor.feature_version=c.get('featureVersion','direct-physical-90-v1')
    loaded=actor.load_state_dict(c['state'],strict=False)
    assert not loaded.unexpected_keys and set(loaded.missing_keys)<=({'aux_head.weight','aux_head.bias','aux_classifier.weight','aux_classifier.bias'} if a.auxiliary or a.intent_supervision else set())
    if a.intent_only:
        if actor.architecture not in ('gru-intent','gru-intent-deep','gru-maneuver'):raise ValueError('Structured intent actor required')
        for name,parameter in actor.named_parameters():parameter.requires_grad_(name.startswith(('core.','intent.','intent_skip.','intent_features.','intent_core.','intent_projection.')))
    from game_lab.artifacts import freeze_dataset
    manifest=freeze_dataset(a.dataset or a.preparation/'dataset',a.output/'dataset')
    sequences=load_sequences(a.output/'dataset')
    if any(s['featureVersion']!=actor.feature_version for s in sequences):raise ValueError('Training sensors mismatch')
    if a.clean_only:sequences=[s for s in sequences if s.get('rolloutClean')]
    started=time.monotonic()
    fit=fit_with_episode_context(actor,sequences,seed=a.seed,updates=a.updates,critical_sampling=a.critical_sampling,steer_weight=a.steer_weight,rate=a.rate)
    source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((a.output/'dataset').glob('train-*.npz'))}
    dataset_hash=hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest()
    origin={**c['origin'],'stage':'recurrent-context-refit','datasetHash':dataset_hash,'additionalUpdates':a.updates,
        'sourceModelHash':hashlib.sha256(source.read_bytes()).hexdigest()}
    origin['auxiliary']=fit.get('auxiliary')
    origin['examplesThisStage']=sum(len(s['x']) for s in sequences)
    policy=actor.export(origin=origin)
    temporary=a.output/'model.pt.tmp';torch.save(dict(architecture=actor.architecture,hidden=actor.hidden,history=actor.history,
        state=actor.state_dict(),featureVersion=actor.feature_version,maneuverHidden=actor.maneuver_hidden,intentScale=actor.maneuver_scale,optimizer=fit['optimizer'],origin=origin,rng=fit['rng'],torchRng=torch.get_rng_state()),temporary)
    temporary.replace(a.output/'model.pt')
    (a.output/'policy.json.tmp').write_text(json.dumps(policy,separators=(',',':'))+'\n');(a.output/'policy.json.tmp').replace(a.output/'policy.json')
    (a.output/'refit.json').write_text(json.dumps({k:v for k,v in fit.items() if k not in ('optimizer','rng')}|
        dict(seed=a.seed,datasetHash=dataset_hash,sourceHashes=source_hashes,wallSeconds=time.monotonic()-started,qualified=False),indent=2)+'\n')


if __name__=='__main__':main()
