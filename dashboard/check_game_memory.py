"""Driving memory: actual inherited actors/genomes, recovery and durable gates."""
import json,tempfile,unittest
import numpy as np
from game_store import GameStore
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_profiles import preset,reference_policy
from game_catalog import configuration
from game_learning import Evolution,PPO,PPOSmooth,Imitation,Policy
from game_driving_memory import PROTOCOL,Review,seed_learner
from game_control import racing_actions
from game_observation_contract import contract


def plain(x):return json.loads(json.dumps(x))
def cls(method):
 if method=='neat':return __import__('game_neat').NEAT
 return dict(evolution=Evolution,ppo=PPO,ppo_smooth=PPOSmooth,imitation=Imitation)[method]


class MemoryChecks(unittest.TestCase):
 def donor(self,s,method):
  identity=s.create_driver('',method);d=s.activate_academy(identity);p=d['profile'];obj=cls(method)(p)
  obj.input_contract=contract();policy=obj.policy();checkpoint=dict(configuration=configuration('oval-1',p['observation']),learner=obj.checkpoint(),steps=123,seconds=7)
  s.save_training(identity,checkpoint,policy,123,7)
  return identity,p,policy

 def test_all_methods_inherit_automatically_and_keep_source_and_local_resume(self):
  for method in ('evolution','neat','ppo','ppo_smooth','imitation'):
   with self.subTest(method=method),tempfile.TemporaryDirectory() as root:
    s=GameStore(root);identity,p,policy=self.donor(s,method);original=s.driver(identity);files={f.name:f.read_bytes() for f in s.policies.glob('*.json')}
    s.select_track('technical-1');s.activate_academy(identity);s.prepare_driving(identity);target=s.driver(identity)
    t=AcademyTrainer(target['profile'],'technical-1',s.load(target['checkpoint']))
    obs=np.random.default_rng(31).normal(size=68)
    inherited=t.learner.candidate_policy() if hasattr(t.learner,'candidate_policy') else t.learner.policy()
    np.testing.assert_allclose(Policy(inherited).act(obs),Policy(policy).act(obs),atol=1e-15)
    self.assertEqual(t.memory['source'],'oval-1');self.assertEqual(t.steps,0);self.assertIsNotNone(t.review)
    self.assertEqual(s.driver(identity,'oval-1'),{**original,'memory':s.driver(identity,'oval-1')['memory']})
    for name,data in files.items():self.assertEqual((s.policies/name).read_bytes(),data)
    saved=t.checkpoint(3);s.save_training(identity,saved,t.learner.policy(),t.steps,3,curriculum=t.state)
    local=s.driver(identity)['checkpoint'];s.prepare_driving(identity);self.assertEqual(s.driver(identity)['checkpoint'],local)
    b=AcademyTrainer(p,'technical-1',plain(saved));self.assertEqual(plain(b.checkpoint(3)),plain(saved))

 def test_evolution_population_has_equal_scenarios_and_replay_is_persistent(self):
  p=academy_profile(preset());c=dict(configuration=configuration('oval-1',p['observation']),protocol=PROTOCOL,memory={'coverage':[dict(track='technical-1',phase='launch')]})
  t=AcademyTrainer(p,'oval-1',c);self.assertEqual(len({e.seed for e in t.episodes}),1)
  t.state.update(phase='control',updates=4);t.reset_episodes()
  self.assertEqual({e.track_id for e in t.episodes},{'technical-1'})
  t.view='attempts';rows,_,meta=t.frame('Evo',1,0);self.assertEqual(meta['phase'],'ripasso');self.assertEqual(len(rows),32)
  saved=plain(t.checkpoint(2));restored=AcademyTrainer(p,'oval-1',saved)
  self.assertEqual(plain(restored.checkpoint(2)),saved)
  restored.view='attempts'
  self.assertEqual([{k:v for k,v in r.items() if k not in ('simRate','resetKey')} for r in restored.frame('Evo',1,0)[0]],[{k:v for k,v in r.items() if k not in ('simRate','resetKey')} for r in rows])

 def test_gradient_replay_generates_current_on_policy_transitions(self):
  for method in ('ppo','imitation'):
   p=academy_profile(preset(1,method));t=AcademyTrainer(p,'oval-1',dict(configuration=configuration('oval-1',p['observation']),protocol=PROTOCOL,memory={'coverage':[dict(track='technical-1',phase='launch')]}))
   t.state['phase']='control';t.reset_episodes()
   self.assertEqual(sum(e.track_id=='technical-1' for e in t.episodes),6)
   for _ in range(63):t.tick()
   if method=='ppo':self.assertEqual(len(t.learner.buffer),1)
   self.assertGreater(t.steps,0)

 def test_recovery_teacher_returns_without_false_clean_lap_qualification(self):
  for track in ('oval-1','technical-1','mallory-oval-1','varano-short-1'):
   for seed in (1,2):
    with self.subTest(track=track,seed=seed):
     e=Episode(track,'recovery',seed,protocol=PROTOCOL)
     self.assertTrue(e.world.was_offroad[0])
     while not e.reason:e.step(racing_actions(e.world,[0])[0])
     self.assertEqual(e.reason,'success',e.result());self.assertGreaterEqual(e.safe_seconds,2)
     self.assertEqual(e.world.track_limits[0],1);self.assertIsNotNone(e.reentry_time)
     self.assertAlmostEqual(e.return_total,sum(e.term_totals.values()),places=9)

 def test_offroad_backward_progress_and_repeated_ground_do_not_pay(self):
  e=Episode('oval-1','control',3,protocol=PROTOCOL);w=e.world
  w.state[0,:7]=[0,-37,np.pi,4,0,0,0];w.was_offroad[0]=True;w.previous_phase=w.coordinates()[2].copy()
  e.step([0,0]);self.assertLess(e.term_totals['progress'],0)
  self.assertEqual(e.valid_progress,0)
  e=Episode('oval-1','control',3,protocol=PROTOCOL);w=e.world
  e.progress_frontier=50.;w.state[0,3]=4
  e.step([0,0]);self.assertEqual(e.term_totals['progress'],0)
  self.assertEqual(e.valid_progress,0)

 def test_review_is_paired_durable_and_never_invents_passes(self):
  policy=reference_policy('oval-1',academy=True);a=Review(policy,policy,[dict(track='oval-1',phase='launch')],2)
  for _ in range(41):a.tick()
  saved=plain(a.snapshot());b=Review(policy,policy,a.contexts,2,saved=saved)
  for _ in range(79):a.tick();b.tick()
  self.assertEqual(plain(a.snapshot()),plain(b.snapshot()))
  for e in a.episodes[:3]:e.reason='contact'
  self.assertTrue(a.tick());self.assertFalse(a.result()['passed'])
  self.assertEqual(a.result()['coverage'][0]['result']['valid'],0)

 def test_local_reset_keeps_base_and_whole_reset_blocks_historical_bootstrap(self):
  with tempfile.TemporaryDirectory() as root:
   s=GameStore(root);identity,p,policy=self.donor(s,'evolution')
   s.select_track('technical-1');s.prepare_driving(identity);base=s.memory_record(identity)
   s.reset_driver(identity);self.assertEqual(s.memory_record(identity),base)
   s.prepare_driving(identity);self.assertTrue(s.load(s.driver(identity)['checkpoint'])['memory']['baseHash'])
   s.reset_all(identity);self.assertIsNone(s.memory_record(identity)['base']);self.assertTrue(s.memory_record(identity)['reset'])
   s.prepare_driving(identity);self.assertFalse(s.load(s.driver(identity)['checkpoint'])['memory'].get('baseHash'))
   self.assertIsNone(s.driver(identity,'oval-1')['policy'])

 def test_real_paired_promotion_is_atomic_idempotent_and_does_not_qualify_racing(self):
  with tempfile.TemporaryDirectory() as root:
   # The current default roster starts with Maestro, not an evolutionary actor.
   s=GameStore(root);identity=s.create_driver('Fixture memoria','evolution');d=s.activate_academy(identity);s.prepare_driving(identity)
   t=AcademyTrainer(d['profile'],'oval-1',s.load(s.driver(identity)['checkpoint']))
   # Analytic straight-driving neural fixture, no teacher overrides its actions.
   t.learner.input_contract=contract();t.learner.best[:]=0;t.learner.best[-1]=2
   policy=t.learner.policy();t.review=Review(policy,None,[dict(track='oval-1',phase='launch')],0)
   while t.review:t.tick()
   self.assertEqual(t.memory['status'],'provisional')
   saved=t.checkpoint(1);s.save_training(identity,saved,policy,0,1,curriculum=t.state)
   base=s.memory_record(identity);self.assertEqual(base['base']['revision'],1);self.assertEqual(base['base']['status'],'provisional')
   self.assertEqual(base['base']['coverage'][0]['result']['valid'],20)
   s.save_training(identity,saved,policy,0,1,curriculum=t.state)
   self.assertEqual(s.memory_record(identity),base)
   from game_catalog import race_eligible
   self.assertFalse(race_eligible(s.driver(identity),'oval-1'))
   s.select_track('technical-1');s.prepare_driving(identity)
   inherited=s.load(s.driver(identity)['checkpoint']);self.assertEqual(inherited['memory']['baseHash'],base['base']['policyHash'])

 def test_neat_inherited_genomes_can_reproduce_without_innovation_collisions(self):
  p=academy_profile(preset(5,'neat'));a=cls('neat')(p)
  for _ in range(3):a.update(np.arange(32))
  seeded=cls('neat')(p,seed_learner(p,a.policy(),a.checkpoint()))
  for _ in range(3):seeded.update(np.arange(32))
  for g in seeded.population.population.values():
   self.assertEqual(len({c.innovation for c in g.connections.values()}),len(g.connections))
  saved=plain(seeded.checkpoint());restored=cls('neat')(p,saved)
  self.assertEqual(plain(restored.checkpoint()),saved)

 def test_vehicle_and_surface_contexts_keep_independent_checkpoints(self):
  from unittest.mock import patch
  from game_catalog import ConditionProfile
  with tempfile.TemporaryDirectory() as root:
   s=GameStore(root);identity,p,policy=self.donor(s,'evolution');s.prepare_driving(identity)
   original=s.driver(identity)['checkpoint'];original_config=s.load(original)['configuration']
   with patch('game_catalog.CONDITION',ConditionProfile(id='test-wet',grip_factor=.6)):
    s.prepare_driving(identity);wet=s.driver(identity)['checkpoint'];self.assertNotEqual(wet,original)
    c=s.load(wet);self.assertEqual(c['configuration']['condition']['id'],'test-wet')
    t=AcademyTrainer(p,'oval-1',c);self.assertEqual(t.episodes[0].world.condition.grip_factor,.6)
    s.save_training(identity,t.checkpoint(2),t.learner.policy(),t.steps,2,curriculum=t.state)
    wet=s.driver(identity)['checkpoint']
   s.prepare_driving(identity);self.assertEqual(s.driver(identity)['checkpoint'],original)
   self.assertEqual(s.load(original)['configuration'],original_config)
   with patch('game_catalog.CONDITION',ConditionProfile(id='test-wet',grip_factor=.6)):
    s.prepare_driving(identity);self.assertEqual(s.driver(identity)['checkpoint'],wet)

 def test_curriculum_only_requires_previously_acquired_skills(self):
  from game_academy import SkillEvaluation
  p=reference_policy('oval-1',academy=True)
  for phase,expected in (('launch',['launch']),('control',['control','launch']),('recovery',['recovery','launch','control'])):
   e=SkillEvaluation(p,None,phase,'oval-1',1,protocol=PROTOCOL)
   self.assertEqual(e.skills,expected)
   self.assertEqual(len(e.scenarios),20)

 def test_ppo_runtime_diagnostics_and_pending_resume(self):
  p=academy_profile(preset(1,'ppo'));a=PPO(p);a.configure_runtime({'batchSize':128});rng=np.random.default_rng(5)
  for _ in range(12):
   obs=rng.normal(size=(32,68));_,raw,logp,value=a.sample(obs)
   a.remember(obs,raw,logp,value,rng.normal(size=32),np.zeros(32,dtype=bool),obs,np.zeros(32,dtype=bool))
  iterator=a.updates();metric=next(iterator);self.assertIn('approxKL',metric);self.assertIn('explainedVariance',metric)
  saved=plain(a.checkpoint());b=PPO(p,saved)
  for x,y in zip(iterator,b.updates(),strict=True):self.assertEqual(x,y)
  self.assertEqual(plain(a.checkpoint()),plain(b.checkpoint()))


if __name__=='__main__':unittest.main()
