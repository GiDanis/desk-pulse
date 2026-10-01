"""QML Sport integration and fresh-process cache checks; no external network."""
import json
import os
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='smartpc-sport-ui-')
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, QThreadPool, QMetaObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from keypad import KeyDecoder, KEY_POSITIONS
from app import SystemInfo
from account import AccountService
from events import EventService
from state import DashboardState
from sport import SportService
from sport_core import save_cache, refresh_detail
from weather import WeatherService


class Keypad(QObject):
    keyPressed = Signal(int)
    connected = False


def main():
    app = QGuiApplication([])
    app.setOrganizationName('SmartPC')
    app.setApplicationName('Sport check')
    directory = Path(os.environ['XDG_CONFIG_HOME'])
    data = json.loads(Path(__file__).with_name('fixtures').joinpath('sport-normalized-sample.json').read_text())
    now = time.time()
    data['fetchedAt'] = data['standingsFetchedAt'] = now
    for match in data['fixtures']:
        match['fetchedAt'] = now
    sport = SportService(auto_refresh=False, cache_path=directory/'sport.json', state_path=directory/'goals.json', initial=data, verified=False)
    events = EventService(path=directory/'events.sqlite3', auto_refresh=False)
    weather = WeatherService(auto_refresh=False)
    account = AccountService(path=directory/'missing.json')
    state = DashboardState(weather, SystemInfo(), account, events, demo=True, sport=sport)
    state.markCommandsSeen()
    keypad = Keypad()
    engine = QQmlApplicationEngine()
    qml_errors = []
    engine.warnings.connect(lambda errors: qml_errors.extend(str(error) for error in errors))
    engine.setInitialProperties({'keypad':keypad, 'dashboardState':state})
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))))
    assert engine.rootObjects(), 'Sport QML did not load'
    window = engine.rootObjects()[0]
    def value(name):
        v = window.property(name)
        return v.toVariant() if hasattr(v,'toVariant') else v
    decoder = KeyDecoder()
    hid_codes = {position: code for code, position in KEY_POSITIONS.items()}
    def press(key):
        decoder.feed(1, 29, 1)
        if key == 1: decoder.feed(1, 42, 1)
        decoded = decoder.feed(1, hid_codes[key], 1)
        assert decoded == key
        decoder.feed(1, hid_codes[key], 0)
        decoder.feed(1, 42, 0); decoder.feed(1, 29, 0)
        keypad.keyPressed.emit(decoded)
        app.processEvents()
    press(4)
    assert value('familyId') == 'sport'
    assert value('sportView') == 'PROSSIME'
    assert value('sportMatch')['homeTeam']
    assert 'FotMob' in window.findChild(QObject, 'sportSourceText').property('text')
    press(8)
    assert value('sportView') == 'RISULTATI'  # No empty Live page.
    press(8)
    assert value('sportView') == 'CLASSIFICA' and value('overlay') == ''
    panel = window.findChild(QObject, 'sportPanel')
    assert len(panel.property('rows').toVariant()) == 3
    press(5)
    assert value('overlay') == 'sportTable'
    for _ in range(19): press(8)
    assert value('sportIndex') == 19
    press(7); press(2)
    assert value('sportView') == 'RISULTATI'
    press(5)
    assert value('overlay') == 'sportList' 
    press(6)
    assert value('overlay') == 'sportTable'
    for _ in range(19): press(8)
    assert value('sportIndex') == 19
    assert len(value('sportRows')) == 20
    press(3); press(7)
    assert value('sportIndex') == 19, 'alerts lost table focus'
    press(7)
    assert value('overlay') == ''
    press(5)
    sport._offline = True
    press(5)
    assert value('overlay') == 'sportDetail'
    selected = value('sportMatchId')
    press(3); press(7)
    assert value('overlay') == 'sportDetail' and value('sportMatchId') == selected
    press(7); press(7)
    assert value('overlay') == ''
    QTimer.singleShot(100, app.quit)
    app.exec()
    QThreadPool.globalInstance().waitForDone(3000); app.processEvents()
    assert sport.moduleState['status'] == 'offline'
    # Round selector, tab bookmarks and contextual future-detail empty states.
    press(2)  # Results -> Prossime
    press(5)
    assert len(value('sportRows')) <= 10
    while value('sportIndex') >= 0: press(2)
    previous_round = value('sportRound')
    press(6)
    assert value('sportRound') != previous_round and value('sportIndex') == -1
    press(4); press(8); press(8)
    focused = value('sportFocusedId')
    press(6); press(8); press(8); press(4)
    assert value('sportFocusedId') == focused
    press(7)
    # A newer selection made while a worker runs must be loaded next.
    sport._offline = False
    raw = json.loads(Path(__file__).with_name('fixtures').joinpath('sport-fotmob-upcoming-detail.json').read_text())
    requested = []
    upcoming = sport.moduleState['data']['upcoming'][:2]
    def detail_load(client, snapshot, timestamp, selected):
        requested.append(selected)
        time.sleep(.05)
        target = next(m for m in snapshot['fixtures'] if m['canonicalMatchId'] == selected)
        from copy import deepcopy
        payload = deepcopy(raw)
        payload['general']['matchId'] = target['providerMatchId']
        for side, team in zip(('home', 'away'), payload['header']['teams']):
            team['name'] = target[side + 'Team']
        class Client:
            def get(self, url): return payload, time.time()
        return refresh_detail(Client(), snapshot, timestamp, selected)
    with patch('sport.refresh_detail', side_effect=detail_load):
        sport.selectMatch(upcoming[0]['canonicalMatchId'])
        sport.selectMatch(upcoming[1]['canonicalMatchId'])
        deadline = time.monotonic() + 3
        while sport._worker and time.monotonic() < deadline:
            app.processEvents(); time.sleep(.005)
        assert not sport._worker and requested == [m['canonicalMatchId'] for m in upcoming]
    sport._offline = True
    press(5); press(5)
    assert value('overlay') == 'sportDetail'
    press(6)
    assert 'dopo il calcio' in window.findChild(QObject, 'sportDetailStatsEmpty').property('text')
    press(6)
    assert 'non ancora pubblicate' in window.findChild(QObject, 'sportDetailLineupsEmpty').property('text')
    page = value('sportDetailPage')
    press(3); press(7)
    assert value('sportDetailPage') == page
    press(7); press(7)
    QThreadPool.globalInstance().waitForDone(3000); app.processEvents()
    # Verified configuration must survive a new service, without enabling gol.
    sport.cycleFavourite(1)
    sport.toggleHome()
    again = SportService(auto_refresh=False, cache_path=directory/'missing-cache.json', state_path=directory/'other-goals.json')
    assert again.moduleState['data']['favourite'] == sport.moduleState['data']['favourite']
    assert again.moduleState['data']['showOnHome']
    sport.toggleGoals()
    assert not sport.moduleState['data']['goalsEnabled']
    sport._offline = True
    sport.refresh()
    # Actual worker failure preserves the current provider's snapshot.
    QTimer.singleShot(100, app.quit)
    app.exec()
    QThreadPool.globalInstance().waitForDone(3000)
    app.processEvents()
    assert sport.moduleState['status'] == 'offline'
    assert len(sport.moduleState['data']['standings']) == 20
    save_cache(directory/'sport.json', data)
    restarted = SportService(auto_refresh=False, cache_path=directory/'sport.json', state_path=directory/'restarted-goals.json')
    assert restarted.moduleState['status'] == 'stale'
    assert restarted.moduleState['data']['fromCache']
    with patch('sport.refresh_detail', side_effect=detail_load):
        restarted.selectMatch(upcoming[0]['canonicalMatchId'])
        deadline = time.monotonic() + 3
        while restarted._worker and time.monotonic() < deadline:
            app.processEvents(); time.sleep(.005)
        assert not restarted._worker
    assert restarted.moduleState['data']['fromCache'], 'one detail made the whole cached calendar fresh'
    assert not any(m['isLive'] for m in restarted.moduleState['data']['fixtures'])
    # Multiple simultaneous fixtures appear, with more than three on page two.
    window.setProperty('sportView', 'PROSSIME')
    original_snapshot = data
    from copy import deepcopy
    simultaneous = deepcopy(data)
    future = [m for m in simultaneous['fixtures'] if m['status'] == 'scheduled'][:4]
    for m in future: m.update(kickoffUtc=now+3600, round='6')
    sport._snapshot = simultaneous
    sport._error = ''
    sport.changed.emit(); app.processEvents()
    assert {m['canonicalMatchId'] for m in future} <= {m['canonicalMatchId'] for m in value('sportOverviewMatches')}
    assert len(panel.property('rows').toVariant()) == 3
    first_page = {m['canonicalMatchId'] for m in panel.property('rows').toVariant()}
    timer = window.findChild(QObject, 'sportOverviewTimer')
    QMetaObject.invokeMethod(timer, 'triggered'); app.processEvents()
    assert value('sportOverviewPage') == 1
    shown = {m['canonicalMatchId'] for m in panel.property('rows').toVariant()}
    assert {m['canonicalMatchId'] for m in future} <= first_page | shown
    press(5)
    assert not timer.property('running'), 'summary rotation continued during selection'
    press(7)
    for m in future: m.update(status='live', kickoffUtc=now-1800, homeScore=0, awayScore=0)
    sport.changed.emit(); app.processEvents()
    press(8)
    assert value('sportView') == 'IN CORSO'
    assert len(value('sportOverviewMatches')) == 4
    assert len(panel.property('rows').toVariant()) == 3
    assert value('sportOverviewPages') == 2
    assert not any(m['isLive'] for m in value('sportOverviewMatches'))
    QMetaObject.invokeMethod(timer, 'triggered'); app.processEvents()
    assert len(panel.property('rows').toVariant()) == 1
    # Classifica remains reachable in the presence of an active fixture.
    press(8); press(8)
    assert value('sportView') == 'CLASSIFICA'
    press(5)
    assert value('overlay') == 'sportTable' and len(value('sportRows')) == 20
    press(7); press(2); press(2)
    assert value('sportView') == 'IN CORSO'
    for m in future: m['status'] = 'finished'
    sport.changed.emit(); app.processEvents()
    assert value('sportView') == 'IN CORSO', 'update unexpectedly changed page'
    assert value('sportMatch')['status'] == 'finished', 'final result disappeared'
    assert panel.property('rows').toVariant()[0]['status'] == 'finished'
    state.toggleModuleVisibility('sport')
    # Main.qml must also recover when visibility is changed outside the menu.
    app.processEvents()
    assert 'sport' not in state.visibleModules
    events.close()
    assert not qml_errors, qml_errors
    print('Sport QML: primary table/HID decoder/simultaneous fixtures/rotation/rounds/tab bookmarks/future detail/queued selection/empty states/focus/settings/offline/cache/live gate PASS')


if __name__ == '__main__':
    main()
