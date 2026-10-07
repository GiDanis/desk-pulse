#!/usr/bin/env python3
"""Apply/verify through real Main and ThemeService; run with the kiosk stopped.

Uses the production appearance store, but isolated demo providers and in-memory
events. Does not mark first-run commands seen or write provider preferences.
"""
import argparse
import json
from pathlib import Path
import sys
import time

parser=argparse.ArgumentParser()
parser.add_argument('--dashboard',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--apply',action='store_true')
parser.add_argument('--manifest',type=Path,help='Require and explicitly select this exact installed revision')
args=parser.parse_args()
expected=json.loads(args.manifest.read_text()) if args.manifest else None
identity={'id':'studio.applecalm','version':expected['themeVersion'],'digest':expected['bundleDigest']} if expected else None
sys.path.insert(0,str(args.dashboard.resolve()))
from PySide6.QtCore import QObject,QSettings,QUrl,qInstallMessageHandler,qVersion
from PySide6.QtGui import QGuiApplication,QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService
from theme_api import bootstrap_theme_api
from theme_test_support import wait_ready,wait_save

app=QGuiApplication([]);app.setOrganizationName('SmartPC');app.setApplicationName('SmartPC')
warnings=[];qInstallMessageHandler(lambda kind,context,message:warnings.append(message))
settings=QSettings('SmartPC','Dashboard')
def preferences():
 settings.sync()
 return {key:settings.value(key) for key in settings.allKeys() if not key.startswith('appearance/') and key not in ('animationsEnabled','nightMode')}
before=preferences()
events=EventService(path=':memory:',auto_refresh=False)
state=DashboardState(WeatherService(auto_refresh=False),SystemInfo(),AccountService(path=Path('/tmp/apple-calm-no-account-fixture')),events,demo=True)
engine=QQmlApplicationEngine();bootstrap_theme_api(engine)
engine.setInitialProperties({'dashboardState':state});engine.load(QUrl.fromLocalFile(str(args.dashboard.resolve()/'Main.qml')))
assert engine.rootObjects(),warnings
root=engine.rootObjects()[0];window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow)
if app.platformName()=='offscreen':window.setVisibility(QWindow.Visibility.Windowed);window.resize(960,640)
service=state.appearance
def until(predicate,timeout=15):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  app.processEvents()
  if predicate():return
  time.sleep(.003)
 raise AssertionError({'status':service.status,'error':service.lastError,'warnings':warnings})
wait_ready(app,root,timeout=15)
if args.apply:
 service.beginEdit();assert service.selectDraft('studio.applecalm'),service.lastError
 wait_ready(app,root,timeout=15)
 if identity:
  assert any(all(row.get(key)==value for key,value in identity.items()) for row in service.revisions),'requested revision is absent'
  for _ in range(len(service.revisions)):
   if service.resolvedAppearance['bundleRevision']==identity:break
   assert service.stepRevision(1),service.lastError
   wait_ready(app,root,timeout=15)
  assert service.resolvedAppearance['bundleRevision']==identity,'requested revision was not selected'
 until(lambda:service.readyToApply)
 assert service.apply(),service.lastError
 wait_save(app,service,timeout=15)
assert service.activeThemeId=='studio.applecalm',(service.activeThemeId,service.lastError)
until(lambda:service._gui_ready)
revision=service.resolvedAppearance['bundleRevision']
if identity:assert revision==identity,{'expected':identity,'actual':revision}
journal=service.lifecycle.read()
assert journal['active']==revision and journal['pending'] is None,journal
assert preferences()==before,'non-appearance preferences changed'
assert not warnings,warnings
args.output.mkdir(parents=True,exist_ok=True)
assert window.grabWindow().save(str(args.output/'installed-home-demo.png'))
report={'status':'passed','operation':'apply' if args.apply else 'coldVerify','qt':qVersion(),'platform':app.platformName(),'windowSize':[window.width(),window.height()],'revision':revision,'journalActiveMatches':True,'pendingActivation':False,'nonAppearancePreferencesPreserved':True,'nonAppearancePreferenceCount':len(before),'qmlWarnings':warnings,'providerData':'isolated demo, no live-data claim'}
(args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
events.close()
