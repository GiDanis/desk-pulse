"""Input semantics, sector recovery, reproduction boundaries and donor isolation."""
from copy import deepcopy
import json,os,tempfile,unittest
import numpy as np
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_profiles import preset
from game_observation_contract import contract,bind,migrate
from game_learning import Policy,Evolution,PPO,Imitation
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_control import racing_actions,pursuit_actions


def trainer(method='evolution',checkpoint=None,objective='impara'):
    return AcademyTrainer(academy_profile(preset(1,method)),'oval-1',checkpoint,objective=objective,balanced=True,batched=True)


class DrivingIntegrityChecks(unittest.TestCase):
    def test_same_policy_action_for_same_physical_state_across_task_cues(self):
        for method in ('evolution','neat','ppo','ppo_smooth','imitation'):
            t=trainer(method);p=Policy(t.learner.policy());a=Episode('oval-1','control',901,single_lap=True)
            b=Episode('oval-1','pace',901,single_lap=True)
            np.testing.assert_array_equal(a.world.state,b.world.state)
            self.assertIsNotNone(p.snapshot.get('inputContract'))
            np.testing.assert_array_equal(p.act(a.observations()),p.act(b.observations()))
            source=p.snapshot;again=Policy(json.loads(json.dumps(source)))
            np.testing.assert_array_equal(p.act(a.observations()),again.act(a.observations()))

    def test_legacy_migration_keeps_actor_moments_rng_and_is_idempotent(self):
        for method in ('evolution','neat','ppo','ppo_smooth','imitation'):
            t=trainer(method);c=t.checkpoint(9);c.pop('inputContract');c['learner'].pop('inputContract',None)
            c['curriculum']['phase']='pace';old=deepcopy(c);new=migrate(c)
            self.assertEqual(c,old);self.assertEqual(new['inputContract']['constantCue'],2/9)
            for key in ('population','actor','critic','actorAdam','criticAdam','weights','adam','rng','random'):
                if key in old['learner']:self.assertEqual(new['learner'][key],old['learner'][key])
            self.assertEqual(migrate(new),new);self.assertIsNone(new['episodes'])

    def test_legacy_archives_keep_their_own_cues(self):
        t=trainer();c=t.checkpoint(1);c.pop('inputContract');c['learner'].pop('inputContract',None)
        p=t.learner.policy();p.pop('inputContract');c['curriculum']['phase']='pace'
        c['curriculum']['evoTraining']['archives']={'10:control':{'policy':deepcopy(p)},'11:pace':{'policy':deepcopy(p)}}
        new=migrate(c);archives=new['curriculum']['evoTraining']['archives']
        self.assertEqual(archives['10:control']['policy']['inputContract']['constantCue'],1/9)
        self.assertEqual(archives['11:pace']['policy']['inputContract']['constantCue'],2/9)

    def test_dirty_sector_rearms_and_next_lap_is_clean_actual_motion(self):
        e=Episode('oval-1','control',901,protocol='driving-memory-1',objective='impara_infinito')
        e.world.native_sensors=True
        while e.age<125:
            if e.reason:self.assertEqual(e.reason,'window');e.next_window()
            # The oval is now 12 m wide: 4.6 m is still inside the asphalt.
            lane=e.world.track.width/2+.6 if 40<float(e.world.progress[0])<100 else 0.
            e.step(pursuit_actions(e.world,[0],speed_factor=.6,lateral_targets=np.array([lane]))[0])
        laps=e.world.lap_times[0]
        self.assertGreaterEqual(len(laps),2);self.assertFalse(laps[0]['clean']);self.assertTrue(laps[1]['clean'])
        self.assertAlmostEqual(laps[0]['end'],59.93,delta=.1)
        self.assertEqual(int(e.world.clean_laps[0]),1)

    def test_polygon_arbitrary_spawn_never_records_partial_lap_as_clean(self):
        for track in ('technical-1','mallory-oval-1','varano-short-1'):
            w=World(laps=1,track_id=track,physics=RACE_PHYSICS_VERSION,telemetry=True)
            w.continuous=True;w.state[0,:3]=w.track.pose(w.track.length-3);w.state[0,3]=3.
            if hasattr(w,'_segments'):del w._segments
            w.previous_phase=w.coordinates()[2].copy();w.progress[:]=0;w.initialize_gates()
            for _ in range(300):
                w.step(racing_actions(w),return_observations=False)
                if w.lap_times[0]:break
            self.assertTrue(w.lap_times[0]);self.assertFalse(w.lap_times[0][0]['clean'])
            self.assertEqual(int(w.clean_laps[0]),0)

    def test_reverse_and_line_jitter_never_award_extra_sectors(self):
        w=World(physics=RACE_PHYSICS_VERSION,telemetry=True);w.continuous=True
        # Fixture sets positions around the line; these are not integration proofs.
        for distance in (1.,-.1,.1,-.1,.1):
            w.state[0,:3]=w.track.pose(distance);w.state[0,3]=0
            w.step(np.zeros((1,2)),return_observations=False)
        self.assertEqual(int(w.clean_laps[0]),0);self.assertFalse(w.lap_times[0])

    def test_unchanged_evo_and_neat_survive_window_reproduction_and_resume(self):
        for method in ('evolution','neat'):
            t=trainer(method,objective='impara_infinito');old=list(t.episodes);keys=t.population_keys()
            for i,e in enumerate(old):
                e.reason='window';e.truncated=True;e.age=120.;e.world.time=120.;e.world.episode_time[:]=120
                e.life_key='stable-'+str(i)
            t.learner.update(np.arange(32,dtype=float));t.reset_episodes();t.continue_survivors(old,keys)
            continued=[e for e in t.episodes if e.age==120]
            self.assertTrue(continued);self.assertTrue(all(e.world.time==120 and not e.reason for e in continued))
            self.assertTrue(any(e.age==0 for e in t.episodes))
            saved=json.loads(json.dumps(t.checkpoint(2)));copy=trainer(method,saved,objective='impara_infinito')
            self.assertEqual(saved,json.loads(json.dumps(copy.checkpoint(2))))

    def test_shared_stages_preserve_method_and_gradient_update_cadence(self):
        for method in ('neat','ppo','ppo_smooth','imitation'):
            t=trainer(method);self.assertIsNotNone(t.evo_plan)
            self.assertEqual(t.task['distance'],1);self.assertEqual(t.profile['algorithm'],method)
            t.evo_plan.data['level']=7;t.evo_plan.sync();t.reset_episodes()
            self.assertEqual(t.task['distance'],60)
            self.assertEqual(t.reward_spec['version'],'balanced-driving-3')
            if method.startswith('ppo'):
                self.assertEqual(t.learner.tuning['gaeLambda'],.99)
                self.assertEqual(t.profile['rollout'],256)

    def test_stratified_teacher_replay_preserves_rare_maneuvers_and_resume(self):
        from game_numeric import ExampleBuffer
        b=ExampleBuffer(68,capacity=8192,stratified=True);x=np.zeros(68);x[46:48]=1
        for target in ([0,-1],[.3,1]):
            for _ in range(50):b.append(x,target)
        for _ in range(20000):b.append(x,[0,1])
        self.assertEqual([p.count for p in b.strata],[50,50,2048,0])
        c=ExampleBuffer(68,b.snapshot(),capacity=8192,stratified=True)
        for a,z in zip(b.sample(np.random.default_rng(1)),c.sample(np.random.default_rng(1))):np.testing.assert_array_equal(a,z)

    def test_branch_comparison_is_resumable_without_training_or_hidden_teacher(self):
        from game_transfer import BranchCheck
        t=trainer();p=t.learner.policy();check=BranchCheck('oval-1',p,p)
        for _ in range(40):check.tick()
        saved=json.loads(json.dumps(check.snapshot()));copy=BranchCheck('oval-1',p,p,saved)
        self.assertEqual(copy.snapshot(),saved)
        for e in check.episodes:e.reason='no_progress'
        self.assertFalse(check.result()['adopted'])

    def test_qualification_adapts_legacy_hash_without_copying_certificates(self):
        from game_store import GameStore
        with tempfile.TemporaryDirectory() as root:
            s=GameStore(root);identity=s.create_driver('Conservato','evolution');s.activate_academy(identity)
            t=trainer();c=t.checkpoint(10);c['curriculum']['phase']='pace'
            p=t.learner.policy();p.pop('inputContract');original=s.artifact(p)
            s.save_training(identity,c,p,3,10,curriculum=c['curriculum'])
            key,profile=s.qualification_candidate(identity)
            self.assertNotEqual(key,original);self.assertEqual(s.load(original),p)
            self.assertEqual(s.load(key)['inputContract']['constantCue'],2/9)
            self.assertFalse(s.driver(identity)['timedQualifications'])

if __name__=='__main__':unittest.main()
