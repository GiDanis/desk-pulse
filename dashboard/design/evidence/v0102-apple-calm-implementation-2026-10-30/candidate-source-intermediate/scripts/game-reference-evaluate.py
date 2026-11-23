from pathlib import Path
import argparse,json
from game_lab.evaluation import evaluate

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--policy',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--split',choices=('development','final'),default='development');p.add_argument('--seconds',type=float,default=180.)
    p.add_argument('--cases',type=int,default=3);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
    evaluate(json.loads(a.policy.read_text()) if a.policy else None,split=a.split,duration=a.seconds,cases=a.cases,output=a.output)
