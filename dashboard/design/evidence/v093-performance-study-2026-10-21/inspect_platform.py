"""Read-only CPU cache, thermal limits and graphics binary identity."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError as error:
        return {'unavailable': str(error)}


r = {'capturedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
r['cpuCaches'] = {cpu.name: {index.name: {key: read(index/key) for key in (
    'level', 'type', 'size', 'coherency_line_size', 'ways_of_associativity', 'shared_cpu_list')}
    for index in sorted((cpu/'cache').glob('index*'))}
    for cpu in sorted(Path('/sys/devices/system/cpu').glob('cpu[0-9]*'))}
r['thermalTrips'] = {zone.name: {path.name: read(path) for path in sorted(zone.glob('trip_point_*'))}
                     for zone in sorted(Path('/sys/class/thermal').glob('thermal_zone*'))}
r['mounts'] = subprocess.check_output(['findmnt', '-n', '-o', 'SOURCE,TARGET,FSTYPE,OPTIONS', '/']).decode()
r['driverBinaries'] = {}
for name in ('/usr/lib/libGLESv2_PVR_MESA.so.24.2.6603887',
             '/usr/lib/libpvr_dri_support.so.24.2.6603887',
             '/usr/local/lib/libEGL.so.1.0.0', '/lib/libPVROCL.so', '/lib/libVK_IMG.so'):
    path = Path(name)
    try:
        r['driverBinaries'][name] = {'resolved': str(path.resolve()), 'size': path.stat().st_size,
                                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    except OSError as error:
        r['driverBinaries'][name] = {'unavailable': str(error)}
r['serviceAfter'] = subprocess.check_output(['systemctl', 'show', 'smartpc-dashboard',
    '-p', 'MainPID', '-p', 'NRestarts', '-p', 'ActiveState']).decode()
print(json.dumps(r, indent=2))
