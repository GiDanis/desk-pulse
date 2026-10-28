"""Refine an exact recurrent preparation with an isolated SB3 learner."""
from pathlib import Path
import argparse,json,time
import torch
from game_lab.skills import initialize,SkillEnv,export
from game_lab.checkpoint import save,load
from game_lab.artifacts import atomic_report,digest
from game_residual import key

def main():
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--method',choices=('ppo','sac','td3'),required=True);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--decisions',type=int,default=32768);p.add_argument('--family',default='mixed');p.add_argument('--bots',type=int,default=3)
    p.add_argument('--update-every',type=int,choices=(1,2,4),default=1)
    p.add_argument('--steering-retention',type=float);p.add_argument('--actor-rate',type=float)
    p.add_argument('--pedal-retention',type=float)
    p.add_argument('--single-lap',action='store_true')
    p.add_argument('--exploration',choices=('gaussian','sde'))
    p.add_argument('--actuator-mode',choices=('readout','plastic','plastic-context'))
    p.add_argument('--demonstrations',type=Path);p.add_argument('--demonstration-fraction',type=float,default=.25)
    p.add_argument('--capture-every',type=int,default=0,help='Export candidates at completed 128-decision boundaries, without selecting on the final bank.')
    p.add_argument('--seconds',type=float,default=180.);p.add_argument('--resume',type=Path);p.add_argument('--tactic',action='store_true');a=p.parse_args()
    from game_lab.actuators import configure
    if a.decisions<1 or a.capture_every<0 or a.capture_every%128:p.error('Positive budget; capture interval must be a multiple of 128 decisions')
    torch.set_num_threads(1);base=configure(json.loads(a.base.read_text()),a.actuator_mode);a.output.mkdir(parents=True,exist_ok=True)
    contract=dict(backend='sb3-skill-1',baseHash=key(base),method=a.method,seed=a.seed,
        family=a.family,bots=a.bots,duration=a.seconds,singleLap=a.single_lap,features=base['features'],role='tactic' if a.tactic else 'driving',updateEvery=128 if a.method=='ppo' else a.update_every)
    from game_lab.provenance import source_hashes
    import numpy,gymnasium,stable_baselines3
    contract.update(sources=source_hashes(),dependencies=dict(torch=torch.__version__,numpy=numpy.__version__,
        gymnasium=gymnasium.__version__,sb3=stable_baselines3.__version__))
    contract.update(steeringRetention=a.steering_retention if a.steering_retention is not None else (base.get('origin') or {}).get('steeringRetention',25.),
        pedalRetention=a.pedal_retention if a.pedal_retention is not None else (base.get('origin') or {}).get('pedalRetention',.01),
        actorLearningRate=a.actor_rate if a.actor_rate is not None else (base.get('origin') or {}).get('actorLearningRate',.000003),
        explorationStyle=a.exploration if a.exploration is not None else (base.get('origin') or {}).get('explorationStyle','gaussian'),
        actuatorMode=base.get('readoutMode','readout'),criticFeatureContext=base.get('criticFeatureContext','sensors-intent'))
    if a.demonstrations:
        from game_lab.demonstrations import load as load_demonstrations
        _,demo=load_demonstrations(a.demonstrations,base)
        contract['expertReplay']=dict(transitionHash=demo['transitionHash'],fraction=a.demonstration_fraction,
            collectionSeed=demo['seed'],transitions=demo['transitions'])
    if a.resume:
        env=SkillEnv(base,family=a.family,bots=a.bots,duration=a.seconds,single_lap=a.single_lap)
        model,_=load(a.resume,env,contract=contract)
    else:model,env=initialize(base,a.method,seed=a.seed,family=a.family,bots=a.bots,duration=a.seconds,budget=a.decisions,role=contract['role'],update_every=a.update_every,
        steering_retention=a.steering_retention,pedal_retention=a.pedal_retention,actor_rate=a.actor_rate,single_lap=a.single_lap,exploration=a.exploration,
        demonstrations=a.demonstrations,demonstration_fraction=a.demonstration_fraction)
    atomic_report(a.output/'base.json',base);start=time.monotonic();before=model.num_timesteps
    def progress(locals_,globals_):
        if model.num_timesteps%1024==0:print('skill',a.method,a.seed,model.num_timesteps,round(time.monotonic()-start,2),flush=True)
        return True
    captures=[]
    if not a.capture_every:model.learn(a.decisions,reset_num_timesteps=not bool(a.resume),callback=progress)
    else:
        while model.num_timesteps-before<a.decisions:
            remaining=a.decisions-(model.num_timesteps-before)
            model.learn(min(a.capture_every,remaining),reset_num_timesteps=not bool(a.resume) and not captures,callback=progress)
            policy=export(model);path=a.output/'candidates'/('decisions-'+str(model.num_timesteps)+'.json')
            atomic_report(path,policy);captures.append(dict(decisions=model.num_timesteps,policyHash=key(policy),file=str(path.relative_to(a.output))))
            atomic_report(a.output/'captures.json',dict(qualified=False,finalBankUsed=False,candidates=captures))
    candidate=export(model);atomic_report(a.output/'policy.json',candidate)
    manifest=save(model,a.output/('checkpoint-'+str(model.num_timesteps)),method=a.method,contract=contract)
    atomic_report(a.output/'training.json',dict(contract=contract,decisions=model.num_timesteps-before,
        totalDecisions=model.num_timesteps,backendUpdates=model._n_updates,physicsSteps=env.total_physics_steps,
        simulatedSeconds=env.total_physics_steps/60.,episodes=model._episode_num,wallSeconds=time.monotonic()-start,baseHash=key(base),
        policyHash=key(candidate),checkpoint=manifest,capturedCandidates=captures,qualified=False,teacherAtInference=False))

if __name__=='__main__':main()
