from pathlib import Path
import argparse,json
from game_lab.reference_learning import train,continue_training

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--dataset',type=Path)
    p.add_argument('--method',choices=('ppo','sac','td3'));p.add_argument('--seed',type=int,default=1)
    p.add_argument('--history',type=int,default=4);p.add_argument('--decisions',type=int,default=32768);p.add_argument('--bc-updates',type=int,default=2000)
    p.add_argument('--recipe',choices=('standard','teacher-anchored-1','normalized-anchored-2'),default='standard')
    p.add_argument('--resume',type=Path)
    a=p.parse_args()
    if a.resume:print(json.dumps(continue_training(a.output,a.resume,decisions=a.decisions)))
    else:
        if a.dataset is None or a.method is None:p.error('--dataset and --method are required for a new preparation')
        print(json.dumps(train(a.output,a.dataset,method=a.method,seed=a.seed,history=a.history,decisions=a.decisions,bc_updates=a.bc_updates,recipe=a.recipe)))
