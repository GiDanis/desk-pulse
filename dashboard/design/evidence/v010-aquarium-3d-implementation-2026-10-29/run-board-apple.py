"""Bounded isolated EGLFS checks. Always restore the installed service."""
from pathlib import Path
import hashlib,json,os,signal,sqlite3,subprocess,time
P=Path('/var/lib/smartpc-dashboard/maintenance-work');H=P.parent;R=Path('/opt/smartpc/dashboard');PY=H/'game-runtime/bin/python';OVER=P/'qt3d-overlay';DATA=H/'.local/share/SmartPC/SmartPC'

def fingerprint():
 manifest=json.loads((R/'release-manifest.json').read_text());assert all(hashlib.sha256((R/f).read_bytes()).hexdigest()==digest for f,digest in manifest['sha256'].items())
 game=DATA/'game'
 with sqlite3.connect((game/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  logical=hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
 return {'manifest':hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest(),'version':manifest['version'],'files':len(manifest['sha256']),'gameDatabase':logical,'gameArtifacts':{str(f.relative_to(game)):hashlib.sha256(f.read_bytes()).hexdigest() for f in game.rglob('*') if f.is_file() and not f.name.startswith('game.sqlite')},'preferences':{str(f.relative_to(H/'.config/SmartPC')):hashlib.sha256(f.read_bytes()).hexdigest() for f in (H/'.config/SmartPC').rglob('*') if f.is_file()},'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}

def source_hashes():
 m=json.loads((P/'dashboard/release-manifest.json').read_text())
 assert all(hashlib.sha256((P/'dashboard'/f).read_bytes()).hexdigest()==digest for f,digest in m['sha256'].items())
 return hashlib.sha256((P/'dashboard/release-manifest.json').read_bytes()).hexdigest()

before=fingerprint();frozen=source_hashes();results=[]
cases=[('apple','studio.applecalm',120,60)]
protocol={'sourceManifestSha256':frozen,'benchSha256':hashlib.sha256((P/'scripts/check-aquarium-3d.py').read_bytes()).hexdigest(),'cases':cases,'scope':'Three focused native workflows, one120s performance sample. No full theme matrix, three nominal repeats or long soak. Private store and providers; no production install.'}
(P/'board-apple-protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
env=['HOME='+str(H),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','LD_LIBRARY_PATH='+str(OVER/'usr/lib/aarch64-linux-gnu'),'QML_IMPORT_PATH='+str(OVER/'usr/lib/aarch64-linux-gnu/qt6/qml'),'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','PYTHONFAULTHANDLER=1','LD_PRELOAD=/usr/local/lib/libGLESv2.so.2']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 for name,theme,seconds,warmup in cases:
  assert source_hashes()==frozen
  out=P/'results'/name;out.mkdir(parents=True,exist_ok=True);subprocess.run(['chown','-R','smartpc:smartpc',str(out)],check=True)
  args=['runuser','-u','smartpc','--','env',*env,str(PY),str(P/'scripts/check-aquarium-3d.py'),'--output',str(out),'--theme',theme,'--seconds',str(seconds),'--warmup',str(warmup),'--qt3d-overlay',str(OVER)]
  if name=='apple':args+=['--theme-data',str(DATA)]
  with (out/'run.log').open('w') as log:
   child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);start=last=time.monotonic()
   try:
    while child.poll() is None:
     now=time.monotonic()
     if now-start>(60 if name=='base' else seconds+warmup+110):raise TimeoutError(name)
     if now-last>=45:print('RUNNING',name,round(now-start),flush=True);last=now
     time.sleep(1)
   except BaseException:
    os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    raise
  assert child.returncode==0,(name,child.returncode,(out/'run.log').read_text()[-4500:])
  report=json.loads((out/'report.json').read_text());assert report['status']=='passed'
  results.append({'case':name,'report':'results/'+name+'/report.json','callbacksPerSecond':report['callbacksPerSecond'],'p95Ms':report['p95Ms'],'checks':len(report['checks'])})
  print('RESULT',json.dumps(results[-1]),flush=True)
finally:
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 after=fingerprint();receipt={'status':'passed' if len(results)==len(cases) and before==after else 'incomplete','productionUnchanged':before==after,'sourceUnchanged':source_hashes()==frozen,'sameBoot':before['bootId']==after['bootId'],'baselineVersion':before['version'],'baselineFiles':before['files'],'gameArtifacts':len(before['gameArtifacts']),'results':results,'sourceManifestSha256':frozen}
 (P/'board-apple-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 assert before==after,'Production state changed'
