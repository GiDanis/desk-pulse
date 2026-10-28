"""Bounded private learning run; never opens the production GameStore."""
import argparse,json,time,sys
from pathlib import Path
import numpy as np
parser=argparse.ArgumentParser();parser.add_argument('--method',default='residual_ppo');parser.add_argument('--seed',type=int,default=2);parser.add_argument('--decisions',type=int,default=4096);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--source',type=Path);args=parser.parse_args()
source=args.source or Path(__file__).resolve().parents[4]
sys.path.insert(0,str(source))
from game_residual import profile,key
from game_residual_trainer import ResidualTrainer
p=profile(args.seed,args.method);t=ResidualTrainer(p,'oval-1');start=time.monotonic();last=0
while t.decisions<args.decisions or t.check or t.iterator:
 t.tick()
 if t.decisions//1024>last:
  last=t.decisions//1024
  print(json.dumps(dict(method=args.method,seed=args.seed,decisions=t.decisions,updates=t.state['updates'],elapsed=time.monotonic()-start,status=t.state['status'])),flush=True)
import hashlib
source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.glob('game_*.py')}
result=dict(sourceHashes=source_hashes,method=args.method,seed=args.seed,decisions=t.decisions,physicalSteps=t.steps,seconds=time.monotonic()-start,stats=t.state['stats'],evaluations=t.state['evaluations'],champion=t.state['champion']['policy'],recipe=t.spec)
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
private=Path('/tmp/smartpc-residual-checkpoints-v2');private.mkdir(mode=0o700,exist_ok=True)
(private/(args.method+'-'+str(args.seed)+'.json')).write_text(json.dumps(t.checkpoint(result['seconds'])))
print(json.dumps({k:v for k,v in result.items() if k not in ('champion','evaluations','sourceHashes')}),flush=True)
