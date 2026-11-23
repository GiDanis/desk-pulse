"""One authorized rc.5 delivery; private verified rollback precedes activation.

Run as root on the board. Never copies the dirty workstation game implementation.
"""
from pathlib import Path
import gzip, hashlib, json, os, pwd, shutil, sqlite3, stat, subprocess, sys, tarfile, tempfile, time

W=Path(__file__).resolve().parent
H=Path('/var/lib/smartpc-dashboard'); D=H/'.local/share/SmartPC/SmartPC'
R=Path('/opt/smartpc/dashboard'); C=Path('/var/backups/smartpc-dashboard/20261030-calm-rc5/failed-runtime'); PY=H/'game-runtime/bin/python'
B=Path('/var/backups/smartpc-dashboard/20261030-calm-rc5-retry2')
PRIOR=Path('/var/backups/smartpc-dashboard/20261030-calm-rc5/snapshot')
CACHE=Path('/var/cache/smartpc-dashboard')
assert os.getuid()==0
os.umask(0o077)
candidate=json.loads((W/'candidate.json').read_text())
identity={'id':'studio.applecalm','version':candidate['themeVersion'],'digest':candidate['bundleDigest']}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def write(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def run(*args,**kwargs):return subprocess.run(list(map(str,args)),check=True,**kwargs)
def as_user(args,output):
 env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME='+str(CACHE),'QT_QPA_PLATFORM=offscreen','QSG_RHI_BACKEND=software','QT_DISABLE_SHADER_DISK_CACHE=1','SMARTPC_AQUARIUM_RENDERER=3d','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
 with Path(output).open('w') as f:run('sudo','-n','-u','smartpc','env',*env,PY,*args,stdout=f,stderr=subprocess.STDOUT)
def inventory(path):
 as_user([W/'collect-preservation.py'],path)
 return json.loads(Path(path).read_text())
def manifest(root,expected):
 assert sha(root/'release-manifest.json')==expected,'runtime manifest changed'
 m=json.loads((root/'release-manifest.json').read_text())
 assert all(sha(root/name)==digest for name,digest in m['sha256'].items()),'runtime bytes changed'
 return m
def sqlite_check(path):
 # SQLite may update SHM even for a read-only connection: validate a disposable
 # copy with its WAL/SHM, leaving the frozen, byte-verified snapshot untouched.
 with tempfile.TemporaryDirectory(prefix='sqlite-verification-',dir=B) as folder:
  target=Path(folder)/path.name
  for suffix in ('','-wal','-shm'):
   source=Path(str(path)+suffix)
   if source.exists():shutil.copy2(source,Path(str(target)+suffix))
  with sqlite3.connect(target.as_uri()+'?mode=ro',uri=True) as db:
   assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok',str(path)
   assert not db.execute('PRAGMA foreign_key_check').fetchall(),str(path)
def verify_archive(archive,snapshot):
 members={};inodes={};files=0;logical=0;hardlinks=0
 with tarfile.open(archive,'r:gz') as t:
  for m in t:
   p=archive.parent/m.name
   assert p==snapshot or snapshot in p.parents,m.name
   s=p.lstat();members[m.name]=m
   assert (m.uid,m.gid,m.mode)==(s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode)),m.name
   assert abs(m.mtime-s.st_mtime)<0.00001,m.name
   if p.is_symlink():assert m.issym() and m.linkname==os.readlink(p)
   elif p.is_dir():assert m.isdir()
   elif p.is_file():
    assert m.isfile() or m.islnk(),m.name
    h=hashlib.sha256();f=t.extractfile(m)
    for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    assert h.hexdigest()==sha(p),m.name
    if m.islnk():
     target=archive.parent/m.linkname;ts=target.stat()
     assert (ts.st_dev,ts.st_ino)==(s.st_dev,s.st_ino),m.name
     hardlinks+=1
    inodes.setdefault((s.st_dev,s.st_ino),[]).append(m.name);files+=1;logical+=s.st_size
   else:raise AssertionError('Unsupported backup node '+m.name)
 expected={'snapshot',*('snapshot/'+str(p.relative_to(snapshot)) for p in snapshot.rglob('*'))}
 assert set(members)==expected,'archive members differ'
 assert hardlinks==sum(len(names)-1 for names in inodes.values()),'hardlink groups differ'
 with gzip.open(archive,'rb') as g:
  while g.read(1024*1024):pass  # Consume trailer and CRC, including tar padding.
 return {'status':'verified','sha256':sha(archive),'members':len(members),'files':files,'logicalBytes':logical,'hardlinks':hardlinks,'metadata':'uid/gid/mode/mtime/symlinks and hardlink identity verified','gzip':'full stream and CRC verified'}
