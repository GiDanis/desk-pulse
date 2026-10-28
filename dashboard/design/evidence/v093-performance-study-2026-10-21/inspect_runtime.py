"""Read-only runtime metadata and driver enumeration, outside the kiosk process."""
import contextlib
import datetime
import importlib.metadata
import io
import json
from pathlib import Path
import subprocess
import sys
import sysconfig
import time

r = {'capturedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
     'runtime': {'executable': sys.executable, 'python': sys.version,
                 'gilEnabled': sys._is_gil_enabled() if hasattr(sys, '_is_gil_enabled') else 'unknown',
                 'Py_GIL_DISABLED': sysconfig.get_config_var('Py_GIL_DISABLED')}}
for name in ('numpy', 'PySide6', 'neat-python', 'threadpoolctl'):
    try:
        r['runtime'][name] = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        r['runtime'][name] = 'no package metadata'
import numpy as np
stream = io.StringIO()
with contextlib.redirect_stdout(stream):
    np.show_config()
    np.show_runtime()
r['numpyConfig'] = stream.getvalue()
for key, argv in (('opencl', ['clinfo']), ('vulkan', ['vulkaninfo', '--summary'])):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=12)
        r[key] = {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}
    except (OSError, subprocess.TimeoutExpired) as error:
        r[key] = {'unavailable': str(error)}
for filename in ('/sys/kernel/debug/dri/0/state', '/sys/fs/cgroup/cgroup.controllers',
                 '/sys/fs/cgroup/system.slice/cgroup.controllers',
                 '/sys/fs/cgroup/system.slice/cgroup.subtree_control'):
    try:
        r[filename] = Path(filename).read_text()
    except OSError as error:
        r[filename] = {'unavailable': str(error)}
import os
config = Path('/boot/config-'+os.uname().release)
if config.exists():
    r['kernelOptions'] = [line for line in config.read_text().splitlines() if any(
        key in line for key in ('CONFIG_PSI', 'CONFIG_UCLAMP', 'CONFIG_SCHED_AUTOGROUP',
                               'CONFIG_PREEMPT', 'CONFIG_CPUSETS', 'CONFIG_FAIR_GROUP_SCHED',
                               'CONFIG_CGROUP_SCHED', 'CONFIG_PERF_EVENTS'))]
supervisor = int(subprocess.check_output(['systemctl', 'show', 'smartpc-dashboard', '-p', 'MainPID', '--value']))
r['health'] = []
for path in Path(f'/proc/{supervisor}/root/tmp').glob('smartpc-theme-health-*/*.json'):
    try:
        value = json.loads(path.read_text())
        r['health'].append({'record': value, 'ageSeconds': time.time()-value.get('time', 0)})
    except (OSError, ValueError) as error:
        r['health'].append({'unavailable': str(error)})
r['serviceAfter'] = subprocess.check_output(['systemctl', 'show', 'smartpc-dashboard',
    '-p', 'MainPID', '-p', 'NRestarts', '-p', 'ActiveState']).decode()
print(json.dumps(r, indent=2))
