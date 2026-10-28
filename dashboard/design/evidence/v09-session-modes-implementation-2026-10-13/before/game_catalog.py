"""Versioned simulation content; SI units, independent of drivers and QML."""
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from functools import lru_cache
from copy import deepcopy


@dataclass(frozen=True)
class TrackSpec:
    id: str = 'oval-1'
    name: str = 'Ovale'
    revision: int = 1
    half_straight: float = 36.0
    radius: float = 31.0
    road_width: float = 10.0


@dataclass(frozen=True)
class VehicleSpec:
    id: str = 'standard-1'
    length: float = 4.4
    width: float = 1.8
    wheelbase: float = 2.65
    mass: float = 1200.0
    power: float = 85000.0
    drive_force: float = 6500.0
    brake_force: float = 10000.0
    yaw_inertia: float = 1700.0
    corner_stiffness: float = 38000.0
    max_steer: float = 0.52
    steer_rate: float = 1.8


@dataclass(frozen=True)
class RaceVehicleSpec(VehicleSpec):
    cg_front: float = 1.10
    cg_height: float = .53
    drive_front: float = 1.0
    brake_front: float = .68
    air_density: float = 1.225
    drag_area: float = .65
    restitution: float = .10


@dataclass(frozen=True)
class SurfaceProfile:
    id: str = 'asphalt'
    grip: float = 0.95
    rolling: float = 0.015


@dataclass(frozen=True)
class ConditionProfile:
    id: str = 'dry'
    grip_factor: float = 1.0


@dataclass(frozen=True)
class TireProfile:
    id: str = 'standard'
    grip_factor: float = 1.0


PHYSICS_VERSION = 'f1-2'
RACE_PHYSICS_VERSION = 'f2-1'
LEGACY_OBSERVATION_VERSION = 'race-32-v1'
OBSERVATION_VERSION = 'race-42-v2'
ACADEMY_OBSERVATION_VERSION = 'race-68-v3'
ACTION_VERSION = 'steer-throttle-brake-v1'
OBSERVATION_SIZE = 42  # legacy 32 + extended speed/width + four lookahead points

def observation_size(version):
    if version == LEGACY_OBSERVATION_VERSION: return 32
    if version == OBSERVATION_VERSION: return 42
    if version == ACADEMY_OBSERVATION_VERSION: return 68
    raise ValueError("Sensori sconosciuti")

def observation_version(size):
    for version in (LEGACY_OBSERVATION_VERSION, OBSERVATION_VERSION, ACADEMY_OBSERVATION_VERSION):
        if observation_size(version)==size:return version
    raise ValueError('Dimensione sensori sconosciuta')
TRACK = TrackSpec()
VEHICLE = VehicleSpec()
RACE_VEHICLE = RaceVehicleSpec()
SURFACE = SurfaceProfile()
CONDITION = ConditionProfile()
TIRE = TireProfile()


TRACKS = ({'id':'oval-1','name':'Ovale','revision':1},
          {'id':'technical-1','name':'Circuito Tecnico','revision':1},
          {'id':'mallory-oval-1','name':'Mallory · Ovale','revision':1},
          {'id':'varano-short-1','name':'Varano · Corto','revision':1})


@lru_cache(maxsize=16)
def _track_data(identity):
    if identity=='oval-1':return asdict(TRACK)
    if identity not in {t['id'] for t in TRACKS}:raise ValueError('Circuito sconosciuto')
    return json.loads(Path(__file__).with_name('game-tracks').joinpath(identity+'.json').read_text())


def track_data(identity='oval-1'):return deepcopy(_track_data(identity))


def configuration(track_id='oval-1', observation=OBSERVATION_VERSION):
    result = {name: asdict(value) for name, value in (
        ('track', TRACK), ('vehicle', VEHICLE), ('surface', SURFACE),
        ('condition', CONDITION), ('tire', TIRE))}
    result.update(physics=PHYSICS_VERSION, observation=observation,
                  action=ACTION_VERSION, decisionHz=60, substeps=2)
    result['track']=track_data(track_id)
    if observation==ACADEMY_OBSERVATION_VERSION:
        result['vehicle']=asdict(RACE_VEHICLE);result['physics']=RACE_PHYSICS_VERSION
        result['roadRules']={'runoffMeters':6.,'offroadGrip':.45,'offroadRolling':.045,
            'contacts':'impulse-1','severeImpactSpeed':12.,'retiredCars':'ghost',
            'grid':'staggered-6m-v2'}
    return result


