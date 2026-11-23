"""Physical timing, persistence, compatibility, and no compensation in promotion."""
import json,tempfile,unittest
from copy import deepcopy
import numpy as np
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION,configuration
from game_control import racing_actions
from game_timing import LapTiming,TimingWriter


def world(laps=3,count=1):
    w=World(count,4,shared=count>1,laps=laps,telemetry=True,physics=RACE_PHYSICS_VERSION,timing=True)
    w.timing.source='qualifica' if count==1 else 'gara'
    return w


def complete(w):
    while w.active.any() and w.time<240:w.step(racing_actions(w),return_observations=False)
    return w


class TimingTests(unittest.TestCase):
    def test_timing_matches_actual_laps_and_excludes_launch(self):
        w=complete(world());s=w.rows()[0]['timing']
        self.assertEqual(len(w.timing.pending),3)
        for measured,actual in zip(w.timing.pending,w.lap_times[0]):
            self.assertAlmostEqual(measured['time'],actual['time'],places=9)
            self.assertAlmostEqual(sum(measured['sectors']),actual['time'],places=9)
        self.assertEqual(s['personal']['lap'],2);self.assertFalse(s['personal']['standingStart'])
        self.assertEqual(w.timing.pending[0]['standingStart'],True)

    def test_timing_does_not_change_physics_or_rewards(self):
        a,b=world(laps=1),world(laps=1);b.timing=None
        for _ in range(400):
            u=racing_actions(a);v=racing_actions(b)
            ra,rb=a.step(u,return_observations=False),b.step(v,return_observations=False)
            for x,y in zip(ra,rb):np.testing.assert_array_equal(x,y)
        np.testing.assert_array_equal(a.state,b.state)

    def test_resume_in_sector_and_old_snapshot(self):
        a=world()
        for _ in range(900):a.step(racing_actions(a),return_observations=False)
        b=world();b.restore(json.loads(json.dumps(a.snapshot())))
        complete(a);complete(b)
        self.assertEqual(a.timing.snapshot(),b.timing.snapshot())
        old=b.snapshot();old.pop('timing');b.restore(old);self.assertIsNone(b.timing)

    def test_dirty_lap_and_model_switch_do_not_set_personal(self):
        w=world(laps=1);w.lap_contacted[0]=True;complete(w)
        self.assertFalse(w.timing.pending[0]['clean'])
        # A reference version change must invalidate an unfinished preview lap.
        w=world();w.timing.bind(0,'a','first');w.timing.bind(0,'a','second')
        self.assertFalse(w.timing.cars[0]['valid']);self.assertIsNone(w.timing.row(0)['personal'])

    def test_candidate_switch_rejects_midlap_and_official_sessions(self):
        w=world();w.timing.bind(0,'a','first')
        with self.assertRaises(ValueError):w.timing.bind_preview_boundary(0,'a','second',0,w.time)
        w.timing.source='preview'
        with self.assertRaises(ValueError):w.timing.bind_preview_boundary(0,'a','second',0,w.time)
        complete(w)
        w.timing.source='qualifica'
        with self.assertRaises(ValueError):w.timing.bind_preview_boundary(0,'a','second',3,w.time)
        w.timing.source='preview'
        with self.assertRaises(ValueError):w.timing.bind_preview_boundary(0,'a','second',3,w.time+1)

    def test_frozen_pb_reference_is_not_zeroed_on_record(self):
        w=world();s=w.timing.cars[0]
        ref=dict(time=50.,sectors=[16.,17.,17.],policy='old',id='old')
        w.timing.bind(0,'x','new',ref)
        complete(w)
        second=w.timing.pending[1]
        self.assertLess(second['personalDelta'],0)
        self.assertAlmostEqual(second['personalDelta'],second['time']-50.)
        self.assertTrue(w.timing.row(0)['deltas'] is not None)

    def test_persistence_is_idempotent_and_context_bound(self):
        from game_store import GameStore
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);driver=store.drivers()[0]
            p=dict(id=driver['id'],policy=driver['policy'],profile=driver['profile'],name=driver['name'])
            run,_=store.begin_session('qualifica',dict(profile=driver['profile'],participants=[p]))
            w=world();w.timing.bind(0,driver['id'],driver['policy']);complete(w)
            records=w.timing.drain();writer=TimingWriter(store);writer.submit(run,records);writer.flush();writer.submit(run,records);writer.close()
            with store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM timing_laps').fetchone()[0],3)
            pb=store.timing_reference(driver['id'],configuration('oval-1',driver['profile']['observation']))
            self.assertEqual(len(pb['sectors']),3);self.assertFalse(pb['standingStart'])
            self.assertIsNone(store.timing_reference(driver['id'],configuration('technical-1',driver['profile']['observation'])))
            bad=deepcopy(records);bad[0]['policy']='wrong'
            with self.assertRaises(ValueError):store.save_timing(run,bad)
            bad=deepcopy(records);bad[0]['sectors'][0]+=1
            with self.assertRaises(ValueError):store.save_timing(run,bad)
            from unittest.mock import patch
            from game_records import category
            config=configuration('oval-1',driver['profile']['observation'])
            historic=dict(category=category(config)[0],bestLap=dict(value=20.,mode='qualifica',standingStart=False,policy='old',session='old',lap=2))
            with patch.object(store,'records',return_value=[historic]):
                historic_pb=store.timing_reference(driver['id'],config)
                self.assertEqual(historic_pb['time'],20.);self.assertIsNone(historic_pb['sectors'])
            store.reset_driver(driver['id']);self.assertIsNotNone(store.timing_reference(driver['id'],configuration('oval-1',driver['profile']['observation'])))

    def test_missing_sector_cannot_become_valid(self):
        w=world();s=w.timing.cars[0];s.update(standing=False,start=0.,splits=[10.],expected=1)
        w.timing._finish(w,0,35.,True)
        self.assertFalse(w.timing.row(0)['last']['clean']);self.assertIsNone(w.timing.row(0)['personal'])

    def test_spatial_verifier_detects_squeeze_and_arbitrary_brake(self):
        from game_academy import Episode
        from game_rewards import specification
        from game_racecraft import observe
        e=Episode('oval-1','defend',3,protocol='driving-memory-1',reward_spec={**specification({'algorithm':'residual_tactic'}),'evaluationRules':'spatial-rules-2'})
        w=e.world;w.state[0,:3]=w.track.pose(0,0);w.state[1,:3]=w.track.pose(-12,0)
        w.state[:,3]=[6,8];w.progress[:]=[0,-12]
        for _ in range(32):observe(e,[0,-1])
        self.assertGreater(e.racecraft['unnecessaryBrake'],0)
        e.racecraft=None;w.state[0,:3]=w.track.pose(30,0)
        for _ in range(32):observe(e,[0,-1])
        self.assertEqual(e.racecraft['unnecessaryBrake'],0)  # necessary corner braking
        e.racecraft=None;w.state[0,:3]=w.track.pose(0,-2);w.state[1,:3]=w.track.pose(1,-4.9);w.progress[:]=[0,1]
        w.residual_rules={0:dict(requestedLine=-3.8)}
        for _ in range(20):observe(e,[0,0])
        self.assertEqual(e.racecraft['spaceViolations'],1)

    def test_sector_gate_rejects_reverse_duplicate_and_offroad_crossing(self):
        w=world();t=w.timing;origin=t.origins[0];axis=t.axes[0];normal=t.normals[0]
        def cross(a,b):t.advance(w,np.array([a]),np.array([b]),0.,1.,np.array([True]),np.array([False]),np.array([False]),np.array([True]),np.array([1.]))
        cross(origin+axis,origin-axis);self.assertEqual(t.cars[0]['expected'],0)
        cross(origin-axis+normal*8,origin+axis+normal*8);self.assertEqual(t.cars[0]['expected'],0)
        cross(origin-axis,origin+axis);self.assertEqual(t.cars[0]['expected'],1)
        cross(origin-axis,origin+axis);self.assertEqual(t.cars[0]['expected'],1)

    def test_promotion_rejects_compensation_between_skills(self):
        from game_residual import profile,snapshot,initial_weights
        from game_residual_trainer import ResidualCheck
        p=profile(2,'residual_tactic');data=snapshot(p,initial_weights(p));check=ResidualCheck(data,data,'oval-1')
        half=len(check.episodes)//2
        for e in check.episodes:e.reason='success';e.age=30.
        for e in check.episodes[half:half+3]:e.age=32.
        # The same total passes can hide a lost corner and a gained straight pass.
        check.episodes[5].reason='skill_failed';check.episodes[half+3].reason='skill_failed'
        result=check.result();self.assertFalse(result['accepted']);self.assertTrue(result['regressions'])
        self.assertEqual(result['candidate']['skills']['corner']['total'],4)

if __name__=='__main__':unittest.main()
