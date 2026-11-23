"""Portable inference costs, with fresh physical sensors and per-car memory.

This is a cost probe of an explicitly supplied experimental model, never a
race qualification or an activation in the pilot store.
"""
from pathlib import Path
import argparse,hashlib,json,platform,resource,time
import numpy as np
from game_temporal import TemporalPolicy
from game_direct import features
from game_simulation import World
from game_catalog import RACE_PHYSICS_VERSION
from game_residual import key
from game_native import available


def distribution(values):
    return dict(zip(('p50Ms','p95Ms','p99Ms','maxMs'),map(float,np.percentile(values,[50,95,99,100]))))


def main():
    p=argparse.ArgumentParser();p.add_argument('--policy',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--decisions',type=int,default=300)
    a=p.parse_args();data=json.loads(a.policy.read_text());start=time.perf_counter();policy=TemporalPolicy(data)
    initialization=(time.perf_counter()-start)*1000;rows=[]
    for count in (1,5):
        world=World(count,531,shared=True,laps=1000,physics=RACE_PHYSICS_VERSION,lazy_sensors=True)
        world.native_sensors=available();world.continuous=True
        pure=[];end_to_end=[];physics=[];cpu=[];hidden=None
        for i in range(a.decisions+20):
            if i%30==0:world.reset(return_observations=False)
            x=features(world);start=time.perf_counter_ns()
            _,hidden=policy.forward(x,hidden);pure.append((time.perf_counter_ns()-start)/1e6)
            # The isolated actor probe above reads telemetry. Invalidate its
            # observation cache so this measurement includes fresh sensor rays.
            world._observed_cache=None
            start=time.perf_counter_ns();before=time.process_time_ns()
            action=policy.act(world);cpu.append((time.process_time_ns()-before)/1e6)
            end_to_end.append((time.perf_counter_ns()-start)/1e6)
            start=time.perf_counter_ns()
            for _ in range(6):world.step(action,return_observations=False)
            physics.append((time.perf_counter_ns()-start)/1e6)
        rows.append(dict(cars=count,decisions=a.decisions,pureOneActor=distribution(pure[20:]),
            sensorsAndAllActors=distribution(end_to_end[20:]),cpuSensorsAndAllActors=distribution(cpu[20:]),
            sixPhysicsTicks=distribution(physics[20:]),nativeSensors=world.native_sensors))
    import game_temporal
    module_root=Path(game_temporal.__file__).resolve().parent
    source_files=[*module_root.glob('game*.py'),*module_root.glob('game*.json'),*module_root.glob('libsmartpc_game_native.so')]
    source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_files)}
    source_hashes['benchmark.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    result=dict(sourceHashes=source_hashes,architecture=data['architecture'],hidden=data['hidden'],policyHash=key(data),
        machine=platform.machine(),python=platform.python_version(),numpy=np.__version__,
        initializationMs=initialization,maxRssKiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        rows=rows,qualified=False,activated=False,opticalFps=False,trainingMeasured=False)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
