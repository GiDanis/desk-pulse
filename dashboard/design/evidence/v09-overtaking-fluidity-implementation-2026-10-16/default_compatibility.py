import json,sys,hashlib
from pathlib import Path
from game_residual import profile,recipe
from game_residual_trainer import ResidualTrainer
mode,root=sys.argv[1],Path(sys.argv[2]);root.mkdir(exist_ok=True)
rows=[]
for method in ('residual_ppo','residual_sac','residual_td3','residual_tactic'):
 p=profile(21,method)
 if mode=='old':
  a=ResidualTrainer(p,'oval-1')
  for _ in range(80):a.tick()
  (root/(method+'-start.json')).write_text(json.dumps(a.checkpoint(12.)))
 else:a=ResidualTrainer(p,'oval-1',json.loads((root/(method+'-start.json')).read_text()))
 for _ in range(1000):a.tick()
 result=dict(recipe=recipe(p),learner=a.learner.checkpoint(),steps=a.steps,decisions=a.decisions,world=a.episode.world.snapshot(),reward=a.episode.return_total,terms=a.episode.term_totals,inflight=a.inflight,stats=a.state['stats'])
 path=root/(method+'-'+mode+'.json');path.write_text(json.dumps(result,sort_keys=True,separators=(',',':')))
 if mode!='old':
  expected=json.loads((root/(method+'-old.json')).read_text());assert json.loads(path.read_text())==expected,method
  rows.append(dict(method=method,steps=a.steps,decisions=a.decisions,exactLearnerAndPhysics=True,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
if mode!='old':print(json.dumps(dict(status='passed',defaultRecipe='race-residual-2',cases=rows),indent=2))
