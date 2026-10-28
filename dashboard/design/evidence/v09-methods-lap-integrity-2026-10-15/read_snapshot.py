"""Read-only durable snapshot. Never construct GameStore on production data."""
import hashlib,json,sqlite3,subprocess,time,datetime,os
from pathlib import Path
root=Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/game');out=Path('/var/lib/smartpc-dashboard/v09-method-audit-20261015-private');out.mkdir(mode=0o700,exist_ok=True)
with sqlite3.connect('file:'+str(root/'game.sqlite')+'?mode=ro',uri=True,timeout=2) as db:
 db.row_factory=sqlite3.Row;db.execute('BEGIN')
 tables={name:[dict(r) for r in db.execute('SELECT * FROM '+name)] for name in ('drivers','driver_paths','objective_paths','driver_memory','timed_qualifications','driving_contexts')}
 sessions=[dict(r) for r in db.execute('SELECT * FROM sessions ORDER BY created DESC LIMIT 18')]
 db.execute('ROLLBACK')
keys=set()
for row in tables['drivers']+tables['driver_paths']:
 for key in ('checkpoint','candidate','policy'):
  if row.get(key):keys.add(row[key])
for row in tables['objective_paths']:
 state=json.loads(row['state'])
 for key in ('checkpoint','candidate','policy'):
  if state.get(key):keys.add(state[key])
artifacts={}
for key in keys:
 p=root/'policies'/(key+'.json')
 if p.exists():
  raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==key
  artifacts[key]=dict(value=json.loads(raw),modified=datetime.datetime.fromtimestamp(p.stat().st_mtime,datetime.timezone.utc).isoformat())
manifest=json.loads(Path('/opt/smartpc/dashboard/release-manifest.json').read_text())
source={name:hashlib.sha256(Path('/opt/smartpc/dashboard',name).read_bytes()).hexdigest() for name in ('game_academy.py','game_academy_trainer.py','game_evo_plan.py','game_simulation.py','game_batch.py','game_learning.py','game_neat.py','game_rewards.py','game_driving_memory.py','game_geometry.py','game_worker.py')}
result=dict(captured=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Durable checkpoints read in a SQLite read-only transaction; not live frame telemetry',version=manifest['version'],manifestFiles=len(manifest['sha256']),sourceSha256=source,service=subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','ActiveState','-p','NRestarts','-p','MainPID'],text=True).strip(),tables=tables,sessions=sessions,artifacts=artifacts)
(out/'snapshot.json').write_text(json.dumps(result,allow_nan=False))
print(json.dumps(dict(captured=result['captured'],version=result['version'],service=result['service'],drivers=[dict(name=d['name'],steps=d['steps'],checkpoint=d['checkpoint']) for d in tables['drivers']],sessions=[dict(id=s['id'],mode=s['mode'],status=s['status'],updated=s['updated']) for s in sessions[:4]],artifacts=len(artifacts)),indent=2))
