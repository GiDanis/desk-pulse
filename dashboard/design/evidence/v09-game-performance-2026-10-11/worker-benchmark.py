"""Real process throughput with fixed private profiles and bounded wall time."""
import argparse
import json
import multiprocessing as mp
from pathlib import Path
import queue
import sys
import tempfile
import time

def profiled_worker(command,frames,root,request):
    import cProfile
    from game_worker import worker_main
    profiler=cProfile.Profile()
    profiler.runcall(worker_main,command,frames,root,request)
    profiler.dump_stats(str(Path(root)/'worker.prof'))

def timed_worker(command,frames,root,request):
    from game_worker import worker_main
    from game_simulation import World
    from game_store import GameStore
    from game_curriculum import Evaluation
    from game_neat import NEAT
    totals={}
    for cls,name in [(World,'step'),(World,'observations'),(GameStore,'save_training'),(Evaluation,'step'),(NEAT,'update')]:
        original=getattr(cls,name);key=cls.__name__+'.'+name
        def wrap(*args,_method=original,_key=key,**kwargs):
            start=time.perf_counter();result=_method(*args,**kwargs);elapsed=time.perf_counter()-start
            data=totals.setdefault(_key,{'calls':0,'total':0.,'maximum':0.})
            data['calls']+=1;data['total']+=elapsed;data['maximum']=max(data['maximum'],elapsed)
            return result
        setattr(cls,name,wrap)
    worker_main(command,frames,root,request)
    Path(root,'timers.json').write_text(json.dumps(totals))

def main():
    p=argparse.ArgumentParser();p.add_argument('--runtime',required=True);p.add_argument('--output',required=True)
    p.add_argument('--methods',default='evolution,neat,traffic,ppo');p.add_argument('--profile',action='store_true')
    p.add_argument('--timers',action='store_true')
    a=p.parse_args();sys.path.insert(0,a.runtime)
    from game_worker import worker_main
    from game_store import GameStore,default_profile
    ctx=mp.get_context('spawn');results=[]
    for algorithm,count,traffic in [('evolution',32,False),('neat',8,False),('evolution',8,True),('ppo',32,False)]:
        if ('traffic' if traffic else algorithm) not in a.methods.split(','):continue
        with tempfile.TemporaryDirectory(prefix='game-performance-') as root:
            store=GameStore(root);driver=store.drivers()[0]
            profile={**default_profile(),'algorithm':algorithm,'population':count,'traffic':traffic}
            store.set_profile(driver['id'],profile)
            parent,child=ctx.Pipe();frames=ctx.Queue(2)
            proc=ctx.Process(target=timed_worker if a.timers else profiled_worker if a.profile else worker_main,args=(child,frames,root,{'mode':'impara','driver':driver['id'],'epoch':'bench'}))
            proc.start();child.close();last=None;received=0;max_gap=0.;last_tick=None
            def receive(kind,timeout=30):
                end=time.monotonic()+timeout
                while time.monotonic()<end:
                    if parent.poll(.05):
                        msg=parent.recv()
                        if msg['type']=='error':raise RuntimeError(msg)
                        if msg['type']==kind:return
                raise RuntimeError('Missing '+kind)
            try:
                receive('ready');started=time.monotonic()
                while time.monotonic()-started<12:
                    while parent.poll():
                        msg=parent.recv()
                        if msg['type']=='error':raise RuntimeError(msg)
                    try:
                        last=frames.get(timeout=.01);now=time.monotonic();received+=1
                        if last_tick is not None:max_gap=max(max_gap,now-last_tick)
                        last_tick=now
                    except queue.Empty:pass
                duration=time.monotonic()-started;tick=time.monotonic();parent.send({'type':'pause'});receive('paused')
                latency=time.monotonic()-tick;receive('saved');parent.send({'type':'stop'});proc.join(5)
                assert not proc.is_alive();row=store.driver(driver['id'])
                results.append(dict(algorithm=algorithm,count=count,traffic=traffic,wallSeconds=duration,
                    steps=row['steps'],transitionsPerSecond=row['steps']/duration,frames=received,
                    maximumFrameGapSeconds=max_gap,pauseAckSeconds=latency,lastMeta=last['meta']))
                if a.profile:
                    import pstats,io
                    text=io.StringIO();pstats.Stats(str(Path(root)/'worker.prof'),stream=text).sort_stats('cumulative').print_stats(20)
                    results[-1]['cpuProfile']=text.getvalue()
                if a.timers:results[-1]['timers']=json.loads(Path(root,'timers.json').read_text())
            finally:
                if proc.is_alive():proc.terminate();proc.join(3)
                parent.close();frames.close();proc.close()
    Path(a.output).write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results),flush=True)
if __name__=='__main__':main()
