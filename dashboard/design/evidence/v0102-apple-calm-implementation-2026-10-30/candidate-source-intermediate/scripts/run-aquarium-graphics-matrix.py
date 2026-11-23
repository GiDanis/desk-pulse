#!/usr/bin/env python3
"""Board-only bounded matrix; invoke as a transient systemd service with recovery."""
from pathlib import Path
import json
import os
import pwd
import subprocess
import time

W = Path(__file__).resolve().parent
assert W == Path('/var/lib/smartpc-dashboard/maintenance-work/graphics-fix')
assert os.geteuid() == 0
assert os.environ.get('INVOCATION_ID'), 'Use a bounded transient systemd service with ExecStopPost recovery'
assert 'SMARTPC_AQUARIUM_RENDERER=2d' in Path('/etc/systemd/system/smartpc-dashboard.service.d/90-aquarium-graphics-recovery.conf').read_text()
identity = pwd.getpwnam('smartpc')
PYTHON = '/var/lib/smartpc-dashboard/game-runtime/bin/python'
SERVICE = 'smartpc-dashboard.service'
subprocess.run(['cc', '-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror', '-o', str(W/'gl-probe.so'), str(W/'aquarium_gl_probe.c'), '-ldl', '-pthread'], check=True)
scene = os.environ.get('SMARTPC_MATRIX_SCENE', 'pattern')
selected = os.environ.get('SMARTPC_MATRIX_CASES', 'ABCD')
assert scene in ('pattern', 'cube') and selected and set(selected) <= set('ABCDE')
if 'E' in selected:
    assert (W/'libsmartpc_egl_context_bridge.so').is_file(), 'Build the candidate bridge before stopping the dashboard'
(W/('matrix-'+scene)).mkdir(parents=True, exist_ok=True)
result = {}
try:
    subprocess.run(['systemctl', 'stop', SERVICE], check=True, timeout=20)
    cases = [('A','baseline','none'),('B','es3','none'),('C','baseline','vendor'),('D','es3','vendor'),('E','es3','bridge')]
    for label, surface, preload in cases:
        if label not in selected:
            continue
        out = W / ('matrix-' + scene) / label
        out.mkdir(parents=True, exist_ok=True)
        os.chown(out.parent, identity.pw_uid, identity.pw_gid)
        os.chown(out, identity.pw_uid, identity.pw_gid)
        private = out / 'home'
        private.mkdir(exist_ok=True)
        os.chown(private, identity.pw_uid, identity.pw_gid)
        env = {'HOME':str(private), 'QT_QPA_PLATFORM':'eglfs', 'QT_QPA_EGLFS_INTEGRATION':'eglfs_kms',
               'QT_QPA_EGLFS_KMS_CONFIG':'/etc/smartpc/eglfs-kms.json', 'QT_QPA_EGLFS_HIDECURSOR':'1',
               'QSG_RHI_BACKEND':'opengl', 'QT_QPA_EGLFS_DEBUG':'1', 'QSG_INFO':'1',
               'SMARTPC_GL_PROBE_FILE':str(out/'native-context.json'),
               'LD_PRELOAD':str(W/'gl-probe.so') + ({'vendor':':/usr/local/lib/libGLESv2.so.2','bridge':':'+str(W/'libsmartpc_egl_context_bridge.so')}.get(preload,''))}
        command = ['runuser','-u','smartpc','--','env', *[k+'='+v for k,v in env.items()], PYTHON,
                   str(W/'probe-aquarium-graphics.py'), '--output',str(out),'--surface',surface,
                   '--seconds','8','--label',label,'--scene',scene]
        print('CASE', label, scene, surface, preload, flush=True)
        with (out/'qt.log').open('w') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            try:
                time.sleep(4)
                if process.poll() is None:
                    capture = subprocess.run(['python3',str(W/'capture-drm-scanout.py'),'--output',str(out)],capture_output=True,text=True,timeout=5)
                    (out/'capture.log').write_text(capture.stdout+capture.stderr)
                code = process.wait(timeout=18)
            except BaseException:
                process.terminate()
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=3)
                raise
        native = out/'native-context.json'
        result[label] = {'returncode':code, 'nativeContext':json.loads(native.read_text()) if native.exists() else None,
                         'surface':surface,'preload':preload}
        print(json.dumps(result[label]),flush=True)
finally:
    try:
        (W/('matrix-'+scene)/'matrix.json').write_text(json.dumps(result,indent=2)+'\n')
    finally:
        subprocess.run(['systemctl','start',SERVICE],check=True,timeout=35)
    print('RECOVERY_SERVICE_STARTED',flush=True)
