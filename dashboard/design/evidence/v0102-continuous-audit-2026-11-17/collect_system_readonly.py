"""Save bounded OS diagnostics on the PC, without changing board configuration."""
import json
from pathlib import Path
import subprocess

REMOTE=r'''
import collections,datetime,json,pathlib,subprocess,time
P=pathlib.Path
def read(p):
    try: return P(p).read_text().strip()
    except OSError: return None
def run(args):
    p=subprocess.run(args,text=True,capture_output=True)
    return {'exitCode':p.returncode,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()}
rows=run(['journalctl','-b','-k','--no-pager','-n','1500','-o','json'])
lines=[json.loads(l) for l in rows['stdout'].splitlines()]
counts=collections.Counter(r.get('MESSAGE','') for r in lines)
thermal=[{'name':p.name,'type':read(p/'type'),'temp':read(p/'temp'),
          'trips':{f.name:read(f) for f in p.glob('trip_point*temp')}} for p in P('/sys/class/thermal').glob('thermal_zone*')]
cooling=[{'name':p.name,'type':read(p/'type'),'cur':read(p/'cur_state'),'max':read(p/'max_state')} for p in P('/sys/class/thermal').glob('cooling_device*')]
result={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'uptime_s':read('/proc/uptime'),'thermal':thermal,'cooling':cooling,
        'gpio101':[l for l in (read('/sys/kernel/debug/gpio') or '').splitlines() if 'gpio-101 ' in l],
        'pin101':[l for l in (read('/sys/kernel/debug/pinctrl/2000000.pinctrl/pinmux-pins') or '').splitlines() if '(PD5)' in l],
        'kernel_tail':{'count':len(lines),'first':lines[0].get('__REALTIME_TIMESTAMP') if lines else None,
                       'last':lines[-1].get('__REALTIME_TIMESTAMP') if lines else None,
                       'top_messages':counts.most_common(12)},
        'journal_disk_usage':run(['journalctl','--disk-usage']),
        'service':run(['systemctl','show','smartpc-dashboard.service','-p','ActiveState','-p','SubState',
                      '-p','NRestarts','-p','MainPID','-p','CPUUsageNSec','-p','MemoryCurrent','-p','MemoryPeak',
                      '-p','ExecMainStartTimestamp','-p','ExecMainStartTimestampMonotonic','-p','TasksCurrent']),
        'helper_smaps':read('/proc/1307/smaps_rollup'),
        'df':run(['df','-B1','/']), 'memory':read('/proc/meminfo'),
        'diskstats_mmcblk1':[l for l in (read('/proc/diskstats') or '').splitlines() if 'mmcblk1 ' in l],
        'process_io_supported':P('/proc/1255/io').exists(),
        'cgroup_io_supported':P('/sys/fs/cgroup/system.slice/smartpc-dashboard.service/io.stat').exists()}
print(json.dumps(result,indent=2))
'''
completed=subprocess.run(['ssh','-i','/home/giuseppe/.ssh/smartpc_ed25519','-o','BatchMode=yes',
    '-o','ConnectTimeout=8','smartpc@192.168.1.179','sudo -n python3 -'],input=REMOTE,
    capture_output=True,text=True)
if completed.returncode:
    raise RuntimeError(completed.stderr)
data=json.loads(completed.stdout)
target=Path(__file__).with_name('system-observation.json')
target.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({'report':str(target),'kernel_messages':data['kernel_tail']['count'],
                  'fan_errors':sum(n for s,n in data['kernel_tail']['top_messages'] if 'Cannot set pwm!' in s)}))
