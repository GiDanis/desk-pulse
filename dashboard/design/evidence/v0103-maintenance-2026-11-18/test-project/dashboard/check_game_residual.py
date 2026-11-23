"""Residual contract, gradients, exact resume, physical scale and clean roster."""
import json
import tempfile
import unittest
from copy import deepcopy
import numpy as np
from game_residual import profile,snapshot,initial_weights,features,controls,RacingPolicy
from game_residual_learning import ResidualPPO,OffPolicy,critic_gradient,sac_actor_gradient
from game_learning import Policy,forward,random_weights
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION,configuration,visual_content


class ResidualTests(unittest.TestCase):
    def world(self,count=1):
        w=World(count,17,shared=count>1,laps=3,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True)
        w.reset(varied=False);return w

    def test_scale_and_drawing(self):
        w=self.world();self.assertEqual(w.track.width,12)
        self.assertEqual(w.vehicle.width,1.8)
        np.testing.assert_equal(w.track.bounds,[[-73,-37],[73,37]])
        self.assertEqual(visual_content('oval-1')[1]['roadWidth'],12)
        self.assertEqual(configuration()['track']['revision'],2)

    def test_zero_residual_is_real_base(self):
        from game_control import racing_actions
        a,b=self.world(),self.world();p=Policy(snapshot(profile(2,'residual_ppo'),initial_weights(profile(2,'residual_ppo'))))
        for _ in range(240):
            ua=racing_actions(a);ub=p.act(None,world=b)
            np.testing.assert_array_equal(ua,ub)
            a.step(ua,return_observations=False);b.step(ub,return_observations=False)
        np.testing.assert_array_equal(a.state,b.state)

    def test_residual_can_choose_both_legal_sides(self):
        for fraction in (-1.,1.):
            w=self.world();w.racing_base_lane=np.full(w.count,3.6);w.racing_lane[:]=3.6
            controls(w,[[fraction,0.]])
            self.assertGreater(fraction*(w.racing_lane[0]-3.6),0)
        bad=snapshot(profile(2,'residual_ppo'),initial_weights(profile(2,'residual_ppo')))
        bad['action']='line-pace-residual-v1'
        with self.assertRaises(ValueError):RacingPolicy(bad)

    def test_race_finishes_at_lap_target_even_if_record_is_invalid(self):
        from game_control import racing_actions
        w=self.world();w.laps=1;w.race_lap_target=True;w.lap_contacted[0]=True
        for _ in range(4000):
            w.step(racing_actions(w),return_observations=False)
            if not w.active.any():break
        self.assertEqual(w.lap_count[0],1);self.assertEqual(w.clean_laps[0],0)
        self.assertTrue(np.isfinite(w.finish[0]));self.assertFalse(w.retired[0])
        v=World(1,17,laps=1,track_id='oval-1',physics=RACE_PHYSICS_VERSION,telemetry=True)
        v.restore(json.loads(json.dumps(w.snapshot())));self.assertTrue(v.race_lap_target)

    def test_verified_residual_progress_and_dossier_after_evaluation(self):
        from types import SimpleNamespace
        from game import GameService
        from game_catalog import scope_hash,qualified
        from game_store import GameStore
        from game_residual_trainer import ResidualTrainer
        from game_dossier import dossier
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);driver=store.drivers()[1];t=ResidualTrainer(driver['profile'],'oval-1')
            policy=t.learner.policy();t.state['champion'].update(policy=policy,proof=dict(accepted=True,scope=scope_hash('oval-1',driver['profile']['observation']),policyHash=store.artifact(policy),candidate=dict(valid=3,total=3,median=35.,results=[]),champion=dict(valid=3,total=3,median=36.)))
            proof=t.state['champion']['proof'];proof.update(phase='pace',round=1)
            # This fixture certifies the stable race version explicitly; a solo
            # best alone no longer changes the policy selected for qualifying.
            if t.state.get('raceChampion') is not None:t.state['raceChampion']=deepcopy(t.state['champion'])
            t.state['evaluations']=[proof]
            store.save_training(driver['id'],t.checkpoint(0),policy,0,0,t.metric,t.state)
            driver=store.driver(driver['id']);self.assertTrue(qualified(driver,'oval-1'))
            progress=GameService._progress(SimpleNamespace(_track='oval-1'),driver)
            self.assertEqual(progress['evaluations'][0]['best'],35.)
            self.assertTrue(progress['verified']);self.assertTrue(dossier(store,driver['id'])['summary'])

    def test_features_are_query_only_and_roles_explicit(self):
        w=self.world(5);before=w.racing_lane.copy();x=features(w)
        self.assertEqual(x.shape,(90,));self.assertTrue(np.isfinite(x).all())
        np.testing.assert_equal(w.racing_lane,before)
        self.assertEqual(x[84],0)  # no alongside car in the staggered grid

    def test_policy_world_json_resume(self):
        w=self.world();p=Policy(snapshot(profile(2,'residual_ppo'),initial_weights(profile(2,'residual_ppo'))))
        for _ in range(37):w.step(p.act(None,world=w),return_observations=False)
        v=self.world();v.restore(json.loads(json.dumps(w.snapshot())))
        for _ in range(50):
            w.step(p.act(None,world=w),return_observations=False);v.step(p.act(None,world=v),return_observations=False)
        np.testing.assert_array_equal(w.state,v.state)

    def test_offpolicy_resume_and_real_updates(self):
        for method in ('residual_sac','residual_td3'):
            a=OffPolicy(profile(3,method));rng=np.random.default_rng(8);before=a.actor.copy()
            for i in range(140):
                x=rng.normal(size=90);u=a.sample(x)[0];a.remember(x,u,float(x[0]),x*.9,False);a.update()
            b=OffPolicy(profile(3,method),json.loads(json.dumps(a.checkpoint())))
            self.assertGreater(np.linalg.norm(before-a.actor),0)
            for i in range(8):
                x=rng.normal(size=90);ua=a.sample(x)[0];ub=b.sample(x)[0]
                np.testing.assert_array_equal(ua,ub)
                a.remember(x,ua,1.,x*.9,False);b.remember(x,ub,1.,x*.9,False);a.update();b.update()
            np.testing.assert_array_equal(a.actor,b.actor)
            np.testing.assert_array_equal(a.q1,b.q1)

    def test_trainer_json_resume(self):
        from game_residual_trainer import ResidualTrainer
        a=ResidualTrainer(profile(2,'residual_ppo'),'oval-1')
        for _ in range(2150):a.tick()
        b=ResidualTrainer(profile(2,'residual_ppo'),'oval-1',json.loads(json.dumps(a.checkpoint(2.))))
        for _ in range(500):a.tick();b.tick()
        np.testing.assert_array_equal(a.learner.actor,b.learner.actor)
        np.testing.assert_array_equal(a.episode.world.state,b.episode.world.state)
        self.assertEqual(a.decisions,b.decisions)
        bad=a.checkpoint(0);bad['curriculum']['effectiveParameters']['action']='old-action'
        with self.assertRaises(ValueError):ResidualTrainer(profile(2,'residual_ppo'),'oval-1',bad)

    def test_actual_progress_reaches_the_learning_reward(self):
        from game_residual_trainer import ResidualTrainer
        t=ResidualTrainer(profile(2,'residual_ppo'),'oval-1')
        for _ in range(200):t.tick()
        self.assertGreater(t.episode.valid_progress,2)
        self.assertGreater(t.episode.term_totals['progress'],0)
        self.assertAlmostEqual(t.episode.term_totals['progress'],t.episode.valid_progress/t.episode.world.track.length,places=10)

    def test_visible_candidate_is_frozen_until_finish_and_resumes_exactly(self):
        from unittest.mock import patch
        from game_residual_trainer import ResidualTrainer
        from game_residual import key
        t=ResidualTrainer(profile(2,'residual_ppo'),'oval-1')
        initial=t.preview_policy.racing.key
        t.learner.actor[-1]=.1;t.learner.update_index=7
        candidate=key(t.learner.policy())
        self.assertNotEqual(initial,candidate)
        rng=json.dumps(t.learner.rng.bit_generator.state,sort_keys=True)
        clock=t.last_preview
        def advance():
            nonlocal clock
            clock+=.05
            with patch('game_residual_trainer.time.monotonic',return_value=clock):t.advance_preview()
        for _ in range(200):advance()
        self.assertEqual(t.preview_policy.racing.key,initial)
        resumed=ResidualTrainer(t.profile,'oval-1',json.loads(json.dumps(t.checkpoint(0))))
        self.assertEqual(resumed.preview_policy.racing.key,initial)
        self.assertEqual(resumed.preview_trial,t.preview_trial)
        np.testing.assert_array_equal(resumed.preview.world.state,t.preview.world.state)
        for _ in range(1000):
            advance()
            if t.preview_trial>1:break
        self.assertEqual(t.preview_trial,2);self.assertEqual(t.preview_update,7)
        self.assertEqual(t.preview_policy.racing.key,candidate)
        timing=t.preview.world.timing
        self.assertEqual(timing.row(0)['last']['policy'],initial)
        self.assertEqual(timing.row(0)['policy'],candidate)
        self.assertTrue(timing.row(0)['currentValid'])
        self.assertFalse(timing.pending)
        self.assertEqual(json.dumps(t.learner.rng.bit_generator.state,sort_keys=True),rng)
        self.assertEqual(t.steps,0)  # Visible tests are not fabricated training data.
        for _ in range(900):
            advance()
            if t.preview_trial>2:break
        self.assertEqual(t.preview_trial,3)
        self.assertEqual(timing.row(0)['last']['policy'],candidate)
        self.assertTrue(timing.row(0)['last']['clean'])
        self.assertIsNotNone(timing.row(0)['personal'])

    def test_legacy_preview_upgrade_keeps_learning_and_exposes_real_counters(self):
        from game_residual_trainer import ResidualTrainer
        from game_residual import key
        t=ResidualTrainer(profile(2,'residual_ppo'),'oval-1')
        for _ in range(1000):t.tick()
        checkpoint=t.checkpoint(0)
        for field in ('previewPolicy','previewTrial','previewUpdate'):checkpoint.pop(field)
        restored=ResidualTrainer(t.profile,'oval-1',checkpoint)
        np.testing.assert_array_equal(restored.learner.actor,t.learner.actor)
        np.testing.assert_array_equal(restored.episode.world.state,t.episode.world.state)
        self.assertEqual(restored.preview_policy.racing.key,key(t.learner.policy()))
        _,_,meta=restored.frame('Crono',2,0)
        self.assertEqual(meta['residual']['updates'],t.learner.update_index)
        self.assertEqual(meta['residual']['episodes'],t.state['stats']['episodes'])
        self.assertEqual(meta['residual']['previewRole'],'candidate')
        self.assertEqual(meta['residual']['championHash'],key(t.state['champion']['policy']))

    def test_clean_roster_and_stable_qualification(self):
        from game_store import GameStore
        from game_residual_trainer import ResidualTrainer
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);rows=store.drivers()
            self.assertEqual([r['name'] for r in rows],['Maestro','Crono','Memoria','Linea','Tattico'])
            p=rows[1];t=ResidualTrainer(p['profile'],'oval-1')
            t.learner.actor[-1]=1.  # exploring candidate must not be used by Qualifica
            store.save_training(p['id'],t.checkpoint(0),t.learner.policy(),0,0,t.metric,t.state)
            chosen,_=store.qualification_candidate(p['id'])
            self.assertEqual(chosen,store.artifact(t.state['champion']['policy']))
            self.assertNotEqual(chosen,store.artifact(t.learner.policy()))
            store.reset_roster();self.assertEqual(len(store.drivers()),5)

    def test_atomic_migration_and_external_rollback(self):
        from pathlib import Path
        from game_store import GameStore
        from game_residual_migration import prepare,install,inventory,exchange
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'game';store=GameStore(root)
            with store.connect() as db:db.execute("UPDATE drivers SET name='Old Evo' WHERE number=1")
            before=inventory(root);stage=prepare(root);backup=Path(tmp)/'backup'/'old'
            result=install(root,stage,backup)
            self.assertTrue(result['originalHashesPreserved']);self.assertEqual(inventory(backup),before)
            self.assertEqual(GameStore(root).drivers()[0]['name'],'Maestro')
            exchange(root,backup)
            self.assertEqual(GameStore(root).drivers()[0]['name'],'Old Evo')

    def test_td3_actor_is_delayed_and_targets_are_polyak(self):
        a=OffPolicy(profile(3,'residual_td3'));rng=np.random.default_rng(4)
        for i in range(128):
            x=rng.normal(size=90);a.remember(x,[.1,.2],.1,x*.9,False)
        original=a.actor.copy();target=a.target1.copy()
        a.update();self.assertEqual(a.update_index,1)
        np.testing.assert_array_equal(original,a.actor);np.testing.assert_array_equal(target,a.target1)
        for i in range(4):
            x=rng.normal(size=90);a.remember(x,[.1,.2],.1,x*.9,False)
        a.update();self.assertEqual(a.update_index,2)
        self.assertGreater(np.linalg.norm(original-a.actor),0)
        np.testing.assert_allclose(a.target1,target+(a.q1-target)*a.spec['tau'],atol=1e-15)

    def test_tactic_curriculum_consolidates_solo_before_mixed_tasks(self):
        from game_residual_trainer import ResidualTrainer
        t=ResidualTrainer(profile(2,'residual_tactic'),'oval-1')
        t.state['stats']['episodes']=1;t.decisions=8191
        self.assertEqual(t.new_episode().phase,'pace')
        t.decisions=8192;self.assertEqual(t.new_episode().phase,'defend')
        u=ResidualTrainer(profile(2,'residual_tactic'),'oval-1',objective='impara_sorpasso')
        self.assertNotEqual(u.episode.phase,'pace')

    def test_mode_change_preserves_learner_not_old_episode(self):
        from game_residual_trainer import ResidualTrainer
        a=ResidualTrainer(profile(2,'residual_ppo'),'oval-1')
        for _ in range(100):a.tick()
        b=ResidualTrainer(profile(2,'residual_ppo'),'oval-1',a.checkpoint(1),objective='impara_sorpasso')
        np.testing.assert_array_equal(a.learner.actor,b.learner.actor)
        self.assertEqual(b.episode.objective,'impara_sorpasso')
        self.assertGreater(b.preview.world.count,1)
        self.assertEqual(len(b.learner.buffer),0)

    def test_race_sensor_budget_keeps_exact_controls(self):
        from game_control import frozen_actions
        a,b=self.world(5),self.world(5)
        pilots=[Policy(snapshot(profile(i,'residual_ppo'),initial_weights(profile(i,'residual_ppo')))) for i in range(1,6)]
        for _ in range(240):
            observed=a.observations(version='race-68-v3')
            ordinary=np.array([p.act(observed[i],world=a,index=i) for i,p in enumerate(pilots)])
            batched=frozen_actions(b,pilots)
            np.testing.assert_array_equal(ordinary,batched)
            a.step(ordinary,return_observations=False);b.step(batched,return_observations=False)
        np.testing.assert_array_equal(a.state,b.state)


