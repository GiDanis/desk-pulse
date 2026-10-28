"""Actual Main header checks for the new immutable Apple revision."""
import argparse,json,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--dashboard',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();sys.path.insert(0,str(a.dashboard.resolve()));a.output.mkdir(parents=True,exist_ok=True)
from theme_fixture_support import isolate_process,LegacyHarness
private,base=isolate_process()
from theme_bundle import validate_project,BundleManager
from PySide6.QtCore import qVersion,QObject
checked=validate_project(a.bundle,app_root=a.dashboard.resolve());cache=json.loads((a.bundle.parent/'evidence/preflight-cache.json').read_text());assert cache['digest']==checked['digest'] and cache['result']['status']=='passed' and cache['result']['qt']==qVersion()
BundleManager(base,app_root=a.dashboard.resolve()).import_bundle(a.bundle,preflight=lambda *_:cache['result'],require_preflight=True)
h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'normal'});checks=[]
def wait(test):
 end=time.monotonic()+12
 while not test() and time.monotonic()<end:h.pump(10)
 assert test(),(h.messages,h.value('familyId'))
def icon():return h.expression('shellHost.currentItem ? shellHost.currentItem.headerIcon : ""')
try:
 assert h.service.selectDraft('studio.applecalm');h.wait_ready();wait(lambda:h.service.readyToApply)
 from theme_test_support import wait_save
 assert h.service.apply(),h.service.lastError
 wait_save(h.app,h.service,timeout=15);h.wait_ready();h.expression('familyId="aquarium"')
 wait(lambda:h.aquarium.snapshot['effectivePlayback']=='running');wait(lambda:icon()=='aquarium')
 assert any(o.property('resolvedSymbol')=='aquarium' and o.property('ready') is True for o in h.root.findChildren(QObject))
 checks.append('actualHeaderFishReady')
 h.service.beginEdit()
 for mode in ('day','night'):
  assert h.service.setSection('paletteMode',mode);h.wait_ready();h.pump(100)
  assert icon()=='aquarium' and h.aquarium.snapshot['effectivePlayback']=='running'
  assert h.window.grabWindow().save(str(a.output/(mode+'.png')));checks.append(mode+'HeaderAndSwimming')
 for mode in ('reduced','off'):
  assert h.service.setSection('motionMode',mode);h.wait_ready();h.pump(100)
  assert icon()=='aquarium' and h.aquarium.snapshot['effectivePlayback']=='static';checks.append(mode+'HeaderAndStatic')
 assert h.service.setSection('motionMode','normal');h.wait_ready()
 h.expression('activateKey(9)');h.pump(100);assert icon()=='aquarium';checks.append('menuKeepsFamilyIcon')
 h.expression('activateKey(7)');h.pump(80);h.expression('activateKey(1)');wait(lambda:icon()=='clock');assert icon()=='clock';checks.append('homeIconUnchanged')
 assert not h.messages and not h.transport,(h.messages,h.transport)
 report={'status':'passed','identity':{k:checked[k] for k in ('id','version','digest')},'checks':checks,'qmlWarnings':h.messages,'networkAttempts':h.transport,'scope':'Real Main private fixtures and actual icon image readiness; no physical input claim'}
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
finally:h.close();private.cleanup()
