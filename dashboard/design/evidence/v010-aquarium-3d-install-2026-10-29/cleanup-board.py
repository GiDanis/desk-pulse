"""Remove only exported installation work after complete archive verification."""
from pathlib import Path
import hashlib,json,os,pwd,shutil,subprocess,sys,time
W=Path('/var/lib/smartpc-dashboard/maintenance-work');R=Path('/opt/smartpc/dashboard');D=W.parent/'.local/share/SmartPC/SmartPC'
assert W.is_dir() and not W.is_symlink();raw=(W/'export-manifest.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==sys.argv[1];entries=json.loads(raw)['entries']
for n,r in entries.items():
 f=W/n
 if r['type']=='file':assert f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256'],n
 else:assert f.is_symlink() and os.readlink(f)==r['target'],n
for f in Path('/proc').glob('[0-9]*/cmdline'):
 try:assert os.fsencode(str(W)) not in f.read_bytes(),'Process still using work path: '+str(f.parent)
 except (PermissionError,FileNotFoundError,ProcessLookupError):pass
m=json.loads((R/'release-manifest.json').read_text());assert m['version']=='0.10.2-rc.2' and len(m['sha256'])==548 and all(hashlib.sha256((R/f).read_bytes()).hexdigest()==v for f,v in m['sha256'].items())
s=dict(row.split('=',1) for row in subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID,NRestarts,ActiveState'],text=True).splitlines());assert s['ActiveState']=='active' and s['NRestarts']=='0'
uid=pwd.getpwnam('smartpc').pw_uid;b=json.loads((Path('/proc')/s['MainPID']/'root/tmp'/('smartpc-theme-health-'+str(uid))/(hashlib.sha256(os.fsencode(str(D))).hexdigest()+'.json')).read_text());assert b['ready'] and b['context']['surfaceId']=='aquarium.3d' and time.time()-b['time']<5
assert hashlib.sha256((W/'restore-runtime.py').read_bytes()).hexdigest()==hashlib.sha256(Path('/var/backups/smartpc-maintenance/restore-aquarium3d-0.10.2.py').read_bytes()).hexdigest()
shutil.rmtree(W);assert not W.exists()
print(json.dumps({'status':'passed','version':m['version'],'runtimeFiles':len(m['sha256']),'service':s,'guiReady':b['ready'],'guiPid':b['pid'],'activeSurface':b['context']['surfaceId'],'observedAt':time.time(),'exportedEntriesVerifiedAgain':len(entries),'removedOnly':str(W),'workDirectoryAbsent':True,'rollbackAndDataRetained':True},indent=2))
