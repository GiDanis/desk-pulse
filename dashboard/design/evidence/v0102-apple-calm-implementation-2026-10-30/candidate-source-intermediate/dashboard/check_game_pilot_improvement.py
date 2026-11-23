"""Driving causes, immutable variants, PPO numerics and hybrid lifecycle."""
from copy import deepcopy
import json
import tempfile
import unittest
import numpy as np
from game_profiles import preset,VARIANTS
from game_academy import academy_profile,Episode
from game_academy_trainer import AcademyTrainer
from game_learning import Policy,ppo_gradient,random_weights,forward,log_probability
from game_hybrid import ClonePPO,HybridGate
from game_store import GameStore,validate_profile
from game_catalog import RACE_PHYSICS_VERSION
from game_simulation import World
from game_curriculum import digest


def trainer(name='clone_ppo',saved=None):
    return AcademyTrainer(academy_profile(preset(41,name)),'oval-1',saved,balanced=True,batched=True)


class PilotImprovementChecks(unittest.TestCase):
    def test_variants_persist_without_mutating_existing_roster(self):
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);original=deepcopy(store.drivers())
            for name in ('clone_ppo',*VARIANTS):
                identity=store.create_driver('',name);p=store.driver(identity)['profile']
                self.assertEqual(validate_profile(p),p)
                self.assertEqual(p,preset(store.driver(identity)['number'],name))
            for old in original:self.assertEqual(store.driver(old['id']),old)
            bad=preset(1);bad['variant']='neat64'
            with self.assertRaises(ValueError):validate_profile(bad)
            self.assertNotEqual(store.path_key(preset(1,'neat')),store.path_key(preset(1,'neat_response')))
            bad=preset(1,'clone_ppo');bad['recipeVersion']=2
            with self.assertRaises(ValueError):validate_profile(bad)

    def test_hybrid_trains_own_actor_then_resumes_without_ppo_rollout(self):
        t=trainer();before=t.learner.actor.copy()
        for _ in range(512):t.tick()
        self.assertGreater(t.learner.hybrid['imitationSteps'],128)
        self.assertFalse(np.array_equal(before,t.learner.actor))
        self.assertEqual(len(t.learner.buffer),0)
        saved=json.loads(json.dumps(t.checkpoint(1)));copy=trainer(saved=saved)
        self.assertEqual(copy.checkpoint(1),saved)
        np.testing.assert_array_equal(t.learner.policy()['weights'],copy.learner.policy()['weights'])
        for _ in range(128):t.tick();copy.tick()
        self.assertEqual(json.loads(json.dumps(t.checkpoint(2))),json.loads(json.dumps(copy.checkpoint(2))))

    def test_transition_preserves_actor_and_requires_correct_frozen_policy(self):
        t=trainer();h=t.learner;old=h.actor.copy()
        failed=dict(passed=False,policyHash=digest(h.policy()))
        self.assertFalse(h.transition(failed));self.assertTrue(h.uses_teacher)
        with self.assertRaises(ValueError):h.transition(dict(passed=True,policyHash='wrong'))
        proof=dict(passed=True,policyHash=digest(h.policy()),launches=20,laps=20,endurance=5)
        self.assertTrue(h.transition(proof));self.assertFalse(h.uses_teacher)
        np.testing.assert_array_equal(old,h.actor)
        self.assertEqual(len(h.buffer),0);self.assertIsNone(h.pending)
        np.testing.assert_allclose(np.exp(h.log_std),.1)
        saved=json.loads(json.dumps(t.checkpoint(1)));copy=trainer(saved=saved)
        self.assertFalse(copy.learner.uses_teacher)
        self.assertEqual(copy.learner.hybrid,h.hybrid)
        for _ in range(64):copy.tick()
        self.assertGreater(len(copy.learner.buffer),0)

    def test_hybrid_gate_pause_preserves_frozen_worlds_and_progress(self):
        gate=HybridGate(trainer().learner.policy(),'oval-1')
        for _ in range(90):gate.tick()
        saved=json.loads(json.dumps(gate.snapshot()))
        copy=HybridGate(saved['policy'],saved['track'],saved)
        for _ in range(90):gate.tick();copy.tick()
        self.assertEqual(gate.snapshot(),copy.snapshot())
        self.assertFalse(gate.result()['passed'])

    def test_continuous_and_overtaking_hybrids_can_enter_readiness_gate(self):
        p=academy_profile(preset(41,'clone_ppo'))
        for objective in ('impara_infinito','impara_sorpasso'):
            t=AcademyTrainer(p,'oval-1',objective=objective,balanced=True,batched=True)
            self.assertIsNone(t.evo_plan);t.state['updates']=8;t.schedule()
            self.assertIsNotNone(t.hybrid_gate)
            saved=json.loads(json.dumps(t.checkpoint(1)))
            resumed=AcademyTrainer(p,'oval-1',saved,objective=objective,balanced=True,batched=True)
            self.assertEqual(saved,resumed.checkpoint(1))

    def test_qualifying_preserves_tested_imitation_actor_during_ppo_exploration(self):
        # Positive gate fixture tests selection, not actual learned competence.
        t=trainer();h=t.learner;archive=h.policy()
        h.transition(dict(passed=True,policyHash=digest(archive),launches=20,laps=20,endurance=5))
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);identity=store.create_driver('Ibrido test','clone_ppo')
            store.set_profile(identity,t.profile,allow_reconfigure=True)
            c=t.checkpoint(1)
            store.save_training(identity,c,h.policy(),t.steps,1,curriculum=c['curriculum'])
            selected,_=store.qualification_candidate(identity)
            self.assertEqual(selected,digest(archive))
            self.assertNotEqual(selected,digest(h.policy()))
            self.assertFalse(store.driver(identity).get('timedQualifications'))

    def test_actual_boundary_and_vehicle_retirement_causes_and_legacy_unknown(self):
        w=World(physics=RACE_PHYSICS_VERSION,telemetry=True)
        w.state[0,:3]=w.track.pose(0,w.track.width/2+8)
        w.step(np.zeros((1,2)),return_observations=False)
        self.assertTrue(w.retired[0]);self.assertEqual(w.retirement_cause[0],1)
        saved=w.snapshot();saved.pop('retirementCause')
        w.restore(saved);self.assertEqual(w.retirement_cause[0],4)
        w=World(2,shared=True,physics=RACE_PHYSICS_VERSION,telemetry=True)
        w.state[0,:3]=w.track.pose(0);w.state[1,:3]=w.track.pose(3)
        w.state[0,3]=25.;w.state[1,3]=0.
        w.step(np.zeros((2,2)),return_observations=False)
        self.assertTrue(w.retired.any());self.assertIn(2,w.retirement_cause)

    def test_neat_response_native_policy_and_resume_match(self):
        from game_learning import Policy
        t=trainer('neat_response');n=t.learner
        self.assertEqual(n.config.genome_config.response_init_mean,.4)
        rows=np.stack([e.observations() for e in t.episodes])
        a=n.act(rows);n.driving_balance=False;b=n.act(rows)
        np.testing.assert_allclose(a,b,atol=1e-12)
        from game_neat import snapshot
        for i,key in enumerate(n.keys):
            np.testing.assert_allclose(a[i],Policy(snapshot(n.population.population[key],n.config)).act(rows[i]),atol=1e-12)
        saved=t.checkpoint(1);copy=trainer('neat_response',saved)
        np.testing.assert_array_equal(b,copy.learner.act(rows))

    def test_effective_configuration_and_multitrack_cases(self):
        for name in ('neat64','neat_response','ppo_cautious','regular','attacker','versatile'):
            t=trainer(name);c=t.checkpoint(1);eff=c['curriculum']['effectiveParameters']
            self.assertEqual(eff['variant'],name)
            if name=='neat64':self.assertEqual(len(t.episodes),64)
            if name=='ppo_cautious':self.assertEqual(eff['ppo']['learningRate'],.0001)
            if name=='regular':self.assertTrue(t.reward_spec['smoothRamp'])
            if name=='attacker':self.assertEqual(t.reward_spec['passReward'],.75)
            if name=='versatile':
                seen=set()
                for level in (5,6,7):
                    t.evo_plan.data['level']=level;t.evo_plan.sync()
                    cases=t.evo_plan.cases();other=cases[-1]
                    seen.add(other['track'])
                    found=False
                    for update in range(len(cases)):
                        t.state['updates']=update;t.reset_episodes()
                        found |= any(e.track_id!=t.track_id for e in t.episodes)
                    self.assertTrue(found)
                self.assertEqual(len(seen),3)

    def test_teacher_pressure_does_not_mix_old_labels_or_reset_network(self):
        t=trainer('imitation');n=t.learner
        for _ in range(512):t.tick()
        old=n.weights.copy();n.set_teacher_pressure(.5)
        self.assertFalse(hasattr(n,'_examples'));self.assertEqual(n.samples,[])
        np.testing.assert_array_equal(old,n.weights)
        self.assertEqual(n.checkpoint()['teacherSpec']['speedFactor'],1.175)

    def test_ppo_actor_critic_and_std_gradients_match_finite_differences(self):
        rng=np.random.default_rng(43);hidden=8;obs=rng.normal(0,.2,(7,32))
        actor=random_weights(rng,hidden,inputs=32);critic=random_weights(rng,hidden,1,inputs=32)
        std=np.array([-.8,-.9]);mean=forward(actor,obs,hidden)
        raw=mean+rng.normal(0,.2,mean.shape);old=log_probability(raw,mean,std)
        advantage=rng.normal(size=7);returns=rng.normal(size=7)
        args=(hidden,obs,raw,old,advantage,returns)
        _,_,ga,gv,gs=ppo_gradient(actor,critic,std,*args)
        for vector,gradient,loss_index in ((actor,ga,0),(critic,gv,1),(std,gs,0)):
            for index in rng.choice(len(vector),min(10,len(vector)),replace=False):
                original=vector[index];eps=1e-6
                vector[index]=original+eps;plus=ppo_gradient(actor,critic,std,*args)[loss_index]
                vector[index]=original-eps;minus=ppo_gradient(actor,critic,std,*args)[loss_index]
                vector[index]=original
                self.assertAlmostEqual(float(gradient[index]),(plus-minus)/(2*eps),places=6)


if __name__=='__main__':unittest.main()
