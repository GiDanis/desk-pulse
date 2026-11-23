"""Validate the uninstrumented installed process and its actual scanout."""
from pathlib import Path
import hashlib,json,os,pwd,sqlite3,subprocess,sys,time
W=Path('/var/lib/smartpc-dashboard/maintenance-work/graphics-fix');H=Path('/var/lib/smartpc-dashboard');R=Path('/opt/smartpc/dashboard');D=H/'.local/share/SmartPC/SmartPC'
sys.path.insert(0,str(W))
from aquarium_graphics_diagnostics import scanout_content
label=sys.argv[1];assert label in ('preboot','postboot','final')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def hashes(root):return {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file() and not p.is_symlink()}
s=dict(l.split('=',1) for l in subprocess.check_output(['systemctl','show','smartpc-dashboard.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True).splitlines());u=pwd.getpwnam('smartpc').pw_uid
root=Path('/proc')/s['MainPID']/'root/tmp';b=json.loads((root/('smartpc-theme-health-'+str(u))/(hashlib.sha256(os.fsencode(str(D))).hexdigest()+'.json')).read_text())
assert s['ActiveState']=='active' and s['NRestarts']=='0' and b['ready'] and not b['pending'] and time.time()-b['time']<5 and b['context']['surfaceId']=='aquarium.3d'
pid=b['pid'];env=dict(v.split('=',1) for v in Path('/proc/'+str(pid)+'/environ').read_bytes().decode().split('\0') if '=' in v)
assert env.get('SMARTPC_AQUARIUM_RENDERER','3d')=='3d'
assert env.get('SMARTPC_AQUARIUM_GRAPHICS_PROFILE')=='egl-query-bridge-no-shader-cache-v1' and env.get('QT_DISABLE_SHADER_DISK_CACHE')=='1'
assert not env.get('QSG_RHI_PIPELINE_CACHE_LOAD') and not env.get('QSG_RHI_PIPELINE_CACHE_SAVE')
assert env.get('LD_PRELOAD')==str(R/'libsmartpc_egl_context_bridge.so') and not env.get('SMARTPC_GL_PROBE_FILE')
lib=sorted({l.split()[-1] for l in Path('/proc/'+str(pid)+'/maps').read_text().splitlines() if any(k in l for k in ('libGLES','libEGL','PVR','egl_context_bridge'))});assert str(R/'libsmartpc_egl_context_bridge.so') in lib
m=json.loads((R/'release-manifest.json').read_text());assert m['version']=='0.10.2-rc.4' and len(m['sha256'])==550 and all(sha(R/n)==h for n,h in m['sha256'].items())
install=json.loads((W/'installation-rc4-receipt.json').read_text());backup=Path(install['backup']);p=json.loads((backup/'preservation.json').read_text())
assert hashes(H/'.config')==p['configuration']
with sqlite3.connect((D/'game/game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
 logical=hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest();assert logical==p['game']['logicalSha256']
artifacts={str(f.relative_to(D/'game')):sha(f) for f in (D/'game').rglob('*') if f.is_file() and not f.name.startswith('game.sqlite')};assert artifacts==p['game']['artifacts']
with sqlite3.connect((D/'aquarium/aquarium.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
 fish=db.execute('SELECT f.id,f.species,v.id FROM visits v JOIN fish f ON v.fish=f.id WHERE v.ended IS NULL ORDER BY v.slot').fetchall();assert [list(r) for r in fish]==p['fish']
assert json.loads((D/'theme-activation.json').read_text())['active']==p['theme']==b['selection']
assert hashlib.sha256(subprocess.check_output(['dpkg-query','-W','-f=${Package}\t${Version}\t${db:Status-Abbrev}\n'])).hexdigest()==p['packageStateSha256']
assert subprocess.check_output(['apt-mark','showhold'],text=True).splitlines()==p['holds']
messages=[json.loads(l) for l in subprocess.check_output(['journalctl','-b','-u','smartpc-dashboard.service','-o','json','--no-pager'],text=True).splitlines()]
needles=('Failed to build graphics pipeline','No GLSL shader code','Unsupported texture format','ReferenceError','TypeError','Unable to assign','Error loading QML','SIGSEGV')
issues=[r['MESSAGE'] for r in messages if str(r.get('_PID'))==str(pid) and isinstance(r.get('MESSAGE'),str) and any(n in r['MESSAGE'] for n in needles)];assert not issues,issues
out=W/('live-rc4-production-'+label+'-scanout');subprocess.run(['/usr/bin/python3',str(W/'capture-drm-scanout.py'),'--output',str(out)],check=True,stdout=subprocess.DEVNULL)
f=json.loads((out/'scanout.json').read_text());content=scanout_content((out/'scanout.raw').read_bytes(),f)
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
if label in ('postboot','final'):assert boot!=p['bootId']
report={'status':'passed','label':label,'observedAt':time.time(),'bootId':boot,'version':m['version'],'manifestSha256':sha(R/'release-manifest.json'),'runtimeFiles':550,'service':s,'gui':b,'graphicsProfile':env['SMARTPC_AQUARIUM_GRAPHICS_PROFILE'],'shaderDiskCacheDisabled':True,'explicitPipelineCacheAbsent':True,'ldPreload':env['LD_PRELOAD'],'nativeDiagnosticProbeAbsent':True,'libraries':lib,'scanout':f,'scanoutContent':content,'qmlGraphicsIssues':issues,'configurationPreserved':True,'gamePreserved':True,'gameArtifactsPreserved':len(artifacts),'activeFishIdentitiesAndVisitsPreserved':len(fish),'themePreserved':True,'osPackagesAndHoldsPreserved':True,'newOsBoot':boot!=p['bootId'],'nativeContextReference':'live-rc4-postrestart.json measures the same runtime/profile before removing the diagnostic probe; not this PID','scope':'Actual uninstrumented service, scanout content and persistence; not physical-panel, HID or optical FPS proof'}
(W/('live-rc4-production-'+label+'.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
