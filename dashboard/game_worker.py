"""One on-demand process owns simulation, learning and durable checkpoints."""
from __future__ import annotations

import os
import queue
import sqlite3
from pathlib import Path
import time


def worker_main(command, frames, root, request):
    # These settings apply only to the child, before NumPy loads BLAS.
    os.environ['OPENBLAS_NUM_THREADS']='1'
    os.environ['OMP_NUM_THREADS']='1'
    os.environ['MKL_NUM_THREADS']='1'
    try:
        os.nice(5)
    except OSError:
        pass
    import numpy as np
    from game_catalog import configuration
    from game_store import GameStore
    from game_learning import Evolution, PPO, Policy
    from game_simulation import World, DT, reference_actions
    from game_curriculum import initial_state, pace_weight, Evaluation, consider, REWARD_VERSION, PHASE_LABELS
    from game_catalog import scope_hash

    store=GameStore(root)
    mode=request['mode']
    run=None
    payload={}
    learner=None
    worlds=[]
    driver=None
    paused=False
    stopping=False
    sequence=0
    metric={}
    policy_hash=None
    active_seconds=0.0
    steps=0
    base_steps=base_seconds=0
    trial_age=None
    fitness=None
    update_iterator=None
    session_metric=[]
    generation_started=time.monotonic()
    last_frame=0.0
    last_save=time.monotonic()
    last_resource_check=0.0
    race_deadline=300.0
    policies=[]
    evaluation=[]
    eval_index=0
    eval_scenario=0
    eval_world=None
    countdown=3.0 if mode=='gara' else 0.0
    curriculum=None
    training_evaluation=None
    try:
        if mode=='impara':
            driver=store.driver(request['driver'])
            if not driver:
                raise ValueError('Pilota sconosciuto')
            profile=driver['profile']
            checkpoint=store.load(driver['checkpoint']) if driver['checkpoint'] else None
            backend_checkpoint=checkpoint.get('learner') if checkpoint else None
            if profile['algorithm']=='neat':
                from game_neat import NEAT
                learner=NEAT(profile,backend_checkpoint)
            else:
                learner=(PPO if profile['algorithm']=='ppo' else Evolution)(profile,backend_checkpoint)
            count=profile['population']
            traffic=profile['traffic']
            worlds=[World(2,profile['seed']+i,shared=True) for i in range(count)] if traffic else [World(count,profile['seed'])]
            if checkpoint and checkpoint.get('configuration')!=configuration():
                raise ValueError('Checkpoint fisico incompatibile')
            if checkpoint and checkpoint.get('worlds'):
                for world,saved in zip(worlds,checkpoint['worlds']):world.restore(saved)
            trial_age=np.array(checkpoint['age']) if checkpoint else np.zeros(count)
            fitness=np.array(checkpoint['fitness']) if checkpoint else np.zeros(count)
            steps=checkpoint.get('steps',driver['steps']) if checkpoint else driver['steps']
            active_seconds=checkpoint.get('seconds',driver['seconds']) if checkpoint else driver['seconds']
            base_steps,base_seconds=steps,active_seconds
            curriculum=checkpoint.get('curriculum') if checkpoint else None
            if curriculum is None:curriculum=initial_state(traffic)
            if curriculum.get('rewardVersion')!=REWARD_VERSION:
                raise ValueError('Ricompensa del checkpoint incompatibile')
            pending=curriculum.get('pending')
            if pending:
                training_evaluation=Evaluation(pending['candidate'],pending['champion'],curriculum['round'],traffic,pending)
            if isinstance(learner,PPO) and learner.pending is not None:update_iterator=learner.updates()
            payload={'driver':driver['id'],'profile':profile,'resumed':bool(checkpoint)}
        elif mode in ('gara','prova','campione'):
            identities=request.get('participants',[]) if mode!='campione' else [request['driver']]
            if mode=='gara' and not 2<=len(identities)<=4:
                raise ValueError('Seleziona da due a quattro piloti')
            if not identities or len(set(identities))!=len(identities):
                raise ValueError('Partecipanti non validi')
            participants=[]
            for identity in identities:
                item=store.driver(identity)
                if not item or not item['policy']:
                    raise ValueError('Pilota senza modello salvato')
                policies.append(Policy(store.load(item['policy'])))
                participants.append({'id':identity,'name':item['name'],'number':item['number'],
                                     'policy':item['policy'],'profile':item['policy_profile'] or item['profile']})
            payload={'participants':participants,'rules':{'version':'race-1','laps':3 if mode=='gara' else 1,
                     'contacts':'retirement','limitSeconds':300,'finishWindowSeconds':30},'grid':identities}
            if mode=='prova':
                eval_world=World(1,1)
                eval_world.reset(varied=True)
                worlds=[eval_world]
            else:
                worlds=[World(len(identities),1,shared=mode=='gara',laps=3 if mode=='gara' else 1)]
        else:
            raise ValueError('Modalità sconosciuta')
        run,payload=store.begin_session(mode,payload)
        command.send({'type':'ready','session':request['epoch'],'run':run})

        def save_training():
            nonlocal policy_hash,last_save
            if learner is None:
                return
            saved_learner=learner.checkpoint()
            checkpoint={'schema':1,'configuration':configuration(),'learner':saved_learner,
                        'worlds':[world.snapshot() for world in worlds],
                        'age':trial_age.tolist(),'fitness':fitness.tolist(),'steps':steps,
                        'seconds':active_seconds,'partialUpdate':update_iterator is not None}
            curriculum['pending']=training_evaluation.snapshot() if training_evaluation else None
            checkpoint['curriculum']=curriculum
            policy_hash=store.save_training(driver['id'],checkpoint,learner.policy(),steps,active_seconds,metric,curriculum)
            last_save=time.monotonic()
            command.send({'type':'saved','session':request['epoch'],'policy':policy_hash,'steps':steps})

        def schedule_evaluation():
            nonlocal training_evaluation
            curriculum['updates']+=1
            old_weight=pace_weight(curriculum)
            curriculum['phaseUpdates']+=1
            candidate=learner.candidate_policy() if hasattr(learner,'candidate_policy') else learner.policy()
            if old_weight!=pace_weight(curriculum) and hasattr(learner,'change_reward'):learner.change_reward()
            interval=8 if isinstance(learner,PPO) else 5
            if (curriculum['updates']-1)%interval==0:
                curriculum['round']+=1
                champion=curriculum['champion']
                training_evaluation=Evaluation(candidate,champion['policy'] if champion else None,
                                               curriculum['round'],traffic)

        def reset_training_worlds():
            for world in worlds:world.reset()
            trial_age[:]=0;fitness[:]=0

        def send_frame():
            nonlocal sequence,last_frame
            sequence+=1
            if mode=='impara':
                rows=([w.rows()[0] for w in worlds] if traffic else worlds[0].rows())
                for i,row in enumerate(rows):
                    row.update(id=str(i),name=driver['name'],number=i+1,driverId=driver['id'])
                if training_evaluation:
                    rows=([w.rows()[0] for w in training_evaluation.worlds] if traffic else
                          [row for world in training_evaluation.worlds for row in world.rows()])
                    for i,row in enumerate(rows):
                        row.update(id='eval-'+str(i),name=driver['name']+(' · candidato' if i<10 else ' · campione'),
                                   number=i%10+1,driverId=driver['id'])
                selected=request.get('selected',0)%len(rows)
                visible=rows[:7]
                if selected>=7:visible.append(rows[selected])
                else:visible=rows[:8]
                if training_evaluation:
                    obs=training_evaluation.worlds[selected].observations()[0] if traffic else training_evaluation.worlds[selected//10].observations()[selected%10]
                else:obs=worlds[selected].observations()[0] if traffic else worlds[0].observations()[selected]
                meta={'driverName':driver['name'],'algorithm':profile['algorithm'],'count':len(rows),
                      'steps':steps,'seconds':active_seconds,'metric':metric,'selected':selected,
                      'phase':'valutazione' if training_evaluation else 'aggiornamento' if update_iterator is not None else 'raccolta',
                      'curriculumPhase':PHASE_LABELS[curriculum['phase']],
                      'evaluationRound':curriculum['round']}
            else:
                if mode=='prova':
                    visible=worlds[0].rows([payload['participants'][min(eval_index,len(policies)-1)]['id']])
                    visible[0].update(name=payload['participants'][min(eval_index,len(policies)-1)]['name'],number=payload['participants'][min(eval_index,len(policies)-1)]['number'])
                else:
                    visible=worlds[0].rows([row['id'] for row in payload['participants']])
                    for row,person in zip(visible,payload['participants']):row.update(name=person['name'],number=person['number'])
                obs=worlds[0].observations()[request.get('selected',0)%len(visible)]
                meta={'count':len(visible),'selected':request.get('selected',0)%len(visible),
                      'phase':'partenza' if countdown>0 else 'gara' if mode=='gara' else 'prova','time':worlds[0].time,
                      'countdown':int(np.ceil(countdown)),
                      'evaluationIndex':eval_index*5+eval_scenario+1,'evaluationTotal':len(policies)*5}
            packet={'session':request['epoch'],'sequence':sequence,'mode':mode,'cars':visible,
                    'sensors':obs[:5].tolist(),'meta':meta,'engine':'CPU'}
            try:frames.put_nowait(packet)
            except queue.Full:pass
            last_frame=time.monotonic()

        def pause_worker(reason=''):
            nonlocal paused
            paused=True
            command.send({'type':'paused','session':request['epoch'],'message':reason})
            try:
                store.finish_session(run,'paused',payload)
                save_training()
            except (OSError,ValueError,sqlite3.Error) as error:
                command.send({'type':'save_failed','session':request['epoch'],'message':str(error)})

        while not stopping:
            now=time.monotonic()
            while command.poll():
                message=command.recv()
                if message['type']=='pause':
                    pause_worker()
                elif message['type']=='resume':
                    paused=False
                    store.finish_session(run,'running',payload)
                    generation_started=time.monotonic()
                    command.send({'type':'ready','session':request['epoch'],'run':run})
                elif message['type']=='stop':stopping=True
                elif message['type']=='select':request['selected']=message['index']
                elif message['type']=='save':
                    try:save_training()
                    except (OSError,ValueError,sqlite3.Error) as error:command.send({'type':'save_failed','session':request['epoch'],'message':str(error)})
            if stopping:break
            if not paused and now-last_resource_check>=2:
                last_resource_check=now
                try:
                    cpu_temperatures=[float((zone/'temp').read_text())/1000 for zone in Path('/sys/class/thermal').glob('thermal_zone*')
                                      if (zone/'type').read_text().strip().lower().startswith('cpu')]
                    memory={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines()}
                    if cpu_temperatures and max(cpu_temperatures)>=85:pause_worker('Temperatura alta · sessione in pausa')
                    elif memory.get('MemAvailable',2**30)<128*1024:pause_worker('Memoria disponibile insufficiente · sessione in pausa')
                except (OSError,ValueError):pass
            if paused:
                command.poll(0.01)
                continue
            if countdown>0:
                countdown=max(0,countdown-(time.monotonic()-generation_started))
                generation_started=time.monotonic()
                if now-last_frame>=1/25:send_frame()
                command.poll(0.01)
                continue
            if mode=='impara':
                if training_evaluation is not None:
                    started_eval=time.monotonic()
                    ended_eval=training_evaluation.step()
                    curriculum['evaluationSeconds']=curriculum.get('evaluationSeconds',0)+time.monotonic()-started_eval
                    if ended_eval:
                        result,old_result=training_evaluation.results()
                        _,changed,proof=consider(curriculum,training_evaluation.candidate,result,old_result,
                                                 training_evaluation.scenarios,scope_hash(),profile)
                        training_evaluation=None
                        if changed:
                            if hasattr(learner,'change_reward'):learner.change_reward()
                            # At this boundary PPO has no unfinished update. Drop
                            # experiences from the previous objective and reset the
                            # critic/optimizer while keeping the actor and RNG.
                            if isinstance(learner,PPO):
                                from game_learning import Adam,random_weights
                                learner.buffer=[]
                                learner.critic=random_weights(learner.rng,learner.hidden,1)
                                learner.critic_adam=Adam(len(learner.critic))
                            reset_training_worlds()
                        save_training()
                elif update_iterator is not None:
                    try:metric=next(update_iterator)
                    except StopIteration:
                        update_iterator=None
                        schedule_evaluation()
                        save_training()
                else:
                    observations=np.array([w.observations()[0] for w in worlds]) if traffic else worlds[0].observations()
                    if isinstance(learner,PPO):
                        actions,raw,logp,values=learner.sample(observations)
                    else:actions=learner.act(observations)
                    if traffic:
                        rewards=[];done=[]
                        for i,world in enumerate(worlds):
                            bot=reference_actions(world)[1]
                            bot[1]=np.clip((7-world.state[1,3])*0.3,-1,1)
                            _,r,d=world.step(np.array([actions[i],bot]),pace=pace_weight(curriculum))
                            rewards.append(r[0]);done.append(d[0])
                        rewards,done=np.array(rewards),np.array(done)
                        next_obs=np.array([w.observations()[0] for w in worlds])
                    else:next_obs,rewards,done=worlds[0].step(actions,pace=pace_weight(curriculum))
                    alive=trial_age<profile['episodeSeconds']
                    fitness+=rewards*alive
                    trial_age+=DT
                    done |= trial_age>=profile['episodeSeconds']
                    steps+=len(observations)
                    if isinstance(learner,PPO):
                        learner.remember(observations,raw,logp,values,rewards,done,next_obs)
                        if traffic:
                            for i,world in enumerate(worlds):
                                if done[i]:world.reset();trial_age[i]=0;fitness[i]=0
                        else:
                            worlds[0].reset_trials(done);trial_age[done]=0;fitness[done]=0
                        if len(learner.buffer)>=profile['rollout']:update_iterator=learner.updates()
                    elif done.all():
                        metric=learner.update(fitness)
                        session_metric.append({**metric,'steps':steps})
                        if traffic:
                            for world in worlds:world.reset()
                        else:
                            worlds[0].reset()
                            # Identical start perturbation for every candidate in this generation.
                            dy,da=worlds[0].rng.uniform(-0.7,0.7),worlds[0].rng.uniform(-0.08,0.08)
                            worlds[0].state[:,1]+=dy;worlds[0].state[:,2]+=da
                        trial_age[:]=0;fitness[:]=0
                        payload['metrics']=session_metric[-100:]
                        schedule_evaluation()
                        if time.monotonic()-last_save>=30:save_training()
                active_seconds += max(0,time.monotonic()-generation_started)
                generation_started=time.monotonic()
                if time.monotonic()-last_save>30:save_training()
            else:
                world=worlds[0]
                if mode=='prova':actions=policies[eval_index].act(world.observations())
                else:actions=np.array([p.act(o) for p,o in zip(policies,world.observations())])
                world.step(actions)
                if mode=='gara' and np.isfinite(world.finish).any():
                    race_deadline=min(race_deadline,float(np.nanmin(world.finish))+30)
                ended=not world.active.any() or world.time>=(60 if mode=='prova' else race_deadline)
                if ended:
                    timed_out=world.active.copy()
                    if mode=='prova':
                        row=world.rows()[0]
                        if timed_out[0]:row['status']='tempo scaduto'
                        evaluation.append({'driver':payload['participants'][min(eval_index,len(policies)-1)]['id'],
                                           'policy':payload['participants'][eval_index]['policy'],
                                           'scenario':eval_scenario,'time':row['finishTime'],
                                           'progress':row['progress'],'status':row['status']})
                        eval_scenario+=1
                        if eval_scenario==5:eval_scenario=0;eval_index+=1
                        if eval_index<len(policies):
                            worlds[0]=World(1,eval_scenario+1);worlds[0].reset(varied=True)
                            continue
                        payload['results']=evaluation
                    else:
                        payload['results']=world.rows([x['id'] for x in payload['participants']])
                        for i,row in enumerate(payload['results']):
                            if timed_out[i]:row['status']='tempo scaduto'
                        payload['events']=world.events
                    send_frame()
                    store.finish_session(run,'complete',payload)
                    command.send({'type':'finished','session':request['epoch'],'run':run})
                    paused=True
                else:
                    # Races/campione are watched in real time, never frame-dependent.
                    remaining=DT-(time.monotonic()-generation_started)
                    if mode!='prova' and remaining>0:command.poll(remaining)
                    generation_started=time.monotonic()
            if time.monotonic()-last_frame>=1/25:send_frame()
        if learner and not paused:save_training()
        if store.sessions(mode,False) and not any(x['id']==run and x['status']=='complete' for x in store.sessions(mode,False)):
            store.finish_session(run,'interrupted',payload)
    except BaseException as error:
        if run:
            try:store.finish_session(run,'failed',{**payload,'error':str(error)})
            except Exception:pass
        try:command.send({'type':'error','session':request['epoch'],'message':str(error)})
        except (BrokenPipeError,EOFError,OSError):pass
    finally:
        command.close()
        frames.cancel_join_thread()
