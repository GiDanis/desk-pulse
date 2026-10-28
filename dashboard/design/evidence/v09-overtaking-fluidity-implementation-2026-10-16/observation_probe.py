import sys,time,json,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.source))
from game_academy import Episode
from game_residual import profile,snapshot,initial_weights
from game_rewards import specification
from game_learning import Policy
import numpy as np
runs=[];states=[]
for observation in (True,False,False,True):
 p=profile(21,'residual_tactic');e=Episode('oval-1','corner',95201,protocol='driving-memory-1',reward_spec=specification(p))
 controller=Policy(snapshot(p,initial_weights(p)));start=time.monotonic()
 for _ in range(1000):e.step(controller.act(None,world=e.world,index=0),return_observation=observation)
 runs.append(dict(returnObservation=observation,seconds=time.monotonic()-start,reward=e.return_total));states.append(e.world.state.copy())
for state in states[1:]:np.testing.assert_array_equal(states[0],state)
a.output.write_text(json.dumps(dict(runs=runs,exactPhysicalParity=True,ticks=1000),indent=2)+'\n');print(json.dumps(runs))
