from functools import partial
from pathlib import Path
import json
from game_direct_bootstrap import rollout
from game_driving_school import actions
rows=[]
for follow in (False,True):
 for phase in ('grid','race4','overtake','corner','defend'):
  for seed in (958001,958002):
   result,_,_=rollout(None,seed,phase,teacher=True,teacher_fn=partial(actions,lane=0.,apex=3.,utilization=.65,follow=follow));rows.append(dict(follow=follow,**result));print(follow,phase,seed,result['reason'],result['contacts'],result['limits'],flush=True)
Path(__file__).with_name('teacher-traffic-probe.json').write_text(json.dumps(rows,indent=2)+'\n')
