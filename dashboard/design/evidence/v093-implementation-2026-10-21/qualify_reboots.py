"""Local coordinator: three candidate reboots, current GUI and completed boot."""
from pathlib import Path
import json
import subprocess
import time

OUTPUT=Path(__file__).resolve().parent
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=5','-i',
     '/home/giuseppe/.ssh/smartpc_ed25519','smartpc@192.168.1.179']
REMOTE=r'''
from pathlib import Path
import json,subprocess,time
home=Path('/var/lib/smartpc-dashboard');proof=home/'v093-proof'
p=proof/'reboot-current-health.json';p.touch()
subprocess.run(['chown','smartpc:smartpc',str(p)],check=True)
subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(home),
 'XDG_CONFIG_HOME='+str(home/'.config'),'XDG_DATA_HOME='+str(home/'.local/share'),
 'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','QT_QPA_PLATFORM=offscreen',
 str(home/'game-runtime/bin/python'),str(home/'v086-source-proof/board-health.py'),
 '--output',str(p)],check=True,stdout=subprocess.DEVNULL)
h=json.loads(p.read_text());pid=h['runtimePid']
boot=subprocess.run(['systemd-analyze','time'],capture_output=True,text=True)
h['systemBoot']=dict(returncode=boot.returncode,text=boot.stdout,error=boot.stderr)
h['jobs']=subprocess.check_output(['systemctl','list-jobs','--no-legend','--no-pager'],text=True)
h['handoff']=subprocess.check_output(['systemctl','show','smartpc-display-handoff.service',
 '-p','Result','-p','ExecMainStatus','-p','ActiveState'],text=True)
h['governors']={f.parent.name:f.read_text().strip() for f in Path('/sys/devices/system/cpu/cpufreq').glob('policy*/scaling_governor')}
h['performanceUnit']=subprocess.check_output(['systemctl','show','smartpc-performance.service','-p','Result','-p','ExecMainStatus','-p','ActiveState'],text=True)
h['failedUnits']=subprocess.check_output(['systemctl','--failed','--no-legend','--no-pager'],text=True)
h['plymouthPidFileExists']=Path('/run/plymouth/pid').exists()
if pid:
 h['renderThreads']=[f.read_text().strip() for f in Path(f'/proc/{pid}/task').glob('*/comm') if 'QSG' in f.read_text()]
 h['inputDescriptors']=[]
 for f in Path(f'/proc/{pid}/fd').iterdir():
  try:
   target=str(f.readlink())
   if '/input/' in target:h['inputDescriptors'].append(target)
  except OSError:pass
print(json.dumps(h))
'''
rows=[]
prior=json.loads((OUTPUT/'installation-receipt.json').read_text())
boot=prior['bootId']
before=None
for index in range(3):
    subprocess.run(SSH+['sudo -n systemctl reboot'],check=True)
    started=time.monotonic()
    errors=[]
    while time.monotonic()-started<150:
        time.sleep(3)
        result=subprocess.run(SSH+['sudo -n python3 -'],input=REMOTE,capture_output=True,text=True)
        if result.returncode:
            errors.append(result.stderr[-200:])
            continue
        current=json.loads(result.stdout)
        beat=current.get('guiHeartbeat') or {}
        if (current['bootId']!=boot and current['version']=='0.9.3-rc.1'
            and current['service']['ActiveState']=='active' and current['service']['NRestarts']=='0'
            and beat.get('ready') and beat.get('ageSeconds',999)<5
            and beat.get('pid')==current['runtimePid'] and not beat.get('pending')
            and current['systemBoot']['returncode']==0 and not current['jobs'].strip()):
            break
    else:raise AssertionError(('Candidate reboot not qualified',index,errors[-3:]))
    assert not current['manifestMismatches']
    assert current['activeTheme']==prior['activeTheme']
    assert current['allPreferenceHashes']==prior['allPreferenceHashes']
    assert 'Result=success' in current['handoff']
    assert current['renderThreads']
    assert current['governors']['policy6']=='performance'
    assert 'ActiveState=active' in current['performanceUnit'] and 'Result=success' in current['performanceUnit']
    if before is not None:assert current['allPreferenceHashes']==before['allPreferenceHashes']
    boot=current['bootId']
    before=current
    current['coordinatorReadySeconds']=time.monotonic()-started
    rows.append(current)
    (OUTPUT/'reboot-qualification.json').write_text(json.dumps(dict(status='in-progress',rows=rows),indent=2)+'\n')
    print(json.dumps(dict(reboot=index+1,bootId=boot,version=current['version'],
                         seconds=current['coordinatorReadySeconds'],boot=current['systemBoot']['text'])),flush=True)
(OUTPUT/'reboot-qualification.json').write_text(json.dumps(dict(status='passed',rows=rows),indent=2)+'\n')
