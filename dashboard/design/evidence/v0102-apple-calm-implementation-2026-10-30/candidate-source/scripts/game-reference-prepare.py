"""Explicit independent neural preparation. Artifacts remain in private cache."""
from pathlib import Path
import argparse,json,time
import torch
from game_lab.dataset import collect,load_sequences
from game_lab.models import Actor,fit


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--architecture',choices=('dense','history','gru','set-gru'),default='gru')
    p.add_argument('--episodes',type=int,default=42);p.add_argument('--seconds',type=float,default=90.)
    p.add_argument('--updates',type=int,default=2000);p.add_argument('--dagger-rounds',type=int,default=2)
    p.add_argument('--hidden',type=int,default=64);p.add_argument('--dataset',type=Path)
    p.add_argument('--steer-weight',type=float,default=25.);p.add_argument('--clean-only',action='store_true')
    a=p.parse_args();torch.set_num_threads(1);torch.manual_seed(a.seed)
    a.output.mkdir(parents=True,exist_ok=True);dataset=a.dataset or a.output/'dataset'
    if not list(dataset.glob('train-*.npz')):collect(dataset,seed=a.seed,episodes=a.episodes,duration=a.seconds)
    actor=Actor(a.architecture,hidden=a.hidden);trace=[];started=time.monotonic()
    for r in range(a.dagger_rounds+1):
        sequences=load_sequences(dataset)
        if a.clean_only:sequences=[s for s in sequences if s.get('rolloutClean')]
        fit_report=fit(actor,sequences,seed=a.seed+r,updates=a.updates,steer_weight=a.steer_weight)
        trace.append({k:v for k,v in fit_report.items() if k!='optimizer'})
        origin=dict(kind='independent-causal-preparation',seed=a.seed,round=r,
            demonstrations=sum(len(s['x']) for s in sequences),cleanOnly=a.clean_only,teacherAtInference=False)
        torch.save(dict(architecture=a.architecture,hidden=a.hidden,history=actor.history,state=actor.state_dict(),
            optimizer=fit_report['optimizer'],origin=origin),a.output/f'round-{r}.pt')
        policy=actor.export(origin=origin)
        (a.output/f'round-{r}.json').write_text(json.dumps(policy,separators=(',',':'))+'\n')
        (a.output/'preparation.json').write_text(json.dumps(dict(seed=a.seed,architecture=a.architecture,trace=trace,
            wallSeconds=time.monotonic()-started,qualified=False),indent=2)+'\n')
        print('fit',a.seed,a.architecture,r,trace[-1]['losses'][-1],flush=True)
        if r<a.dagger_rounds:
            actor.eval();collect(dataset,seed=a.seed+100000*(r+1),episodes=a.episodes//2,duration=a.seconds,
                actor=actor,round_number=r+1)
    (a.output/'policy.json').write_text(json.dumps(policy,separators=(',',':'))+'\n')


if __name__=='__main__':main()
