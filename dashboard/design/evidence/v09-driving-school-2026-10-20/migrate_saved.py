from pathlib import Path
import json
import numpy as np
from game_direct_trainer import DirectTrainer
r=Path('/tmp/smartpc-school-original-checkpoints');p=Path(__file__).parent;profiles=json.loads((r/'profiles.json').read_text());rows=[]
for method in ('residual_ppo','residual_sac','residual_td3','residual_tactic'):
 c=json.loads((r/(method+'.json')).read_text());old_steps=c['steps'];t=DirectTrainer(profiles[method],'oval-1',c)
 assert t.steps==old_steps and t.learner.update_index==0 and t.profile['hidden']==128 and t.state['migration']['version']=='direct-driving-3'
 for _ in range(4000):t.tick()
 saved=t.checkpoint(c['seconds']);u=DirectTrainer(t.profile,'oval-1',json.loads(json.dumps(saved)))
 for _ in range(100):t.tick();u.tick()
 np.testing.assert_array_equal(t.learner.actor,u.learner.actor);np.testing.assert_array_equal(t.episode.world.state,u.episode.world.state)
 rows.append(dict(method=method,previousSteps=old_steps,newSteps=t.steps,hidden=t.profile['hidden'],sourceProtocol=c['protocol'],newProtocol=saved['protocol'],exactResume=True,recipeArchives=t.state['recipeArchives']))
 print(method,'migrated and resumed exactly',flush=True)
(p/'migration-checks.json').write_text(json.dumps(dict(status='passed',rows=rows,scope='Private paused-checkpoint copies; full histories and artifacts preserved by staged installation'),indent=2)+'\n')
