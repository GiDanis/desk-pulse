import collections,gzip,json,statistics
from pathlib import Path
P=Path(__file__).resolve().parent;B=P/'board';summary={}
for mode in ('capture','replay32','replay8','smooth30','qml30'):
 r=json.loads((B/(mode+'.json')).read_text());cpu=collections.defaultdict(list)
 for s in r['resources']:
  rows=s.get('threads',[]);main=next((x['tid'] for x in rows if x['name']=='python'),None)
  for t in rows:
   if t['tid']==main:cpu['main'].append(t['cpuOneCore'])
   elif t['name']=='QSGRenderThread':cpu['render'].append(t['cpuOneCore'])
 summary[mode]={k:r[k] for k in ('frameHz','frameGaps','sceneGaps','probeCallbackCost','qmlWarnings')}
 summary[mode]['cpuMedianOneCore']={k:statistics.median(v) for k,v in cpu.items()}
 summary[mode]['selectedCarPose']=r['motionGaps'].get('gameCar0')
with gzip.open(B/'capture-scenes.json.gz','rt') as f:scenes=json.load(f)['scenes']
last={};epoch=None;motion=[];sim=[];last_time=None;counts=[]
for at,s in scenes:
 meta=s['meta'];this=(meta.get('generation'),meta.get('presentation'))
 if this!=epoch:last={};last_time=None;epoch=this
 if meta.get('presentation')!='population':continue
 counts.append(meta['completedAttempts'])
 for car in s['cars']:
  key=car['id'];point=(car['x'],car['y'],car['yaw'])
  if car.get('completed') or car['speed']<.5:last.pop(key,None);continue
  old=last.get(key)
  if old and point!=old[1]:motion.append(at-old[0]);last[key]=(at,point)
  elif not old:last[key]=(at,point)
 if last_time and meta['time']>last_time[1]:sim.append((meta['time']-last_time[1])/(at-last_time[0]))
 if last_time is None or meta['time']!=last_time[1]:last_time=(at,meta['time'])
def stats(x):
 v=sorted(x);return dict(n=len(v),medianMs=statistics.median(v)*1000,p95Ms=v[int(.95*(len(v)-1))]*1000,maxMs=max(v)*1000)
summary['movingPopulationSourceGaps']=stats(motion)
summary['populationLimit']='All 32 displayed, source checkpoint mid-generation; 1–21 active in captured stream. Evaluation transition included in whole-window frame metrics; per-car probes lose delegates when model count changes. replay8 has no valid pose metric.'
summary['currentPrototypeQualification']='Neither 30 Hz prototype meets strict regular-frame gate; no prototype installed.'
(P/'comparison-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary['movingPopulationSourceGaps']))
