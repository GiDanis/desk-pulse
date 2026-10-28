"""Same pilot/scenario protocol, optional native kernels and 0/2/4 collectors.

Separate invocation for each case avoids model/RNG contamination. No GameStore.
"""
import argparse,json,os,sys,time
from pathlib import Path
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--profiles',type=Path,required=True)
    parser.add_argument('--method',required=True)
    parser.add_argument('--track',default='oval-1')
    parser.add_argument('--objective',default='impara_infinito',choices=('impara_infinito','impara_sorpasso'))
    parser.add_argument('--collectors',type=int,default=0)
    parser.add_argument('--seconds',type=float,default=6.)
    parser.add_argument('--native',choices=('on','off'),default='on')
    parser.add_argument('--batch',choices=('on','off'),default='off')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();sys.path.insert(0,str(args.source))
    import numpy as np
    from game_academy import academy_profile,upgrade_learner
    from game_academy_trainer import AcademyTrainer
    from game_catalog import configuration
    import game_native
    if args.native=='off':game_native._library=None
    source=next(row for row in json.loads(args.profiles.read_text())['profiles'] if row['profile']['algorithm']==args.method)
    profile=academy_profile(source['profile']);original=source['checkpoint']
    backend=(original or {}).get('learner')
    if original and original['configuration']['observation']!=profile['observation']:
        backend=upgrade_learner(original,profile)
    warm=dict(configuration=configuration(args.track,profile['observation']),protocol='driving-memory-1',
              learner=backend,steps=0,seconds=0)
    trainer=AcademyTrainer(profile,args.track,warm,objective=args.objective,balanced=True,view='attempts',batched=args.batch=='on')
    if args.collectors:trainer.enable_collectors(args.collectors,persistent=True)
    try:
        # Warm startup including initial imports/child spawn, excluded explicitly.
        begin=time.monotonic()
        while trainer.steps<profile['population']:
            trainer.tick()
            if trainer.collecting:time.sleep(.0002)
        cold=time.monotonic()-begin
        started=time.monotonic();steps=trainer.steps;times=[];active=[];ticks=0
        while time.monotonic()-started<args.seconds:
            tick=time.monotonic();trainer.tick();times.append(time.monotonic()-tick);ticks+=1
            if ticks%64==0:active.append(sum(not e.reason for e in trainer.episodes))
            if trainer.collecting:time.sleep(.0002)
        elapsed=time.monotonic()-started;new_steps=trainer.steps-steps
        checkpoint=trainer.checkpoint(elapsed)
        report=dict(method=args.method,objective=args.objective,track=args.track,population=profile['population'],
                    sourceHash=source['sourceHash'],native=args.native,batched=args.batch,collectors=args.collectors,
                    startupSeconds=cold,seconds=elapsed,transitions=new_steps,transitionsPerSecond=new_steps/elapsed,
                    fullPopulationEquivalentRate=new_steps/(elapsed*profile['population']*60),
                    activeCounts=active,tickP95Ms=float(np.percentile(times,95)*1000),
                    tickMaxMs=max(times)*1000,stepsSaved=checkpoint['steps'],
                    activity=trainer.activity,learningMetrics=trainer.metric,
                    scope='Private headless complete trainer sample, not GUI FPS or all-active guarantee')
        args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    finally:trainer.close()


if __name__=='__main__':main()
