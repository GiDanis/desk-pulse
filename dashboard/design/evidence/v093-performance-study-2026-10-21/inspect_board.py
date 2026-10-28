"""Passive v0.9.3 inventory. Stream via SSH; writes only JSON to stdout.

No dashboard imports, configuration writes, benchmark, or provider requests.
Run as root only to read process maps, selected environment keys and debugfs.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time


def read(path):
    try:
        return Path(path).read_text().strip().replace('\0', '|')
    except (OSError, UnicodeError) as error:
        return {'unavailable': str(error)}


def command(argv, timeout=12):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return {'argv': argv, 'returncode': p.returncode,
                'stdout': p.stdout.strip(), 'stderr': p.stderr.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'argv': argv, 'unavailable': str(error)}


def files(directory, names):
    return {p.name: {name: read(p/name) for name in names}
            for p in sorted(Path(directory).glob('*')) if p.is_dir()}


def service():
    return command(['systemctl', 'show', 'smartpc-dashboard.service',
                    '-p', 'MainPID', '-p', 'NRestarts', '-p', 'ActiveState',
                    '-p', 'SubState', '-p', 'Nice', '-p', 'CPUWeight',
                    '-p', 'CPUAffinity', '-p', 'AllowedCPUs', '-p', 'MemoryMax',
                    '-p', 'MemoryHigh', '-p', 'ControlGroup'])


result = {'startedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'scope': 'Passive inventory and 6 s of process CPU sampling; no FPS or throughput benchmark',
          'serviceBefore': service()}
result['identity'] = {p: read(p) for p in (
    '/proc/device-tree/model', '/proc/device-tree/compatible',
    '/etc/os-release', '/proc/version', '/proc/cpuinfo', '/proc/meminfo',
    '/proc/swaps', '/proc/cmdline', '/proc/uptime',
    '/sys/devices/system/cpu/online', '/sys/fs/cgroup/cgroup.controllers')}
result['cpuPolicies'] = files('/sys/devices/system/cpu/cpufreq', (
    'affected_cpus', 'scaling_driver', 'scaling_governor',
    'scaling_available_governors', 'scaling_min_freq', 'scaling_max_freq',
    'cpuinfo_max_freq', 'scaling_cur_freq', 'scaling_available_frequencies'))
result['cpuTopology'] = {p.name: {k: read(p/k) for k in (
    'cpu_capacity', 'regs/identification/midr_el1',
    'topology/cluster_id', 'topology/core_id')}
    for p in sorted(Path('/sys/devices/system/cpu').glob('cpu[0-9]*'))}
result['devfreq'] = files('/sys/class/devfreq', (
    'name', 'cur_freq', 'governor', 'available_governors',
    'available_frequencies', 'device/power/runtime_status', 'trans_stat'))
result['thermal'] = {p.name: {k: read(p/k) for k in ('type', 'temp', 'policy')}
                     for p in sorted(Path('/sys/class/thermal').glob('thermal_zone*'))}
result['cooling'] = {p.name: {k: read(p/k) for k in ('type', 'cur_state', 'max_state')}
                     for p in sorted(Path('/sys/class/thermal').glob('cooling_device*'))}
result['pressureBefore'] = {k: read('/proc/pressure/'+k) for k in ('cpu', 'memory', 'io')}
result['graphics'] = {p: read(p) for p in (
    '/sys/kernel/debug/pvr/status', '/sys/class/drm/card0-DP-1/status',
    '/sys/class/drm/card0-DP-1/enabled', '/sys/class/drm/card0-DP-1/modes',
    '/etc/smartpc/eglfs-kms.json', '/etc/OpenCL/vendors/pvr.icd',
    '/usr/share/vulkan/icd.d/img_icd.json')}
result['modules'] = command(['lsmod'])
result['tools'] = {name: command(argv) for name, argv in (
    ('systemd', ['systemctl', '--version']), ('python', ['python3', '--version']),
    ('gcc', ['gcc', '--version']), ('storage', ['lsblk', '-o', 'NAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS']),
    ('perf', ['perf', '--version']), ('clinfo', ['clinfo', '-l']))}
result['packages'] = command(['dpkg-query', '-W', '-f=${Package}\t${Version}\n',
    'python3-pyside6*', 'libqt6core6*', '*pvr*', '*img*', '*vulkan*',
    '*opencl*', '*vip*', 'python3-numpy', 'libopenblas*'])
root = Path('/opt/smartpc/dashboard')
manifest = json.loads((root/'release-manifest.json').read_text())
mismatches = []
for name, expected in manifest['sha256'].items():
    try:
        actual = hashlib.sha256((root/name).read_bytes()).hexdigest()
        if actual != expected:
            mismatches.append(name)
    except OSError:
        mismatches.append(name)
result['manifest'] = {'version': manifest['version'], 'files': len(manifest['sha256']),
                      'mismatches': mismatches,
                      'manifestSha256': hashlib.sha256((root/'release-manifest.json').read_bytes()).hexdigest()}
data = Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC')
for filename, keys in (('theme-activation.json', ('active', 'pending', 'generation', 'phase')),
                       ('theme-runtime-status.json', ('pid', 'ready', 'phase', 'heartbeat'))):
    try:
        value = json.loads((data/filename).read_text())
        result[filename] = {k: value[k] for k in keys if k in value}
    except (OSError, ValueError) as error:
        result[filename] = {'unavailable': str(error)}
pid = int(subprocess.check_output(['systemctl', 'show', 'smartpc-dashboard.service', '-p', 'MainPID', '--value']))
cgroup = next((line.split('=', 1)[1] for line in result['serviceBefore']['stdout'].splitlines()
               if line.startswith('ControlGroup=')), '')
cg = Path('/sys/fs/cgroup')/cgroup.lstrip('/')
result['cgroup'] = {k: read(cg/k) for k in ('cpu.weight', 'cpu.max', 'cpuset.cpus.effective',
    'memory.max', 'memory.high', 'memory.current', 'memory.events')}
processes = []
for p in Path('/proc').glob('[0-9]*'):
    try:
        if cgroup and cgroup in (p/'cgroup').read_text():
            processes.append(int(p.name))
    except OSError:
        pass
result['processes'] = []
for process in sorted(processes):
    p = Path('/proc')/str(process)
    row = {'pid': process, 'command': read(p/'cmdline'),
           'status': read(p/'status'), 'io': read(p/'io')}
    try:
        row['environment'] = {k: v for item in (p/'environ').read_bytes().decode().split('\0') if '=' in item
                              for k, v in [item.split('=', 1)]
                              if k.startswith(('QSG_', 'QT_QPA_', 'QT_QUICK_', 'QML_'))
                              or k in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                                       'SMARTPC_GAME_PRESENTER', 'XDG_CACHE_HOME')}
        maps = (p/'maps').read_text().splitlines()
        row['graphicsLibraries'] = sorted({line.split()[-1] for line in maps
                if any(k in line.lower() for k in ('libegl', 'libgles', 'pvr', 'vip', 'openblas', 'libqt6quick', 'libsmartpc'))})
        row['devices'] = sorted({str(f.readlink()) for f in (p/'fd').glob('*')
                                 if str(f.readlink()).startswith('/dev/')})
    except (OSError, UnicodeError) as error:
        row['partial'] = str(error)
    row['threads'] = command(['ps', '-T', '-p', str(process), '-o',
                            'pid,tid,psr,cls,rtprio,pri,ni,pcpu,comm'])
    result['processes'].append(row)


def counters():
    values = {}
    for process in processes:
        try:
            raw = Path(f'/proc/{process}/stat').read_text().split(') ', 1)[1].split()
            values[process] = {'ticks': int(raw[11])+int(raw[12]),
                               'startTicks': int(raw[19]), 'rssPages': int(raw[21])}
        except (OSError, ValueError, IndexError):
            pass
    return values


samples = []
for index in range(4):
    samples.append({'monotonic': time.monotonic(), 'processes': counters(),
                    'gpu': read('/sys/kernel/debug/pvr/status'),
                    'thermal': {p.name: read(p/'temp') for p in Path('/sys/class/thermal').glob('thermal_zone*')}})
    if index < 3:
        time.sleep(2)
result['samples'] = samples
result['clockTicks'] = os.sysconf('SC_CLK_TCK')
result['pageSize'] = os.sysconf('SC_PAGE_SIZE')
result['pressureAfter'] = {k: read('/proc/pressure/'+k) for k in ('cpu', 'memory', 'io')}
result['serviceAfter'] = service()
result['finishedAtUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps(result, indent=2))
