"""Stage immutable ARM candidates; production remains running and untouched."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,tarfile
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-attack-proof';S=H/'smartpc-attack-project';R=H/'smartpc-attack-runtime'
for path in (P,S,R,P/'private',P/'private/test-home'):path.mkdir(exist_ok=True)
for archive,root in (('/tmp/smartpc-attack-project.tar.gz',S),('/tmp/smartpc-attack-runtime.tar.gz',R)):
 with tarfile.open(archive) as tar:tar.extractall(root,filter='data')
for root in (S/'dashboard',R/'dashboard'):
 m=json.loads((root/'release-manifest.json').read_text());assert m['version']=='0.9.3-rc.2'
 assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
 native=Path('/opt/smartpc/dashboard/libsmartpc_game_native.so');shutil.copy2(native,root/native.name)
 m['sha256'][native.name]=hashlib.sha256(native.read_bytes()).hexdigest()
 (root/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
source=H/'smartpc-menu-project/theme-projects';link=S/'theme-projects'
if not link.exists():link.symlink_to(source,target_is_directory=True)
with tarfile.open('/tmp/smartpc-attack-fixtures.tar.gz') as tar:tar.extractall(P/'private/saved',filter='data')
subprocess.run(['chown','-R','smartpc:smartpc',str(P),str(S),str(R)],check=True);(P/'private').chmod(0o700)
print('ARM candidate staged, production untouched',flush=True)
