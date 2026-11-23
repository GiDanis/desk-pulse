"""Attack-specific causal outcomes, safety, continuation and checkpoint tests."""
import json,unittest
import numpy as np
from game_direct_bootstrap import direct_profile
from game_direct_trainer import DirectTrainer
from game_learning import Policy
from game_overtaking import scenario,before_step,relative_step
from game_racing_objective import RacingCheck

def profile(method='residual_sac',coefficient=.25):
    return {**direct_profile(711,method),'trafficLearning':'attack-1','relativeAdvantage':coefficient}


class AttackTests(unittest.TestCase):
    def test_fast_approach_is_distinct_from_matching_a_front_car(self):
        from game_overtaking import observe
        e=scenario('oval-1','attack',711,profile());w=e.world
        w.state[0,3]=12.;w.state[1,3]=6.;e.age=1/60;observe(e)
        self.assertGreater(e.attack['queueSeconds'],0.)
        self.assertGreater(e.attack['closingApproachSeconds'],0.)
        self.assertEqual(e.attack['followingWithoutClosingSeconds'],0.)
        e.age=.1;e.attack['ticks']=6;w.state[0,3]=6.
        before=e.attack['closingApproachSeconds'];observe(e)
        self.assertEqual(e.attack['closingApproachSeconds'],before)
        self.assertGreater(e.attack['followingWithoutClosingSeconds'],0.)
        # These observations must not change a command, physical state, or
        # historical gate. They explain what the old proximity counter means.
        np.testing.assert_array_equal(w.state[:,3],[6.,6.])

    def test_relative_reward_cannot_be_farmed_by_reverse_offroad(self):
        e=scenario('oval-1','attack',711,profile());w=e.world
        total=0.
        for distance,outside in ((2.,False),(-2.,True),(2.,False),(-2.,False)):
            old=before_step(e);w.progress[0]+=distance;w.was_offroad[0]=outside
            total+=relative_step(e,old)
        self.assertLessEqual(total,1e-12)
        old=before_step(e);w.active[1]=False;w.progress[0]+=20
        self.assertEqual(relative_step(e,old),0.)

    def test_curriculum_is_bounded_and_preview_stays_continuous(self):
        t=DirectTrainer(profile(),'oval-1',objective='impara_sorpasso')
        self.assertTrue(t.preview.world.continuous)
        seen=set()
        for i in range(10):
            t.state['stats']['episodes']=i;e=t.new_episode()
            seen.add(e.spec['attackFamily']);self.assertLessEqual(e.spec['limitSeconds'],60.)
        self.assertEqual(seen,{'complete','attack','corner','pace','defend','recover','traffic'})

    def test_exact_resume_preserves_replay_strata_actor_and_next_step(self):
        t=DirectTrainer(profile(),'oval-1',objective='impara_sorpasso')
        for _ in range(1600):t.tick()
        saved=t.checkpoint(0.);u=DirectTrainer(profile(),'oval-1',json.loads(json.dumps(saved)),objective='impara_sorpasso')
        np.testing.assert_array_equal(t.learner.family_tags[:t.learner.count],u.learner.family_tags[:u.learner.count])
        for _ in range(60):t.tick();u.tick()
        np.testing.assert_array_equal(t.learner.actor,u.learner.actor)
        np.testing.assert_array_equal(t.episode.world.state,u.episode.world.state)

    def test_all_methods_have_attack_evaluations_and_no_teacher(self):
        for method in ('residual_ppo','residual_sac','residual_td3','residual_tactic'):
            p=profile(method);t=DirectTrainer(p,'oval-1',objective='impara_sorpasso')
            c=RacingCheck(t.learner.policy(),t.state['champion']['policy'],'oval-1')
            self.assertEqual(len(c.cases),15)
            self.assertFalse(t.learner.policy()['teacherAtInference'])
            self.assertEqual(t.episode.spec['attackFamily'],'complete')

    def test_pass_detector_and_reward_are_not_overridden(self):
        e=scenario('oval-1','complete',711,profile());p=Policy(DirectTrainer(profile(),'oval-1').learner.policy())
        self.assertEqual(e.passes,0)
        while not e.reason:e.step(p.act(None,world=e.world,index=0),return_observation=False)
        self.assertEqual(e.reason,'success');self.assertEqual(e.passes,1)
        self.assertEqual(e.contact_count,0);self.assertEqual(e.world.track_limits[0],0)
        self.assertEqual(e.result()['attack']['passes'],e.passes)
        self.assertGreater(e.result()['attack']['startedAlongside'],0)
        self.assertLessEqual(e.result()['attack']['queueSeconds'],e.age)

    def test_attack_latency_measures_action_not_initial_alongside(self):
        from game_overtaking import observe
        e=scenario('oval-1','attack',711,profile());observe(e)
        self.assertEqual(e.attack['attacks'],0)
        e.age=1.5;e.attack['ticks']=6
        e.world.state[0,:3]=e.world.track.pose(0.,2.)
        observe(e)
        self.assertEqual(e.attack['attacks'],1)
        self.assertEqual(e.attack['attackLatencies'],[1.5])

    def test_legacy_resume_does_not_count_unobserved_historical_waiting(self):
        from game_overtaking import observe
        e=scenario('oval-1','attack',711,profile());e.age=300.
        observe(e)
        self.assertGreater(e.attack['opportunities'],0)
        self.assertLessEqual(e.attack['queueSeconds'],1/60+1e-9)

    def test_tactical_improvement_without_new_pb_and_safety_regression(self):
        t=DirectTrainer(profile(),'oval-1');c=RacingCheck(t.learner.policy(),t.state['champion']['policy'],'oval-1')
        half=len(c.cases)
        for i,e in enumerate(c.episodes):
            e.reason='success';e.age=6. if i<half else 7.
            e.world.lap_times[0]=[dict(time=23.,clean=True),dict(time=21.,clean=True),dict(time=21.,clean=True)]
        r=c.result();self.assertFalse(r['accepted']);self.assertTrue(r['attackAccepted']);self.assertTrue(r['raceProposed'])
        c.episodes[3].contact_count=1
        self.assertFalse(c.result()['attackAccepted'])

    def test_migration_keeps_personal_actor_and_archives_old_targets(self):
        old={k:v for k,v in profile().items() if k not in ('trafficLearning','relativeAdvantage')}
        t=DirectTrainer(old,'oval-1')
        for _ in range(850):t.tick()
        c=t.checkpoint(0.);u=DirectTrainer(profile(),'oval-1',c,objective='impara_sorpasso')
        np.testing.assert_array_equal(t.learner.actor,u.learner.actor)
        self.assertEqual(u.learner.count,0);self.assertGreater(len(u.state['recipeArchives']),0)
        self.assertEqual(u.steps,t.steps);self.assertEqual(c['curriculum']['effectiveParameters']['version'],'direct-driving-4')

    def test_pending_tactical_check_restores_exact_worlds(self):
        t=DirectTrainer(profile(),'oval-1');a=RacingCheck(t.learner.policy(),t.state['champion']['policy'],'oval-1')
        for _ in range(240):a.tick()
        saved=json.loads(json.dumps(a.snapshot()));b=RacingCheck(a.candidate,a.champion,'oval-1',saved=saved)
        for _ in range(180):a.tick();b.tick()
        for x,y in zip(a.episodes,b.episodes):np.testing.assert_array_equal(x.world.state,y.world.state)

if __name__=='__main__':unittest.main()
