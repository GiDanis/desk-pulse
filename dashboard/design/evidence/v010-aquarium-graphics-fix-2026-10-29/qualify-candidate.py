from pathlib import Path
import subprocess,json,os,time,pwd,hashlib,signal
W=Path('/var/lib/smartpc-dashboard/maintenance-work/graphics-fix');D=W/'candidate/dashboard';PY='/var/lib/smartpc-dashboard/game-runtime/bin/python';H=Path('/var/lib/smartpc-dashboard');DATA=H/'.local/share/SmartPC/SmartPC'
assert os.geteuid()==0 and os.environ.get('INVOCATION_ID')
m=json.loads((D/'release-manifest.json').read_text());assert m['version']=='0.10.2-rc.3';assert all(hashlib.sha256((D/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
mode=os.environ.get('SMARTPC_QUALIFY_CASE','smoke');cases=[('apple-smoke','studio.applecalm',3,1)] if mode=='smoke' else [('apple-nominal','studio.applecalm',120,60),('base','base',3,1),('functional','functional',3,1)]
root=W/('qualification-'+mode);root.mkdir(parents=True,exist_ok=True);uid=pwd.getpwnam('smartpc').pw_uid;gid=pwd.getpwnam('smartpc').pw_gid;rows=[]
try:
 subprocess.run(['systemctl','stop','smartpc-dashboard.service'],check=True,timeout=25)
 for name,theme,duration,warmup in cases:
  out=root/name;out.mkdir(parents=True,exist_ok=True);os.chown(out,uid,gid)
  env=['HOME='+str(H),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','LD_PRELOAD='+str(W/'gl-probe.so')+':'+str(D/'libsmartpc_egl_context_bridge.so'),'SMARTPC_GL_PROBE_FILE='+str(out/'native-context.json'),'SMARTPC_AQUARIUM_RENDERER=3d','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1']
  args=[PY,str(W/'candidate/scripts/check-aquarium-3d.py'),'--output',str(out),'--theme',theme,'--seconds',str(duration),'--warmup',str(warmup)]
  if theme=='studio.applecalm':args+=['--theme-data',str(DATA)]
  print('BEGIN',name,flush=True)
  with (out/'run.log').open('w') as log:
   child=subprocess.Popen(['runuser','-u','smartpc','--','env',*env,*args],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   try:code=child.wait(timeout=duration+warmup+95)
   except BaseException:
    os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    raise
  if code:raise RuntimeError((out/'run.log').read_text()[-3500:])
  a=json.loads((out/'report.json').read_text());assert a['status']=='passed'
  rows.append({'case':name,'status':a['status'],'checks':len(a['checks']),'glContext':a['glContext'],'callbacksPerSecond':a['callbacksPerSecond'],'p95Ms':a['p95Ms'],'p99Ms':a['p99Ms'],'maxMs':a['maxMs'],'stallsOver50Ms':a['stallsOver50Ms']});print('RESULT',json.dumps(rows[-1]),flush=True)
finally:
 try:(root/'receipt.json').write_text(json.dumps({'cases':rows,'candidateVersion':m['version'],'scope':'Private data, real Main, EGLFS960x640; no full GLES preload; no optical or physical panel proof'},indent=2)+'\n')
 finally:subprocess.run(['systemctl','start','smartpc-dashboard.service'],check=True,timeout=35)
 print('RECOVERY_2D_STARTED',flush=True)
