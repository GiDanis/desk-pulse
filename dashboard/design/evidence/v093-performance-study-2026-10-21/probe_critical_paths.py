"""Synthetic, headless attribution. No display, providers, real DB or training.

All settings/store writes are temporary. Emits JSON to stdout. Run with the
target's interpreter and --source pointing at its existing dashboard directory.
"""
import argparse
import cProfile
from copy import deepcopy
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import pstats
import statistics
import sys
import tempfile
import time

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
args = parser.parse_args()
source = args.source.resolve()
sys.path.insert(0, str(source))
os.environ.update(OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
try:
    os.nice(10)
except OSError:
    pass


def measure(function, repeats=20):
    function()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter_ns()
        function()
        samples.append((time.perf_counter_ns()-start)/1e6)
    ordered = sorted(samples)
    return {'n': len(samples), 'p50Ms': statistics.median(samples),
            'p95Ms': ordered[max(0, __import__('math').ceil(.95*len(ordered))-1)],
            'maxMs': max(samples), 'samplesMs': samples}


def profile(function):
    probe = cProfile.Profile()
    probe.runcall(function)
    stream = io.StringIO()
    pstats.Stats(probe, stream=stream).strip_dirs().sort_stats('cumulative').print_stats(18)
    return stream.getvalue()


result = {'capturedAtUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'scope': 'Synthetic isolated headless critical-path attribution, not GUI/render/FPS qualification',
          'runtime': {'python': sys.version, 'arch': platform.machine(), 'source': str(source)},
          'sourceHashes': {name: hashlib.sha256((source/name).read_bytes()).hexdigest() for name in (
              'game.py', 'game_results.py', 'theme_api.py', 'theme_contexts.py',
              'game_direct_trainer.py', 'game_residual_learning.py', 'game_checkpoint_writer.py')}}
with tempfile.TemporaryDirectory(prefix='smartpc-v093-study-') as temp:
    base = Path(temp)
    for key, name in (('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                      ('XDG_CACHE_HOME', 'cache'), ('XDG_STATE_HOME', 'state')):
        os.environ[key] = str(base/name)
        (base/name).mkdir()
    os.environ['SMARTPC_GAME_STORE'] = str(base/'game')
    from PySide6.QtCore import QCoreApplication, qVersion
    app = QCoreApplication([])
    app.setOrganizationName('SmartPCStudy')
    app.setApplicationName('V093CriticalPaths')
    import PySide6
    import numpy as np
    result['runtime'].update(qt=qVersion(), pyside=PySide6.__version__, numpy=np.__version__,
                             nice=os.getpriority(os.PRIO_PROCESS, 0))
    from game import GameService
    import game_results
    service = GameService(base/'game')
    assert service._drivers and not service._process
    driver = next(row for row in service._drivers if row['id'] == service._selected)
    original_curriculum = driver.get('curriculum')
    proof = {'round': 1, 'phase': 'pace', 'candidate': {
        'valid': 3, 'total': 3, 'median': 22., 'best': 21.8,
        'results': [{'reason': 'success', 'goalMeters': 100.} for _ in range(3)]},
        'rewardVersion': 'synthetic-study', 'accepted': False}
    result['progressScaling'] = []
    try:
        for count in (0, 10, 100, 1000):
            driver['curriculum'] = dict(phase='pace', evaluations=[dict(deepcopy(proof), round=i+1) for i in range(count)])
            result['progressScaling'].append({'evaluationCount': count,
                'progressOnly': measure(lambda: service._progress(driver)),
                'wholePythonSnapshot': measure(lambda: service.snapshot, repeats=12)})
        calls = [0]
        original_exercise = game_results.exercise
        def counted(*a, **kw):
            calls[0] += 1
            return original_exercise(*a, **kw)
        game_results.exercise = counted
        service._progress(driver)
        game_results.exercise = original_exercise
        result['exerciseCallsFor1000Rows'] = calls[0]
        result['progressProfile1000'] = profile(lambda: service.snapshot)
        driver['curriculum'] = original_curriculum
        result['emptyPrivateStoreRefresh'] = measure(service._refresh, repeats=8)
    finally:
        driver['curriculum'] = original_curriculum
        service.close()

    from theme_api import PublicContextFactory
    factory = PublicContextFactory()
    context = factory.create('game.track')
    assert context is not None
    result['sceneCommitScaling'] = []
    for cars in (1, 5, 32):
        for metadata_rows in (0, 100):
            scene = {'sequence': 1, 'timestamp': 1., 'cars': [dict(id=i, x=float(i), y=0.,
                heading=0., speed=10., status='in corsa', resetKey='study') for i in range(cars)],
                'sensors': [float(i) for i in range(9)],
                'meta': {'phase': 'synthetic', 'time': 1.,
                         'diagnosticRows': [{'name': str(i), 'values': list(range(12))} for i in range(metadata_rows)]}}
            def changed_commit():
                scene['sequence'] += 1
                scene['timestamp'] += 1/30
                assert factory.update(context, {'scene': scene})
            changed = measure(changed_commit)
            stable = deepcopy(scene)
            unchanged = measure(lambda: factory.update(context, {'scene': stable}))
            row = {'cars': cars, 'syntheticMetadataRows': metadata_rows,
                   'jsonBytes': len(json.dumps(scene).encode()),
                   'changed': changed, 'equalIndependentCopy': unchanged}
            if cars == 5 and metadata_rows == 100:
                row['profile'] = profile(changed_commit)
            result['sceneCommitScaling'].append(row)
    factory.release(context)

    from game_direct_bootstrap import direct_profile
    from game_racing_presets import production_profile
    from game_direct_trainer import DirectOffPolicy
    from game_residual_learning import encode_checkpoint
    policy_profile = production_profile(direct_profile(4242, 'residual_sac'))
    learner = DirectOffPolicy(policy_profile)
    rng = np.random.default_rng(193)
    learner.replay[:] = rng.normal(0, .2, learner.replay.shape)
    learner.count = learner.capacity
    learner.cursor = 0
    learner.transitions = learner.capacity
    sealed = np.empty_like(learner.replay)
    result['checkpoint'] = {'syntheticReplay': True, 'trainingSteps': 0,
        'shape': list(learner.replay.shape), 'replayBytes': learner.replay.nbytes,
        'method': policy_profile['algorithm'],
        'captureBeforeWriter': measure(lambda: learner.checkpoint(deferred='writer'), repeats=5),
        'copyToPreallocatedArray': measure(lambda: np.copyto(sealed, learner.replay), repeats=5)}
    def encode():
        value = {'learner': learner.checkpoint(deferred='writer')}
        encode_checkpoint(value)
    result['checkpoint']['encodingOutsidePreview'] = measure(encode, repeats=3)
    result['checkpoint']['captureProfile'] = profile(lambda: learner.checkpoint(deferred='writer'))
    QCoreApplication.sendPostedEvents()
    app.processEvents()
result['finishedAtUtc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps(result, indent=2))
