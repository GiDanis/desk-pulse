"""Read-only kiosk observation, isolated installed-code CPU workloads."""
import cProfile,hashlib,json,os,pstats,sqlite3,sys,tempfile,time,statistics,multiprocessing as mp,queue
from pathlib import Path
ROOT=Path(sys.argv[2]) if len(sys.argv)>2 else Path('/opt/smartpc/dashboard');sys.path.insert(0,str(ROOT))
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
OUT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/tmp/smartpc-resource-audit.json')
HZ=os.sysconf('SC_CLK_TCK')
def read(path):
 try:return Path(path).read_text().strip()
 except OSError:return None
def status(pid):
 text=read('/proc/'+str(pid)+'/status') or '';return {x.split(':')[0]:x.split(':',1)[1].strip() for x in text.splitlines()}
def ticks(pid,tid=None):
 s=read('/proc/'+str(pid)+('/task/'+str(tid) if tid else '')+'/stat')
 if not s:return None
 t=s.rsplit(')',1)[1].split();return {'ticks':int(t[11])+int(t[12]),'cpu':int(t[36]),'nice':int(t[16])}
def snap(pid):
 st=status(pid);threads={}
 for p in Path('/proc/'+str(pid)+'/task').glob('*'):
  n=int(p.name);v=ticks(pid,n)
  if v:threads[n]={**v,'name':read(p/'comm')}
 mem=read('/proc/'+str(pid)+'/smaps_rollup') or ''
 return {'threads':threads,'status':{k:st.get(k) for k in ('VmRSS','VmHWM','Threads','Cpus_allowed_list')},
 'pssKB':next((int(x.split()[1]) for x in mem.splitlines() if x.startswith('Pss:')),None)}
def system():
 mem={x.split(':')[0]:int(x.split()[1]) for x in (read('/proc/meminfo') or '').splitlines()}
 cpu={}
 for x in (read('/proc/stat') or '').splitlines():
  if x.startswith('cpu'):cpu[x.split()[0]]=list(map(int,x.split()[1:]))
 return {'time':time.time(),'memKB':{k:mem[k] for k in ('MemTotal','MemAvailable','SwapTotal','SwapFree','Dirty','Writeback')},'cpu':cpu,
 'thermal':{p.name:{'type':read(p/'type'),'mC':read(p/'temp')} for p in Path('/sys/class/thermal').glob('thermal_zone*')},
 'freq':{p.name:read(p/'scaling_cur_freq') for p in Path('/sys/devices/system/cpu/cpufreq').glob('policy*')},
 'devfreq':{p.name:{f:read(p/f) for f in ('cur_freq','governor')} for p in Path('/sys/class/devfreq').glob('*')}}
def percentages(a,b,dt):
 return sorted([{'tid':n,'name':v['name'],'cpuPercentOfOneCore':round((v['ticks']-a['threads'].get(n,{'ticks':v['ticks']})['ticks'])/HZ/dt*100,2),'lastCPU':v['cpu'],'nice':v['nice']} for n,v in b['threads'].items()],key=lambda x:-x['cpuPercentOfOneCore'])
def integrity():
 game=Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC/game')
 with sqlite3.connect('file:'+str(game/'game.sqlite')+'?mode=ro',uri=True) as db:
  data=list(db.iterdump())
 return {'dumpHash':hashlib.sha256(json.dumps(data).encode()).hexdigest(),'artifacts':len(list((game/'policies').glob('*.json')))}
def profile_case(method,phase='launch',track='oval-1'):
 from game_academy import academy_profile
 from game_academy_trainer import AcademyTrainer
 from game_profiles import preset
 a=AcademyTrainer(academy_profile(preset(3,method)),track)
 if phase!='launch':a.state['phase']=phase;a.reset_episodes()
 start=time.monotonic();base=a.steps;phases={};samples={};pr=cProfile.Profile();pr.enable()
 while time.monotonic()-start<6:
  kind='evaluation' if a.evaluation else 'update' if a.iterator is not None else 'collection'
  t=time.perf_counter();a.tick();ms=(time.perf_counter()-t)*1000
  phases[kind]=phases.get(kind,0)+ms;samples.setdefault(kind,[]).append(ms)
 pr.disable();elapsed=time.monotonic()-start;stat=pstats.Stats(pr)
 functions=[]
 for (f,line,name),v in stat.stats.items():
  functions.append({'file':Path(f).name,'line':line,'name':name,'calls':v[1],'selfSeconds':v[2],'cumulativeSeconds':v[3]})
 return {'method':method,'track':track,'task':phase,'population':a.profile['population'],'steps':a.steps-base,'wallSeconds':elapsed,
 'stepsPerSecondProfiled':(a.steps-base)/elapsed,'timeByStageMs':phases,
 'tickTimings':{k:{'medianMs':statistics.median(v),'p95Ms':sorted(v)[int(.95*(len(v)-1))],'maxMs':max(v)} for k,v in samples.items()},
 'rss':status(os.getpid()).get('VmRSS'),'topCumulative':sorted(functions,key=lambda x:-x['cumulativeSeconds'])[:20],
 'topSelf':sorted(functions,key=lambda x:-x['selfSeconds'])[:15]}
