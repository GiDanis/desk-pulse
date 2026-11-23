"""Private measured headless grids; never a scientific or screen certificate."""
from pathlib import Path
import argparse,json
from game_lab.races import run
from game_lab.artifacts import atomic_report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--policy',type=Path,action='append',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--qualifying',action='store_true')
    p.add_argument('--laps',type=int,default=3);p.add_argument('--seed',type=int,default=1)
    p.add_argument('--track',default='oval-1');p.add_argument('--qualifying-times',type=float,nargs='+');a=p.parse_args()
    result=run([json.loads(f.read_text()) for f in a.policy],qualifying=a.qualifying,laps=a.laps,seed=a.seed,track=a.track,qualifying_times=a.qualifying_times)
    atomic_report(a.output,result);print(json.dumps({k:result[k] for k in ('kind','cars','laps','complete','allCarsRepresented','simulatedSeconds','wallSeconds')}),flush=True)