@lru_cache(maxsize=16)
def visual_content(track_id):
    """Static GUI projection; physics geometry stays in the worker/catalog.

    Existing compact circuits keep their legacy drawing format. New metric
    circuits publish the same exact boundary as SVG path strings, preventing
    thousands of coordinates from being copied across Qt every scene update.
    """
    config=configuration(track_id)
    drawing=config['track'].get('drawing',{'kind':'oval','bounds':[[-72,-36],[72,36]]})
    if track_id in ('mallory-oval-1','varano-short-1'):
        config={**config,'track':{k:v for k,v in config['track'].items() if k not in ('centerline','drawing')}}
        def path(points):
            return ' '.join(('M' if i==0 else 'L')+str(p[0])+','+str(-p[1]) for i,p in enumerate(points))+' Z'
        drawing={**{k:v for k,v in drawing.items() if k not in ('outer','inner')},
                 'outerPath':path(drawing['outer']),'innerPath':path(drawing['inner'])}
    return config,drawing


def configuration_hash(config):
    return hashlib.sha256(json.dumps(config,sort_keys=True).encode()).hexdigest()


def scope_hash(track_id='oval-1', observation=OBSERVATION_VERSION):
    return configuration_hash(configuration(track_id,observation))


def qualified(driver,track_id='oval-1'):
    if not driver or not driver.get('policy'):return False
    profile=driver.get('policy_profile') or driver.get('profile') or {}
    state=(driver.get('policy_curriculum') if profile.get('version')!=2 else None) or driver.get('curriculum') or {}
    if state.get('academyVersion'):
        proof=state.get('qualifications',{}).get('solo',{})
        profile=driver.get('policy_profile') or driver.get('profile') or {}
        return proof.get('scope')==scope_hash(track_id,profile.get('observation',OBSERVATION_VERSION)) and proof.get('candidateHash')==driver['policy'] and proof.get('valid',0)>=18 and proof.get('total')==20 and proof.get('laps',0)>=3
    champion=state.get('champion') or {}
    proof=champion.get('proof') or {}
    return proof.get('scope')==scope_hash(track_id,(driver.get('policy_profile') or driver.get('profile') or {}).get('observation',OBSERVATION_VERSION)) and proof.get('candidateHash')==driver['policy'] and proof.get('candidate',{}).get('valid',0)>=9 and (track_id not in ('mallory-oval-1','varano-short-1') or proof.get('candidate',{}).get('laps',1)>=3)


def race_eligible(driver,track_id='oval-1',participants=2):
    if driver and (driver.get('policy_profile') or {}).get('version')==2:
        if reference_ready(driver,track_id):return True
        proof=(driver.get('curriculum') or {}).get('qualifications',{}).get('race4' if participants>2 else 'race2',{})
        return bool(qualified(driver,track_id) and proof.get('candidateHash')==driver.get('policy') and proof.get('scope')==scope_hash(track_id,ACADEMY_OBSERVATION_VERSION) and proof.get('valid',0)>=18 and proof.get('total')==20 and proof.get('laps',0)>=3)
    # Preserve the legacy oval roster, including explicitly previous models.
    return bool(driver and driver.get('policy')) and (track_id=='oval-1' or reference_ready(driver,track_id) or qualified(driver,track_id))


def race_cohort(drivers,track_id):
    """References can select their explicit controller version per race.

    Neural policies require the physics under which they were qualified.
    """
    modern=lambda d:(d.get('policy_profile') or d.get('profile') or {}).get('observation')==ACADEMY_OBSERVATION_VERSION
    versions={modern(d) for d in drivers if not reference_ready(d,track_id)}
    if len(versions)>1:raise ValueError('Schiera modelli dello stesso percorso: precedente oppure Accademia')
    return next(iter(versions)) if versions else any(modern(d) for d in drivers)


@lru_cache(maxsize=16)
def _reference_hash(track_id,academy=False):
    from game_profiles import reference_policy
    return hashlib.sha256(json.dumps(reference_policy(track_id,academy),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def reference_ready(driver,track_id):
    """Exact immutable reference artifact; no neural qualification is implied."""
    profile=(driver.get('policy_profile') or driver.get('profile') or {}) if driver else {}
    return bool(driver and profile.get('algorithm')=='pure_pursuit' and driver.get('policy')==_reference_hash(track_id,profile.get('version')==2))
