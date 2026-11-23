"""Bounded native EGLFS checks on isolated data, after the kiosk is stopped."""
from pathlib import Path
import json,os,subprocess

W=Path(__file__).resolve().parent
H=Path('/var/lib/smartpc-dashboard');D=H/'.local/share/SmartPC/SmartPC'
assert subprocess.run(['systemctl','is-active','smartpc-dashboard'],capture_output=True,text=True).stdout.strip()=='inactive'
for label,theme in [('base','base'),('functional','functional'),('apple','studio.applecalm')]:
    out=W/'eglfs'/label;out.mkdir(parents=True,exist_ok=True)
    env=['HOME='+str(H),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms',
         'QT_QPA_EGLFS_HIDECURSOR=1','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json',
         'QSG_RHI_BACKEND=opengl','QT_DISABLE_SHADER_DISK_CACHE=1','SMARTPC_AQUARIUM_RENDERER=3d',
         'OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','SMARTPC_GL_PROBE_FILE='+str(out/'native-context.json'),
         'LD_PRELOAD='+str(W/'gl-probe.so')+':'+str(W/'runtime/libsmartpc_egl_context_bridge.so')]
    command=['env',*env,str(H/'game-runtime/bin/python'),str(W/'test-project/scripts/check-aquarium-3d.py'),
             '--output',str(out),'--seconds','8','--warmup','2','--theme',theme]
    if label=='apple':command+=['--theme-data',str(D)]
    with (out/'process.log').open('w') as log:
        result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    report=json.loads((out/'report.json').read_text())
    assert result.returncode==0 and report['status']=='passed' and not report['qmlWarnings'],label
    print(json.dumps({'theme':label,'status':report['status'],'checks':len(report['checks']),
                      'callbacks':report['callbacks'],'p95Ms':report['p95Ms']}),flush=True)
print('PASS all three native themes with isolated data',flush=True)
