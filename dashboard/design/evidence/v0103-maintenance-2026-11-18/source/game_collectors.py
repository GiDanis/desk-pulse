"""Bounded CPU collectors for independent episodes of one learning pilot."""
import multiprocessing as mp
import os
import time


def collect(connection,parent_pid):
    os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
    try:os.setpriority(os.PRIO_PROCESS,0,10)
    except OSError:pass
    from game_academy import Episode
    from game_learning import Policy
    from game_control import racing_actions
    episodes={};opponents=[];bank=None
    try:
        while os.getppid()==parent_pid:
            if not connection.poll(.2):continue
            message=connection.recv()
            if message is None:return
            if message['opponents']!=bank:
                bank=message['opponents'];opponents=[Policy(p) for p in bank]
            results=[]
            for index,saved,action in message['jobs']:
                key=(saved['track_id'],saved['phase'],saved['seed'],saved['spec']['distance'])
                e=episodes.get(index)
                if e is None or getattr(e,'_collector_key',None)!=key:
                    e=Episode(saved['track_id'],saved['phase'],saved['seed'],opponents,saved)
                    e._collector_key=key;episodes[index]=e
                else:e.restore(saved)
                # This runtime-only key must never enter the episode checkpoint.
                teacher=racing_actions(e.world,[0])[0] if message['clone'] and not e.reason else [0.,0.]
                obs,reward,done,terminated=e.step(action,message['smooth'])
                state=e.snapshot();state.pop('_collector_key',None)
                results.append((index,state,obs,reward,done,terminated,teacher))
            connection.send({'results':results})
    except (EOFError,BrokenPipeError,OSError):pass
    except BaseException as error:
        try:connection.send({'error':str(error)})
        except OSError:pass
    finally:connection.close()


class EpisodePool:
    def __init__(self,count):
        self.members=[];self.pending=False;self.received={}
        if mp.current_process().daemon:raise RuntimeError('I collector richiedono un worker non daemon')
        context=mp.get_context('spawn')
        try:
            for _ in range(count):
                parent,child=context.Pipe();process=context.Process(target=collect,args=(child,os.getpid()),daemon=False)
                process.start();child.close();self.members.append((parent,process))
        except BaseException:self.close();raise

    def start(self,episodes,actions,method,opponents,teacher=None,smooth=None):
        if self.pending:raise RuntimeError('Batch collector ancora attivo')
        self.pending=True;self.received={};self.started=time.monotonic();self.size=len(episodes)
        for k,(pipe,process) in enumerate(self.members):
            jobs=[(i,episodes[i].snapshot(),actions[i]) for i in range(k,len(episodes),len(self.members))]
            pipe.send({'jobs':jobs,'smooth':method=='ppo_smooth' if smooth is None else smooth,'clone':method=='imitation' if teacher is None else teacher,
                       'opponents':[p.snapshot for p in opponents]})

    def poll(self,timeout=0.):
        if not self.pending:return None
        end=time.monotonic()+timeout
        while True:
            for k,(pipe,process) in enumerate(self.members):
                if k in self.received:continue
                if pipe.poll():
                    message=pipe.recv()
                    if 'error' in message:raise RuntimeError('Collector: '+message['error'])
                    self.received[k]=message['results']
                elif not process.is_alive():raise RuntimeError('Collector interrotto')
            if len(self.received)==len(self.members):
                result=[None]*self.size
                for rows in self.received.values():
                    for index,*data in rows:result[index]=data
                if any(row is None for row in result):raise RuntimeError('Batch collector incompleto')
                self.pending=False;return result
            if time.monotonic()-self.started>5:raise RuntimeError('Collector senza risposta')
            if time.monotonic()>=end:return None
            time.sleep(.001)

    def close(self):
        for pipe,process in self.members:
            try:pipe.send(None)
            except (OSError,BrokenPipeError):pass
        for pipe,process in self.members:
            process.join(.5)
            if process.is_alive():process.terminate();process.join(.5)
            pipe.close();process.close()
        self.members=[];self.pending=False
