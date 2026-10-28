"""Finite passive observation. No provider requests, workload, or runtime changes."""
from pathlib import Path
import argparse,hashlib,json,os,pwd,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=28800);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
appdata='/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC'
beatname=hashlib.sha256(appdata.encode()).hexdigest()+'.json'
uid=pwd.getpwnam('smartpc').pw_uid
root=Path('/opt/smartpc/dashboard');manifestpath=root/'release-manifest.json'
manifest=manifestpath.read_bytes();qualified=json.loads(manifest)
assert qualified['version']=='0.9.3-rc.1'
expected_theme=json.loads(Path('/var/lib/smartpc-dashboard/v093-proof/installation-receipt.json').read_text())['activeTheme']
def hashes_ok():return manifestpath.read_bytes()==manifest and all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in qualified['sha256'].items())
assert hashes_ok()
def properties():
 text=subprocess.check_output(['systemctl','show','smartpc-dashboard.service','-p','MainPID','-p','ActiveState','-p','NRestarts'],text=True)
 return dict(line.split('=',1) for line in text.splitlines())
started=time.monotonic();rows=0;bad=0;failures=[];initial_boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
initial_service=properties();initial_gui=None
status='running'
while True:
 now=time.monotonic();service=properties();pid=int(service['MainPID']);heartbeat={}
 try:heartbeat=json.loads(Path(f'/proc/{pid}/root/tmp/smartpc-theme-health-{uid}/{beatname}').read_text())
 except (OSError,ValueError):pass
 # Heartbeat file mtime is independent of its evolving JSON schema.
 try:age=time.time()-Path(f'/proc/{pid}/root/tmp/smartpc-theme-health-{uid}/{beatname}').stat().st_mtime
 except OSError:age=9999
 gui=heartbeat.get('pid')
 if initial_gui is None and gui:initial_gui=gui
 memory={}
 if gui:
  try:
   for line in Path(f'/proc/{gui}/smaps_rollup').read_text().splitlines():
    if line.startswith(('Rss:','Pss:','Swap:')):k,v=line.split(':',1);memory[k]=int(v.split()[0])
  except OSError:pass
 row=dict(elapsedSeconds=now-started,service=service,heartbeat=heartbeat,heartbeatAgeSeconds=age,memoryKiB=memory,
  systemMemory={k:int(v.split()[0]) for k,v in (line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemAvailable','SwapFree')},
  governor=Path('/sys/devices/system/cpu/cpufreq/policy6/scaling_governor').read_text().strip(),
  temperatureC={f.parent.name:int(f.read_text())/1000 for f in Path('/sys/class/thermal').glob('thermal_zone*/temp')})
 rows+=1
 with (a.output/'samples.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 healthy=service['ActiveState']=='active' and service['NRestarts']=='0' and bool(gui) and bool(heartbeat.get('ready')) and age<10
 bad=0 if healthy else bad+1
 if bad>=3:failures.append('Three consecutive unhealthy samples');status='failed'
 if heartbeat and heartbeat.get('selection')!=expected_theme:failures.append('Active theme changed during observation');status='interrupted'
 if row['governor']!='performance':failures.append('Selected CPU policy changed');status='interrupted'
 if gui and initial_gui and gui!=initial_gui:failures.append('GUI process changed during observation');status='interrupted'
 if service['MainPID']!=initial_service['MainPID']:failures.append('Supervisor changed during observation');status='interrupted'
 report=dict(status=status,elapsedSeconds=now-started,requestedSeconds=a.seconds,samples=rows,failures=failures,
  manifestSha256=hashlib.sha256(manifest).hexdigest(),bootId=initial_boot,
  scope='Passive production observation; no active mixed workload, optical measurement, or learner start')
 (a.output/'progress.json').write_text(json.dumps(report,indent=2)+'\n')
 if status!='running':
  (a.output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');break
 if now-started>=a.seconds:
  report['status']='passed' if hashes_ok() else 'failed';report['finalManifestVerified']=hashes_ok()
  (a.output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');break
 time.sleep(min(60,max(1,a.seconds-(time.monotonic()-started))))
