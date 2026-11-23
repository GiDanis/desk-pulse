"""Driving outcomes, expert retention, multi-step boundaries and durable identity."""
from copy import deepcopy
import json,tempfile,unittest
import numpy as np
from game_direct_bootstrap import direct_profile,initial_policy
from game_direct_trainer import DirectTrainer,DirectOffPolicy
from game_learning import Policy,Adam,forward
from game_racing_learning import RoutedAdam,routed_backward
from game_racing_objective import RacingCheck,school_ready
from game_academy import Episode
from game_rewards import specification


def racing_profile(seed=2,method='residual_ppo'):
    from game_racing_presets import PROFILE_KEYS
    return {**{k:v for k,v in direct_profile(seed,method).items() if k not in PROFILE_KEYS},'racingObjective':'valid-time-1',
        'racingCurriculum':'graduated-1','expertLearning':'routed-1'}


class RacingObjectiveTests(unittest.TestCase):
    def test_faster_clean_straight_is_preferred_and_failure_is_not(self):
        from game_direct import controls
        from game_catalog import TRACK
        from game_driving_memory import current_context
        p=racing_profile();driver=Policy(initial_policy(p));rows=[]
        for variant,grip in (('normal',1.),('straight',1.),('full',1.),('straight',.85)):
            context=deepcopy(current_context('oval-1'));context['condition']['grip_factor']*=grip
            e=Episode('oval-1','pace',981001,protocol='driving-memory-1',single_lap=False,
                reward_spec=specification(p),context=context)
            while not e.reason:
                w=e.world;a=driver.act(None,world=w,index=0);x,y=w.state[0,:2]
                if variant=='full' or variant=='straight' and abs(x)<TRACK.half_straight-10 and abs(y)>TRACK.radius-7 and abs(w.state[0,5])<.12:
                    a[1]=1.;controls(w,a,[0])
                e.step(a,return_observation=False)
            rows.append(e)
        slow,fast,crash,slippery=rows
        self.assertEqual([slow.reason,fast.reason],['success','success'])
        self.assertLess(fast.age,slow.age);self.assertGreater(fast.return_total,slow.return_total)
        self.assertEqual(fast.contact_count,0);self.assertEqual(fast.world.track_limits[0],0)
        self.assertGreater(fast.understeer_seconds,1.);self.assertEqual(fast.term_totals['understeer'],0.)
        for failure in (crash,slippery):
            self.assertNotEqual(failure.reason,'success');self.assertLess(failure.return_total,slow.return_total)

    def test_routing_stops_both_gradient_and_adam_momentum_leakage(self):
        from game_neural_mixture import EXPERT_SIZE
        p=racing_profile();t=DirectTrainer(p,'oval-1');w=t.learner.actor.copy()
        obs=np.zeros((4,90));obs[:,73]=.95
        _,cache=forward(w,obs,128,cache=True);gradient=routed_backward(cache,np.ones((4,2)))
        full=Adam(len(w));full.m[:]=.1;full.v[:]=.05;full.t=10
        opt=RoutedAdam(full.snapshot());before=w.copy();opt.step(w,gradient,.001,obs)
        np.testing.assert_array_equal(w[EXPERT_SIZE:],before[EXPERT_SIZE:])
        self.assertGreater(np.linalg.norm(w[:EXPERT_SIZE]-before[:EXPERT_SIZE]),0.)
        self.assertEqual([b.t for b in opt.blocks],[11,10,10])
        obs[:,17]=1.
        _,cache=forward(w,obs,128,cache=True);gradient=routed_backward(cache,np.ones((4,2)))
        before=w.copy();restored=RoutedAdam(json.loads(json.dumps(opt.snapshot())))
        restored.step(w,gradient,.001,obs)
        np.testing.assert_array_equal(w[:EXPERT_SIZE],before[:EXPERT_SIZE])
        self.assertEqual([b.t for b in restored.blocks],[11,11,11])

    def test_multi_step_resume_terminal_and_truncation(self):
        p={**racing_profile(3,'residual_sac'),'racingBackup':3};a=DirectOffPolicy(p)
        obs=np.zeros(94)
        for value in (1.,2.):a.remember(obs,[0.,0.],value,obs,False)
        b=DirectOffPolicy(p,json.loads(json.dumps(a.checkpoint())))
        for learner in (a,b):learner.remember(obs,[0.,0.],3.,obs,True,True)
        gamma=a.spec['gamma'];self.assertEqual(a.count,3)
        np.testing.assert_allclose(a.replay[:3,92],[1+gamma*2+gamma**2*3,2+gamma*3,3])
        np.testing.assert_allclose(a.replay[:3,-1],[gamma**3,gamma**2,gamma])
        np.testing.assert_array_equal(a.replay[:3],b.replay[:3])
        self.assertTrue(np.all(a.replay[:3,183]==1.))
        a.remember(obs,[0.,0.],4.,obs,False,True)
        self.assertEqual(a.count,4);self.assertEqual(a.replay[3,183],0.)
        self.assertFalse(a.pending_transitions)

    def test_mode_change_discards_only_incomplete_old_horizon_and_check(self):
        p={**racing_profile(3,'residual_sac'),'racingBackup':3};t=DirectTrainer(p,'oval-1')
        for _ in range(7):t.tick()
        self.assertTrue(t.learner.pending_transitions)
        t.check=RacingCheck(t.learner.policy(),t.state['champion']['policy'],'oval-1')
        restored=DirectTrainer(p,'oval-1',t.checkpoint(0.),objective='impara_infinito')
        self.assertFalse(restored.learner.pending_transitions);self.assertIsNone(restored.check)
        np.testing.assert_array_equal(t.learner.actor,restored.learner.actor)

    def test_traffic_rehearsal_does_not_mask_race_practice(self):
        from game_school_lessons import SKILLS
        p={**racing_profile(5,'residual_tactic'),'racingAnchor':'steering-retained-1'}
        t=DirectTrainer(p,'oval-1');t.state['schoolStats']={s:dict(total=2,valid=2) for s in SKILLS};t.decisions=9000
        t.state['stats']['episodes']=14;self.assertIn('schoolSkill',t.new_episode().spec)
        t.state['stats']['episodes']=15;e=t.new_episode()
        self.assertEqual(e.phase,'race4');self.assertTrue(e.spec['practiceGrid'])

    def test_tactical_curriculum_counts_new_epoch_not_lifetime(self):
        from game_school_lessons import SKILLS
        p={**racing_profile(5,'residual_tactic'),'racingAnchor':'steering-retained-1'}
        t=DirectTrainer(p,'oval-1');t.state['schoolStats']={s:dict(total=2,valid=2) for s in SKILLS}
        t.state['epochStart']=dict(decisions=90000,steps=540000);t.decisions=90000
        for episode in (5,7,15):
            t.state['stats']['episodes']=episode
            self.assertEqual(t.new_episode().phase,'pace')
        self.assertEqual(t.curriculum_decisions(),0)
        t.decisions+=8192;t.state['stats']['episodes']=15
        self.assertEqual(t.new_episode().phase,'race4')
        t.state.pop('epochStart');self.assertEqual(t.curriculum_decisions(),t.decisions)

    def test_school_mastery_requires_every_skill(self):
        from game_school_lessons import SKILLS
        stats={s:dict(total=3,valid=2) for s in SKILLS}
        self.assertTrue(school_ready(stats));stats[SKILLS[-1]]['valid']=1
        self.assertFalse(school_ready(stats))
        p=racing_profile();t=DirectTrainer(p,'oval-1');t.state['schoolStats']={s:dict(total=2,valid=2) for s in SKILLS}
        t.state['stats']['episodes']=13
        e=t.new_episode();self.assertNotIn('schoolSkill',e.spec);self.assertGreater(e.initial_speed,0.)
        self.assertTrue(t.state['schoolGraduated'])

    def test_episode_exploration_is_coherent_and_resumes_conditionally(self):
        from game_direct_trainer import DirectPPO
        from game_learning import log_probability
        p={**racing_profile(),'episodeExploration':'coherent-pedal-1'}
        learner=DirectPPO(p);obs=np.zeros((1,94));obs[:,73]=.95
        action,raw,logp,_=learner.sample(obs);bias=learner.block['pedal']
        np.testing.assert_allclose(action,np.tanh(raw+[0.,bias]))
        np.testing.assert_allclose(logp,log_probability(raw,forward(learner.actor,obs[:,:90],128),learner.log_std))
        for _ in range(30):learner.sample(obs);self.assertEqual(learner.block['pedal'],bias)
        restored=DirectPPO(p,json.loads(json.dumps(learner.checkpoint())))
        for _ in range(20):
            for a,b in zip(learner.sample(obs),restored.sample(obs)):np.testing.assert_array_equal(a,b)

    def test_distributed_practice_succeeds_without_fabricating_a_flying_lap(self):
        from game_geometry import get_track
        p=racing_profile();track=get_track('oval-1')
        e=Episode('oval-1','pace',994008,protocol='driving-memory-1',single_lap=True,
            reward_spec=specification(p),scenario=dict(start=track.length/4,speed=8.,
            distance=track.length,label='Circuito da partenza variata',limitSeconds=100.,practiceCircuit=True))
        driver=Policy(initial_policy(p))
        while not e.reason:e.step(driver.act(None,world=e.world,index=0),return_observation=False)
        self.assertEqual(e.reason,'success');self.assertGreaterEqual(e.world.checkpoint[0],4)
        self.assertGreaterEqual(e.valid_progress,track.length)
        self.assertEqual(e.world.clean_laps[0],0)
        self.assertFalse(any(row['clean'] for row in e.world.lap_times[0]))

    def test_frozen_check_resume_and_flying_units(self):
        p=racing_profile();policy=initial_policy(p);a=RacingCheck(policy,policy,'oval-1')
        for _ in range(73):a.tick()
        b=RacingCheck(policy,policy,'oval-1',json.loads(json.dumps(a.snapshot())))
        for _ in range(20):a.tick();b.tick()
        self.assertEqual(a.snapshot(),b.snapshot())
        while not a.tick():pass
        result=a.result();self.assertFalse(result['accepted']);self.assertFalse(result['raceAccepted'])
        self.assertEqual(result['candidate']['valid'],3)
        self.assertLess(result['candidate']['median'],result['candidate']['results'][0]['standingAndFlyingSeconds']/3)
        from game_results import exercise
        facts=exercise(result);self.assertIn('serie valide',facts['value']);self.assertIn('lancio',facts['description'])

    def test_small_lap_gain_waits_for_real_race_validation(self):
        from game_neural_mixture import EXPERT_SIZE
        p=racing_profile();champion=initial_policy(p);candidate=deepcopy(champion)
        candidate['weights'][EXPERT_SIZE-1]+=.03
        check=RacingCheck(candidate,champion,'oval-1',race_due=False)
        while not check.tick():pass
        result=check.result()
        self.assertTrue(result['accepted']);self.assertTrue(result['raceProposed'])
        self.assertFalse(result['raceDue']);self.assertFalse(result['raceAccepted'])
        self.assertEqual(check.races,[])

    def test_migration_preserves_actor_identity_and_exact_qualification(self):
        from game_store import GameStore,canonical
        from game_residual import key
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);d=store.drivers()[2]
            from game_racing_presets import PROFILE_KEYS
            p={**{k:v for k,v in d['profile'].items() if k not in PROFILE_KEYS},'racingObjective':'legacy'}
            old=DirectTrainer(p,'oval-1')
            for _ in range(120):old.tick()
            checkpoint=old.checkpoint(7.);checkpoint['migrationSource']='a'*64
            original=json.dumps(checkpoint,sort_keys=True)
            new=DirectTrainer({**p,**{k:v for k,v in racing_profile(3,'residual_sac').items() if k in ('racingObjective','racingCurriculum','expertLearning')}},'oval-1',checkpoint)
            from game_neural_mixture import EXPERT_SIZE
            np.testing.assert_array_equal(old.learner.actor[:EXPERT_SIZE],new.learner.actor[:EXPERT_SIZE])
            np.testing.assert_array_equal(new.learner.actor[EXPERT_SIZE:],new.state['raceChampion']['policy']['weights'][EXPERT_SIZE:])
            self.assertEqual(original,json.dumps(checkpoint,sort_keys=True))
            self.assertEqual(new.steps,old.steps);self.assertEqual(new.learner.count,0)
            self.assertEqual(new.state['migration']['actor'],'solo-preserved-traffic-from-own-champion')
            stable=key(new.state['raceChampion']['policy'])
            fast=deepcopy(new.state['champion']);fast['policy']['weights'][0]+=.01
            new.state['champion']=fast
            with store.connect() as db:
                db.execute('INSERT INTO timed_qualifications VALUES(?,?,?,?)',(d['id'],'fixture',stable,canonical(dict(track='oval-1',bestLap=22.,policy=stable)).decode()))
            for _ in range(2):store.save_training(d['id'],new.checkpoint(7.),new.learner.policy(),new.steps,7.,{},new.state)
            self.assertEqual(store.driver(d['id'])['policy'],stable)
            self.assertEqual(store.qualification_candidate(d['id'])[0],stable)
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT policy FROM timed_qualifications').fetchone()[0],stable)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM history WHERE kind='racing_migration'").fetchone()[0],1)


if __name__=='__main__':unittest.main()
