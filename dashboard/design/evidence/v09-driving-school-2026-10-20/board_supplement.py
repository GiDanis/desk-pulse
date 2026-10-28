"""Qualify only the final changed retention module; EGLFS sources unchanged."""
from pathlib import Path
import json,hashlib,subprocess,sys
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-school-proof';S=H/'smartpc-school-project/dashboard';R=H/'smartpc-school-runtime/dashboard';PY=H/'game-runtime/bin/python'
old=json.loads((P/'native-source-checks.json').read_text());m=json.loads((S/'release-manifest.json').read_text())
delta=[n for n,h in m['sha256'].items() if old['sourceHashes'].get(n)!=h]
assert set(delta)=={'game_school_lessons.py','check_game_school.py','game_store.py'},delta
assert all(hashlib.sha256((S/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
env=['HOME='+str(H),'XDG_CONFIG_HOME='+str(H/'.config'),'XDG_DATA_HOME='+str(H/'.local/share'),'XDG_CACHE_HOME=/var/cache/smartpc-dashboard','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','QT_QPA_PLATFORM=offscreen','PYTHONPATH='+str(S)]
with (P/'arm-final-school.txt').open('w') as out:
 subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),'-m','unittest','check_game_school','-v'],cwd=S,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=300)
with (P/'arm-frozen-retention.txt').open('w') as out:
 subprocess.run(['runuser','-u','smartpc','--','env',*env,str(PY),str(P/'prove_grid.py')],cwd=S,stdout=out,stderr=subprocess.STDOUT,check=True,timeout=600)
proof=json.loads((P/'arm-frozen-retention.json').read_text());assert proof['status']=='passed'
(P/'source-checks.json').write_text(json.dumps(dict(status='passed',sourceHashes=m['sha256'],nativeCases=['base','functional','apple'],nativeSourceReceipt='native-source-checks.json',supplementalDelta=delta,supplement='arm-frozen-retention.json',scope='Same QML, actor, learning updates and preview. Final grid-retention proof, snapshot/contact tests and continuous-mode profile migration separately verified on ARM; native harness never reached promotion before 4000 collected steps.'),indent=2)+'\n')
print('Final retention source supplement passed',flush=True)
