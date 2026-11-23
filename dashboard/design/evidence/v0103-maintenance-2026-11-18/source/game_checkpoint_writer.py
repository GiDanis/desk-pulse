"""Bounded detached writer with durable ACK and no named POSIX IPC objects.

A persistent child encodes/persists; one supervisor thread exchanges messages.
The replay lives in a private regular mmap file, outside logind RemoveIPC.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import mmap
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import time
import numpy as np
from game_residual_learning import encode_checkpoint


def persist_snapshot(store,identity,checkpoint,policy,steps,seconds,metric,curriculum,session,session_stats,prune):
    start=time.monotonic();block=None
    learner=checkpoint.get('learner',{});descriptor=learner.pop('_sharedReplay',None)
    try:
        if descriptor:
            block=np.memmap(descriptor['path'],mode='r',dtype='<f8',shape=tuple(descriptor['shape']))
            learner['_replaySnapshot']=block
        encode_checkpoint(checkpoint);encoded=time.monotonic()
        digest=store.save_training(identity,checkpoint,policy,steps,seconds,metric,curriculum,session=session,session_stats=session_stats)
        if prune:store.prune_residual_artifacts()
        return dict(policy=digest,steps=steps,encodeMs=(encoded-start)*1000,persistMs=(time.monotonic()-encoded)*1000)
    finally:
        learner.pop('_replaySnapshot',None)
        if block is not None:block._mmap.close()


def child_main():
    while True:
        try:request=pickle.load(sys.stdin.buffer)
        except EOFError:return
        if request is None:return
        try:response=(True,persist_snapshot(*request))
        except Exception as exc:response=(False,exc)
        pickle.dump(response,sys.stdout.buffer,protocol=5);sys.stdout.buffer.flush()


class CheckpointWriter:
    def __init__(self,store,replay_bytes=0):
        self.store=store;self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='game-save-ack')
        self.process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--checkpoint-child'],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        self.private=tempfile.TemporaryDirectory(prefix='smartpc-checkpoint-');self.path=Path(self.private.name)/'replay.bin'
        self.job=None;self.block=None;self.last_cost=None;self.save_count=0
        if replay_bytes:self._allocate(replay_bytes)

    def _allocate(self,size):
        self._release()
        with self.path.open('w+b') as stream:
            os.chmod(self.path,0o600);stream.truncate(size);self.block=mmap.mmap(stream.fileno(),size)
        np.ndarray((size,),dtype=np.uint8,buffer=self.block).fill(0)

    @property
    def busy(self):return self.job is not None

    def _release(self):
        if self.block is not None:self.block.close();self.block=None

    def _send(self,args):
        pickle.dump(args,self.process.stdin,protocol=5);self.process.stdin.flush()
        try:success,value=pickle.load(self.process.stdout)
        except EOFError as exc:raise RuntimeError('Processo salvataggio interrotto') from exc
        if not success:raise value
        return value

    def submit(self,identity,checkpoint,policy,steps,seconds,metric,curriculum,session,session_stats):
        if self.busy:return False
        learner=checkpoint.get('learner',{});rows=learner.pop('_replaySnapshot',None)
        if rows is not None and rows.nbytes:
            if self.block is None or len(self.block)<rows.nbytes:self._allocate(rows.nbytes)
            np.ndarray(rows.shape,dtype='<f8',buffer=self.block)[:]=rows
            learner['_sharedReplay']=dict(path=str(self.path),shape=rows.shape)
        elif rows is not None:learner['_replaySnapshot']=rows
        self.save_count+=1
        self.job=self.pool.submit(self._send,(self.store,identity,checkpoint,deepcopy(policy),steps,seconds,deepcopy(metric),deepcopy(curriculum),session,deepcopy(session_stats),self.save_count%10==0))
        return True

    def collect(self,wait=False):
        if self.job is None or not wait and not self.job.done():return None
        job,self.job=self.job,None;self.last_cost=job.result();return self.last_cost

    def close(self):
        try:return self.collect(wait=True)
        finally:
            self.pool.shutdown(wait=True)
            try:
                if self.process.poll() is None:
                    pickle.dump(None,self.process.stdin,protocol=5);self.process.stdin.flush()
                self.process.wait(timeout=10)
            except (BrokenPipeError,subprocess.TimeoutExpired):
                self.process.kill();self.process.wait()
            finally:
                self.process.stdin.close();self.process.stdout.close();self._release();self.private.cleanup()


if __name__=='__main__' and sys.argv[1:]==['--checkpoint-child']:child_main()
