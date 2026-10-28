"""Migrate only read-only exported checkpoint copies; production stays untouched."""
from pathlib import Path
import json,hashlib
import numpy as np
from game_direct_trainer import DirectTrainer
from game_residual import key
from game_neural_mixture import EXPERT_SIZE
from game_racing_presets import production_profile

P=Path(__file__).parent;private=Path('/tmp/smartpc-racing-implementation-private-20261021/snapshot')
meta=json.loads((private/'saved-meta.json').read_text());rows=[]
for d in meta['drivers']:
    if d['name']=='Maestro' or not d['checkpoint']:continue
    source=private/'models'/(d['checkpoint']+'.json');payload=json.loads(source.read_text())
    payload['migrationSource']=d['checkpoint']
    p=production_profile(json.loads(d['profile']))
    old=np.asarray(payload['learner']['actor']);t=DirectTrainer(p,'oval-1',payload)
    np.testing.assert_array_equal(t.learner.actor[:EXPERT_SIZE],old[:EXPERT_SIZE])
    np.testing.assert_array_equal(t.learner.actor[EXPERT_SIZE:],t.state['raceChampion']['policy']['weights'][EXPERT_SIZE:])
    assert key(t.state['raceChampion']['policy'])==key(payload['curriculum']['champion']['policy'])
    assert t.steps==d['steps'] and t.state['migration']['sourceCheckpoint']==d['checkpoint']
    initial=t.checkpoint(d['seconds']);(private/(d['name']+'-migrated.json')).write_text(json.dumps(initial))
    for _ in range(220):t.tick()
    r=DirectTrainer(p,'oval-1',json.loads(json.dumps(t.checkpoint(d['seconds']))))
    for _ in range(40):t.tick();r.tick()
    np.testing.assert_array_equal(t.learner.actor,r.learner.actor)
    np.testing.assert_array_equal(t.episode.world.state,r.episode.world.state)
    assert hashlib.sha256(source.read_bytes()).hexdigest()==d['checkpoint']
    rows.append(dict(id=d['id'],name=d['name'],sourceCheckpoint=d['checkpoint'],steps=d['steps'],seconds=d['seconds'],
        originalActorHash=hashlib.sha256(old.tobytes()).hexdigest(),preservedSoloHash=hashlib.sha256(old[:EXPERT_SIZE].tobytes()).hexdigest(),
        activeActorHash=hashlib.sha256(np.asarray(initial['learner']['actor']).tobytes()).hexdigest(),trafficFromOwnStableChampion=True,epochSteps=initial['curriculum']['epochStart'],
        exactResume=True,originalUntouched=True,oldRacePolicyPreserved=True))
P.joinpath('saved-migration-check.json').write_text(json.dumps(dict(status='passed',capturedAt=meta['capturedAt'],
    productionChanges=False,rows=rows),indent=2)+'\n')
print('Preserved solo weights, consolidated own stable traffic, originals, totals and exact resume:',len(rows))
