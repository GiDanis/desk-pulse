#!/usr/bin/env python3
"""Install headless networking and a key-only developer account on this SD."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

def find_sd_root() -> Path:
    if len(sys.argv) > 2:
        return Path(sys.argv[2])
    # Search for typical mountpoints of armbian/debian rootfs
    for cand in Path('/media').glob('*/*'):
        if (cand / 'etc/armbian-release').exists() or (cand / 'etc/os-release').exists():
            return cand
    raise SystemExit('Cartella rootfs della SD non trovata. Specifica il mountpoint come secondo argomento.')

def find_ssh_pubkey() -> str:
    key_env = os.environ.get('SSH_PUBKEY')
    if key_env and Path(key_env).is_file():
        return Path(key_env).read_text().strip()
    home = Path.home()
    for cand in [
        home / '.ssh/smartpc_ed25519.pub',
        home / '.ssh/id_ed25519.pub',
        home / '.ssh/id_rsa.pub',
        home / '.ssh/authorized_keys'
    ]:
        if cand.is_file():
            return cand.read_text().strip()
    # If no public key found, generate a temporary one or warn
    raise SystemExit('Nessuna chiave SSH pubblica trovata in ~/.ssh/ (id_ed25519.pub o id_rsa.pub). Imposta SSH_PUBKEY=/path/to/key.pub')

assert os.geteuid() == 0, 'Questo script richiede privilegi di root.'
root = find_sd_root()
project = Path(__file__).resolve().parent.parent

if (root / 'etc/armbian-release').exists():
    assert 'BOARD=orangepizero3w' in (root / 'etc/armbian-release').read_text(), 'Avviso: la scheda indicata potrebbe non essere Orange Pi Zero 3W.'

credentials = Path(sys.argv[1])
data = json.loads(credentials.read_text())
assert 1 <= len(data['ssid'].encode()) <= 32
assert 8 <= len(data['password']) <= 63

def write(name, content, mode=0o644):
    p = root / name
    assert not p.is_symlink(), name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    p.chmod(mode)

# JSON string quoting is valid YAML quoting and avoids shell interpolation.
network = {'network': {'version': 2, 'renderer': 'networkd', 'wifis': {
    'wlan0': {'dhcp4': True,
        'optional': True, 'regulatory-domain': 'IT', 'access-points': {
            data['ssid']: {'password': data['password']}}}}}}
write('etc/netplan/90-smartpc-wifi.yaml', json.dumps(network, indent=2) + '\n', 0o600)
if shutil.which('netplan'):
    subprocess.run(['netplan', 'generate', '--root-dir', str(root)], check=True, stdout=subprocess.DEVNULL)

ssh_pub = find_ssh_pubkey()
write('etc/smartpc/authorized_keys', ssh_pub + '\n', 0o600)
write('usr/local/sbin/smartpc-firstboot', (project / 'scripts/smartpc-firstboot.sh').read_text(), 0o755)
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
link = root / 'etc/systemd/system/multi-user.target.wants/smartpc-firstboot.service'
if not link.exists():
    link.symlink_to('../smartpc-firstboot.service')
write('etc/ssh/sshd_config.d/00-smartpc.conf', '''PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
''')
marker = root / 'root/.not_logged_in_yet'
if marker.exists():
    marker.rename(root / 'root/.not_logged_in_yet.before-smartpc')
os.sync()
credentials.unlink()
print('✓ Wi-Fi configurato e accesso SSH smartpc tramite chiave predisposto.')
if (root / 'etc/hostname').exists():
    print('Nome scheda: ' + (root / 'etc/hostname').read_text().strip())
