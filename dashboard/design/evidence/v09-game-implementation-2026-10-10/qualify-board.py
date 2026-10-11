"""Run isolated native game qualifications, always restoring the kiosk service."""
import json
from pathlib import Path
import subprocess
import time

H=Path('/var/lib/smartpc-dashboard');P=H/'v09-game-proof';PROJECT=H/'v09-game-staging/project'
PYTHON=H/'game-runtime/bin/python';HEALTH=H/'v086-source-proof/board-health.py'
P.mkdir(exist_ok=True);subprocess.run(['chown','-R','smartpc:smartpc',str(P)],check=True)
environment=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),
             'XDG_CACHE_HOME=/var/cache/smartpc-dashboard']
egl=['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json',
     'QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
def run(arguments,name,graphics=egl,timeout=180):
    with (P/(name+'.txt')).open('w') as output:
        subprocess.run(['runuser','-u','smartpc','--','env',*environment,*graphics,str(PYTHON),*map(str,arguments)],
                       cwd=PROJECT,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=timeout)
run([HEALTH,'--output',P/'before.json'],'before',graphics=['QT_QPA_PLATFORM=offscreen'])
before=json.loads((P/'before.json').read_text());assert before['service']['ActiveState']=='active' and not before['manifestMismatches']
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    profiles=[('base','day','normal','evolution',1.0),('functional','night','reduced','evolution',1.1),
              ('apple','day','normal','evolution',1.0),('apple','night','off','evolution',1.1),
              ('apple','night','normal','ppo',1.1),('apple','day','normal','neat',1.0)]
    reports=[]
    for theme,palette,motion,method,scale in profiles:
        name='-'.join((theme,palette,motion,method))
        run([PROJECT/'dashboard/check_game_ui.py','--theme',theme,'--palette',palette,'--motion',motion,
             '--method',method,'--text-scale',scale,'--capture-dir',P/name],name)
        report=json.loads((P/name/'report.json').read_text());assert report['status']=='passed' and report['platform']=='eglfs'
        assert report['window']==[960,640] and not report['qmlWarnings'] and report['pauseAckSeconds']<.25
        reports.append(report)
        print('Native passed: '+name,flush=True)
    run([PROJECT/'dashboard/check_game_ui.py','--theme','apple','--soak-seconds','1800','--capture-dir',P/'soak'],
        'soak',timeout=1900)
    soak=json.loads((P/'soak/report.json').read_text());assert soak['status']=='passed' and soak['soakSeconds']>=1800
    (P/'qualification.json').write_text(json.dumps({'status':'passed','profiles':reports,'soak':soak,
       'scope':'Real Main and real learning in isolated stores on EGLFS; physical key presses and optical 60 FPS not claimed'},indent=2)+'\n')
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
print('Native qualification completed; service restored',flush=True)
