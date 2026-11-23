"""Final preservation, installed graphics, persistent fish and journal audit."""
from pathlib import Path
import hashlib,json,os,pwd,sqlite3,subprocess,time
W=Path('/var/lib/smartpc-dashboard/maintenance-work');R=Path('/opt/smartpc/dashboard');H=W.parent;DATA=H/'.local/share/SmartPC/SmartPC';G=DATA/'game';B=Path(json.loads((W/'backup-receipt.json').read_text())['backup']);original=json.loads((B/'preservation.json').read_text())
m=json.loads((R/'release-manifest.json').read_text());assert m['version']=='0.10.2-rc.2' and all(hashlib.sha256((R/f).read_bytes()).hexdigest()==v for f,v in m['sha256'].items())
with sqlite3.connect((G/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall();logical=hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
assert logical==original['game']['logicalSha256']
a={str(f.relative_to(G)):hashlib.sha256(f.read_bytes()).hexdigest() for f in G.rglob('*') if f.is_file() and not f.name.startswith('game.sqlite')};assert a==original['game']['artifacts']
c={str(f.relative_to(H/'.config')):hashlib.sha256(f.read_bytes()).hexdigest() for f in (H/'.config').rglob('*') if f.is_file()};assert c==original['configurationHashes']
s=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID,NRestarts,ActiveState'],text=True).splitlines());pid=s['MainPID'];uid=pwd.getpwnam('smartpc').pw_uid;assert s['NRestarts']=='0' and s['ActiveState']=='active'
b=json.loads((Path('/proc')/pid/'root/tmp'/('smartpc-theme-health-'+str(uid))/(hashlib.sha256(os.fsencode(str(DATA))).hexdigest()+'.json')).read_text());assert b['ready'] and b['context']['surfaceId']=='aquarium.3d' and time.time()-b['time']<5
libraries=sorted({Path(row.split()[-1]).name for row in (Path('/proc')/str(b['pid'])/'maps').read_text().splitlines() if any(k in row for k in ('libGLES','libEGL','Quick3D','PVR'))});assert 'libGLESv2.so.2.0.0' in libraries and any('Quick3D' in k for k in libraries)
with sqlite3.connect((DATA/'aquarium/aquarium.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall();active,shown=db.execute('SELECT COUNT(*),COUNT(shown) FROM visits WHERE ended IS NULL').fetchone();assert active==shown==6
activation=json.loads((DATA/'theme-activation.json').read_text())['active'];assert activation==original['theme']==b['selection']
install=json.loads((W/'installation-rc2-receipt.json').read_text());pids={str(b['pid']),str(install['guiHeartbeat']['pid'])};start=int((W/'installed-health.json').stat().st_mtime)-5
records=[json.loads(row) for row in subprocess.check_output(['journalctl','-u','smartpc-dashboard','--since','@'+str(start),'-o','json','--no-pager'],text=True).splitlines()];messages=[r.get('MESSAGE','') for r in records if r.get('_PID') in pids]
needles=('Failed to build graphics pipeline','No GLSL shader code','Unsupported texture format','ReferenceError','TypeError','Unable to assign','Error loading QML','SIGSEGV');issues=[x for x in messages if any(n in x for n in needles)];assert not issues,issues
known=0
for i,x in enumerate(messages):
 if x.startswith('Traceback'):
  block='\n'.join(messages[i:i+15]);assert 'multiprocessing/synchronize.py' in block and 'sem_unlink(name)' in block and 'FileNotFoundError' in block,'Unknown Python exception';known+=1
parse=lambda text:{r.split('\t')[0]:r.split('\t')[1:] for r in text.splitlines()}
before=parse(original['packageState']);after=parse(subprocess.check_output(['dpkg-query','-W','-f=${Package}\t${Version}\t${db:Status-Abbrev}\n'],text=True));added=set(after)-set(before);assert added=={'libqt6quick3d6','libqt6quick3druntimerender6','libqt6quick3dutils6','libqt6shadertools6','python3-pyside6.qtquick3d','qml6-module-qtquick3d'}
assert all(after.get(k)==v for k,v in before.items());assert subprocess.check_output(['apt-mark','showhold'],text=True).splitlines()==original['heldPackages']
report={'status':'passed','version':m['version'],'runtimeFiles':len(m['sha256']),'manifestSha256':hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest(),'service':s,'guiPid':b['pid'],'guiReady':True,'activeSurface':b['context'],'activeTheme':activation,'activeFish':active,'shownAcknowledged':shown,'gameDatabasePreserved':True,'gameArtifactsPreserved':len(a),'configurationBytesPreserved':True,'graphicsLibraries':libraries,'qmlOrGraphicsIssuesInRc2Journal':0,'knownPreexistingSemaphoreShutdownExceptions':known,'osPackagesAdded':{k:after[k][0] for k in sorted(added)},'allPreviousPackagesAndHoldsPreserved':True,'sameBoot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()==original['bootId'],'observedAt':time.time(),'scope':'Installed rc2 after service restart and synthetic dedicated-keypad events. Six persistent fish and frame ACKs; not optical or physical-keypad qualification.'}
(W/'final-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
