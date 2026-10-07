"""Theme integration: fresh engines, typed preview, loads/focus, save and scene continuity."""
import os
import tempfile
os.environ['XDG_CONFIG_HOME']=tempfile.mkdtemp(prefix='smartpc-theme-check-')
os.environ['SMARTPC_THEME_STORE']=os.path.join(tempfile.mkdtemp(prefix='smartpc-theme-packs-'),'themes')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
from pathlib import Path
import time
from unittest.mock import patch
from PySide6.QtCore import QObject, QUrl, Qt, QEvent, QCoreApplication, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication, QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression
from PySide6.QtQuick import QQuickWindow
import shiboken6
from events import EventService
from account import AccountService
from state import DashboardState
from system_info import SystemInfo
from weather import WeatherService
from theme_service import ThemeService
from theme_test_support import as_value, current_item, wait_ready, wait_save

app=QGuiApplication([]);app.setOrganizationName('SmartPC');app.setApplicationName('Theme check')
messages=[];qInstallMessageHandler(lambda kind,context,message: messages.append(message))

def create():
    state=DashboardState(WeatherService(auto_refresh=False),SystemInfo(),AccountService(path=Path(os.environ['XDG_CONFIG_HOME'])/'missing'),EventService(path=':memory:',auto_refresh=False),demo=True)
    state.markCommandsSeen()
    engine=QQmlApplicationEngine();engine.setInitialProperties({'dashboardState':state});engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name('Main.qml'))))
    assert engine.rootObjects(),messages
    root=engine.rootObjects()[0];window=shiboken6.wrapInstance(shiboken6.getCppPointer(root)[0],QQuickWindow)
    wait_ready(app,root);return engine,state,root,window

def wait(ms=200):
    deadline=time.monotonic()+ms/1000
    while time.monotonic()<deadline:app.processEvents();time.sleep(.002)

def press(window,key):
    QCoreApplication.sendEvent(window,QKeyEvent(QEvent.Type.KeyPress,key,Qt.KeyboardModifier.NoModifier))
    QCoreApplication.sendEvent(window,QKeyEvent(QEvent.Type.KeyRelease,key,Qt.KeyboardModifier.NoModifier))
    wait(30)

engine,state,root,window=create();service=state.appearance
initial=current_item(app,root,'homeNow');controller_selection=as_value(root.property('viewIndex'))
assert service.resolvedAppearance["tokens"]["typography.uiFamily"]==app.font().family()
revision=service.revision
wait(100);assert service.revision==revision,'idle republished style'
service.beginEdit();assert service.setToken('shape.radiusCard',0);wait(50)
assert QQmlExpression(engine.rootContext(),root,'style.radiusCard').evaluate()[0]==0
assert not service.setToken('color.surface','#fff');assert service.resolvedAppearance['tokens']['shape.radiusCard']==0
before_commit=service.revision
assert service.selectDraft('functional');assert service.revision==before_commit,'layout was published before readiness'
wait_ready(app,root)
assert root.findChild(QObject,'homeNow').property('loadedPresentationId')=='builtin.home.centered'
assert current_item(app,root,'homeNow') is not initial
assert as_value(root.property('viewIndex'))==controller_selection
# Qt keys prove activeFocus; FakeKeypad would bypass this path.
assert window.activeFocusItem().objectName()=='inputOwner'
press(window,Qt.Key_Right);assert root.property('familyId')=='meteo';wait_ready(app,root)
press(window,Qt.Key_9);assert root.property('overlay')=='menu'
assert service.selectDraft('base');assert service.selectDraft('functional');wait(80)
assert root.property('overlay')=='menu';assert window.activeFocusItem().objectName()=='inputOwner'
press(window,Qt.Key_Escape);assert root.property('overlay')==''
# A menu/urgent arriving during a real Home Loader preparation must retain focus.
press(window,Qt.Key_1);wait_ready(app,root);service.beginEdit();assert service.selectDraft('functional')
assert service.candidateAppearance
QCoreApplication.sendEvent(window,QKeyEvent(QEvent.Type.KeyPress,Qt.Key_9,Qt.KeyboardModifier.NoModifier))
assert root.property('overlay')=='menu';wait_ready(app,root)
assert window.activeFocusItem().objectName()=='inputOwner'
press(window,Qt.Key_Escape)
service.selectDraft('base')
state._events.set_demo_scenario('urgente');wait_ready(app,root)
assert as_value(root.property('urgentEvent'))['id'];assert window.activeFocusItem().objectName()=='inputOwner'
assert root.findChild(QObject,'eventUrgent').property('visible')
press(window,Qt.Key_Escape);assert not as_value(root.property('urgentEvent')).get('id')
# Rapid navigation/theme swaps must settle transforms and stop stale candidate callbacks.
for i in range(12):
    service.selectDraft('base' if i%2 else 'functional');press(window,Qt.Key_Left if i%2 else Qt.Key_Right)
