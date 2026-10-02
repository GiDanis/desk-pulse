"""100 real theme swaps, TTF first use, scene/motion and bounded memory sampling on EGLFS."""
import argparse,json,os,sys,tempfile,time,shutil
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--swaps',type=int,default=100)
parser.add_argument('--fonts',choices=('none','three'),default='three')
args=parser.parse_args();args.directory.mkdir(parents=True,exist_ok=True)
work=Path(tempfile.mkdtemp(prefix='smartpc-theme-stress-'))
os.environ['XDG_CONFIG_HOME']=str(work/'config');os.environ['XDG_CACHE_HOME']=str(work/'cache');os.environ['SMARTPC_THEME_STORE']=str(work/'themes')
from PySide6.QtCore import QObject,QTimer,QUrl,qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine,QQmlExpression
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService
from theme_service import FontRegistry
from theme_pack import import_pack

app=QGuiApplication([])
# Three actual families exercise first-use glyph caches and a bounded registration pool.
source=work/'source';source.mkdir()
for identifier,parent,font in [('stress.base','base','DejaVuSans.ttf'),('stress.functional','functional','DejaVuSansMono.ttf'),('stress.serif','base','DejaVuSerif.ttf')]:
    shutil.copyfile('/usr/share/fonts/truetype/dejavu/'+font,source/'UI.ttf')
    (source/'theme.json').write_text(json.dumps({'schemaVersion':1,'id':identifier,'name':identifier,'version':'1.0.0','extends':parent,
        'tokens':{'typography.uiFamily':'asset:ui','typography.displayFamily':'asset:ui'},'assets':[{'id':'ui','type':'font','path':'UI.ttf'}]}))
    import_pack(source,work/'themes')
events=EventService(path=':memory:',auto_refresh=False)
state=DashboardState(WeatherService(auto_refresh=False),SystemInfo(),AccountService(path=work/'missing'),events,demo=True);state.markCommandsSeen()
state._brightness_mode='manual';state._manual_brightness=100
service=state.appearance;service.beginEdit();service.setSection('paletteMode','day');service.setSection('scene',{'enabled':True})
engine=QQmlApplicationEngine();warnings=[];engine.warnings.connect(lambda errors:warnings.extend(str(e) for e in errors))
engine.setInitialProperties({'dashboardState':state});engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))));assert engine.rootObjects()
root=engine.rootObjects()[0];window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow)
from theme_test_support import wait_ready
wait_ready(app,root)
prepare_times=[];intervals=[];latencies=[];samples=[];steps=0;last_frame=None;action_at=None;action_end=0;peak_registrations=0;expected_theme=""

def memory():
    global peak_registrations
    row={'swap':steps,'time':round(time.monotonic(),3),'registeredFonts':len(FontRegistry.entries)}
    peak_registrations=max(peak_registrations,len(FontRegistry.entries))
    for line in Path('/proc/self/smaps_rollup').read_text().splitlines():
        if line.startswith(('Rss:','Pss:')):key,value,*_=line.split();row[key[:-1]]=int(value)
    samples.append(row)

def frame():
    global action_at,last_frame
    now=time.perf_counter()
    if now>action_end:return
    if action_at is not None and service.activeThemeId==expected_theme and service._candidate is None:latencies.append((now-action_at)*1000);action_at=None
    if last_frame is not None:intervals.append((now-last_frame)*1000)
    last_frame=now

def animate():
    QQmlExpression(engine.rootContext(),root,'animateMove(1,false)').evaluate()
service.changed.connect(lambda:QTimer.singleShot(0,animate))
window.frameSwapped.connect(frame)

def step():
    global steps,last_frame,action_at,action_end,expected_theme
    if steps>=args.swaps:
        timer.stop();QTimer.singleShot(900,app.quit);return
    last_frame=None;action_at=time.perf_counter();action_end=action_at+.3
    identifier=(('stress.base','stress.functional','stress.serif','base') if args.fonts=='three' else ('base','functional','base','functional'))[steps%4]
    expected_theme=identifier
    before=time.perf_counter()
    assert service.selectDraft(identifier),service.lastError
    prepare_times.append((time.perf_counter()-before)*1000)
    if steps%8 in (3,7):
        root.setProperty('familyId','meteo' if root.property('familyId')=='oggi' else 'oggi')
    steps+=1;memory()

timer=QTimer();timer.setInterval(350);timer.timeout.connect(step)
memtimer=QTimer();memtimer.setInterval(100);memtimer.timeout.connect(memory)
QTimer.singleShot(700,lambda:(memory(),timer.start(),memtimer.start()))
app.exec();memory()
ordered=sorted(intervals)
def p(values,f):return sorted(values)[int((len(values)-1)*f)] if values else None
warm=[x['Pss'] for x in samples if 20<=x['swap']<=40];late=[x['Pss'] for x in samples if x['swap']>=80]
result={'qt':qVersion(),'backend':os.environ.get('QT_QPA_PLATFORM'),'swaps':steps,'fontProfile':args.fonts,'snapshotPublications':service.revision,
        'registeredFontsPeak':peak_registrations,'registeredFontsEnd':len(FontRegistry.entries),'samples':samples,
        'memoryMiB':{'peakPss':max(x['Pss'] for x in samples)/1024,'warmMedianPss':p(warm,.5)/1024,'lateMedianPss':p(late,.5)/1024,'lateGrowthMiB':(p(late,.5)-p(warm,.5))/1024},
        'intervalMs':{'p95':p(intervals,.95),'max':max(intervals) if intervals else None,'over33ms':sum(i>33.34 for i in intervals),'over50ms':sum(i>50 for i in intervals)},
        'inputToFrameMs':{'p95':p(latencies,.95),'max':max(latencies) if latencies else None},'prepareMs':{'p95':p(prepare_times,.95),'max':max(prepare_times)},'warnings':warnings,
        'scope':'Theme preparation+commit+real QML tween and scene; retained long intervals; PSS is not direct GPU allocation telemetry.'}
(args.directory/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='samples'}))
assert steps==args.swaps and not warnings,warnings
assert result['memoryMiB']['lateGrowthMiB']<5,result['memoryMiB']
assert peak_registrations<=FontRegistry.idle_capacity+4
# Cache/allocator/GPU allocations are judged from observed plateau, not from removeApplicationFont alone.
events.close()
