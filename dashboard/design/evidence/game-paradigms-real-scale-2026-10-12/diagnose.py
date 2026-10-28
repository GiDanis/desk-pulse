"""Read-only source diagnostics; temporary stores never touch user pilots."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'dashboard'))
import numpy as np
from game_store import GameStore, default_profile
from game_learning import PurePursuit, Policy, PPOSmooth, Imitation, log_probability
from game_simulation import World, DT, reference_actions
from game_geometry import get_track

report = {'date': '2026-10-12', 'scope': 'PC diagnostics, no deployment or user store writes',
          'sourceHashes': {}, 'board': 'SSH failed: No route to host; live roster and FPS unverified'}
for name in ('game_learning.py', 'game_worker.py', 'game_store.py', 'game_settings.py',
             'game.py', 'game_simulation.py', 'game_curriculum.py', 'presentations/GameVisual.qml'):
    report['sourceHashes'][name] = hashlib.sha256((ROOT / 'dashboard' / name).read_bytes()).hexdigest()

report['geometricController'] = []
for track_id in ('oval-1', 'technical-1'):
    for controller in ('pilot', 'diagnostic-reference'):
        world = World(10, 17, track_id=track_id)
        world.reset(varied=True)
        learner = PurePursuit(default_profile(17, 'pure_pursuit'))
        started = time.monotonic()
        for _ in range(3600):
            if not world.active.any(): break
            obs = world.observations()
            actions = learner.act(obs) if controller == 'pilot' else reference_actions(world, obs)
            world.step(actions, return_observations=False)
        report['geometricController'].append({'track': track_id, 'controller': controller,
            'arrived': int(np.isfinite(world.finish).sum()), 'retired': int(world.retired.sum()),
            'active': int(world.active.sum()), 'simulatedSeconds': world.time,
            'finishTimes': [float(t) for t in world.finish if np.isfinite(t)],
            'wallSeconds': time.monotonic() - started})

p = default_profile(1, 'ppo_smooth')
smooth = PPOSmooth(p)
obs = np.zeros((32, 32))
mean = __import__('game_learning').forward(smooth.actor, obs, p['hidden'])
_, raw, reported, _ = smooth.sample(obs)
conditional_std = smooth.log_std + np.log(np.sqrt(1 - .82**2))
conditional = log_probability(raw, mean, conditional_std)
report['smoothNoise'] = {'firstStepConditionalVarianceFactor': 1-.82**2,
    'maximumLogProbabilityError': float(np.abs(reported-conditional).max()),
    'noiseShape': list(smooth.noise_state.shape), 'episodeResetPresent': False}

old = World(1, 1, laps=1).snapshot()
try:
    World(1, 1, laps=3).restore(old)
    outcome = 'accepted'
except ValueError as error:
    outcome = str(error)
report['oneToThreeLapCheckpoint'] = outcome

report['trackMetrics'] = []
for track_id in ('oval-1', 'technical-1'):
    t = get_track(track_id)
    report['trackMetrics'].append({'id': track_id, 'lengthM': t.length, 'widthM': t.width})

with tempfile.TemporaryDirectory(prefix='smartpc-paradigms-analysis-') as directory:
    store = GameStore(directory)
    drivers = store.drivers()
    report['newStoreRoster'] = [{'name': d['name'], 'method': d['profile']['algorithm'],
                                'hasPolicy': bool(d['policy'])} for d in drivers]
    report['uninitializedTechnicalProfiles'] = [{'name': d['name'], 'method': d['profile']['algorithm']}
                                              for d in store.drivers('technical-1')]
    target = drivers[0]
    changed = {**target['profile'], 'hidden': 32, 'algorithm': 'ppo'}
    store.set_profile(target['id'], changed)
    report['storeLock'] = {'methodChangeAccepted': store.driver(target['id'])['profile']['algorithm']=='ppo',
                           'hiddenChangeAccepted': store.driver(target['id'])['profile']['hidden']==32}
    new_id = store.create_driver('Diagnostic')
    report['createdDriverMethod'] = store.driver(new_id)['profile']['algorithm']
    pursuit = next(d for d in drivers if d['profile']['algorithm']=='pure_pursuit')
    store.reset_driver(pursuit['id'])
    report['referencePolicyAfterReset'] = store.driver(pursuit['id'])['policy']

clone = Imitation(default_profile(5, 'imitation'))
before = clone.weights.copy()
clone.learn_step(np.zeros((32, 32)))
report['imitationZeroRows'] = {'target': [0., 1.],
                             'updatesWeights': bool(np.any(clone.weights != before))}

Path(__file__).with_name('diagnostics.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
