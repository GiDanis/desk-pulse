"""Cold legacy preferences with only F1 visible; fresh Main, existing offline seeds."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from theme_fixture_support import isolate_process,LegacyHarness
private,base=isolate_process()
h=None
try:
 from PySide6.QtCore import QSettings,QUrl
 from PySide6.QtQml import QQmlApplicationEngine,QQmlExpression,QQmlEngine
 from state import DashboardState
 from theme_test_support import configure_appearance,wait_ready,as_value
 h=LegacyHarness(base,{'theme':'base','variant':'day','motion':'off'})
 settings=QSettings('SmartPC','Dashboard');settings.remove('navigation')
 for key,value in [('sport',False),('f1',True),('motogp',False)]:settings.setValue('moduleVisible/'+key,value)
 settings.sync()
 state=DashboardState(h.weather,h.system,h.account,h.events,sport=h.sport,racing=h.racing)
 state.markCommandsSeen();configure_appearance(state)
 engine=QQmlApplicationEngine();engine.setInitialProperties({'dashboardState':state})
 engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[3]/'Main.qml')))
 root=engine.rootObjects()[0];wait_ready(h.app,root)
 def expression(code):
  expr=QQmlExpression(QQmlEngine.contextForObject(root),root,code);result=expr.evaluate();assert not expr.hasError(),expr.error().toString();return as_value(result[0])
 assert state.sportGroupVisible and expression('sportDisciplines.map(row=>row.id)')==['f1']
 for key in [1,6,6,6,5]:expression('activateKey('+str(key)+')');wait_ready(h.app,root);h.pump(20)
 assert root.property('familyId')=='f1'
 assert not h.messages,h.messages
 assert state.moduleVisibility['sport'] is False and state.moduleVisibility['motogp'] is False
 print(json.dumps({'status':'passed','coldLegacyOnlyF1':True,'freshMainKeypad':True,'hiddenDisciplinesPreserved':True,'qmlWarnings':h.messages}))
 engine.deleteLater();h.pump(10)
finally:
 if h:h.close()
 private.cleanup()
