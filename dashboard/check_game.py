#!/usr/bin/env python3
"""Physics, numerical optimization, persistence and real process gates."""
import json
import multiprocessing as mp
from pathlib import Path
import tempfile
import time
import unittest

import numpy as np

from game_catalog import OBSERVATION_SIZE
from game_learning import Evolution, PPO, Policy, forward, log_probability, ppo_gradient
from game_simulation import World, DT, reference_actions
from game_store import GameStore, default_profile
from game_worker import worker_main


class GameChecks(unittest.TestCase):
    def test_reference_lap_and_substep_convergence(self):
        times=[]
        for substeps in (1,2,4):
            world=World(substeps=substeps)
            for _ in range(3600):
                world.step(reference_actions(world))
                if not world.active.any():break
            self.assertFalse(world.retired.any())
            self.assertTrue(np.isfinite(world.finish).all())
            self.assertEqual(world.checkpoint.tolist(),[4])
            from game_curriculum import summary
            row=world.rows()[0]
            self.assertEqual(summary([{'status':row['status'],'time':row['finishTime']}])['valid'],1)
            times.append(float(world.finish[0]))
        self.assertLess(max(times)-min(times),0.5)

    def test_fast_opposing_contact_and_rank_ties(self):
        world=World(2,shared=True)
        world.state[:,0]=[-5,5];world.state[:,1]=-31
        world.state[:,2]=[0,np.pi];world.state[:,3]=600
        world.step(np.zeros((2,2)))
        self.assertTrue(world.retired.all())
        self.assertTrue(any(x['type']=='contact' for x in world.events))
        world.finish[:]=10;self.assertEqual([r['position'] for r in world.rows()],[1,1])

    def test_world_resume_and_observable_opponents(self):
        world=World(4,shared=True)
        self.assertEqual(world.observations().shape,(4,OBSERVATION_SIZE))
        self.assertTrue((world.observations()[:,17]>0).all())
        for _ in range(30):world.step(reference_actions(world))
        other=World(4,shared=True);other.restore(json.loads(json.dumps(world.snapshot())))
        for _ in range(20):
            actions=reference_actions(world);world.step(actions);other.step(actions)
        np.testing.assert_array_equal(world.state,other.state)
        np.testing.assert_array_equal(world.progress,other.progress)

    def test_evolution_resume_rng(self):
        profile=default_profile();a=Evolution(profile)
        a.update(np.arange(32));saved=json.loads(json.dumps(a.checkpoint()))
        b=Evolution(profile,saved)
        a.update(np.linspace(-2,2,32));b.update(np.linspace(-2,2,32))
        np.testing.assert_array_equal(a.population,b.population)

    def test_ppo_gradient_against_finite_differences(self):
        p=PPO(default_profile());rng=np.random.default_rng(4)
        obs=rng.uniform(-0.5,0.5,(6,OBSERVATION_SIZE))
        mean=forward(p.actor,obs,p.hidden);raw=mean+rng.normal(0,.2,mean.shape)
        old=log_probability(raw,mean,p.log_std)+np.array([0,.4,-.4,.3,-.3,0])
        adv=np.array([1,-1,1,-1,-1,.5]);returns=rng.normal(size=6)
        result=ppo_gradient(p.actor,p.critic,p.log_std,p.hidden,obs,raw,old,adv,returns)
        for vector,gradient,loss_index in ((p.actor,result[2],0),(p.critic,result[3],1),(p.log_std,result[4],0)):
            for i in rng.choice(len(vector),min(12,len(vector)),replace=False):
                old_value=vector[i];eps=1e-6
                vector[i]=old_value+eps;plus=ppo_gradient(p.actor,p.critic,p.log_std,p.hidden,obs,raw,old,adv,returns)[loss_index]
                vector[i]=old_value-eps;minus=ppo_gradient(p.actor,p.critic,p.log_std,p.hidden,obs,raw,old,adv,returns)[loss_index]
                vector[i]=old_value
                self.assertAlmostEqual(float(gradient[i]),(plus-minus)/(2*eps),places=6)

    def test_neat_graph_and_resume_generation(self):
        from game_neat import NEAT
        import random
        profile={**default_profile(),'algorithm':'neat'};a=NEAT(profile)
        a.update(np.arange(32));checkpoint=json.loads(json.dumps(a.checkpoint()))
        obs=np.random.default_rng(7).uniform(-1,1,(32,OBSERVATION_SIZE))
        native=a.population.best_genome
        import neat
        net=neat.nn.FeedForwardNetwork.create(native,a.config)
        np.testing.assert_allclose(Policy(a.policy()).act(obs),[net.activate(row) for row in obs],atol=1e-14)
        a.update(np.arange(32));next_a=a.checkpoint()
        b=NEAT(profile,checkpoint);b.update(np.arange(32));next_b=b.checkpoint()
        self.assertEqual(next_a,next_b)

    def test_ppo_resume_between_minibatches(self):
        profile={**default_profile(),'population':8,'rollout':64,'epochs':2}
        a=PPO(profile);world=World(8)
        for _ in range(64):
            obs=world.observations();actions,raw,logp,values=a.sample(obs)
            nxt,reward,done=world.step(actions)
            a.remember(obs,raw,logp,values,reward,done,nxt)
            world.reset_trials(done)
        iterator=a.updates();next(iterator);next(iterator)
        saved=json.loads(json.dumps(a.checkpoint()))
        list(iterator);b=PPO(profile,saved);list(b.updates())
        self.assertEqual(a.checkpoint(),b.checkpoint())

    def test_artifact_corruption_and_interrupted_session(self):
        with tempfile.TemporaryDirectory() as root:
            store=GameStore(root);drivers=store.drivers();a=Evolution(drivers[0]['profile'])
            digest=store.save_training(drivers[0]['id'],a.checkpoint(),a.policy(),100,1.0)
            self.assertEqual(store.load(digest),a.policy())
            self.assertIsNone(store.driver(drivers[1]['id'])['policy'])
            profile={**drivers[0]['profile'],'algorithm':'ppo','traffic':True}
            store.set_profile(drivers[0]['id'],profile)
            changed=store.driver(drivers[0]['id'])
            self.assertIsNone(changed['checkpoint'])
            self.assertEqual(changed['policy'],digest)
            self.assertEqual(changed['policy_profile']['algorithm'],'evolution')
            (store.policies/(digest+'.json')).write_text('{}')
            with self.assertRaises(ValueError):store.load(digest)
            identity,payload=store.begin_session('gara',{'participants':[]})
            GameStore(root)
            self.assertEqual(store.sessions(complete=False)[0]['status'],'interrupted')
            self.assertFalse(store.sessions())

    def test_frozen_race_and_trials_keep_each_pilots_policy(self):
        context=mp.get_context('spawn')
        for mode,count in (('gara',2),('gara',4),('prova',2)):
            with self.subTest(mode=mode,count=count),tempfile.TemporaryDirectory() as root:
                store=GameStore(root);drivers=store.drivers()[:count]
                hashes=[]
                for driver in drivers:
                    learner=Evolution(driver['profile'])
                    fixture=learner.policy()
                    fixture['weights']=[0.0]*len(fixture['weights'])
                    fixture['weights'][-2:]=[2.0+driver['number']*.01,2.0]
                    hashes.append(store.save_training(driver['id'],learner.checkpoint(),fixture,100,1))
                self.assertEqual(len(set(hashes)),count)
                parent,child=context.Pipe();frames=context.Queue(2)
                process=context.Process(target=worker_main,args=(child,frames,root,
                    {'mode':mode,'participants':[d['id'] for d in drivers],'epoch':'frozen'}))
                process.start();child.close()
                try:
                    deadline=time.monotonic()+30;finished=False
                    while time.monotonic()<deadline and not finished:
                        if parent.poll(.05):
                            message=parent.recv()
                            self.assertNotEqual(message['type'],'error',message)
                            finished=message['type']=='finished'
                    self.assertTrue(finished,'La sessione congelata non termina')
                    sessions=store.sessions(mode)
                    self.assertEqual(len(sessions),1)
                    payload=sessions[0]['payload']
                    self.assertEqual([p['policy'] for p in payload['participants']],hashes)
                    self.assertEqual(len(payload['results']),count*(5 if mode=='prova' else 1))
                    for driver,digest in zip(drivers,hashes):
                        saved=store.driver(driver['id'])
                        self.assertEqual(saved['policy'],digest)
                        self.assertEqual(saved['steps'],100)
                    # Deliberately poor fixture pilots retire: no finish is invented.
                    for row in payload['results']:
                        if row['status']!='arrivato':
                            self.assertIsNone(row.get('finishTime',row.get('time')))
                finally:
                    if process.is_alive():parent.send({'type':'stop'});process.join(3)
                    if process.is_alive():process.terminate();process.join(2)
                    parent.close();frames.close();process.close()

    def test_real_workers_pause_and_resume(self):
        context=mp.get_context('spawn')
        for method in ('evolution','ppo','neat'):
            with self.subTest(method=method),tempfile.TemporaryDirectory() as root:
                store=GameStore(root);driver=store.drivers()[0]
                store.set_profile(driver['id'],{**driver['profile'],'algorithm':method,'population':8,'rollout':64})
                parent,child=context.Pipe();frames=context.Queue(2)
                process=context.Process(target=worker_main,args=(child,frames,root,{'mode':'impara','driver':driver['id'],'epoch':'test'}))
                process.start();child.close()
                def receive(kind,limit=15):
                    deadline=time.monotonic()+limit
                    while time.monotonic()<deadline:
                        if parent.poll(.05):
                            message=parent.recv()
                            self.assertNotEqual(message['type'],'error',message)
                            if message['type']==kind:return message
                    self.fail('Nessun ack '+kind)
                try:
                    receive('ready');time.sleep(.15)
                    started=time.monotonic();parent.send({'type':'pause'});receive('paused')
                    self.assertLess(time.monotonic()-started,.25)
                    first=receive('saved');self.assertGreater(first['steps'],0)
                    first_checkpoint=store.load(store.driver(driver['id'])['checkpoint'])
                    time.sleep(.05);parent.send({'type':'resume'});receive('ready');time.sleep(.1)
                    parent.send({'type':'pause'});receive('paused');second=receive('saved')
                    self.assertGreaterEqual(second['steps'],first['steps'])
                    second_checkpoint=store.load(store.driver(driver['id'])['checkpoint'])
                    self.assertGreater(second_checkpoint['seconds'],first_checkpoint['seconds'])
                    parent.send({'type':'stop'});process.join(5)
                    self.assertFalse(process.is_alive())
                    self.assertIsNone(store.drivers()[1]['policy'])
                finally:
                    if process.is_alive():process.terminate();process.join(2)
                    parent.close();frames.close();process.close()


if __name__=='__main__':unittest.main()
