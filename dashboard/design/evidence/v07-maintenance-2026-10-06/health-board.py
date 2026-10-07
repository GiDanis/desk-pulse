from pathlib import Path
import hashlib,json,subprocess
root=Path('/opt/smartpc/dashboard')
manifest=json.loads((root/'release-manifest.json').read_text())
mismatches=[name for name,digest in manifest['sha256'].items() if not (root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest]
state=Path('/var/lib/smartpc-dashboard')
prefs=state/'.config/SmartPC/Dashboard.conf'
ledgers=list((state/'.local/state/smartpc/casa').glob('*-budget.json'))
caches=[p for p in (state/'.local/state/smartpc/casa').glob('*.json') if not p.name.endswith('-budget.json')]
service=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show','smartpc-dashboard','-p','ActiveState','-p','SubState','-p','NRestarts'],text=True).splitlines())
report={'manifestVersion':manifest['version'],'manifestFiles':len(manifest['sha256']),'hashMismatches':mismatches,'service':service,
'preferencesHash':hashlib.sha256(prefs.read_bytes()).hexdigest(),'requests':[json.loads(p.read_text())['requests'] for p in ledgers],
'ledgerHashes':[hashlib.sha256(p.read_bytes()).hexdigest() for p in ledgers],
'cacheInventory':[{'devices':len(json.loads(p.read_text())['devices']),'favourites':len(json.loads(p.read_text())['favourites'])} for p in caches]}
print(json.dumps(report,indent=2))
assert not mismatches and service=={'NRestarts':'0','ActiveState':'active','SubState':'running'},report
