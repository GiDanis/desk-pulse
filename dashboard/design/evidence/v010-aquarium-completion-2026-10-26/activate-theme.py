"""Apply only the qualified immutable revision through real Main readiness."""
import argparse,json,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args();sys.path.insert(0,'/opt/smartpc/dashboard')
from PySide6.QtCore import QSettings,QUrl,QThreadPool,QCoreApplication,QEvent
from PySide6.QtGui import QGuiApplication,QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from theme_bundle import BundleManager,validate_project
from theme_api import bootstrap_theme_api
from account import AccountService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService
from theme_test_support import wait_ready,wait_save
app=QGuiApplication([]);app.setOrganizationName('SmartPC');app.setApplicationName('SmartPC')
bundle=a.stage/'theme-projects/apple-calm/bundle';cache=json.loads((bundle.parent/'evidence/preflight-cache.json').read_text());checked=validate_project(bundle)
from PySide6.QtCore import qVersion
assert cache['digest']==checked['digest'] and cache['result']['status']=='passed' and cache['result']['qt']==qVersion()
identity={k:checked[k] for k in ('id','version','digest')};assert identity['version']=='1.6.5'
revision=BundleManager(Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC')).import_bundle(a.stage/'apple-calm-1.6.5.smartpc-theme',preflight=lambda *_:cache['result'],require_preflight=True)
assert {k:revision[k] for k in identity}==identity
weather=WeatherService(auto_refresh=False);account=AccountService();state=DashboardState(weather,SystemInfo(),account)
service=state.appearance;previous=dict(service.draft);assert previous['bundleRevision']['version']=='1.6.4'
profiles_before=json.loads(QSettings('SmartPC','Dashboard').value('appearance/themeOverrides','{}'))
engine=QQmlApplicationEngine();bootstrap_theme_api(engine);engine.setInitialProperties({'dashboardState':state});engine.load(QUrl.fromLocalFile('/opt/smartpc/dashboard/Main.qml'));assert engine.rootObjects()
root=engine.rootObjects()[0];window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow);window.setVisibility(QWindow.Windowed);window.resize(960,640)
try:
 wait_ready(app,root,timeout=20);service.beginEdit();assert service._change({**previous,'bundleRevision':identity}),service.lastError
 end=time.monotonic()+30
 while not service.readyToApply and time.monotonic()<end:app.processEvents();time.sleep(.01)
 assert service.readyToApply,service.lastError
 assert service.apply(),service.lastError
 wait_save(app,service,timeout=20)
 current=json.loads(QSettings('SmartPC','Dashboard').value('appearance/config'));assert current=={**previous,'bundleRevision':identity},'Appearance options changed'
 assert service.lifecycle.read()['active']==identity and service.lifecycle.read()['pending'] is None
 profiles_after=json.loads(QSettings('SmartPC','Dashboard').value('appearance/themeOverrides','{}'))
 from theme_lifecycle import selection_key
 assert profiles_after[selection_key(identity)]==previous['overrides']
 assert all(profiles_after.get(k)==v for k,v in profiles_before.items() if not k.startswith('studio.applecalm@'))
 result={'status':'passed','before':previous['bundleRevision'],'after':identity,'appearanceOptionsPreserved':True,'otherThemeProfilesPreserved':True,'activeOverridesCopiedToNewIdentity':True}
 (a.stage/'activation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
finally:
 weather.close();account.close();service.cancel();window.close();engine.deleteLater();app.processEvents()
 assert QThreadPool.globalInstance().waitForDone(5000)
 QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
