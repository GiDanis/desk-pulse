"""Analysis only: capture unchanged 0.8.3 Main in isolated, offline fixtures."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'dashboard'))
from theme_fixture_support import isolate_process,LegacyHarness,read_corpus
parser=argparse.ArgumentParser();parser.add_argument('--theme',choices=['base','apple'],required=True);args=parser.parse_args()
out=Path(__file__).parent/args.theme;out.mkdir(exist_ok=True)
private,base=isolate_process();h=None
try:
 from PySide6.QtCore import QObject
 from PySide6.QtQml import QQmlExpression,QQmlEngine
 from theme_test_support import as_value
 if args.theme=='apple':
  from theme_bundle import BundleManager,validate_project
  bundle=ROOT/'theme-projects/apple-calm/bundle';valid=validate_project(bundle)
  cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
  assert cache['digest']==valid['digest'] and cache['result']['status']=='passed'
  BundleManager(base,app_root=ROOT/'dashboard').import_bundle(bundle,preflight=lambda *_:cache['result'],require_preflight=True)
 h=LegacyHarness(base,{'theme':'base','variant':'night','motion':'off'})
 if args.theme=='apple':
  assert h.service.selectDraft('studio.applecalm');h.wait_ready()
 _,cases,_=read_corpus();results=[]
 def ready():h.wait_ready();h.pump(150)
 def capture(name):
  ready();assert h.window.grabWindow().save(str(out/(name+'.png')))
 def expression(obj,text):
  expr=QQmlExpression(QQmlEngine.contextForObject(obj),obj,text);value,undefined=expr.evaluate();assert not expr.hasError(),expr.error().toString();return as_value(value)
 h.setup(next(c for c in cases if c['surfaceId']=='device.info'));ready()
 for tab in range(4):
  if tab:h.expression('activateKey(6)')
  ready();raw=h.expression('publicSurfacePayload("device.info")')
  record={'infoPage':h.value('infoPage'),'selectedTab':raw['selection']['tabId'],'controllerRowTitles':[r['title'] for r in raw['rows']]}
  if args.theme=='apple':
   host=h.root.findChild(QObject,'overlayHost');loader=as_value(host.property('currentLoader'));adapter=loader.findChild(QObject,'publicContextAdapter');ctx=as_value(adapter.property('publicContext'));item=as_value(host.property('currentItem'))
   record['publicRowTitles']=[ctx.rows.get(i).title for i in range(ctx.rows.count)]
   record['rendererRowTitles']=expression(item,'rows.map(row=>row.title)')
   record['revision']=ctx.dataRevision;record['contextTab']=ctx.selection.tabId;record['contextUpdatedAt']=ctx.updatedAt;record['systemUpdatedAt']=h.state.systemState['updatedAt']
  capture('info-'+str(tab));results.append(record)
 for sid in ['sport.hub','settings.index','casa.overview','casa.devices','casa.detail','network.overview','network.devices','network.router','network.wifi','network.ports','home.now','weather.now','account.usage']:
  case=next(c for c in cases if c['surfaceId']==sid);h.setup(case);capture(sid)
  if args.theme=='apple' and sid=='sport.hub':
   host=h.root.findChild(QObject,'sportHub');item=as_value(host.property('currentItem'))
   rows=next(child for child in item.findChildren(QObject) if child.metaObject().indexOfProperty('rowHeight')>=0)
   results.append({'surface':sid,'panelWidth':item.property('width'),'panelHeight':item.property('height'),'rowsHeight':rows.property('height'),'rowHeight':rows.property('rowHeight'),'capacity':rows.property('capacity'),'pageStart':rows.property('pageStart')})
  if sid=='network.overview':
   h.expression('networkOverviewSection="tools"');capture('network.tools')
 if args.theme=='apple':
  h.setup(next(c for c in cases if c['surfaceId']=='device.info'));ready()
  host=h.root.findChild(QObject,'overlayHost');loader=as_value(host.property('currentLoader'));ctx=as_value(loader.findChild(QObject,'publicContextAdapter').property('publicContext'))
  handle=ctx.requestAction('tabs.select','RISORSE',{});ready()
  item=as_value(host.property('currentItem'));results.append({'input':'public-tabs-select','status':handle.status,'infoPage':h.value('infoPage'),'contextTab':ctx.selection.tabId,'rendererRowTitles':expression(item,'rows.map(row=>row.title)')});capture('info-public-resources')
 assert not h.transport,h.transport
 report={'theme':args.theme,'qt':'6.8.2','scope':'Unchanged source, synthetic offline Main; no installation or board mutation','info':results,'qmlWarnings':h.messages,'providerTransportCalls':len(h.transport)}
 (out/'audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps(report,ensure_ascii=False))
finally:
 if h:h.close()
 private.cleanup()
