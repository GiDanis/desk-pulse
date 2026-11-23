"""Local sunrise and sunset for the dashboard's configured location."""

from calendar import isleap
from datetime import date, datetime, time, timedelta, timezone
from functools import lru_cache
from math import acos, cos, degrees, radians, sin, tau
from zoneinfo import ZoneInfo


@lru_cache(maxsize=8)
def daylight_bounds(day: date, latitude: float, longitude: float) -> tuple[float, float]:
    """Return astronomical sunrise and sunset as UTC timestamps.

    NOAA's approximation includes standard atmospheric refraction.
    https://gml.noaa.gov/grad/solcalc/solareqns.PDF
    """
    year_days = 366 if isleap(day.year) else 365
    angle = tau * (day.timetuple().tm_yday - 1) / year_days
    time_correction = 229.18 * (
        0.000075 + 0.001868 * cos(angle) - 0.032077 * sin(angle)
        - 0.014615 * cos(2 * angle) - 0.040849 * sin(2 * angle)
    )
    declination = (
        0.006918 - 0.399912 * cos(angle) + 0.070257 * sin(angle)
        - 0.006758 * cos(2 * angle) + 0.000907 * sin(2 * angle)
        - 0.002697 * cos(3 * angle) + 0.00148 * sin(3 * angle)
    )
    lat = radians(latitude)
    zenith = radians(90.833)
    horizon = (cos(zenith) - sin(lat) * sin(declination)) / (cos(lat) * cos(declination))
    half_day = 4 * degrees(acos(max(-1.0, min(1.0, horizon))))
    noon = datetime.combine(day, time(), timezone.utc) + timedelta(
        minutes=720 - 4 * longitude - time_correction,
    )
    return (noon - timedelta(minutes=half_day)).timestamp(), (noon + timedelta(minutes=half_day)).timestamp()


def is_daylight(epoch: float, latitude: float, longitude: float, local_zone: str) -> bool:
    local_date = datetime.fromtimestamp(epoch, ZoneInfo(local_zone)).date()
    sunrise, sunset = daylight_bounds(local_date, latitude, longitude)
    return sunrise <= epoch < sunset
