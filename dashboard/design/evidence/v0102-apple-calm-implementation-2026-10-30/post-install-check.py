"""Read-only installed graphics profile plus the actual DRM scanout capture."""
from pathlib import Path
import hashlib,json,os,pwd,subprocess,time
W=Path(__file__).resolve().parent;H=Path('/var/lib/smartpc-dashboard');D=H/'.local/share/SmartPC/SmartPC';R=Path('/opt/smartpc/dashboard')
assert os.getuid()==0
installed=json.loads((W/'installation.json').read_text());pid=installed['guiPid']
raw=(Path('/proc')/str(pid)/'environ').read_bytes()
env=dict(part.decode().split('=',1) for part in raw.split(b'\0') if b'=' in part)
keys=['QT_QPA_PLATFORM','QT_QPA_EGLFS_INTEGRATION','QT_QPA_EGLFS_KMS_CONFIG','QT_QPA_EGLFS_HIDECURSOR','QSG_RHI_BACKEND','QT_DISABLE_SHADER_DISK_CACHE','LD_PRELOAD','SMARTPC_AQUARIUM_RENDERER','QT_QUICK_BACKEND','QSG_RHI_PIPELINE_CACHE_LOAD','QSG_RHI_PIPELINE_CACHE_SAVE']
profile={k:env.get(k) for k in keys}
assert profile['QT_QPA_PLATFORM']=='eglfs' and profile['QSG_RHI_BACKEND']=='opengl'
assert profile['QT_QPA_EGLFS_INTEGRATION']=='eglfs_kms' and profile['QT_DISABLE_SHADER_DISK_CACHE']=='1'
assert profile['LD_PRELOAD']==str(R/'libsmartpc_egl_context_bridge.so')
assert profile['SMARTPC_AQUARIUM_RENDERER'] in (None,'3d')  # Unset selects the installed 3D-capable default.
capability=subprocess.check_output(['sudo','-n','-u','smartpc','env','PYTHONPATH='+str(R),str(H/'game-runtime/bin/python'),'-c','from aquarium_geometry import available;assert available();print("3D available")'],text=True).strip()
assert all(not profile[k] for k in ['QT_QUICK_BACKEND','QSG_RHI_PIPELINE_CACHE_LOAD','QSG_RHI_PIPELINE_CACHE_SAVE'])
code='''from pathlib import Path
import json,sys
sys.path.insert(0,"/opt/smartpc/dashboard")
from theme_bundle import BundleManager
d=Path("/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC");identity=json.loads((d/"theme-activation.json").read_text())["active"]
r=BundleManager(d,app_root=Path("/opt/smartpc/dashboard")).verify_revision(identity)
print(json.dumps({"identity":identity,"files":len(r["files"]),"preflight":r["preflight"]}))
'''
bundle=json.loads(subprocess.check_output(['sudo','-n','-u','smartpc',str(H/'game-runtime/bin/python'),'-c',code],text=True))
assert bundle['identity']==installed['theme']
subprocess.run([str(H/'game-runtime/bin/python'),str(W/'capture-drm-scanout.py'),'--output',str(W/'scanout')],check=True)
manifest=json.loads((R/'release-manifest.json').read_text());baseline=json.loads((W/'candidate-source/dashboard/release-manifest.json').read_text())
assert manifest['sha256']==baseline['sha256']
native={k:hashlib.sha256((R/k).read_bytes()).hexdigest() for k in manifest['sha256'] if k.endswith('.so')}
report={'status':'passed','guiPid':pid,'profile':profile,'aquariumDefaultCapability':capability,'installedBundle':bundle,'nativeLibrarySha256':native,'scanout':'actual installed service DRM memory; not optical or physical-panel verification','rebootPerformed':False}
(W/'post-install-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
