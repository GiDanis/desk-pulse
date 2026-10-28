"""Circuit topology, scoped persistence, draft transactions and PPO boundaries."""
import json
import tempfile
import unittest
import numpy as np
from game_geometry import get_track,validate_rings
from game_simulation import World,reference_actions,vertices,LAP_LENGTH
from game_store import GameStore
from game_learning import Evolution,PPO,forward
from game_catalog import configuration,scope_hash


class TrackChecks(unittest.TestCase):
    def test_technical_grid_is_staggered_inside_the_road(self):
        from game_simulation import overlap
        world=World(4,shared=True,track_id='technical-1');body=vertices(world.state)
        self.assertTrue(world.track.contains(body).all())
        # At a polyline vertex the lateral grid point projects a few mm onto
        # its adjacent segment; progression follows that physical projection.
        np.testing.assert_allclose(world.progress,[0,-4,-8,-12],atol=.01)
        for i in range(4):
            for j in range(i+1,4):self.assertFalse(overlap(body[i],body[j]))

    def test_new_track_roster_requires_proof_for_exact_saved_policy(self):
        from game_catalog import race_eligible
        driver={'policy':'saved','curriculum':None}
        self.assertFalse(race_eligible(driver))
        self.assertFalse(race_eligible(driver,'technical-1'))
        driver['curriculum']={'champion':{'proof':{'scope':scope_hash('technical-1'),'candidateHash':'saved','candidate':{'valid':9}}}}
        self.assertFalse(race_eligible(driver,'technical-1'))
        driver['policy']='different';self.assertFalse(race_eligible(driver,'technical-1'))
        driver['policy']='saved';driver['curriculum']['champion']['proof']['scope']=scope_hash()
        self.assertFalse(race_eligible(driver,'technical-1'))

    def test_unknown_archive_version_is_rejected_before_migration(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as root:
            with sqlite3.connect(root+'/game.sqlite') as db:db.execute('PRAGMA user_version=3')
            with self.assertRaises(ValueError):GameStore(root)
            with sqlite3.connect(root+'/game.sqlite') as db:
                self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)
                self.assertFalse(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())

    def test_indexed_sensors_match_all_segment_intersections(self):
        from game_geometry import cross
        t=get_track('technical-1');rng=np.random.default_rng(271)
        states=np.zeros((256,7))
        for row in states:row[:3]=t.pose(rng.uniform(0,t.length),rng.uniform(-4,4));row[2]+=rng.uniform(-3,3)
        angles=np.array([-1.5,-.7,0,.7,1.5])
        origin=np.repeat(states[:,:2],len(angles),axis=0)
        angle=(states[:,2,None]+angles).ravel();d=np.column_stack((np.cos(angle),np.sin(angle)))[:,None,:]
        v=t.boundary_delta[None,:,:];relative=t.boundaries[None,:,:]-origin[:,None,:];den=cross(d,v)
        distance=np.divide(cross(relative,v),den,out=np.full_like(den,51.),where=abs(den)>1e-12)
        frac=np.divide(cross(relative,d),den,out=np.full_like(den,2.),where=abs(den)>1e-12)
        valid=(distance>1e-6)&(distance<=50)&(frac>=0)&(frac<=1)
        brute=np.min(np.where(valid,distance,50),axis=1).reshape(len(states),len(angles))
        np.testing.assert_allclose(t.rays(states,angles),brute,atol=1e-12)

    def test_catalog_validation_and_shared_boundaries(self):
        t=get_track('technical-1')
        self.assertEqual(t.render(),configuration('technical-1')['track']['drawing'])
        self.assertTrue(t.contains(t.points).all())
        self.assertNotEqual(scope_hash(),scope_hash('technical-1'))
        self.assertAlmostEqual(get_track().length,LAP_LENGTH)
        with self.assertRaises(ValueError):validate_rings((np.array([[0.,0.],[2,2],[0,2],[2,0]]),))
        with self.assertRaises(ValueError):validate_rings((np.array([[0.,0.],[3,0],[2,0],[2,2],[0,2]]),))
        for distance in np.linspace(0,t.length,30,endpoint=False):
            pose=t.pose(distance);state=np.zeros((1,7));state[0,:3]=pose
            self.assertTrue(t.contains(vertices(state)).all())
            rays=t.rays(state,np.array([-np.pi/2,np.pi/2]))
            np.testing.assert_allclose(rays,5,atol=.015)

    def test_geometry_controller_lap_and_checkpoint_roundtrip(self):
        world=World(1,track_id='technical-1');copy=World(1,track_id='technical-1')
        for i in range(4000):
            world.step(reference_actions(world),return_observations=False)
            if i==100:
                copy.restore(json.loads(json.dumps(world.snapshot())))
                action=reference_actions(world);world.step(action);copy.step(action)
                self.assertEqual(world.snapshot(),copy.snapshot())
            if not world.active.any():break
        self.assertEqual(world.rows()[0]['status'],'arrivato')
        self.assertEqual(world.checkpoint[0],4)
        world.reset();self.assertFalse(world.retired.any());self.assertTrue(world.active.all())
        self.assertAlmostEqual(world.previous_phase[0],0,places=5)

    def test_gate_direction_and_shortcut_do_not_credit_lap(self):
        t=get_track('technical-1');gate=t.gates[0];direction=np.array([np.cos(gate[2]),np.sin(gate[2])])
        old=gate[:2]-direction;new=gate[:2]+direction
        self.assertTrue(t.gate_crossings(old[None],new[None],[0])[0][0])
        self.assertFalse(t.gate_crossings(new[None],old[None],[0])[0][0])
        self.assertFalse(t.gate_crossings(old[None],new[None],[1])[0][0])
        world=World(track_id='technical-1');world.state[0,:2]=np.mean(t.inner,axis=0)
        world.step(np.zeros((1,2)),return_observations=False)
        self.assertTrue(world.retired[0]);self.assertEqual(world.checkpoint[0],0)

    def test_track_and_profile_paths_resume_without_loss(self):
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);original=store.drivers()[0];identity=original['id']
            policy=Evolution(original['profile']).policy();store.save_training(identity,{'fixture':1},policy,100,12)
            oval=store.driver(identity)
            store.select_track('technical-1');self.assertIsNone(store.driver(identity)['checkpoint'])
            store.save_training(identity,{'fixture':2},policy,200,23)
            technical=store.driver(identity)
            changed={**technical['profile'],'algorithm':'ppo'};store.set_profile(identity,changed,allow_reconfigure=True)
            self.assertEqual(store.driver(identity)['steps'],0)
            store.set_profile(identity,technical['profile'],allow_reconfigure=True);self.assertEqual(store.driver(identity),technical)
            store.reset_driver(identity)
            store.select_track('oval-1');self.assertEqual(store.driver(identity),oval)
            self.assertEqual(store.total_seconds(identity),35)
            reopened=GameStore(root);self.assertEqual(reopened.driver(identity),oval)
            self.assertEqual(reopened.load(technical['checkpoint']),{'fixture':2})

    def test_transfer_keeps_source_and_requires_empty_compatible_path(self):
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);d=store.drivers()[0];policy=Evolution(d['profile']).policy()
            store.save_training(d['id'],{},policy,10,1);oval=store.driver(d['id'])
            store.select_track('technical-1');store.initialize_from(d['id'],'oval-1')
            self.assertEqual(store.initializer(d['id']),policy);self.assertIsNone(store.driver(d['id'])['policy'])
            store.select_track('oval-1');self.assertEqual(store.driver(d['id']),oval)

    def test_partial_episode_clock_and_pace_bonus_are_independent(self):
        a,b=World(),World();b.time=400
        for world in (a,b):
            world.state[0,0]=-.04;world.state[0,3]=6;world.progress[0]=LAP_LENGTH-.04
            world.previous_phase[0]=36-.04;world.checkpoint[0]=3;world.episode_time[0]=20
        np.testing.assert_allclose(a.step([[0.,0.]],pace=1)[1],b.step([[0.,0.]],pace=1)[1])
        world=World(2);world.episode_time[:]=[25,40];world.reset_trials([True,False])
        np.testing.assert_array_equal(world.episode_time,[0,40])

    def test_ppo_timeout_bootstraps_but_terminal_does_not(self):
        from game_store import default_profile
        profile={**default_profile(),'algorithm':'ppo','population':8}
        p=PPO(profile);obs=np.zeros((8,42));next_obs=np.ones((8,42))*.2
        _,raw,logp,value=p.sample(obs);reward=np.ones(8);done=np.ones(8,dtype=bool);terminated=np.arange(8)%2==0
        next_value=forward(p.critic,next_obs,p.hidden,1)[:,0]
        p.remember(obs,raw,logp,value,reward,done,next_obs,terminated)
        update=p.updates();next(update)
        np.testing.assert_allclose(p.pending['flat'][4],reward+profile['gamma']*next_value*(~terminated))


if __name__=='__main__':unittest.main()
