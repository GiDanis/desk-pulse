"""Isolated, network-denied analysis of real Main; does not measure EGLFS/GPU."""
import argparse
from collections import Counter
from copy import deepcopy
import cProfile
import json
from pathlib import Path
import pstats
import platform
import statistics
import time
from unittest.mock import patch

from theme_fixture_support import isolate_process, LegacyHarness

parser = argparse.ArgumentParser()
parser.add_argument('--theme', choices=['base', 'apple'], required=True)
parser.add_argument('--fixtures', type=int, default=380)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--no-profile', action='store_true')
parser.add_argument('--pin-style', action='store_true', help='analysis-only experiment: retain Python style wrapper within each context')
args = parser.parse_args()
private, base = isolate_process()
import theme_api
import PySide6
from PySide6.QtCore import qVersion
from theme_bundle import BundleManager, validate_project
import sport

calls = Counter()
cost = Counter()
cache_stats = Counter()
cache_keys = {}
normalizer = theme_api.normalize_legacy
cached = theme_api._cached
sport_data = sport.SportService._data
style_refs = {}

def observed_cache(cache, key, raw, build):
    label = str(key)
    cache_stats[label + ':lookup'] += 1
    if label == 'style':
        record = cache_keys.setdefault(str(id(cache)), {'input_type': type(raw).__name__, 'keys': Counter()})
        record['keys'][str(raw) if isinstance(raw, tuple) else type(raw).__name__] += 1
    def observed_build():
        cache_stats[label + ':build'] += 1
        return build()
    return cached(cache, key, raw, observed_build)

def normalize(*a, **kw):
    if args.pin_style:
        # Isolated experiment only. No change to the runtime or Theme API.
        style_refs[id(a[2])] = a[1].get('style')
    t = time.perf_counter()
    try:
        return normalizer(*a, **kw)
    finally:
        key = 'normalize:' + a[0]
        calls[key] += 1
        cost[key] += (time.perf_counter() - t) * 1000

def data(self):
    t = time.perf_counter()
    try:
        return sport_data(self)
    finally:
        calls['sport._data'] += 1
        cost['sport._data'] += (time.perf_counter() - t) * 1000

def stats(values):
    ordered = sorted(values)
    return {'n': len(values), 'median_ms': statistics.median(ordered),
            'p95_ms': ordered[int((len(ordered)-1)*.95)], 'max_ms': max(ordered)}

h = None
try:
    if args.theme == 'apple':
        project = Path(__file__).resolve().parents[4] / 'theme-projects/apple-calm/bundle'
        valid = validate_project(project)
        preflight = json.loads((project.parent / 'evidence/preflight-cache.json').read_text())
        assert preflight['digest'] == valid['digest']
        BundleManager(base).import_bundle(project, preflight=lambda *_: preflight['result'], require_preflight=True)
    with patch('theme_api.normalize_legacy', normalize), patch('theme_api._cached', observed_cache), patch.object(sport.SportService, '_data', data):
        h = LegacyHarness(base, {'theme': 'base', 'variant': 'day', 'motion': 'off'})
        if args.theme == 'apple':
            assert h.service.selectDraft('studio.applecalm')
            h.wait_ready()
        original = deepcopy(h.sport._snapshot)
        rows = original['fixtures']
        expanded = []
        for i in range(args.fixtures):
            row = deepcopy(rows[i % len(rows)])
            row.update(canonicalMatchId='analysis-'+str(i), round=str(i//10+1),
                       kickoffUtc=h.now+3600+i*7200, status='scheduled', homeScore=None, awayScore=None)
            expanded.append(row)
        h.sport._snapshot['fixtures'] = expanded
        h.sport.changed.emit()
        h.wait_ready()
        h.pump(50)
        # Stable timers and sources stay as configured by the existing harness.
        # No artificial delay is included in timed action samples.
        cold, warm, keys = [], [], []
        def action(expr):
            start = time.perf_counter()
            h.expression(expr)
            direct = (time.perf_counter() - start) * 1000
            h.wait_ready()
            h.app.processEvents()
            return direct, (time.perf_counter() - start) * 1000
        h.root.setProperty('familyId', 'oggi')
        h.wait_ready()
        calls.clear(); cost.clear(); cache_stats.clear(); cache_keys.clear()
        profiler = cProfile.Profile()
        if not args.no_profile:
            profiler.enable()
        for run in range(3):
            for family in ['meteo', 'account', 'sports', 'casa', 'network', 'oggi']:
                h.root.setProperty('overlay', '')
                h.root.setProperty('overlayStack', [])
                h.root.setProperty('familyId', family)
                h.wait_ready()
                for _ in range(2):
                    direct, ready = action('activateKey(8)')
                    (cold if run == 0 else warm).append({'family': family, 'direct_ms': direct, 'ready_ms': ready})
            h.root.setProperty('familyId', 'sports')
            h.root.setProperty('sportHubSelectedId', 'sport')
            h.wait_ready()
            action('activateKey(5)')
            assert h.value('overlay') == 'sportList'
            h.root.setProperty('sportIndex', 0)
            h.wait_ready()
            for i in range(24):
                before = h.value('sportIndex')
                direct, ready = action('activateKey(8)' if i % 2 == 0 else 'activateKey(2)')
                assert h.value('sportIndex') != before, 'exclude boundary no-ops'
                keys.append({'direct_ms': direct, 'ready_ms': ready})
            action('activateKey(7)')
        if not args.no_profile:
            profiler.disable()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if not args.no_profile:
            profiler.dump_stats(str(args.output.with_suffix('.pstats')))
            with args.output.with_suffix('.profile.txt').open('w') as output:
                pstats.Stats(profiler, stream=output).strip_dirs().sort_stats('cumulative').print_stats(45)
        report = {'theme': args.theme, 'fixture_count': len(expanded), 'environment': 'PC offscreen software, isolated, motion off', 'runtime': {'python': platform.python_version(), 'qt': qVersion(), 'pyside': PySide6.__version__}, 'cprofile_enabled': not args.no_profile, 'experimental_style_wrapper_retention': args.pin_style,
                  'scope': 'QQmlExpression activateKey plus ViewHost readiness; no frame/optical timing, no native board latency',
                  'cold_cycle': cold, 'warm_cycles': warm, 'list_keys': keys,
                  'statistics': {'cold_ready': stats([x['ready_ms'] for x in cold]),
                                 'warm_ready': stats([x['ready_ms'] for x in warm]),
                                 'list_direct': stats([x['direct_ms'] for x in keys]),
                                 'list_ready': stats([x['ready_ms'] for x in keys])},
                  'calls': dict(calls), 'cache_stats': dict(cache_stats), 'style_cache_inputs': cache_keys, 'cumulative_ms': dict(cost), 'network_attempts': h.transport,
                  'qml_messages': h.messages}
        args.output.write_text(json.dumps(report, indent=2))
        print(json.dumps({'theme': args.theme, 'statistics': report['statistics'], 'calls': report['calls']}))
finally:
    if h is not None:
        h.close()
    private.cleanup()
