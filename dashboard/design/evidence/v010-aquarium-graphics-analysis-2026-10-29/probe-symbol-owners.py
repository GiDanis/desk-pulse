import ctypes as C,json
from PySide6 import QtGui
# Promote Qt dependencies for process-global lookup in this diagnostic child.
C.CDLL("libQt6Gui.so.6",mode=C.RTLD_GLOBAL)
class DlInfo(C.Structure):
 _fields_=[('dli_fname',C.c_char_p),('dli_fbase',C.c_void_p),('dli_sname',C.c_char_p),('dli_saddr',C.c_void_p)]
lib=C.CDLL(None);lib.dladdr.argtypes=[C.c_void_p,C.POINTER(DlInfo)];lib.dladdr.restype=C.c_int
def owner(ptr):
 d=DlInfo();lib.dladdr(ptr,C.byref(d));return d.dli_fname.decode() if d.dli_fname else None
E=C.CDLL('/usr/local/lib/libEGL.so.1');E.eglGetProcAddress.argtypes=[C.c_char_p];E.eglGetProcAddress.restype=C.c_void_p
V=C.CDLL('/usr/local/lib/libGLESv2.so.2')
a={}
for name in ['glGetString','glGetIntegerv','glBindTexture','glTexImage2D','glDrawElements','glClear']:
 direct=C.cast(getattr(lib,name),C.c_void_p).value
 vendor=C.cast(getattr(V,name),C.c_void_p).value
 ep=E.eglGetProcAddress(name.encode())
 a[name]={'processGlobalOwner':owner(direct),'vendorLibraryOwner':owner(vendor),'eglResolvedOwner':owner(ep),'globalMatchesVendor':direct==vendor,'globalMatchesEglResolver':direct==ep}
print(json.dumps({'scope':'Symbol resolution only: QtGui imported; no QGuiApplication, EGL initialization, context, window, DRM master or display change','qtModuleType':str(QtGui.QOpenGLContext.openGLModuleType()),'lookupScope':'QtGui dependencies promoted RTLD_GLOBAL in diagnostic child; binding logs reported separately','symbols':a}))
