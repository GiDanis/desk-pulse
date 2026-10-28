"""Summarize frozen diagnostics; assert complete cohorts, never select defaults."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,platform,statistics
import numpy as np
HERE=Path(__file__).parent
data=json.loads((HERE/'frozen-probes.json').read_text());ablation=json.loads((HERE/'expert-ablation.json').read_text())
assert len(data['rows'])==48 and len(ablation['rows'])==3
assert len({(r['name'],r['role'],r['traffic'],r['seed']) for r in data['rows']})==48
data['shadowScope']='Expert shadow commands recomputed after the real command updates previous-action inputs; not exact actuator decompositions'
(HERE/'frozen-probes.json').write_text(json.dumps(data,indent=2)+'\n')
groups=defaultdict(list)
for r in data['rows']:groups[r['name'],r['role'],r['traffic']].append(r)
rows=[]
for (name,role,traffic),cases in groups.items():
 assert len(cases)==3
 rows.append(dict(name=name,role=role,traffic=traffic,cases=3,
  meanSpeedAfter5=statistics.mean(r['meanSpeedAfter5'] for r in cases),passes=sum(r['passes'] for r in cases),
  contacts=sum(r['contacts'] for r in cases),limits=sum(r['limits'] for r in cases),
  stoppedAlongsideSeconds=sum(r['stoppedAlongsideSeconds'] for r in cases),meanGate=statistics.mean(r['meanGate'] for r in cases),
  reasons=[r['reason'] for r in cases]))
root=HERE.parents[2]
receipt=dict(status='study-complete-no-runtime-change',capturedAt=data['capturedAt'],scenarioSeeds=[961101,961102,961103],trainingSeeds=0,
 frozenCases=48,ablationCases=3,rows=rows,ablationMeanSpeedAfter5=statistics.mean(r['meanSpeedAfter5'] for r in ablation['rows']),
 ablationContacts=sum(r['contacts'] for r in ablation['rows']),ablationPasses=sum(r['passes'] for r in ablation['rows']),
 physicsTicks=sum(round(r['seconds']*60) for r in data['rows']+ablation['rows']),wallSecondsSum=sum(r['wallSeconds'] for r in data['rows']+ablation['rows']),
 runtime=dict(python=platform.python_version(),numpy=np.__version__,machine=platform.machine(),nativeSha256=hashlib.sha256((root/'libsmartpc_game_native.so').read_bytes()).hexdigest()),
 scriptHashes={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ('capture.py','probe.py','mechanisms.py','ablate.py','summarize.py')},
 productionChanges=False,newTraining=False,modelsPrivate=True,defaultsSelected=False,boardVisualQualification=False,
 limitation='Frozen three-scenario diagnosis, no learning convergence, no FPS or board throughput claim. Shadow pedals are post-command observations, not exact actuator decomposition. Probe main guard/metadata clarified after execution; numerical run body unchanged.')
(HERE/'summary.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('48 frozen cases + 3 paired ablations; study only; contacts in ablation',receipt['ablationContacts'])
