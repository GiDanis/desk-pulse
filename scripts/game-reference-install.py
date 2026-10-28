"""Validate or activate a P7/P9 package in a quiescent, backed-up archive."""
from pathlib import Path
import argparse,json
from game_store import GameStore
from game_reference_release import validate,install
from game_lab.artifacts import atomic_report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--proposal',type=Path,required=True)
    p.add_argument('--arm',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--install',action='store_true')
    a=p.parse_args();proposal=json.loads(a.proposal.read_text());arm=json.loads(a.arm.read_text())
    policies=validate(proposal,arm)
    if a.install:result=install(GameStore(a.root),proposal,arm)
    else:result=dict(validated=True,installed=False,policies=policies)
    atomic_report(a.receipt,result);print(json.dumps(result))
