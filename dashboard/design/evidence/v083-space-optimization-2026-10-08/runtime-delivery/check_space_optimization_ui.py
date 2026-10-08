#!/usr/bin/env python3
"""Real Main regressions for conservative Apple Calm spacing and row updates."""
import argparse,json,os
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
if os.environ['QT_QPA_PLATFORM']=='offscreen':os.environ.setdefault('QT_QUICK_BACKEND','software')
from theme_fixture_support import isolate_process,LegacyHarness,read_corpus
from theme_bundle import BundleManager,validate_project
from theme_test_support import as_value
from PySide6.QtCore import QObject,qVersion
from PySide6.QtQml import QQmlEngine,QQmlExpression
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--capture-dir',type=Path);p.add_argument('--palette',choices=['day','night'],default='night');args=p.parse_args()
private,base=isolate_process();h=None;checks=[]
args.capture_dir=args.capture_dir or Path(private.name)/'space-captures'
args.capture_dir.mkdir(parents=True,exist_ok=True)
try:
 bundle=ROOT/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
 cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
 assert cache['digest']==valid['digest'] and cache['result']['status']=='passed' and cache['result']['qt']==qVersion()
 BundleManager(base,app_root=ROOT/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
 h=LegacyHarness(base,{'theme':'base','variant':args.palette,'motion':'off'})
 assert h.service.selectDraft('studio.applecalm');h.wait_ready()
 _,cases,_=read_corpus()
 names={'sport.hub':'sportHub','settings.index':'overlayHost','casa.overview':'casaOverview','network.overview':'networkOverview'}
 def ready():h.wait_ready();h.pump(120)
 def setup(sid):h.setup(next(c for c in cases if c['surfaceId']==sid));ready()
 def host(sid):return h.root.findChild(QObject,names.get(sid,'overlayHost'))
 def item(sid):return as_value(host(sid).property('currentItem'))
 def expr(obj,text):
  e=QQmlExpression(QQmlEngine.contextForObject(obj),obj,text);v,u=e.evaluate();assert not e.hasError(),e.error().toString();assert not u,text;return as_value(v)
 def capture(name):ready();assert h.window.grabWindow().save(str(args.capture_dir/(name+'.png')))
 setup('device.info')
 for tab in range(4):
  if tab:h.expression('activateKey(6)');ready()
  view=item('device.info');expected=[r['title'] for r in h.expression('publicSurfacePayload("device.info")')['rows']]
  assert expr(view,'rows.map(row=>row.title)')==expected
  scrolling=view.findChild(QObject,'scrollingRows');assert scrolling
  assert expr(scrolling,'itemAtIndex(0).modelData.title')==expected[0]
  capture('info-'+str(tab));checks.append('Info '+str(tab)+' rendered rows match DTO')
 h.expression('activateKey(4)');h.expression('activateKey(4)');h.expression('activateKey(4)');ready()
 loader=as_value(host('device.info').property('currentLoader'));ctx=as_value(loader.findChild(QObject,'publicContextAdapter').property('publicContext'))
 ctx.requestAction('tabs.select','RISORSE',{});ready();assert expr(item('device.info'),'rows[0].title')=='Temperature'
 assert ctx.updatedAt==h.state.systemState['updatedAt'];assert expr(item('device.info'),'footer').startswith('Rilevato ')
 checks.append('Equal-count tab replacement via keys and public action; timestamp present')
 for sid in ['sport.hub','settings.index','casa.overview','casa.devices','network.overview','network.devices','network.router','network.wifi','network.ports','network.detail','settings.network']:
  setup(sid);capture(sid)
  if sid=='sport.hub':
   view=item(sid);scrolling=view.findChild(QObject,'scrollingRows')
   assert scrolling.property('count')==3
   assert expr(scrolling,'contentHeight <= height'),('sport clipping',scrolling.property('contentHeight'),scrolling.property('height'))
   assert view.property('footerText')==''
  if sid=='settings.index':
   for _ in range(5):h.expression('activateKey(8)')
   ready();scrolling=item(sid).findChild(QObject,'scrollingRows');assert scrolling.property('contentY')>0
   assert expr(scrolling,'itemAtIndex(5).y>=contentY && itemAtIndex(5).y+itemAtIndex(5).height<=contentY+height+0.5')
   capture('settings-last-selected')
  checks.append(sid+' captured without QML warnings')
 for scale in [1.1,1.0]:
  assert h.service.setToken('typography.textScale',scale);ready();setup('sport.hub')
  scrolling=item('sport.hub').findChild(QObject,'scrollingRows');assert scrolling.property('count')==3
  h.expression('activateKey(8)');h.expression('activateKey(8)');ready()
  assert expr(scrolling,'itemAtIndex(2).y>=contentY && itemAtIndex(2).y+itemAtIndex(2).height<=contentY+height+0.5')
  capture('sport-scale-'+str(scale));checks.append('Last discipline visible at scale '+str(scale))
 assert not h.messages,h.messages
 assert not h.transport,h.transport
 report={'status':'passed','scope':'Synthetic real Main, not live providers or physical readability','platform':os.environ['QT_QPA_PLATFORM'],'windowSize':[h.window.width(),h.window.height()],'qt':qVersion(),'checks':checks,'themeDigest':valid['digest'],'palette':args.palette,'qmlWarnings':h.messages,'transportCalls':len(h.transport)}
 (args.capture_dir/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps(report,ensure_ascii=False))
finally:
 if h:h.close()
 private.cleanup()
