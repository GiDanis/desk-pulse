"""Run pinned original End2Race evaluations in its separate Python 3.11 env.

No external code is vendored in SmartPC. This calls the reference's own
evaluate_segment and checkpoints, on a declared subset of its standard cases.
"""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--cases',type=int,default=4)
    a=p.parse_args();root=a.source.resolve()
    commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if commit!='769bedb571125b2392b909fa1e0eb0a0c3649322':raise ValueError('Reference revision mismatch')
    sys.path.insert(0,str(root))
    import torch,yaml
    from imitation.model import End2Race
    from evaluation.eval_multi import evaluate_segment
    from expert.utils import collection_scenarios
    from f1tenth_sim.utils import load_simulator_config
    torch.set_num_threads(1);torch.manual_seed(7301)
    config=yaml.safe_load((root/'config.yaml').read_text());settings=config['eval_multi'];rows=[]
    a.output.parent.mkdir(parents=True,exist_ok=True)
    report=dict(commit=commit,device='cpu',render=False,physicsUnmodified=True,
        subset=True,originalMatrixReproduced=False,checkpoints={},rows=rows)
    for method in ('bc','ppo'):
        path=root/'checkpoint'/f'{method}.pt';model=End2Race().eval()
        model.load_state_dict(torch.load(path,map_location='cpu',weights_only=True))
        report['checkpoints'][method]=hashlib.sha256(path.read_bytes()).hexdigest()
        for map_name in settings['maps'][:2]:
            bank=collection_scenarios(map_name,settings['ego_raceline'],settings['num_startpoints'],
                settings['opponent_racelines'],settings['opponent_speed_scales'])
            for raceline,scale,index in bank[:a.cases]:
                args={**settings,'map_name':map_name,'output_dir':a.output.parent,
                    'opponent_raceline':raceline,'opponent_speed_scale':scale,'ego_idx':int(index)}
                started=time.monotonic()
                result=evaluate_segment(method,model,torch.device('cpu'),load_simulator_config().vehicle,args)
                rows.append(dict(method=method,track=map_name,index=int(index),raceline=raceline,
                    opponentScale=scale,simDuration=args['sim_duration'],wallSeconds=time.monotonic()-started,result=result))
                a.output.write_text(json.dumps(report,indent=2)+'\n')
                print(method,map_name,index,result,flush=True)
    report['status']='subset-reproduced';a.output.write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
