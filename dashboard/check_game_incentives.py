"""Task observability, exact shaping, migration and asymmetric gradients."""
from copy import deepcopy
import json,unittest
import numpy as np
from game_residual import profile,features,value_features,learning_potential
from game_residual_trainer import ResidualTrainer
from game_learning import forward,random_weights,ppo_gradient,log_probability
from game_residual_learning import sac_actor_gradient

METHODS=('residual_ppo','residual_sac','residual_td3','residual_tactic')


class IncentiveChecks(unittest.TestCase):
    def test_task_alias_is_visible_only_to_critic(self):
        a=ResidualTrainer(profile(3,'residual_ppo'),'oval-1')
        e=a.episode;x=features(e.world)
        c1=value_features(e,x);e.valid_progress=e.world.track.length/2;c2=value_features(e,x)
        np.testing.assert_array_equal(c1[:90],c2[:90]);self.assertNotEqual(c1[91],c2[91])
        saved=a.learner.checkpoint();b=type(a.learner)(a.profile,saved)
        u,raw,_,_=a.learner.sample(c1[None,:]);v,other,_,_=b.sample(c2[None,:])
        np.testing.assert_array_equal(raw,other);np.testing.assert_array_equal(u,v)
        e.objective='impara_infinito';e.age=59.;c3=value_features(e,x)
        e.age=60.;c4=value_features(e,x);np.testing.assert_array_equal(c3,c4)

    def test_potential_telescopes_and_preserves_terminal_objective(self):
        t=ResidualTrainer(profile(3,'residual_ppo'),'oval-1');gamma=t.spec['gamma']
        for path in ([-.25,-.22,-.05,.06,0.],[-.25,-.10,0.],[-.25,.01,.09,.08,-.04,0.]):
            shaped=sum(gamma**i*(gamma*b-a) for i,(a,b) in enumerate(zip(path,path[1:])))
            self.assertAlmostEqual(shaped,-path[0],places=14)
        # A truncated boundary retains potential; it is not a terminal bonus.
        self.assertNotEqual(gamma*.06-.05,-.05)
        for _ in range(600):t.tick()
        self.assertAlmostEqual(sum(t.episode.term_totals.values()),t.episode.return_total,places=10)
        self.assertNotEqual(t.episode.term_totals['shaping'],0.)

    def test_ppo_value_prior_cancels_shaping_in_bellman_residual(self):
        from game_residual import potential_from_value_features
        t=ResidualTrainer(profile(3,'residual_ppo'),'oval-1')
        for _ in range(120):t.tick()
        obs=value_features(t.episode)[None,:]
        self.assertAlmostEqual(float(potential_from_value_features(obs)[0]),learning_potential(t.episode),places=12)
        t.learner.potential_prior=True
        _,_,_,value=t.learner.sample(obs)
        expected=forward(t.learner.critic,obs,t.learner.hidden,1)[:,0]-potential_from_value_features(obs)
        np.testing.assert_array_equal(value,expected)
        gamma=t.spec['gamma'];phi=-.14;next_phi=.05;reward=.002;v=.03;next_v=.04
        shaped=reward+gamma*next_phi-phi
        self.assertAlmostEqual(shaped+gamma*(next_v-next_phi)-(v-phi),reward+gamma*next_v-v,places=14)
        # Terminal transition has zero next potential and no next value.
        self.assertAlmostEqual(reward-phi-(v-phi),reward-v,places=14)

    def test_all_methods_archive_old_targets_and_keep_actor_champion_rng(self):
        for method in METHODS:
            p=profile(3,method);old=ResidualTrainer({**p,'rewardExperiment':'legacy-1'},'oval-1')
            for _ in range(1600):old.tick()
            c=old.checkpoint(12.);c['sourceCheckpoint']='a'*64;before=deepcopy(c)
            new=ResidualTrainer(p,'oval-1',c)
            self.assertEqual(c,before);np.testing.assert_array_equal(new.learner.actor,old.learner.actor)
            self.assertEqual(new.state['champion'],old.state['champion'])
            self.assertEqual(new.learner.rng.bit_generator.state,old.learner.rng.bit_generator.state)
            self.assertEqual(new.learner.update_index,old.learner.update_index)
            self.assertEqual(new.steps,old.steps);self.assertEqual(new.decisions,old.decisions)
            self.assertEqual(new.state['stats'],old.state['stats'])
            self.assertEqual(new.state['recipeArchives'][-1]['sourceCheckpoint'],'a'*64)
            self.assertEqual(new.spec['version'],'race-residual-4')
            self.assertGreaterEqual(np.exp(new.learner.log_std[0]),new.spec['exploration'][0]-1e-12)
            if method=='residual_ppo':self.assertEqual(len(new.learner.buffer),0)
            else:self.assertEqual(new.learner.count,0);self.assertEqual(new.learner.replay.shape[1],192)
            for _ in range(120):new.tick()
            resumed=ResidualTrainer(p,'oval-1',json.loads(json.dumps(new.checkpoint(13.))))
            self.assertEqual(resumed.state['recipeArchives'],new.state['recipeArchives'])
            for _ in range(150):new.tick();resumed.tick()
            np.testing.assert_array_equal(new.learner.actor,resumed.learner.actor)
            self.assertEqual(new.learner.checkpoint(),resumed.learner.checkpoint())

    def test_asymmetric_gradients_match_finite_differences(self):
        rng=np.random.default_rng(2);h=4;obs=rng.normal(size=(7,94));std=np.log([.1,.15])
        actor=random_weights(rng,h,inputs=90);critic=random_weights(rng,h,1,inputs=94)
        raw=forward(actor,obs[:,:90],h)+rng.normal(size=(7,2))*.1
        logp=log_probability(raw,forward(actor,obs[:,:90],h),std)
        adv=rng.normal(size=7);ret=rng.normal(size=7)
        args=(critic,std,h,obs,raw,logp,adv,ret)
        _,_,ga,_,_=ppo_gradient(actor,*args,actor_inputs=90,critic_inputs=94)
        epsilon=1e-6
        for j in (0,123,len(actor)-1):
            a=actor.copy();b=actor.copy();a[j]+=epsilon;b[j]-=epsilon
            la=ppo_gradient(a,*args,actor_inputs=90,critic_inputs=94)[0]
            lb=ppo_gradient(b,*args,actor_inputs=90,critic_inputs=94)[0]
            self.assertAlmostEqual(ga[j],(la-lb)/(2*epsilon),places=6)
        q1=random_weights(rng,h,1,inputs=96);q2=random_weights(rng,h,1,inputs=96)
        noise=rng.normal(size=(7,2));args=(std,q1,q2,obs,noise,h,.0001)
        _,ga,_=sac_actor_gradient(actor,*args,actor_inputs=90)
        for j in (0,123,len(actor)-1):
            a=actor.copy();b=actor.copy();a[j]+=epsilon;b[j]-=epsilon
            la=sac_actor_gradient(a,*args,actor_inputs=90)[0];lb=sac_actor_gradient(b,*args,actor_inputs=90)[0]
            self.assertAlmostEqual(ga[j],(la-lb)/(2*epsilon),places=6)


if __name__=='__main__':unittest.main()
