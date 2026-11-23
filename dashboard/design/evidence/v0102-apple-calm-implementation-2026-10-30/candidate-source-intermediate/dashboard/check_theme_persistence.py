"""Fresh-process persistence, malformed settings recovery and real AccessError rollback."""
import os,subprocess,sys,tempfile
from pathlib import Path
root=Path(tempfile.mkdtemp(prefix='smartpc-persistence-'));dashboard=Path(__file__).parent
common="""
import time
from PySide6.QtCore import QSettings
from PySide6.QtGui import QGuiApplication
from theme_service import ThemeService
app=QGuiApplication([]);service=ThemeService()
def wait():
    end=time.monotonic()+5
    while service.status=='saving' and time.monotonic()<end:app.processEvents();time.sleep(.002)
    assert service.status!='saving'
"""
def run(code,configuration):
    env=dict(os.environ,XDG_CONFIG_HOME=str(configuration),SMARTPC_THEME_STORE=str(root/'themes'),QT_QPA_PLATFORM='offscreen')
    proc=subprocess.run([sys.executable,'-c',common+code],cwd=dashboard,env=env,capture_output=True,text=True,timeout=15)
    assert proc.returncode==0,(proc.stdout,proc.stderr)
configuration=root/'normal'
run("""
settings=QSettings('SmartPC','Dashboard');assert not settings.contains('appearance/config')
service.beginEdit();service.selectDraft('functional');service.cancel();assert not settings.contains('appearance/config')
service.beginEdit();service.selectDraft('functional');service.setSection('motionMode','off');assert service.apply();wait();assert service.status=='ready'
""",configuration)
run("assert service.activeThemeId=='functional' and service.resolvedAppearance['motionMode']=='off'",configuration)
for corrupted in ('"unexpected string"','{"schemaVersion":true}','not JSON'):
    run("QSettings('SmartPC','Dashboard').setValue('appearance/config',"+repr(corrupted)+");QSettings('SmartPC','Dashboard').sync()",configuration)
    run("assert service.activeThemeId=='base' and service.lastError",configuration)
readonly=root/'readonly';readonly.mkdir(mode=0o500)
try:
    run("""
service.beginEdit();service.setToken('shape.radiusCard',0);assert service.apply();wait()
assert service.status=='error' and service.lastError
assert service.resolvedAppearance['tokens']['shape.radiusCard']==13
assert service.draft['overrides']['tokens']['shape.radiusCard']==0
assert service.editing
assert ThemeService().resolvedAppearance['tokens']['shape.radiusCard']==13
""",readonly)
finally:readonly.chmod(0o700)
print('Settings: preview/cancel without write, fresh-process Apply, corrupted config and real read-only sync failure rollback PASS')
