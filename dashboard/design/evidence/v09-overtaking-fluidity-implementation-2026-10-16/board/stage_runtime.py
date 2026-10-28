"""Validate ARM source subset before switching the installed runtime."""
from pathlib import Path
import hashlib,json,shutil,platform
H=Path('/var/lib/smartpc-dashboard');R=H/'smartpc-overtake-runtime';D=H/'smartpc-overtake-project/dashboard';P=H/'v09-overtake-proof'
m=json.loads((R/'release-manifest.json').read_text());d=json.loads((D/'release-manifest.json').read_text())
assert m['version']=='0.9.0-rc.22' and m['distributionKind']=='runtime' and len(m['sha256'])==624
assert all(hashlib.sha256((R/n).read_bytes()).hexdigest()==v for n,v in m['sha256'].items())
lib='libsmartpc_game_native.so';assert hashlib.sha256((D/lib).read_bytes()).hexdigest()==d['sha256'][lib]
shutil.copy2(D/lib,R/lib);m['sha256'][lib]=d['sha256'][lib]
assert all(v==d['sha256'].get(n) for n,v in m['sha256'].items()),'Runtime differs from diagnostic source'
(R/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
assert all(hashlib.sha256((R/n).read_bytes()).hexdigest()==v for n,v in m['sha256'].items())
installed=json.loads(Path('/opt/smartpc/dashboard/release-manifest.json').read_text())
changes=dict(added=sorted(m['sha256'].keys()-installed['sha256'].keys()),removed=sorted(installed['sha256'].keys()-m['sha256'].keys()),changed=sorted(n for n,v in m['sha256'].items() if n in installed['sha256'] and installed['sha256'][n]!=v))
receipt=dict(status='passed',version=m['version'],files=len(m['sha256']),architecture=platform.machine(),runtimeSourceSubsetMatchesDiagnostic=True,manifestSha256=hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest(),nativeLibrarySha256=m['sha256'][lib],changesFromInstalled=changes)
(P/'stage-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
