"""Read-only facts from saved game state; no learner, UI control or migration."""
import json,math,sqlite3,sys,time
from pathlib import Path
ROOT=Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/game')
sys.path.insert(0,'/opt/smartpc/dashboard')
from game_driving_memory import task
from game_catalog import TRACK
output={'observedAt':time.time(),'scope':'Read-only saved state, not current unsaved positions or measured display cadence','version':__import__('version').VERSION,'pilots':[]}
with sqlite3.connect('file:'+str(ROOT/'game.sqlite')+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 for raw in db.execute('SELECT * FROM drivers ORDER BY number'):
  d=dict(raw);profile=json.loads(d['profile']);state=json.loads(d.get('curriculum') or '{}');phase=state.get('phase','launch')
  entries=[]
  for e in state.get('evaluations',[]):
   c=e.get('candidate',{});med=c.get('median');entries.append(dict(round=e.get('round'),phase=e.get('phase'),valid=c.get('valid'),total=c.get('total'),median=med,best=c.get('best'),laps=c.get('laps'),skills={k:{a:v.get(a) for a in ('valid','total','median','best','laps','tested')} for k,v in c.get('skills',{}).items()}))
  entry=dict(name=d['name'],algorithm=profile['algorithm'],population=profile.get('population'),profileVersion=profile.get('version'),steps=d.get('steps'),wallSeconds=d.get('seconds'),phase=phase,checkpoint=d.get('checkpoint'),policy=d.get('policy'),task=task('oval-1',phase) if phase in ('launch','control','recovery','pace','follow','overtake','corner','defend','duel','grid','race4') else None,lastEvaluations=entries[-4:],matching491=[e for e in entries if e['median'] is not None and round(e['median'],2)==4.91],qualifications=state.get('qualifications',{}))
  output['pilots'].append(entry)
 sessions=[]
 for row in db.execute('SELECT * FROM sessions ORDER BY rowid DESC LIMIT 3'):
  d=dict(row);p=json.loads(d['payload']);sessions.append({k:d.get(k) for k in ('mode','status','created','finished')}|dict(driver=p.get('driver'),profileAlgorithm=(p.get('profile') or {}).get('algorithm'),task=p.get('task'),track=(p.get('configuration') or {}).get('track',{}).get('id')))
 output['recentSessions']=sessions
output['oval']=dict(length=4*TRACK.half_straight+2*math.pi*TRACK.radius,roadWidth=TRACK.road_width,nominalLapAt60Kmh=(4*TRACK.half_straight+2*math.pi*TRACK.radius)/(60/3.6))
print(json.dumps(output,indent=2))
