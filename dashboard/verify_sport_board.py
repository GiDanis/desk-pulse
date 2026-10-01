"""Bounded v0.6 board check: actual REST data, EGLFS captures and transitions.

Stop the kiosk before using EGLFS. Capture/benchmark work uses a separate config
and does not enable goals. An offline restart is checked with separate processes.
"""
import argparse
import json
import os
from pathlib import Path
import statistics
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument('--mode', choices=('fetch','capture','offline'), default='fetch')
parser.add_argument('--directory', required=True)
parser.add_argument('--duration', type=int, default=15)
args = parser.parse_args()
root = Path(args.directory)
root.mkdir(parents=True, exist_ok=True)
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='smartpc-v06-render-')
from sport_core import HTTPClient, read_cache, refresh_snapshot, refresh_detail, save_cache

if args.mode == 'fetch':
    client = HTTPClient()
    snapshot = refresh_snapshot(client, None, time.time(), full=True)
    upcoming = sorted((m for m in snapshot['fixtures'] if m['status'] == 'scheduled' and (m.get('kickoffUtc') or 0) >= time.time()), key=lambda m: m['kickoffUtc'])[:3]
    finished = sorted((m for m in snapshot['fixtures'] if m['status'] == 'finished'), key=lambda m: m.get('kickoffUtc') or 0)[-1:]
    details = []
    for match in upcoming + finished:
        snapshot = refresh_detail(client, snapshot, time.time(), match['canonicalMatchId'])
        selected = next(m for m in snapshot['fixtures'] if m['canonicalMatchId'] == match['canonicalMatchId'])
        assert not snapshot.get('detailError'), snapshot.get('detailError')
        assert selected.get('detailFetchedAt'), 'Detail was not merged'
        details.append({'id':selected['providerMatchId'], 'status':selected['status'], 'venue':selected['venue'],
                        'stats':len(selected['stats']), 'events':len(selected['events']), 'lineups':len(selected['lineups'])})
    # Actual response cache, only for repeatable rendering without more HTTP.
    responses = {url: [entry[1], entry[2]] for url, entry in client.cache.items() if 'matchDetails?' in url or 'summary?' in url}
    (root/'detail-responses.json').write_text(json.dumps(responses))
    save_cache(root/'sport.json', snapshot)
    result = {'provider':snapshot['provider'], 'season':snapshot['season'], 'fixtures':len(snapshot['fixtures']),
              'standings':len(snapshot['standings']), 'fetchedAt':snapshot['fetchedAt'], 'requests':client.request_count, 'details':details}
    (root/'online.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    raise SystemExit(0)

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, QMetaObject
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
import shiboken6
from account import AccountService
from app import SystemInfo
from events import EventService
from sport import SportService
from state import DashboardState
from weather import WeatherService

application = QGuiApplication([])
application.setOrganizationName('SmartPC')
application.setApplicationName('Sport board verification')

if args.mode == 'offline':
    os.environ['SMARTPC_SPORT_OFFLINE']='1'
    service = SportService(auto_refresh=False,cache_path=root/'sport.json',state_path=root/'goals.json')
    assert service.moduleState['data']['fromCache']
    assert len(service.moduleState['data']['standings']) == 20
    service.refresh()
    def finish():
        state = service.moduleState
        if state['status'] != 'offline':
            return
        assert not any(m['isLive'] for m in state['data']['fixtures'])
        result={'status':state['status'],'fromCache':state['data']['fromCache'], 'fetchedAt':state['updatedAt'],
                'fixtures':len(state['data']['fixtures']),'standings':len(state['data']['standings'])}
        (root/'offline.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result));application.quit()
    service.changed.connect(finish)
    QTimer.singleShot(5000,lambda: application.exit(2))
    raise SystemExit(application.exec())

snapshot = read_cache(root/'sport.json')
assert snapshot is not None
class Keypad(QObject):
    keyPressed=Signal(int)
    connected=False

sport = SportService(auto_refresh=False,cache_path=root/'sport.json',state_path=root/'goals.json',initial=snapshot)
responses = json.loads((root/'detail-responses.json').read_text()) if (root/'detail-responses.json').exists() else {}
for url, (payload, acquired) in responses.items():
    sport._client.cache[url] = (time.time() + 3600, payload, acquired)
weather = WeatherService(auto_refresh=False)
account = AccountService(path=Path('/var/cache/smartpc-dashboard/account-chatgpt.json'))
events = EventService(path=':memory:',auto_refresh=False)
state = DashboardState(weather,SystemInfo(),account,events,sport=sport)
state.markCommandsSeen()
keypad = Keypad()
engine = QQmlApplicationEngine()
engine.setInitialProperties({'keypad':keypad,'dashboardState':state})
engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))))
assert engine.rootObjects()
window = shiboken6.wrapInstance(shiboken6.getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    window.setVisibility(QWindow.Visibility.Windowed)
    window.resize(960,640)
window.setProperty('familyId','sport')
window.setProperty('sportView','PROSSIME')
intervals=[]
last_frame=0.0
last_action=0.0
first_frame_latencies=[]
index=0
errors=[]

def capture(name):
    image=window.grabWindow()
    assert not image.isNull() and image.width()==960 and image.height()==640, f'capture {image.width()}x{image.height()}'
    assert image.save(str(root/name))

def frame():
    global last_frame
    now=time.perf_counter()
    if last_action and last_frame < last_action <= now:
        first_frame_latencies.append((now-last_action)*1000)
    if now-last_action < 0.25 and last_frame >= last_action and 0 < now-last_frame < 0.1:
        intervals.append((now-last_frame)*1000)
    last_frame=now
window.frameSwapped.connect(frame)

# Representative real data: next/result pages, full table, focus and families.
actions=(8,5,6,8,8,8,7,2,6,4,8,2,1,4)
def action():
    global index,last_action
    last_action=time.perf_counter()
    keypad.keyPressed.emit(actions[index % len(actions)])
    index+=1

def start():
    capture('sport-next.png')
    summary_timer = window.findChild(QObject, 'sportOverviewTimer')
    QMetaObject.invokeMethod(summary_timer, 'triggered')
    QTimer.singleShot(150, next_page)
def next_page():
    capture('sport-next-page-2.png')
    window.setProperty('sportOverviewPage', 0)
    keypad.keyPressed.emit(5)
    QTimer.singleShot(150,listing)
def listing():
    capture('sport-round.png')
    keypad.keyPressed.emit(5)
    QTimer.singleShot(250,detail)
def detail():
    capture('sport-upcoming-detail.png')
    keypad.keyPressed.emit(6)
    QTimer.singleShot(150,stats)
def stats():
    capture('sport-upcoming-stats.png')
    keypad.keyPressed.emit(6)
    QTimer.singleShot(150,lineups)
def lineups():
    capture('sport-upcoming-lineups.png')
    keypad.keyPressed.emit(7);keypad.keyPressed.emit(7)
    keypad.keyPressed.emit(8)
    QTimer.singleShot(150,results)
def results():
    capture('sport-results.png')
    keypad.keyPressed.emit(5)
    # Pick the last fetched historical detail from the visible round.
    rows = window.property('sportRows').toVariant()
    selected = next((i for i,m in enumerate(rows) if m.get('detailFetchedAt')),0)
    window.setProperty('sportIndex', selected)
    keypad.keyPressed.emit(5);keypad.keyPressed.emit(6)
    QTimer.singleShot(200,finished_stats)
def finished_stats():
    capture('sport-finished-stats.png')
    keypad.keyPressed.emit(6)
    QTimer.singleShot(150,finished_lineups)
def finished_lineups():
    capture('sport-finished-lineups.png')
    keypad.keyPressed.emit(7);keypad.keyPressed.emit(7)
    keypad.keyPressed.emit(8)
    QTimer.singleShot(150, primary_table)
def primary_table():
    assert window.property('sportView') == 'CLASSIFICA'
    capture('sport-table-primary.png')
    keypad.keyPressed.emit(5)
    QTimer.singleShot(150,table)
def table():
    capture('sport-table.png')
    keypad.keyPressed.emit(7)
    keypad.keyPressed.emit(9)
    window.setProperty('menuIndex',1);keypad.keyPressed.emit(5)
    window.setProperty('settingsIndex',5);keypad.keyPressed.emit(5);keypad.keyPressed.emit(5)
    QTimer.singleShot(150,settings)
def settings():
    capture('sport-settings.png')
    keypad.keyPressed.emit(1);keypad.keyPressed.emit(4)
    timer.start()
    QTimer.singleShot(args.duration*1000,finish)
def finish():
    timer.stop()
    ordered=sorted(intervals)
    result={'renderer':str(window.rendererInterface().graphicsApi()),'duration_s':args.duration,
            'actions':index,'frames':len(intervals),'provider':snapshot['provider'],'fixture_count':len(snapshot['fixtures']),
            'median_ms':round(statistics.median(intervals),2) if intervals else None,
            'p95_ms':round(ordered[int((len(ordered)-1)*.95)],2) if ordered else None,
            'max_ms':round(max(intervals),2) if intervals else None,
            'first_frame_max_ms':round(max(first_frame_latencies),2) if first_frame_latencies else None,
            'scope':'short actual-data navigation measurement; excludes first frames after idle; reports first-frame latency separately; not endurance or fixed-60fps guarantee'}
    (root/'render.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));events.close();application.quit()
timer=QTimer();timer.setInterval(450);timer.timeout.connect(action)
QTimer.singleShot(400,start)
QTimer.singleShot((args.duration + 12)*1000, lambda: application.exit(2))
raise SystemExit(application.exec())
