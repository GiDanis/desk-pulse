"""Versioned task budgets, independent of UI and wall-clock rendering."""
from game_catalog import track_data, TRACK
import math

TRAINING_PROTOCOL = 'driving-task-2'
TRIAL_PROTOCOL = 'time-trial-laps-2'


def lap_budget(track_id):
    # Conservative initial learning pace; no imposed vehicle speed.
    return max(60., (4*TRACK.half_straight+2*math.pi*TRACK.radius if track_id=='oval-1' else track_data(track_id)['drawing']['length']) / 7. * 1.8)


def training_task(track_id, phase='control', minimum_seconds=60):
    laps = 3 if phase in ('pace','endurance', 'traffic') else 1
    return {'version':TRAINING_PROTOCOL, 'laps':laps,
            'limitSeconds':max(float(minimum_seconds), lap_budget(track_id)*laps)}


def race_budget(track_id, laps):
    return max(300., lap_budget(track_id)*laps)