def health():
 s=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID','-p','ActiveState','-p','SubState','-p','NRestarts'],text=True).splitlines())
 pid=int(s['MainPID']);uid=pwd.getpwnam('smartpc').pw_uid
 key=hashlib.sha256(os.fsencode(str(D))).hexdigest()+'.json'
 p=Path('/proc')/str(pid)/'root/tmp'/('smartpc-theme-health-'+str(uid))/key
 h=json.loads(p.read_text())
 assert s['ActiveState']=='active' and s['SubState']=='running' and s['NRestarts']=='0',s
 # systemd owns the theme supervisor; the heartbeat belongs to its GUI child.
 gui=int(h['pid']);ancestor=gui
 for _ in range(8):
  if ancestor==pid:break
  status=(Path('/proc')/str(ancestor)/'status').read_text()
  ancestor=int(next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:')))
 else:raise AssertionError('GUI is not a child of the active service')
 assert b'/opt/smartpc/dashboard/app.py' in (Path('/proc')/str(gui)/'cmdline').read_bytes()
 assert h['ready'] and h['pending'] is None and h['selection']==identity,h
 assert time.time()-h['time']<5,h
 return s,h

assert not B.exists(),'Never overwrite a previous rollback'
assert shutil.disk_usage(H).free>10*1024**3
baseline=manifest(R,candidate['baselineManifestSha256'])
new=manifest(C,candidate['runtimeManifestSha256'])
assert len(new['sha256'])==candidate['runtimeFiles']==550
assert all(new['sha256'][n]==h for n,h in baseline['sha256'].items() if n.startswith('game') or n.endswith('.so'))
assert sha(W/'apple-calm-1.7.0.zip')==candidate['bundleArchiveSha256']
cache=json.loads((W/'candidate-source/theme-projects/apple-calm/evidence/preflight-cache.json').read_text())
assert cache['digest']==identity['digest'] and cache['result']['status']=='passed' and cache['result']['qt']=='6.8.2'
native=json.loads((W/'eglfs/day/report.json').read_text())
assert native['status']=='passed' and native['revision']['digest']==identity['digest'] and not native['qmlWarnings']
assert json.loads((W/'eglfs/qualification.json').read_text())['status']=='passed'
B.mkdir(parents=True,mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
started=time.time();moved_old=False;activated=False;selected=[]
run('systemctl','stop','smartpc-dashboard')
try:
 before=inventory(B/'before-private.json')
 selected=[R,*[p for p in H.iterdir() if p.name not in {'game-runtime','pilot-learner-runtime','maintenance-work'}],CACHE]
 selected=[p for p in selected if p.exists()]
 snapshot=B/'snapshot';snapshot.mkdir()
 run('rsync','-aH','--checksum','--relative','--link-dest='+str(PRIOR),*selected,snapshot)
 # Verify every copied node against the stopped originals before tar creation.
 original_inodes={};copied_inodes={};original_files=0
 for root in selected:
  for p in [root,*root.rglob('*')] if root.is_dir() else [root]:
   q=snapshot/str(p).lstrip('/');a=p.lstat();b=q.lstat()
   assert (a.st_mode,a.st_uid,a.st_gid,a.st_mtime_ns)==(b.st_mode,b.st_uid,b.st_gid,b.st_mtime_ns),str(p)
   if p.is_symlink():assert os.readlink(p)==os.readlink(q)
   elif p.is_file():
    assert sha(p)==sha(q),str(p);original_files+=1
    original_inodes.setdefault((a.st_dev,a.st_ino),set()).add(str(p))
    copied_inodes.setdefault((b.st_dev,b.st_ino),set()).add(str(p))
 assert {frozenset(v) for v in original_inodes.values()}=={frozenset(v) for v in copied_inodes.values()}
 for path in [D/'game/game.sqlite',D/'aquarium/aquarium.sqlite',H/'events.sqlite3']:
  if path.exists():sqlite_check(snapshot/str(path).lstrip('/'))
 archive=B/'before.tar.gz'
 with tarfile.open(archive,'w:gz',compresslevel=3,dereference=False) as t:t.add(snapshot,arcname='snapshot')
 backup=verify_archive(archive,snapshot);backup['originalFilesCompared']=original_files
 write(B/'backup-verification.json',backup);write(W/'backup-public.json',backup)
 print('PASS private backup: bytes, metadata, hardlinks, database integrity and gzip',flush=True)
 # Both paths are local on the same filesystem; retain the old runtime intact.
 assert R.stat().st_dev==C.stat().st_dev
 run('chown','-R','root:root',C)
 R.rename(B/'previous-runtime');moved_old=True;C.rename(R)
 code='''import json,sys
from pathlib import Path
sys.path.insert(0,"/opt/smartpc/dashboard")
from theme_bundle import BundleManager, manager_lock, sync_directory, semver
import os,shutil,tempfile
from PySide6.QtCore import qVersion
w=Path(sys.argv[1]);c=json.loads((w/"candidate.json").read_text());cache=json.loads((w/"candidate-source/theme-projects/apple-calm/evidence/preflight-cache.json").read_text())
def checked(payload,manifest,registry):
 assert cache["digest"]==c["bundleDigest"] and cache["result"]["qt"]==qVersion() and cache["result"]["status"]=="passed"
 return cache["result"]
# Validate the archive with the unchanged guarded importer on RAM. SD fsync
# latency must not consume its anti-abuse extraction deadline. Then persist
# exactly that verified revision, fsync, atomically rename, and reverify.
destination=BundleManager(Path("/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC"),app_root=Path("/opt/smartpc/dashboard"))
with tempfile.TemporaryDirectory(prefix="smartpc-calm-import-",dir="/dev/shm") as ram:
 source=BundleManager(Path(ram),app_root=Path("/opt/smartpc/dashboard"))
 r=source.import_bundle(w/"apple-calm-1.7.0.zip",preflight=checked,require_preflight=True)
 identity={k:r[k] for k in ("id","version","digest")}
 with manager_lock(destination.root):
  final=destination._revision_path(identity)
  assert not final.exists() and not list(final.parent.glob(identity["version"]+"-*"))
  stage=Path(tempfile.mkdtemp(prefix=".verified-import-",dir=destination.root/"theme-staging"))
  try:
   shutil.copytree(Path(r["path"]),stage,dirs_exist_ok=True)
   for path in stage.rglob("*"):
    if path.is_file():
     fd=os.open(path,os.O_RDONLY)
     try:os.fsync(fd)
     finally:os.close(fd)
   for directory,_,_ in os.walk(stage,topdown=False):sync_directory(Path(directory))
   final.parent.mkdir(parents=True,exist_ok=True);os.rename(stage,final);sync_directory(final.parent)
  finally:
   if stage.exists():shutil.rmtree(stage)
 r=destination.verify_revision(identity)
assert r["digest"]==c["bundleDigest"]
print(json.dumps({k:r[k] for k in ("id","version","digest")}))
'''
 as_user(['-c',code,W],B/'import.log')
 for apply,folder in [(True,'activation'),(False,'cold-verify')]:
  args=[W/'candidate-source/theme-projects/apple-calm/tools/activate_board.py','--dashboard',R,'--output',W/folder,'--manifest',W/'candidate.json']
  if apply:args+=['--apply']
  as_user(args,B/(folder+'.log'))
 stopped=inventory(B/'after-activation-private.json')
 assert before['databases']==stopped['databases'],'activation changed protected databases'
 assert before['gameArtifacts']==stopped['gameArtifacts'],'activation changed pilot artifacts'
 assert before['fishIds']==stopped['fishIds'] and before['visitIds']==stopped['visitIds']
 allowed=lambda k:k.startswith('appearance/')
 assert all(stopped['preferenceHashes'].get(k)==v for k,v in before['preferenceHashes'].items() if not allowed(k)),'user preferences changed'
 assert stopped['appearancePersonalization']==before['appearancePersonalization'],'palette/motion/text scale changed'
 assert stopped['theme']==identity
 manifest(R,candidate['runtimeManifestSha256'])
 print('PASS activation and cold load; protected data and preferences preserved',flush=True)
 run('systemctl','start','smartpc-dashboard')
 deadline=time.monotonic()+90;last=None
 while time.monotonic()<deadline:
  try:
   s,h=health()
   if last and h['time']>last:break
   last=h['time']
  except (AssertionError,FileNotFoundError,ValueError,ProcessLookupError):pass
  time.sleep(1)
 else:raise AssertionError('No fresh ready GUI heartbeat')
 after=inventory(B/'after-live-private.json')
 assert before['gameArtifacts']==after['gameArtifacts'],'pilot artifacts changed at startup'
 assert before['databases']['game']==after['databases']['game'],'pilot database changed at startup'
 assert set(before['fishIds'])<=set(after['fishIds']) and set(before['visitIds'])<=set(after['visitIds']),'aquarium history lost'
 assert all(after['preferenceHashes'].get(k)==v for k,v in before['preferenceHashes'].items() if not allowed(k)),'user preferences changed at startup'
 assert after['appearancePersonalization']==before['appearancePersonalization'],'palette/motion/text scale changed at startup'
 assert after['theme']==identity
 manifest(R,candidate['runtimeManifestSha256'])
 journal=subprocess.check_output(['journalctl','-u','smartpc-dashboard','_PID='+str(h['pid']),'--since','@'+str(int(started)),'--no-pager','-o','cat'],text=True)
 (B/'installed-journal-private.txt').write_text(journal)
 warnings=[line for line in journal.splitlines() if any(term in line for term in ['ReferenceError:','TypeError:','Cannot assign','Unable to assign','QQmlApplicationEngine failed','failed to create OpenGL','Failed to initialize'])]
 assert not warnings,'QML or graphics warning in installed service; see private journal'
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
 report={'status':'installed','version':candidate['version'],'runtimeManifestSha256':candidate['runtimeManifestSha256'],'runtimeFiles':550,'theme':identity,'themeApi':'2.15','service':s,'guiPid':h['pid'],'freshReadyHeartbeat':True,'heartbeatContext':h.get('context'),'qmlGraphicsWarnings':warnings,'sameBoot':True,'rebootPerformed':False,'gameDatabaseAndArtifactsPreserved':True,'gameArtifacts':len(after['gameArtifacts']),'aquariumFishPreserved':len(before['fishIds']),'aquariumVisitsPreserved':len(before['visitIds']),'nonAppearancePreferencesPreserved':True,'paletteMotionTextScalePreserved':True,'preferenceCount':len(before['preferenceHashes']),'backup':backup,'privateBackupDirectory':str(B),'rollbackRuntime':str(B/'previous-runtime'),'freeBytes':shutil.disk_usage(H).free,'scope':'Installed and native EGLFS verified; physical input/optical readability, live goal/VAR and prolonged soak remain open'}
 write(W/'installation.json',report);write(B/'installation.json',report)
 activated=True;print(json.dumps(report),flush=True)
except BaseException:
 if moved_old:
  run('systemctl','stop','smartpc-dashboard')
  if R.exists():R.rename(B/'failed-runtime')
  (B/'previous-runtime').rename(R)
  failed=B/'failed-state';failed.mkdir()
  # Preserve failed state as well, then restore exactly the verified snapshot.
  for original in selected:
   if original==R:continue
   if original.exists():
    target=failed/str(original).lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);original.rename(target)
   original.parent.mkdir(parents=True,exist_ok=True)
   run('cp','-a',B/'snapshot'/str(original).lstrip('/'),original)
  print('ROLLED BACK to verified previous runtime and data',flush=True)
 raise
finally:
 if not activated:run('systemctl','start','smartpc-dashboard')
