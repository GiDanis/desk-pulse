"""One bounded writer for detached training snapshots; ACK only after fsync/commit."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import time
from game_residual_learning import encode_checkpoint


class CheckpointWriter:
    def __init__(self,store):
        self.store=store;self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='game-checkpoint')
        self.job=None;self.last_cost=None;self.save_count=0

    @property
    def busy(self):return self.job is not None

    def submit(self,identity,checkpoint,policy,steps,seconds,metric,curriculum,session,session_stats):
        if self.busy:return False
        # checkpoint already owns every array; never read a live learner here.
        args=(identity,checkpoint,deepcopy(policy),steps,seconds,deepcopy(metric),deepcopy(curriculum),session,deepcopy(session_stats))
        self.job=self.pool.submit(self._save,*args)
        return True

    def _save(self,identity,checkpoint,policy,steps,seconds,metric,curriculum,session,session_stats):
        start=time.monotonic();encode_checkpoint(checkpoint);encoded=time.monotonic()
        digest=self.store.save_training(identity,checkpoint,policy,steps,seconds,metric,curriculum,
            session=session,session_stats=session_stats)
        self.save_count+=1
        if self.save_count%10==0:self.store.prune_residual_artifacts()
        return dict(policy=digest,steps=steps,encodeMs=(encoded-start)*1000,persistMs=(time.monotonic()-encoded)*1000)

    def collect(self,wait=False):
        if self.job is None or not wait and not self.job.done():return None
        job,self.job=self.job,None
        self.last_cost=job.result()  # surface a failure, never emit a success ACK
        return self.last_cost

    def close(self):
        try:return self.collect(wait=True)
        finally:self.pool.shutdown(wait=True)
