"""Second matrix: compatible integrator batches, same private source pilots."""
import json,subprocess,sys
from pathlib import Path
root=Path('/var/lib/smartpc-dashboard/v09-balanced-proof')
python='/var/lib/smartpc-dashboard/game-runtime/bin/python'
source='/var/lib/smartpc-dashboard/smartpc-v09-rc15-project/dashboard'
results=[]
for track in ('oval-1','varano-short-1'):
    for method in ('evolution','neat','ppo','ppo_smooth','imitation'):
        for collectors in (0,2,4):
            label=f'batch-{track}-{method}-{collectors}'
            output=root/(label+'.json')
            args=[python,str(root/'benchmark_execution.py'),'--source',source,'--profiles',str(root/'smartpc-balanced-profiles.json'),
                  '--track',track,'--method',method,'--native','on','--collectors',str(collectors),'--batch','on','--seconds','6','--output',str(output)]
            with (root/(label+'.log')).open('w') as log:
                result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=90)
            if result.returncode:
                print(json.dumps(dict(label=label,error=(root/(label+'.log')).read_text()[-1500:])),flush=True);sys.exit(1)
            data=json.loads(output.read_text());results.append(data)
            (root/'batch-matrix.json').write_text(json.dumps(results,indent=2)+'\n')
            print(json.dumps(dict(case=label,transitionsPerSecond=round(data['transitionsPerSecond'],1),
                                  equivalentRate=round(data['fullPopulationEquivalentRate'],3),
                                  activeRange=[min(data['activeCounts']),max(data['activeCounts'])] if data['activeCounts'] else [],
                                  tickMaxMs=round(data['tickMaxMs'],2))),flush=True)
