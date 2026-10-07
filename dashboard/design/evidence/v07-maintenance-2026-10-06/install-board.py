from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess,time
base=Path('/tmp/smartpc-maintenance-rc2')
evidence=base/'evidence'
runtime=Path('/opt/smartpc/dashboard')
manifest=json.loads((base/'runtime/release-manifest.json').read_text())
assert manifest['version']=='0.7.0-rc.2'
for name,digest in manifest['sha256'].items():
    assert hashlib.sha256((base/'runtime'/name).read_bytes()).hexdigest()==digest,name
assert not (base/'runtime/fixtures/theme-runtime/renderers').exists()
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
backup=Path('/var/backups')/('smartpc-before-v07-maintenance-'+stamp)
backup.mkdir(mode=0o700)
previous=runtime.with_name('dashboard.previous-'+stamp)
staged=runtime.with_name('dashboard.staged-'+stamp)
installed=False
before=json.loads(subprocess.check_output(['python3','/tmp/smartpc-maintenance-health.py'],text=True))
started=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    shutil.copytree(runtime,backup/'runtime')
    shutil.copytree('/var/lib/smartpc-dashboard',backup/'state')
    shutil.copytree('/var/cache/smartpc-dashboard',backup/'cache')
    env=['QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl']
    for profile in ('base:day:off','functional:night:off'):
        name='eglfs-'+profile.split(':')[0]
        command=['runuser','-u','smartpc','--','env',*env,'python3',str(base/'dashboard/check_casa_ui.py'),'--profile',profile,'--output',str(evidence/(name+'.json')),'--capture-dir',str(evidence/name)]
        with (evidence/(name+'.txt')).open('w') as log:
            subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
    with (evidence/'real-cache-render.txt').open('w') as log:
        subprocess.run(['runuser','-u','smartpc','--','env',*env,'python3',str(base/'dashboard/capture-real-cache.py')],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
    shutil.copytree(base/'runtime',staged)
    runtime.rename(previous)
    try: staged.rename(runtime)
    except BaseException:
        previous.rename(runtime)
        raise
    installed=True
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    time.sleep(8)
    after=json.loads(subprocess.check_output(['python3','/tmp/smartpc-maintenance-health.py'],text=True))
    for key in ('preferencesHash','ledgerHashes','requests','cacheInventory'):
        assert before[key]==after[key],key
    journal=subprocess.check_output(['journalctl','-u','smartpc-dashboard','--since',started,'--no-pager'],text=True)
    warnings=[line for line in journal.splitlines() if any(marker in line for marker in ('ReferenceError','TypeError','Binding loop','QQmlApplicationEngine failed','Traceback','Segmentation fault'))]
    assert not warnings,warnings
    (evidence/'installed-journal.txt').write_text(journal)
    previous.rename(backup/'runtime-replaced')
    receipt={'status':'passed','backup':str(backup),'installed':after,'preferencesPreserved':True,'ledgerPreserved':True,'additionalCasaCalls':0,'qmlWarnings':warnings,'restartKind':'service restart; no operating-system reboot'}
    (evidence/'installation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)
except BaseException:
    if installed and previous.exists():
        subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
        runtime.rename(backup/'failed-runtime')
        previous.rename(runtime)
    raise
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
