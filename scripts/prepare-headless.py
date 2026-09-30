#!/usr/bin/env python3
"""Install headless networking and a key-only developer account on this SD."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('/media/giuseppe/armbi_root')
project = Path('/home/giuseppe/Documenti/Workspace/SmartPC')
assert os.geteuid() == 0
source = subprocess.check_output(['findmnt', '-nro', 'SOURCE', '--target', str(root)], text=True).strip()
uuid = subprocess.check_output(['blkid', '-s', 'UUID', '-o', 'value', source], text=True).strip()
assert uuid in ('932dec6a-307e-4174-8694-c4a1ef18eef4', 'd8bcf295-3d76-4436-be46-7c06b17369f9', 'B6D0-9AA5'), f'Wrong SD card: {uuid}'
assert 'BOARD=orangepizero3w\n' in (root/'etc/armbian-release').read_text()
credentials = Path(sys.argv[1])
data = json.loads(credentials.read_text())
assert 1 <= len(data['ssid'].encode()) <= 32
assert 8 <= len(data['password']) <= 63

def write(name, content, mode=0o644):
    p = root/name
    assert not p.is_symlink(), name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    p.chmod(mode)

# JSON string quoting is valid YAML quoting and avoids shell interpolation.
network = {'network': {'version': 2, 'renderer': 'networkd', 'wifis': {
    'wlan0': {'dhcp4': True,
        'optional': True, 'regulatory-domain': 'IT', 'access-points': {
            data['ssid']: {'password': data['password']}}}}}}
write('etc/netplan/90-smartpc-wifi.yaml', json.dumps(network, indent=2)+'\n', 0o600)
subprocess.run(['netplan', 'generate', '--root-dir', str(root)], check=True, stdout=subprocess.DEVNULL)
write('etc/smartpc/authorized_keys', Path('/home/giuseppe/.ssh/smartpc_ed25519.pub').read_text(), 0o600)
write('usr/local/sbin/smartpc-firstboot', (project/'scripts/smartpc-firstboot.sh').read_text(), 0o755)
write('etc/systemd/system/smartpc-firstboot.service', '''[Unit]
Description=Configure SmartPC SSH developer access
After=local-fs.target
Before=ssh.service getty.target
ConditionPathExists=!/var/lib/smartpc/provisioned

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/smartpc-firstboot
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
''')
link = root/'etc/systemd/system/multi-user.target.wants/smartpc-firstboot.service'
if not link.exists():
    link.symlink_to('../smartpc-firstboot.service')
write('etc/ssh/sshd_config.d/00-smartpc.conf', '''PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
''')
marker = root/'root/.not_logged_in_yet'
if marker.exists():
    marker.rename(root/'root/.not_logged_in_yet.before-smartpc')
os.sync()
credentials.unlink()
print('Wi-Fi configurato; accesso SSH smartpc tramite chiave predisposto.')
print('Nome scheda: '+(root/'etc/hostname').read_text().strip())
