"""Read-only audit with isolated deterministic physical and archive fixtures."""
import json,math,sys,tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from game_simulation import World,DT
from game_catalog import RACE_PHYSICS_VERSION
from game_academy import academy_profile,Episode
from game_academy_trainer import AcademyTrainer
from game_profiles import preset
from game_learning import Evolution
from game_store import GameStore
report={'scope':'Isolated controlled fixtures, not a learning-quality benchmark','surfaceComparisons':[]}
for label,action,ticks in [('accelerate',[0.,1.],30),('brake',[0.,-1.],30),('steer',[.25,0.],12)]:
 pair=[]
 for outside in (False,True):
  w=World(physics=RACE_PHYSICS_VERSION);w.state[0,:7]=[0.,-37. if outside else -31.,0.,12.,0.,0.,0.]
  w.was_offroad[0]=outside;w.previous_phase=w.coordinates()[2].copy()
  for _ in range(ticks):w.step([action],return_observations=False)
  pair.append(dict(surface='runoff' if outside else 'asphalt',speed=float(w.state[0,3]),lateral=float(w.state[0,4]),yaw=float(w.state[0,5]),retired=bool(w.retired[0]),terms={k:float(v[0]) for k,v in w.reward_terms.items()}))
 report['surfaceComparisons'].append(dict(command=label,seconds=ticks*DT,results=pair))
w=World(physics=RACE_PHYSICS_VERSION);w.state[0,:7]=[0.,-37.,0.,4.,0.,0.,0.];w.previous_phase=w.coordinates()[2].copy()
w.step([[0.,0.]],return_observations=False);exit_terms={k:float(v[0]) for k,v in w.reward_terms.items()}
w.state[0,1]=-31.;w.previous_phase=w.coordinates()[2].copy();w.step([[0.,0.]],return_observations=False)
report['returnToRoad']=dict(exitTerms=exit_terms,returnTerms={k:float(v[0]) for k,v in w.reward_terms.items()},trackLimits=int(w.track_limits[0]),offroad=bool(w.was_offroad[0]))
report['backwardProgress']=[]
for outside in (False,True):
 w=World(physics=RACE_PHYSICS_VERSION);w.state[0,:7]=[0.,-37. if outside else -31.,math.pi,4.,0.,0.,0.];w.was_offroad[0]=outside;w.previous_phase=w.coordinates()[2].copy()
 w.step([[0.,0.]],return_observations=False)
 report['backwardProgress'].append(dict(offroad=outside,delta=float(w.progress[0]),progressReward=float(w.reward_terms['progress'][0])))
a=AcademyTrainer(academy_profile(preset()),'oval-1')
report['actualBudget']=dict(profileSeconds=a.profile['episodeSeconds'],launchSeconds=a.episodes[0].spec['limitSeconds'],launchGoal=a.launch_goal)
gamma=academy_profile(preset(3,'ppo'))['gamma']
report['ppo']=dict(gamma=gamma,discountSeconds=-DT/math.log(gamma),gaeLambda=.95,gaeTraceSeconds=-DT/math.log(gamma*.95),rolloutSeconds=256*DT,transitions=256*32,minibatchesPerUpdate=256*32//64*4)
report['populationSeeds']=dict(distinct=len({e.seed for e in a.episodes}),offsetSpread=float(np.ptp([e.world.state[0,1] for e in a.episodes])))
with tempfile.TemporaryDirectory() as root:
 s=GameStore(root);d=s.drivers()[0];d=s.activate_academy(d['id']);learner=Evolution(d['profile'])
 # All exported weights have a recognizable compatible donor value.
 learner.best[:]=.123;policy=learner.policy();s.save_training(d['id'],{},policy,10,1)
 s.select_track('technical-1');s.initialize_from(d['id'],'oval-1');target=s.driver(d['id']);s.activate_academy(d['id'])
 checkpoint=s.load(s.driver(d['id'])['checkpoint']) if s.driver(d['id'])['checkpoint'] else None
 trained=AcademyTrainer(target['profile'],'technical-1',checkpoint)
 report['academyTransfer']=dict(targetVersion=target['profile']['version'],initializerRegistered=s.initializer(d['id'])==policy,checkpointCreated=bool(checkpoint),donorApplied=bool(np.array_equal(trained.learner.best,np.asarray(policy['weights']))),sourceIntact=s.driver(d['id'],'oval-1')['steps']==10)
print(json.dumps(report,indent=2))
