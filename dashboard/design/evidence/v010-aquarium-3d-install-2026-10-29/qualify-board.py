"""Bounded candidate qualification with installed Qt dependencies and private data."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
W=Path('/var/lib/smartpc-dashboard/maintenance-work');H=W.parent;R=W/'runtime';D=W/'source/dashboard';PY=H/'game-runtime/bin/python'
r=json.loads((R/'release-manifest.json').read_text());d=json.loads((D/'release-manifest.json').read_text());assert r['version']=='0.10.2-rc.1'
assert all(d['sha256'][f]==v for f,v in r['sha256'].items())
assert all(hashlib.sha256((D/f).read_bytes()).hexdigest()==v for f,v in d['sha256'].items())
base=['HOME='+str(H),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','LD_PRELOAD=/usr/local/lib/libGLESv2.so.2','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
rows=[]
def run(name,args,seconds=240,env=base):
 out=W/'qualification'/name;out.mkdir(parents=True,exist_ok=True);subprocess.run(['chown','-R','smartpc:smartpc',str(out)],check=True)
 with (out/'run.log').open('w') as log:
  child=subprocess.Popen(['runuser','-u','smartpc','--','env',*env,str(PY),*args,'--output',str(out)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True);start=last=time.monotonic()
  try:
   while child.poll() is None:
    now=time.monotonic()
    if now-start>seconds:raise TimeoutError(name)
    if now-last>45:print('RUNNING',name,round(now-start),flush=True);last=now
    time.sleep(1)
  except BaseException:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=5)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
   raise
 assert child.returncode==0,(name,(out/'run.log').read_text()[-3000:])
 report=json.loads((out/'report.json').read_text());assert report['status']=='passed'
 rows.append({'case':name,'checks':len(report.get('checks',[])),'callbacksPerSecond':report.get('callbacksPerSecond'),'p95Ms':report.get('p95Ms'),'report':str(out/'report.json')});print('RESULT',json.dumps(rows[-1]),flush=True)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 for name,theme,duration,warmup in [('base','base',3,1),('functional','functional',3,1),('apple','studio.applecalm',120,60)]:
  args=[str(W/'source/scripts/check-aquarium-3d.py'),'--theme',theme,'--seconds',str(duration),'--warmup',str(warmup)]
  if name=='apple':args+=['--theme-data',str(H/'.local/share/SmartPC/SmartPC')]
  run(name,args,seconds=duration+warmup+100)
 run('main-game',[str(W/'smoke-main.py'),'--dashboard',str(D),'--theme','apple'],seconds=180)
 (W/'qualification-receipt.json').write_text(json.dumps({'status':'passed','version':r['version'],'runtimeManifestSha256':hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest(),'diagnosticManifestSha256':hashlib.sha256((D/'release-manifest.json').read_bytes()).hexdigest(),'installedDependencies':True,'cases':rows,'scope':'Private Main EGLFS960x640, three themes, one nominal120s after60s, Home/domains/Game Start-Pause-Save; not optical/physical/live qualification.'},indent=2)+'\n')
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
