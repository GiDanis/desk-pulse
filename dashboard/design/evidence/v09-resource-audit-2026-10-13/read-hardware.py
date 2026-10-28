import json,subprocess,hashlib
from pathlib import Path
root=Path('/opt/smartpc/dashboard');m=json.loads((root/'release-manifest.json').read_text());p=int(subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID','--value']));gui=int(subprocess.check_output(['ps','--ppid',str(p),'-o','pid=']).decode().split()[0]);maps=Path(f'/proc/{gui}/maps').read_text().splitlines()
def read(p):
 try:return Path(p).read_text().strip()
 except OSError:return None
r={'version':m['version'],'files':len(m['sha256']),'manifestMismatches':[k for k,v in m['sha256'].items() if hashlib.sha256((root/k).read_bytes()).hexdigest()!=v],
   'gpuLibraries':sorted(set(x.split()[-1] for x in maps if any(w in x.lower() for w in ('libegl','libgles','pvr')))),'deviceFds':[],
   'cpuPolicies':{q.name:{k:read(q/k) for k in ('affected_cpus','scaling_governor','cpuinfo_max_freq','scaling_cur_freq')} for q in Path('/sys/devices/system/cpu/cpufreq').glob('policy*')},
   'devfreq':{q.name:{k:read(q/k) for k in ('cur_freq','governor','available_frequencies','trans_stat')} for q in Path('/sys/class/devfreq').glob('*')}}
for f in Path(f'/proc/{gui}/fd').glob('*'):
 try:
  target=str(f.readlink())
  if '/dev/' in target and any(w in target for w in ('dri','galcore','npu','pvr')):r['deviceFds'].append(target)
 except OSError:pass
for name in ('gpu_top','npu'):r[name+'PowerState']=read('/sys/kernel/debug/pm_genpd/pd_'+name+'/current_state')
r['pvrStatus']=read('/sys/kernel/debug/pvr/status');r['cpuinfo']=read('/proc/device-tree/compatible');r['service']=subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','ActiveState','-p','NRestarts']).decode()
print(json.dumps(r,indent=2))
