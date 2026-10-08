"""Passive idle control: no clock tick, no observer-manufactured update/tween."""
import argparse
import json
from pathlib import Path
import time
from theme_fixture_support import isolate_process

parser=argparse.ArgumentParser()
parser.add_argument('--trace',action='store_true')
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
private,base=isolate_process()
from PySide6.QtCore import QObject,QTimer,QUrl,qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService
from theme_test_support import wait_ready

app=QGuiApplication([])
app.setOrganizationName('SmartPC');app.setApplicationName('SmartPC')
trace=None
if args.trace:
    from theme_trace_bridge import ThemeTraceBridge
    trace=ThemeTraceBridge()
events=EventService(path=':memory:',auto_refresh=False)
state=DashboardState(WeatherService(auto_refresh=False),SystemInfo(),AccountService(path=base/'missing'),events,demo=True,trace=trace)
state.markCommandsSeen();state._brightness_mode='manual';state._manual_brightness=100
engine=QQmlApplicationEngine();warnings=[]
engine.warnings.connect(lambda values:warnings.extend(str(value) for value in values))
engine.setInitialProperties({'dashboardState':state,'traceRecorder':trace})
engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))))
assert engine.rootObjects(),warnings
window=engine.rootObjects()[0]
if trace:trace.attach(window)
wait_ready(app,window)
window.findChild(QObject,'clockTimer').setProperty('running',False)
frames=[];measuring=False;started=0
window.frameSwapped.connect(lambda:frames.append(time.perf_counter_ns()) if measuring else None)
def begin():
    global measuring,started
    measuring=True;started=time.perf_counter_ns()
    QTimer.singleShot(10000,app.quit)
QTimer.singleShot(2000,begin)
app.exec()
if trace:trace.finish()
result={'reportVersion':1,'qt':qVersion(),'traceEnabled':args.trace,'durationNs':time.perf_counter_ns()-started,
        'idleFrames':len(frames),'warnings':warnings,'scope':'Main clock explicitly stopped; only test start/deadline timers; no observer update/poll/tween',
        'trace':trace.report() if trace else None}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2)+'\n')
events.close();private.cleanup()
assert not frames and not warnings,(len(frames),warnings)
print(json.dumps({k:v for k,v in result.items() if k!='trace'}))
