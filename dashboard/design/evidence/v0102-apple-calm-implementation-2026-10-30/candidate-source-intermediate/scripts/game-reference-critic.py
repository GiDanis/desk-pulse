from pathlib import Path
import argparse,json,torch
from game_lab.critic_audit import audit

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--base',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,required=True);p.add_argument('--horizon',type=int,default=40);a=p.parse_args()
    torch.set_num_threads(1);result=audit(a.checkpoint,json.loads(a.base.read_text()),output=a.output,seed=a.seed,horizon=a.horizon)
    print('critic probe',result['finiteReturnRankAgreement'],result['rankPairs'],flush=True)
