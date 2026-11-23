"""Qt Quick 3D registration, lazy and optional. Meshes are built offline."""
from functools import lru_cache
from pathlib import Path
import struct

_REGISTERED = False
_SURFACE_CONFIGURED = False
ROOT = Path(__file__).parent/'assets/aquarium/calm-3d-v1'


def available():
    import os
    if os.environ.get('QT_QUICK_BACKEND') == 'software' or os.environ.get('SMARTPC_AQUARIUM_RENDERER')=='2d':
        return False
    try:
        from PySide6.QtQuick3D import QQuick3DGeometry
    except ImportError:
        return False
    return True


@lru_cache(maxsize=8)
def read_mesh(path):
    raw=Path(path).read_bytes()
    if raw[:8]!=b'FISHMESH':raise ValueError('Mesh Acquario non valida')
    count,indices=struct.unpack_from('<II',raw,8)
    if not 1<=count<=100000 or not 3<=indices<=600000 or indices%3 or len(raw)!=16+count*72+indices*4:
        raise ValueError('Dimensioni mesh Acquario non valide')
    data=raw[16:16+count*72];idx=raw[16+count*72:]
    values=list(struct.iter_unpack('<10f4i4f',data))
    import math
    if any(not math.isfinite(x) for v in values for x in v):raise ValueError('Vertice non finito')
    if any(any(j not in (0,1,2) for j in v[10:14]) or any(w<0 for w in v[14:18]) or abs(sum(v[14:18])-1)>.001 for v in values):raise ValueError('Pesi o ossa non validi')
    if any(x>=count for x, in struct.iter_unpack('<I',idx)):raise ValueError('Indice non valido')
    return data,idx,tuple(min(v[k] for v in values) for k in range(3)),tuple(max(v[k] for v in values) for k in range(3))


def configure_surface():
    """Called by service construction, after QGuiApplication and before any window.

    Qt Quick's default ES2 context cannot run the skinned shader path. Let Qt
    select a capable context; retain zero samples for the measured kiosk profile.
    """
    global _SURFACE_CONFIGURED
    if _SURFACE_CONFIGURED:return
    from PySide6.QtGui import QGuiApplication,QSurfaceFormat
    if not isinstance(QGuiApplication.instance(),QGuiApplication):return
    import os
    # Diagnostic override separates context selection from geometry registration.
    # The default remains explicit GLES on EGLFS; other backends keep Qt's helper.
    if os.environ.get('SMARTPC_AQUARIUM_SURFACE') == 'baseline':
        _SURFACE_CONFIGURED=True
        return
    if os.environ.get('QT_QPA_PLATFORM')=='eglfs':
        surface=QSurfaceFormat()
        surface.setRenderableType(QSurfaceFormat.OpenGLES)
        surface.setVersion(3,0);surface.setDepthBufferSize(24);surface.setStencilBufferSize(8);surface.setSamples(0)
    else:
        from PySide6.QtQuick3D import QQuick3D
        surface=QQuick3D.idealSurfaceFormat(0)
    QSurfaceFormat.setDefaultFormat(surface)
    _SURFACE_CONFIGURED=True


def register():
    global _REGISTERED
    if not available():return False
    configure_surface()
    if _REGISTERED:return True
    from PySide6.QtCore import QByteArray,Property,Signal,QUrl
    from PySide6.QtGui import QVector3D
    from PySide6.QtQml import qmlRegisterType
    from PySide6.QtQuick3D import QQuick3DGeometry
    class FishMesh(QQuick3DGeometry):
        changed=Signal()
        def __init__(self,parent=None):
            super().__init__(parent);self._source='';self._valid=False
        @Property(bool,notify=changed)
        def valid(self):return self._valid
        @Property(str,notify=changed)
        def source(self):return self._source
        @source.setter
        def source(self,value):
            if value==self._source:return
            self._source=value;self._valid=False;self.clear()
            path=Path(QUrl(value).toLocalFile()).resolve()
            if path.is_relative_to(ROOT.resolve()) and path.suffix=='.fishmesh' and path.is_file():
                try:
                    data,idx,low,high=read_mesh(str(path))
                    self.setStride(72);self.setVertexData(QByteArray(data));self.setIndexData(QByteArray(idx))
                    A=QQuick3DGeometry.Attribute
                    for semantic,offset,kind in [(A.PositionSemantic,0,A.F32Type),(A.NormalSemantic,12,A.F32Type),(A.ColorSemantic,24,A.F32Type),(A.JointSemantic,40,A.I32Type),(A.WeightSemantic,56,A.F32Type),(A.IndexSemantic,0,A.U32Type)]:self.addAttribute(semantic,offset,kind)
                    self.setPrimitiveType(QQuick3DGeometry.PrimitiveType.Triangles);self.setBounds(QVector3D(*low),QVector3D(*high));self.update();self._valid=True
                except (ValueError,OSError,struct.error):pass
            self.changed.emit()
    # Keep the class alive for the lifetime of the QML registration.
    globals()['FishMesh']=FishMesh
    qmlRegisterType(FishMesh,'SmartPC.Aquarium',1,0,'FishMesh')
    _REGISTERED=True
    return True
