"""Assess completed private trials; refuse incomplete or drifting source proofs."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

p=argparse.ArgumentParser();p.add_argument('proof',type=Path);a=p.parse_args()
root=a.proof;native=root/'native'
receipt=json.loads((root/'native-receipt.json').read_text());assert receipt['status']=='passed'
rows={name:json.loads((native/name/'report.json').read_text()) for name in
      [*(f'{label}-{i}' for i in range(3) for label in ('original','candidate')),'soak-30min']}
assert all(r['status']=='passed' and r['deferredDeletesDrained'] and not r['qmlWarnings']
           and not r['transportAttempts'] for r in rows.values())
soak=rows['soak-30min'];assert soak['seconds']>=1790
stats={}
for label in ('original','candidate'):
    runs=[rows[f'{label}-{i}'] for i in range(3)]
    stats[label]={'p95ReadyMsMedian':statistics.median(r['readyMs']['p95'] for r in runs),
                  'p95FrameMsMedian':statistics.median(r['frameMs']['p95'] for r in runs),
                  'appearancePublications':[r['appearancePublicationsDuringNavigation'] for r in runs],
                  'stallsOver100ms':[r['stallsOver100ms'] for r in runs],
                  'actions':[r['actions'] for r in runs]}
regressions=[]
for name in ('p95ReadyMsMedian','p95FrameMsMedian'):
    before,after=stats['original'][name],stats['candidate'][name]
    if after>before*1.25 and after-before>8:regressions.append(name)
assert not regressions,regressions
assert all(n==0 for n in stats['candidate']['appearancePublications'])
assert any(n>0 for n in stats['original']['appearancePublications'])
m=soak['memoryKiB'];t=m[0]['at'];middle=[r for r in m if 300<=r['at']-t<=600]
late=[r for r in m if r['at']>=m[-1]['at']-300]
assert middle and late
first_median=statistics.median(r['Rss'] for r in middle);last_median=statistics.median(r['Rss'] for r in late)
growth=(last_median-first_median)/1024
assert growth<=max(32,.15*first_median/1024),('memory growth after warmup',growth)
assert max(r['contexts'] for r in late)<=max(r['contexts'] for r in middle)+2
assert max(r['leases'] for r in late)<=max(r['leases'] for r in middle)+4
assert max(r['qmlObjects'] for r in late)<=max(r['qmlObjects'] for r in middle)+200
frozen=json.loads((root/'source-hashes-before.json').read_text())
source=Path('/tmp/smartpc-apple-candidate/dashboard')
actual={name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in frozen}
assert actual==frozen,'Source changed during qualification'
(root/'qualified-source-hashes.json').write_text(json.dumps(actual,indent=2)+'\n')
temperatures=[n for r in m for n in r['platform']['temperaturesMilliC'].values() if n is not None]
summary={'status':'passed','comparisons':stats,'regressionThreshold':'both +25 percent and +8 ms in median of per-run p95',
         'soak':{'seconds':soak['seconds'],'actions':soak['actions'],'frameMs':soak['frameMs'],
                 'bundle':soak['bundle'],
                 'readyMs':soak['readyMs'],'stallsOver100ms':soak['stallsOver100ms'],
                 'appearancePublications':soak['appearancePublicationsDuringNavigation'],
                 'rssMiBStart':m[0]['Rss']/1024,'rssMiBEnd':m[-1]['Rss']/1024,
                 'rssMiBMedian5to10min':first_median/1024,'rssMiBMedianLast5min':last_median/1024,
                 'rssMiBGrowthAfterWarmup':growth,'maxContexts':max(r['contexts'] for r in m),
                 'maxLeases':max(r['leases'] for r in m),'maxQmlObjects':max(r['qmlObjects'] for r in m),
                 'maxTemperatureC':max(temperatures)/1000 if temperatures else None,
                 'qmlWarnings':0,'networkAttempts':0},
         'scope':'Private synthetic workflows, native EGLFS software timing. No optical FPS, USB latency or live-provider qualification.'}
(root/'performance-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
