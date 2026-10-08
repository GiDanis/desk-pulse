"""EGLFS notification theme swaps, actual motion, delivery timing and memory.

Isolated preferences/SQLite/fixtures; no provider network and no diagnostic tween.
Only frame intervals inside explicit theme-change windows are counted. Cold first
uses and complete request-to-frame latency are retained and reported separately.
"""
from contextlib import nullcontext
import argparse
import hashlib
import platform
import socket
import json
import os
from pathlib import Path
import shutil
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument('--directory', type=Path, required=True)
parser.add_argument('--swaps', type=int, default=100)
parser.add_argument('--fonts', choices=('none','three'), default='none')
parser.add_argument('--trace', action='store_true')
args = parser.parse_args()
assert args.swaps >= 80
args.directory.mkdir(parents=True,exist_ok=True)
work = Path(tempfile.mkdtemp(prefix='smartpc-notice-board-'))
for name in ('CONFIG','CACHE','DATA'):
    os.environ['XDG_'+name+'_HOME'] = str(work/name.lower())
os.environ['SMARTPC_THEME_STORE'] = str(work/'themes')

transport_attempts=[]
def deny_network(*arguments,**keywords):
    transport_attempts.append('denied')
    raise RuntimeError('Isolated benchmark network denied')
socket.socket.connect=deny_network
socket.getaddrinfo=deny_network
try:
    with socket.socket() as probe:probe.connect(('127.0.0.1',1))
except RuntimeError:pass
assert transport_attempts==['denied']
transport_attempts.clear()

from PySide6.QtCore import QObject,QTimer,QUrl,qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService
from theme_pack import import_pack
from theme_service import FontRegistry
from theme_test_support import as_value,wait_ready

app = QGuiApplication([])
app.setOrganizationName('SmartPC'); app.setApplicationName('Notification verification')
themes = ['base','functional','personal.sample']
import_pack(Path(__file__).parent/'examples/themes/personal-sample',work/'themes')
if args.fonts == 'three':
    source=work/'source'; source.mkdir()
    themes=[]
    for i,(parent,font) in enumerate(zip(('base','functional','personal.sample'),('DejaVuSans.ttf','DejaVuSansMono.ttf','DejaVuSerif.ttf'))):
        identifier='notice.font'+str(i)
        shutil.copyfile('/usr/share/fonts/truetype/dejavu/'+font,source/'Title.ttf')
        tokens={'notifications.'+mode+'.titleFamily':'asset:title' for mode in ('small','large','urgent','badge','inbox','detail')}
        (source/'theme.json').write_text(json.dumps({'schemaVersion':1,'id':identifier,'name':identifier,'version':'1.0.0','extends':parent,
            'tokens':tokens,'assets':[{'id':'title','type':'font','path':'Title.ttf'}]}))
        import_pack(source,work/'themes'); themes.append(identifier)

events=EventService(path=':memory:',auto_refresh=False)
trace=None
if args.trace:
    from theme_trace_bridge import ThemeTraceBridge
    trace=ThemeTraceBridge()
state=DashboardState(WeatherService(auto_refresh=False),SystemInfo(),AccountService(path=work/'missing'),events,demo=True,trace=trace)
state.markCommandsSeen(); events.set_quiet(False,0,1)
state._brightness_mode='manual'; state._manual_brightness=100
service=state.appearance; service.beginEdit(); service.setSection('paletteMode','day')
engine=QQmlApplicationEngine(); warnings=[]
engine.warnings.connect(lambda values:warnings.extend(str(value) for value in values))
engine.setInitialProperties({'dashboardState':state,'traceRecorder':trace}); engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))))
assert engine.rootObjects(),warnings
root=engine.rootObjects()[0]; window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow)
if trace: trace.attach(window)
wait_ready(app,root)
names=('eventBanner','eventLargeBanner','eventUrgent','unreadAlertsBadge','alertsInbox','alertDetail')
hosts=[root.findChild(QObject,name) for name in names]
assert all(as_value(host.property('currentItem')) for host in hosts)

steps=0; request_at=None; last_frame=None; action_end=0; expected_theme=''; expected_id=''
baseline_rows=None; baseline_deadline=None; notification_at=None
latencies=[]; intervals=[]; preparation=[]; delivery=[]; samples=[]; captures=[]; peak_fonts=0
interval_samples=[]; seen_profiles=set(); cold_action=False; event_mode='small'

def rows():
    return [tuple(row) for row in events._engine.db.execute('SELECT id,notified_level,dismissed_level,seen FROM events ORDER BY id')]

