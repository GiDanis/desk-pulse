"""Semantic icon backends and independent typed preview using real QML/PNG/TTF."""
import os,tempfile,json
from pathlib import Path
os.environ['XDG_CONFIG_HOME']=tempfile.mkdtemp(prefix='smartpc-icons-config-')
os.environ['SMARTPC_THEME_STORE']=tempfile.mkdtemp(prefix='smartpc-icons-store-')
os.environ.setdefault('QT_QPA_PLATFORM','offscreen');os.environ.setdefault('QT_QUICK_BACKEND','software')
from PySide6.QtCore import QObject,QUrl,QEventLoop,QTimer
from PySide6.QtGui import QGuiApplication,QImage,QColor
from PySide6.QtQml import QQmlApplicationEngine,QQmlExpression
from theme_core import ThemeCatalog
from theme_service import ThemeService
from theme_pack import import_pack

app=QGuiApplication([]);source=Path(tempfile.mkdtemp(prefix='smartpc-icon-image-'))
image=QImage(32,32,QImage.Format.Format_ARGB32);image.fill(QColor('#6de0be'));assert image.save(str(source/'icon.png'))
pack={'schemaVersion':1,'id':'image.proof','name':'Image proof','version':'1.0.0','extends':'base','assets':[{'id':'icon','type':'image','path':'icon.png'}],
      'iconOverrides':{'weather.clear':{'backend':'image','asset':'icon'}}}
(source/'theme.json').write_text(json.dumps(pack));import_pack(source,Path(os.environ['SMARTPC_THEME_STORE']))
service=ThemeService();service.beginEdit();assert service.selectDraft('image.proof')
a=service.resolvedAppearance;b=service.catalog.resolve('base',{'iconOverrides':{'weather.clear':{'backend':'glyph','glyph':'A','family':'DejaVu Sans'}}})
engine=QQmlApplicationEngine();warnings=[];engine.warnings.connect(lambda errors:warnings.extend(str(e) for e in errors))
engine.rootContext().setContextProperty('previewA',a);engine.rootContext().setContextProperty('previewB',b)
qml='''import QtQuick
import "themes"
import "components"
import "components/IconIds.js" as IconIds
Window {
    width: 180; height: 120; visible: true
    StyleFacade { id: styleA; appearance: previewA }
    StyleFacade { id: styleB; appearance: previewB }
    AppIcon { objectName: "imageIcon"; style: styleA; iconId: "weather.clear"; x: 10; y: 10 }
    AppIcon { objectName: "glyphIcon"; style: styleB; iconId: "weather.clear"; x: 60; y: 10 }
    AppIcon { objectName: "fallbackIcon"; style: styleA; iconId: "unknown.request"; x: 110; y: 10 }
    function weatherId(code) { return IconIds.weather(code) }
}
'''
engine.loadData(qml.encode(),QUrl.fromLocalFile(str(Path(__file__).with_name('IconVerification.qml'))));assert engine.rootObjects(),warnings
root=engine.rootObjects()[0];loop=QEventLoop();QTimer.singleShot(250,loop.quit);loop.exec()
assert root.findChild(QObject,'imageIcon').property('backend')=='image'
assert root.findChild(QObject,'glyphIcon').property('backend')=='glyph'
assert root.findChild(QObject,'fallbackIcon').property('symbol')=='unknown'
for code,expected in [(-1,'unknown'),(999,'unknown'),(72,'unknown'),(0,'clear'),(3,'cloudy'),(45,'fog'),(61,'rain'),(71,'snow'),(95,'storm')]:
 expression=QQmlExpression(engine.rootContext(),root,'weatherId('+str(code)+')');assert expression.evaluate()[0]=='weather.'+expected
assert not warnings,warnings
print('Icons: same semantic id via geometry/TTF/real PNG, isolated preview, unknown fallback and structured weather codes PASS')
