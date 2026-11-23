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


def finish_window(qualifying_times,laps):
    """Allow the qualified slower grid to finish, plus one slower lap.

    The overall race budget still bounds the session. A fixed 30-second
    cutoff otherwise disqualifies a legitimate slower car before three laps.
    """
    values=[float(v) for v in qualifying_times if v is not None]
    if not values:return 30.
    if any(not math.isfinite(v) or v<=0 for v in values):raise ValueError('Invalid qualifying pace')
    if type(laps) is not int or laps<=0:raise ValueError('Invalid race lap target')
    return max(30.,(max(values)-min(values))*laps+max(values))


def academy_task(track_id,phase):
    """Lightweight task metadata; safe for QML-facing code (no NumPy import)."""
    from game_curriculum import PHASE_LABELS
    length=4*TRACK.half_straight+2*math.pi*TRACK.radius if track_id=='oval-1' else track_data(track_id)['drawing']['length']
    distance={'launch':20.,'control':length,'pace':3*length,'follow':100.,
              'overtake':200.,'corner':160.,'defend':120.,'duel':3*length,'grid':200.,'race4':3*length}[phase]
    limit={'launch':15.,'follow':40.,'overtake':50.,'corner':50.,'defend':40.,'grid':60.}.get(phase)
    if limit is None:limit=lap_budget(track_id)*(3 if phase in ('pace','duel','race4') else 1)
    return {'version':'academy-1','phase':phase,'label':PHASE_LABELS[phase],'distance':distance,
            'laps':3 if phase in ('pace','duel','race4') else 1,'limitSeconds':limit,
            'opponents':3 if phase in ('grid','race4') else 1 if phase in ('follow','overtake','corner','defend','duel') else 0,
            'stall':{'grace':2.,'creditMeters':1.,'slowSeconds':4.,'maxNoProgressSeconds':15.},
            'teacher':'traffic-pursuit-2','rewardVersion':'academy-progress-1'}
