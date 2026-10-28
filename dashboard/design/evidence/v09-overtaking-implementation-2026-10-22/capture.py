"""Read-only board snapshot; personal weights remain outside the repository."""
from pathlib import Path
import hashlib,json,os,subprocess,shlex

HERE=Path(__file__).parent
PRIVATE=Path('/tmp/smartpc-attack-live-20261022')
PRIVATE.mkdir(mode=0o700,exist_ok=True)
remote=r'''
import sqlite3,json,pathlib,datetime,hashlib,subprocess
p=pathlib.Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/game')
c=sqlite3.connect('file:'+str(p/'game.sqlite')+'?mode=ro',uri=True)
c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
drivers=[dict(r) for r in c.execute('SELECT id,name,profile,checkpoint,steps,seconds FROM drivers ORDER BY number')]
sessions=[dict(r) for r in c.execute('SELECT id,mode,status,updated FROM sessions ORDER BY updated DESC LIMIT 4')]
c.rollback();c.close()
models={}
for d in drivers:
 d['profile']=json.loads(d['profile'])
 if d['checkpoint']:
  data=(p/'policies'/(d['checkpoint']+'.json')).read_bytes()
  assert hashlib.sha256(data).hexdigest()==d['checkpoint']
  models[d['profile']['algorithm']]=json.loads(data)
t=pathlib.Path('/opt/smartpc/dashboard')
names=['game_academy.py','game_rewards.py','game_racecraft.py','game_direct.py','game_direct_trainer.py','game_residual_trainer.py','game_neural_mixture.py','game_racing_learning.py','game_racing_objective.py','game_school_lessons.py','game_simulation.py','game_control.py','game-direct-base.json','game-direct-tactical-base.json']
print(json.dumps(dict(capturedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),drivers=drivers,sessions=sessions,models=models,version=(t/'version.py').read_text(),sourceHashes={n:hashlib.sha256((t/n).read_bytes()).hexdigest() for n in names},service=subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','ActiveState','-p','NRestarts','-p','MainPID'],text=True))))
'''
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=2','-i','/home/giuseppe/.ssh/smartpc_ed25519','smartpc@192.168.1.179',shlex.join(['python3','-c',remote])]
data=json.loads(subprocess.check_output(ssh,text=True))
private=PRIVATE/'snapshot.json';private.write_text(json.dumps(data));private.chmod(0o600)
rows=[]
for d in data['drivers']:
 row=dict(d);model=data['models'].get(d['profile']['algorithm'],{})
 state=model.get('curriculum',{});learner=model.get('learner',{})
 row.update(savedSteps=model.get('steps'),updates=learner.get('update',learner.get('update_index')),objective=model.get('objective'),phase=state.get('phase'),stats=state.get('stats'),epochStart=state.get('epochStart'),evaluations=[{k:e.get(k) for k in ('decision','accepted','raceAccepted','raceProposed','raceDecisionLabel','regressions')} for e in state.get('evaluations',[])[-3:]])
 rows.append(row)
root=HERE.parents[2]
report={k:v for k,v in data.items() if k not in ('models','drivers')}
report.update(drivers=rows,productionChanges=False,modelsPrivate=True,sourceParity={n:hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in data['sourceHashes'].items()})
(HERE/'board-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('capturedAt','version','service','sourceParity')},indent=2))
for r in rows:print(r['name'],r['savedSteps'],r['updates'],r['objective'],r['phase'])
