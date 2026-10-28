"""Exclusive native graphics qualification; restores the installed service in finally."""
from pathlib import Path
import json,os,subprocess,time,signal
H=Path('/var/lib/smartpc-dashboard')
P=H/'aquarium-proof-20261025'
PY=H/'game-runtime/bin/python'
B=P/'dashboard'
config=H/'.config/SmartPC'
import hashlib
before={str(p.relative_to(config)):hashlib.sha256(p.read_bytes()).hexdigest() for p in config.rglob('*') if p.is_file()}
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
results=[]
checks=['check_aquarium_assets.py','check_theme_action_lifetime.py','public-actions','check_theme_bundle_tools.py','check_theme_runtime_fixtures.py','check_aquarium.py','check_aquarium_motion.py','check_theme_api_contract.py','check_theme_api_runtime.py','check_theme_api_adapters.py']
for check in checks:
 with (P/(check+'.log')).open('w') as log:
  command=[str(PY),str(B/check)]
  if check=='public-actions':command=[str(PY),str(P/'verify-actions.py'),'--source',str(B),'--output',str(P/'public-actions.json')]
  if check=='check_theme_runtime_fixtures.py':command += ['--track','legacyUi','--profiles','base:day:normal,functional:night:off','--select','aquarium','--output',str(P/'arm-variants.json')]
  if check=='check_theme_api_runtime.py':
   code="import sys,unittest;sys.path.insert(0,"+repr(str('/var/lib/smartpc-dashboard/aquarium-proof-20261025/dashboard'))+");import check_theme_api_runtime as m;m.PublicApiTests.test_lint_typo_rejected_with_real_qmllint=unittest.skip('ARM qmllint unavailable; actual lint verified on PC')(m.PublicApiTests.test_lint_typo_rejected_with_real_qmllint);unittest.main(module=m)"
   command=[str(PY),'-c',code]
  result=subprocess.run(['runuser','-u','smartpc','--','env','HOME='+str(H),'QT_QPA_PLATFORM=offscreen','QT_QUICK_BACKEND=software',*command],stdout=log,stderr=subprocess.STDOUT,timeout=180)
 assert result.returncode==0,(check,(P/(check+'.log')).read_text()[-2500:])
 print('ARM passed',check,flush=True)
commands=[('final-base',[]),('final-functional',['--theme','functional']),('final-apple',['--theme','apple']),('asset-error',['--missing-assets']),('image-error',['--broken-image']),*[(f'nominal-{i}',['--benchmark-only','--theme','apple','--warmup','60','--seconds','120']) for i in range(1,4)],*[(f'scale-{n}',['--benchmark-only','--theme','apple','--population',str(n),'--seconds','30']) for n in (1,4,8,16)],('sprite-one',['--benchmark-only','--theme','apple','--population','1','--sprite','--seconds','30']),('sprite-six',['--benchmark-only','--theme','apple','--sprite','--seconds','40']),('soak30',['--benchmark-only','--theme','apple','--warmup','60','--seconds','1800'])]
def source_hashes():
 return {str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest() for p in B.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
archive=P/'qualification'
if archive.exists():archive.rename(P/('qualification-history-'+time.strftime('%Y%m%d-%H%M%S')))
frozen=source_hashes()
source_digest=hashlib.sha256(json.dumps(frozen,sort_keys=True).encode()).hexdigest()
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 for name,extra in commands:
  out=P/'qualification'/name;out.mkdir(parents=True,exist_ok=True)
  cmd=['runuser','-u','smartpc','--','env','HOME='+str(H),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1',str(PY),str(B/'check_aquarium_ui.py'),'--output',str(out),'--bundle',str(P/'theme-projects/apple-calm/bundle'),*extra]
  subprocess.run(['chown','-R','smartpc:smartpc',str(out)],check=True)
  assert source_hashes()==frozen,'Source changed before '+name
  with (out/'run.log').open('w') as log:
   proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   started=time.monotonic();last_progress=started
   try:
    while proc.poll() is None:
     now=time.monotonic()
     if now-started>2100:raise TimeoutError(name)
     if now-last_progress>=60:
      live={'caseId':name,'processAgeSeconds':now-started,'time':time.time()}
      for entry in Path('/proc').iterdir():
       if not entry.name.isdigit():continue
       try:
        args=(entry/'cmdline').read_bytes().split(b'\0')
        if len(args)>1 and args[1]==os.fsencode(str(B/'check_aquarium_ui.py')):
         status=dict(line.split(':',1) for line in (entry/'status').read_text().splitlines() if ':' in line)
         live.update(pid=int(entry.name),rssKiB=int(status['VmRSS'].split()[0]),threads=int(status['Threads']))
       except (OSError,KeyError,ValueError):pass
      live['temperaturesC']={p.parent.name:int(p.read_text())/1000 for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')}
      (P/'qualification-live.json').write_text(json.dumps(live,indent=2)+'\n')
      print('LIVE',json.dumps(live),flush=True);last_progress=now
     time.sleep(1)
   except BaseException:
    os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    raise
  assert proc.returncode==0,(name,proc.returncode,(out/'run.log').read_text()[-2500:])
  assert source_hashes()==frozen,'Source changed during '+name
  report=json.loads((out/'report.json').read_text());report.update(caseId=name,sourceTreeSha256=source_digest);(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');results.append({k:v for k,v in report.items() if k not in ('rawIntervalsMs',)})
  print(name,report.get('callbacksPerSecond'),report.get('p95Ms'),report.get('near60SoftwareGate'),flush=True)
  (P/'qualification-progress.json').write_text(json.dumps(results,indent=2)+'\n')
finally:
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 after={str(p.relative_to(config)):hashlib.sha256(p.read_bytes()).hexdigest() for p in config.rglob('*') if p.is_file()}
 (P/'qualification-receipt.json').write_text(json.dumps({'results':results,'sameBoot':boot==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'preferencesPreserved':before==after,'serviceRestarted':True,'sourceHashes':frozen,'sameSourceForAllCases':source_hashes()==frozen,'sourceTreeSha256':source_digest},indent=2)+'\n')
