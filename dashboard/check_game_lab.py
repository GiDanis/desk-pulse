"""Physics parity, truncation and exact environment resume, no training here."""
from copy import deepcopy
import unittest
import numpy as np
from game_lab.environment import RacingEnv,TICKS
from game_direct import controls,features
from game_lab.teacher import Teacher


class LabChecks(unittest.TestCase):
    def test_long_evaluation_does_not_recount_old_contacts(self):
        from unittest.mock import patch
        from game_lab.environment import make_episode
        from game_lab.evaluation import evaluate
        case=dict(seed=72,family='traffic',bots=1,duration=2.)
        e=make_episode(**case);w=e.world
        w.state[1,:3]=w.state[0,:3];w.state[1,0]+=.5
        with patch('game_lab.evaluation.bank',return_value=dict(cases=[case])),patch('game_lab.evaluation.make_episode',return_value=e):
            report=evaluate(duration=2.,cases=1)
        contacts=sum(v['type']=='contact' for v in w.events)
        self.assertGreater(contacts,0);self.assertEqual(report['rows'][0]['globalContacts'],contacts)

    def test_gym_and_sb3_contracts(self):
        from gymnasium.utils.env_checker import check_env
        from stable_baselines3.common.env_checker import check_env as check_sb3
        e=RacingEnv(duration=.3)
        check_env(e,skip_render_check=True);check_sb3(e)

    def test_exact_physics_and_reward_parity_all_families(self):
        for family in ('solo','traffic','attack','complete','corner','defend','recover'):
            with self.subTest(family=family):
                a=RacingEnv(family=family,duration=2.);b=RacingEnv(family=family,duration=2.)
                a.reset(seed=831);b.reset(seed=831)
                rng=np.random.default_rng(31)
                for _ in range(6):
                    action=rng.uniform(-.2,.3,2);_,reward,terminated,truncated,_=a.step(action)
                    expected=0.
                    for _ in range(TICKS):
                        applied=controls(b.episode.world,action,[0])[0]
                        _,r,done,_=b.episode.step(applied,return_observation=False);expected+=r
                        if done:break
                    np.testing.assert_array_equal(a.episode.world.state,b.episode.world.state)
                    self.assertEqual(reward,expected)
                    self.assertEqual(terminated,b.episode.terminated);self.assertEqual(truncated,b.episode.truncated)
                    if terminated or truncated:break

    def test_teacher_does_not_mutate_actor_or_opponent_planner_memory(self):
        env=RacingEnv();env.reset(seed=11);w=env.episode.world;teacher=Teacher()
        original=deepcopy(w.snapshot());obs=features(w)
        for _ in range(5):teacher.label(w)
        self.assertEqual(w.snapshot(),original);np.testing.assert_array_equal(features(w),obs)
        self.assertEqual(teacher.calls,5)

    def test_resume_and_external_time_limit_keep_terminal_observation(self):
        a=RacingEnv(family='solo',duration=.35,history=4);a.reset(seed=81)
        a.step([0.,.4]);saved=deepcopy(a.snapshot())
        b=RacingEnv(family='solo',duration=.35,history=4);b.restore(saved)
        for _ in range(3):
            x=a.step([0.,.4]);y=b.step([0.,.4])
            np.testing.assert_array_equal(x[0],y[0]);self.assertEqual(x[1:],y[1:])
        self.assertFalse(x[2]);self.assertTrue(x[3]);self.assertNotEqual(x[4]['physicsSteps'],0)
        with self.assertRaises(RuntimeError):a.step([0.,.4])


if __name__=='__main__':unittest.main()
