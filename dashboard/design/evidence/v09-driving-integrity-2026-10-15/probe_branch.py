from pathlib import Path
import sys,json,time
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from game_transfer import BranchCheck,candidate
from game_academy_trainer import AcademyTrainer
s=json.loads(Path(sys.argv[1]).read_text());d=next(d for d in s['tables']['drivers'] if d['name']=='Evo');profile=json.loads(d['profile']);donor=s['artifacts'][d['checkpoint']]['value']
row=next(r for r in s['tables']['objective_paths'] if r['driver']==d['id'] and r['objective']=='impara_infinito' and r['track']=='oval-1')
state=json.loads(row['state']);local=s['artifacts'][state['checkpoint']]['value'];local['transferCandidate']=dict(source=d['checkpoint'],checkpoint=donor,localCheckpoint=state['checkpoint'])
t=AcademyTrainer(profile,'oval-1',local,objective='impara_infinito',balanced=True,batched=True)
initial=t.steps;start=time.monotonic();ticks=0
while t.transfer:
 t.tick();ticks+=1
 if ticks==100:
  c=json.loads(json.dumps(t.checkpoint(2)));t=AcademyTrainer(profile,'oval-1',c,objective='impara_infinito',balanced=True,batched=True)
assert t.steps==initial and t.state['branchTransfer']['adopted']
assert t.input_contract['constantCue']==2/9
result=dict(result=t.state['branchTransfer'],stepsUnchanged=True,durableResume=True,ticks=ticks,pcWallSeconds=time.monotonic()-start,inputContract=t.input_contract)
Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
