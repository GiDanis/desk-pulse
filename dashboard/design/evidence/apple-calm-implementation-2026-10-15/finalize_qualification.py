"""Wait for the ongoing soak, qualify the final payload delta, then assess results.

This prepares reviewable evidence only. Installation is a separate transaction.
"""
import json
from pathlib import Path
import subprocess
import sys
import time

E=Path('/tmp/smartpc-apple-final-proof');W=Path('/tmp/smartpc-apple-candidate')
release=Path('/tmp/smartpc-apple-release');PY=Path('/var/lib/smartpc-dashboard/game-runtime/bin/python')
deadline=time.monotonic()+2400
while not (E/'native-receipt.json').exists():
    assert time.monotonic()<deadline,'Native qualification did not finish'
    time.sleep(2)
assert json.loads((E/'native-receipt.json').read_text())['status']=='passed'
print('PASS final core soak; START final payload matrix',flush=True)
with (release/'preview.txt').open('w') as out:
    subprocess.run(['runuser','-u','smartpc','--','env','HOME=/var/lib/smartpc-dashboard',
        'QT_QPA_PLATFORM=offscreen','nice','-n','10',str(PY),str(W/'dashboard/theme_bundle_preview.py'),
        str(release/'bundle'),'--matrix','--output',str(release/'preview')],
        stdout=out,stderr=subprocess.STDOUT,check=True,timeout=720)
r=json.loads((release/'preview/preview-report.json').read_text())
assert r['status']=='passed' and not r['qmlWarnings']
sys.path.insert(0,str(W/'dashboard'))
from theme_bundle import validate_project
v=validate_project(release/'bundle',app_root=W/'dashboard')
cache={'digest':v['digest'],'result':{'status':'passed','qt':r['qt'],'backend':r['backend'],
       'scope':'isolatedPublicRenderers','renderers':len(r['renderers']),'boardEglfs':'notVerified'}}
(release/'cache.json').write_text(json.dumps(cache,indent=2)+'\n')
print('PASS final payload matrix; START native delta supplement',flush=True)
subprocess.run([sys.executable,'/tmp/release_supplement.py'],check=True)
print('PASS native delta supplement; START assessment',flush=True)
subprocess.run([sys.executable,'/tmp/summarize_final.py',str(E)],check=True)
print('QUALIFIED_READY_TO_INSTALL',flush=True)
