"""Repeatable EGLFS motion/capture evidence; isolated preferences, no network.

Works with the pre-engine dashboard through --dashboard, so baseline and release
use identical data/actions. Only intervals inside motion windows are counted;
long stalls inside those windows are retained. Idle gaps are excluded by resetting
the timestamp at each action, not by deleting intervals above a threshold.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument('--dashboard', type=Path, default=Path(__file__).parent)
parser.add_argument('--directory', type=Path, required=True)
parser.add_argument('--duration', type=int, default=20)
parser.add_argument('--theme', default='base')
parser.add_argument('--variant', choices=('day','night'), default='day')
parser.add_argument('--motion', choices=('normal','reduced','off'),default='normal')
args = parser.parse_args()
sys.path.insert(0,str(args.dashboard.resolve()))
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='smartpc-theme-board-')
os.environ['XDG_CACHE_HOME'] = tempfile.mkdtemp(prefix='smartpc-theme-cache-')
os.environ['SMARTPC_THEME_STORE'] = tempfile.mkdtemp(prefix='smartpc-theme-store-')
args.directory.mkdir(parents=True,exist_ok=True)
from PySide6.QtCore import QObject,QTimer,QUrl,Signal,QThreadPool,qVersion
from PySide6.QtGui import QGuiApplication,QFontInfo
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from events import EventService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService

class Keypad(QObject):
    keyPressed=Signal(int)
    connected=False

app=QGuiApplication([])
app.setOrganizationName('SmartPC'); app.setApplicationName('Theme verification')
events=EventService(path=':memory:',auto_refresh=False)
state=DashboardState(WeatherService(auto_refresh=False),SystemInfo(),AccountService(path=Path(os.environ['XDG_CONFIG_HOME'])/'missing.json'),events,demo=True)
state.markCommandsSeen(); state._night_mode=args.variant
state._brightness_mode='manual'; state._manual_brightness=100
keypad=Keypad(); engine=QQmlApplicationEngine(); warnings=[]
engine.warnings.connect(lambda errors:warnings.extend(str(e) for e in errors))
appearance=getattr(state,'appearance',None)
if appearance:
    appearance.beginEdit(); appearance.selectDraft(args.theme); appearance.setSection('paletteMode',args.variant); appearance.setSection('motionMode',args.motion); appearance.preview()
engine.setInitialProperties({'keypad':keypad,'dashboardState':state})
engine.load(QUrl.fromLocalFile(str((args.dashboard/'Main.qml').resolve())))
assert engine.rootObjects(),warnings
root=engine.rootObjects()[0]
window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow)
intervals=[]; latencies=[]; memory=[]; captures=[]
last_frame=None; action_at=None; action_end=0; actions=0

def mem():
    fields={}
    for line in Path('/proc/self/smaps_rollup').read_text().splitlines():
        if line.startswith(('Rss:','Pss:')):
            k,v,*_=line.split(); fields[k[:-1]]=int(v)
    memory.append({'at':round(time.monotonic(),3),**fields})

def frame():
    global last_frame,action_at
    now=time.perf_counter()
    if now<=action_end:
        if action_at is not None:
            latencies.append((now-action_at)*1000); action_at=None
        if last_frame is not None:
            intervals.append((now-last_frame)*1000)
        last_frame=now

def capture(name):
    img=window.grabWindow()
    assert not img.isNull() and img.width()==960 and img.height()==640
    assert img.save(str(args.directory/(name+'.png')))
    captures.append(name)

def navigate():
    global last_frame,action_at,action_end,actions
    action_at=time.perf_counter(); action_end=action_at+0.30; last_frame=None
    keypad.keyPressed.emit((6,8,4,2)[actions%4]); actions+=1

window.frameSwapped.connect(frame)
timer=QTimer(); timer.setInterval(450); timer.timeout.connect(navigate)
memtimer=QTimer(); memtimer.setInterval(1000); memtimer.timeout.connect(mem)
def start():
    capture('home-'+args.theme+'-'+args.variant); mem(); timer.start(); memtimer.start()
QTimer.singleShot(700,start)
QTimer.singleShot(args.duration*1000,app.quit)
app.exec(); mem()
font=QFontInfo(app.font())
def p(values,fraction):
    return round(sorted(values)[int((len(values)-1)*fraction)],3) if values else None
result={'qt':qVersion(),'backend':os.environ.get('QT_QPA_PLATFORM'),'theme':args.theme,'variant':args.variant,'motionMode':args.motion,'durationSeconds':args.duration,'transitions':actions,'animatedIntervals':len(intervals),'intervalMs':{'median':p(intervals,.5),'p95':p(intervals,.95),'p99':p(intervals,.99),'max':round(max(intervals),3) if intervals else None,'over33ms':sum(i>33.34 for i in intervals),'over50ms':sum(i>50 for i in intervals)},'inputToFrameMs':{'p95':p(latencies,.95),'max':round(max(latencies),3) if latencies else None},'memoryKiB':memory,'defaultFont':font.family(),'captures':captures,'warnings':warnings,'scope':'Qt frameSwapped timing inside explicit motion windows; not optical panel or direct GPU timing.'}
(args.directory/'report.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='memoryKiB'}))
events.close(); QThreadPool.globalInstance().waitForDone(3000)
assert not warnings,warnings
if args.motion != 'off': assert intervals,'No animated frames captured'
