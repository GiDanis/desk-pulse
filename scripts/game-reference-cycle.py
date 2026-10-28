"""Bounded development-only DAgger cycles; final evaluation is never invoked."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time

def main():
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--dataset',type=Path,required=True)
    p.add_argument('--coverage',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,required=True);p.add_argument('--rounds',type=int,default=2)
    p.add_argument('--reference-solo',type=float,required=True);a=p.parse_args()
    if not 0<a.reference_solo<86400 or not 1<=a.rounds<=10:p.error('Invalid development budget/reference')
    a.output.mkdir(parents=True,exist_ok=False);scripts=Path(__file__).parent;checkpoint=a.checkpoint;dataset=a.dataset;results=[]
    def run(name,*arguments):
        with (root/(name+'.log')).open('wb') as log:
            subprocess.run([sys.executable,str(scripts/('game-reference-'+name+'.py')),*map(str,arguments)],stdout=log,stderr=subprocess.STDOUT,check=True)
    for number in range(a.rounds):
        root=a.output/('round-'+str(number+1));root.mkdir();seed=a.seed+number
        run('collect','--checkpoint',checkpoint,'--output',root/'corrections','--seed',seed,'--episodes',18,'--seconds',150,
            '--families','traffic','--bots',3,'--road-sensors','--round',number+5,'--stop-unsafe')
        aggregate=root/'aggregate';aggregate.mkdir()
        for source in (dataset,root/'corrections'):
            for f in source.iterdir():
                if f.suffix=='.npz' or f.name.startswith('collection-train-'):os.link(f,aggregate/f.name)
        run('maneuver','--checkpoint',checkpoint,'--dataset',aggregate,'--coverage',a.coverage,'--resume',
            '--output',root/'model','--seed',seed+1000,'--updates',3000)
        run('evaluate','--policy',root/'model/policy.json','--output',root/'development.json','--split','development')
        report=json.loads((root/'development.json').read_text());groups=report['summary']
        solo=[r['flyingMedian'] for r in report['rows'] if r['family']=='solo']
        ready=(len(report['rows'])==27 and groups['traffic']['rate']>=.75 and groups['attack']['rate']>=.9
            and groups['complete']['rate']>=.9 and groups['corner']['rate']>=.75
            and all(groups[k]['rate']==1 for k in ('solo','defend','recover'))
            and all(v is not None and v<=a.reference_solo*1.01 for v in solo))
        results.append(dict(round=number+1,seed=seed,summary=groups,policyHash=report['policyHash'],readyForIndependentPreparations=ready))
        (a.output/'progress.json').write_text(json.dumps(dict(qualified=False,finalBankUsed=False,declaredMaximumRounds=a.rounds,referenceSoloMedian=a.reference_solo,results=results),indent=2)+'\n')
        print('development-cycle',number+1,'traffic',groups['traffic']['valid'],'of',groups['traffic']['total'],'ready',ready,flush=True)
        if ready:break
        checkpoint=root/'model/model.pt';dataset=aggregate

if __name__=='__main__':main()
