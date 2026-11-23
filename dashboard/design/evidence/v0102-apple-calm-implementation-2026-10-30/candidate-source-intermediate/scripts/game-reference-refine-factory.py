"""Matched on-policy preparation correction, before any RL/final evaluation."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time

def main():
    p=argparse.ArgumentParser();p.add_argument('--preparation',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    original=json.loads((a.preparation/'preparation.json').read_text());started=time.monotonic();scripts=Path(__file__).parent;collection_seed=8_000_000+a.seed
    def run(name,*arguments):
        print('own-corrections',a.seed,name,flush=True)
        with (a.output/(name+'.log')).open('wb') as out:subprocess.run([sys.executable,str(scripts/('game-reference-'+name+'.py')),*map(str,arguments)],stdout=out,stderr=subprocess.STDOUT,check=True)
    run('collect','--checkpoint',a.preparation/'base/model.pt','--output',a.output/'corrections','--seed',collection_seed,
        '--episodes',14,'--seconds',150,'--road-sensors','--bots',3,'--families','solo','traffic','attack','complete','corner','defend','recover','--round',7,'--stop-unsafe')
    aggregate=a.output/'aggregate';aggregate.mkdir()
    for source in (a.preparation/'aggregate',a.output/'corrections'):
        for f in source.iterdir():
            if f.suffix=='.npz' or f.name.startswith('collection-train-'):os.link(f,aggregate/f.name)
    run('maneuver','--checkpoint',a.preparation/'base/model.pt','--dataset',aggregate,'--output',a.output/'actuators',
        '--seed',9_000_000+a.seed,'--resume','--memory-updates',0,'--control-updates',10000,'--priority-seed',collection_seed)
    run('memory','--checkpoint',a.output/'actuators/model.pt','--dataset',aggregate,'--output',a.output/'base','--seed',10_000_000+a.seed,
        '--updates',8000,'--units',32,'--scale',.7,'--priority-seed',collection_seed)
    run('evaluate','--policy',a.output/'base/policy.json','--output',a.output/'development.json','--split','development')
    report=json.loads((a.output/'development.json').read_text());policy=json.loads((a.output/'base/policy.json').read_text())
    (a.output/'preparation.json').write_text(json.dumps({**original,'stage':'own-on-policy-correction',
        'policyHash':report['policyHash'],'datasetHash':policy['origin']['datasetHash'],'summary':report['summary'],
        'additionalControlUpdates':10000,'additionalMemoryUpdates':8000,'additionalWallSeconds':time.monotonic()-started},indent=2)+'\n')
    print('own-corrections-complete',a.seed,report['summary']['traffic'],flush=True)

if __name__=='__main__':main()
