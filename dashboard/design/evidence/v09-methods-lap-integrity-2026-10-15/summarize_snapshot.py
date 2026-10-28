"""Reduce a private read-only export; never store weights in study evidence."""
import json,hashlib,sys
from pathlib import Path
from collections import Counter
source=Path(sys.argv[1]);dest=Path(sys.argv[2]);s=json.loads(source.read_text())
def compact(c):
 st=c.get('curriculum') or {};l=c.get('learner') or {};plan=st.get('evoTraining') or {};eps=c.get('episodes') or []
 state_fields=('phase','phaseUpdates','updates','round','curveReady','pacePressure','rewardVersion','objective')
 stats=st.get('stats') or {};memory=c.get('memory') or {}
 out=dict(steps=c.get('steps'),seconds=c.get('seconds'),protocol=c.get('protocol'),state={k:st.get(k) for k in state_fields},
  generation=l.get('generation',l.get('update')),rewardSpec=c.get('rewardSpec'),task=c.get('task'),
  plan={k:plan.get(k) for k in ('level','generations','stageGenerations','case','reliable')},metric=c.get('metric'),
  statistics={k:stats.get(k) for k in ('episodes','success','no_progress','contact','skill_failed','timeout','window','pedalCounts','simulatedSeconds')},
  epoch={k:st.get('epochStats',{}).get(k) for k in ('version','startedSteps','episodes','pedalCounts')},
  epochTasks={k:{j:v.get(j) for j in ('episodes','success','no_progress','contact','skill_failed','timeout')} for k,v in st.get('epochStats',{}).get('byTask',{}).items()},
  memory=dict(source=memory.get('source'),baseHash=memory.get('baseHash'),status=memory.get('status'),fresh=memory.get('fresh'),
   skills=[dict(track=x['track'],phase=x['phase'],valid=x.get('result',{}).get('valid'),total=x.get('result',{}).get('total')) for x in memory.get('coverage',[])]),
  episodeReasons=dict(Counter(e.get('reason') or 'running' for e in eps)),
  episodes=[dict(index=i,phase=e['phase'],reason=e.get('reason'),age=e.get('age'),validProgress=e.get('valid_progress'),worldProgress=(e.get('world') or {}).get('progress'),
   checkpoint=(e.get('world') or {}).get('checkpoint'),trackLimits=(e.get('world') or {}).get('trackLimits'),finish=(e.get('world') or {}).get('finish'),
   startDistance=e.get('start_distance'),speed=(e.get('world') or {}).get('state',[[None]*7])[0][3],worldActive=(e.get('world') or {}).get('active')) for i,e in enumerate(eps)],
  latestChecks=[dict(round=x['round'],phase=x['phase'],valid=x['candidate']['valid'],total=x['candidate']['total'],retained=x['candidate'].get('retained'),
   tested=x['candidate'].get('tested'),stage=x.get('stage'),median=x['candidate'].get('median')) for x in st.get('evaluations',[])[-8:]],
  candidate=digest(l.get('candidate',l.get('actor',l.get('weights')))),actor=digest(l.get('population',l.get('actor',l.get('weights')))),
  review=dict(kind=c.get('memoryReview',{}).get('kind'),finished=sum(bool(e.get('reason')) for e in c.get('memoryReview',{}).get('episodes',[])),total=len(c.get('memoryReview',{}).get('episodes',[]))) if c.get('memoryReview') else None)
 return out

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest() if value is not None else None
rows=[]
for row in s['tables']['drivers']+s['tables']['driver_paths']:
 c=s['artifacts'].get(row.get('checkpoint'),{});rows.append(dict(id=row['id'],name=row.get('name'),track=row.get('track_id','oval-1'),profile=json.loads(row['profile']),checkpoint=row.get('checkpoint'),modified=c.get('modified'),storedSteps=row['steps'],storedSeconds=row['seconds'],training=compact(c.get('value',{}))))
objectives=[]
for row in s['tables']['objective_paths']:
 path=json.loads(row['state']);c=s['artifacts'].get(path.get('checkpoint'),{});objectives.append(dict(driver=row['driver'],track=row['track'],objective=row['objective'],checkpoint=path.get('checkpoint'),modified=c.get('modified'),training=compact(c.get('value',{}))))
result=dict(captured=s['captured'],scope=s['scope'],version=s['version'],service=s['service'],sourceSha256=s['sourceSha256'],sourceMatchesWorkspace=all(hashlib.sha256(Path('dashboard',k).read_bytes()).hexdigest()==v for k,v in s['sourceSha256'].items()),drivers=rows,objectives=objectives,
 sessions=[dict(id=r['id'],mode=r['mode'],status=r['status'],updated=r['updated'],driver=json.loads(r['payload']).get('driver'),training=json.loads(r['payload']).get('training')) for r in s['sessions']])
dest.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
for d in rows:
 if d['track']!='oval-1':continue
 t=d['training'];print(d['name'],d['storedSteps'],t['state'],t['plan'],t['episodeReasons'],'review',t['review'])
for o in objectives:print('Objective',o['objective'],o['training']['steps'],o['modified'],o['training']['state'],o['training']['episodeReasons'])
