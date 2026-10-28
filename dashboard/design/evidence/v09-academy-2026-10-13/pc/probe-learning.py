"""Bounded isolated learning probes. No original driver or artifact is opened."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_profiles import preset
from game_learning import Policy

P=Path(__file__).parent
reports=[]
for method,seed in [('evolution',1),('neat',2),('ppo',3),('imitation',5),('ppo_smooth',6)]:
 p=academy_profile(preset(seed,method));trainer=AcademyTrainer(p,'oval-1');started=time.monotonic();ticks=0
 initial=trainer.learner.candidate_policy() if hasattr(trainer.learner,'candidate_policy') else trainer.learner.policy()
 while time.monotonic()-started<90:
  trainer.tick();ticks+=1
 final=trainer.learner.candidate_policy() if hasattr(trainer.learner,'candidate_policy') else trainer.learner.policy()
 results=[]
 for label,snapshot in [('initial',initial),('trained',final)]:
  policy=Policy(snapshot)
  for trial in range(5):
   e=Episode('oval-1','launch',1000001+trial)
   while not e.reason:e.step(policy.act(e.observations(),world=e.world,index=0))
   results.append({'version':label,**e.result()})
 row={'method':method,'seed':seed,'wallBudgetSeconds':90,'ticks':ticks,'steps':trainer.steps,
      'phase':trainer.phase,'updates':trainer.state['updates'],'stats':trainer.state['stats'],
      'evaluations':trainer.state['evaluations'],'heldoutLaunches':results}
 (P/('probe-'+method+'.json')).write_text(json.dumps(row,indent=2)+'\n');reports.append(row)
 print(method,trainer.steps,trainer.phase,[(label,sum(r['reason']=='success' for r in results if r['version']==label)) for label in ['initial','trained']],flush=True)
(P/'learning-probes.json').write_text(json.dumps({'scope':'one seed per method, 90 wall seconds; five heldout launch scenarios each, not full race qualification','results':reports},indent=2)+'\n')
