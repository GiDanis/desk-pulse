"""Activate the normal rc4 launcher with an independent bounded 2D recovery guard."""
from pathlib import Path
import json,shutil,subprocess,sys
W=Path('/var/lib/smartpc-dashboard/maintenance-work/graphics-fix');S=Path('/etc/systemd/system');D=S/'smartpc-dashboard.service.d'
assert json.loads(Path('/opt/smartpc/dashboard/release-manifest.json').read_text())['version']=='0.10.2-rc.4'
assert json.loads((W/'live-rc4-postrestart.json').read_text())['status']=='passed'
sys.path.insert(0,str(W))
from aquarium_graphics_diagnostics import scanout_content
for label in ('preboot','postrestart'):
 q=W/('live-rc4-'+label+'-scanout');scanout_content((q/'scanout.raw').read_bytes(),json.loads((q/'scanout.json').read_text()))
assert 'Owned by SmartPC' in (D/'99-aquarium-graphics-trial.conf').read_text()
b=W/'removed-trial-dropins';b.mkdir(mode=0o700)
for name in ('90-aquarium-graphics-recovery.conf','99-aquarium-graphics-trial.conf'):shutil.copy2(D/name,b/name)
fallback=W/'force-2d.conf';fallback.write_text('[Service]\nEnvironment=SMARTPC_AQUARIUM_RENDERER=2d\n');fallback.chmod(0o644)
p=S/'smartpc-graphics-trial-recovery.service';assert 'Restore SmartPC 2D' in p.read_text()
p.write_text('''[Unit]
Description=Restore SmartPC 2D after bounded graphics trial
[Service]
Type=oneshot
ExecStart=/usr/bin/cp /var/lib/smartpc-dashboard/maintenance-work/graphics-fix/force-2d.conf /etc/systemd/system/smartpc-dashboard.service.d/90-aquarium-graphics-recovery.conf
ExecStart=/usr/bin/rm -f /etc/systemd/system/smartpc-dashboard.service.d/99-aquarium-graphics-trial.conf
ExecStart=/usr/bin/systemctl daemon-reload
ExecStart=/usr/bin/systemctl restart smartpc-dashboard.service
''')
for name in ('90-aquarium-graphics-recovery.conf','99-aquarium-graphics-trial.conf'):(D/name).unlink()
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','smartpc-graphics-trial-recovery.timer'],check=True)
subprocess.run(['systemctl','restart','smartpc-dashboard.service'],check=True)
print('Normal rc4 active; no diagnostic preload; independent timer restores 2D in 900s, also after reboot',flush=True)
