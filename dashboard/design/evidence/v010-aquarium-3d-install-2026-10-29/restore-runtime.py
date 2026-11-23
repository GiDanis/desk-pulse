#!/usr/bin/env python3
"""Restore verified0.10.1 runtime only, retaining current user data/preferences."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
assert os.geteuid()==0,'Run with sudo'
B=Path('/var/backups/smartpc-maintenance/rollback-0.10.1-rc.1-aquarium3d-20261029-121954');R=Path('/opt/smartpc/dashboard');W=Path('/var/lib/smartpc-dashboard/maintenance-work')
m=json.loads((B/'runtime/release-manifest.json').read_text());current=json.loads((R/'release-manifest.json').read_text());assert m['version']=='0.10.1-rc.1' and current['version'] in ('0.10.2-rc.1','0.10.2-rc.2')
assert all(hashlib.sha256((B/'runtime'/f).read_bytes()).hexdigest()==v for f,v in m['sha256'].items())
W.mkdir(exist_ok=True);stage=W/'rollback-stage';assert not stage.exists();shutil.copytree(B/'runtime',stage)
subprocess.run(['systemctl','stop','smartpc-dashboard'],check=True)
try:
 R.rename(B/('replaced-0.10.2-rc.1-'+time.strftime('%Y%m%d-%H%M%S')));stage.rename(R);os.sync()
finally:subprocess.run(['systemctl','start','smartpc-dashboard'],check=True)
print('Runtime0.10.1 restored; user data, Aquarium archive and Qt dependencies retained.')
