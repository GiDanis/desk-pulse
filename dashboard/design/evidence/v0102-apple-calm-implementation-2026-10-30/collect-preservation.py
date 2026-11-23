"""Read-only preservation inventory. Detailed output belongs in a private backup."""
from pathlib import Path
import hashlib,json,os,sqlite3,subprocess
H=Path('/var/lib/smartpc-dashboard');D=H/'.local/share/SmartPC/SmartPC';R=Path('/opt/smartpc/dashboard');PY=H/'game-runtime/bin/python'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prefs_code='''from PySide6.QtCore import QCoreApplication,QSettings
import hashlib,json
app=QCoreApplication([]);s=QSettings("SmartPC","Dashboard");s.sync()
cfg=json.loads(s.value("appearance/config","{}"))
print(json.dumps({"hashes":{k:hashlib.sha256(json.dumps(s.value(k),sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest() for k in s.allKeys()},"personalization":{"paletteMode":cfg.get("paletteMode"),"motionMode":cfg.get("motionMode"),"textScale":cfg.get("overrides",{}).get("tokens",{}).get("typography.textScale",1)}},sort_keys=True))'''
env={**os.environ,'HOME':str(H),'XDG_CONFIG_HOME':str(H/'.config')}
prefs=json.loads(subprocess.check_output([str(PY),'-c',prefs_code],env=env,text=True))
report={'preferenceHashes':prefs['hashes'],'appearancePersonalization':prefs['personalization'],'configuration':{str(p.relative_to(H/'.config')):sha(p) for p in (H/'.config').rglob('*') if p.is_file()},'runtimeManifestSha256':sha(R/'release-manifest.json'),'databases':{},'gameArtifacts':{},'fishIds':[],'visitIds':[],'activeFish':[],'theme':json.loads((D/'theme-activation.json').read_text())['active']}
for key,p in [('game',D/'game/game.sqlite'),('aquarium',D/'aquarium/aquarium.sqlite'),('events',H/'events.sqlite3')]:
 if not p.exists():continue
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok',key
  assert not db.execute('PRAGMA foreign_key_check').fetchall(),key
  tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
  report['databases'][key]={'integrity':'ok','foreignKeys':'ok','logicalSha256':hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest(),'rows':{t:db.execute('SELECT COUNT(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}}
  if key=='aquarium':
   report['fishIds']=[r[0] for r in db.execute('SELECT id FROM fish ORDER BY id')]
   report['visitIds']=[r[0] for r in db.execute('SELECT id FROM visits ORDER BY id')]
   report['activeFish']=[list(r) for r in db.execute('SELECT fish,id FROM visits WHERE ended IS NULL ORDER BY slot')]
for p in (D/'game').rglob('*'):
 if p.is_file() and not p.name.startswith('game.sqlite'):report['gameArtifacts'][str(p.relative_to(D/'game'))]=sha(p)
print(json.dumps(report,sort_keys=True))
