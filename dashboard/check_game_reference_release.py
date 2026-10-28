"""Release authority, exact hashes and atomic activation on synthetic stores."""
from copy import deepcopy
import json,tempfile,unittest
import torch
from game_lab.models import Actor
from game_lab.skills import initialize,export
from game_lab.provenance import source_hashes
from game_reference_release import validate,install,VERSION,METHODS
from game_lab.qualification import VERSION as GATE
from game_store import GameStore
from game_catalog import configuration
from game_residual import key
from game_reference_backend import factory_policy,qualified_ancestry


class ReleaseChecks(unittest.TestCase):
    def fixture(self):
        # Synthetic gate records exercise transactions only. They are never
        # written to project evidence or accepted as a measured qualification.
        torch.set_num_threads(1);torch.manual_seed(810)
        proposal=dict(version=VERSION,methods={})
        for method in METHODS:
            model,_=initialize(Actor('gru-skip',128).export(),'td3' if method=='residual_tactic' else method.removeprefix('residual_'),
                role='tactic' if method=='residual_tactic' else 'driving')
            policy=export(model);policy['features']='direct-physical-90-road-v2';digest=key(policy)
            runs=[dict(seed=i,datasetHash=str(i),candidateHash=digest,passed=True,issues=[]) for i in range(5)]
            proposal['methods'][method]=dict(policy=policy,policyHash=digest,selectedSeed=0,
                qualification=dict(version=GATE,qualified=True,failures=[],runs=runs,improvedSeeds=5),
                context=configuration('oval-1','race-68-v3'))
        arm=dict(version=VERSION,qualified=True,policies={m:p['policyHash'] for m,p in proposal['methods'].items()},
            runtimeSourceHashes=source_hashes(),checks={k:True for k in
            ('learning','exactResume','allModes','race2','race5','eglfsBase','eglfsFunctional','eglfsApple','health')})
        return proposal,arm

    def test_missing_scientific_or_arm_evidence_is_rejected(self):
        p,a=self.fixture()
        for broken in ('scientific','partial','hash','arm','source'):
            with self.subTest(broken=broken):
                proposal=deepcopy(p);arm=deepcopy(a)
                if broken=='scientific':proposal['methods']['residual_ppo']['qualification']['qualified']=False
                elif broken=='partial':proposal['methods'].pop('residual_sac')
                elif broken=='hash':proposal['methods']['residual_td3']['policy']['weights']['head.bias'][0]+=.1
                elif broken=='arm':arm['checks']['eglfsApple']=False
                else:arm['runtimeSourceHashes']={}
                with self.assertRaises(ValueError):validate(proposal,arm)

    def test_atomic_activation_keeps_old_paths_and_reset_uses_new_base(self):
        p,a=self.fixture()
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);old={d['id']:deepcopy(d) for d in store.drivers()}
            result=install(store,p,a);self.assertTrue(result['installed'])
            self.assertEqual(len(store.drivers()),len(old))
            for driver in store.drivers():
                if driver['profile']['algorithm'] not in METHODS:continue
                self.assertEqual(driver['name'],old[driver['id']]['name'])
                self.assertEqual(driver['profile']['learningBackend'],'sb3-skill-1')
                with store.connect() as db:
                    row=db.execute('SELECT state FROM profile_paths WHERE id=?',(driver['id'],)).fetchone()
                self.assertTrue(row)
                policy=factory_policy(store,driver['profile']);self.assertTrue(qualified_ancestry(store,policy,store.reference_release()))
                store.reset_driver(driver['id']);self.assertEqual(store.driver(driver['id'])['policy'],key(policy))

    def test_qualification_freezes_saved_candidate_and_legacy_objectives_stay_archived(self):
        # Synthetic lap values verify selection/persistence, not driving skill.
        from game_store import canonical
        from game_modes import qualified_snapshot
        p,a=self.fixture()
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);driver=next(d for d in store.drivers() if d['name']=='Crono');identity=driver['id']
            def certify(digest,profile):
                session,_=store.begin_session('qualifica',dict(participants=[dict(id=identity,policy=digest,profile=profile)],profile=profile))
                return store.record_qualification(identity,digest,profile,dict(clean=True,time=30.,standingStart=False),session)
            certify(driver['policy'],driver['profile'])
            checkpoint=store.artifact(dict(configuration=configuration('oval-1','race-68-v3')))
            state={k:driver[k] for k in ('policy','policy_profile','candidate','steps','seconds')}
            state.update(profile=canonical(driver['profile']).decode(),policy_profile=canonical(driver['profile']).decode(),checkpoint=checkpoint,curriculum=None)
            with store.connect() as db:db.execute('INSERT INTO objective_paths VALUES(?,?,?,?)',
                (identity,'oval-1','impara_sorpasso',canonical(state).decode()))
            store.select_track('technical-1');store.select_track('oval-1')
            install(store,p,a)
            current=store.driver(identity)
            self.assertIsNone(qualified_snapshot(current,'oval-1'))
            self.assertTrue(current['timedQualifications'])  # history preserved
            store.select_objective('impara_sorpasso');self.assertIsNone(store.objective_checkpoint(identity,'impara_sorpasso'))
            self.assertEqual(store.driver(identity)['profile']['learningBackend'],'sb3-skill-1')
            store.select_objective('impara')
            policy=deepcopy(p['methods']['residual_ppo']['policy']);policy['weights']['head.bias'][0]+=.001
            candidate=store.artifact(policy)
            with store.connect() as db:db.execute('UPDATE drivers SET candidate=?,steps=777 WHERE id=?',(candidate,identity))
            self.assertEqual(store.qualification_candidate(identity),(candidate,current['profile']))
            certify(candidate,current['profile'])
            self.assertEqual(qualified_snapshot(store.driver(identity),'oval-1')['policy'],candidate)
            policy['weights']['head.bias'][0]+=.001;later=store.artifact(policy)
            with store.connect() as db:db.execute('UPDATE drivers SET candidate=? WHERE id=?',(later,identity))
            self.assertEqual(qualified_snapshot(store.driver(identity),'oval-1')['policy'],candidate)
            result=install(store,p,a);self.assertTrue(result['alreadyInstalled'])
            self.assertEqual(store.driver(identity)['steps'],777)
            # Overtaking contributes to the same pilot's next new objective
            # and qualifying candidate. Its timed race snapshot stays frozen.
            store.select_objective('impara_sorpasso')
            state=dict(trainingProfile=current['profile'],evaluations=[])
            checkpoint=dict(backend='sb3-skill-1',protocol='sb3-skill-1',configuration=configuration('oval-1','race-68-v3'),task={})
            policy['weights']['head.bias'][1]+=.003;shared=store.save_training(identity,checkpoint,policy,1000,100.,curriculum=state)
            self.assertEqual(store.reference_candidate(identity),shared)
            store.select_objective('impara')
            self.assertEqual(store.qualification_candidate(identity)[0],shared)
            self.assertEqual(qualified_snapshot(store.driver(identity),'oval-1')['policy'],candidate)
            store.select_track('technical-1')
            self.assertEqual(store.driver(identity)['profile']['learningBackend'],'sb3-skill-1')
            self.assertEqual(store.reference_candidate(identity),shared)
            store.reset_driver(identity);self.assertIsNone(store.reference_candidate(identity))
            with store.connect() as db:
                event=db.execute("SELECT payload FROM history WHERE driver=? AND kind='reference_archive'",(identity,)).fetchone()
            self.assertIn('impara_sorpasso',event[0])

    def test_new_release_with_same_backend_cannot_resurrect_old_personal_models(self):
        from game_modes import qualified_snapshot
        from game_store import canonical
        p,a=self.fixture()
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);install(store,p,a)
            driver=next(d for d in store.drivers() if d['name']=='Crono');identity=driver['id']
            policy=deepcopy(p['methods']['residual_ppo']['policy']);policy['weights']['head.bias'][0]+=.001
            policy['origin']['baseHash']=driver['policy']
            checkpoint=dict(backend='sb3-skill-1',configuration=configuration('oval-1','race-68-v3'),task={})
            shared=store.save_training(identity,checkpoint,policy,1000,100.,curriculum=dict(trainingProfile=driver['profile'],evaluations=[]))
            self.assertEqual(store.reference_candidate(identity),shared)
            session,_=store.begin_session('qualifica',dict(participants=[dict(id=identity,policy=shared,profile=driver['profile'])],profile=driver['profile']))
            store.record_qualification(identity,shared,driver['profile'],dict(clean=True,time=30.,standingStart=False),session)
            with store.connect() as db:db.execute('INSERT INTO objective_archives VALUES(?,?,?,?,?)',
                (identity,'oval-1','impara_sorpasso','previous-scope',canonical(dict(oldCheckpoint=shared)).decode()))
            self.assertIsNotNone(qualified_snapshot(store.driver(identity),'oval-1'))
            upgraded=deepcopy(p)
            for method,pack in upgraded['methods'].items():
                pack['policy']['weights']['head.bias'][1]+=.002;pack['policyHash']=key(pack['policy'])
                for run in pack['qualification']['runs']:run['candidateHash']=pack['policyHash']
            arm=deepcopy(a);arm['policies']={m:v['policyHash'] for m,v in upgraded['methods'].items()}
            install(store,upgraded,arm)
            self.assertIsNone(store.reference_candidate(identity))
            self.assertIsNone(qualified_snapshot(store.driver(identity),'oval-1'))
            self.assertTrue(store.driver(identity)['timedQualifications'])
            self.assertEqual(store.qualification_candidate(identity)[0],upgraded['methods']['residual_ppo']['policyHash'])
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM objective_archives WHERE driver=?',(identity,)).fetchone()[0],0)
                archive=json.loads(db.execute("SELECT payload FROM history WHERE driver=? AND kind='reference_archive' ORDER BY id DESC LIMIT 1",(identity,)).fetchone()[0])
            self.assertEqual(archive['memory']['reference']['policyHash'],shared)
            self.assertEqual(len(archive['qualifications']),1)
            self.assertEqual(len(archive['objectiveArchives']),1)

if __name__=='__main__':unittest.main()
