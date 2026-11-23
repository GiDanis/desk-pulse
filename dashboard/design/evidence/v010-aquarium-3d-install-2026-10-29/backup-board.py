"""Create and verify a quiescent rollback before package/runtime changes."""
from pathlib import Path
import hashlib,json,os,shutil,sqlite3,subprocess,time
H=Path('/var/lib/smartpc-dashboard');W=H/'maintenance-work';R=Path('/opt/smartpc/dashboard');DATA=H/'.local/share/SmartPC/SmartPC';G=DATA/'game'
def hashes(root):
 return {str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file() and not f.is_symlink()}
def game(root=G):
 with sqlite3.connect((root/'game.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall()
  logical=hashlib.sha256('\n'.join(db.iterdump()).encode()).hexdigest()
 return {'logicalSha256':logical,'artifacts':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in root.rglob('*') if f.is_file() and not f.name.startswith('game.sqlite')}}
m=json.loads((R/'release-manifest.json').read_text());assert m['version']=='0.10.1-rc.1' and len(m['sha256'])==533
assert all(hashlib.sha256((R/f).read_bytes()).hexdigest()==v for f,v in m['sha256'].items())
B=Path('/var/backups/smartpc-maintenance')/('rollback-0.10.1-rc.1-aquarium3d-'+time.strftime('%Y%m%d-%H%M%S'));B.mkdir(mode=0o700)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 before={'game':game(),'configurationHashes':hashes(H/'.config'),'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'theme':json.loads((DATA/'theme-activation.json').read_text())['active']}
 (B/'state').mkdir()
 for source,dest in [(R,B/'runtime'),(H/'.config',B/'state/.config'),(H/'.local',B/'state/.local'),(H/'game-runtime',B/'state/game-runtime')]:
  subprocess.run(['cp','-a','--reflink=auto',str(source),str(dest)],check=True)
 for f in H.iterdir():
  if f.is_file() and (f.suffix in ('.json','.sqlite3') or f.name.startswith('events.sqlite3-')):subprocess.run(['cp','-a',str(f),str(B/'state'/f.name)],check=True)
 (B/'system').mkdir()
 for f in [Path('/etc/systemd/system/smartpc-dashboard.service'),Path('/etc/systemd/system/smartpc-dashboard.service.d'),Path('/etc/smartpc')]:
  if f.exists():subprocess.run(['cp','-a',str(f),str(B/'system'/f.name)],check=True)
 assert hashes(B/'state/.config')==before['configurationHashes'] and game(B/'state/.local/share/SmartPC/SmartPC/game')==before['game']
 assert all(hashlib.sha256((B/'runtime'/f).read_bytes()).hexdigest()==v for f,v in m['sha256'].items())
 assert hashes(B/'state/.local')==hashes(H/'.local')
 before['packageState']=subprocess.check_output(['dpkg-query','-W','-f=${Package}\t${Version}\t${db:Status-Abbrev}\n'],text=True)
 before['heldPackages']=subprocess.check_output(['apt-mark','showhold'],text=True).splitlines()
 (B/'preservation.json').write_text(json.dumps(before,indent=2)+'\n')
 manifest=hashes(B);(B/'backup-manifest.json').write_text(json.dumps({'files':manifest},indent=2)+'\n');os.sync()
 receipt={'status':'passed','backup':str(B),'baselineManifestSha256':hashlib.sha256((R/'release-manifest.json').read_bytes()).hexdigest(),'verifiedBackupFiles':len(manifest),'configurationVerified':True,'userLocalDataVerified':True,'gameIntegrityAndArtifactsVerified':True,'gameArtifacts':len(before['game']['artifacts']),'bootId':before['bootId']}
 (W/'backup-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
