"""Distance filter: is a listing within the tracked ring around Greenbrier?"""
import math

from config import HOME_LAT, HOME_LON, RADIUS_MILES


def miles_from_home(lat: float, lon: float) -> float:
    """Haversine distance in miles from Greenbrier."""
    r = 3958.8
    p1, p2 = math.radians(HOME_LAT), math.radians(lat)
    dp = math.radians(lat - HOME_LAT)
    dl = math.radians(lon - HOME_LON)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def in_range(lat, lon) -> bool:
    """True if coordinates are usable and within the radius.

    Listings without coordinates pass (county whitelist already gates them);
    they just get distance = None.
    """
    if lat is None or lon is None:
        return True
    return miles_from_home(lat, lon) <= RADIUS_MILES
