"""Read private PC artifacts: prove actor changes without publishing personal weights."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
P=Path(__file__).parent;private=Path('/tmp/smartpc-pilot-menu-20261021')
p=argparse.ArgumentParser();p.add_argument('--saved-root',type=Path,default=private/'saved')
p.add_argument('--store',type=Path,default=private/'reopen-pc')
p.add_argument('--report',type=Path,default=P/'pc/apple/report.json')
p.add_argument('--output',type=Path,default=P/'pc-learning-proof.json');args=p.parse_args()
report=json.loads(args.report.read_text())
by_name={d['name']:d['profile']['algorithm'] for d in json.loads((args.saved_root/'metadata.json').read_text())['drivers'] if d['checkpoint']}
previous={name:json.loads((args.saved_root/(method+'.json')).read_text()) for name,method in by_name.items()}
rows=[]
for session in report['sessions']:
    old=previous[session['name']];new=json.loads((args.store/'policies'/(session['checkpoint']+'.json')).read_text())
    a=np.asarray(old['learner']['actor']);b=np.asarray(new['learner']['actor'])
    delta=float(np.linalg.norm(a-b));assert delta>0,(session['name'],session['mode'])
    rows.append(dict(name=session['name'],mode=session['mode'],actorParameters=len(b),actorDeltaL2=delta,
        beforeActorSha256=hashlib.sha256(a.tobytes()).hexdigest(),afterActorSha256=hashlib.sha256(b.tobytes()).hexdigest(),
        collectedSteps=new['steps']-old['steps'],updates=new['learner']['update']-old['learner']['update']))
    previous[session['name']]=new
args.output.write_text(json.dumps(dict(status='passed',rows=rows,modelsPrivate=True,
    scope='All twelve menu-driven sessions changed actual actor weights; this does not prove faster lap times'),indent=2)+'\n')
print('Actor weights changed in all',len(rows),'sessions; models private')
