"""Read-only /proc sampler; run via SSH stdin, never inside the kiosk."""
import json
import os
from pathlib import Path
import subprocess
import time

def read(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None

cg = subprocess.check_output(['systemctl', 'show', 'smartpc-dashboard', '--property=ControlGroup', '--value'], text=True).strip()
pids = [int(x) for x in read('/sys/fs/cgroup' + cg + '/cgroup.procs').split()]
# Match a standalone app.py argv, excluding the supervisor's embedded command.
pid = next(n for n in pids if Path('/proc', str(n), 'cmdline').read_bytes().split(b'\0')[1].endswith(b'/app.py'))
hz = os.sysconf('SC_CLK_TCK')

def sample():
    tasks = {}
    for q in Path('/proc', str(pid), 'task').glob('*'):
        try:
            stat = (q / 'stat').read_text().rsplit(')', 1)[1].split()
            tasks[q.name] = {'ticks': int(stat[11]) + int(stat[12]), 'name': read(q / 'comm')}
        except OSError:
            pass
    return {'monotonic': time.monotonic(), 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'tasks': tasks, 'status': read('/proc/' + str(pid) + '/status'),
            'cgroup_cpu': read('/sys/fs/cgroup' + cg + '/cpu.stat'),
            'cgroup_memory_bytes': read('/sys/fs/cgroup' + cg + '/memory.current'),
            'pressure': {k: read('/proc/pressure/' + k) for k in ['cpu', 'memory', 'io']},
            'temperature_mC': read('/sys/class/thermal/thermal_zone0/temp'),
            'cpufreq': {q.name: {k: read(q / k) for k in ['scaling_cur_freq', 'scaling_governor', 'scaling_max_freq', 'cpuinfo_max_freq']}
                        for q in Path('/sys/devices/system/cpu/cpufreq').glob('policy*')}}

samples = [sample()]
for _ in range(12):
    time.sleep(2)
    samples.append(sample())
duration = samples[-1]['monotonic'] - samples[0]['monotonic']
cpu = sorted([{'tid': tid, 'name': task['name'], 'cpu_percent_one_core': round((task['ticks'] - samples[0]['tasks'][tid]['ticks']) / hz / duration * 100, 2)}
              for tid, task in samples[-1]['tasks'].items() if tid in samples[0]['tasks']], key=lambda x: -x['cpu_percent_one_core'])
print(json.dumps({'pid': pid, 'hz': hz, 'duration_s': duration, 'thread_cpu': cpu,
                  'cpu_percent_one_core': sum(t['cpu_percent_one_core'] for t in cpu),
                  'service': subprocess.check_output(['systemctl', 'show', 'smartpc-dashboard', '--property=ActiveState,SubState,NRestarts,MainPID,CPUUsageNSec,MemoryCurrent'], text=True),
                  'boot_id': read('/proc/sys/kernel/random/boot_id'), 'samples': samples}, indent=2))
