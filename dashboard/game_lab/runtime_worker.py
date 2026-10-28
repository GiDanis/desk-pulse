"""On-demand SB3 learning with a separate, real-time neural demonstration.

The training process owns learner/replay/optimizer and checkpoints only at
full update boundaries. The preview process keeps serving IPC and frames.
This module is imported exclusively by the isolated learner interpreter.
"""
from copy import deepcopy
from pathlib import Path
import json,os,queue,sys,time,uuid
import numpy as np
from game_lab.environment import make_episode
from game_temporal import TemporalPolicy
from game_residual import key
from game_policy_digest import mutable_weights

BACKEND='sb3-skill-1'


def runtime_contract(base,method,options):
    import torch,gymnasium,stable_baselines3
    from game_lab.provenance import source_hashes
    return dict(backend=BACKEND,baseHash=key(base),method=method,features=base['features'],options=options,
        updateEvery=128 if method=='ppo' else 1,
        sources=source_hashes(),dependencies=dict(torch=torch.__version__,numpy=np.__version__,
            gymnasium=gymnasium.__version__,sb3=stable_baselines3.__version__))


def binary_path(root,relative):
    base=(Path(root)/'reference-checkpoints').resolve();path=(Path(root)/relative).resolve()
    if not path.is_relative_to(base) or path==base:raise ValueError('Percorso checkpoint non valido')
    return path


