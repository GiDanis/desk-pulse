"""Migrate exported personal copies only, preserve every original artifact."""
from pathlib import Path
import json,hashlib
import numpy as np
from game_direct_trainer import DirectTrainer
P=Path(__file__).parent;private=Path('/tmp/smartpc-attack-live-20261022');data=json.loads((private/'snapshot.json').read_text())
root=private/'migrated';root.mkdir(mode=0o700,exist_ok=True);profiles={};rows=[]
for d in data['drivers']:
 if not d['checkpoint']:continue
 method=d['profile']['algorithm'];old=data['models'][method];p={**d['profile'],'trafficLearning':'attack-1','relativeAdvantage':0.}
 t=DirectTrainer(p,'oval-1',old,objective='impara_sorpasso');c=t.checkpoint(old.get('seconds',0.));profiles[method]=p
 np.testing.assert_array_equal(t.learner.actor,np.asarray(old['learner']['actor']))
 assert t.steps==old['steps'] and t.decisions==old['decisions']
 assert t.state['champion']==old['curriculum']['champion'] and t.state['raceChampion']==old['curriculum']['raceChampion']
 assert len(t.state['recipeArchives'])>len(old['curriculum'].get('recipeArchives',[]))
 (root/(method+'.json')).write_text(json.dumps(c));(root/(method+'.json')).chmod(0o600)
 rows.append(dict(name=d['name'],method=method,sourceCheckpoint=d['checkpoint'],steps=t.steps,decisions=t.decisions,actorPreserved=True,soloChampionPreserved=True,raceChampionPreserved=True,replayTargetsArchived=True,newReplayCount=getattr(t.learner,'count',0)))
(root/'profiles.json').write_text(json.dumps(profiles));(root/'metadata.json').write_text(json.dumps({k:v for k,v in data.items() if k not in ('models',)}))
(P/'personal-copy-migration.json').write_text(json.dumps(dict(status='passed',productionChanges=False,rows=rows),indent=2)+'\n')
print('Four personal copies migrated; actors/champions/history preserved; no production writes')