wait_ready(app,root);wait(220)
layer=root.findChild(QObject,'contentLayer');assert abs(layer.property('x'))<.01 and layer.property('y')==90 and layer.property('opacity')==1
# Scene host identity and actor state survive navigation and appearance previews.
assert service.setSection('scene',{'enabled':True});wait(40)
assert service.apply();wait_save(app,service)
scene=root.findChild(QObject,'sceneHost');identity=scene;actor_state=as_value(scene.property('actorState'))
actor_state.setProperty('pose','playing')
press(window,Qt.Key_1);wait_ready(app,root);press(window,Qt.Key_Right);wait_ready(app,root)
assert actor_state.property('pose')=='playing','navigation overwrote actor action'
assert root.findChild(QObject,'sceneHost') is identity and as_value(scene.property('actorState'))==actor_state
# Configuration is atomic and persists after explicit Apply only.
service.beginEdit()
assert service.setSection('motionMode','off');assert service.apply();wait_save(app,service)
assert not service.editing
persisted=ThemeService();assert persisted.resolvedAppearance['motionMode']=='off'
service.beginEdit();service.selectDraft('base');service.cancel();assert service.activeThemeId==persisted.activeThemeId
# A simulated worker failure restores committed appearance and retains the editable draft.
service.beginEdit();service.setSection('motionMode','normal')
with patch('theme_service.QThreadPool') as pool:
    assert service.apply()
service._saved(False,'write failure');assert service.draft['motionMode']=='normal';assert service.resolvedAppearance['motionMode']=='off';assert service.editing
service.cancel()
# Exercise numeric values through the actual QML editor and Qt keyboard path.
QQmlExpression(engine.rootContext(),root,'pushOverlay("appearance")').evaluate()
root.findChild(QObject,'settingsPanel').setProperty('advancedAppearance',True)
root.setProperty('optionIndex',6);before=service.resolvedAppearance['tokens']['shape.radiusCard'];press(window,Qt.Key_Right)
assert service.resolvedAppearance['tokens']['shape.radiusCard']==min(24,before+2),service.lastError
root.setProperty('optionIndex',5);press(window,Qt.Key_Right)
assert service.resolvedAppearance['tokens']['metrics.listRows']==3,service.lastError
assert service.resolvedAppearance['tokens']['metrics.compactRows']==2
root.setProperty('optionIndex',4);press(window,Qt.Key_Right)
assert service.resolvedAppearance['tokens']['typography.textScale']==1.05,service.lastError
press(window,Qt.Key_Escape);assert not service.editing
# Import/select a third data pack plus an installed presentation extension.
from theme_pack import import_pack
import_pack(Path(__file__).parent/'examples/themes/personal-sample',service.store)
assert service.reloadCatalog();service.beginEdit();service.selectDraft('personal.sample')
press(window,Qt.Key_1)  # Home cancels the draft by design; explicitly start its preview again.
service.beginEdit();assert service.selectDraft('personal.sample');wait_ready(app,root)
assert root.findChild(QObject,'homeNow').property('loadedPresentationId')=='example.home.summary'
assert service.resolvedAppearance['tokens']['ext.summary.clockInset']==24
service.cancel();wait_ready(app,root)
# GUI transfers use the same validator in a worker, without writing draft preferences.
import shutil
inbox=service.store.parent/'theme-imports'/'sample'
inbox.parent.mkdir(exist_ok=True)
shutil.copytree(Path(__file__).parent/'examples/themes/personal-sample',inbox)
payload=__import__('json').loads((inbox/'theme.json').read_text());payload['id']='personal.gui'
(inbox/'theme.json').write_text(__import__('json').dumps(payload))
assert service.transferPack('import')
assert not service.transferPack('export')
deadline=time.monotonic()+10
while service.status=='working' and time.monotonic()<deadline: wait(10)
assert 'personal.gui' in service.catalog.packs,service.lastError
assert service.transferPack('export')
while service.status=='working' and time.monotonic()<deadline: wait(10)
assert service.status=='ready',service.lastError
exports=list((service.store.parent/'theme-exports').glob('*/theme.json'))
assert exports,service.lastError
# Switch icon backend through data, retaining the same semantic id and consumer.
service.beginEdit();assert service.setSection('iconOverrides',{'weather.clear':{'backend':'glyph','glyph':'A','family':'DejaVu Sans'}})
assert service.setSection('iconOverrides',{'weather.clear':'clear'})
service.cancel()
# A new engine gets its own singleton/service and the QML-only facade fallback.
engine2,state2,root2,window2=create();assert state2.appearance is not service
assert QQmlExpression(engine2.rootContext(),root2,'style.appearance.revision').evaluate()[0]==state2.appearance.revision
state2.appearance.beginEdit();state2.appearance.selectDraft('base');wait_ready(app,root2)
assert service.activeThemeId==persisted.activeThemeId
fatal=list(messages)
assert not fatal,fatal
print('Theme QML: typed facade, two Home layouts, Qt focus, rapid swaps, persistent scene, draft/save/recovery and fresh engine PASS')