class ReferenceLearner:
    def __init__(self,root,driver,policy,checkpoint,request,events):
        self.root=Path(root);self.driver=driver;self.policy=policy;self.checkpoint=checkpoint
        self.request=request;self.events=events;self.running=True;self.stopping=False

    def run(self):
        try:self.execute()
        except Exception as error:self.events.put(('error',str(error)))

    def execute(self):
        import torch
        from game_lab.skills import initialize,SkillEnv,export,head_sizes,readout
        from game_lab.checkpoint import save,load
        from game_store import GameStore
        torch.set_num_threads(1);store=GameStore(self.root,self.request.get('track','oval-1'),recover_sessions=False)
        method={'residual_ppo':'ppo','residual_sac':'sac','residual_td3':'td3','residual_tactic':'td3'}[self.driver['profile']['algorithm']]
        checkpoint=self.checkpoint
        base=store.load(checkpoint['basePolicy']) if checkpoint else self.policy
        family=('racecraft' if self.driver['profile']['algorithm']=='residual_tactic' else 'traffic') if self.request['mode']=='impara_sorpasso' else 'solo'
        options=dict(family=family,bots=self.request.get('bots',2),duration=180.,track=self.request.get('track','oval-1'))
        if self.request['mode']=='impara':options['single_lap']=True
        contract=runtime_contract(base,method,options)
        if checkpoint:
            if checkpoint['contract']!=contract:raise ValueError('Checkpoint appartenente a un altro obiettivo o contesto')
            env=SkillEnv(base,**options);model,_=load(binary_path(self.root,checkpoint['binary']),env,contract=contract)
        else:
            model,env=initialize(base,method,seed=self.driver['profile']['seed'],
                role='tactic' if self.driver['profile']['algorithm']=='residual_tactic' else 'driving',**options)
        from game_policy_digest import ReadoutDigest
        portable=export(model);digester=ReadoutDigest(portable)
        if model._last_obs is None:
            model._last_obs=model.get_env().reset();model._last_episode_starts=np.ones((1,),dtype=bool)
        self.events.put(('loaded',portable))
        last_result={};last_committed=None
        def progress(_locals,_globals):
            nonlocal last_result
            for info in _locals.get('infos',[]):
                if info.get('result') is not None:last_result=deepcopy(info['result'])
            return True
        while not self.stopping:
            while True:
                try:message=self.commands.get_nowait()
                except queue.Empty:break
                kind=message['type']
                if kind in ('pause','stop','snapshot'):
                    # A durable paused checkpoint is already the exact state
                    # requested by Stop. A second binary/JSON/SQLite write
                    # adds latency without collecting any new experience.
                    if (kind=='stop' and not self.running and last_committed
                        and last_committed['decisions']==model.num_timesteps
                        and last_committed['seconds']==message['seconds']):
                        self.stopping=True;self.events.put(('boundary',None))
                        self.events.put(('committed',(last_committed['digest'],last_committed['steps'],True)))
                        break
                    if kind!='snapshot':
                        self.running=False;self.stopping=kind=='stop';self.events.put(('boundary',None))
                    destination=self.root/'reference-checkpoints'/self.driver['id']/uuid.uuid4().hex
                    manifest=save(model,destination,method=method,contract=contract)
                    data=dict(protocol=BACKEND,backend=BACKEND,contract=contract,binary=str(destination.relative_to(self.root)),
                        basePolicy=store.artifact(base),decisions=model.num_timesteps,steps=env.total_physics_steps,
                        manifestHash=__import__('hashlib').sha256((destination/'manifest.json').read_bytes()).hexdigest())
                    from game_catalog import configuration
                    from game_geometry import get_track
                    session=self.session;seconds=message['seconds'];saved_policy=export(model)
                    data.update(seconds=seconds,configuration=configuration(store.track_id,'race-68-v3'),lastEpisode=deepcopy(last_result),
                        task=dict(label='Sorpassi continui' if self.request['mode']=='impara_sorpasso' else 'Guida e passo',
                            distance=get_track(store.track_id).length if self.request['mode']=='impara' else None,
                            continuous=self.request['mode']!='impara',laps=1,limitSeconds=180.),
                        preview=message.get('preview'),previewRevision=message.get('previewRevision',0),
                        previewPolicy=restore_preview_policy(saved_policy,message['previewReadout']) if message.get('previewReadout') else None)
                    metric=dict(decisions=model.num_timesteps,episodes=model._episode_num,updates=model._n_updates)
                    state=dict(backend=BACKEND,phase='reference',stats=metric,evaluations=[],trainingProfile=self.driver['profile'],lastEpisode=deepcopy(last_result))
                    store.select_objective(self.request['mode'])
                    digest=store.save_training(self.driver['id'],data,saved_policy,data['steps'],seconds,metric,state,
                        session=session['id'],session_stats=dict(steps=data['steps']-session['baseSteps'],seconds=seconds-session['baseSeconds']))
                    store.finish_session(session['id'],'paused' if kind!='snapshot' else 'running',
                        {**session['payload'],'training':dict(steps=data['steps']-session['baseSteps'],seconds=seconds-session['baseSeconds'])})
                    last_committed=dict(digest=digest,steps=data['steps'],decisions=model.num_timesteps,seconds=seconds)
                    self.events.put(('committed',(digest,data['steps'],kind!='snapshot')))
                    # Cleanup is independent of session length, and cannot
                    # delay the durable save acknowledgement or fail a save.
                    maintain_checkpoints(store)
                elif kind=='resume':
                    self.running=True;store.finish_session(self.session['id'],'running',self.session['payload'])
            if self.stopping:break
            if not self.running:
                time.sleep(.01);continue
            model.learn(128 if method=='ppo' else 32,reset_num_timesteps=False,callback=progress)
            # The encoder is immutable; publish one small readout update at a
            # completed boundary. Never expose a model mid-gradient to IPC.
            layer=readout(model,method)
            if base.get('readoutMode')=='plastic-actuators-1':
                changes={('weights',k):v.detach().cpu().numpy().astype(float).tolist() for k,v in layer.state_dict().items()}
            else:
                h,s=head_sizes(base);weight=layer.weight.detach().cpu().numpy();bias=layer.bias.detach().cpu().numpy()
                changes={('weights','head.weight'):weight[:,:h].astype(float).tolist(),('weights','skip.weight'):weight[:,h:h+s].astype(float).tolist(),
                    ('weights','head.bias'):bias.astype(float).tolist()}
                if base['architecture']=='gru-adapter':changes[('weights','adapter_head.weight')]=weight[:,h+90:].astype(float).tolist()
            changes[('origin','decisions')]=model.num_timesteps
            self.events.put(('update',dict(actuators={name:changes[('weights',name)] for name in mutable_weights(portable)},policyHash=digester.digest(changes),decisions=model.num_timesteps,
                steps=env.total_physics_steps,episodes=model._episode_num,updates=model._n_updates,
                result=deepcopy(env.episode.result()),lastEpisode=deepcopy(last_result))))
        env.close()


