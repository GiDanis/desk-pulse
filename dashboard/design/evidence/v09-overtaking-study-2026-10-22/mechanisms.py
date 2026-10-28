"""Public numeric audit of installed reward/gate mechanisms, without training."""
from pathlib import Path
import json,math,hashlib
import numpy as np
from game_neural_mixture import EXPERT_SIZE
from game_direct_bootstrap import base_asset
from game_geometry import get_track
HERE=Path(__file__).parent
data=json.loads(Path('/tmp/smartpc-overtaking-study-20261022/snapshot.json').read_text())
base=np.array(base_asset('driving')['policy']['weights']);gate=base[-91:]
presence=[]
for count in range(4):
 x=np.zeros(91);x[-1]=1.;x[[17,24,31][:count]]=1.
 logit=float(x@gate);g=1/(1+math.exp(-logit))
 presence.append(dict(visibleRivals=count,logit=logit,trafficWeight=g,soloWeight=1-g,gateDerivative=g*(1-g)))
pilots=[]
for name,c in data['models'].items():
 state=c['curriculum'];w=np.array(c['learner']['actor']);p=c['preview'];e=c['episode']
 pilots.append(dict(method=name,gateDeltaFromFactory=float(np.linalg.norm(w[-91:]-gate)),actorSha256=hashlib.sha256(w.tobytes()).hexdigest(),candidateRestarts=state.get('candidateRestarts',0),noGainChecks=state.get('noGainChecks',0),
   preview=dict(phase=p['phase'],seconds=p['age'],passes=p['passes'],contacts=p['contact_count'],reason=p['reason']),
   collection=dict(phase=e['phase'],seconds=e['age'],passes=e['passes'],contacts=e['contact_count'],objective=e['objective']),
   soloSeconds=state['champion'].get('flyingMedian'),raceReferenceSeconds=state.get('raceChampion',{}).get('flyingMedian')))
report=dict(capturedAt=data['capturedAt'],productionChanges=False,presence=presence,pilots=pilots,
 reward=dict(completedPass=.5,ruleViolation=-2.,retirement=-3.,trackExit=-.5,contactAt1mps=-(.2+1.8/12),contactAt5mps=-(.2+1.8*5/12),continuousProgressPerLap=1.,drillProgressPerLap=2.,referenceSeconds=get_track('oval-1').length/9.),
 interpretation='Ratios are not expected returns; discounted futures and critic estimates matter. Gate deltas do not measure causality or convergence.')
(HERE/'mechanisms.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
