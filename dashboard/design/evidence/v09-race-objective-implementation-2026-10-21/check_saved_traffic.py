"""Frozen traffic retention of the actual exported actors; no training."""
from pathlib import Path
import json
from game_school_lessons import RaceProof
from game_direct import snapshot

P=Path(__file__).parent;private=Path('/tmp/smartpc-racing-implementation-private-20261021/snapshot')
meta=json.loads((private/'saved-meta.json').read_text());rows=[]
for d in meta['drivers']:
    if d['name']=='Maestro' or not d['checkpoint']:continue
    c=json.loads((private/'models'/(d['checkpoint']+'.json')).read_text());p=json.loads(d['profile'])
    actor=snapshot(p,c['learner']['actor']);champion=c['curriculum']['champion']['policy'];cases=[]
    for seed,slot in ((942002,2),(942004,4)):
        pair=[]
        for policy in (actor,champion):
            race=RaceProof(policy,'oval-1',seed,slot)
            while not race.tick():pass
            pair.append(race.result())
        a,b=pair;safe=a['finished']==5 and a['reason']=='success' and a['contacts']<=b['contacts'] and a['limits']<=b['limits']
        cases.append(dict(candidate=a,champion=b,retained=safe))
    rows.append(dict(name=d['name'],checkpoint=d['checkpoint'],cases=cases,retained=all(c['retained'] for c in cases)))
    print(d['name'],rows[-1]['retained'],flush=True)
P.joinpath('saved-traffic-check.json').write_text(json.dumps(dict(status='passed' if all(r['retained'] for r in rows) else 'requires-stable-start',
    capturedAt=meta['capturedAt'],productionChanges=False,rows=rows),indent=2)+'\n')
