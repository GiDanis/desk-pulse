from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-menu-proof';S=H/'smartpc-menu-project';R=H/'smartpc-menu-runtime'
for p in (P,S,R,P/'private'):p.mkdir(exist_ok=True)
for archive,root in (('/tmp/smartpc-menu-project.tar.gz',S),('/tmp/smartpc-menu-runtime.tar.gz',R)):
    with tarfile.open(archive) as tar:tar.extractall(root,filter='data')
for root in (S/'dashboard',R/'dashboard'):
    m=json.loads((root/'release-manifest.json').read_text());assert m['version']=='0.9.0-rc.28'
    assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==h for n,h in m['sha256'].items())
    lib=Path('/opt/smartpc/dashboard/libsmartpc_game_native.so');shutil.copy2(lib,root/lib.name)
    m['sha256'][lib.name]=hashlib.sha256(lib.read_bytes()).hexdigest()
    (root/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
with tarfile.open('/tmp/smartpc-menu-saved.tar.gz') as tar:tar.extractall(P/'private/saved',filter='data')
subprocess.run(['chown','-R','smartpc:smartpc',str(P),str(S),str(R)],check=True)
(P/'private').chmod(0o700)
print('Prepared rc.28 ARM runtime and private fixtures',flush=True)
