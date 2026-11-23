"""Persistent CPU environments; actions go in, numeric deltas come back.

No learner, selection, random mutation or optimizer runs in these processes.
The parent applies ordered results and retains checkpoint/scene authority.
"""
from copy import deepcopy
import multiprocessing as mp
import os
import time
import numpy as np


def recommended_collectors(profile,track,objective,board=None):
    """Measured Orange Pi 4 Pro traffic route; other workloads remain serial.

    Solo worlds benefit more from one full integrator batch. Traffic worlds
    cannot share a collision domain, and four persistent groups improved the
    measured 32-environment workload. No inference about larger populations.
    """
    if board is None:
        from pathlib import Path
        try:board=Path('/proc/device-tree/compatible').read_bytes().split(b'\0')[0].decode()
        except (OSError,UnicodeError):board=''
    from game_native import available
    return 4 if (board=='xunlong,orangepi-4-pro' and available()
        and objective=='impara_sorpasso' and profile.get('population')==32
        and track in ('oval-1','varano-short-1')
        and profile.get('algorithm') in ('evolution','neat','ppo','ppo_smooth','imitation')) else 0


STATIC_EPISODE={'world','opponent_policies','track_id','phase','seed','spec',
                'context_config','protocol','objective','bots','single_lap',
                'reward_spec','pace_pressure','approach','scenario','revision','style',
                'opponent_offsets','start_distance'}


def packet(episode):
    state={key:deepcopy(value) for key,value in vars(episode).items()
           if key not in STATIC_EPISODE and not key.startswith('reported') and key!='recorded'}
    world={}
    for key,value in vars(episode.world).items():
        if isinstance(value,np.ndarray) and (not key.startswith('_') or key=='_segments'):
            world[key]=value.copy()
        elif key in ('time','continuous','training_phase','events','contact_times','lap_times','reward_terms'):
            world[key]=deepcopy(value)
    return dict(packet=1,episode=state,world=world)


def apply_packet(episode,state):
    if state.get('packet')!=1:raise ValueError('Packet di ambiente sconosciuto')
    for key,value in state['episode'].items():setattr(episode,key,deepcopy(value))
    for key,value in state['world'].items():
        current=getattr(episode.world,key,None)
        if isinstance(current,np.ndarray):
            new=np.asarray(value,dtype=current.dtype)
            if new.shape==current.shape:np.copyto(current,new)
            else:setattr(episode.world,key,new.copy())
        elif key=='_segments':setattr(episode.world,key,np.asarray(value,dtype=int))
        else:setattr(episode.world,key,deepcopy(value))


def durable_results(results):
    if results is None:return None
    from game_numeric import checkpoint_value
    output=[]
    for result in results:
        row=deepcopy(result);state=row[0]
        if state.get('packet'):
            state['world']['finish']=[float(x) if x is not None and np.isfinite(x) else None for x in state['world']['finish']]
        output.append(checkpoint_value(row))
    return output


def collect(connection,parent_pid):
    os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
    try:os.setpriority(os.PRIO_PROCESS,0,10)
    except OSError:pass
    from game_academy import Episode
    from game_learning import Policy
    from game_batch import BatchPhysics
    batch_physics=BatchPhysics()
    episodes={};opponents=[];bank=None
    try:
        while os.getppid()==parent_pid:
            if not connection.poll(.2):continue
            message=connection.recv()
            if message is None:return
            if message['opponents'] is not None:
                bank=message['opponents'];opponents=[Policy(p) for p in bank]
            rows=[]
            for index,saved,action in message['jobs']:
                if saved is not None:
                    episodes[index]=Episode(saved['track_id'],saved['phase'],saved['seed'],opponents,saved)
            group=[episodes[i] for i,_,_ in message['jobs']]
            actions=np.array([a for _,_,a in message['jobs']])
            physics=batch_physics.prepare(group,actions,message['smooth']) if message['batched'] else [None]*len(group)
            for row,(index,saved,action) in enumerate(message['jobs']):
                e=episodes[index]
                teacher=e.teacher_actions() if message['clone'] and not e.reason else np.zeros(2)
                obs,reward,done,terminated=e.step(action,message['smooth'],physics=physics[row])
                rows.append((index,packet(e),obs,reward,done,terminated,teacher))
            connection.send(dict(results=rows))
    except (EOFError,BrokenPipeError,OSError):pass
    except BaseException as error:
        try:connection.send(dict(error=str(error)))
        except OSError:pass
    finally:connection.close()


class PersistentEpisodePool:
    def __init__(self,count,batched=False):
        if mp.current_process().daemon:raise RuntimeError('Collector in un processo daemon')
        self.members=[];self.pending=False;self.received={};self.signatures={};self.bank=None
        self.batched=batched
        context=mp.get_context('spawn')
        try:
            for _ in range(count):
                parent,child=context.Pipe();process=context.Process(target=collect,args=(child,os.getpid()),daemon=False)
                process.start();child.close();self.members.append((parent,process))
        except BaseException:self.close();raise

    def start(self,episodes,actions,method,opponents,teacher=None,smooth=None):
        if self.pending:raise RuntimeError('Batch persistente ancora attivo')
        self.pending=True;self.received={};self.started=time.monotonic();self.size=len(episodes)
        bank=[p.snapshot for p in opponents];changed=bank!=self.bank
        for k,(pipe,process) in enumerate(self.members):
            jobs=[]
            for i in range(k,len(episodes),len(self.members)):
                e=episodes[i];signature=(id(e),e.revision,e.window_started)
                initial=e.snapshot() if self.signatures.get(i)!=signature else None
                self.signatures[i]=signature;jobs.append((i,initial,actions[i]))
            pipe.send(dict(jobs=jobs,smooth=method=='ppo_smooth' if smooth is None else smooth,clone=method=='imitation' if teacher is None else teacher,
                           opponents=bank if changed else None,batched=self.batched))
        self.bank=bank

    def poll(self,timeout=0.):
        if not self.pending:return None
        deadline=time.monotonic()+timeout
        while True:
            for k,(pipe,process) in enumerate(self.members):
                if k in self.received:continue
                if pipe.poll():
                    message=pipe.recv()
                    if 'error' in message:raise RuntimeError('Collector: '+message['error'])
                    self.received[k]=message['results']
                elif not process.is_alive():raise RuntimeError('Collector persistente interrotto')
            if len(self.received)==len(self.members):
                result=[None]*self.size
                for rows in self.received.values():
                    for index,*data in rows:result[index]=data
                if any(row is None for row in result):raise RuntimeError('Batch incompleto')
                self.pending=False;return result
            if time.monotonic()-self.started>10.:raise RuntimeError('Collector senza risposta')
            if time.monotonic()>=deadline:return None
            time.sleep(.0005)

    def close(self):
        for pipe,process in self.members:
            try:pipe.send(None)
            except OSError:pass
        for pipe,process in self.members:
            process.join(.5)
            if process.is_alive():process.terminate();process.join(.5)
            pipe.close();process.close()
