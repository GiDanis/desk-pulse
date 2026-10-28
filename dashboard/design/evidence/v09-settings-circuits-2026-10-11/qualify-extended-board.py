"""Native pilot dossier qualification in isolated stores; restore the kiosk."""
import json
from pathlib import Path
import subprocess

H=Path('/var/lib/smartpc-dashboard');P=H/'v09-settings-circuits-proof'
PROJECT=H/'smartpc-v09-rc7-project';PY=H/'game-runtime/bin/python'
P.mkdir(exist_ok=True);subprocess.run(['chown','-R','smartpc:smartpc',str(P)],check=True)
environment=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),
             'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=eglfs',
             'QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json',
             'QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    reports=[]
    commands=[('race',['dashboard/design/evidence/v09-settings-circuits-2026-10-11/qualify-race-ui.py','--evidence',str(PROJECT/'dashboard/design/evidence/v09-settings-circuits-2026-10-11')],330),
              ('neat',['dashboard/check_game_ui.py','--theme','apple','--track','technical-1','--method','neat','--text-scale','1.1'],90),
              ('ppo-soak',['dashboard/check_game_ui.py','--theme','apple','--track','technical-1','--method','ppo','--text-scale','1.1','--soak-seconds','1800'],1950)]
    for label,arguments,timeout in commands:
        with (P/(label+'.txt')).open('w') as output:
            subprocess.run(['runuser','-u','smartpc','--','env',*environment,str(PY),
                            str(PROJECT/arguments[0]),*arguments[1:],'--capture-dir',str(P/label)],
                           cwd=PROJECT,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=timeout)
        report=json.loads((P/label/'report.json').read_text())
        assert report['status']=='passed' and report['platform']=='eglfs' and report['window']==[960,640]
        assert not report['qmlWarnings']
        reports.append(report);print('Native passed: '+label,flush=True)
    (P/'extended-qualification.json').write_text(json.dumps(dict(status='passed',profiles=reports,
        scope='Actual EGLFS with isolated stores; 30-minute PPO training on the technical track. Software timing, not optical FPS.'),indent=2)+'\n')

finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
