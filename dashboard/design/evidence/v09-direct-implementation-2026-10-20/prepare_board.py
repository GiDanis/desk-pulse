from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-direct-proof';S=H/'smartpc-direct-project';R=H/'smartpc-direct-runtime'
for p in (P,S,R):p.mkdir(exist_ok=True)
for archive,root in (('/tmp/smartpc-direct-project.tar.gz',S),('/tmp/smartpc-direct-runtime.tar.gz',R)):
 with tarfile.open(archive) as tar:tar.extractall(root,filter='data')
shutil.copytree(H/'smartpc-learning-project/theme-projects',S/'theme-projects',dirs_exist_ok=True)
lib=Path('/opt/smartpc/dashboard/libsmartpc_game_native.so')
for root in (S/'dashboard',R/'dashboard'):
 m=json.loads((root/'release-manifest.json').read_text());assert m['version']=='0.9.0-rc.25'
 assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in m['sha256'].items())
 shutil.copy2(lib,root/lib.name);m['sha256'][lib.name]=hashlib.sha256(lib.read_bytes()).hexdigest()
 (root/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
subprocess.run(['chown','-R','smartpc:smartpc',str(P),str(S),str(R)],check=True)
print('Prepared exact rc.25 ARM packages',flush=True)
