import sys,json,time,hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0,'/home/giuseppe/Documenti/Workspace/SmartPC/dashboard')
from game_residual_trainer import ResidualTrainer
from game_residual import key
p=Path('/tmp/smartpc-mature-private/crono.json');c=json.loads(p.read_text());profile=c['curriculum']['champion']['profile'];start=time.monotonic()
a=ResidualTrainer(profile,'oval-1',c,objective=c['objective'])
np.testing.assert_array_equal(a.learner.actor,c['learner']['actor']);assert a.steps==c['steps'] and a.decisions==c['decisions']
assert key(a.state['champion']['policy'])==key(c['curriculum']['champion']['policy'])
# A resumed preview cannot certify a partial lap as PB.
assert not a.preview.world.timing.row(0)['currentValid']
for _ in range(1000):a.tick()
b=ResidualTrainer(profile,'oval-1',json.loads(json.dumps(a.checkpoint(c['seconds']))),objective=c['objective'])
for _ in range(500):a.tick();b.tick()
np.testing.assert_array_equal(a.learner.actor,b.learner.actor);np.testing.assert_array_equal(a.episode.world.state,b.episode.world.state)
r=dict(status='passed',originalSteps=c['steps'],originalDecisions=c['decisions'],secondsOfPriorExperience=c['seconds'],actorRetained=True,championRetained=True,optimizerAndRngResumeExact=True,decisionsAfter=a.decisions,sourceCheckpointSha256=hashlib.sha256(p.read_bytes()).hexdigest(),productionWrites=0,seconds=time.monotonic()-start)
Path('dashboard/design/evidence/v09-timing-improvements-2026-10-16/mature-resume.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