def memory():
    global peak_fonts
    row={'swap':steps,'registeredFonts':len(FontRegistry.entries),'cpuTimeNs':time.process_time_ns()}
    peak_fonts=max(peak_fonts,row['registeredFonts'])
    for line in Path('/proc/self/smaps_rollup').read_text().splitlines():
        if line.startswith(('Rss:','Pss:')): key,value,*_=line.split(); row[key[:-1]]=int(value)
    samples.append(row)

def frame():
    global request_at,last_frame,baseline_rows,baseline_deadline,notification_at
    now=time.perf_counter()
    if request_at is not None and service.activeThemeId==expected_theme and not service.candidateAppearance:
        latencies.append({'swap':steps,'ms':(now-request_at)*1000,'theme':expected_theme,'eventId':expected_id})
        request_at=None
    if now <= action_end:
        if last_frame is not None:
            interval=(now-last_frame)*1000; intervals.append(interval)
            interval_samples.append({'swap':steps,'ms':interval,'firstUseOfModeAndTheme':cold_action,'mode':event_mode,'theme':expected_theme})
        last_frame=now
    if notification_at is not None and not events.eventState['bannerPending']:
        visible=events.eventState['urgent'] or events.eventState['visibleBanner']
        if visible.get('id')==expected_id:
            delivery.append({'id':expected_id,'ms':(now-notification_at)*1000})
            notification_at=None
            baseline_rows=rows(); baseline_deadline=events._banner_until

window.frameSwapped.connect(frame)

def capture(name):
    with trace.suspend_observation("screenshotOutsideLatencyWindow") if trace else nullcontext():
        image=window.grabWindow()
    assert not image.isNull() and (image.width(),image.height())==(960,640)
    assert image.save(str(args.directory/(name+'.png')))
    captures.append(name)

fatal=[]

