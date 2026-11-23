"""Read-only board audit. Run locally; only reports are written on the PC."""
import argparse
import json
from pathlib import Path
import subprocess

REMOTE = r'''
import collections, datetime, glob, hashlib, json, os, pathlib, re, subprocess, time
P=pathlib.Path
def read(path):
    try: return P(path).read_text()
    except OSError: return ''
def cmd(args):
    p=subprocess.run(args,capture_output=True,text=True)
    return p.stdout.strip()
def kv(path):
    out={}
    for line in read(path).splitlines():
        fields=line.replace(':','').split()
        if len(fields)>1:
            try: out[fields[0]]=int(fields[1])
            except ValueError: pass
    return out
root=P('/opt/smartpc/dashboard')
m=json.loads((root/'release-manifest.json').read_text())
fail=[]
for name,digest in m['sha256'].items():
    f=root/name
    if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=digest: fail.append(name)
gui=[]
for f in P('/proc').glob('[0-9]*/cmdline'):
    args=read(f).split('\0')
    if len(args)>1 and args[1]==str(root/'app.py'): gui.append(int(f.parent.name))
assert len(gui)==1,gui
pid=gui[0]
data=P('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC')
state=json.loads((data/'theme-activation.json').read_text())
boot=read('/proc/sys/kernel/random/boot_id').strip()
logs=cmd(['journalctl','--boot='+boot,'_SYSTEMD_UNIT=smartpc-dashboard.service','-o','json','--no-pager'])
patterns={'qml':r'QML|ReferenceError|TypeError|binding loop|Cannot assign|Unable to assign',
          'traceback':r'Traceback|Exception|RuntimeError', 'graphics':r'EGL|OpenGL|QRhi|DRM|shader',
          'recovery':r'recovered|GUI heartbeat|readiness timeout',
          'network':r'timeout|HTTP|ConnectionError|SSL|connection refused'}
counts=collections.Counter(); levels=collections.Counter(); logtimes=[]
for line in logs.splitlines():
    try: row=json.loads(line)
    except ValueError: continue
    counts['total']+=1
    msg=str(row.get('MESSAGE','')); levels[str(row.get('PRIORITY','?'))]+=1
    logtimes.append(row.get('__REALTIME_TIMESTAMP'))
    for name,pattern in patterns.items():
        if re.search(pattern,msg,re.I): counts[name]+=1
def sample():
    stat=read('/proc/'+str(pid)+'/stat').rsplit(')',1)[1].split()
    threads={}
    for f in P('/proc/'+str(pid)+'/task').glob('*/stat'):
        v=read(f).rsplit(')',1)[-1].split()
        if len(v)>13: threads[f.parent.name]=int(v[11])+int(v[12])
    health=[]
    for f in P('/proc/'+str(pid)+'/root/tmp').glob('smartpc-theme-health-*/*.json'):
        try:
            h=json.loads(f.read_text())
            if h.get('pid')==pid:
                health.append({'age_s':time.time()-h['time'],'ready':h.get('ready'),
                               'context':h.get('context'),'processStart':h.get('processStart')})
        except (OSError,ValueError): pass
    return {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'uptime_s':float(read('/proc/uptime').split()[0]), 'pid':pid,
            'cpu_ticks':int(stat[11])+int(stat[12]), 'start_ticks':int(stat[19]),
            'smaps_kib':kv('/proc/'+str(pid)+'/smaps_rollup'),
            'io':kv('/proc/'+str(pid)+'/io'), 'status':kv('/proc/'+str(pid)+'/status'),
            'fds':len(list(P('/proc/'+str(pid)+'/fd').iterdir())), 'threads_cpu_ticks':threads,
            'memory_stat':kv('/sys/fs/cgroup/system.slice/smartpc-dashboard.service/memory.stat'),
            'memory_current':read('/sys/fs/cgroup/system.slice/smartpc-dashboard.service/memory.current').strip(),
            'memory_peak':read('/sys/fs/cgroup/system.slice/smartpc-dashboard.service/memory.peak').strip(),
            'temperatures_mC':[int(read(f).strip()) for f in glob.glob('/sys/class/thermal/thermal_zone*/temp')],
            'health':health}
print(json.dumps({'kind':'identity','version':m['version'],'manifest_sha256':hashlib.sha256((root/'release-manifest.json').read_bytes()).hexdigest(),
                  'manifest_files':len(m['sha256']),'manifest_failures':fail,
                  'pid':pid,'clock_ticks':os.sysconf('SC_CLK_TCK'), 'boot_id':boot,
                  'selection':state['active'],'pending':state['pending'],'lastRecovery':state['lastRecovery'],
                  'journal':{'counts':dict(counts),'priorities':dict(levels),'first':min(logtimes) if logtimes else None,'last':max(logtimes) if logtimes else None},
                  'clock':cmd(['timedatectl','show','-p','NTPSynchronized','-p','TimeUSec','-p','RTCTimeUSec'])}),flush=True)
for i in range(SAMPLES):
    print(json.dumps({'kind':'sample',**sample()}),flush=True)
    if i<SAMPLES-1: time.sleep(INTERVAL)
'''

parser=argparse.ArgumentParser()
parser.add_argument('--samples',type=int,default=25)
parser.add_argument('--interval',type=int,default=5)
args=parser.parse_args()
out=Path(__file__).with_name('board-observation.jsonl')
source='SAMPLES='+str(args.samples)+'\nINTERVAL='+str(args.interval)+'\n'+REMOTE
with out.open('w') as f:
    result=subprocess.run(['ssh','-i','/home/giuseppe/.ssh/smartpc_ed25519','-o','BatchMode=yes',
        '-o','ConnectTimeout=8','smartpc@192.168.1.179','sudo -n python3 -'],input=source,text=True,stdout=f)
print(json.dumps({'exitCode':result.returncode,'report':str(out)}))
raise SystemExit(result.returncode)
