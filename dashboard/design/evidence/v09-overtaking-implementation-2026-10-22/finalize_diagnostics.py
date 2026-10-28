"""Qualify the diagnostic-only legacy-resume correction after native walkthrough."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile,unittest,time,sys
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-attack-proof';S=H/'smartpc-attack-project/dashboard';R=H/'smartpc-attack-runtime/dashboard'
assert (P/'source-checks.json').exists() and (P/'original-preservation.json').exists()
assert subprocess.check_output(['systemctl','is-active','smartpc-dashboard'],text=True).strip()=='active'
shutil.copy2(P/'source-checks.json',P/'source-checks-before-counter-fix.json')
for root in (S,R):
 m=json.loads((root/'release-manifest.json').read_text())
 with tarfile.open('/tmp/smartpc-attack-counter-fix.tar.gz') as t:
  assert {x.name for x in t.getmembers()}=={'game_overtaking.py','check_game_attack.py'}
  t.extractall(root,filter='data')
 for name in ('game_overtaking.py','check_game_attack.py'):m['sha256'][name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
 (root/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
sys.path.insert(0,str(S));start=time.monotonic()
with (P/'diagnostic-counter-tests.txt').open('w') as out:
 result=unittest.TextTestRunner(stream=out,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('check_game_attack'))
assert result.wasSuccessful() and result.testsRun==10
proof=dict(status='passed',tests=result.testsRun,seconds=time.monotonic()-start,scope='No numerical controls or rewards changed. Legacy episode diagnostic starts at current age; all ten attack tests rerun on ARM.',productionChanges=False)
(P/'diagnostic-counter-checks.json').write_text(json.dumps(proof,indent=2)+'\n')
checks=json.loads((P/'source-checks.json').read_text());checks['sourceHashes']=json.loads((S/'release-manifest.json').read_text())['sha256'];checks['postNativeDiagnosticCorrection']=proof
(P/'source-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(proof),flush=True)