def step_impl():
    global steps,request_at,last_frame,action_end,expected_theme,expected_id,notification_at,baseline_rows,baseline_deadline
    global cold_action,event_mode
    if request_at is not None:
        assert time.perf_counter()-request_at < 5,'No frame after a theme change'
        return
    if steps >= args.swaps:
        timer.stop(); QTimer.singleShot(600,app.quit); return
    assert all(host.property('readiness')=='ready' for host in hosts)
    if baseline_rows is not None:
        assert rows()==baseline_rows,'Changing a theme altered read/dismiss/delivery state'
        assert events._banner_until==baseline_deadline,'Changing a theme restarted the eight second timer'
    if steps % 10 == 0:
        events.publish_snapshot('notice.probe',[])
        group=steps//10; mode=('small','large','urgent')[group%3]
        event_mode=mode
        expected_id='notice-'+str(group)
        now=time.time(); notification_at=time.perf_counter()
        events.publish_snapshot('notice.probe',[{'version':1,'id':expected_id,'source':'notice.probe','sourceLabel':'Demo','category':'demo',
            'priority':3 if mode=='urgent' else 2,'bannerSize':'large' if mode=='large' else 'small',
            'title':'Avviso '+mode+' · cambio tema','detail':'Dati simulati. Composizione e font cambiano; identità, consegna e durata restano stabili.',
            'issuedAt':now,'startsAt':now-1,'expiresAt':now+3600,'revision':str(group)}])
        baseline_rows=None; baseline_deadline=None
    if steps in (9,19,29): capture(('small','large','urgent')[steps//10]+'-'+args.fonts)
    last_frame=None; request_at=time.perf_counter(); action_end=request_at+.30
    expected_theme=themes[steps%len(themes)]
    profile=(event_mode,expected_theme); cold_action=profile not in seen_profiles; seen_profiles.add(profile)
    before=time.perf_counter(); assert service.selectDraft(expected_theme),service.lastError
    preparation.append((time.perf_counter()-before)*1000)
    steps+=1; memory()

def step():
    try:step_impl()
    except Exception as error:
        fatal.append({"type":type(error).__name__,"message":str(error)})
        timer.stop();app.quit()

timer=QTimer(); timer.setInterval(350); timer.timeout.connect(step)
memtimer=QTimer(); memtimer.setInterval(100); memtimer.timeout.connect(memory)
QTimer.singleShot(500,lambda:(memory(),timer.start(),memtimer.start()))
app.exec(); memory()

def p(values, fraction):
    return round(sorted(values)[int((len(values)-1)*fraction)],3) if values else None
warm=[row['Pss'] for row in samples if 20 <= row['swap'] <= 40]
late=[row['Pss'] for row in samples if row['swap']>=80]
times=[row['ms'] for row in latencies]; warm_times=[row['ms'] for row in latencies if row['swap']>6]
warm_intervals=[row['ms'] for row in interval_samples if not row['firstUseOfModeAndTheme']]
result={'qt':qVersion(),'backend':os.environ.get('QT_QPA_PLATFORM'),'swaps':steps,'fontProfile':args.fonts,'themes':themes,
    'memoryMiB':{'peakPss':max(row['Pss'] for row in samples)/1024,'warmMedianPss':p(warm,.5)/1024,'lateMedianPss':p(late,.5)/1024,
                 'lateGrowthMiB':(p(late,.5)-p(warm,.5))/1024},
    'registeredFontsPeak':peak_fonts,'registeredFontsEnd':len(FontRegistry.entries),
    'requestToThemeFrameMs':{'count':len(times),'p95':p(times,.95),'max':max(times) if times else None,'warmP95':p(warm_times,.95)},
    'notificationToFrameMs':{'count':len(delivery),'p95':p([row['ms'] for row in delivery],.95),'max':max((row['ms'] for row in delivery),default=None)},
    'intervalMs':{'count':len(intervals),'p95':p(intervals,.95),'max':max(intervals) if intervals else None,'over33ms':sum(value>33.34 for value in intervals),'over50ms':sum(value>50 for value in intervals)},
    'warmIntervalMs':{'count':len(warm_intervals),'p95':p(warm_intervals,.95),'max':max(warm_intervals) if warm_intervals else None,'over33ms':sum(value>33.34 for value in warm_intervals)},
    'prepareMs':{'p95':p(preparation,.95),'max':max(preparation)},'samples':samples,'themeFrames':latencies,'deliveryFrames':delivery,
    'intervalSamples':interval_samples,'captures':captures,'warnings':warnings,'scope':'FrameSwapped is Qt presentation submission, not optical timing or GPU memory telemetry. Actual theme/notification transitions only; no diagnostic animation. Warm intervals exclude only the first requested (mode, theme) pair; all intervals are retained separately.'}
if trace:
    trace.finish()
    raw=trace.report()
    (args.directory/'trace.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n')
    from theme_trace_metrics import build_trace_metrics
    result['diagnostics']=build_trace_metrics(raw)
result['fatalErrors']=fatal
result['reportVersion']=2
result['traceEnabled']=args.trace
result['statisticsMethod']='sorted[floor((n-1)*q)], no interpolation'
result['legacyWarmDefinition']='swap > 6; frame intervals separately exclude first (mode,theme) pair'
result['architecture']=platform.machine()
result['pyside']=__import__('PySide6').__version__
result['display']={'width':window.width(),'height':window.height(),'dpr':window.devicePixelRatio()}
result['sourceHarnessSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
result['fixtureActionFingerprint']=hashlib.sha256(json.dumps({'themes':themes,'swaps':args.swaps,'fonts':args.fonts,'tickMs':350,'actionWindowMs':300,'noticeEvery':10,'modes':['small','large','urgent'],'captureSteps':[9,19,29]},sort_keys=True).encode()).hexdigest()
result['manifest']=json.loads(Path(__file__).with_name('release-manifest.json').read_text()) if Path(__file__).with_name('release-manifest.json').exists() else None
result['transportAttempts']=len(transport_attempts)
result['isolation']={'networkGuardPositiveControl':True,'privateXdgAndStore':True,'privateSQLite':True,'providerNetworkDisabled':True,'productionStateUsed':False}
result['productTargets']={'completeSwapP95Ms':150,'ordinaryFrameIntervalP95Ms':20,'legacySwapWithinTarget':p(times,.95)<=150,'ordinaryIntervalsWithinTarget':p(warm_intervals,.95)<=20}
if args.trace:result['productTargets']['coherentSwapWithinTarget']=result['diagnostics']['requestToCoherentSubmissionMs']['p95'] is not None and result['diagnostics']['requestToCoherentSubmissionMs']['p95']<=150
(args.directory/'report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({key:value for key,value in result.items() if key not in ('samples','themeFrames','deliveryFrames','intervalSamples','manifest','diagnostics')},ensure_ascii=False))
assert steps==args.swaps and len(times)==steps and not warnings and not fatal and not transport_attempts,(warnings,fatal,transport_attempts)
if args.trace:assert result['diagnostics']['complete'],result['diagnostics']
if not args.trace:assert result['memoryMiB']['lateGrowthMiB'] < 5
assert peak_fonts <= FontRegistry.idle_capacity+4
events.close()
