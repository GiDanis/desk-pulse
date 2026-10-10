"""Read-only CPU/thread/GPU evidence. Never changes service, clocks or providers."""
from pathlib import Path
import hashlib,json,os,platform,subprocess,sys,sysconfig,time
P=Path('/proc');service=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show','smartpc-dashboard','--property=MainPID,ActiveState,SubState,NRestarts,CPUQuotaPerSecUSec,CPUAffinity,AllowedCPUs'],text=True).splitlines())
main=int(service['MainPID']);children=[child for child,parent in (line.split() for line in subprocess.check_output(['ps','-eo','pid=,ppid='],text=True).splitlines()) if int(parent)==main];pid=next(int(x) for x in children if b'/app.py' in Path(f'/proc/{x}/cmdline').read_bytes());root=Path(f'/proc/{pid}');ticks=os.sysconf('SC_CLK_TCK')
def read(p):
 try:return p.read_text().strip()
 except (OSError,ValueError):return None
def stat(p):
 text=p.read_text();parts=text[text.rfind(')')+2:].split();return {'cpuSeconds':(int(parts[11])+int(parts[12]))/ticks,'lastCpu':int(parts[36]),'state':parts[0]}
def sample():
 tasks={}
 for p in (root/'task').iterdir():
  try:tasks[p.name]={**stat(p/'stat'),'name':read(p/'comm'),'affinity':next((s.split(':',1)[1].strip() for s in (p/'status').read_text().splitlines() if s.startswith('Cpus_allowed_list:')),None)}
  except OSError:continue
 cpu={}
 for l in Path('/proc/stat').read_text().splitlines():
  fields=l.split()
  if fields and fields[0].startswith('cpu') and fields[0]!='cpu':
   values=list(map(int,fields[1:]));cpu[fields[0]]={'total':sum(values[:8]),'idle':values[3]+values[4]}
 gpu=Path('/sys/class/devfreq/1800000.gpu');metrics={n:read(gpu/n) for n in ('cur_freq','governor','load','busy_time','total_time','trans_stat') if (gpu/n).exists()}
 return {'time':time.time(),'tasks':tasks,'cpu':cpu,'gpu':metrics,'frequencies':{p.name:read(p/'scaling_cur_freq') for p in Path('/sys/devices/system/cpu/cpufreq').glob('policy*')}}
manifest=Path('/opt/smartpc/dashboard/release-manifest.json');m=json.loads(manifest.read_text());env={k.decode():v.decode() for item in (root/'environ').read_bytes().split(b'\0') if b'=' in item for k,v in [item.split(b'=',1)] if k.startswith((b'QT_',b'QSG_',b'QML_'))}
maps=sorted({l.split()[-1] for l in (root/'maps').read_text().splitlines() if any(x in l.lower() for x in ('libegl','libgles','libgl.','powervr','pvr','swrast','llvmpipe','libvulkan','libqt6quick'))})
fds=[]
for f in (root/'fd').iterdir():
 try:target=os.readlink(f)
 except OSError:continue
 if target.startswith(('/dev/dri','/dev/pvr')):fds.append({'fd':f.name,'target':target,'info':read(root/'fdinfo'/f.name)})
policies={p.name:{n:read(p/n) for n in ('affected_cpus','related_cpus','scaling_driver','scaling_governor','scaling_min_freq','scaling_max_freq','cpuinfo_max_freq')} for p in Path('/sys/devices/system/cpu/cpufreq').glob('policy*')}
topology={p.name:{'capacity':read(p/'cpu_capacity'),'compatible':(p/'of_node/compatible').read_bytes().replace(b'\0',b',').decode() if (p/'of_node/compatible').exists() else None} for p in Path('/sys/devices/system/cpu').glob('cpu[0-9]*')}
gpu=Path('/sys/class/devfreq/1800000.gpu');gpuInfo={n:read(gpu/n) for n in ('name','available_frequencies','governor','available_governors')};gpuInfo['driver']=str((gpu/'device/driver').resolve());gpuInfo['deviceFiles']=sorted(p.name for p in (gpu/'device').iterdir())
samples=[sample()]
for _ in range(30):time.sleep(1);samples.append(sample())
serviceAfter=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show','smartpc-dashboard','--property=MainPID,ActiveState,SubState,NRestarts'],text=True).splitlines());assert serviceAfter['MainPID']==service['MainPID'] and serviceAfter['ActiveState']=='active'
report={'status':'passed','scope':'30 seconds passive; no controlled input; lastCpu is a scheduler snapshot, not a per-core residency history','version':m['version'],'manifestSha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'manifestMismatches':[n for n,h in m['sha256'].items() if hashlib.sha256((manifest.parent/n).read_bytes()).hexdigest()!=h],'hostname':platform.node(),'bootId':read(Path('/proc/sys/kernel/random/boot_id')),'runtimePid':pid,'service':service,'serviceAfter':serviceAfter,'python':{'version':platform.python_version(),'gilEnabled':sys._is_gil_enabled() if hasattr(sys,'_is_gil_enabled') else 'unknown','gilDisabledBuild':sysconfig.get_config_var('Py_GIL_DISABLED')},'cpuOnline':read(Path('/sys/devices/system/cpu/online')),'cpuPolicies':policies,'cpuTopology':topology,'graphicsEnvironment':env,'graphicsLibraries':maps,'graphicsDeviceDescriptors':fds,'gpuInfo':gpuInfo,'samples':samples}
print(json.dumps(report,indent=2))
