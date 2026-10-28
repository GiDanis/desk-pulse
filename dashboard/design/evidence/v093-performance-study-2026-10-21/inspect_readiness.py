"""Passive tooling/clock checks for the execution plan. No trace enabling."""
import datetime
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
for path in ('/sys/kernel/debug/tracing/available_events', '/sys/kernel/tracing/available_events'):
    value = read(path)
    r[path] = [line for line in value.splitlines() if line.startswith(('sched:', 'drm:'))][:40] if isinstance(value, str) else value
config = read('/boot/config-'+os.uname().release)
r['traceKernelConfig'] = [line for line in config.splitlines() if any(key in line for key in (
    'CONFIG_FTRACE', 'CONFIG_FUNCTION_TRACER', 'CONFIG_SCHED_TRACER', 'CONFIG_TRACING',
    'CONFIG_TRACEPOINTS', 'CONFIG_DEBUG_FS', 'CONFIG_PERF_EVENTS'))] if isinstance(config, str) else config
r['clocks'] = {}
for clock in ('gpu0', 'pll-gpu', 'cpu_b', 'cpu_l', 'npu', 'dram0', 'pll-ddr', 'mbus'):
    base = Path('/sys/kernel/debug/clk')/clock
    r['clocks'][clock] = {field: read(base/field) for field in ('clk_rate', 'clk_enable_count', 'clk_prepare_count')}
r['service'] = subprocess.check_output(['systemctl', 'show', 'smartpc-dashboard.service',
    '-p', 'MainPID', '-p', 'ActiveState', '-p', 'NRestarts']).decode()
r['scope'] = 'read-only; clock framework values are not independent frequency measurements'
print(json.dumps(r, indent=2))
