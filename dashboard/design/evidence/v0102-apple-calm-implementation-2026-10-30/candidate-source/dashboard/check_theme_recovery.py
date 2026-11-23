"""A broken catalog must leave QML-only Base, Home/navigation and providers usable."""
import os,tempfile
from pathlib import Path
from unittest.mock import patch
os.environ['XDG_CONFIG_HOME']=tempfile.mkdtemp(prefix='smartpc-recovery-')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
from PySide6.QtCore import QObject,QUrl,Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from theme_core import ThemeError
from state import DashboardState
from weather import WeatherService
from account import AccountService
from events import EventService
from system_info import SystemInfo
from theme_test_support import wait_ready,as_value
app=QGuiApplication([])
class Keypad(QObject):keyPressed=Signal(int)
events=EventService(path=':memory:',auto_refresh=False)
with patch('state.ThemeService',side_effect=ThemeError('base','catalogo guasto')):
 state=DashboardState(WeatherService(auto_refresh=False),SystemInfo(),AccountService(path=Path(os.environ['XDG_CONFIG_HOME'])/'missing'),events,demo=True)
state.markCommandsSeen();assert state.appearance is None and state.themeRecoveryError
keypad=Keypad();engine=QQmlApplicationEngine();warnings=[];engine.warnings.connect(lambda errors:warnings.extend(str(e) for e in errors))
engine.setInitialProperties({'dashboardState':state,'keypad':keypad});engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))));assert engine.rootObjects(),warnings
root=engine.rootObjects()[0];wait_ready(app,root);assert root.findChild(QObject,'homeNow').property('readiness')=='ready'
keypad.keyPressed.emit(6);wait_ready(app,root);assert root.property('familyId')=='meteo'
assert as_value(root.property('weatherData'))['temperature']
assert all(root.findChild(QObject,name).property('readiness')=='ready' for name in ('eventBanner','eventLargeBanner','eventUrgent','unreadAlertsBadge','alertsInbox','alertDetail'))
events.set_quiet(False,0,1);events.set_demo_scenario('urgente');app.processEvents()
assert root.findChild(QObject,'eventUrgent').property('visible')
keypad.keyPressed.emit(7);assert not events.eventState['urgent'];events.close()
assert not warnings,warnings
print('Recovery: broken Python catalog, independent QML fallback, real Home/Meteo, preserved data and navigation PASS')
