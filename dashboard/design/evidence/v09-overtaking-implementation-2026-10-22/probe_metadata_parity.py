"""Physical/reward parity of final diagnostics versus frozen learning source."""
import argparse,hashlib,json,struct
from game_direct_bootstrap import direct_profile,base_asset
from game_direct import snapshot
from game_learning import Policy
from game_academy import Episode
from game_rewards import specification
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
profile={**direct_profile(71,'residual_tactic'),'trafficLearning':'attack-1','relativeAdvantage':0.}
weights=base_asset('traffic')['policy']['weights'];driver_policy=snapshot(profile,weights);rows=[]
for count in (1,2,3):
 e=Episode('oval-1','overtake',975301,protocol='driving-memory-1',objective='impara_sorpasso',bots=count,reward_spec=specification(profile));driver=Policy(driver_policy);digest=hashlib.sha256()
 while not e.reason:
  _,reward,_,_=e.step(driver.act(None,world=e.world,index=0),return_observation=False)
  digest.update(e.world.state.tobytes());digest.update(struct.pack('<dqq',reward,e.passes,int(e.world.track_limits[0])))
 rows.append(dict(bots=count,hash=digest.hexdigest(),passes=e.passes,contacts=e.contact_count,limits=int(e.world.track_limits[0])))
open(a.output,'w').write(json.dumps(rows,indent=2)+'\n');print('parity probe complete',a.output,flush=True)
