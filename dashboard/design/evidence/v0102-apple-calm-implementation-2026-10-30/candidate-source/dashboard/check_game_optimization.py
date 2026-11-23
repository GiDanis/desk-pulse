"""Numerical and durable boundaries for performance changes."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
import numpy as np
from game_simulation import World,RAY_ANGLES
from game_catalog import PHYSICS_VERSION,RACE_PHYSICS_VERSION,ACADEMY_OBSERVATION_VERSION
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_learning import PPO
from game_profiles import preset

class OptimizationChecks(unittest.TestCase):
 def test_observations_and_physics_match_release_rc9(self):
  source=Path(__file__).parent/'design/evidence/v09-optimization-2026-10-13/before/game_simulation.py'
  if not source.exists():self.skipTest('Original source evidence is a local qualification fixture')
  spec=importlib.util.spec_from_file_location('original_game_simulation',source);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
  rng=np.random.default_rng(481)
  for track in ('oval-1','technical-1','mallory-oval-1','varano-short-1'):
   for physics in (PHYSICS_VERSION,RACE_PHYSICS_VERSION):
    a=old.World(4,21,shared=True,track_id=track,physics=physics);b=World(4,21,shared=True,track_id=track,physics=physics)
    for _ in range(65):
     for version in ('race-32-v1','race-42-v2',ACADEMY_OBSERVATION_VERSION):
      np.testing.assert_array_equal(a.observations(version=version),b.observations(version=version))
     command=rng.uniform(-1,1,(4,2));a.step(command,return_observations=False);b.step(command,return_observations=False)
     previous=a.snapshot();current=b.snapshot()
     # rc.14 added an explicit continuous flag; absence in the rc.9 fixture
     # means False, not a physics discrepancy.
     previous.setdefault('continuous',False)
     # New durable gate/frontier metadata has dedicated migration checks.
     self.assertEqual(previous,{k:current[k] for k in previous})
    saved=a.snapshot();b.restore(saved);np.testing.assert_array_equal(a.observations(version=ACADEMY_OBSERVATION_VERSION),b.observations(version=ACADEMY_OBSERVATION_VERSION))

 def test_cache_tracks_direct_changes_and_does_not_leak_mutable_results(self):
  w=World(2,shared=True,physics=RACE_PHYSICS_VERSION)
  first=w.observations(version=ACADEMY_OBSERVATION_VERSION);first[:]=42
  self.assertFalse((w.observations(version=ACADEMY_OBSERVATION_VERSION)==42).any())
  before=w.observations(version=ACADEMY_OBSERVATION_VERSION)
  for array,index,value in ((w.state,(0,3),13),(w.acceleration,(0,0),2),(w.training_context,(0,1),.4),(w.active,1,False)):
   array[index]=value;after=w.observations(version=ACADEMY_OBSERVATION_VERSION);self.assertFalse(np.array_equal(before,after));before=after
  w.reset();self.assertEqual(w.observations(version=ACADEMY_OBSERVATION_VERSION)[0,5],0)

 def original_learning(self):
  source=Path(__file__).parent/'design/evidence/v09-optimization-2026-10-13/before/game_learning.py'
  if not source.exists():self.skipTest('Original learning source is a local qualification fixture')
  spec=importlib.util.spec_from_file_location('original_game_learning',source);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);return old

 def test_numeric_rollout_matches_old_updates_and_resumes_pending_optimizer(self):
  old=self.original_learning();p=academy_profile(preset(3,'ppo'));a=old.PPO(p);b=PPO(p);rng=np.random.default_rng(71)
  for _ in range(19):
   obs=rng.normal(size=(32,68));aa=a.sample(obs);bb=b.sample(obs)
   for x,y in zip(aa,bb):np.testing.assert_array_equal(x,y)
   _,raw,logp,value=aa;reward=rng.normal(size=32);done=rng.random(32)<.1;terminal=done&(rng.random(32)<.5)
   for learner in (a,b):learner.remember(obs,raw,logp,value,reward,done,obs+.01,terminal)
  self.assertEqual(a.checkpoint(),b.checkpoint())
  ai=a.updates();bi=b.updates()
  for _ in range(5):self.assertEqual(next(ai),next(bi))
  self.assertEqual(a.checkpoint(),b.checkpoint())
  resumed=PPO(p,json.loads(json.dumps(b.checkpoint())));ri=resumed.updates()
  for x,y,z in zip(ai,bi,ri,strict=True):self.assertEqual(x,y);self.assertEqual(x,z)
  self.assertEqual(a.checkpoint(),b.checkpoint());self.assertEqual(b.checkpoint(),resumed.checkpoint())

 def test_clone_numeric_examples_match_original(self):
  from game_learning import Imitation
  old=self.original_learning();p=academy_profile(preset(5,'imitation'));a=old.Imitation(p);b=Imitation(p);rng=np.random.default_rng(90)
  for _ in range(80):
   obs=rng.normal(size=(32,68));target=rng.uniform(-1,1,(32,2));active=rng.random(32)>.05
   a.learn_step(obs,target,active);b.learn_step(obs,target,active)
  self.assertEqual(a.checkpoint(),b.checkpoint())
  resumed=Imitation(p,json.loads(json.dumps(b.checkpoint())))
  self.assertEqual(resumed.checkpoint(),b.checkpoint())

 def test_parallel_collectors_preserve_one_pilots_order_rng_and_resume(self):
  import time
  for method in ('ppo','neat','imitation','evolution'):
   p=academy_profile(preset(3,method));a=AcademyTrainer(p,'oval-1');b=AcademyTrainer(p,'oval-1')
   b.enable_collectors(2)
   try:
    while a.steps<96:a.tick()
    end=time.monotonic()+20
    while b.steps<96:
     b.tick();time.sleep(.001)
     self.assertLess(time.monotonic(),end)
    self.assertIsNone(b.inflight)
    self.assertEqual(a.checkpoint(0),b.checkpoint(0))
    # Pause/serialize with collectors in flight; restore on a serial runtime.
    b.tick();saved=json.loads(json.dumps(b.checkpoint(0)))
    c=AcademyTrainer(p,'oval-1',saved)
    while b.inflight is not None:b.tick()
    while c.inflight is not None:c.tick()
    self.assertEqual(b.checkpoint(0),c.checkpoint(0))
   finally:b.close()

 def test_reference_grid_batch_controls_match_per_car_execution(self):
  from game_control import frozen_actions
  from game_profiles import reference_policy
  from game_learning import Policy
  for track in ('oval-1','technical-1','varano-short-1','mallory-oval-1'):
   for modern in (False,True):
    p=Policy(reference_policy(track,academy=modern));a=World(4,shared=True,track_id=track,physics=RACE_PHYSICS_VERSION if modern else PHYSICS_VERSION);b=World(4,shared=True,track_id=track,physics=a.physics)
    for _ in range(250):
     obs=a.observations(version=p.snapshot['observation'])
     old=np.array([p.act(o,world=a,index=i) for i,o in enumerate(obs)])
     new=frozen_actions(b,[p]*4)
     np.testing.assert_array_equal(old,new)
     a.step(old,return_observations=False);b.step(new,return_observations=False)
    self.assertEqual(a.snapshot(),b.snapshot())

if __name__=='__main__':unittest.main()
