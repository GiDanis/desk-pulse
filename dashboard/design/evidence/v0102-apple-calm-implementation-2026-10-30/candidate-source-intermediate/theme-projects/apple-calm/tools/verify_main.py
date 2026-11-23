#!/usr/bin/env python3
"""Apple Calm against real Main, canonical fixtures, and public action routing."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'dashboard'))
from theme_fixture_support import isolate_process,LegacyHarness,read_corpus
P=argparse.ArgumentParser();P.add_argument('--output',type=Path,required=True);P.add_argument('--palette',default='day',choices=['day','night']);P.add_argument('--all',action='store_true');P.add_argument('--surfaces',help='Comma-separated surfaces for a targeted regression');A=P.parse_args()
A.output.mkdir(parents=True,exist_ok=True)
private,base=isolate_process();h=None;records=[];captured=set()
try:
 from theme_bundle import BundleManager,validate_project
 from theme_runtime import preflight
 from PySide6.QtCore import QObject,qVersion,SIGNAL
 from PySide6.QtQml import QQmlEngine,QQmlExpression
 from theme_test_support import as_value,wait_save
 manager=BundleManager(base,app_root=ROOT/'dashboard')
 project=ROOT/'theme-projects/apple-calm/bundle'
 validation=validate_project(project)
 digest=validation['digest']
 expected_content_height=validation['manifest']['layout']['content']['height']
 cache_path=project.parent/'evidence/preflight-cache.json'
 cache=json.loads(cache_path.read_text()) if cache_path.exists() else {}
 def checked_preflight(payload,manifest,registry):
  if cache.get('digest')==digest and cache.get('result',{}).get('status')=='passed' and cache['result'].get('qt')==qVersion():return cache['result']
  print('Preflight matrix '+digest,flush=True)
  result=preflight(payload,manifest,registry)
  cache_path.write_text(json.dumps({'digest':digest,'result':result},indent=2)+'\n')
  return result
 revision=manager.import_bundle(project,preflight=checked_preflight,require_preflight=True)
 h=LegacyHarness(base,{'theme':'base','variant':A.palette,'motion':'off'})
 assert 'sport.match.detail' not in h.service._prepared_contents
 assert h.service.selectDraft('studio.applecalm'),{'error':h.service.lastError,'catalogErrors':h.service.catalog.errors}
 h.wait_ready();h.reset_effects()
 def context(host):
  loader=as_value(host.property('currentLoader'));assert loader is not None
  adapter=loader.findChild(QObject,'publicContextAdapter');assert adapter is not None
  return as_value(adapter.property('publicContext'))
 def expression(obj,text):
  e=QQmlExpression(QQmlEngine.contextForObject(obj),obj,text);value,undefined=e.evaluate();assert not e.hasError(),e.error().toString();assert not undefined,text;return as_value(value)
 names={'home.now':'homeNow','home.clock':'homeClock','home.day':'homeDay','casa.overview':'casaOverview','casa.devices':'casaDevices','network.overview':'networkOverview','network.devices':'networkDevices','weather.now':'weatherNow','weather.forecast':'weatherForecast','account.usage':'accountPanel','sport.hub':'sportHub','sport.overview':'sportPanel','sport.team':'sportTeamPanel','racing.overview':'racingPanel','alerts.badge':'unreadAlertsBadge','alerts.banner.small':'eventBanner','alerts.banner.large':'eventLargeBanner','alerts.urgent':'eventUrgent','alerts.inbox':'alertsInbox','alerts.detail':'alertDetail','shell.main':'shellHost'}
 registry=json.loads((ROOT/'theme-projects/apple-calm/bundle/theme.json').read_text())['presentations']
 def host_for(sid):return h.root.findChild(QObject,names.get(sid,'overlayHost'))
 def capture(label):
  image=h.window.grabWindow();assert not image.isNull();assert image.save(str(A.output/(label+'.png')))
 _,cases,contract=read_corpus()
 own=[c for c in cases if c['surfaceId'] in registry]
 if not A.all:
  seen=set();own=[c for c in own if not(c['surfaceId'] in seen or seen.add(c['surfaceId']))]
 if A.surfaces:own=[c for c in own if c['surfaceId'] in A.surfaces.split(',')]
 for case in own:
  h.setup(case)
  for expected in case['expectedExpressions']:assert h.expression(expected),(case['id'],expected)
  h.assert_match_domain(case)
  host=host_for(case['surfaceId']);assert host is not None,case['surfaceId']
  item=as_value(host.property('currentItem'));assert item is not None,(case['id'],'renderer absent',h.messages)
  assert str(host.property('loadedPresentationId')).endswith(registry[case['surfaceId']]),(case['id'],host.property('loadedPresentationId'))
  assert item.property('ready') is True and item.property('contentReady') is True,case['id']
  assert item.property('width')>0 and item.property('height')>0,case['id']
  assert not h.messages,(case['id'],h.messages)
  ctx=context(host)
  shell=host_for('shell.main');shell_context=context(shell);shell_item=as_value(shell.property('currentItem'))
  side=shell_item.findChild(QObject,'viewDots')
  assert side.property('count')==shell_context.navigation.scopeCount,(case['id'],'scope count')
  assert side.property('selectedIndex')==shell_context.navigation.scopePosition-1,(case['id'],'scope position')
  assert shell_item.property('visible') == (not shell_context.uiStatus.urgent),(case['id'],'shell urgency visibility')
  if case['surfaceId'] in ['home.now','weather.now'] and ctx.weather and ctx.weather.code==0:
   assert item.findChild(QObject,'weatherSymbol').property('resolvedSymbol')=='sun'
  if not case['surfaceId'].startswith('alerts.'):
   assert ctx.commands.count>0 and all(ctx.commands.get(i).enabled for i in range(ctx.commands.count))
  before={k:h.value(k) for k in h.KEPT};flags=h.event_flags();deadline=h.events._banner_until
  oldscale=h.service.resolvedAppearance['tokens']['typography.textScale']
  assert h.service.setToken('typography.textScale',1.1 if oldscale!=1.1 else 1.0);h.wait_ready();h.pump(30)
  assert {k:h.value(k) for k in h.KEPT}==before,(case['id'],'theme reset navigation')
  assert h.event_flags()==flags and h.events._banner_until==deadline,(case['id'],'theme altered notification delivery')
  assert not any(h.effects.values()) and not h.transport,(case['id'],'provider side effect')
  assert not h.messages,(case['id'],h.messages)
  assert h.window.activeFocusItem().objectName()=='inputOwner'
  h.service.setToken('typography.textScale',1.0);h.wait_ready()
  if case['surfaceId'] not in captured:
   captured.add(case['surfaceId'])
   capture(case['id'].replace(':','--').replace('/','-'))
  records.append({'id':case['id'],'surface':case['surfaceId'],'status':'passed','typedContext':context(host).metaObject().className(),'renderer':str(host.property('loadedPresentationId')),'navigationPreserved':True,'deliveryPreserved':True,'providerEffects':0})
  print('PASS '+case['id'],flush=True)
 # Real navigation, wrapping and dynamic module visibility drive both dot axes.
 h.setup(next(c for c in cases if c['surfaceId']=='home.now'))
 def dots():
  item=as_value(host_for('shell.main').property('currentItem'))
  return item.findChild(QObject,'familyDots'),item.findChild(QObject,'viewDots')
 def wait_dots_settled():
  deadline=time.monotonic()+3
  while any(dot.property('animating') for dot in dots()) and time.monotonic()<deadline:h.pump(10)
  assert not any(dot.property('animating') for dot in dots()),'dot animation did not finish'
 navigation_steps=0
 def wait_navigation_published():
  deadline=time.monotonic()+3
  while time.monotonic()<deadline:
   ctx=context(host_for('shell.main'));expected=h.expression('navigationSnapshot()')
   if ctx.navigation.familyId==expected['familyId'] and ctx.navigation.scopePosition==expected['scopePosition'] and ctx.navigation.scopeId==expected['scopeId']:break
   h.pump(5)
  assert ctx.navigation.familyId==expected['familyId'] and ctx.navigation.scopePosition==expected['scopePosition'] and ctx.navigation.scopeId==expected['scopeId'],'navigation publication did not settle'
  return ctx
 def check_dots():
  global navigation_steps
  ctx=wait_navigation_published();wait_dots_settled()
  family,view=dots()
  for indicator,count,position in [(family,ctx.navigation.familyCount,ctx.navigation.familyPosition),(view,ctx.navigation.scopeCount,ctx.navigation.scopePosition)]:
   assert indicator.property('count')==count and indicator.property('selectedIndex')==position-1
   assert abs(indicator.property('position')-20*(position-1))<.1,{'axis':indicator.objectName(),'position':indicator.property('position'),'target':indicator.property('targetPosition'),'selected':position,'animating':indicator.property('animating'),'mode':ctx.motionPolicy.mode}
  assert abs(family.property('x')+family.property('width')/2-480)<.1
  assert view.property('x')==939
  assert h.expression('pageGeometry("home.now").height')==expected_content_height
  navigation_steps+=1
 for direction in (1,-1):
  for _ in range(len(h.value('families'))):
   check_dots()
   for key in (8,2):
    for _ in range(len(h.value('currentFamily')['views'])+1):
     h.expression('activateKey('+str(key)+')');h.wait_ready();h.pump(30);check_dots()
   h.expression('activateKey('+str(6 if direction>0 else 4)+')');h.wait_ready();h.pump(30)
 h.root.setProperty('familyId','oggi');h.wait_ready();h.pump(30)
 old_count=dots()[0].property('count');h.state.toggleModuleVisibility('meteo');h.wait_ready();h.pump(30)
 assert dots()[0].property('count')==old_count-1;check_dots()
 h.state.toggleModuleVisibility('meteo');h.wait_ready();h.pump(30);assert dots()[0].property('count')==old_count
 motion_checks=[]
 animation_starts={'family':0,'view':0}
 for axis,dot in zip(('family','view'),dots()):
  animation=next(child for child in dot.findChildren(QObject) if child.metaObject().className()=='QQuickNumberAnimation')
  def started(running,axis=axis):
   if running:animation_starts[axis]+=1
  QObject.connect(animation,SIGNAL('runningChanged(bool)'),started)
 def wait_motion_start(axis,before,mode):
  deadline=time.monotonic()+3
  while mode!='off' and animation_starts[axis]==before and time.monotonic()<deadline:h.pump(5)
  if mode=='off':h.wait_ready();h.pump(30)
  assert (animation_starts[axis]>before)==(mode!='off'),(mode,axis,'animation start signal')
 for mode,duration in [('normal',140),('reduced',80),('off',0)]:
  assert h.service.setSection('motionMode',mode);h.wait_ready();h.pump(30);wait_dots_settled()
  family,view=dots();assert family.property('duration')==duration,(mode,family.property('duration'))
  before=animation_starts['family'];h.expression('activateKey(6)')
  wait_motion_start('family',before,mode)
  wait_dots_settled();check_dots()
  h.root.setProperty('familyId','oggi');h.wait_ready();h.pump(30);wait_dots_settled()
  before=animation_starts['view'];h.expression('activateKey(8)')
  wait_motion_start('view',before,mode)
  wait_dots_settled();check_dots()
  h.expression('activateKey(8)');wait_navigation_published()
  item=as_value(host_for('shell.main').property('currentItem'));expression(item,'(settleMotion(),true)')
  assert not any(dot.property('animating') for dot in dots()),'settleMotion did not cancel animation immediately'
  check_dots()
  motion_checks.append({'mode':mode,'durationMs':duration,'bothAxes':True,'settled':True})
 assert h.service.setSection('motionMode','off');h.wait_ready();h.pump(40)
 h.setup(next(c for c in cases if c['surfaceId']=='home.now'));capture('navigation-home')
 h.expression('activateKey(6)');h.expression('activateKey(8)');h.wait_ready();h.pump(40);capture('navigation-weather-second-view')
 # The list shown by the theme must use the exact round and keyboard order.
 h.setup(next(c for c in cases if c['surfaceId']=='sport.fixtures'))
 ctx=context(host_for('sport.fixtures'))
 assert [ctx.matches.get(i).id for i in range(ctx.matches.count)]==h.expression('publicSurfacePayload("sport.fixtures").rows.map(row => row.id)')
 # More statistics than the viewport fits remain reachable by keypad.
 h.setup(next(c for c in cases if c['surfaceId']=='sport.match.detail' and c['variant']=='finished'))
 selected=h.value('sportMatchId')
 target=next(m for m in h.sport._snapshot['fixtures'] if m['canonicalMatchId']==selected)
 target['stats']=[{'id':'stat-'+str(i),'label':'Statistica '+str(i),'home':i,'away':0} for i in range(20)]
 h.sport.changed.emit();h.root.setProperty('sportDetailPage',1);h.wait_ready();h.pump(50)
 for _ in range(12):h.expression('activateKey(8)');h.pump(5)
 ctx=context(host_for('sport.match.detail'));assert ctx.selection.count==20 and ctx.selection.index>0
 item=as_value(host_for('sport.match.detail').property('currentItem'));scroll=item.findChild(QObject,'statisticsScroll');assert scroll.property('contentY')>0
 capture('long-statistics-scrolled')
 # Long notification must scroll through the public action and root extent bridge.
 case=next(c for c in cases if c['surfaceId']=='alerts.detail');h.setup(case)
 event=h.value('selectedAlert');event['detail']='Avviso lungo di prova. '+('Dati sintetici, nessun evento reale. '*180);h.root.setProperty('selectedAlert',event);h.pump(60)
 host=host_for('alerts.detail');item=as_value(host.property('currentItem'));ctx=context(host)
 deadline=time.monotonic()+5
 while item.property('scrollMaximum')<=500 and time.monotonic()<deadline:h.pump(30)
 maximum=item.property('scrollMaximum');assert maximum>500,{'maximum':maximum,'width':item.property('width'),'height':item.property('height'),'mode':item.property('mode'),'publicBodyLength':len(ctx.eventData.body),'selectedDetailLength':len(h.value('selectedAlert').get('detail','')),'warnings':h.messages}
 deadline=time.monotonic()+5
 while ctx.scrollMaximum!=item.property('scrollMaximum') and time.monotonic()<deadline:h.pump(30)
 maximum=item.property('scrollMaximum')
 assert ctx.scrollMaximum==maximum,(ctx.scrollMaximum,maximum)
 result=ctx.request('scrollDetails',event['id'],{'delta':500});assert result.status=='completed',result.status
 h.pump(60);assert h.value('alertScroll')==500
 scroll=item.findChild(QObject,'notificationScroll');assert abs(scroll.property('contentY')-500)<1
 capture('long-notification-scrolled')
 # Team picker includes the actual app route for clearing a favourite.
 h.setup(next(c for c in cases if c['surfaceId']=='sport.team.picker'))
 ctx=context(host_for('sport.team.picker'));assert ctx.teams.get(0).id=='none'
 h.sport._favourite='inter';h.sport.changed.emit();h.pump(20)
 result=ctx.requestAction('selection.select','none',{});assert result.status=='completed',result.status
 result=ctx.requestAction('details.open','none',{});assert result.status=='completed',result.status
 assert h.sport._favourite==''
 # Account with more than two windows must publish the actual viewport offset.
 h.root.setProperty('overlay','');h.root.setProperty('familyId','account')
 h.account.value['data']['windows']=[{'name':'Finestra '+str(i),'usedPercent':i,'resetAt':h.now+3600} for i in range(4)];h.account.changed.emit();h.root.setProperty('accountIndex',2);h.wait_ready();h.pump(50)
 ctx=context(host_for('account.usage'));assert ctx.selection.index==2 and ctx.selection.count==4
 item=as_value(host_for('account.usage').property('currentItem'));assert item.property('first')==2
 capture('account-page-two')
 # Apply writes the immutable identity; reloading retains all appearance choices.
 deadline=time.monotonic()+10
 while not h.service.readyToApply and time.monotonic()<deadline:h.pump(30)
 assert h.service.readyToApply,{'status':h.service.status,'error':h.service.lastError,'warnings':h.messages}
 assert h.service.apply(),h.service.lastError;wait_save(h.app,h.service)
 assert h.service.activeThemeId=='studio.applecalm'
 assert h.service.reloadCatalog();h.wait_ready()
 for _ in range(10):
  h.root.setProperty('overlay','menu');h.wait_ready();h.root.setProperty('overlay','');h.wait_ready()
 assert not h.messages,h.messages
 assert not h.transport,h.transport
 report={'status':'passed','qt':qVersion(),'platform':h.app.platformName(),'windowSize':[h.window.width(),h.window.height()],'palette':A.palette,'revision':{k:revision[k] for k in ['id','version','digest']},'apiFingerprint':contract.fingerprint,'canonicalCases':records,'additionalChecks':['sport-fixtures-keyboard-order','long-statistics-keypad-scroll','typed-notification-root-scroll-extent','public-detail-scroll-dispatch','team-picker-none-route','account-public-selection-offset','apply-reload','ten-menu-cycles'],'qmlWarnings':h.messages,'networkDenied':True,'boardRuntime':'eglfsFixtures' if h.app.platformName()=='eglfs' else 'notVerified','performance':'notVerified'}
 report['navigationDots']={'steps':navigation_steps,'dynamicFamilies':True,'centeredFamilies':True,'rightEdgeViews':True,'contentHeight':h.expression('pageGeometry("home.now").height'),'motion':motion_checks}
 report['additionalChecks']+=['navigation-both-axes-and-wrap','dynamic-family-dot-count','normal-reduced-off-dot-animation','dot-settlement','consistent-overlay-scopes','persistent-shell-across-details-and-settings']
 (A.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='canonicalCases'},ensure_ascii=False),flush=True)
except Exception:
 import traceback
 traceback.print_exc()
 (A.output/'failure.json').write_text(json.dumps({'status':'failed','completedCases':records,'qmlWarnings':h.messages if h else []},ensure_ascii=False,indent=2))
 raise
finally:
 if h:h.close()
 private.cleanup()
