"""Run as root on the board; preserve preferences and provide rollback."""
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
stage=Path('/var/lib/smartpc-dashboard/v08-staging/smartpc-v08-runtime');target=Path('/opt/smartpc/dashboard');proof=Path('/var/lib/smartpc-dashboard/v08-proof');proof.mkdir(mode=0o700,exist_ok=True)
manifest=json.loads((stage/'release-manifest.json').read_text());assert manifest['version']=='0.8.0-rc.1'
for relative,digest in manifest['sha256'].items():assert hashlib.sha256((stage/relative).read_bytes()).hexdigest()==digest,relative
backup=Path('/var/backups')/time.strftime('smartpc-before-v08-%Y%m%dT%H%M%SZ',time.gmtime());backup.mkdir(mode=0o700)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True);replaced=False
try:
    conf=Path('/var/lib/smartpc-dashboard/.config/SmartPC/Dashboard.conf');before=hashlib.sha256(conf.read_bytes()).hexdigest()
    shutil.copytree(target,backup/'dashboard')
    # Keep the snapshot small and exclude the test/staging archives from state backup.
    shutil.copytree('/var/lib/smartpc-dashboard',backup/'state',ignore=shutil.ignore_patterns('v08-staging','v08-proof'))
    shutil.copytree('/var/cache/smartpc-dashboard',backup/'cache')
    new=target.with_name('dashboard-v08.new');assert not new.exists();shutil.copytree(stage,new)
    os.rename(target,backup/'replaced-runtime')
    try:os.rename(new,target)
    except BaseException:os.rename(backup/'replaced-runtime',target);raise
    replaced=True
    assert hashlib.sha256(conf.read_bytes()).hexdigest()==before
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
    receipt={'version':manifest['version'],'files':len(manifest['sha256']),'manifestVerified':True,'backup':str(backup),'preferenceSha256':before,'preferencesPreservedAtInstall':True,'gitCommit':manifest['gitCommit'],'dirty':manifest['dirty'],'installedAt':time.time(),'bootIdBefore':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    (proof/'install-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
except BaseException:
    if replaced:shutil.rmtree(target);shutil.copytree(backup/'dashboard',target)
    subprocess.run(['systemctl','start','smartpc-dashboard'],check=False);raise
