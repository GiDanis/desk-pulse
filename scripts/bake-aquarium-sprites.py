#!/usr/bin/env python3
"""Bake the actual QML rig to sprite frames for an equivalent renderer A/B."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('QT_QUICK_BACKEND','software')
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dashboard'))
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication,QColor,QImage,QPainter
from PySide6.QtQuick import QQuickView
from aquarium_catalog import ROOT,load_catalog

app=QGuiApplication([])
catalog=load_catalog()
for species in catalog['species']:
    qml='''import QtQuick
import "'''+(ROOT.parents[2]/'presentations/aquarium').as_uri()+'''"
Item {
    required property var artSpecies
    property real pose:0
    width:384;height:256
    FishRig {anchors.centerIn:parent;width:250;height:160;species:parent.artSpecies;phase:parent.pose}
}
'''
    with tempfile.TemporaryDirectory(prefix='aquarium-bake-') as temp:
        path=Path(temp)/'Bake.qml';path.write_text(qml)
        view=QQuickView();view.setColor(QColor('transparent'));view.setInitialProperties({'artSpecies':species});view.setSource(QUrl.fromLocalFile(str(path)));view.show()
        if not view.rootObject():raise RuntimeError(view.errors())
        sheet=QImage(384*8,256*2,QImage.Format.Format_RGBA8888);sheet.fill(QColor('transparent'));painter=QPainter(sheet)
        for frame in range(16):
            view.rootObject().setProperty('pose',frame*2*3.141592653589793/16)
            end=time.monotonic()+(.25 if frame==0 else .04)
            while time.monotonic()<end:app.processEvents();time.sleep(.001)
            # Window grabs on the software backend can flatten alpha to black.
            # Render the Item into its own transparent image instead.
            grab=view.rootObject().grabToImage()
            end=time.monotonic()+5
            while grab.image().isNull() and time.monotonic()<end:app.processEvents();time.sleep(.001)
            pic=grab.image();assert not pic.isNull() and pic.pixelColor(0,0).alpha()==0
            painter.drawImage((frame%8)*384,(frame//8)*256,pic)
        painter.end();assert sheet.save(str(ROOT/(species['id']+'-swim.png')))
        view.close();view.deleteLater();app.processEvents()
        print(species['id'],sheet.width(),sheet.height())
manifest=ROOT/'catalog.json'
data=json.loads(manifest.read_text())
for name in data['files']:
    data['files'][name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
manifest.write_text(json.dumps(data,indent=2)+'\n')
