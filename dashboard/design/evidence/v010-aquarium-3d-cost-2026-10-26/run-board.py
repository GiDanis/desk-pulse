"""Exclusive, bounded, isolated EGLFS experiment; restores production service."""
import argparse,hashlib,json,os,signal,subprocess,time,sqlite3
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['smoke','measure'],required=True);a=p.parse_args()
H=Path('/var/lib/smartpc-dashboard');P=H/'aquarium-3d-cost-20261026';PY=H/'game-runtime/bin/python';R=Path('/opt/smartpc/dashboard');C=H/'.config/SmartPC';OVER=P/'qt3d-overlay';BUNDLE=H/'aquarium-completion-20261026/theme-projects/apple-calm/bundle'
def game_fingerprint():
 G=H/'.local/share/SmartPC/SmartPC/game'
 with sqlite3.connect((G/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
  rows={n:db.execute('SELECT * FROM "'+n+'" ORDER BY rowid').fetchall() for n in tables}
 return {'database':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'artifacts':{str(f.relative_to(G)):hashlib.sha256(f.read_bytes()).hexdigest() for f in G.rglob('*') if f.is_file() and not f.name.startswith('game.sqlite')}}
def fingerprint():
 m=json.loads((R/'release-manifest.json').read_text());assert m['version']=='0.10.0-rc.2'
 assert all(hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
 return {'game':game_fingerprint(),'manifest':hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest(),'preferences':{str(f.relative_to(C)):hashlib.sha256(f.read_bytes()).hexdigest() for f in C.rglob('*') if f.is_file()},'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
def source_hashes():
 paths=[P/n for n in ('geometry.py','bench.py','Fish3D.qml','source-proof.json')]+[P/'source3d/dashboard/presentations/aquarium'/n for n in ('AquariumVisual.qml','Fish3D.qml')]
 return {str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths}
before=fingerprint();frozen=source_hashes();results=[]
cases=[('smoke-2d','2d',6,[],3,6),('smoke-3d','3d',6,[],5,12)] if a.phase=='smoke' else [('one-2d','2d',1,[],30,60),('one-3d','3d',1,[],30,60),('nominal-2d-1','2d',6,[],60,120),('nominal-3d-1','3d',6,[],60,120),('nominal-3d-2','3d',6,[],60,120),('nominal-2d-2','2d',6,[],60,120),('nominal-2d-3','2d',6,[],60,120),('nominal-3d-3','3d',6,[],60,120),('aa4-3d','3d',6,['--aa','4'],30,60),('highmesh-3d','3d',6,['--quality','high'],30,60),('stress16-3d','3d',16,[],15,30)]
(P/(a.phase+'-protocol.json')).write_text(json.dumps({'cases':cases,'thresholds':{'meanMin':59,'p95MaxMs':18.5,'missedSlotRatioMax':.01,'stallsOver50msLessThan':2,'poseTicksMin':58},'sourceHashes':frozen,'scope':'Paired actual Main, fixture providers; timing gates are software, prototype artwork not production'},indent=2)+'\n')
env=['HOME='+str(H),'QT_QPA_PLATFORM=eglfs','QT_QPA_EGLFS_INTEGRATION=eglfs_kms','QT_QPA_EGLFS_KMS_CONFIG=/etc/smartpc/eglfs-kms.json','QT_QPA_EGLFS_HIDECURSOR=1','QSG_RHI_BACKEND=opengl','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','LD_LIBRARY_PATH='+str(OVER/'usr/lib/aarch64-linux-gnu'),'QML_IMPORT_PATH='+str(OVER/'usr/lib/aarch64-linux-gnu/qt6/qml')]
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 for name,mode,population,extra,warmup,seconds in cases:
  assert source_hashes()==frozen,'Experiment changed before '+name
  out=P/a.phase/name;out.mkdir(parents=True,exist_ok=True);subprocess.run(['chown','-R','smartpc:smartpc',str(out)],check=True)
  command=['runuser','-u','smartpc','--','env',*env,str(PY),str(P/'bench.py'),'--source',str(P/('source'+mode)/'dashboard'),'--bundle',str(BUNDLE),'--overlay',str(OVER),'--mode',mode,'--population',str(population),'--warmup',str(warmup),'--seconds',str(seconds),'--output',str(out),*extra]
  with (out/'run.log').open('w') as log:
   process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);started=last=time.monotonic()
   try:
    while process.poll() is None:
     now=time.monotonic()
     if now-started>warmup+seconds+120:raise TimeoutError(name)
     if now-last>=60:print('RUNNING',name,round(now-started),'seconds',flush=True);last=now
     time.sleep(1)
   except BaseException:
    os.killpg(process.pid,signal.SIGTERM)
    try:process.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
    raise
  assert process.returncode==0,(name,process.returncode,(out/'run.log').read_text()[-4000:])
  assert source_hashes()==frozen,'Experiment changed during '+name
  report=json.loads((out/'report.json').read_text());assert report['status']=='passed' and not report['qmlWarnings'] and not report['networkAttempts']
  report.update(caseId=name);(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
  row={k:v for k,v in report.items() if k not in ('rawIntervalsMs',)};results.append(row)
  (P/(a.phase+'-progress.json')).write_text(json.dumps(results,indent=2)+'\n')
  print('RESULT',name,report['callbacksPerSecond'],report['p95Ms'],report['near60SoftwareGate'],flush=True)
finally:
 subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
 after=fingerprint();receipt={'status':'passed' if len(results)==len(cases) and before==after else 'incomplete','phase':a.phase,'cases':len(results),'expectedCases':len(cases),'productionUnchanged':before==after,'sameBoot':before['bootId']==after['bootId'],'results':results,'sourceHashes':frozen,'sourceUnchanged':source_hashes()==frozen}
 (P/(a.phase+'-receipt.json')).write_text(json.dumps(receipt,indent=2)+'\n')
 assert before==after,'Production state changed'
