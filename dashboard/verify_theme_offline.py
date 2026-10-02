"""Cold EGLFS start with real network failure in a PrivateNetwork systemd unit.

The cache and preferences are isolated fixtures; host networking is preserved.
Run with --prepare once, then run normally after reboot from the test unit.
"""
import argparse,json,os,time,subprocess
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
args.directory.mkdir(parents=True,exist_ok=True)
os.environ['XDG_CONFIG_HOME']=str(args.directory/'config');os.environ['XDG_CACHE_HOME']=str(args.directory/'cache');os.environ['SMARTPC_THEME_STORE']=str(args.directory/'themes')
from PySide6.QtCore import QObject,QSettings,QTimer,QUrl,Signal,QStandardPaths,QThreadPool
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from theme_service import ThemeService
from state import DashboardState,DEMO_WEATHER
from weather import WeatherService
from account import AccountService
from events import EventService
from system_info import SystemInfo
from theme_test_support import wait_ready,wait_save,as_value
app=QGuiApplication([]);app.setOrganizationName('SmartPC');app.setApplicationName('SmartPC')
if args.prepare:
 service=ThemeService();service.beginEdit();assert service.selectDraft('functional');assert service.setSection('paletteMode','night');assert service.setSection('motionMode','reduced');assert service.apply();wait_save(app,service)
 cache=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation))/'weather.json';cache.parent.mkdir(parents=True,exist_ok=True)
 cache.write_text(json.dumps({'snapshot':DEMO_WEATHER,'fetched_at':time.time()-3600}));print('Prepared isolated Functional/night/reduced preferences and weather cache');raise SystemExit()
class Keypad(QObject):keyPressed=Signal(int)
weather=WeatherService(auto_refresh=True)
assert weather.moduleState['data']['temperature']=='18°' and weather.moduleState['status']=='stale'
events=EventService(path=':memory:',auto_refresh=False)
state=DashboardState(weather,SystemInfo(),AccountService(path=args.directory/'missing'),events);state.markCommandsSeen();state._brightness_mode='manual';state._manual_brightness=100
assert state.appearance.activeThemeId=='functional' and state.appearance.resolvedAppearance['motionMode']=='reduced'
engine=QQmlApplicationEngine();warnings=[];engine.warnings.connect(lambda errors:warnings.extend(str(e) for e in errors))
keypad=Keypad();engine.setInitialProperties({'dashboardState':state,'keypad':keypad});engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))));assert engine.rootObjects(),warnings
root=engine.rootObjects()[0];window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow)
wait_ready(app,root);started=time.monotonic();done=False

def finish():
 global done
 if done:return
 if weather.moduleState['status']=='updating' and time.monotonic()-started<30:return
 done=True;timer.stop()
 status=weather.moduleState['status'];assert status=='offline',status
 keypad.keyPressed.emit(6);wait_ready(app,root);assert root.property('familyId')=='meteo'
 assert as_value(root.property('weatherData'))['temperature']=='18°'
 image=window.grabWindow();assert image.width()==960 and image.height()==640 and image.save(str(args.directory/'cold-offline.png'))
 report={'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'networkInterfaces':sorted(p.name for p in Path('/sys/class/net').iterdir()),'status':status,'cacheRetained':True,'theme':state.appearance.activeThemeId,'variant':state.appearance.resolvedAppearance['variant'],'motion':state.appearance.resolvedAppearance['motionMode'],'navigation':'Home → Meteo','seconds':round(time.monotonic()-started,2),'warnings':warnings,'scope':'Physical reboot; isolated preferences/cache; real Open-Meteo request fails in PrivateNetwork namespace. Host LAN remains reachable.'}
 interfaces=json.loads(subprocess.check_output(['ip','-j','address'],text=True))
 global_addresses=[a['local'] for row in interfaces for a in row.get('addr_info',[]) if a.get('scope')=='global']
 default_routes=json.loads(subprocess.check_output(['ip','-j','route','show','default'],text=True))
 report.update(globalAddresses=global_addresses,defaultRoutes=default_routes)
 assert not global_addresses and not default_routes,report
 assert not warnings,warnings
 (args.directory/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);app.quit()

timer=QTimer();timer.setInterval(250);timer.timeout.connect(finish);timer.start();app.exec();QThreadPool.globalInstance().waitForDone(3000);events.close();assert done
