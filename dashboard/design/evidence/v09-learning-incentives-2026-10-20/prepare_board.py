from pathlib import Path
import hashlib,json,shutil,sqlite3,subprocess,tarfile
H=Path('/var/lib/smartpc-dashboard');P=H/'v09-incentives-proof';S=H/'smartpc-incentives-project';R=H/'smartpc-incentives-runtime';G=H/'.local/share/SmartPC/SmartPC/game'
P.mkdir(exist_ok=True);S.mkdir(exist_ok=True);R.mkdir(exist_ok=True)
for archive,root in (('/tmp/smartpc-incentives-project.tar.gz',S),('/tmp/smartpc-incentives-runtime.tar.gz',R)):
    with tarfile.open(archive) as tar:tar.extractall(root,filter='data')
shutil.copytree(H/'smartpc-learning-project/theme-projects',S/'theme-projects',dirs_exist_ok=True)
lib=Path('/opt/smartpc/dashboard/libsmartpc_game_native.so')
for root in (S/'dashboard',R/'dashboard'):
    m=json.loads((root/'release-manifest.json').read_text());assert m['version']=='0.9.0-rc.24'
    assert all(hashlib.sha256((root/n).read_bytes()).hexdigest()==v for n,v in m['sha256'].items())
    shutil.copy2(lib,root/lib.name);m['sha256'][lib.name]=hashlib.sha256(lib.read_bytes()).hexdigest()
    (root/'release-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
private=P/'private';private.mkdir(mode=0o700,exist_ok=True);private.chmod(0o700);profiles={};summaries=[]
if (P/'private-recovered-game').exists():(P/'private-recovered-game').chmod(0o700)
with sqlite3.connect((G/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
    assert not db.execute("SELECT 1 FROM sessions WHERE status='running'").fetchone(),'Pause training first'
    for d in db.execute('SELECT * FROM drivers'):
        profile=json.loads(d['profile']);method=profile['algorithm']
        if method=='race_master':continue
        assert d['checkpoint'],d['name']
        dest=private/(method+'.json');shutil.copy2(G/'policies'/(d['checkpoint']+'.json'),dest);dest.chmod(0o600)
        profiles[method]=profile;summaries.append(dict(name=d['name'],method=method,checkpoint=d['checkpoint'],steps=d['steps']))
(private/'profiles.json').write_text(json.dumps(profiles));(private/'profiles.json').chmod(0o600)
(P/'original-copy-receipt.json').write_text(json.dumps(dict(status='copied-read-only',drivers=summaries,productionWrites=False),indent=2)+'\n')
subprocess.run(['chown','-R','smartpc:smartpc',str(P),str(S),str(R)],check=True)
print('Prepared exact ARM packages and four private original checkpoints',flush=True)
