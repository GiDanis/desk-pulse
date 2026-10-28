"""Read-only 2-minute sampler. No process attach, signals, app or governor changes."""
import json,os,subprocess,time
from pathlib import Path
P=Path('/var/lib/smartpc-dashboard/v09-evo-pacing-proof');P.mkdir(exist_ok=True)
HZ=os.sysconf('SC_CLK_TCK')
def read(path):
 try:return Path(path).read_text().strip()
 except (OSError,UnicodeError):return None

def proc(pid):
 result={}
 for q in Path(f'/proc/{pid}/task').glob('*'):
  raw=read(q/'stat')
  if not raw:continue
  v=raw.rsplit(')',1)[1].split()
  result[q.name]=dict(ticks=int(v[11])+int(v[12]),lastCPU=int(v[36]),name=read(q/'comm'),nice=int(v[16]))
 raw=read(f'/proc/{pid}/status') or ''
 return dict(threads=result,status={x.split(':')[0]:x.split(':',1)[1].strip() for x in raw.splitlines() if x.split(':')[0] in ('VmRSS','VmHWM','Threads','Cpus_allowed_list')},io=read(f'/proc/{pid}/io'))

def sample():
 processes={}
 for q in Path('/proc').glob('[0-9]*'):
  cmd=read(q/'cmdline') or ''
  if '/opt/smartpc/dashboard/app.py' in cmd or 'from multiprocessing.spawn import spawn_main' in cmd:
   processes[q.name]=dict(role='gui' if 'app.py' in cmd else 'worker',**proc(q.name))
 raw=read('/proc/stat') or ''
 cpu={x.split()[0]:list(map(int,x.split()[1:])) for x in raw.splitlines() if x.startswith('cpu')}
 mem={x.split(':')[0]:int(x.split()[1]) for x in (read('/proc/meminfo') or '').splitlines()}
 health=[]
 for q in Path('/tmp').glob('smartpc-theme-health-*/*.json'):
  try:
   h=json.loads(q.read_text())
   if str(h.get('pid')) in processes:health.append(dict(pid=h['pid'],age=time.time()-h['time'],ready=h.get('ready')))
  except (OSError,ValueError):pass
 return dict(time=time.time(),monotonic=time.monotonic(),processes=processes,cpu=cpu,
  memoryKB={k:mem.get(k) for k in ('MemAvailable','SwapTotal','SwapFree','Dirty','Writeback')},
  pressure={k:read('/proc/pressure/'+k) for k in ('cpu','memory','io')},
  thermal={q.name:dict(kind=read(q/'type'),mC=read(q/'temp')) for q in Path('/sys/class/thermal').glob('thermal_zone*')},
  frequencies={q.name:read(q/'scaling_cur_freq') for q in Path('/sys/devices/system/cpu/cpufreq').glob('policy*')},
  devfreq={q.name:{k:read(q/k) for k in ('cur_freq','governor','load','busy_time','total_time')} for q in Path('/sys/class/devfreq').glob('*')},
  gpuStatus=read('/sys/kernel/debug/pvr/status'),gpuUtilisation=read('/sys/kernel/debug/pvr/gpu00/utilisation'),health=health)

rows=[];start=time.monotonic()
for index in range(61):
 rows.append(sample());(P/'live-resources.json').write_text(json.dumps(dict(scope='Real running installed GUI/worker; no frame or per-car cadence measurement',hz=HZ,samples=rows),indent=2)+'\n')
 if index%10==0:print('sample',index,'elapsed',round(time.monotonic()-start),flush=True)
 if index<60:time.sleep(max(0,start+(index+1)*2-time.monotonic()))
