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
    commands=[('final-apple',['dashboard/check_game_settings_ui.py','--theme','apple'],90),
              ('final-race',['dashboard/design/evidence/v09-settings-circuits-2026-10-11/qualify-race-ui.py','--evidence',str(PROJECT/'dashboard/design/evidence/v09-settings-circuits-2026-10-11')],330)]
    for label,arguments,timeout in commands:
        with (P/(label+'.txt')).open('w') as output:
            subprocess.run(['runuser','-u','smartpc','--','env',*environment,str(PY),
                            str(PROJECT/arguments[0]),*arguments[1:],'--capture-dir',str(P/label)],
                           cwd=PROJECT,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=timeout)
        report=json.loads((P/label/'report.json').read_text());assert report['status']=='passed' and not report['qmlWarnings']
        reports.append(report);print('Native passed: '+label,flush=True)
    (P/'final-qualification.json').write_text(json.dumps({'status':'passed','profiles':reports},indent=2)+'\n')

finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
