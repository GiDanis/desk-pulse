"""Two-process persistence proof with real network failure in PrivateNetwork.

Prepare isolated theme/preferences/weather/events, then verify in a fresh process.
No production data, no OS reboot claim; EGLFS capture uses the real display path.
"""
import argparse,json,os,time,subprocess
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--directory',type=Path,required=True)
parser.add_argument('--prepare',action='store_true')
args=parser.parse_args();args.directory.mkdir(parents=True,exist_ok=True)
for field in ('CONFIG','CACHE','DATA'):os.environ['XDG_'+field+'_HOME']=str(args.directory/field.lower())
os.environ['SMARTPC_THEME_STORE']=str(args.directory/'themes')
from PySide6.QtCore import QStandardPaths,QTimer,QUrl,QThreadPool,qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from theme_service import ThemeService
from events import EventService
from weather import WeatherService
from state import DashboardState,DEMO_WEATHER
from account import AccountService
from system_info import SystemInfo
from theme_test_support import wait_ready,wait_save,as_value
app=QGuiApplication([]);app.setOrganizationName('SmartPC');app.setApplicationName('SmartPC')
database=args.directory/'events.sqlite'

def rows(events):
    return {row['id']:{name:row[name] for name in ('notified_level','dismissed_level','seen')} for row in events._engine.db.execute('SELECT id,notified_level,dismissed_level,seen FROM events')}

if args.prepare:
    service=ThemeService();service.beginEdit();assert service.selectDraft('functional')
    assert service.setSection('paletteMode','night') and service.setSection('motionMode','reduced')
    assert service.setToken('notifications.small.titleSize',31)
    assert service.apply();wait_save(app,service)
    cache=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation))/'weather.json'
    cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps({'snapshot':DEMO_WEATHER,'fetched_at':time.time()-3600}))
    events=EventService(path=database,auto_refresh=False);events.set_quiet(False,0,1)
    now=time.time();values=[]
    for index,identifier in enumerate(('a-delivered','b-pending','c-dismissed')):
        values.append({'version':1,'id':identifier,'source':'restart.probe','sourceLabel':'Demo','category':'demo',
            'priority':3 if index==2 else 2,'title':identifier,'detail':'Evento simulato per verifica del riavvio offline.',
            'issuedAt':now,'startsAt':now-30+index,'expiresAt':now+3600,'revision':'1'})
    events.publish_snapshot('restart.probe',values);events.dismiss('c-dismissed')
    events.setPresentationAcknowledgement(True);events.setBannerAvailable(True)
    assert events.markBannerPresented('a-delivered','1',2)
    (args.directory/'before.json').write_text(json.dumps(rows(events),indent=2)+'\n');events.close()
    print('Prepared isolated notification state and Functional/night/reduced theme');raise SystemExit()

interfaces=json.loads(subprocess.check_output(['ip','-j','address'],text=True))
addresses=[item['local'] for row in interfaces for item in row.get('addr_info',[]) if item.get('scope')=='global']
routes=json.loads(subprocess.check_output(['ip','-j','route','show','default'],text=True))
assert not addresses and not routes,'Verification requires a PrivateNetwork namespace'
weather=WeatherService(auto_refresh=True);events=EventService(path=database,auto_refresh=False)
before=json.loads((args.directory/'before.json').read_text());assert rows(events)==before
state=DashboardState(weather,SystemInfo(),AccountService(path=args.directory/'missing'),events)
state.markCommandsSeen();state._brightness_mode='manual';state._manual_brightness=100;events.set_quiet(False,0,1)
assert state.appearance.activeThemeId=='functional'
assert state.appearance.resolvedAppearance['motionMode']=='reduced'
assert state.appearance.resolvedAppearance['tokens']['notifications.small.titleSize']==31
engine=QQmlApplicationEngine();warnings=[];engine.warnings.connect(lambda values:warnings.extend(str(value) for value in values))
engine.setInitialProperties({'dashboardState':state});engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))));assert engine.rootObjects(),warnings
root=engine.rootObjects()[0];window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow)
wait_ready(app,root);started=time.monotonic();done=False

def finish():
    global done
    if done:return
    if weather.moduleState['status']=='updating' or events.eventState['bannerPending']:
        assert time.monotonic()-started<30,'Offline startup timeout'
        return
    assert weather.moduleState['status']=='offline',weather.moduleState['status']
    assert as_value(root.property('weatherData'))['temperature']=='18°'
    assert events.eventState['visibleBanner']['id']=='b-pending'
    assert not events.eventState['urgent'] and events.eventState['unreadCount']==2
    after=rows(events);assert after['a-delivered']==before['a-delivered'] and after['c-dismissed']==before['c-dismissed']
    assert after['b-pending']=={'notified_level':2,'dismissed_level':0,'seen':0}
    assert root.findChild(__import__('PySide6.QtCore',fromlist=['QObject']).QObject,'eventBanner').property('loadedPresentationId')=='builtin.alerts.small-rail'
    image=window.grabWindow();assert (image.width(),image.height())==(960,640)
    assert image.save(str(args.directory/'cold-notifications.png'))
    assert not warnings,warnings
    report={'qt':qVersion(),'backend':os.environ.get('QT_QPA_PLATFORM'),'weatherStatus':weather.moduleState['status'],
        'theme':state.appearance.activeThemeId,'variant':state.appearance.resolvedAppearance['variant'],'motion':'reduced','titleSize':31,
        'deliveredNotReplayed':True,'pendingDeliveredAfterFrame':True,'dismissalAndReadPreserved':True,'before':before,'after':after,
        'globalAddresses':addresses,'defaultRoutes':routes,'warnings':warnings,'scope':'Fresh process, isolated SQLite/preferences/cache, actual Open-Meteo failure in PrivateNetwork; no OS reboot.'}
    (args.directory/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
    done=True;timer.stop();app.quit()

timer=QTimer();timer.setInterval(250);timer.timeout.connect(finish);timer.start();app.exec()
QThreadPool.globalInstance().waitForDone(3000);events.close();assert done
