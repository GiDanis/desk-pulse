"""Whole-system passive audit: no provider requests, restart or configuration writes."""
import datetime
import json
import os
from pathlib import Path
import subprocess
import time


def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError as error:
        return {'unavailable': str(error)}


def command(argv, timeout=15):
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return dict(returncode=p.returncode, stdout=p.stdout.strip(), stderr=p.stderr.strip())
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'unavailable': str(error)}


def proc_sample():
    out = {}
    for p in Path('/proc').glob('[0-9]*'):
        try:
            text = (p/'stat').read_text()
            fields = text.rsplit(') ', 1)[1].split()
            row = dict(name=text.split('(', 1)[1].rsplit(')', 1)[0],
                       ticks=int(fields[11])+int(fields[12]), startTicks=int(fields[19]),
                       rssPages=int(fields[21]), majorFaults=int(fields[9]))
            io = read(p/'io')
            if isinstance(io, str):
                row['io'] = {k: int(v) for line in io.splitlines() for k, v in [line.split(':', 1)]}
            out[p.name] = row
        except (OSError, ValueError, IndexError):
            pass
    return out


def sample():
    return dict(monotonic=time.monotonic(), processes=proc_sample(),
                cpu=read('/proc/stat'), vmstat=read('/proc/vmstat'),
                diskstats=read('/proc/diskstats'), meminfo=read('/proc/meminfo'),
                load=read('/proc/loadavg'),
                thermal={p.name: read(p/'temp') for p in Path('/sys/class/thermal').glob('thermal_zone*')})


r = dict(capturedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
         scope='Passive whole-system observation, no active UI workload or provider calls',
         clockTicks=os.sysconf('SC_CLK_TCK'), pageSize=os.sysconf('SC_PAGE_SIZE'))
r['serviceBefore'] = command(['systemctl', 'show', 'smartpc-dashboard.service', '-p', 'MainPID',
    '-p', 'ActiveState', '-p', 'NRestarts', '-p', 'ExecMainStartTimestamp', '-p', 'MemoryCurrent',
    '-p', 'TasksCurrent', '-p', 'FragmentPath', '-p', 'DropInPaths'])
r['boot'] = {name: command(argv) for name, argv in (
    ('time', ['systemd-analyze', 'time']),
    ('criticalChain', ['systemd-analyze', 'critical-chain', 'smartpc-dashboard.service']),
    ('blame', ['systemd-analyze', 'blame']),
    ('runningServices', ['systemctl', 'list-units', '--type=service', '--state=running', '--no-pager', '--no-legend']),
    ('timers', ['systemctl', 'list-timers', '--all', '--no-pager']),
    ('failed', ['systemctl', '--failed', '--no-pager']),
    ('mounts', ['findmnt', '-n', '-o', 'TARGET,FSTYPE,OPTIONS']),
    ('freeSpace', ['df', '-B1', '/', '/var/log', '/var/cache']),
    ('journalSize', ['journalctl', '--disk-usage']),
    ('sockets', ['ss', '-s']))}
r['knobs'] = {name: read(name) for name in (
    '/proc/sys/vm/swappiness', '/proc/sys/vm/dirty_background_ratio', '/proc/sys/vm/dirty_ratio',
    '/proc/sys/vm/dirty_expire_centisecs', '/proc/sys/vm/dirty_writeback_centisecs',
    '/sys/kernel/mm/transparent_hugepage/enabled', '/sys/block/mmcblk1/queue/scheduler',
    '/sys/block/mmcblk1/queue/read_ahead_kb', '/sys/block/zram0/mm_stat',
    '/sys/block/zram0/comp_algorithm', '/proc/net/sockstat')}
r['networkCounters'] = {p.name: {k: read(p/'statistics'/k) for k in (
    'rx_bytes', 'tx_bytes', 'rx_errors', 'tx_errors', 'rx_dropped', 'tx_dropped')}
    for p in Path('/sys/class/net').glob('*')}
r['samples'] = []
for index in range(11):
    r['samples'].append(sample())
    if index < 10:
        time.sleep(2)
main = int(subprocess.check_output(['systemctl', 'show', 'smartpc-dashboard.service', '-p', 'MainPID', '--value']))
r['dashboardMemory'] = {}
for p in Path('/proc').glob('[0-9]*'):
    try:
        if '/smartpc-dashboard.service' in (p/'cgroup').read_text():
            r['dashboardMemory'][p.name] = dict(smapsRollup=read(p/'smaps_rollup'), status=read(p/'status'))
    except OSError:
        pass
r['cacheFileMetadata'] = []
for base in (Path('/var/cache/smartpc-dashboard'), Path('/var/lib/smartpc-dashboard/.local/share/SmartPC/SmartPC')):
    for p in base.glob('**/*'):
        try:
            if p.is_file() and (p.suffix in ('.sqlite', '.sqlite3', '.json') or p.name.endswith('.conf')) and 'game/' not in str(p):
                r['cacheFileMetadata'].append(dict(path=str(p), bytes=p.stat().st_size,
                    mtimeUtc=datetime.datetime.fromtimestamp(p.stat().st_mtime, datetime.timezone.utc).isoformat()))
        except OSError:
            pass
r['serviceAfter'] = command(['systemctl', 'show', 'smartpc-dashboard.service', '-p', 'MainPID',
    '-p', 'ActiveState', '-p', 'NRestarts', '-p', 'MemoryCurrent', '-p', 'TasksCurrent'])
r['finishedAtUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps(r, indent=2))
