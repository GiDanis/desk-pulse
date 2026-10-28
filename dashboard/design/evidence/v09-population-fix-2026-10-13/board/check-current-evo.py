"""Restore the user's current checkpoint privately; originals remain read only."""
import hashlib,json,sqlite3,sys
from pathlib import Path
H=Path('/var/lib/smartpc-dashboard');GAME=H/'.local/share/SmartPC/SmartPC/game';P=H/'v09-population-proof'
sys.path.insert(0,str(H/'smartpc-v09-rc11-project/dashboard'))
from game_academy_trainer import AcademyTrainer
with sqlite3.connect('file:'+str(GAME/'game.sqlite')+'?mode=ro',uri=True) as db:
 profile,key,steps=db.execute("SELECT profile,checkpoint,steps FROM drivers WHERE name='Evo'").fetchone()
file=GAME/'policies'/(key+'.json');before=hashlib.sha256(file.read_bytes()).hexdigest();saved=json.loads(file.read_text());profile=json.loads(profile)
track=saved['configuration']['track']['id']
t=AcademyTrainer(profile,track,saved);initial=json.loads(json.dumps(t.checkpoint(saved['seconds'])))
rows,obs,meta=t.frame('Evo',1,31,paused=True)
assert meta['presentation']=='population' and meta['count']==32 and meta['selected']==31
assert t.steps==steps and meta['generation']==saved['learner']['generation']+1
assert json.loads(json.dumps(t.checkpoint(saved['seconds'])))==initial
for _ in range(512):t.tick()
state=json.loads(json.dumps(t.checkpoint(saved['seconds'])));resumed=AcademyTrainer(profile,track,state)
assert json.loads(json.dumps(resumed.checkpoint(saved['seconds'])))==state
assert hashlib.sha256(file.read_bytes()).hexdigest()==before==key
report=dict(status='passed',checkpoint=key,stepsPreserved=steps,generation=meta['generation'],population=meta['count'],selected=meta['selected'],privateResumeExact=True,originalArtifactUnchanged=True)
(P/'current-evo-copy.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
