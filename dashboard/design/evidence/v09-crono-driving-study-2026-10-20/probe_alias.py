"""Synthetic observation alias on a symmetric finite-lap solo task."""
import json,math
from pathlib import Path
import numpy as np
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_residual import features

worlds=[]
for s in (10.,10.+(144+2*math.pi*31)/2):
    w=World(1,71,laps=1,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True)
    w.reset(varied=False);w.native_sensors=True
    w.state[0,:3]=w.track.pose(s,0);w.state[0,3:]=0;w.state[0,3]=10
    w.progress[0]=s;w.previous_phase[0]=w.coordinates()[2][0];w.progress_origin[0]=w.previous_phase[0]-s
    worlds.append(w)
a,b=map(features,worlds);m=float(np.max(np.abs(a-b)))
out=dict(scope='Synthetic symmetry diagnostic, two solo states rotated by pi on the same finite-lap oval',
    progressMeters=[float(w.progress[0]) for w in worlds],remainingMeters=[float(w.track.length-w.progress[0]) for w in worlds],
    maximumFeatureDifference=m,indistinguishableAt1eMinus12=bool(m<1e-12),featureCount=len(a),
    note='No training or reward change; current actor/critic share these inputs. Remaining episode distance is not encoded.')
Path(__file__).with_name('finite-horizon-alias.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
