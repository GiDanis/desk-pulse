from pathlib import Path
import collections,ctypes,gc,json,os,sys,time,tracemalloc
root=Path('/home/giuseppe/Documenti/Workspace/SmartPC');out=root/'dashboard/design/evidence/v093-implementation-2026-10-21'
os.environ.update(QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
sys.path.insert(0,str(root/'dashboard'))
from theme_fixture_support import isolate_process,LegacyHarness,read_corpus
private,base=isolate_process()
from PySide6.QtCore import QEventLoop,QTimer,QCoreApplication,QEvent,QObject
from theme_bundle import BundleManager
bundle=root/'theme-projects/apple-calm/bundle';cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text());BundleManager(base).import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
h=None;rows=[]
def memory(label):
 d={line.split(':')[0]:int(line.split(':')[1].split()[0]) for line in Path('/proc/self/smaps_rollup').read_text().splitlines() if line.startswith(('Rss:','Pss:'))}
 d.update(label=label,contexts=len(h.service.apiFactory._contexts),normalizationCaches=len(h.service.apiFactory._normalization_cache),leases=len(h.service._leases),pythonHeapBytes=tracemalloc.get_traced_memory(),objects=dict(collections.Counter(obj.metaObject().className() for obj in h.root.findChildren(QObject))))
 rows.append(d);print(json.dumps({k:v for k,v in d.items() if k!='objects'}),flush=True)
try:
 h=LegacyHarness(base,dict(theme='base',variant='day',motion='normal'));assert h.service.selectDraft('studio.applecalm');h.wait_ready()
 def pump(ms=30):
  loop=QEventLoop();QTimer.singleShot(round(ms),loop.quit);loop.exec()
 h.pump=pump
 cases=read_corpus()[1];case=next(c for c in cases if c['id']=='sport.match.detail:scheduled')
 tracemalloc.start();memory('initial')
 for i in range(30):
  assert h.run_case(case)['status']=='passed';QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete)
  if (i+1)%10==0:memory('repeat-'+str(i+1))
 pump(1000);memory('idle')
 gc.collect();h.engine.collectGarbage();QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);pump(200);memory('garbage-collected')
 ctypes.CDLL(None).malloc_trim(0);memory('allocator-trimmed')
 (out/'memory-retention-wire-pc.json').write_text(json.dumps(dict(status='passed',rows=rows,scope='Private software QML fixed-route stress; forced GC/trim are diagnostic only, not production behavior or an ARM RAM gate'),indent=2)+'\n')
finally:
 if h:h.close()
 private.cleanup()
