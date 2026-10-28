"""Read-only accelerator inventory; run on the board, stdout is the receipt."""
import datetime
import json
import os
import pathlib
import subprocess


def command(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=15)
        return dict(argv=args, returncode=result.returncode,
                    stdout=result.stdout, stderr=result.stderr)
    except (OSError, subprocess.TimeoutExpired) as error:
        return dict(argv=args, error=str(error))


result = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              scope='Read-only capability enumeration, not a throughput benchmark',
              kernel=os.uname().release, cpuLogical=os.cpu_count(),
              clinfo=command(['clinfo']), vulkan=command(['vulkaninfo', '--summary']),
              service=command(['systemctl', 'show', 'smartpc-dashboard.service',
                               '-p', 'ActiveState', '-p', 'NRestarts', '-p', 'MainPID']))
libraries = command(['/sbin/ldconfig', '-p'])
libraries['stdout'] = '\n'.join(line for line in libraries.get('stdout', '').splitlines()
                                if any(name in line for name in ('OpenCL', 'PVROCL', 'VK_IMG',
                                                                 'VIP', 'NBG', 'OpenVX')))
result['libraries'] = libraries
result['files'] = {}
for name in ('/etc/OpenCL/vendors/pvr.icd', '/usr/share/vulkan/icd.d/img_icd.json',
             '/sys/firmware/devicetree/base/model'):
    path = pathlib.Path(name)
    if path.exists():
        result['files'][name] = path.read_text().strip('\0\n')
result['devfreq'] = []
for device in pathlib.Path('/sys/class/devfreq').glob('*'):
    row = dict(path=str(device), resolved=str(device.resolve()))
    for name in ('name', 'cur_freq', 'governor', 'available_frequencies',
                 'device/power/runtime_status'):
        try:
            row[name] = (device/name).read_text().strip()
        except OSError:
            pass
    result['devfreq'].append(row)
print(json.dumps(result, indent=2))