def training_main(link,root,message):
    # SB3 imports Matplotlib via its logger, even without plotting. A fresh
    # dashboard/test XDG directory must not rebuild font metadata at each
    # Start. This is an isolated library cache, never GUI preferences or data.
    cache=Path(sys.prefix)/'cache/matplotlib';cache.mkdir(parents=True,exist_ok=True)
    os.environ.setdefault('MPLCONFIGDIR',str(cache))
    # The preview process owns lifecycle. A forced parent termination must not
    # leave a learner running behind a closed Dashboard view.
    import ctypes,signal
    try:ctypes.CDLL(None).prctl(1,signal.SIGTERM)
    except (AttributeError,OSError):pass
    if os.getppid()!=message['parent']:return
    try:
        if os.getpriority(os.PRIO_PROCESS,0)<15:os.setpriority(os.PRIO_PROCESS,0,15)
    except OSError:pass
    from game_process import ChildRequests,ChildResults
    learner=ReferenceLearner(root,message['driver'],message['policy'],message.get('checkpoint'),message['request'],ChildResults(link))
    learner.commands=ChildRequests(link);learner.session=message['session'];learner.run()


def worker_main(command,frames,root,request):
    try:
        if os.getpriority(os.PRIO_PROCESS,0)<10:os.setpriority(os.PRIO_PROCESS,0,10)
    except OSError:pass
    from game_store import GameStore
    from game_catalog import configuration
    store=GameStore(root,request.get('track','oval-1'));store.select_objective(request['mode']);driver=store.driver(request['driver'])
    if not driver:raise ValueError('Pilota sconosciuto')
    checkpoint=store.load(driver['checkpoint']) if driver.get('checkpoint') else None
    if checkpoint and checkpoint.get('backend')!=BACKEND:checkpoint=None
    prior_options=(checkpoint or {}).get('contract',{}).get('options',{})
    desired_family=('racecraft' if driver['profile']['algorithm']=='residual_tactic' else 'traffic') if request['mode']=='impara_sorpasso' else 'solo'
    if checkpoint and (prior_options.get('bots')!=request.get('bots',2) or prior_options.get('family')!=desired_family or bool(prior_options.get('single_lap'))!=(request['mode']=='impara')):
        # A different curriculum reuses driving knowledge with a fresh critic
        # and replay. An incompatible environment snapshot is never restored.
        checkpoint=None
    # A new objective starts from this pilot's latest saved neural knowledge.
    # Existing objective checkpoints retain their exact optimizer and episode.
    policy=store.load((store.reference_candidate(driver['id']) if not checkpoint else None) or driver.get('candidate') or driver['policy'])
    if (policy.get('origin') or {}).get('backend')!=BACKEND:raise ValueError('Base di apprendimento incompatibile')
    # The installer publishes a qualified package only after P7. Experiments
    # use private stores and an explicit process environment, never a GUI flag.
    if os.environ.get('SMARTPC_GAME_REFERENCE_EXPERIMENT')!='1':
        release=store.reference_release()
        from game_reference_backend import qualified_ancestry
        if not qualified_ancestry(store,policy,release):raise ValueError('Nuova base ancora da qualificare')
    from game_process import spawn_role
    # Private filesystem sockets survive logind RemoveIPC. Never create POSIX
    # semaphore queues or reconstruct the GUI/main module through mp.spawn.
    payload=dict(driver=driver['id'],profile=driver['profile'],backend=BACKEND,training={'steps':0,'seconds':0})
    run,payload=store.begin_session(request['mode'],payload)
    trainer,trainer_link,_=spawn_role('reference-training',root,
        dict(driver=driver,policy=policy,checkpoint=checkpoint,request=request,parent=os.getpid(),
            session=dict(id=run,payload=payload,baseSteps=(checkpoint or {}).get('steps',0),baseSeconds=(checkpoint or {}).get('seconds',0.))),interpreter=sys.executable)
    epoch=request['epoch'];sequence=0;paused=False;pending=False;stopping=False;ready=False
    preview=None;actor=None;candidate=None;stats={};seconds=(checkpoint or {}).get('seconds',0.)
    base_seconds=seconds;base_steps=(checkpoint or {}).get('steps',0);tick=time.monotonic();remaining=0.;next_frame=tick
    revision=0;last_lap=0;reset_at=None;view=request.get('view','pilot');selected=0;last_save=tick;save_busy=False
    candidate_key=key(policy);rate_time=0.;rate_simulated=0.;sim_rate=None
    def snapshot_message(kind):
        return dict(type=kind,seconds=seconds,preview=preview.snapshot() if preview else None,
            previewReadout=preview_readout(actor) if actor else None,previewRevision=revision)
    def apply_readout():
        # These incoming lists are immutable snapshots: subsequent updates
        # replace whole fields. Share them instead of deep-copying thousands
        # of control coefficients on the frame deadline at a lap boundary.
        for name in mutable_weights(actor.data):
            actor.data['weights'][name]=candidate['weights'][name]
            actor.weights[name]=np.asarray(actor.data['weights'][name],dtype=float)
        actor.data['origin']=deepcopy(candidate['origin']);actor.key=candidate_key
    def new_preview():
        nonlocal preview,remaining,revision,last_lap,reset_at
        preview=make_episode(driver['profile']['seed']+revision,family='traffic' if request['mode']=='impara_sorpasso' else 'solo',
            bots=request.get('bots',2),duration=1.e9,track=request.get('track','oval-1'))
        if request['mode']=='impara':preview.spec.update(distance=preview.world.track.length,continuous=False)
        revision+=1;remaining=0.;last_lap=0;reset_at=None
        preview.world.enable_timing('preview').bind(0,driver['id'],actor.key)
    try:
        while True:
            now=time.monotonic();wall_elapsed=max(0.,now-tick);elapsed=min(.1,wall_elapsed);tick=now
            while command.poll():
                message=command.recv();kind=message.get('type')
                if kind in ('pause','stop'):
                    queued=False
                    if not pending:
                        command.send(dict(type='pause_pending',session=epoch));pending=True;paused=True
                        trainer_link.send(snapshot_message(kind));queued=True
                    if kind=='stop':
                        stopping=True
                        if not queued:trainer_link.send(snapshot_message('stop'))
                elif kind=='resume' and paused and not pending:
                    paused=False;trainer_link.send(message);command.send(dict(type='ready',session=epoch,run=run))
                elif kind=='view':view=message.get('view','pilot')
                elif kind=='select':selected=int(message.get('index',0))
            while True:
                try:
                    if not trainer_link.poll():break
                    kind,value=trainer_link.recv()
                except EOFError:break
                if kind=='loaded':
                    actor=TemporalPolicy(value);candidate=deepcopy(value);candidate_key=actor.key;new_preview();ready=True
                    if checkpoint and checkpoint.get('preview'):
                        preview.restore(checkpoint['preview']);actor=TemporalPolicy(checkpoint['previewPolicy'])
                        revision=checkpoint.get('previewRevision',revision);last_lap=int(preview.world.lap_count[0])
                    command.send(dict(type='ready',session=epoch,run=run))
                elif kind=='update':
                    stats=value;candidate_key=value['policyHash']
                    if set(value['actuators'])!=set(mutable_weights(candidate)):raise ValueError('Mutable control contract changed')
                    candidate['weights'].update(value['actuators'])
                    candidate['origin']['decisions']=value['decisions']
                elif kind=='boundary':command.send(dict(type='paused',session=epoch))
                elif kind=='committed':
                    digest,saved_steps,was_pause=value
                    if was_pause:pending=False
                    last_save=now;save_busy=False
                    command.send(dict(type='saved',session=epoch,policy=digest,steps=saved_steps,automatic=not was_pause))
                elif kind=='error':raise RuntimeError(value)
            if stopping and not trainer.is_alive() and not pending:break
            if not trainer.is_alive() and not stopping:raise RuntimeError('Apprendimento interrotto')
            if ready and not paused:
                seconds+=wall_elapsed;remaining+=elapsed
                if now-last_save>=30 and not save_busy:
                    trainer_link.send(snapshot_message('snapshot'));save_busy=True
                if preview.reason:
                    reset_at=reset_at or now+1.
                    if now>=reset_at:apply_readout();new_preview()
                else:
                    rate_time+=wall_elapsed
                    while remaining>=1/60:
                        preview.step(actor.act(preview.world,0),return_observation=False);remaining-=1/60;rate_simulated+=1/60
                        lap=int(preview.world.lap_count[0])
                        if lap>last_lap:
                            # Keep the entire lap on one frozen candidate.
                            apply_readout()
                            if preview.world.timing:preview.world.timing.bind_preview_boundary(0,driver['id'],actor.key,lap,preview.world.time)
                            last_lap=lap
                        if preview.reason:remaining=0.;break
                    if rate_time>=1.:
                        sim_rate=rate_simulated/rate_time;rate_time=rate_simulated=0.
            if ready and now>=next_frame:
                sequence+=1;w=preview.world;rows=w.rows();selected%=len(rows)
                for i,row in enumerate(rows):
                    row.update(id='preview-'+str(i),driverId=driver['id'] if i==0 else '',name=driver['name'] if i==0 else 'Bot '+str(i),
                        number=driver['number'] if i==0 else i,resetKey=str(revision),passes=preview.passes,
                        simulatedTime=w.time,simRate=sim_rate)
                meta=dict(driverName=driver['name'],algorithm=driver['profile']['algorithm'],count=len(rows),selected=selected,
                    steps=stats.get('steps',base_steps),seconds=seconds,phase='pausa' if paused else 'apprendimento',
                    curriculumPhase='Rete ricorrente · controllo diretto',presentation='preview',time=w.time,
                    policyVersion=actor.key,trainingCount=1,sensorRange=150,objective=request['mode'],
                    learningStats={k:stats.get(k,0) for k in ('decisions','episodes','updates')},
                    exercise='Pilota · guida a 1×',trainingExercise='Sorpasso e difesa' if request['mode']=='impara_sorpasso' else 'Guida e passo',
                    view=view,backend=BACKEND,simRate=sim_rate)
                applied=getattr(w,'direct_previous',np.zeros((w.count,2)))[0]
                meta.update(controlMode='direct',previewState=preview.reason or 'running',residual=dict(
                    updates=stats.get('updates',0),decisions=stats.get('decisions',0),episodes=stats.get('episodes',0),
                    speedKmh=float(np.hypot(w.state[0,3],w.state[0,4]))*3.6,steer=float(applied[0]),pedal=float(applied[1]),
                    stage='critic_preparation' if stats.get('decisions',0)<1024 else 'refinement',previewTrial=revision,
                    objectiveStage='Affinamento neurale',lastDecisionLabel='Candidato · Qualifica separata',
                    raceStatus='Versione gara conservata',schoolSkill='Esperienze causali',pedalBlockSeconds=0.,
                    rewardTerms=stats.get('result',{}).get('rewardTerms',{}),attack=stats.get('result',{}).get('attack',{}),
                    collectionLabel=stats.get('result',{}).get('manoeuvre','Guida e passo')))
                produced=time.monotonic()
                packet=dict(timestamp=produced,session=epoch,sequence=sequence,mode=request['mode'],cars=rows,
                    sensors=w.observations(version='race-68-v3')[selected,:5].tolist(),meta=meta,engine='CPU',trackId=store.track_id)
                try:frames.put_nowait(packet)
                except queue.Full:pass
                next_frame+=1/30
                if next_frame<=produced:next_frame+=(int((produced-next_frame)*30)+1)/30
            time.sleep(.002)
    except Exception as error:
        store.finish_session(run,'failed',{**payload,'error':str(error)})
        try:command.send(dict(type='save_failed' if pending else 'error',session=epoch,message=str(error)))
        except (EOFError,OSError):pass
    finally:
        try:trainer_link.send(snapshot_message('stop'))
        except (EOFError,OSError):pass
        trainer.join(8)
        if trainer.is_alive():trainer.terminate();trainer.join(1)
        if trainer.is_alive():trainer.kill();trainer.join(1)
        # A SIGKILL can still be pending behind kernel I/O. Avoid replacing
        # the primary error with Popen.close's "still running" exception.
        if not trainer.is_alive():trainer.close()
        trainer_link.close()


