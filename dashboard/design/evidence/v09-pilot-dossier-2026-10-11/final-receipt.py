"""Check every driver column, all artifacts and the installation receipt."""
import hashlib
import json
from pathlib import Path
import sqlite3

H=Path('/var/lib/smartpc-dashboard');P=H/'v09-pilot-dossier-install-proof'
install=json.loads((P/'install.json').read_text())
before=json.loads((P/'before.json').read_text());after=json.loads((P/'installed.json').read_text())
old=Path(install['backup'])/'private-1/SmartPC/game'
current=H/'.local/share/SmartPC/SmartPC/game'
def drivers(root):
    with sqlite3.connect('file:'+str(root/'game.sqlite')+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        return [dict(row) for row in db.execute('SELECT * FROM drivers ORDER BY number')]
def artifacts(root):
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'policies').glob('*.json')}
assert drivers(old)==drivers(current),'Driver columns, including curriculum/candidate, changed'
assert artifacts(old)==artifacts(current),'Artifacts changed'
assert all(k[:-5]==v for k,v in artifacts(current).items()),'Artifact hash mismatch'
assert after['version']=='0.9.0-rc.6' and not after['manifestMismatches']
assert before['allPreferenceHashes']==after['allPreferenceHashes']
assert after['guiHeartbeat']['ready'] and after['service']['NRestarts']=='0'
result=dict(status='passed',version=after['version'],files=551,backup=install['backup'],
            allDriverColumnsPreserved=True,artifactCount=len(artifacts(current)),allArtifactsPreserved=True,
            preferencesPreserved=True,themePreserved=before['activeTheme']==after['activeTheme'],
            sameBoot=before['bootId']==after['bootId'],newOSReboot=False,
            manifestMismatches=after['manifestMismatches'],guiHeartbeat=after['guiHeartbeat'],service=after['service'])
(P/'final-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
