"""Driving lessons, conditional exploration, migration and truthful promotion."""
from copy import deepcopy
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from game_direct_bootstrap import direct_profile,initial_policy
from game_direct_trainer import DirectPPO,DirectOffPolicy,DirectTrainer
from game_learning import forward,log_probability,Policy
from game_school_lessons import Lesson,SKILLS,make_check

class SchoolTests(unittest.TestCase):
    def test_neural_mixture_all_parameters_have_correct_gradients(self):
        from game_learning import backward,random_weights
        rng=np.random.default_rng(37);w=np.r_[random_weights(rng,64,inputs=90),random_weights(rng,64,inputs=90),rng.normal(0,.1,91)]
        obs=rng.normal(size=(4,90));dy=rng.normal(size=(4,2));y,c=forward(w,obs,128,cache=True);g=backward(c,dy)
        for index in [0,500,5900,5954,11000,11908,11930,11998]:
            delta=np.zeros_like(w);delta[index]=1e-5
            expected=np.sum((forward(w+delta,obs,128)-forward(w-delta,obs,128))*dy)/2e-5
            self.assertAlmostEqual(g[index],expected,places=7)

    def test_unseen_rival_columns_are_neutral_not_random(self):
        from game_direct_bootstrap import fit
        from game_learning import random_weights
        rng=np.random.default_rng(30);w=random_weights(rng,64,inputs=90)
        x=rng.normal(size=(40,90));columns=list(range(18,32))+list(range(58,68));x[:,columns]=0.
        before=np.tanh(forward(w,x,64));fit(w,x,np.zeros((40,2)),rng,0)
        np.testing.assert_array_equal(w[:90*64].reshape(90,64)[columns],0.)
        np.testing.assert_allclose(np.tanh(forward(w,x,64)),before,rtol=0,atol=0)

    def test_block_noise_ppo_likelihood_and_exact_resume(self):
        p=direct_profile(2,'residual_ppo');l=DirectPPO(p);obs=np.zeros((1,94));obs[:,73]=.95
        l.block=dict(left=8,pedal=.6,number=1)
        action,raw,logp,value=l.sample(obs);mean=forward(l.actor,obs[:,:90],p['hidden'])
        np.testing.assert_allclose(action,np.tanh(raw+[0,.6]))
        np.testing.assert_array_equal(logp,log_probability(raw,mean,l.log_std))
        restored=DirectPPO(p,json.loads(json.dumps(l.checkpoint())))
        for _ in range(30):
            a=l.sample(obs);b=restored.sample(obs)
            for x,y in zip(a,b):np.testing.assert_array_equal(x,y)

    def test_offpolicy_block_resume_and_different_axes(self):
        p=direct_profile(3,'residual_sac');a=DirectOffPolicy(p);obs=np.zeros(94);obs[73]=.95
        for _ in range(7):a.sample(obs)
        b=DirectOffPolicy(p,json.loads(json.dumps(a.checkpoint())))
        for _ in range(30):np.testing.assert_array_equal(a.sample(obs),b.sample(obs))
        self.assertGreater(a.spec['explorationBlock']['pedalStd'],a.spec['exploration'][0]*20)

    def test_lesson_snapshot_preserves_measurements(self):
        p=direct_profile(2,'residual_ppo');e=Lesson('oval-1','frenata',951001,p);driver=Policy(initial_policy(p))
        for _ in range(23):e.step(driver.act(None,world=e.world,index=0),return_observation=False)
        s=json.loads(json.dumps(e.snapshot()));b=Lesson('oval-1','frenata',951001,p,saved=s)
        for _ in range(50):
            e.step(driver.act(None,world=e.world,index=0),return_observation=False)
            b.step(driver.act(None,world=b.world,index=0),return_observation=False)
        self.assertEqual(e.lesson,b.lesson);np.testing.assert_array_equal(e.world.state,b.world.state)

    def test_legacy_epoch_archives_source_and_rejects_unknown(self):
        p=direct_profile(2,'residual_ppo');policy=initial_policy(p)
        old=dict(protocol='direct-driving-2',steps=400,decisions=70,seconds=12.,sourceCheckpoint='a'*64,
            learner=dict(actor=policy['weights']),curriculum=dict(effectiveParameters=dict(version='direct-driving-2'),champion=dict(policy=policy),stats=dict(episodes=8),updates=2))
        t=DirectTrainer(p,'oval-1',old)
        self.assertEqual(t.steps,400);self.assertEqual(t.state['recipeArchives'][0]['sourceCheckpoint'],'a'*64)
        self.assertEqual(t.learner.update_index,0);self.assertEqual(t.state['stats']['episodes'],0)
        self.assertEqual(t.state['migration']['version'],'direct-driving-3')
        with self.assertRaises(ValueError):DirectTrainer(p,'oval-1',dict(protocol='direct-driving-future'))

    def test_check_resume_keeps_independent_lesson_gates(self):
        p=direct_profile(2,'residual_ppo');policy=initial_policy(p);c=make_check(policy,policy,'oval-1')
        for _ in range(70):c.tick()
        saved=json.loads(json.dumps(c.snapshot()));d=make_check(policy,policy,'oval-1',saved=saved)
        self.assertEqual(c.cases,d.cases)
        for _ in range(100):c.tick();d.tick()
        self.assertEqual(c.snapshot(),d.snapshot())
        self.assertEqual(len([e for e in c.episodes if isinstance(e,Lesson)]),8)

    def test_store_migration_archives_qualifications_once_and_preserves_totals(self):
        from game_store import GameStore,canonical
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);d=store.drivers()[1];p=d['profile']
            old=dict(protocol='direct-driving-2',steps=400,decisions=70,seconds=12.,
                curriculum=dict(effectiveParameters=dict(version='direct-driving-2'),champion=dict(policy=initial_policy(p)),stats={}))
            t=DirectTrainer(p,'oval-1',old)
            with store.connect() as db:
                db.execute('INSERT INTO timed_qualifications VALUES(?,?,?,?)',(d['id'],'old','old',canonical(dict(track='oval-1',bestLap=25.,policy='fixture')).decode()))
            for index in range(2):
                store.save_training(d['id'],t.checkpoint(12.),t.learner.policy(),400,12.,t.metric,t.state)
                if index==0:
                    with store.connect() as db:
                        self.assertEqual(db.execute('SELECT COUNT(*) FROM timed_qualifications').fetchone()[0],0)
                        db.execute('INSERT INTO timed_qualifications VALUES(?,?,?,?)',(d['id'],'new','new',canonical(dict(track='oval-1',bestLap=25.,policy='fixture')).decode()))
            saved=store.driver(d['id']);self.assertEqual(saved['profile']['hidden'],128)
            self.assertEqual((saved['steps'],saved['seconds']),(400,12.))
            with store.connect() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM history WHERE kind='school_migration'").fetchone()[0],1)
                self.assertEqual(db.execute('SELECT policy FROM timed_qualifications').fetchone()[0],'new')
            for objective in ('impara_infinito','impara_sorpasso'):
                old_state=dict(profile=canonical({**p,'hidden':64}).decode(),policy=None,checkpoint=store.driver(d['id'])['checkpoint'],policy_profile=None,candidate=None,curriculum=None,steps=0,seconds=0.)
                with store.connect() as db:
                    db.execute('INSERT INTO objective_paths VALUES(?,?,?,?)',(d['id'],'oval-1',objective,canonical(old_state).decode()))
                store.select_objective(objective)
                store.save_training(d['id'],t.checkpoint(12.),t.learner.policy(),400,12.,t.metric,t.state)
                self.assertEqual(store.driver(d['id'])['profile']['hidden'],128)
            store.select_objective('impara')

    def test_writer_repeated_replay_ack_and_child_cleanup(self):
        from game_checkpoint_writer import CheckpointWriter
        from game_store import GameStore
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);d=store.drivers()[2];t=DirectTrainer(d['profile'],'oval-1')
            for _ in range(80):t.tick()
            writer=CheckpointWriter(store);private=Path(writer.private.name)
            try:
                for index in range(3):
                    c=t.checkpoint(float(index),deferred=True)
                    self.assertTrue(writer.submit(d['id'],c,t.learner.policy(),t.steps,float(index),t.metric,t.state,None,{}))
                    self.assertEqual(writer.collect(wait=True)['steps'],t.steps)
                    saved=store.load(store.driver(d['id'])['checkpoint'])
                    self.assertEqual(saved['protocol'],'direct-driving-3')
            finally:writer.close()
            self.assertIsNotNone(writer.process.poll());self.assertFalse(private.exists())

    def test_five_car_proof_resume_is_exact_and_has_no_training(self):
        from game_school_lessons import RaceProof
        p=direct_profile(2,'residual_ppo');policy=initial_policy(p)
        a=RaceProof(policy,'oval-1',942002,2)
        for _ in range(45):a.tick()
        b=RaceProof(policy,'oval-1',942002,2,saved=json.loads(json.dumps(a.snapshot())))
        for _ in range(100):a.tick();b.tick()
        np.testing.assert_array_equal(a.world.state,b.world.state);self.assertEqual(a.result(),b.result())
        self.assertEqual(a.policy,policy)

    def test_race_contact_history_counts_each_event_once(self):
        from game_school_lessons import RaceProof
        a=RaceProof(initial_policy(direct_profile(2,'residual_ppo')),'oval-1',942002,2)
        a.world.events=[dict(type='contact',time=0.,cars=[0,1])]
        with patch.object(a.world,'step'):
            a.tick();a.tick()
        self.assertEqual(a.contacts,1)

    def test_teacher_cannot_be_called_by_neural_policy(self):
        p=direct_profile(2,'residual_ppo');driver=Policy(initial_policy(p));e=Lesson('oval-1','accelerazione',951001,p)
        with patch('game_driving_school.actions',side_effect=AssertionError('Teacher in inference')):
            for _ in range(20):e.step(driver.act(None,world=e.world,index=0),return_observation=False)

if __name__=='__main__':unittest.main()
