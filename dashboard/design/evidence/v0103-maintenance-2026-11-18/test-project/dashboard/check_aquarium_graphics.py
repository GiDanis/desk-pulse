"""Native dispatch regression: EGL queries, no-context fallback and thread isolation."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from aquarium_graphics_diagnostics import parse_qt_messages,read_native_context,scanout_content

class NativeDiagnosticsChecks(unittest.TestCase):
    def test_uniform_frame_cannot_pass_as_visible_content(self):
        metadata={'format':'XR24','width':16,'height':16,'pitch':64}
        with self.assertRaises(ValueError):scanout_content(bytes([244,242,241,0])*256,metadata)
        gradient=b''.join(bytes([x,y,0,0]) for y in range(16) for x in range(16))
        self.assertEqual(256,scanout_content(gradient,metadata)['uniqueColors'])
        with self.assertRaises(ValueError):scanout_content(gradient[:-1],metadata)

    def test_qt_capability_mismatch_cannot_pass(self):
        context = {'pid':42,'vendor':'test','renderer':'test','version':'OpenGL ES 3.2 test',
                   'glsl':'3.20','eglConfig':{'id':16}}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'context.json';path.write_text(json.dumps(context))
            log='SMARTPC-QT|debug|qt.rhi.general|Created OpenGL context QSurfaceFormat(version 2.0, options ...)\n'
            with self.assertRaises(ValueError):read_native_context(path,42,parse_qt_messages(log))
            messages=parse_qt_messages(log.replace('version 2.0','version 3.2'))
            self.assertEqual([3,2],read_native_context(path,42,messages)['qtRhiVersion'])
            with self.assertRaises(ValueError):read_native_context(path,43,messages)
            with self.assertRaises(ValueError):read_native_context(path,42,[])
            with self.assertRaises(ValueError):read_native_context(None,42,messages)
            context['renderer']='llvmpipe';path.write_text(json.dumps(context))
            with self.assertRaises(ValueError):read_native_context(path,42,messages)

    def test_warning_severity_and_multiline_diagnostics_are_preserved(self):
        messages=parse_qt_messages('SMARTPC-QT|debug|qt.rhi.general|detail\nmore detail\nSMARTPC-QT|warning|default|shader failed\n')
        self.assertEqual('detail\nmore detail',messages[0]['message'])
        self.assertEqual('warning',messages[1]['severity'])
        self.assertEqual('shader failed',messages[1]['message'])

@unittest.skipUnless(shutil.which('cc') and shutil.which('nm'), 'native C toolchain unavailable')
class EGLBridgeChecks(unittest.TestCase):
    def test_current_egl_context_and_fallback_are_thread_local(self):
        with tempfile.TemporaryDirectory(prefix='smartpc-egl-bridge-') as directory:
            d = Path(directory)
            egl = '''#include <string.h>
static _Thread_local int active;
void fakeSetCurrent(int value) { active=value; }
void *eglGetCurrentContext(void) { return active ? (void *)1 : 0; }
static const unsigned char *query(unsigned int n) {(void)n;return (const unsigned char *)"EGL synthetic 3.2";}
static void integer(unsigned int n,int *v) {(void)n;*v=1234;}
void *eglGetProcAddress(const char *n) {if(!strcmp(n,"glGetString"))return query;if(!strcmp(n,"glGetIntegerv"))return integer;return 0;}
'''
            fallback = '''const unsigned char *glGetString(unsigned int n) {(void)n;return (const unsigned char *)"fallback";}
void glGetIntegerv(unsigned int n,int *v) {(void)n;*v=77;}
'''
            for name, source in [('EGL',egl),('fallback',fallback)]:
                (d/(name+'.c')).write_text(source)
                subprocess.run(['cc','-shared','-fPIC','-o',str(d/('lib'+name+'.so.1')),str(d/(name+'.c'))],check=True,capture_output=True)
            build = subprocess.run([sys.executable,str(ROOT/'scripts/build-egl-context-bridge.py'),
                                    '--source',str(ROOT/'dashboard/egl_context_bridge.c'),
                                    '--output',str(d/'bridge.so')],check=True,text=True,capture_output=True)
            self.assertEqual(['glGetIntegerv','glGetString'],json.loads(build.stdout)['exports'])
            script = '''import ctypes as C,threading,json
egl=C.CDLL("libEGL.so.1",mode=C.RTLD_GLOBAL)
q=C.CDLL(None);q.glGetString.argtypes=[C.c_uint];q.glGetString.restype=C.c_char_p
q.glGetIntegerv.argtypes=[C.c_uint,C.POINTER(C.c_int)]
def read():
 v=C.c_int(-1);q.glGetIntegerv(1,C.byref(v));return [q.glGetString(1).decode(),v.value]
egl.fakeSetCurrent(1)
assert read()==["EGL synthetic 3.2",1234]
other=[]
t=threading.Thread(target=lambda:other.append(read()));t.start();t.join()
assert other==[["fallback",77]]
assert read()==["EGL synthetic 3.2",1234]
egl.fakeSetCurrent(0)
assert read()==["fallback",77]
print("native context query routing and fallback passed")
'''
            env = os.environ.copy()
            env['LD_PRELOAD'] = str(d/'bridge.so')+':'+str(d/'libfallback.so.1')
            env['LD_LIBRARY_PATH'] = str(d)
            result = subprocess.run([sys.executable,'-c',script],env=env,capture_output=True,text=True,timeout=10)
            self.assertEqual(0,result.returncode,result.stderr)

if __name__ == '__main__':
    unittest.main()
