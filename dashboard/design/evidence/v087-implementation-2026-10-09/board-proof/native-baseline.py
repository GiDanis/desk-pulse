"""Capture 0.8.6 EGLFS performance before installing changes; restore kiosk."""
import json
from pathlib import Path
import subprocess
import time

proof = Path('/var/lib/smartpc-dashboard/v087-performance-proof')
project = Path('/var/lib/smartpc-dashboard/smartpc-v086-seriea-staging/project')
home = Path('/var/lib/smartpc-dashboard')
env = ['HOME='+str(home), 'XDG_CONFIG_HOME='+str(home/'.config'), 'XDG_DATA_HOME='+str(home/'.local/share'),
       'XDG_CACHE_HOME=/var/cache/smartpc-dashboard', 'QT_QPA_PLATFORM=eglfs',
       'QT_QPA_EGLFS_INTEGRATION=eglfs_kms', 'QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json',
       'QT_QPA_EGLFS_HIDECURSOR=1', 'QSG_RHI_BACKEND=opengl', 'PYTHONPATH='+str(project/'dashboard')]
before = subprocess.check_output(['systemctl','show','smartpc-dashboard','--property=ActiveState,SubState,NRestarts'],text=True)
assert 'ActiveState=active' in before
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    for theme in ['apple','base']:
        output = proof/('baseline-'+theme+'.json')
        with (proof/('baseline-'+theme+'.log')).open('w') as log:
            subprocess.run(['runuser','-u','smartpc','--','env',*env,'python3',str(proof/'verify_performance_ui.py'),
                            '--theme',theme,'--bundle-project',str(project/'theme-projects/apple-calm/bundle'),
                            '--output',str(output)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=240)
        report=json.loads(output.read_text())
        assert report['platform']=='eglfs' and not report['network_attempts']
        print(json.dumps({'theme':theme,'statistics':report['statistics']}),flush=True)
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    time.sleep(2)
    print(subprocess.check_output(['systemctl','show','smartpc-dashboard','--property=ActiveState,SubState,NRestarts'],text=True),flush=True)
