"""Read-only reward audit. Frozen controllers; no training, Qt, store or board writes.

Run from any directory with Python/NumPy:
  OPENBLAS_NUM_THREADS=1 python probe_current_rewards.py --output /tmp/audit.json
Optional --policy accepts an immutable policy snapshot copied separately.
The full-gas case deliberately replaces only the named geometric controller's pedal.
This is a diagnostic, never an assistance mechanism for real pilots.
"""
import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np

SOURCE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SOURCE))
from game_academy import Episode
from game_catalog import RACE_PHYSICS_VERSION, TRACKS
from game_control import pursuit_actions
from game_driving_memory import PROTOCOL
from game_geometry import get_track
from game_learning import Policy
from game_simulation import DT
from game_rewards import specification,reference_time


def run(controller, seed, policy):
    episode = Episode('oval-1', 'control', seed, protocol=PROTOCOL,
                      objective='impara_infinito',reward_spec=specification())
    world = episode.world
    samples = []
    while not episode.reason:
        if controller == 'frozen_evo':
            action = policy.act(episode.observations(), world=world, index=0)
        elif controller == 'idle':
            action = np.zeros(2)
        else:
            factor = {'reference_slow': .7, 'reference': 1.,
                      'reference_fast': 1.4, 'geometric_steer_full_gas': 1.}[controller]
            action = pursuit_actions(world, [0], speed_factor=factor)[0]
            if controller == 'geometric_steer_full_gas':
                action[1] = 1.
        episode.step(action)
        u, lateral, yaw, steer = world.state[0, 3:7]
        slip = steer - math.atan2(lateral + world.vehicle.cg_front*yaw, max(u, 2.))
        samples.append((float(action[1]), abs(slip), math.hypot(u, lateral)*3.6))
    values = np.asarray(samples)
    result = episode.result()
    return dict(controller=controller, seed=seed, simulatedSeconds=episode.age,
                returnTotal=episode.return_total, reason=episode.reason,
                laps=result['laps'], cleanLaps=sum(l['clean'] for l in result['lapTimes']),
                validProgress=episode.valid_progress, trackLimits=result['trackLimits'],
                offroadSeconds=result['offroadSeconds'], rewardTerms=result['rewardTerms'],
                meanPedal=float(values[:, 0].mean()),
                fullGasFraction=float((values[:, 0] > .95).mean()),
                brakeFraction=float((values[:, 0] < -.05).mean()),
                frontSlipMedianDegrees=float(np.median(values[:, 1])*180/math.pi),
                maxSpeed=float(values[:, 2].max()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--policy', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    policy = Policy(json.loads(args.policy.read_text())) if args.policy else None
    started = time.monotonic()
    controllers = ['idle', 'geometric_steer_full_gas', 'reference_slow', 'reference', 'reference_fast']
    if policy:
        controllers.append('frozen_evo')
    rows = []
    for controller in controllers:
        for seed in (2000901, 2000902, 2000903, 2000904, 2000905):
            rows.append(run(controller, seed, policy))
        print(json.dumps(dict(controller=controller, seconds=round(time.monotonic()-started, 2))), flush=True)
    gamma = math.exp(-DT/40.)
    report = dict(scope='PC frozen-controller audit, no training or production writes',
                  physics=RACE_PHYSICS_VERSION, protocol=PROTOCOL,rewardSpec=specification(),
                  python=platform.python_version(), numpy=np.__version__,
                  policySha256=hashlib.sha256(args.policy.read_bytes()).hexdigest() if policy else None,
                  sourceHashes={name: hashlib.sha256((SOURCE/name).read_bytes()).hexdigest()
                                for name in ('game_simulation.py', 'game_academy.py', 'game_learning.py',
                                             'game_academy_trainer.py', 'game_control.py', 'game_driving_memory.py')},
                  tracks=[dict(id=t['id'], length=get_track(t['id']).length,
                               progressPerLap=10.,fatalPenaltyFractionOfLap=.3) for t in TRACKS],
                  ppo=dict(gamma=gamma, gaeLambda=.99,
                           gaeOneEfoldSeconds=-DT/math.log(gamma*.99),
                           rolloutSeconds=256*DT,
                           note='GAE decay is not the complete critic planning horizon'),
                  rows=rows, wallSeconds=time.monotonic()-started)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
