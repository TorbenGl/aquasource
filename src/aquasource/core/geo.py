"""Coordinate sanity checks, precision ordering and navigation interpolation."""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from .schema import PRECISION_RANK, Geo


class CoordinateRejected(ValueError):
    """A coordinate failed a sanity check; the message says which one."""


def _is_number(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def check_coordinate(lat: float | None, lon: float | None) -> str | None:
    """Return a rejection reason, or None when the coordinate is acceptable.

    ``None``/``None`` (no coordinate at all) is acceptable here; it simply
    means geo_precision ``none``.
    """
    if lat is None and lon is None:
        return None
    if lat is None or lon is None:
        return "only one of lat/lon given"
    if not (_is_number(lat) and _is_number(lon)):
        return f"non-numeric coordinate ({lat!r}, {lon!r})"
    if not -90.0 <= lat <= 90.0:
        return f"latitude {lat} outside [-90, 90]"
    if not -180.0 <= lon <= 180.0:
        return f"longitude {lon} outside [-180, 180]"
    if lat == 0.0 and lon == 0.0:
        return "coordinate is exactly (0, 0)"
    return None


_land_mask = None
_land_mask_loaded = False


def on_land(lat: float, lon: float) -> bool | None:
    """True if the point is clearly on land, None if no coastline data is available.

    Uses the optional ``global-land-mask`` package (1 km grid). Coastal and
    lake samples can legitimately fall on "land" pixels, so callers treat this
    as a flag unless configured otherwise.
    """
    global _land_mask, _land_mask_loaded
    if not _land_mask_loaded:
        _land_mask_loaded = True
        try:
            from global_land_mask import globe  # type: ignore

            _land_mask = globe
        except Exception:
            _land_mask = None
    if _land_mask is None:
        return None
    try:
        return bool(_land_mask.is_land(lat, lon))
    except Exception:
        return None


def precision_at_least(precision: str, minimum: str) -> bool:
    """True if ``precision`` is at least as precise as ``minimum``."""
    return PRECISION_RANK[precision] >= PRECISION_RANK[minimum]


def to_float(value: object) -> float | None:
    """Parse a number from provider metadata; blanks and NaN become None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) else None
    s = str(value).strip()
    if not s or s.lower() in {"nan", "null", "none", "na", "n/a", "-", "-999", "-9999"}:
        return None
    try:
        f = float(s.replace(",", ".")) if s.count(",") == 1 and "." not in s else float(s)
    except ValueError:
        return None
    return f if math.isfinite(f) else None


def depth_from(value: object) -> float | None:
    """Depth in metres, positive downwards. Elevation-style negatives are flipped."""
    d = to_float(value)
    return None if d is None else abs(d)


def parse_time(value: object) -> float | None:
    """Parse an ISO-8601-ish timestamp (or epoch seconds) to epoch seconds (UTC)."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        pass
    s = s.replace("Z", "+00:00")
    if " " in s and "T" not in s:
        s = s.replace(" ", "T", 1)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


@dataclass
class NavFix:
    t: float
    lat: float
    lon: float
    depth_m: float | None = None


@dataclass
class Interpolated:
    lat: float
    lon: float
    depth_m: float | None
    offset_s: float  # time to the nearest navigation fix used
    gap_s: float  # time between the two bracketing fixes (0 for an exact match)


class NavTrack:
    """A navigation time series used to place video frames or photos.

    Linear interpolation only between two fixes that are at most
    ``max_gap_s`` seconds apart (spec: 10 s). Otherwise ``locate`` returns None.
    """

    def __init__(self, fixes: Sequence[NavFix], max_gap_s: float = 10.0):
        good = [f for f in fixes if check_coordinate(f.lat, f.lon) is None and f.lat is not None]
        self.fixes = sorted(good, key=lambda f: f.t)
        self.times = [f.t for f in self.fixes]
        self.max_gap_s = max_gap_s

    def __len__(self) -> int:
        return len(self.fixes)

    def locate(self, t: float) -> Interpolated | None:
        if not self.fixes:
            return None
        i = bisect.bisect_left(self.times, t)
        if i < len(self.times) and self.times[i] == t:
            f = self.fixes[i]
            return Interpolated(f.lat, f.lon, f.depth_m, 0.0, 0.0)
        if i == 0 or i == len(self.times):
            return None
        a, b = self.fixes[i - 1], self.fixes[i]
        gap = b.t - a.t
        if gap <= 0 or gap > self.max_gap_s:
            return None
        w = (t - a.t) / gap
        lat = a.lat + w * (b.lat - a.lat)
        dlon = b.lon - a.lon
        if dlon > 180:
            dlon -= 360
        elif dlon < -180:
            dlon += 360
        lon = a.lon + w * dlon
        if lon > 180:
            lon -= 360
        elif lon < -180:
            lon += 360
        depth = None
        if a.depth_m is not None and b.depth_m is not None:
            depth = a.depth_m + w * (b.depth_m - a.depth_m)
        offset = min(t - a.t, b.t - t)
        return Interpolated(lat, lon, depth, offset, gap)

    def geo_at(self, t: float, geo_source: str) -> tuple[Geo, float | None]:
        """Geo for time ``t`` with precision ``segment``, plus the offset used."""
        hit = self.locate(t)
        if hit is None:
            return Geo.none(geo_source=f"{geo_source} (no fix within {self.max_gap_s:g} s)"), None
        geo = Geo(
            lat=round(hit.lat, 7),
            lon=round(hit.lon, 7),
            depth_m=None if hit.depth_m is None else round(hit.depth_m, 2),
            geo_precision="segment",
            geo_source=geo_source,
            geo_inferred=True,
            geo_uncertainty_m=None,
        )
        return geo, hit.offset_s


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse_dms(text: str) -> float | None:
    """Parse '54°52.196'N', '54 52 11.8 N', '-6.5' and similar to decimal degrees."""
    import re

    s = text.strip().upper().replace("º", "°").replace("’", "'").replace("′", "'").replace("″", '"')
    hemi = None
    m = re.search(r"([NSEW])\s*$", s) or re.match(r"^\s*([NSEW])", s)
    if m:
        hemi = m.group(1)
        s = s.replace(hemi, " ")
    nums = [float(x) for x in re.findall(r"-?\d+(?:[.,]\d+)?", s.replace(",", "."))]
    if not nums:
        return None
    deg = nums[0]
    mins = nums[1] if len(nums) > 1 else 0.0
    secs = nums[2] if len(nums) > 2 else 0.0
    value = abs(deg) + mins / 60.0 + secs / 3600.0
    if deg < 0 or hemi in ("S", "W"):
        value = -value
    return value
