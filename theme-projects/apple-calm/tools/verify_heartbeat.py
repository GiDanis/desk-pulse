#!/usr/bin/env python3
"""An unchanged public clock refresh must regain a real coherent GUI frame."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'dashboard'))
from theme_fixture_support import isolate_process,LegacyHarness
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
private,base=isolate_process();h=None
try:
 from PySide6.QtCore import QObject,qVersion
 from theme_bundle import BundleManager,validate_project
 from theme_runtime import preflight
 from theme_test_support import as_value
 project=ROOT/'theme-projects/apple-calm/bundle'
 digest=validate_project(project)['digest']
 cache=json.loads((project.parent/'evidence/preflight-cache.json').read_text())
 def checked(payload,manifest,registry):
  if cache['digest']==digest and cache['result']['qt']==qVersion() and cache['result']['status']=='passed':return cache['result']
  return preflight(payload,manifest,registry)
 BundleManager(base,app_root=ROOT/'dashboard').import_bundle(project,preflight=checked,require_preflight=True)
 h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'})
 assert h.service.selectDraft('studio.applecalm');h.wait_ready();h.pump(1200)
 assert h.service._gui_ready
 frames=[];h.window.frameSwapped.connect(lambda:frames.append(time.monotonic()))
 home=h.root.findChild(QObject,'homeNow');loader=as_value(home.property('currentLoader'));adapter=loader.findChild(QObject,'publicContextAdapter')
 clock=h.expression('timeText()')
 h.expression('now = new Date(now.getTime()+1000)')
 assert h.expression('timeText()')==clock,'the probe must leave rendered clock text unchanged'
 assert adapter.property('refreshScheduled') and not h.expression('currentThemeRenderCoherent()')
 h.service.heartbeat(False)
 assert not h.service._gui_ready
 deadline=time.monotonic()+3
 while (not h.service._gui_ready or not h.expression('currentThemeRenderCoherent()')) and time.monotonic()<deadline:h.pump(10)
 recovered=h.service._gui_ready and h.expression('currentThemeRenderCoherent()')
 report={'status':'partial' if recovered else 'failed','qt':qVersion(),'platform':h.app.platformName(),'revision':h.service.resolvedAppearance['bundleRevision'],'unchangedClockText':True,'pendingContextPositiveControl':True,'coherentAfterPublication':h.expression('currentThemeRenderCoherent()'),'readyRecovered':recovered,'realFramesAfterInvalidation':len(frames),'qmlWarnings':h.messages}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True)
 assert recovered,'coherent public DTO returned, but no submitted frame restored GUI readiness'
 assert frames and not h.messages
 # A forced frame cannot certify a required renderer of another revision.
 loaded_revision=home.property('loadedRevision')
 home.setProperty('loadedRevision',loaded_revision-1);h.service.heartbeat(False);h.pump(1300)
 assert not h.service._gui_ready and not h.expression('currentThemeRenderCoherent()')
 home.setProperty('loadedRevision',loaded_revision)
 deadline=time.monotonic()+3
 while (not h.service._gui_ready or not h.expression('currentThemeRenderCoherent()')) and time.monotonic()<deadline:h.pump(10)
 assert h.service._gui_ready and h.expression('currentThemeRenderCoherent()')
 report['staleRendererNeverAcknowledged']=True;report['restoredRendererRecovers']=True
 report['status']='passed'
 args.output.write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report),flush=True)
finally:
 if h:h.close()
 private.cleanup()
