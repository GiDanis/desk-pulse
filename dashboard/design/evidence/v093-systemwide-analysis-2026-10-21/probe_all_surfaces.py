"""Private offline Main across the full non-game fixture corpus.

Wall time includes setup/pumping and style changes: never an FPS benchmark.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import sys
import time
import traceback

p = argparse.ArgumentParser()
p.add_argument('--source', type=Path, required=True)
p.add_argument('--theme', choices=('base', 'functional', 'apple'), required=True)
p.add_argument('--variant', choices=('day', 'night'), default='day')
p.add_argument('--output', type=Path, required=True)
p.add_argument('--from-case')
p.add_argument('--unique-surfaces', action='store_true')
p.add_argument('--public-network-oracle', action='store_true')
a = p.parse_args()
sys.path.insert(0, str(a.source.resolve()))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
from theme_fixture_support import isolate_process, read_corpus, LegacyHarness
private, base = isolate_process()
h = None
rows = []
result = dict(startedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              theme=a.theme, variant=a.variant,
              scope='Private offline Main, functional surface corpus and main-thread CPU; no GPU/optical FPS',
              status='running')
try:
    from PySide6.QtCore import qVersion
    if a.theme == 'apple':
        from theme_bundle import BundleManager, validate_project
        bundle = a.source.resolve().parent/'theme-projects/apple-calm/bundle'
        valid = validate_project(bundle)
        preflight = json.loads((bundle.parent/'evidence/preflight-cache.json').read_text())
        assert preflight['digest'] == valid['digest']
        BundleManager(base).import_bundle(bundle, preflight=lambda *_: preflight['result'], require_preflight=True)
    _, cases, contract = read_corpus()
    cases = [case for case in cases if case['family'] != 'game']
    result['sourceCorpusNonGameCases'] = len(cases)
    if a.from_case:
        start_index = next(i for i, case in enumerate(cases) if case['id'] == a.from_case)
        cases = cases[start_index:]
    if a.unique_surfaces:
        seen = set()
        cases = [case for case in cases if not (case['surfaceId'] in seen or seen.add(case['surfaceId']))]
    result.update(expectedCases=len(cases), expectedUniqueSurfaces=len({c['surfaceId'] for c in cases}),
                  excludedGameCases=6, qt=qVersion(), apiFingerprint=contract.fingerprint,
                  uniqueSurfaceSubset=a.unique_surfaces, fromCase=a.from_case,
                  publicNetworkOracle=a.public_network_oracle)
    before = time.monotonic()
    h = LegacyHarness(base, dict(theme='base' if a.theme == 'apple' else a.theme,
                                variant=a.variant, motion='normal', game=False))
    if a.theme == 'apple':
        assert h.service.selectDraft('studio.applecalm')
        h.wait_ready()
    result['harnessReadyWallMs'] = (time.monotonic()-before)*1000
    if a.public_network_oracle:
        # The old oracle searches for a legacy DashboardOverlay on new public
        # metrics surfaces. Check the actual host/context/renderer instead.
        original_assert = h.assert_surface
        def current_assert(case):
            if case['surfaceId'] not in ('network.router', 'network.wifi', 'network.ports', 'network.history'):
                return original_assert(case)
            from PySide6.QtCore import QObject
            from theme_test_support import as_value
            host = h.root.findChild(QObject, 'overlayHost')
            assert host is not None and host.property('visible') and host.property('readiness') == 'ready'
            assert host.property('contentId') == case['surfaceId'], (host.property('contentId'), case['surfaceId'])
            item = as_value(host.property('currentItem'))
            assert item is not None and item.width() > 0 and item.height() > 0
            assert any(ctx.contentId == case['surfaceId'] and ctx.lifecycle.active
                       for ctx, generation in h.service.apiFactory._contexts.values())
        h.assert_surface = current_assert
    for case in cases:
        start_wall, start_cpu = time.perf_counter_ns(), time.thread_time_ns()
        try:
            row = h.run_case(case)
            row = {key: row[key] for key in ('id', 'family', 'surfaceId', 'status', 'assertions')}
        except Exception as error:
            row = dict(id=case['id'], family=case['family'], surfaceId=case['surfaceId'],
                       status='failed', error=str(error), traceback=traceback.format_exc())
        row.update(wallMs=(time.perf_counter_ns()-start_wall)/1e6,
                   mainThreadCpuMs=(time.thread_time_ns()-start_cpu)/1e6)
        rows.append(row)
        if row['status'] != 'passed':
            # A failed style assertion can contaminate subsequent setup; record
            # the exact coverage limit instead of fabricating later passes.
            break
    result.update(status='passed' if len(rows) == len(cases) and all(r['status'] == 'passed' for r in rows) else 'partial',
                  rows=rows, qmlWarnings=h.messages, networkAttempts=h.transport,
                  measuredUniqueSurfaces=len({r['surfaceId'] for r in rows if r['status'] == 'passed'}))
except Exception as error:
    result.update(status='error', error=str(error), traceback=traceback.format_exc(), rows=rows)
finally:
    if h:
        h.close()
    private.cleanup()
    result['finishedAtUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: result.get(key) for key in ('theme', 'variant', 'status', 'expectedCases', 'measuredUniqueSurfaces', 'error')}), flush=True)
