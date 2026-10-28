"""Native performance qualification in isolated stores; restore the kiosk."""
import json
from pathlib import Path
import subprocess

H=Path('/var/lib/smartpc-dashboard');P=H/'v09-game-performance-proof'
PROJECT=H/'smartpc-v09-rc4-qualified-project';PY=H/'game-runtime/bin/python'
P.mkdir(exist_ok=True);subprocess.run(['chown','-R','smartpc:smartpc',str(P)],check=True)
environment=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),
             'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs',
             'QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json',
             'QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    reports=[]
    for method,soak in [('evolution',120),('neat',60),('ppo',0)]:
        with (P/(method+'.txt')).open('w') as output:
            subprocess.run(['runuser','-u','smartpc','--','env',*environment,str(PY),
                            str(PROJECT/'dashboard/check_game_ui.py'),'--theme','apple','--text-scale','1.1',
                            '--method',method,'--soak-seconds',str(soak),'--capture-dir',str(P/method)],
                           cwd=PROJECT,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=soak+90)
        report=json.loads((P/method/'report.json').read_text())
        assert report['status']=='passed' and report['platform']=='eglfs' and report['window']==[960,640]
        assert not report['qmlWarnings'] and report['pauseAckSeconds']<.25
        reports.append(report);print('Native passed: '+method,flush=True)
    (P/'qualification.json').write_text(json.dumps(dict(status='passed',profiles=reports,
        scope='Actual EGLFS, isolated pilots; software timing only, no optical/input/60 FPS certification'),indent=2)+'\n')
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
