"""Stage the exact manifest delta over the installed baseline, no service stop."""
from pathlib import Path
import json,hashlib,shutil,tarfile,sqlite3,sys,os
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-attack-proof';T=Path('/opt/smartpc/dashboard')
P.mkdir(exist_ok=True);(P/'private').mkdir(exist_ok=True);(P/'private').chmod(0o700)
old=json.loads((T/'release-manifest.json').read_text());assert old['version']=='0.9.3-rc.1'
assert all(hashlib.sha256((T/n).read_bytes()).hexdigest()==h for n,h in old['sha256'].items())
for kind in ('runtime','project'):
 root=H/('smartpc-attack-'+kind)/'dashboard';root.mkdir(parents=True,exist_ok=True)
 for name in old['sha256']:
  target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(T/name,target)
 with tarfile.open('/tmp/smartpc-attack-delta.tar.gz') as tar:
  for member in tar.getmembers():
   if member.name.startswith(kind+'/'):
    member.name=member.name[len(kind)+1:];tar.extract(member,root,filter='data')
 shutil.copy2(T/'libsmartpc_game_native.so',root/'libsmartpc_game_native.so')
 m=json.loads((root/'release-manifest.json').read_text());m['sha256']['libsmartpc_game_native.so']=hashlib.sha256((root/'libsmartpc_game_native.so').read_bytes()).hexdigest()
 (root/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
link=H/'smartpc-attack-project/theme-projects'
if not link.exists():link.symlink_to(H/'smartpc-menu-project/theme-projects',target_is_directory=True)
sys.path.insert(0,str(H/'smartpc-attack-project/dashboard'))
from game_direct_trainer import DirectTrainer
import numpy as np
G=H/'.local/share/SmartPC/SmartPC/game';dest=P/'private/saved';dest.mkdir(exist_ok=True)
with sqlite3.connect('file:'+str(G/'game.sqlite')+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
 assert not db.execute("SELECT 1 FROM sessions WHERE status='running'").fetchall()
 drivers=[dict(r) for r in db.execute('SELECT id,name,profile,checkpoint FROM drivers ORDER BY number')]
profiles={};rows=[]
for d in drivers:
 if not d['checkpoint']:continue
 original=G/'policies'/(d['checkpoint']+'.json');assert hashlib.sha256(original.read_bytes()).hexdigest()==d['checkpoint']
 old=json.loads(original.read_text());p={**json.loads(d['profile']),'trafficLearning':'attack-1','relativeAdvantage':0.}
 t=DirectTrainer(p,'oval-1',old,objective='impara_sorpasso');c=t.checkpoint(old.get('seconds',0.));method=p['algorithm'];profiles[method]=p
 np.testing.assert_array_equal(t.learner.actor,old['learner']['actor']);assert t.steps==old['steps']
 target=dest/(method+'.json');target.write_text(json.dumps(c));target.chmod(0o600)
 rows.append(dict(name=d['name'],sourceCheckpoint=d['checkpoint'],actorPreserved=True,steps=t.steps))
(dest/'profiles.json').write_text(json.dumps(profiles))
(P/'staging.json').write_text(json.dumps(dict(status='passed',rows=rows,productionChanges=False),indent=2)+'\n')
import subprocess
subprocess.run(['chown','-R','smartpc:smartpc',str(P),str(H/'smartpc-attack-project'),str(H/'smartpc-attack-runtime')],check=True)
print('Exact ARM source staged and personal copies migrated',flush=True)
