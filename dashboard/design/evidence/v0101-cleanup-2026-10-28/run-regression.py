"""Run the selected cleanup regressions against an explicit isolated source."""
import argparse,concurrent.futures,json,os,subprocess,sys,tempfile,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--workers',type=int,default=2);p.add_argument('--case',action='append');a=p.parse_args();a.source=a.source.resolve();a.output.mkdir(parents=True,exist_ok=True)
cases=['check_game','check_game_residual','check_game_direct','check_game_balance','check_game_timing','check_game_school','check_game_sessions','check_game_process','check_aquarium','check_aquarium_assets','check_aquarium_motion','check_settings','check_dashboard']
if a.case:cases=a.case
def run(name):
 start=time.monotonic()
 with tempfile.TemporaryDirectory(prefix='smartpc-cleanup-test-') as private:
  home=Path(private);env=os.environ.copy();env.update(HOME=private,QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
  for key,subdir in [('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state'),('STATE_DIRECTORY','state'),('SMARTPC_THEME_STORE','themes')]:
   d=home/subdir;d.mkdir(exist_ok=True);env[key]=str(d)
  try:
   result=subprocess.run([sys.executable,str(a.source/(name+'.py'))],cwd=a.source,env=env,capture_output=True,text=True,timeout=300)
   text=result.stdout+result.stderr;row={'case':name,'exitCode':result.returncode,'status':'passed' if result.returncode==0 else 'failed'}
  except subprocess.TimeoutExpired as error:
   text=str(error);row={'case':name,'status':'timeout'}
 (a.output/(name+'.txt')).write_text(text);row['seconds']=round(time.monotonic()-start,3);print(json.dumps(row),flush=True);return row
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:results=list(pool.map(run,cases))
report={'status':'passed' if all(r['status']=='passed' for r in results) else 'failed','python':sys.version,'source':str(a.source),'results':results}
(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');raise SystemExit(0 if report['status']=='passed' else 1)
