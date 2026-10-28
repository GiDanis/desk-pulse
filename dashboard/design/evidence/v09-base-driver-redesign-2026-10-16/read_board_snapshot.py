import sqlite3,json,pathlib,datetime,hashlib
root=pathlib.Path('/opt/smartpc/dashboard');p=pathlib.Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/game')
db=sqlite3.connect('file:'+str(p/'game.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
out={'capturedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'access':'sqlite mode=ro; query_only; read transaction; no GameStore; no service changes','runtimeVersionSource':(root/'version.py').read_text(),'drivers':[],'pathSummary':[]}
for r in db.execute('SELECT name,profile,steps,seconds,checkpoint FROM drivers ORDER BY number'):
 d=dict(r);profile=json.loads(d.pop('profile'));d['method']=profile['algorithm'];d['observation']=profile['observation'];d['checkpointPresent']=bool(d.pop('checkpoint'));d['storedHours']=round(d['seconds']/3600,3);out['drivers'].append(d)
for r in db.execute('SELECT d.name,p.track_id,p.steps,p.seconds,p.curriculum FROM driver_paths p JOIN drivers d ON d.id=p.id WHERE p.steps>0'):
 d=dict(r);c=json.loads(d.pop('curriculum') or '{}');ev=c.get('evoTraining') or {};d.update(phase=c.get('phase'),level=ev.get('level'),generations=ev.get('generations'),pacePressure=c.get('pacePressure'));out['pathSummary'].append(d)
out['rowCounts']={table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('drivers','driver_paths','objective_paths','objective_archives','timed_qualifications','track_records','driver_memory','driving_contexts','driving_archives','profile_paths','sessions','history')}
files=('game_control.py','game_hybrid.py','game_learning.py','game_rewards.py','game_simulation.py','game_academy.py','game_store.py','game_profiles.py')
out['runtimeSourceHashes']={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in files}
out['limitations']=['Stored steps/seconds belong to different scopes and historical recipes; do not sum driver and path counters.','No behavioral replay or live performance measurement was performed.','A snapshot cannot prove that every learner failed to learn.']
db.rollback();db.close();print(json.dumps(out,indent=2))
