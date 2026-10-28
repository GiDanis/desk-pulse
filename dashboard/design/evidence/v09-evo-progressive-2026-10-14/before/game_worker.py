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
        os.setpriority(os.PRIO_PROCESS, 0, 10)
    except OSError:
        try:
            os.nice(15)
        except OSError:
            pass
    import numpy as np
    from game_catalog import configuration, observation_version, ACADEMY_OBSERVATION_VERSION
    from game_store import GameStore
    from game_learning import Evolution, PPO, Policy
    from game_simulation import World, DT
    from game_curriculum import initial_state, pace_weight, Evaluation, consider, REWARD_VERSION, PHASE_LABELS
    from game_catalog import scope_hash, race_eligible, reference_ready,race_cohort
    from game_protocol import training_task, race_budget, TRIAL_PROTOCOL
    from game_control import pursuit_actions,frozen_actions

    from game_modes import learning, CONTINUOUS, grid_order, qualified_snapshot
    from copy import deepcopy
    track_id=request.get('track','oval-1')
    store=GameStore(root,track_id)
    config=configuration(track_id)
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
    next_frame=time.monotonic()
    race_next_tick=0.0
    last_save=time.monotonic()
    last_resource_check=0.0
    last_yield=time.monotonic()
    race_deadline=300.0
    policies=[]
    evaluation=[]
    eval_index=0
    eval_world=None
    countdown=3.0 if mode=='gara' else 0.0
    curriculum=None
    training_evaluation=None
    preview=None
    academy=None
    saved_evaluation_round=0
    preview_tick=time.monotonic()
    try:
        if (learning(mode) and request.get('academy',True)) or (mode=='campione' and request.get('academy',False)):
            store.activate_academy(request['driver'])
            if request.get('drivingMemory',True):store.prepare_driving(request['driver'])
        if learning(mode) and (store.driver(request['driver']) or {}).get('profile',{}).get('algorithm')=='pure_pursuit':raise ValueError('Il riferimento non apprende: scegli Qualifica o Gara')
        if learning(mode):
            driver=store.driver(request['driver'])
            if not driver:
                raise ValueError('Pilota sconosciuto')
            profile=driver['profile']
            config=configuration(track_id,profile['observation'])
            checkpoint=store.load(driver['checkpoint']) if driver['checkpoint'] else None
            if mode in CONTINUOUS:
                local=store.objective_checkpoint(driver['id'],mode)
                if local is not None:checkpoint=local
                else:
                    # Preserve actor/topology and RNG; task-specific optimizer state must not leak.
                    from game_academy import upgrade_learner
                    backend=upgrade_learner(checkpoint,profile) if checkpoint else None
                    checkpoint=dict(configuration=config,protocol='driving-memory-1',memory=deepcopy((checkpoint or {}).get('memory',{})),learner=backend,steps=0,seconds=0)
                    checkpoint['memory']['fresh']=False
                store.select_objective(mode)
                driver=store.driver(request['driver'])
            if profile.get('version')==2:
                from game_academy_trainer import AcademyTrainer
                opponents=[Policy(store.load(p['policy'])) for p in store.drivers()
                           if p['id']!=driver['id'] and p['policy'] and (p['policy_profile'] or {}).get('version')==2
                           and race_eligible(p,track_id,4)]
                if checkpoint and not checkpoint.get('sourceCheckpoint'):
                    checkpoint={**checkpoint,'sourceCheckpoint':driver['checkpoint']}
                academy=AcademyTrainer(profile,track_id,checkpoint,opponents,objective=mode,view=request.get('view','pilot'),bots=request.get('bots',2),balanced=True,batched=True)
                if mode in CONTINUOUS and not academy.state.get('objective'):
                    academy.state.update(phase='overtake' if mode=='impara_sorpasso' else 'control',objective=mode)
                    academy.review=academy.evaluation=None;academy.reset_episodes()
                from game_parallel import recommended_collectors
                collectors=request.get('collectors',recommended_collectors(profile,track_id,mode))
                if collectors:academy.enable_collectors(min(4,int(collectors)),persistent=True)
                learner=academy.learner;curriculum=academy.state
                task=academy.task;steps=academy.steps
                active_seconds=checkpoint.get('seconds',0) if checkpoint else 0
                base_steps,base_seconds=steps,active_seconds
                payload={'driver':driver['id'],'profile':profile,'resumed':bool(checkpoint),
                         'task':task,'academy':academy.protocol or 'academy-1','memory':academy.memory,'training':{'steps':0,'seconds':0},
                         'rewardSpec':deepcopy(academy.reward_spec),'rewardMigration':deepcopy(academy.migration),
                         'sourceCheckpoint':academy.source_checkpoint,'execution':deepcopy(academy.state.get('execution',{})),
                         'frozenOpponents':[p.snapshot for p in opponents]}
            else:
                backend_checkpoint=checkpoint.get('learner') if checkpoint else None
                if profile['algorithm']=='neat':
                    from game_neat import NEAT
                    learner=NEAT(profile,backend_checkpoint)
                elif profile['algorithm']=='pure_pursuit':
                    from game_learning import PurePursuit
                    learner=PurePursuit(profile,backend_checkpoint)
                elif profile['algorithm']=='imitation':
                    from game_learning import Imitation
                    learner=Imitation(profile,backend_checkpoint)
                elif profile['algorithm']=='ppo_smooth':
                    from game_learning import PPOSmooth
                    learner=PPOSmooth(profile,backend_checkpoint)
                else:
                    learner=(PPO if profile['algorithm']=='ppo' else Evolution)(profile,backend_checkpoint)
                initializer=store.initializer(driver['id']) if not checkpoint else None
                if initializer:
                    weights=np.asarray(initializer['weights'])
                    if isinstance(learner,PPO):learner.actor=weights.copy()
                    elif isinstance(learner,Evolution):
                        learner.best=weights.copy();learner.population[:max(2,len(learner.population)//4)]=weights
                    elif hasattr(learner,'weights'):
                        learner.weights=weights.copy();learner.best=weights.copy()
                    else:raise ValueError('Trasferimento non supportato da questo metodo')
                count=profile['population']
                traffic=profile['traffic']
                saved_curriculum=checkpoint.get('curriculum') if checkpoint else None
                task=training_task(track_id,(saved_curriculum or {}).get('phase','control'),profile['episodeSeconds'])
                training_laps=task['laps']
                worlds=[World(2,profile['seed']+i,shared=True,laps=training_laps,track_id=track_id) for i in range(count)] if traffic else [World(count,profile['seed'],laps=training_laps,track_id=track_id)]
                if checkpoint and checkpoint.get('configuration')!=config:
                    raise ValueError('Checkpoint fisico incompatibile')
                if checkpoint and checkpoint.get('worlds'):
                    compatible=all(saved.get('laps')==training_laps for saved in checkpoint['worlds'])
                    if compatible:
                        for world,saved in zip(worlds,checkpoint['worlds'],strict=True):world.restore(saved)
                    else:
                        checkpoint={**checkpoint,'age':[0.]*count,'fitness':[0.]*count}
                        if isinstance(learner,PPO):learner.buffer=[];learner.pending=None
                        payload['taskMigration']='Nuovo episodio; pesi e contatori conservati'
                trial_age=np.array(checkpoint['age']) if checkpoint else np.zeros(count)
                fitness=np.array(checkpoint['fitness']) if checkpoint else np.zeros(count)
                steps=checkpoint.get('steps',driver['steps']) if checkpoint else driver['steps']
                active_seconds=checkpoint.get('seconds',driver['seconds']) if checkpoint else driver['seconds']
                base_steps,base_seconds=steps,active_seconds
                curriculum=checkpoint.get('curriculum') if checkpoint else None
                if curriculum is None:curriculum=initial_state(traffic)
                if curriculum.get('rewardVersion') in ('control-pace-1','control-pace-2'):
                    curriculum['rewardVersion']=REWARD_VERSION
                    if isinstance(learner,PPO):
                        from game_learning import Adam,random_weights
                        learner.buffer=[];learner.pending=None
                        learner.critic=random_weights(learner.rng,learner.hidden,1,inputs=learner.inputs)
                        learner.critic_adam=Adam(len(learner.critic))
                        learner.actor_adam=Adam(len(learner.actor));learner.std_adam=Adam(2)
                        for i,world in enumerate(worlds):world.episode_time[:]=trial_age[i] if traffic else trial_age
                    payload['rewardMigration']='control-pace-3; actor preserved'
                elif curriculum.get('rewardVersion')!=REWARD_VERSION:
                    raise ValueError('Ricompensa del checkpoint incompatibile')
                pending=curriculum.get('pending')
                if pending and pending.get('version')!=__import__('game_curriculum').EVALUATION_VERSION:
                    curriculum['pending']=None;pending=None
                if pending:
                    training_evaluation=Evaluation(pending['candidate'],pending['champion'],curriculum['round'],traffic,pending,track_id)
                if isinstance(learner,PPO) and learner.pending is not None:update_iterator=learner.updates()
                if isinstance(learner,PPO):
                    from game_preview import PracticePreview
                    preview=PracticePreview(profile['seed'],track_id)
                payload={**payload,'driver':driver['id'],'profile':profile,'resumed':bool(checkpoint),'task':task,
                         'training':{'steps':0,'seconds':0}}
        elif mode in ('gara','prova','campione','qualifica'):
            identities=request.get('participants',[]) if mode not in ('campione','qualifica') else [request['driver']]
            if mode=='gara':identities=[d['id'] for d,c in grid_order([store.driver(i) for i in identities],track_id,request.get('grid','fastest_first'))]
            if mode=='qualifica':store.select_objective(request.get('trainingSource','impara'))
            if mode=='gara' and not 2<=len(identities)<=4:
                raise ValueError('Seleziona da due a quattro piloti')
            if not identities or len(set(identities))!=len(identities):
                raise ValueError('Partecipanti non validi')
            participants=[]
            for identity in identities:
                item=store.driver(identity)
                if not item:raise ValueError('Pilota sconosciuto')
                cert=qualified_snapshot(item,track_id) if mode=='gara' else None
                policy_hash=cert['policy'] if cert else (item.get('candidate') or item.get('policy')) if mode=='qualifica' else item.get('policy')
                policy_profile=cert['profile'] if cert else (item['profile'] if mode=='qualifica' and item.get('candidate') else item['policy_profile'] or item['profile'])
                if mode=='qualifica' and item['profile']['algorithm']=='pure_pursuit':
                    from game_profiles import reference_policy
                    from game_academy import academy_profile
                    policy_hash=store.artifact(reference_policy(track_id,academy=True));policy_profile=academy_profile(item['profile'])
                if not policy_hash:
                    raise ValueError('Pilota senza modello salvato')
                if mode=='gara' and not race_eligible(item,track_id,len(identities)):
                    raise ValueError('Pilota da qualificare su questo circuito')
                policies.append(Policy(store.load(policy_hash)))
                participants.append({'id':identity,'name':item['name'],'number':item['number'],
                                     'policy':policy_hash,'profile':policy_profile, 'qualifyingTime':cert['bestLap'] if cert else None})
            laps=4 if mode=='qualifica' else request.get('laps',3) if mode in ('gara','prova') else 1
            versions={p.snapshot['observation']==ACADEMY_OBSERVATION_VERSION for p in policies}
            if len(versions)!=1:raise ValueError('Schiera versioni qualificate con la stessa fisica')
            cohort=next(iter(versions))
            modern=[cohort]*len(policies)
            sensor_version=observation_version(max(p.inputs for p in policies))
            config=configuration(track_id,sensor_version)
            physics=config['physics']
            if mode in ('gara','prova') and (type(laps) is not int or laps not in (3,5,10)):raise ValueError('Giri non validi')
            payload={'participants':participants,'profile':{'observation':sensor_version},'trialProtocol':TRIAL_PROTOCOL if mode=='prova' else None,'rules':{'version':'race-4' if modern[0] else 'race-2' if track_id=='oval-1' else 'race-3','laps':laps,
                     'grid':'staggered-6m-v2' if modern[0] else 'paired-7m-v1' if track_id=='oval-1' else 'staggered-4m-v1',
                     'contacts':'impulse-1' if modern[0] else 'retirement','limitSeconds':race_budget(track_id,laps),'finishWindowSeconds':30},'grid':identities,'gridOrder':request.get('grid','fastest_first'),'qualificationProtocol':'flying-lap-1' if mode=='qualifica' else None}
            race_deadline=payload['rules']['limitSeconds']
            if mode=='prova':
                eval_world=World(1,1,laps=laps,track_id=track_id,physics=physics,telemetry=True)
                eval_world.reset(varied=False)
                worlds=[eval_world]
            else:
                worlds=[World(len(identities),1,shared=mode=='gara',laps=laps,track_id=track_id,physics=physics,telemetry=True)]
                if mode=='qualifica':worlds[0].reset(varied=False)
                if mode=='gara' and worlds[0].track.oval and not modern[0]:worlds[0].progress[:]=worlds[0].state[:,0]
        else:
            raise ValueError('Modalità sconosciuta')
        run,payload=store.begin_session(mode,payload)
        persisted_laps=0
        simulation_anchor=time.monotonic();simulation_time_anchor=0.
        race_next_tick=simulation_anchor
        command.send({'type':'ready','session':request['epoch'],'run':run})

        def save_training():
            nonlocal policy_hash,last_save
            if learner is None:
                return
            if academy is not None:
                checkpoint=academy.checkpoint(active_seconds)
                payload['task']=academy.task
                payload['training']={'steps':academy.steps-base_steps,'seconds':active_seconds-base_seconds}
                candidate=learner.candidate_policy() if hasattr(learner,'candidate_policy') else learner.policy()
                policy_hash=store.save_training(driver['id'],checkpoint,candidate,academy.steps,
                    active_seconds,academy.metric,academy.state,session=run,session_stats=payload['training'])
                last_save=time.monotonic()
                command.send({'type':'saved','session':request['epoch'],'policy':policy_hash,'steps':academy.steps})
                return
            saved_learner=learner.checkpoint()
            checkpoint={'schema':1,'configuration':config,'learner':saved_learner,
                        'worlds':[world.snapshot() for world in worlds],
                        'age':trial_age.tolist(),'fitness':fitness.tolist(),'steps':steps,
                        'seconds':active_seconds,'partialUpdate':update_iterator is not None,'task':task}
            curriculum['pending']=training_evaluation.snapshot() if training_evaluation else None
            checkpoint['curriculum']=curriculum
            payload['training']={'steps':steps-base_steps,'seconds':active_seconds-base_seconds}
            payload['task']=task
            policy_hash=store.save_training(driver['id'],checkpoint,learner.policy(),steps,active_seconds,metric,curriculum,
                                           session=run,session_stats=payload['training'])
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
                                               curriculum['round'],traffic,track_id=track_id,laps=training_task(track_id,curriculum['phase'])['laps'])

        def reset_training_worlds():
            nonlocal worlds,task
            task=training_task(track_id,curriculum['phase'],profile['episodeSeconds'])
            count=profile['population']
            worlds=[World(2,profile['seed']+i,shared=True,laps=task['laps'],track_id=track_id) for i in range(count)] if traffic else [World(count,profile['seed'],laps=task['laps'],track_id=track_id)]
            trial_age[:]=0;fitness[:]=0

        def send_frame():
            nonlocal sequence,last_frame,preview_tick,next_frame
            sequence+=1
            if learning(mode):
                if academy is not None:
                    visible,obs,meta=academy.frame(driver['name'],driver['number'],request.get('selected',0),paused)
                    meta['seconds']=active_seconds
                else:
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
                    if preview is not None:
                        tick=time.monotonic()
                        preview.advance(tick-preview_tick,Policy(learner.policy()))
                        preview_tick=tick
                        visible=preview.world.rows(['preview'])
                        visible[0].update(name=driver['name'],number=driver['number'],driverId=driver['id'])
                        obs=preview.world.observations()[0]
                        meta.update(count=1,selected=0,trainingCount=profile['population'],presentation='preview',
                                    previewState=preview.status,time=preview.world.time)
            else:
                if mode=='prova':
                    visible=worlds[0].rows([payload['participants'][min(eval_index,len(policies)-1)]['id']])
                    visible[0].update(name=payload['participants'][min(eval_index,len(policies)-1)]['name'],number=payload['participants'][min(eval_index,len(policies)-1)]['number'])
                else:
                    visible=worlds[0].rows([row['id'] for row in payload['participants']])
                    for row,person in zip(visible,payload['participants']):row.update(name=person['name'],number=person['number'])
                obs=worlds[0].observations(version=__import__('game_catalog').observation_version(max(p.inputs for p in policies)))[request.get('selected',0)%len(visible)]
                meta={'count':len(visible),'selected':request.get('selected',0)%len(visible),
                      'laps':worlds[0].laps,
                      'phase':'partenza' if countdown>0 else 'gara' if mode=='gara' else 'prova','time':worlds[0].time,
                      'countdown':int(np.ceil(countdown)),
                      'sensorRange':150 if modern[0] else 50,'physics':physics,
                      'simRate':(worlds[0].time-simulation_time_anchor)/max(.001,time.monotonic()-simulation_anchor),
                      'qualificationLaps':worlds[0].lap_times[0][1:] if mode=='qualifica' else [],
                      'evaluationIndex':eval_index+1,'evaluationTotal':len(policies)}
            if not learning(mode):
                for row in visible:row['simRate']=meta.get('simRate')
            packet={'timestamp':time.monotonic(),'session':request['epoch'],'sequence':sequence,'mode':mode,'cars':visible,
                    'sensors':obs[:5].tolist(),'meta':meta,'engine':'CPU','trackId':track_id}
            try:frames.put_nowait(packet)
            except queue.Full:
                try:frames.get_nowait();frames.put_nowait(packet)
                except (queue.Full,queue.Empty):pass
            # Short NumPy calls can repeatedly reacquire the GIL and starve
            # multiprocessing.Queue's feeder. Yield at the publication boundary
            # so queued scenes reach the GUI even during accelerated evaluation.
            time.sleep(0.001)
            last_frame=time.monotonic()
            next_frame+=1/30
            if next_frame<=last_frame:next_frame=last_frame+1/30

        def pause_worker(reason=''):
            nonlocal paused
            if academy is not None:academy.quiesce()
            paused=True
            command.send({'type':'paused','session':request['epoch'],'message':reason})
            try:
                if mode=='qualifica':payload['results']=worlds[0].rows([request['driver']])
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
                    preview_tick=time.monotonic();race_next_tick=preview_tick
                    simulation_anchor=preview_tick;simulation_time_anchor=worlds[0].time if worlds else 0.
                    if academy is not None:academy.last_preview=preview_tick;academy.rate_samples={}
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
                if now>=next_frame:send_frame()
                if countdown==0:
                    race_next_tick=time.monotonic();simulation_anchor=race_next_tick;simulation_time_anchor=0.
                command.poll(0.01)
                continue
            if learning(mode):
                if academy is not None:
                    academy.advance_preview()
                    academy.tick();steps=academy.steps;metric=academy.metric
                    if academy.collecting:command.poll(.001)
                    task=academy.task
                    latest=academy.state['evaluations'][-1]['round'] if academy.state['evaluations'] else 0
                    if latest!=saved_evaluation_round:
                        saved_evaluation_round=latest;save_training()
                else:
                    if training_evaluation is not None:
                        started_eval=time.monotonic()
                        ended_eval=training_evaluation.step()
                        curriculum['evaluationSeconds']=curriculum.get('evaluationSeconds',0)+time.monotonic()-started_eval
                        if ended_eval:
                            result,old_result=training_evaluation.results()
                            _,changed,proof=consider(curriculum,training_evaluation.candidate,result,old_result,
                                                     training_evaluation.scenarios,scope_hash(track_id,profile['observation']),profile)
                            training_evaluation=None
                            if changed:
                                if hasattr(learner,'change_reward'):learner.change_reward()
                                # At this boundary PPO has no unfinished update. Drop
                                # experiences from the previous objective and reset the
                                # critic/optimizer while keeping the actor and RNG.
                                if isinstance(learner,PPO):
                                    from game_learning import Adam,random_weights
                                    learner.buffer=[]
                                    learner.critic=random_weights(learner.rng,learner.hidden,1,inputs=learner.inputs)
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
                        traffic_observations=[w.observations(active_only=True,version=profile['observation']) for w in worlds] if traffic else None
                        observations=np.array([obs[0] for obs in traffic_observations]) if traffic else worlds[0].observations(active_only=True,version=profile['observation'])
                        sample_active=np.array([w.active[0] for w in worlds]) if traffic else worlds[0].active.copy()
                        teacher=np.array([pursuit_actions(w,[0])[0] for w in worlds]) if traffic and hasattr(learner,'learn_step') else pursuit_actions(worlds[0]) if hasattr(learner,'learn_step') else None
                        if isinstance(learner,PPO):
                            actions,raw,logp,values=learner.sample(observations)
                        else:actions=learner.act(observations)
                        if traffic:
                            rewards=[];done=[]
                            for i,world in enumerate(worlds):
                                bot=pursuit_actions(world,[1],speed_factor=.7)[0]
                                _,r,d=world.step(np.array([actions[i],bot]),pace=pace_weight(curriculum),return_observations=False,control_cost=.03 if profile['algorithm']=='ppo_smooth' else 0.)
                                rewards.append(r[0]);done.append(d[0])
                            rewards,done=np.array(rewards),np.array(done)
                            next_obs=np.array([w.observations()[0] for w in worlds]) if isinstance(learner,PPO) else None
                        else:next_obs,rewards,done=worlds[0].step(actions,pace=pace_weight(curriculum),return_observations=isinstance(learner,PPO),control_cost=.03 if profile['algorithm']=='ppo_smooth' else 0.)
                        alive=trial_age<task['limitSeconds']
                        fitness+=rewards*alive
                        trial_age+=DT
                        terminated=done.copy()
                        done |= trial_age>=task['limitSeconds']
                        steps+=len(observations)
                        if hasattr(learner,'learn_step'):learner.learn_step(observations,teacher,sample_active)
                        if isinstance(learner,PPO):
                            learner.remember(observations,raw,logp,values,rewards,done,next_obs,terminated)
                            if traffic:
                                for i,world in enumerate(worlds):
                                    if done[i]:world.reset();trial_age[i]=0;fitness[i]=0
                            else:
                                worlds[0].reset_trials(done);trial_age[done]=0;fitness[done]=0
                            if len(learner.buffer)>=profile['rollout']:update_iterator=learner.updates()
                        elif hasattr(learner,'learn_step'):
                            if steps%(profile['population']*profile['rollout'])==0:
                                metric=learner.update(fitness);session_metric.append({**metric,'steps':steps})
                                schedule_evaluation()
                            if traffic:
                                for i,world in enumerate(worlds):
                                    if done[i]:world.reset();trial_age[i]=0;fitness[i]=0
                            else:
                                worlds[0].reset_trials(done);trial_age[done]=0;fitness[done]=0
                        elif done.all():
                            metric=learner.update(fitness)
                            session_metric.append({**metric,'steps':steps})
                            if traffic:
                                for world in worlds:world.reset()
                            else:
                                worlds[0].reset()
                                # Identical start perturbation for every candidate in this generation.
                                dy,da=worlds[0].rng.uniform(-0.7,0.7),worlds[0].rng.uniform(-0.08,0.08)
                                for index in range(worlds[0].count):worlds[0].perturb(index,dy,da)
                            trial_age[:]=0;fitness[:]=0
                            payload['metrics']=session_metric[-100:]
                            schedule_evaluation()
                            if time.monotonic()-last_save>=30:save_training()
                active_seconds += max(0,time.monotonic()-generation_started)
                generation_started=time.monotonic()
                if time.monotonic()-last_save>30:save_training()
            else:
                now=time.monotonic()
                if now<race_next_tick:
                    if now>=next_frame:send_frame()
                    command.poll(max(0,min(race_next_tick,next_frame)-time.monotonic()))
                    continue
                race_next_tick+=DT
                if now-race_next_tick>.1:race_next_tick=now-.1
                world=worlds[0]
                # The qualified deployment cue is control=1/9 in both Qualifica and Gara.
                world.training_phase='control'
                world.training_context[:,0]=np.minimum(1,world.episode_time/2)
                world.training_context[:,1]=np.minimum(1,world.credit_age/15)
                world.training_context[:,2]=np.clip(world.progress-world.progress_credit,0,1)
                world.training_context[:,3]=1/9
                actions=frozen_actions(world,[policies[eval_index]] if mode=='prova' else policies)
                world.step(actions,return_observations=False)
                if mode=='qualifica':
                    for lap in world.lap_times[0][persisted_laps:]:
                        if lap['clean'] and not lap['standingStart']:
                            person=payload['participants'][0]
                            store.record_qualification(person['id'],person['policy'],person['profile'],lap,run)
                            command.send({'type':'qualification','session':request['epoch']})
                    persisted_laps=len(world.lap_times[0])
                if mode=='gara' and np.isfinite(world.finish).any():
                    race_deadline=min(race_deadline,float(np.nanmin(world.finish))+30)
                ended=not world.active.any() or world.time>=race_deadline
                if ended:
                    timed_out=world.active.copy()
                    if mode=='prova':
                        row=world.rows()[0]
                        if timed_out[0]:row['status']='tempo scaduto'
                        evaluation.append({'driver':payload['participants'][min(eval_index,len(policies)-1)]['id'],
                                           'policy':payload['participants'][eval_index]['policy'],
                                           'time':row['finishTime'],
                                           'progress':row['progress'],'status':row['status'],**{k:row[k] for k in ('telemetryVersion','lapTimes','bestLap','maxSpeed')}})
                        eval_index+=1
                        if eval_index<len(policies):
                            worlds[0]=World(1,1,laps=laps,track_id=track_id,physics=physics,telemetry=True);worlds[0].reset(varied=False)
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
                    # Races/campione/prova are watched in real time, never frame-dependent.
                    remaining=min(race_next_tick,next_frame)-time.monotonic()
                    if remaining>0:command.poll(remaining)
                    generation_started=time.monotonic()
            if time.monotonic()>=next_frame:send_frame()
            if learning(mode) and time.monotonic()-last_yield>=.008:
                command.poll(.001);last_yield=time.monotonic()
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
        if academy is not None:academy.close()
        command.close()
        frames.cancel_join_thread()
