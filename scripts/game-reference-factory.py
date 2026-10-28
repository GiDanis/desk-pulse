"""Independent complete preparations on independently trained original cores.

Every run initializes its own actuator networks and maneuver memory. Shared
teacher/DAgger cases supplement a fresh seed-specific collection; it is never
five continuations of the screening candidate.
"""
from pathlib import Path
import argparse,json,os,subprocess,sys,time,hashlib

def main():
    p=argparse.ArgumentParser();p.add_argument('--core',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--coverage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--seed',type=int,required=True)
    p.add_argument('--episodes',type=int,default=14);p.add_argument('--control-updates',type=int,default=50000);p.add_argument('--memory-updates',type=int,default=8000)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);started=time.monotonic();scripts=Path(__file__).parent
    def run(name,*arguments):
        print('factory',a.seed,name,flush=True)
        with (a.output/(name+'.log')).open('wb') as out:
            subprocess.run([sys.executable,str(scripts/('game-reference-'+name+'.py')),*map(str,arguments)],stdout=out,stderr=subprocess.STDOUT,check=True)
    run('sensors','--checkpoint',a.core,'--output',a.output/'core')
    run('collect','--output',a.output/'fresh-data','--seed',5_000_000+a.seed,'--episodes',a.episodes,'--seconds',150,
        '--road-sensors','--noise',.01,'--bots',3,'--families','solo','traffic','attack','complete','corner','defend','recover')
    aggregate=a.output/'aggregate';aggregate.mkdir()
    for source in (a.dataset,a.output/'fresh-data'):
        for f in source.iterdir():
            if f.suffix=='.npz' or f.name.startswith('collection-train-'):os.link(f,aggregate/f.name)
    run('maneuver','--checkpoint',a.output/'core/model.pt','--dataset',aggregate,'--coverage',a.coverage,'--output',a.output/'actuators',
        '--seed',6_000_000+a.seed,'--memory-updates',0,'--control-updates',a.control_updates,'--intent-noise',.01)
    run('memory','--checkpoint',a.output/'actuators/model.pt','--dataset',aggregate,'--output',a.output/'base',
        '--seed',7_000_000+a.seed,'--updates',a.memory_updates,'--units',32,'--scale',.7)
    run('evaluate','--policy',a.output/'base/policy.json','--output',a.output/'development.json','--split','development')
    report=json.loads((a.output/'development.json').read_text());training=json.loads((a.output/'base/training.json').read_text())
    policy=json.loads((a.output/'base/policy.json').read_text())
    (a.output/'preparation.json').write_text(json.dumps(dict(kind='independent-complete-preparation',seed=a.seed,
        originalCoreHash=hashlib.sha256(a.core.read_bytes()).hexdigest(),policyHash=report['policyHash'],datasetHash=policy['origin']['datasetHash'],
        controlUpdates=a.control_updates,memoryUpdates=a.memory_updates,freshEpisodes=a.episodes,
        summary=report['summary'],wallSeconds=time.monotonic()-started,qualified=False),indent=2)+'\n')
    print('factory-complete',a.seed,report['summary']['traffic'],flush=True)

if __name__=='__main__':main()
