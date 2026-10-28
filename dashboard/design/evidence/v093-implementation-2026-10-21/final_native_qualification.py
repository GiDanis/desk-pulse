"""Exclusive KMS qualification, reversible resource trials, guaranteed recovery."""
from pathlib import Path
import json
import os
import pwd
import signal
import subprocess
import time

ROOT=Path('/var/lib/smartpc-dashboard/v093-stage')
SOURCE=ROOT/'dashboard'
PROOF=Path('/var/lib/smartpc-dashboard/v093-proof')
OUTPUT=PROOF/'native-final'
PY='/var/lib/smartpc-dashboard/game-runtime/bin/python'
user=pwd.getpwnam('smartpc')
os.chown(PROOF,0,user.pw_gid)
PROOF.chmod(0o750)
OUTPUT.mkdir(exist_ok=True)
os.chown(OUTPUT,user.pw_uid,user.pw_gid)
governor=Path('/sys/devices/system/cpu/cpufreq/policy6/scaling_governor')
previous_governor=governor.read_text().strip()
environment=dict(os.environ,HOME='/var/lib/smartpc-dashboard',QT_QPA_PLATFORM='eglfs',
    QT_QPA_EGLFS_INTEGRATION='eglfs_kms',QT_QPA_EGLFS_HIDECURSOR='1',
    QT_QPA_EGLFS_KMS_CONFIG='/etc/smartpc/eglfs-kms.json',QSG_RHI_BACKEND='opengl',
    OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
    PYTHONDONTWRITEBYTECODE='1',SMARTPC_TEST_ASYNC_METADATA='1')
environment.pop('QT_QUICK_BACKEND',None)
rows=[]

def temperatures():
    return {p.parent.name:int(p.read_text())/1000 for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')}

def case(name,arguments,*,source=SOURCE,nice=0,timeout=300):
    target=OUTPUT/name
    target.mkdir(exist_ok=True)
    os.chown(target,user.pw_uid,user.pw_gid)
    command=[PY,str(source/arguments[0]),*arguments[1:]]
    command=[str(target) if arg=='@DIR' else str(target/'report.json') if arg=='@FILE' else arg for arg in command]
    def drop():
        os.setpriority(os.PRIO_PROCESS,0,nice)
        os.initgroups(user.pw_name,user.pw_gid)
        os.setgid(user.pw_gid)
        os.setuid(user.pw_uid)
    before=time.monotonic()
    with (target/'stdout.txt').open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=environment,
                                 preexec_fn=drop,start_new_session=True)
        try:code=process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGTERM)
            try:process.wait(10)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            code=-999
    report=target/'report.json'
    row=dict(name=name,code=code,seconds=time.monotonic()-before,nice=nice,
             governor=governor.read_text().strip(),temperatureC=temperatures(),
             reportStatus=json.loads(report.read_text()).get('status') if report.exists() else None)
    rows.append(row)
    (OUTPUT/'progress.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(row),flush=True)
    assert code==0 and row['reportStatus']=='passed',row

performance=['verify_performance_ui.py','--theme','apple','--motion','normal',
             '--bundle-project',str(ROOT/'theme-projects/apple-calm/bundle'),
             '--extra-lists','--output','@FILE']
manifest=json.loads((SOURCE/'release-manifest.json').read_text())
import hashlib
assert all(hashlib.sha256((SOURCE/n).read_bytes()).hexdigest()==v for n,v in manifest['sha256'].items())
previous=json.loads((PROOF/'native-r4/receipt.json').read_text())
changed=[n for n,v in manifest['sha256'].items() if previous['sourceManifest']['sha256'].get(n)!=v]
assert set(changed)<=set(['state.py','Main.qml','check_state_availability.py']),changed
rollback=[]
for action,expected in [('stop','schedutil'),('start','performance')]:
    subprocess.run(['systemctl',action,'smartpc-performance.service'],check=True)
    actual=governor.read_text().strip()
    rollback.append(dict(action=action,expected=expected,actual=actual))
    assert actual==expected
(OUTPUT/'governor-rollback.json').write_text(json.dumps(rollback,indent=2)+'\n')
subprocess.run(['systemctl','stop','smartpc-dashboard.service'],check=True)
try:
    bundle=str(ROOT/'theme-projects/apple-calm/bundle')
    for name,source in [('baseline',Path('/var/lib/smartpc-dashboard/v093-baseline/dashboard')),('candidate',SOURCE)]:
        case('first-response-'+name,[str(PROOF/'first_response.py'),'--source',str(source),'--bundle',bundle,'--output','@FILE'],source=source)
    case('performance-final',performance)
    case('mixed-all-surfaces',[str(PROOF/'mixed_native.py'),'--source',str(SOURCE),'--seconds','600','--output','@DIR'],timeout=1100)
    case('game-race',['check_game_fluidity_ui.py','--theme','apple','--load','race','--seconds','120','--trace','--output','@DIR'],timeout=400)
    case('game-sac',['check_game_fluidity_ui.py','--theme','apple','--load','sac','--seconds','120','--mature','--trace','--output','@DIR'],timeout=400)
    case('metadata-reader',[str(PROOF/'probe_metadata_reader.py'),'--source',str(SOURCE),'--root','/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/game','--output','@FILE'],timeout=120)
    assert all(hashlib.sha256((SOURCE/n).read_bytes()).hexdigest()==v for n,v in manifest['sha256'].items())
    report=dict(status='passed',rows=rows,sourceManifest=manifest,
        changedFromEarlierQualification=changed,priorQualification=str(PROOF/'native-r4/receipt.json'),
        selectedResourcePolicy='performance policy6 only; nice 0; unrestricted affinity',
        scope='Final product bytes: native 68 surfaces, first coherent frames, five-car race, mature SAC, real metadata read-only. Prior qualification retains PPO/TD3/Tactic/qualification and ABBA evidence for identical game code.',
        limits=['Software frames, not optical FPS','Synthetic providers/replay; no production training','10 minute mixed gate; 60 minute and 8-24 hour gates remain open'])
    (OUTPUT/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
finally:
    subprocess.run(['systemctl','start','smartpc-dashboard.service'],check=True)
