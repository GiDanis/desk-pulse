"""Parent heartbeat during a full immutable SAC replay save, no GUI claims."""
import sys,json,time,tempfile,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--mode',choices=('process','production','thread'),default='process');p.add_argument('--thread-source',type=Path);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.source))

def main():
 import numpy as np
 from game_store import GameStore
 from game_residual_trainer import ResidualTrainer
 from game_checkpoint_writer import CheckpointWriter
 if a.mode=='thread':
  import importlib.util
  spec=importlib.util.spec_from_file_location('game_checkpoint_writer_thread',a.thread_source)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);CheckpointWriter=module.CheckpointWriter
 with tempfile.TemporaryDirectory() as root:
  store=GameStore(root);d=store.drivers()[2];t=ResidualTrainer(d['profile'],'oval-1');l=t.learner
  l.replay[:]=np.random.default_rng(123).normal(0,.2,l.replay.shape);l.count=l.capacity;l.cursor=0
  startup=time.monotonic();writer=CheckpointWriter(store,replay_bytes=l.replay.nbytes) if a.mode=='production' else CheckpointWriter(store)
  prewarm=time.monotonic()-startup
  start=time.monotonic();c=t.checkpoint(1,deferred='writer' if a.mode=='production' else True);snapshot=time.monotonic()-start
  ticks=[time.monotonic()]
  try:
   writer.submit(d['id'],c,l.policy(),0,1,{},t.state,None,{})
   while writer.job and not writer.job.done():time.sleep(.001);ticks.append(time.monotonic())
   saved=writer.collect(wait=True)
  finally:writer.close()
  spans=sorted((b-a)*1000 for a,b in zip(ticks,ticks[1:]))
  result=dict(mode=a.mode,prewarmMs=prewarm*1000,snapshotMs=snapshot*1000,heartbeatMaxMs=max(spans),heartbeatP99Ms=spans[int(len(spans)*.99)],elapsed=time.monotonic()-start,save=saved,replayBytes=l.replay.nbytes)
  a.output.write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()
