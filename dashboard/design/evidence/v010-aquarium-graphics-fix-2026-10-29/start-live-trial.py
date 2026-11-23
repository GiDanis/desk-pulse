"""Temporarily enable rc3 3D, with persistent boot-time fallback to existing 2D."""
from pathlib import Path
import json,subprocess
W=Path('/var/lib/smartpc-dashboard/maintenance-work/graphics-fix');S=Path('/etc/systemd/system');D=S/'smartpc-dashboard.service.d'
assert json.loads((Path('/opt/smartpc/dashboard/release-manifest.json')).read_text())['version']=='0.10.2-rc.3'
assert 'SMARTPC_AQUARIUM_RENDERER=2d' in (D/'90-aquarium-graphics-recovery.conf').read_text()
service='''[Unit]
Description=Restore SmartPC 2D after bounded graphics trial
[Service]
Type=oneshot
ExecStart=/usr/bin/rm -f /etc/systemd/system/smartpc-dashboard.service.d/99-aquarium-graphics-trial.conf
ExecStart=/usr/bin/systemctl daemon-reload
ExecStart=/usr/bin/systemctl restart smartpc-dashboard.service
'''
timer='''[Unit]
Description=Bounded SmartPC graphics trial fallback, including after reboot
[Timer]
OnActiveSec=360s
AccuracySec=1s
Unit=smartpc-graphics-trial-recovery.service
[Install]
WantedBy=timers.target
'''
trial='''# Owned by SmartPC rc3 bounded graphics trial
[Service]
Environment=SMARTPC_AQUARIUM_RENDERER=3d
Environment=QSG_INFO=1
Environment=SMARTPC_GL_PROBE_FILE=/tmp/smartpc-rc3-native-context.json
Environment=LD_PRELOAD=/var/lib/smartpc-dashboard/maintenance-work/graphics-fix/gl-probe.so
'''
for path,body in [(S/'smartpc-graphics-trial-recovery.service',service),(S/'smartpc-graphics-trial-recovery.timer',timer),(D/'99-aquarium-graphics-trial.conf',trial)]:
 assert not path.exists(),str(path)
 path.write_text(body);path.chmod(0o644)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','smartpc-graphics-trial-recovery.timer'],check=True)
subprocess.run(['systemctl','restart','smartpc-dashboard.service'],check=True)
print('3D trial started; timer restores persistent 2D in 360s and starts again after reboot',flush=True)
