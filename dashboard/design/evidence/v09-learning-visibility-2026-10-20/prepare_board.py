from pathlib import Path
import hashlib,json,shutil,sqlite3,subprocess,tarfile
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-learning-proof';S=H/'smartpc-learning-project';R=H/'smartpc-learning-runtime';G=H/'.local/share/SmartPC/SmartPC/game'
P.mkdir();S.mkdir();R.mkdir()
for archive,root in (('/tmp/smartpc-learning-rc23-project.tar.gz',S),('/tmp/smartpc-learning-rc23-runtime.tar.gz',R)):
 with tarfile.open(archive) as tar:tar.extractall(root,filter='data')
shutil.copytree(H/'smartpc-overtake-project/theme-projects',S/'theme-projects')
lib=Path('/opt/smartpc/dashboard/libsmartpc_game_native.so')
for root in (S/'dashboard',R/'dashboard'):
 m=json.loads((root/'release-manifest.json').read_text());assert m['version']=='0.9.0-rc.23'
 assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in m['sha256'].items())
 shutil.copy2(lib,root/lib.name);m['sha256'][lib.name]=hashlib.sha256(lib.read_bytes()).hexdigest()
 (root/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
with sqlite3.connect((G/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.execute('PRAGMA query_only=ON')
 assert not db.execute("SELECT 1 FROM sessions WHERE status='running'").fetchone()
 checkpoint=db.execute("SELECT checkpoint FROM drivers WHERE name='Crono'").fetchone()[0]
private=P/'private';private.mkdir(mode=0o700);dest=private/'crono.json'
shutil.copy2(G/'policies'/(checkpoint+'.json'),dest);dest.chmod(0o600)
subprocess.run(['chown','-R','smartpc:smartpc',str(P),str(S),str(R)],check=True)
print(json.dumps(dict(status='prepared',checkpoint=checkpoint,originalStoreWritten=False)))