def wait(conn,kind,epoch,timeout=30):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  if conn.poll(.03):
   m=conn.recv()
   if m.get('session')==epoch:
    assert m['type']!='error',m
    if m['type']==kind:return m
 raise RuntimeError('Timeout '+kind)
def worker_case(gui,mode):
 from game_store import GameStore
 from game_worker import worker_main
 from game_profiles import reference_policy
 from game_academy import academy_profile
 context=mp.get_context('spawn')
 with tempfile.TemporaryDirectory(prefix='smartpc-resource-audit-') as root:
  s=GameStore(root);drivers=[]
  if mode=='gara':
   for i in range(4):
    d=s.create_driver(algorithm='pure_pursuit');s.activate_academy(d);drivers.append(d)
  else:drivers=[s.create_driver(algorithm='ppo_smooth')]
  parent,child=context.Pipe();frames=context.Queue(maxsize=2);epoch='audit-'+mode
  proc=context.Process(target=worker_main,args=(child,frames,root,{'mode':mode,'driver':drivers[0],'epoch':epoch,'participants':drivers if mode=='gara' else [],'selected':0,'laps':3,'track':'technical-1' if mode=='gara' else 'oval-1'}))
  proc.start();child.close()
  try:
   wait(parent,'ready',epoch);time.sleep(.5);before=snap(proc.pid);guiBefore=snap(gui);sysBefore=system();start=time.monotonic();packets=[];gaps=[];sizes=[];last=start;seq=[]
   while time.monotonic()-start<18:
    while parent.poll():
     m=parent.recv();assert m['type']!='error',m
    try:
     packet=frames.get(timeout=.03);t=time.monotonic();gaps.append(t-last);last=t
     seq.append(packet['sequence']);packets.append(packet['meta']);sizes.append(len(json.dumps(packet)))
    except queue.Empty:pass
   dt=time.monotonic()-start;after=snap(proc.pid);guiAfter=snap(gui);sysAfter=system()
   t=time.monotonic();parent.send({'type':'pause'});wait(parent,'paused',epoch);ack=time.monotonic()-t
   save=None
   if mode=='impara':t=time.monotonic();wait(parent,'saved',epoch,90);save=time.monotonic()-t
   result={'mode':mode,'wallSeconds':dt,'workerThreads':percentages(before,after,dt),'guiThreads':percentages(guiBefore,guiAfter,dt),
    'workerMemory':after['status'],'workerPssKB':after['pssKB'],'guiMemory':guiAfter['status'],'guiPssKB':guiAfter['pssKB'],
    'systemBefore':sysBefore,'systemAfter':sysAfter,'frames':len(packets),'sceneHz':len(packets)/dt,
    'sceneIntervalsMs':{'median':statistics.median(gaps)*1000,'p95':sorted(gaps)[int(.95*(len(gaps)-1))]*1000,'max':max(gaps)*1000},
    'medianJsonFrameBytes':statistics.median(sizes),'first':packets[0],'last':packets[-1],'pauseAckMs':ack*1000,'saveAfterAckSeconds':save,
    'scope':'Headless isolated worker while installed Home remains visible. Queue delivery, not QML/GPU/optical FPS.'}
   return result
  finally:
   if proc.is_alive():parent.send({'type':'stop'});proc.join(10)
   if proc.is_alive():proc.terminate();proc.join(3)
   frames.close();parent.close();proc.close()
def main():
 import subprocess
 service=int(subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','MainPID','--value']).decode())
 children=subprocess.check_output(['ps','--ppid',str(service),'-o','pid=']).decode().split();gui=int(children[0])
 before=integrity();a=snap(gui);sa=system();t=time.monotonic();time.sleep(8);dt=time.monotonic()-t;b=snap(gui)
 result={'time':time.time(),'version':__import__('version').VERSION,'guiPID':gui,'baseline':{'seconds':dt,'threads':percentages(a,b,dt),'memory':b['status'],'pssKB':b['pssKB'],'system':system()},'workers':[],'profiles':[]}
 for mode in ('impara','gara'):
  print('Worker '+mode,flush=True);result['workers'].append(worker_case(gui,mode));OUT.write_text(json.dumps(result,indent=2))
 for method in ('evolution','neat','ppo','ppo_smooth','imitation'):
  print('Profile '+method,flush=True);result['profiles'].append(profile_case(method));OUT.write_text(json.dumps(result,indent=2))
 for phase in ('overtake','race4'):
  print('Profile traffic '+phase,flush=True);result['profiles'].append(profile_case('ppo',phase,'varano-short-1'));OUT.write_text(json.dumps(result,indent=2))
 result['originalGameUnchanged']=integrity()==before;result['originalGameBaseline']=before;assert result['originalGameUnchanged']
 OUT.write_text(json.dumps(result,indent=2));print('Audit passed',flush=True)
if __name__=='__main__':main()
