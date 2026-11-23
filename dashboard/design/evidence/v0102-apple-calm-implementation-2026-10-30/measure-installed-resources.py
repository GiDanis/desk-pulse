"""Short read-only idle observation, no GPU/optical/performance qualification."""
from pathlib import Path
import argparse,hashlib,json,os,pwd,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--label',required=True);a=p.parse_args()
time.sleep(20)
H=Path('/var/lib/smartpc-dashboard');D=H/'.local/share/SmartPC/SmartPC'
def snapshot():
 values=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID','-p','ControlGroup'],text=True).splitlines())
 key=hashlib.sha256(os.fsencode(str(D))).hexdigest()+'.json';uid=pwd.getpwnam('smartpc').pw_uid
 health=json.loads((Path('/proc')/values['MainPID']/'root/tmp'/('smartpc-theme-health-'+str(uid))/key).read_text());pid=health['pid']
 status=dict((line.split(':',1)[0],line.split(':',1)[1].strip()) for line in (Path('/proc')/str(pid)/'status').read_text().splitlines() if ':' in line)
 cg=Path('/sys/fs/cgroup')/values['ControlGroup'].lstrip('/')
 cpu=dict(line.split() for line in (cg/'cpu.stat').read_text().splitlines())
 thermal={q.parent.name:q.read_text().strip() for q in Path('/sys/class/thermal').glob('thermal_zone*/temp')}
 return {'monotonic':time.monotonic(),'pid':pid,'selection':health['selection'],'context':health.get('context'),'guiRssKb':int(status['VmRSS'].split()[0]),'cgroupMemoryBytes':int((cg/'memory.current').read_text()),'cgroupCpuUsec':int(cpu['usage_usec']),'thermalMilliC':thermal}
before=snapshot();time.sleep(10);after=snapshot();assert before['pid']==after['pid']
report={'scope':'20 s warmup + 10 s passive installed-service observation; provider timing is uncontrolled; not a paired load benchmark, GPU energy or optical FPS','label':a.label,'before':before,'after':after,'cpuPercentOneCore':(after['cgroupCpuUsec']-before['cgroupCpuUsec'])/(after['monotonic']-before['monotonic'])/10000}
a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