class ReferenceGradientTests(unittest.TestCase):
    def test_against_torch_autograd(self):
        try:import torch
        except ImportError:self.skipTest('Torch reference is a PC-only test dependency')
        torch.set_num_threads(1);rng=np.random.default_rng(9);h=8;n=5;batch=7
        actor=random_weights(rng,h,inputs=n);q1=random_weights(rng,h,1,inputs=n+2);q2=random_weights(rng,h,1,inputs=n+2)
        obs=rng.normal(size=(batch,n));eps=rng.normal(size=(batch,2));std=np.array([-2.,-1.8]);alpha=.02
        def fw(w,x,outputs=2):
            split=(x.shape[1]+1)*h;a=w[:split].reshape(x.shape[1]+1,h);b=w[split:].reshape(h+1,outputs)
            hidden=torch.tanh(torch.cat((x,torch.ones((len(x),1),dtype=x.dtype)),1)@a)
            return torch.cat((hidden,torch.ones((len(x),1),dtype=x.dtype)),1)@b
        tensors=[torch.tensor(v,dtype=torch.float64,requires_grad=True) for v in (actor,std,q1,q2)]
        a,s,c1,c2=tensors;x=torch.tensor(obs,dtype=torch.float64);e=torch.tensor(eps,dtype=torch.float64)
        raw=fw(a,x)+e*torch.exp(s);u=torch.tanh(raw)
        logp=(-.5*(e**2+np.log(2*np.pi))-s-torch.log(1-u**2+1e-8)).sum(1)
        loss=(alpha*logp-torch.minimum(fw(c1,torch.cat((x,u),1),1),fw(c2,torch.cat((x,u),1),1))[:,0]).mean();loss.backward()
        _,ga,gs=sac_actor_gradient(actor,std,q1,q2,obs,eps,h,alpha)
        np.testing.assert_allclose(ga,a.grad.numpy(),rtol=2e-6,atol=2e-8)
        np.testing.assert_allclose(gs,s.grad.numpy(),rtol=2e-6,atol=2e-8)
        inputs=np.c_[obs,np.tanh(eps)];targets=rng.normal(size=batch)
        c=torch.tensor(q1,dtype=torch.float64,requires_grad=True)
        value=fw(c,torch.tensor(inputs,dtype=torch.float64),1)[:,0]
        ((value-torch.tensor(targets))**2).mean().backward()
        _,gq=critic_gradient(q1,inputs,targets,h)
        np.testing.assert_allclose(gq,c.grad.numpy(),rtol=1e-10,atol=1e-10)


if __name__=='__main__':unittest.main()
