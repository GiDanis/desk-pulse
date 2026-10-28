import json,os,sys,time,statistics,platform
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
sys.path.insert(0,sys.argv[1])
from game_simulation import World,reference_actions
from game_geometry import get_track
r={'platform':platform.machine(),'python':platform.python_version(),'numpy':np.__version__,'cases':[]}
for track in ('oval-1','technical-1'):
 for count in (1,4,32):
  w=World(count,track_id=track);times=[];rng=np.random.default_rng(29)
  for i in range(500):
   if i%90==0:w.reset()
   start=time.perf_counter();o=w.observations();w.step(reference_actions(w,o),return_observations=False)
   times.append(time.perf_counter()-start)
  r['cases'].append({'track':track,'count':count,'calls':len(times),'medianMs':statistics.median(times)*1000,'p95Ms':sorted(times)[474]*1000})
r['scope']='Observations plus diagnostic policy and physical decision at 60 Hz with adaptive substeps; full rays, valid moving poses. No learner, GUI or optical FPS measurement.'
print(json.dumps(r,indent=2))
