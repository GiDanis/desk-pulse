"""Collect physical expert replay on training seeds; no evaluation-bank access."""
from pathlib import Path
import argparse,json
from game_lab.actuators import configure
from game_lab.demonstrations import collect

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--seconds',type=float,default=90.);p.add_argument('--capacity',type=int,default=16384)
    p.add_argument('--actuator-mode',choices=('readout','plastic','plastic-context'));a=p.parse_args()
    collect(configure(json.loads(a.base.read_text()),a.actuator_mode),a.output,seed=a.seed,seconds=a.seconds,capacity=a.capacity)
