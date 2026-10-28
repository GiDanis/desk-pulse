from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-racing-objective-proof';S=H/'smartpc-racing-final-project';R=H/'smartpc-racing-final-runtime'
for p in (P,S,R):p.mkdir(exist_ok=True)
for archive,root in (('/tmp/smartpc-racing-final-project.tar.gz',S),('/tmp/smartpc-racing-final-runtime.tar.gz',R)):
 with tarfile.open(archive) as tar:tar.extractall(root,filter='data')
assert (S/'theme-projects/apple-calm/bundle/theme.json').exists()
lib=Path('/opt/smartpc/dashboard/libsmartpc_game_native.so')
for root in (S/'dashboard',R/'dashboard'):
 m=json.loads((root/'release-manifest.json').read_text());assert m['version']=='0.9.0-rc.27'
 assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in m['sha256'].items())
 shutil.copy2(lib,root/lib.name);m['sha256'][lib.name]=hashlib.sha256(lib.read_bytes()).hexdigest()
 (root/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
with tarfile.open('/tmp/smartpc-racing-originals.tar.gz') as tar:tar.extractall(P/'saved-originals',filter='data')
subprocess.run(['chown','-R','smartpc:smartpc',str(P),str(S),str(R)],check=True)
print('Prepared exact rc.27 ARM packages',flush=True)
