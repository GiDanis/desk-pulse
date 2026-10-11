"""Versioned simulation content; SI units, independent of drivers and QML."""
from dataclasses import asdict, dataclass
import hashlib
import json


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
OBSERVATION_VERSION = 'race-32-v1'
ACTION_VERSION = 'steer-throttle-brake-v1'
OBSERVATION_SIZE = 32  # numeric9 + lane offset/heading + 3 opponents × 7
TRACK = TrackSpec()
VEHICLE = VehicleSpec()
SURFACE = SurfaceProfile()
CONDITION = ConditionProfile()
TIRE = TireProfile()


def configuration():
    result = {name: asdict(value) for name, value in (
        ('track', TRACK), ('vehicle', VEHICLE), ('surface', SURFACE),
        ('condition', CONDITION), ('tire', TIRE))}
    result.update(physics=PHYSICS_VERSION, observation=OBSERVATION_VERSION,
                  action=ACTION_VERSION, decisionHz=60, substeps=2)
    return result


def scope_hash():
    return hashlib.sha256(json.dumps(configuration(), sort_keys=True).encode()).hexdigest()
