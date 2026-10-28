"""Episode-separated expert/DAgger collection; explicit jobs, never at import."""
from pathlib import Path
import json,time
import numpy as np
from game_lab.environment import RacingEnv
from game_lab.teacher import Teacher
from game_direct import features,FEATURES

FAMILIES=('solo','traffic','attack','complete','corner','defend','recover')


def collect(output,*,seed=1,episodes=42,duration=90.,actor=None,split='train',round_number=0,families=FAMILIES,bot_counts=(1,2,3),noise=0.,feature_version=FEATURES,intervention=0.,stop_unsafe=False):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed);rows=[];samples=0;started=time.monotonic()
    report=dict(version='causal-driving-sequences-2',seed=seed,split=split,round=round_number,
        teacherVersion=Teacher.VERSION,noise=noise,interventionThreshold=intervention,stopAtFirstUnsafe=stop_unsafe,
        collector=('perturbed-teacher' if noise else 'teacher') if actor is None else 'learner-with-offline-interventions' if intervention else 'learner-with-private-teacher-labels',rows=rows)
    for number in range(episodes):
        family=families[number%len(families)];bots=bot_counts[number//len(families)%len(bot_counts)]
        s=int(rng.integers(1,2**31-1))
        while 980000<=s<=990000 or 1980000<=s<=1990000:s=int(rng.integers(1,2**31-1))
        env=RacingEnv(family=family,bots=bots,duration=duration,feature_version=feature_version)
        observation,_=env.reset(seed=s);teacher=Teacher();state=None;x=[];y=[];rewards=[];next_x=[];applied=[];terminals=[];truncations=[];first_unsafe=None;intents=[];perturb=np.zeros(2);proposals=[];interventions=[];hold=0
        while True:
            z=features(env.episode.world,version=feature_version).copy()
            label=teacher.label(env.episode.world)
            x.append(z);y.append(label);intents.append(teacher.last_intent)
            if actor is None:
                if noise:
                    if len(x)%5==1:perturb=rng.normal(size=2)*np.array([noise,5*noise])
                    command=np.clip(label+perturb,-1,1)
                else:command=label
            else:
                import torch
                with torch.no_grad():
                    action,state=actor(torch.as_tensor(z[None,None,:],dtype=torch.float32),state)
                    command=action[0,-1].numpy()
            proposals.append(np.asarray(command).copy())
            if actor is not None and intervention:
                if abs(command[0]-label[0])>intervention or abs(command[1]-label[1])>.1:hold=10
                intervened=hold>0
                if intervened:command=label;hold-=1
            else:intervened=False
            interventions.append(intervened)
            observation,reward,terminal,truncated,info=env.step(command);rewards.append(reward)
            next_x.append(observation.copy());applied.append(np.asarray(command).copy());terminals.append(terminal);truncations.append(truncated)
            if first_unsafe is None and (info['contacts'] or info['trackLimits']>(1 if family=='recover' else 0)):first_unsafe=len(x)
            if terminal or truncated or (stop_unsafe and first_unsafe is not None):break
        path=output/f'{split}-{seed}-{round_number}-{number:04}.npz'
        temporary=path.with_suffix('.npz.tmp')
        with temporary.open('wb') as stream:
            np.savez_compressed(stream,x=np.asarray(x,dtype=np.float32),y=np.asarray(y,dtype=np.float32),
            featureVersion=feature_version,rewards=np.asarray(rewards),seed=s,split=split,family=family,teacherCalls=teacher.calls,
            u=np.asarray(applied,dtype=np.float32),proposed=np.asarray(proposals,dtype=np.float32),interventions=np.asarray(interventions),next_x=np.asarray(next_x,dtype=np.float32),
            terminated=np.asarray(terminals),truncated=np.asarray(truncations),teacherVersion=Teacher.VERSION,round=round_number,actorDriven=actor is not None or noise>0,collector=report['collector'],intent=np.asarray(intents,dtype=np.float32),noise=noise,firstUnsafeDecision=-1 if first_unsafe is None else first_unsafe,censoredAtUnsafe=bool(stop_unsafe and first_unsafe is not None))
        temporary.replace(path)
        samples+=len(x);result=env.episode.result()
        rows.append(dict(file=path.name,family=family,bots=bots,seed=s,samples=len(x),interventions=sum(interventions),result=result,censoredAtUnsafe=bool(stop_unsafe and first_unsafe is not None)))
        report.update(samples=samples,wallSeconds=time.monotonic()-started)
        from game_lab.artifacts import atomic_report
        atomic_report(output/f'collection-{split}-{seed}-{round_number}.json',report)
        print('collection',split,seed,round_number,number,family,bots,result['passes'],result['contacts'],result['trackLimits'],flush=True)
    return report


def load_sequences(root,split='train'):
    result=[];outcomes={}
    for path in Path(root).glob('collection-'+split+'-*.json'):
        for row in json.loads(path.read_text())['rows']:outcomes[row['file']]=row
    for path in sorted(Path(root).glob(split+'-*.npz')):
        with np.load(path,allow_pickle=False) as f:
            if str(f['split'])!=split:raise ValueError('Split mismatch')
            row=outcomes.get(path.name,{});r=row.get('result',{})
            clean=bool(r and not r.get('contacts') and r.get('trackLimits',99)<=(1 if str(f['family'])=='recover' else 0))
            # Failed oracle demonstrations remain evidence, not training labels.
            # DAgger failures still carry oracle corrections at learner states.
            if not bool(f['actorDriven']) and not clean:continue
            end=int(f['firstUnsafeDecision']) if 'firstUnsafeDecision' in f and int(f['firstUnsafeDecision'])>=0 and bool(f['actorDriven']) else len(f['x'])
            result.append(dict(x=f['x'][:end].copy(),y=f['y'][:end].copy(),u=f['u'][:end].copy() if 'u' in f else f['y'][:end].copy(),source=path.name,seed=int(f['seed']),
                proposed=f['proposed'][:end].copy() if 'proposed' in f else (f['u'] if 'u' in f else f['y'])[:end].copy(),family=str(f['family']),
                featureVersion=str(f['featureVersion']) if 'featureVersion' in f else FEATURES,rolloutClean=clean,
                teacherClean=clean and (str(f['collector']) in ('teacher','perturbed-teacher') if 'collector' in f else not bool(f['actorDriven']) or ('noise' in f and float(f['noise'])>0)),
                intent=f['intent'][:end].copy() if 'intent' in f else None))
    return result
