from pathlib import Path
import argparse
from game_lab.dataset import collect

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--episodes',type=int,default=42);p.add_argument('--seconds',type=float,default=180.)
    p.add_argument('--stop-unsafe',action='store_true',help='End correction collection at its first unsafe event; never a completed evaluation window.')
    p.add_argument('--bots',type=int,nargs='+',default=[1,2,3]);p.add_argument('--checkpoint',type=Path);p.add_argument('--round',type=int,default=0);p.add_argument('--noise',type=float,default=0.);p.add_argument('--intervention',type=float,default=0.);p.add_argument('--road-sensors',action='store_true');p.add_argument('--families',nargs='+',default=['traffic']);a=p.parse_args()
    actor=None
    if a.checkpoint:
        import torch
        from game_lab.models import Actor
        torch.set_num_threads(1)
        c=torch.load(a.checkpoint,map_location='cpu',weights_only=True)
        actor=Actor(c['architecture'],c['hidden'],c['history'],auxiliary='intent' if 'aux_classifier.weight' in c['state'] else 'aux_head.weight' in c['state'],maneuver_hidden=c.get('maneuverHidden',2),maneuver_scale=c.get('intentScale',1.))
        actor.load_state_dict(c['state']);actor.eval()
        actor.feature_version=c.get('featureVersion','direct-physical-90-v1')
        if actor.feature_version!=('direct-physical-90-road-v2' if a.road_sensors else 'direct-physical-90-v1'):p.error('Checkpoint and collection sensors differ')
    collect(a.output,seed=a.seed,episodes=a.episodes,duration=a.seconds,families=tuple(a.families),bot_counts=tuple(a.bots),actor=actor,round_number=a.round,noise=a.noise,intervention=a.intervention,feature_version='direct-physical-90-road-v2' if a.road_sensors else 'direct-physical-90-v1',stop_unsafe=a.stop_unsafe)
