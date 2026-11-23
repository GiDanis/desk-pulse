"""Install qualified rc4 atomically, retaining the persistent 2D recovery override."""
from pathlib import Path
import hashlib,json,os,pwd,shutil,sqlite3,subprocess,time
H=Path('/var/lib/smartpc-dashboard');W=H/'maintenance-work/graphics-fix';R=Path('/opt/smartpc/dashboard');C=W/'runtime-rc4';DATA=H/'.local/share/SmartPC/SmartPC';G=DATA/'game'
assert os.geteuid()==0
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(root):return {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
def game(root=G):
 with sqlite3.connect((root/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
  logical=hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
 return {'logicalSha256':logical,'artifacts':{str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and not p.name.startswith('game.sqlite')}}
def fish():
 with sqlite3.connect((DATA/'aquarium/aquarium.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
  return db.execute('SELECT f.id,f.species,v.id FROM visits v JOIN fish f ON v.fish=f.id WHERE v.ended IS NULL ORDER BY v.slot').fetchall()
def ready():
 end=time.monotonic()+85;uid=pwd.getpwnam('smartpc').pw_uid;name=hashlib.sha256(os.fsencode(str(DATA))).hexdigest()+'.json'
 while time.monotonic()<end:
  s=dict(r.split('=',1) for r in subprocess.check_output(['systemctl','show','smartpc-dashboard.service','-p','MainPID','-p','NRestarts','-p','ActiveState'],text=True).splitlines())
  try:
   b=json.loads((Path('/proc')/s['MainPID']/'root/tmp'/('smartpc-theme-health-'+str(uid))/name).read_text())
   if s['ActiveState']=='active' and b['ready'] and not b['pending'] and time.time()-b['time']<5:return s,b
  except (OSError,KeyError,ValueError):pass
  time.sleep(1)
 raise TimeoutError('GUI readiness deadline')
prior=json.loads((R/'release-manifest.json').read_text());new=json.loads((C/'release-manifest.json').read_text());d=json.loads((W/'candidate-rc4/dashboard/release-manifest.json').read_text());q=json.loads((W/'qualification-rc4-nominal/receipt.json').read_text())
assert json.loads((W/'main-smoke/report.json').read_text())['status']=='passed'
assert prior['version']=='0.10.2-rc.3' and new['version']=='0.10.2-rc.4' and len(new['sha256'])==550
assert new['sourceBaseline']['manifestSha256']==sha(R/'release-manifest.json')
assert len(q['cases'])==3 and all(c['status']=='passed' and c['checks']==21 and c['glContext']['qtRhiVersion']>=[3,0] for c in q['cases'])
for root,m in ((R,prior),(C,new)):assert all(sha(root/n)==h for n,h in m['sha256'].items())
assert all(d['sha256'][n]==h for n,h in new['sha256'].items())
changed={n for n,h in prior['sha256'].items() if new['sha256'].get(n)!=h};assert changed=={'run.sh','version.py'},changed
assert set(new['sha256'])-set(prior['sha256'])==set()
assert 'SMARTPC_AQUARIUM_RENDERER=2d' in Path('/etc/systemd/system/smartpc-dashboard.service.d/90-aquarium-graphics-recovery.conf').read_text()
subprocess.run(['systemctl','stop','smartpc-graphics-trial-recovery.timer'],check=True)
stage=W/'install-ready-rc4';shutil.copytree(C,stage);subprocess.run(['chown','-R','root:root',str(stage)],check=True)
B=Path('/var/backups/smartpc-maintenance')/('rollback-0.10.2-rc.3-graphics-fix-'+time.strftime('%Y%m%d-%H%M%S'));B.mkdir(mode=0o700)
subprocess.run(['systemctl','stop','smartpc-dashboard.service'],check=True,timeout=25);switched=False
try:
 original={'configuration':hashes(H/'.config'),'game':game(),'fish':fish(),'theme':json.loads((DATA/'theme-activation.json').read_text())['active'],'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'packageStateSha256':hashlib.sha256(subprocess.check_output(['dpkg-query','-W','-f=${Package}\t${Version}\t${db:Status-Abbrev}\n'])).hexdigest(),'holds':subprocess.check_output(['apt-mark','showhold'],text=True).splitlines()}
 (B/'state').mkdir();(B/'system').mkdir()
 for src,dst in [(R,B/'runtime'),(H/'.config',B/'state/.config'),(Path('/etc/systemd/system/smartpc-dashboard.service.d'),B/'system/smartpc-dashboard.service.d')]:subprocess.run(['cp','-a','--reflink=auto',str(src),str(dst)],check=True)
 subprocess.run(['rsync','-aH','--checksum','--link-dest=/var/backups/smartpc-maintenance/rollback-0.10.2-rc.2-graphics-fix-20261029-134638/state/.local',str(H/'.local')+'/',str(B/'state/.local')+'/'],check=True)
 for p in H.iterdir():
  if p.is_file() and (p.suffix in ('.json','.sqlite3') or p.name.startswith('events.sqlite3-')):subprocess.run(['cp','-a',str(p),str(B/'state'/p.name)],check=True)
 assert hashes(B/'state/.config')==original['configuration'] and hashes(B/'state/.local')==hashes(H/'.local')
 assert game(B/'state/.local/share/SmartPC/SmartPC/game')==original['game']
 assert all(sha(B/'runtime'/n)==h for n,h in prior['sha256'].items())
 (B/'preservation.json').write_text(json.dumps(original,indent=2)+'\n');(B/'backup-manifest.json').write_text(json.dumps({'sha256':hashes(B)},indent=2)+'\n');os.sync()
 R.rename(W/'replaced-runtime-rc3');stage.rename(R);switched=True
 subprocess.run(['systemctl','start','smartpc-dashboard.service'],check=True);s,b=ready()
 assert s['NRestarts']=='0' and b['selection']==original['theme'] and b['context']['surfaceId']=='home.now'
 assert hashes(H/'.config')==original['configuration'] and game()==original['game'] and fish()==original['fish']
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==original['bootId']
 assert all(sha(R/n)==h for n,h in new['sha256'].items())
 report={'status':'passed','installedVersion':new['version'],'files':550,'manifestSha256':sha(R/'release-manifest.json'),'backup':str(B),'service':s,'gui':b,'configurationPreserved':True,'gamePreserved':True,'gameArtifacts':len(original['game']['artifacts']),'activeFishIdentitiesPreserved':len(original['fish']),'sameBoot':True,'renderer':'2d','mainSmokeReuse':'rc3 Main/QML/geometry identical; only launcher and version change','scope':'Qualified rc4 installed with persistent 2D recovery; actual scanout, reboot and physical acceptance follow separately'}
 (W/'installation-rc4-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
except BaseException:
 subprocess.run(['systemctl','stop','smartpc-dashboard.service'],check=True)
 if switched:
  R.rename(W/'failed-runtime-rc4');(W/'replaced-runtime-rc3').rename(R)
 raise
finally:subprocess.run(['systemctl','start','smartpc-dashboard.service'],check=True)