def preview_readout(actor):
    fields=mutable_weights(actor.data)
    return dict(weights={k:actor.weights[k].tolist() for k in fields},origin=deepcopy(actor.data['origin']),
        policyHash=actor.key,encoderKey=actor.encoder_key)


def restore_preview_policy(template,descriptor):
    """Rebuild the immutable encoder in the learner, never in a frame loop."""
    data=deepcopy(template)
    allowed=set(mutable_weights(data))
    if set(descriptor['weights'])!=allowed:raise ValueError('Preview readout contract')
    data['weights'].update(deepcopy(descriptor['weights']));data['origin']=deepcopy(descriptor['origin'])
    policy=TemporalPolicy(data)
    if policy.key!=descriptor['policyHash'] or policy.encoder_key!=descriptor['encoderKey']:raise ValueError('Preview snapshot identity changed')
    return data


def readout_sizes(base):
    return (256,92) if base['architecture'] in ('gru-intent-deep','gru-maneuver') else (128,92) if base['architecture']=='gru-intent' else (base['hidden'],90)


def prune_checkpoints(store):
    """Only remove owned binary snapshots whose JSON artifacts were pruned.

    Current/context/archive pointers and the two retained history saves remain
    roots in GameStore. Portable race/qualifying policies need no optimizer.
    """
    import shutil
    referenced=set()
    for path in store.policies.glob('*.json'):
        data=json.loads(path.read_text())
        if isinstance(data,dict) and data.get('backend')==BACKEND and data.get('binary'):
            referenced.add(binary_path(store.root,data['binary']))
    parent=store.root/'reference-checkpoints'
    for manifest in parent.glob('*/*/manifest.json'):
        directory=manifest.parent
        if directory.resolve() not in referenced and time.time()-manifest.stat().st_mtime>120:
            shutil.rmtree(directory)


def maintain_checkpoints(store,*,now=None):
    """Bound snapshot growth across short sessions as well as long runs.

    The marker is advisory, not a durability promise. Current, archived and
    recent resumable roots remain governed by GameStore's conservative GC.
    """
    import sqlite3
    now=time.time() if now is None else now
    marker=store.root/'reference-maintenance.json'
    try:
        try:last=json.loads(marker.read_text())['time']
        except (FileNotFoundError,ValueError,KeyError,TypeError):last=None
        if last is not None and 0<=now-last<300:return False
        temporary=marker.with_suffix('.tmp');temporary.write_text(json.dumps(dict(time=now)))
        temporary.replace(marker)
        if last is None:return False
        store.prune_residual_artifacts();prune_checkpoints(store)
        return True
    except (OSError,ValueError,TypeError,sqlite3.Error) as error:
        print('Reference checkpoint maintenance deferred:',str(error),file=sys.stderr,flush=True)
        return False
