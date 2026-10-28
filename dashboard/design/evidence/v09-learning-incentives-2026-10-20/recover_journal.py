"""Back up a quiescent SQLite database AND journal, recover copy, then original."""
from pathlib import Path
import json,hashlib,sqlite3,subprocess,shutil,time
H=Path('/var/lib/smartpc-dashboard');G=H/'.local/share/SmartPC/SmartPC/game';P=H/'v09-incentives-proof'
assert not any('spawn_main' in line for line in subprocess.check_output(['ps','-eo','args='],text=True).splitlines())
def hashes(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
def rows(path):
    with sqlite3.connect(path) as db:
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        return {name:db.execute('SELECT * FROM '+name+' ORDER BY rowid').fetchall() for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
    backup=H/'game-backups'/time.strftime('before-incentives-hot-journal-%Y%m%d-%H%M%S')
    before=hashes(G);assert 'game.sqlite-journal' in before
    shutil.copytree(G,backup);shutil.copytree(H/'.config/SmartPC',backup.with_name(backup.name+'-config'))
    assert hashes(backup)==before
    recovered=P/'private-recovered-game';shutil.copytree(backup,recovered)
    expected=rows(recovered/'game.sqlite')
    subprocess.run(['runuser','-u','smartpc','--','python3','-c',"import sqlite3; db=sqlite3.connect("+repr(str(G/'game.sqlite'))+"); assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'; db.close()"],check=True)
    assert rows(G/'game.sqlite')==expected,'Recovery differs from validated private copy'
    after=hashes(G);assert all(after.get(n)==v for n,v in before.items() if not n.startswith('game.sqlite'))
    with sqlite3.connect((G/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.execute('PRAGMA query_only=ON');assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        drivers=[dict(name=r[0],steps=r[1],checkpoint=r[2]) for r in db.execute('SELECT name,steps,checkpoint FROM drivers')]
    receipt=dict(status='passed',rawBackup=str(backup),rawFilesAndJournalHashes=before,privateRecoveryValidated=True,
        originalMatchesRecoveredCopy=True,allModelArtifactsPreserved=True,readonlyQueryRestored=True,drivers=drivers,
        action='SQLite automatic rollback of the pre-existing hot journal; no manual SQL edits')
    (P/'journal-recovery.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='rawFilesAndJournalHashes'}),flush=True)
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
