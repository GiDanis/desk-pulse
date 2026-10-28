"""Evo curriculum: matched selection, real physics, retention and durable restart."""
from copy import deepcopy
import json,tempfile,unittest
import numpy as np
from game_academy import Episode,academy_profile
from game_academy_trainer import AcademyTrainer
from game_profiles import preset
from game_evo_plan import EvoPlan,EvoStageCheck,STAGES,stage_scenario
from game_learning import Evolution,Policy
from game_rewards import specification,migrate
from game_control import racing_actions
from game_store import GameStore
from game_dossier import dossier


def plain(value):return json.loads(json.dumps(value,allow_nan=False))
def trainer(checkpoint=None,**kwargs):
    return AcademyTrainer(academy_profile(preset(1,'evolution')),'oval-1',checkpoint,balanced=True,batched=True,**kwargs)


class EvoProgressiveChecks(unittest.TestCase):
    def test_migration_preserves_weights_and_rng_but_restarts_exercises_and_epoch(self):
        t=trainer();c=t.checkpoint(12.);c['rewardSpec']['version']='balanced-driving-1'
        c['curriculum'].update(phase='bend',launchGoal=20,stats={'episodes':193,'no_progress':155})
        c['steps']=1992091;old=deepcopy(c);result=migrate(c,t.profile,'impara')
        self.assertEqual(c,old);self.assertEqual(result['learner']['population'],old['learner']['population'])
        self.assertEqual(result['learner']['rng'],old['learner']['rng'])
        self.assertEqual(result['curriculum']['stats']['episodes'],193)
        self.assertEqual(result['curriculum']['epochStats']['episodes'],0)
        self.assertEqual(result['curriculum']['epochStats']['startedSteps'],1992091)
        self.assertEqual(result['curriculum']['launchGoal'],1)
        self.assertIsNone(result['episodes']);self.assertEqual(result['rewardSpec']['version'],'balanced-driving-2')
        self.assertEqual(migrate(result,t.profile,'impara'),result)

    def test_scenario_bank_is_stable_speed_only_changes_on_promotion(self):
        t=trainer();p=t.evo_plan;p.data['level']=7;p.sync();first=p.cases()
        p.data['generations']+=60;p.data['stageGenerations']+=60
        self.assertEqual(first,p.cases());self.assertTrue(set(c['seed'] for c in first).isdisjoint(c['seed'] for c in p.cases(True)))
        training_case=first[0];held_case=p.cases(True)[0]
        a=Episode('oval-1','bend',training_case['seed'],protocol='driving-memory-1',scenario=training_case['scenario'])
        b=Episode('oval-1','bend',held_case['seed'],protocol='driving-memory-1',scenario=held_case['scenario'])
        self.assertFalse(np.array_equal(a.world.state,b.world.state))
        self.assertEqual({c['scenario']['speed'] for c in first[:2]},{6.})
        self.assertFalse(p.accept(dict(retained=True)));self.assertEqual(p.data['level'],7)
        self.assertFalse(p.accept(dict(retained=False)));self.assertFalse(p.accept(dict(retained=True)))
        self.assertTrue(p.accept(dict(retained=True)));self.assertEqual(p.data['level'],8)
        self.assertEqual(p.cases()[0]['scenario']['speed'],8.)

    def test_retention_is_in_the_same_selection_without_resetting_stagnation(self):
        t=trainer();p=t.evo_plan;p.data['level']=7;p.sync();t.reset_episodes()
        t.learner.best_key=[99.,0.,0.,0.];t.learner.stagnation=22
        for case in range(3):
            for e in t.episodes:e.reason='success';e.valid_progress=e.spec['distance']
            result=p.take_results(t.episodes,np.arange(32,dtype=float))
            if case<2:
                self.assertIsNone(result);t.reset_episodes();self.assertEqual(t.learner.stagnation,22)
        scores,ranks=result
        self.assertTrue(np.all(ranks[:,:3]==[3.,1.,2.]))
        t.learner.update(scores,ranks);self.assertEqual(t.learner.stagnation,23)
        self.assertEqual(t.learner.mutation_scale,1.15)  # Reliable elites use local mutations, stagnation is retained.

    def test_current_reevaluated_elite_replaces_incomparable_historic_winner(self):
        t=trainer();l=t.learner;old=l.population.copy()
        l.best=np.full_like(l.best,123.);l.best_score=1e9;l.best_key=[1e9]
        scores=np.arange(32,dtype=float);ranks=np.column_stack((np.zeros(32),np.zeros(32),np.zeros(32),scores))
        ranks[4,0:3]=[3,1,2]
        l.update(scores,ranks)
        np.testing.assert_array_equal(l.population[0],old[4]);np.testing.assert_array_equal(l.best,old[4])
        self.assertEqual(l.best_score,4.)
        for index,shift in ((-3,-.25),(-2,.25)):
            expected=old[4].copy();expected[-1]+=shift;np.testing.assert_array_equal(l.population[index],expected)
        copied=Evolution(t.profile,plain(l.checkpoint()),evo_v2=True)
        l.update(scores,ranks);copied.update(scores,ranks)
        self.assertEqual(plain(l.checkpoint()),plain(copied.checkpoint()))

    def test_mutation_uses_fan_in_and_most_descendants_remain_local(self):
        t=trainer();l=t.learner;parent=l.population[0].copy();l.population[:]=parent
        l.update(np.zeros(32),np.zeros((32,4)))
        perturb=np.linalg.norm(l.population[4:28]-parent,axis=1)
        self.assertLess(float(np.median(perturb)),.6)
        self.assertGreater(float(np.median(perturb)),.1)

    def test_mid_physics_and_suite_checkpoint_resume_without_extra_update(self):
        t=trainer();t.evo_plan.data['level']=5;t.evo_plan.sync();t.reset_episodes()
        for e in t.episodes:e.reason='no_progress'
        for _ in range(64):
            if t.evo_plan.data['case']==1:break
            t.tick()
        self.assertEqual(t.evo_plan.data['case'],1);self.assertEqual(t.learner.generation,0)
        for _ in range(41):t.tick()
        saved=plain(t.checkpoint(2.));b=trainer(saved)
        self.assertEqual(plain(b.checkpoint(2.)),saved)
        for _ in range(233):t.tick();b.tick()
        self.assertEqual(plain(t.checkpoint(2.)),plain(b.checkpoint(2.)))

    def test_independent_check_runs_every_case_and_resumes(self):
        t=trainer();p=t.evo_plan;p.data['level']=5;p.sync()
        check=EvoStageCheck(p,t.learner.policy())
        for _ in range(33):check.tick()
        saved=plain(check.snapshot());copy=EvoStageCheck(p,check.candidate,saved)
        self.assertEqual(plain(copy.snapshot()),saved)
        while not check.tick():pass
        while not copy.tick():pass
        self.assertEqual(check.results(),copy.results())
        result=check.results()[0];self.assertEqual(result['tested'],4)
        self.assertEqual(sum(r['tested'] for r in result['skills'].values()),6)
        self.assertTrue(all(e.reason for e in check.episodes))
        self.assertGreater(p.data['evaluationSteps'],0)

    def test_old_track_retention_never_uses_positions_on_the_current_track(self):
        t=trainer(view='attempts');p=t.evo_plan;p.data['level']=5;p.sync()
        p.coverage=[dict(track='technical-1',phase='launch')]
        p.data['case']=3;t.reset_episodes()
        self.assertEqual(t.replay_context['track'],'technical-1')
        self.assertEqual(t.frame('Evo',1,0)[2]['phase'],'ripasso')
        self.assertTrue(all(e.track_id=='oval-1' for e in t.display_episodes))
        saved=t.checkpoint(2.);saved['memory']['coverage']=p.coverage
        b=trainer(plain(saved),view='attempts');self.assertEqual(b.evo_plan.cases(),p.cases())
        self.assertEqual(b.evo_plan.meta()['role'],'retention')

    def test_actual_physics_reference_can_solve_all_progression_stages(self):
        for track in ('oval-1','technical-1','mallory-oval-1','varano-short-1'):
            for level in range(len(STAGES)):
                with self.subTest(track=track,level=level):
                    scenario=stage_scenario(track,level,7000000+level*64)
                    e=Episode(track,scenario['phase'],7000000+level*64,protocol='driving-memory-1',
                        scenario=scenario,single_lap=True,reward_spec=specification(academy_profile(preset())))
                    e.world.native_sensors=True
                    while not e.reason:e.step(racing_actions(e.world,[0])[0])
                    self.assertEqual(e.reason,'success')

    def test_restart_preserves_weights_identity_history_and_full_reset_is_cold(self):
        with tempfile.TemporaryDirectory() as root:
            s=GameStore(root);identity=s.create_driver('Evo test','evolution');d=s.activate_academy(identity)
            t=AcademyTrainer(d['profile'],'oval-1',balanced=True,batched=True)
            for _ in range(96):t.tick()
            c=t.checkpoint(1.);s.save_training(identity,c,t.learner.policy(),t.steps,1.,curriculum=t.state)
            before=s.driver(identity);old=s.load(before['checkpoint']);s.restart_curriculum(identity);after=s.driver(identity)
            new=s.load(after['checkpoint']);self.assertNotEqual(after['checkpoint'],before['checkpoint'])
            self.assertEqual(new['learner']['population'],old['learner']['population'])
            for key in ('name','profile','policy','candidate','steps','seconds'):self.assertEqual(before[key],after[key])
            self.assertEqual(new['sourceCheckpoint'],before['checkpoint'])
            self.assertEqual(new['curriculum']['epochStats']['startedSteps'],t.steps)
            self.assertEqual(new['task']['distance'],1.);self.assertEqual(new['task']['limitSeconds'],12.)
            info=dossier(s,identity)
            self.assertTrue(any(r['title']=='Compito attuale' and r['value']=='1 m · 12 s' for r in info['parameters']))
            self.assertIn('reset.curriculum',[r['id'] for r in info['reset']])
            self.assertTrue(any(e['kind']=='curriculum_restart' for e in s.driver_events(identity)))
            s.reset_all(identity);self.assertIsNone(s.driver(identity)['checkpoint'])
            s.prepare_driving(identity);fresh=s.load(s.driver(identity)['checkpoint'])
            self.assertIsNone(fresh.get('memory',{}).get('baseline'))
            self.assertEqual(s.driver(identity)['steps'],0)
            self.assertIsNone(fresh.get('learner'))
            self.assertTrue(s.memory_record(identity)['reset'])
            self.assertEqual(s.driver(identity)['id'],identity);self.assertEqual(s.load(before['checkpoint']),old)

if __name__=='__main__':unittest.main()
