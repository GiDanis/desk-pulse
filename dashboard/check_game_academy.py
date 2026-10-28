"""Academy gates: provenance, physical recovery, termination and resume."""
import json
import tempfile
import unittest
from copy import deepcopy
import numpy as np

from game_academy import Episode,SkillEvaluation,academy_profile,upgrade_learner,expand_weights
from game_academy_trainer import AcademyTrainer
from game_catalog import ACADEMY_OBSERVATION_VERSION,RACE_PHYSICS_VERSION,RACE_VEHICLE,configuration,scope_hash,qualified,race_eligible
from game_contacts import resolve
from game_control import racing_actions
from game_learning import Evolution,PPO,Imitation,forward,Policy
from game_profiles import preset,reference_policy
from game_simulation import World,vertices,DT
from game_store import GameStore


class AcademyChecks(unittest.TestCase):
    def test_population_frames_show_actual_attempts_without_advancing_training(self):
        for method in ('evolution','neat'):
            t=AcademyTrainer(academy_profile(preset(3,method)),'oval-1',view='attempts')
            t.episodes[9].step([0.,1.])
            t.episodes[2].reason='success'
            before=t.checkpoint(0)
            t.advance_preview()
            rows,obs,meta=t.frame('Pilota',99,41)
            self.assertIsNone(t.preview)
            self.assertEqual(len(rows),32);self.assertEqual(meta['selected'],9)
            self.assertEqual((meta['presentation'],meta['generation'],meta['completedAttempts']),('population',1,1))
            self.assertEqual(len({r['id'] for r in rows}),32)
            self.assertEqual(rows[9]['x'],t.episodes[9].world.state[0,0])
            self.assertTrue(rows[2]['completed']);self.assertIsNone(rows[9]['position'])
            np.testing.assert_array_equal(obs,t.episodes[9].observations())
            self.assertEqual(before,t.checkpoint(0))
            t.learner.update(np.arange(32));t.reset_episodes()
            new,_,meta=t.frame('Pilota',99,-1,paused=True)
            self.assertEqual((meta['generation'],meta['selected'],meta['completedAttempts']),(2,31,0))
            self.assertNotEqual(new[9]['id'],rows[9]['id'])
            saved=json.loads(json.dumps(t.checkpoint(0)))
            restored=AcademyTrainer(t.profile,'oval-1',saved,view='attempts')
            self.assertEqual([{k:v for k,v in r.items() if k not in ('simRate','resetKey')} for r in restored.frame('Pilota',99,-1,True)[0]],[{k:v for k,v in r.items() if k not in ('simRate','resetKey')} for r in new])
            self.assertEqual(json.loads(json.dumps(restored.checkpoint(0))),saved)

    def test_gradient_learners_keep_independent_preview(self):
        for method in ('ppo','ppo_smooth','imitation'):
            t=AcademyTrainer(academy_profile(preset(3,method)),'oval-1')
            before=t.checkpoint(0)
            rows,_,meta=t.frame('Pilota',99,41,paused=True)
            self.assertEqual((len(rows),rows[0]['id'],meta['presentation']),(1,'preview','preview'))
            self.assertEqual(before,t.checkpoint(0))

    def test_population_traffic_shows_only_selected_attempts_frozen_rivals(self):
        t=AcademyTrainer(academy_profile(preset(3)),'oval-1',view='attempts')
        t.state['phase']='overtake';t.reset_episodes()
        before=t.checkpoint(0)
        rows,obs,meta=t.frame('Evo',1,9)
        self.assertEqual((meta['count'],meta['trainingCount'],meta['selected']),(32,32,9))
        self.assertEqual(len(rows),32+t.episodes[9].world.count-1)
        for row,actual in zip(rows[32:],t.episodes[9].world.rows()[1:]):
            self.assertTrue(row['contextRival']);self.assertEqual(row['x'],actual['x'])
        np.testing.assert_array_equal(obs,t.episodes[9].observations())
        self.assertEqual(t.checkpoint(0),before)

    def test_expansion_preserves_original_actor_and_zeroes_new_channels(self):
        p=preset(3,'ppo');old=PPO(p);q=academy_profile(p)
        obs=np.random.default_rng(16).normal(size=(8,42))
        upgraded=upgrade_learner({'learner':old.checkpoint(),'configuration':configuration()},q)
        new=PPO(q,upgraded);extended=np.c_[obs,np.zeros((8,26))]
        np.testing.assert_array_equal(forward(old.actor,obs,16),forward(new.actor,extended,16))
        self.assertAlmostEqual(q['gamma']**(40/DT),np.exp(-1))
        self.assertEqual((q['seed'],q['algorithm'],q['population']),(p['seed'],p['algorithm'],p['population']))

    def test_start_archives_checkpoint_without_rewriting_old_artifacts(self):
        with tempfile.TemporaryDirectory() as root:
            s=GameStore(root);d=s.drivers()[0];l=Evolution(d['profile'])
            checkpoint={'configuration':configuration(),'learner':l.checkpoint(),'steps':111,'seconds':27}
            s.save_training(d['id'],checkpoint,l.policy(),111,27)
            original=s.driver(d['id']);artifacts={p.name:p.read_bytes() for p in s.policies.glob('*.json')}
            new=s.activate_academy(d['id'])
            self.assertEqual(new['policy'],original['policy']);self.assertEqual(new['profile']['version'],2)
            self.assertEqual(s.total_seconds(d['id']),27)
            for name,data in artifacts.items():self.assertEqual((s.policies/name).read_bytes(),data)
            self.assertEqual(s.activate_academy(d['id']),new)
            self.assertFalse(race_eligible(new,'mallory-oval-1'))
            s.set_profile(d['id'],original['profile'],allow_reconfigure=True)
            self.assertEqual(s.driver(d['id']),original)
            from game_dossier import dossier
            self.assertTrue(any(x['title']=='Percorso Accademia' for x in dossier(s,d['id'])['history']))

    def test_archived_race_proof_follows_only_its_original_policy(self):
        with tempfile.TemporaryDirectory() as root:
            s=GameStore(root);s.select_track('varano-short-1');d=s.drivers()[0];l=Evolution(d['profile'])
            s.save_training(d['id'],{'configuration':configuration(s.track_id,d['profile']['observation']),'learner':l.checkpoint()},l.policy(),111,27)
            old=s.driver(d['id']);proof={'champion':{'proof':{'candidateHash':old['policy'],
                'scope':scope_hash('varano-short-1',old['profile']['observation']),
                'candidate':{'valid':9,'laps':3}}}}
            with s.connect() as db:
                db.execute('UPDATE driver_paths SET curriculum=? WHERE id=? AND track_id=?',
                           (json.dumps(proof),d['id'],s.track_id))
            self.assertTrue(qualified(s.driver(d['id']),s.track_id));self.assertFalse(race_eligible(s.driver(d['id']),s.track_id))
            s.activate_academy(d['id'])
            with s.connect() as db:
                db.execute('UPDATE driver_paths SET curriculum=? WHERE id=? AND track_id=?',
                           (json.dumps({'academyVersion':'academy-1','qualifications':{}}),d['id'],s.track_id))
            self.assertTrue(qualified(s.driver(d['id']),s.track_id));self.assertFalse(race_eligible(s.driver(d['id']),s.track_id))
            with s.connect() as db:
                db.execute('UPDATE driver_paths SET policy=? WHERE id=? AND track_id=?',
                           (s.artifact({'different':True}),d['id'],s.track_id))
            self.assertFalse(race_eligible(s.driver(d['id']),s.track_id))

    def test_idle_is_terminal_once_and_has_reward_breakdown(self):
        e=Episode('oval-1','launch',1)
        while not e.reason:e.step([0.,-1.])
        self.assertEqual(e.reason,'no_progress');self.assertTrue(e.terminated);self.assertFalse(e.truncated)
        self.assertLess(e.age,8);self.assertEqual(e.term_totals['stall'],-.5)
        self.assertAlmostEqual(sum(e.term_totals.values()),e.return_total,places=9)
        before=deepcopy(e.snapshot());self.assertEqual(e.step([0.,1.])[1],0);self.assertEqual(e.snapshot(),before)

    def test_blocked_traffic_is_truncation_and_legitimate_braking_recovers(self):
        e=Episode('oval-1','follow',1)
        e.world.state[1,:3]=e.world.track.pose(6);e.world.state[:,3:6]=0;e.world.progress[1]=6
        e.world.previous_phase=e.world.coordinates()[2].copy()
        e.opponent_actions=lambda:[[0.,-1.]]
        while not e.reason:e.step([0.,-1.])
        self.assertEqual(e.reason,'blocked');self.assertTrue(e.truncated);self.assertFalse(e.terminated)
        e=Episode('oval-1','launch',2)
        for _ in range(120):e.step([0.,-1.])
        self.assertFalse(e.reason)
        while not e.reason:e.step(racing_actions(e.world,[0])[0])
        self.assertEqual(e.reason,'success')

    def test_body_sensors_and_serialized_physics_are_consistent(self):
        w=World(4,shared=True,physics=RACE_PHYSICS_VERSION)
        self.assertEqual(w.progress.tolist(),[0.,-6.,-12.,-18.])
        w.state[0,2]=.3;w.state[1,3]=8
        obs=w.observations(version=ACADEMY_OBSERVATION_VERSION)
        self.assertEqual(obs.shape,(4,68));self.assertTrue(np.isfinite(obs).all())
        self.assertLess(min(obs[0,46:48]),.41);self.assertGreater(obs[0,17],0)
        w.step(racing_actions(w),return_observations=False)
        b=World(4,shared=True,physics=RACE_PHYSICS_VERSION);b.restore(json.loads(json.dumps(w.snapshot())))
        self.assertEqual(w.snapshot(),b.snapshot())
        with self.assertRaises(ValueError):World(4,shared=True).restore(w.snapshot())
        for row in w.rows():self.assertEqual((row['vehicleLength'],row['vehicleWidth']),(4.4,1.8))

    def test_impulse_preserves_momentum_and_dissipates_energy(self):
        x=np.zeros((2,7));x[1,0]=4.3;x[:,3]=[7,2]
        momentum=x[:,3:5].sum(axis=0)*RACE_VEHICLE.mass
        energy=lambda:.5*RACE_VEHICLE.mass*np.sum(x[:,3:5]**2)+.5*RACE_VEHICLE.yaw_inertia*np.sum(x[:,5]**2)
        initial=energy();body=vertices(x,RACE_VEHICLE)
        hit=resolve(x,0,1,*body,RACE_VEHICLE)
        np.testing.assert_allclose(x[:,3:5].sum(axis=0)*RACE_VEHICLE.mass,momentum,atol=1e-8)
        self.assertLess(energy(),initial);self.assertAlmostEqual(hit['impactSpeed'],5)
        self.assertGreater(x[1,0]-x[0,0],4.4)

    def test_soft_contact_recovers_and_severe_contact_retires(self):
        for speed,severe in ((2,False),(16,True)):
            w=World(2,shared=True,physics=RACE_PHYSICS_VERSION)
            w.state[:,0]=[0,4.3];w.state[:,1]=-31;w.state[:,2]=0;w.state[:,3]=[speed,0]
            w.previous_phase=w.coordinates()[2].copy();w.step([[0.,0.],[0.,0.]],return_observations=False)
            self.assertEqual(w.retired.all(),severe)
            self.assertTrue(any(e['type']=='contact' for e in w.events))

    def test_offroad_is_recoverable_but_never_a_clean_qualification(self):
        w=World(physics=RACE_PHYSICS_VERSION);w.state[0,1]=-37
        w.step([[0,0]],return_observations=False)
        self.assertTrue(w.active[0]);self.assertEqual(w.track_limits[0],1)
        self.assertEqual(w.reward_terms['progress'][0],0)
        w.state[0,1]=-31;w.previous_phase=w.coordinates()[2].copy()
        w.step([[0,.5]],return_observations=False);self.assertFalse(w.was_offroad[0])
        e=Episode('oval-1','launch',3);e.world.track_limits[0]=1
        self.assertFalse(e.skill_valid())

    def test_each_method_resumes_an_inflight_batch_exactly(self):
        for method in ('evolution','ppo','ppo_smooth','imitation','neat'):
            with self.subTest(method=method):
                p=academy_profile({**preset(5,method),'population':8,'rollout':64})
                a=AcademyTrainer(p,'oval-1')
                for _ in range(43):a.tick()
                b=AcademyTrainer(p,'oval-1',json.loads(json.dumps(a.checkpoint(2))))
                for _ in range(53):a.tick();b.tick()
                self.assertEqual(a.checkpoint(4),b.checkpoint(4))

    def test_progressive_launch_changes_goal_without_forcing_commands(self):
        p=academy_profile(preset(3,'ppo'));t=AcademyTrainer(p,'oval-1')
        self.assertEqual(t.task['distance'],1)
        t.state['launchGoal']=3;t.reset_episodes();self.assertEqual(t.task['distance'],3)
        for e in t.episodes:self.assertEqual(e.spec['distance'],3)
        e=t.episodes[0]
        for _ in range(15):e.step([0.,-1.])
        self.assertEqual(e.world.state[0,3],0)
        restored=AcademyTrainer(p,'oval-1',json.loads(json.dumps(t.checkpoint(1))))
        self.assertEqual(restored.checkpoint(1),t.checkpoint(1))
        validation=SkillEvaluation(t.learner.policy(),None,'launch','oval-1',1)
        self.assertTrue(all(e.spec['distance']==20 for e in validation.episodes))

    def test_evaluation_does_not_change_training_and_resume_is_exact(self):
        p=academy_profile(preset(2));trainer=AcademyTrainer(p,'oval-1')
        before=trainer.checkpoint(0);policy=reference_policy('oval-1',academy=True)
        a=SkillEvaluation(policy,policy,'overtake','oval-1',2)
        for _ in range(61):a.tick()
        b=SkillEvaluation(policy,policy,'overtake','oval-1',2,saved=json.loads(json.dumps(a.snapshot())))
        for _ in range(39):a.tick();b.tick()
        self.assertEqual(a.snapshot(),b.snapshot());self.assertEqual(trainer.checkpoint(0),before)

    def test_impossible_evaluation_stops_without_inventing_valid_trials(self):
        p=reference_policy('oval-1',academy=True)
        e=SkillEvaluation(p,p,'duel','oval-1',1)
        self.assertEqual(len(e.scenarios),20);self.assertIn('pace',e.skills);self.assertIn('overtake',e.skills)
        for episode in e.episodes[:3]:episode.reason='contact'
        self.assertTrue(e.tick());result,previous=e.results()
        self.assertTrue(e.cancelled);self.assertIsNone(previous)
        self.assertEqual((result['valid'],result['total'],result['tested']),(0,20,3))
        self.assertFalse(result['retained'])

    def test_qualification_requires_actual_duel_and_retained_skills(self):
        from types import SimpleNamespace
        t=AcademyTrainer(academy_profile(preset()),'oval-1');policy=t.learner.policy()
        def proof(skill,laps):return {'valid':20,'total':20,'laps':laps,'median':40.,'best':39.,'results':[],'skill':skill}
        for phase,skills in [('overtake',{'pace':proof('pace',3),'overtake':proof('overtake',1)}),
                             ('duel',{'pace':proof('pace',3),'duel':proof('duel',3),'overtake':proof('overtake',1)})]:
            t.state['phase']=phase;t.state['round']+=1
            result={**proof(phase,3),'skills':skills,'retained':True}
            t.evaluation=SimpleNamespace(candidate=policy,champion=None,scenarios=list(range(20)),results=lambda:(result,None))
            t.accept_evaluation()
            self.assertEqual('race2' in t.state['qualifications'],phase=='duel')

    def test_solo_certificate_does_not_grant_traffic_and_hash_is_required(self):
        profile=academy_profile(preset());s=scope_hash('oval-1',ACADEMY_OBSERVATION_VERSION)
        cert={'scope':s,'candidateHash':'abc','valid':18,'total':20,'laps':3}
        d={'policy':'abc','policy_profile':profile,'curriculum':{'academyVersion':'academy-1','qualifications':{'solo':cert}}}
        self.assertTrue(qualified(d));self.assertFalse(race_eligible(d))
        d['curriculum']['qualifications']['race2']=cert
        self.assertFalse(race_eligible(d));self.assertFalse(race_eligible(d,participants=4))
        d['policy']='changed';self.assertFalse(qualified(d));self.assertFalse(race_eligible(d))

    def test_teacher_completes_launch_and_traffic_without_assisting_networks(self):
        for track in ('oval-1','technical-1','mallory-oval-1','varano-short-1'):
            for phase in ('launch','follow','overtake','corner'):
                with self.subTest(track=track,phase=phase):
                    e=Episode(track,phase,12)
                    while not e.reason:e.step(racing_actions(e.world,[0])[0])
                    self.assertEqual(e.reason,'success',e.result())
                    self.assertEqual(e.world.track_limits[0],0)


if __name__=='__main__':unittest.main()
