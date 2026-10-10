"""Read-only hardware-path snapshot of the installed, freshly verified GUI."""
from pathlib import Path
import json,os,subprocess,time
p=Path('/var/lib/smartpc-dashboard/v087-opening-proof')
health=json.loads((p/'reboot-health.json').read_text());pid=health['guiHeartbeat']['pid']
assert health['guiHeartbeat']['ready'] and time.time()-health['time']<30
process=Path('/proc')/str(pid)
threads=[]
for task in sorted((process/'task').iterdir(),key=lambda f:int(f.name)):
 text=(task/'stat').read_text();fields=text[text.rfind(')')+2:].split()
 threads.append({'tid':int(task.name),'name':(task/'comm').read_text().strip(),'allowedCpus':sorted(os.sched_getaffinity(int(task.name))),'lastObservedCpu':int(fields[36])})
libs=sorted({line.split()[-1] for line in (process/'maps').read_text().splitlines() if any(x in line.lower() for x in ('pvr','libegl','libgles','libsrv_um','libimg'))})
fds=[]
for f in (process/'fd').iterdir():
 try:target=str(f.resolve(strict=True))
 except OSError:continue
 if target.startswith('/dev/dri/'):fds.append(target)
cpus=[]
for cpu in sorted(Path('/sys/devices/system/cpu').glob('cpu[0-9]*'),key=lambda f:int(f.name[3:])):
 row={'cpu':int(cpu.name[3:])}
 for rel in ['online','cpu_capacity','cpufreq/scaling_governor','cpufreq/scaling_cur_freq','cpufreq/cpuinfo_max_freq']:
  f=cpu/rel
  if f.exists():row[rel]=f.read_text().strip()
 cpus.append(row)
status=Path('/sys/kernel/debug/pvr/status').read_text()
report={'status':'passed','time':time.time(),'version':health['version'],'pid':pid,'threads':threads,'cpus':cpus,'graphicsLibraries':libs,'drmDescriptors':sorted(set(fds)),'powerVrStatus':status,'scope':'Read-only loaded-driver/thread/affinity snapshot; last CPU is not migration history, utilization is instantaneous, not a loaded benchmark or proof of parallel speedup'}
assert any('pvr' in f.lower() or 'libsrv_um' in f.lower() for f in libs),libs
assert any(row['name']=='QSGRenderThread' for row in threads),threads
assert fds
(p/'installed-hardware.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'passed','pid':pid,'threads':len(threads),'cpus':len(cpus),'hardwareGraphicsPathConfirmed':True}))
