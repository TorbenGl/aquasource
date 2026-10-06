"""Data model: candidates found by an adapter, and the sample rows we store.

Every stored sample carries the geo fields required by the project spec:
``lat``, ``lon`` (WGS 84 decimal degrees), ``depth_m``, ``geo_precision``,
``geo_source``, ``geo_inferred``, plus the optional ``geo_uncertainty_m``.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

GeoPrecision = Literal["image", "segment", "station", "fixed_site", "region", "none"]
MediaType = Literal["image", "video"]
Tier = Literal["A", "B", "C", "U", "X"]

GEO_PRECISIONS: tuple[str, ...] = ("image", "segment", "station", "fixed_site", "region", "none")

# Higher is more precise. A fixed camera has one known coordinate, so it ranks
# with station: precise position, just no spatial diversity.
PRECISION_RANK: dict[str, int] = {
    "image": 4,
    "segment": 3,
    "station": 2,
    "fixed_site": 2,
    "region": 1,
    "none": 0,
}

TIERS: tuple[str, ...] = ("A", "B", "C", "U", "X")
TIER_LABELS = {
    "A": "public domain / CC0",
    "B": "attribution (CC BY, OGL, DL-DE-BY, NLOD, Etalab)",
    "C": "share-alike (CC BY-SA)",
    "U": "unknown / unresolved",
    "X": "excluded (NC / ND / research-only)",
}


@dataclass
class Geo:
    """Geolocation of one sample."""

    lat: float | None
    lon: float | None
    depth_m: float | None
    geo_precision: str
    geo_source: str
    geo_inferred: bool
    geo_uncertainty_m: float | None = None

    def __post_init__(self) -> None:
        if self.geo_precision not in PRECISION_RANK:
            raise ValueError(f"unknown geo_precision {self.geo_precision!r}")
        if self.geo_precision == "none":
            if self.lat is not None or self.lon is not None:
                raise ValueError("geo_precision 'none' must not carry coordinates")
        elif self.lat is None or self.lon is None:
            raise ValueError(f"geo_precision {self.geo_precision!r} needs lat and lon")

    @classmethod
    def none(cls, geo_source: str = "", depth_m: float | None = None) -> "Geo":
        """No usable coordinates. ``geo_source`` may say what was looked at."""
        return cls(None, None, depth_m, "none", geo_source, False, None)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Licence:
    """Licence of one sample, read at the most specific level available."""

    name: str
    tier: str
    level: Literal["file", "record", "collection", "unknown"]
    url: str | None
    attribution: str

    def __post_init__(self) -> None:
        if self.tier not in TIERS:
            raise ValueError(f"unknown tier {self.tier!r}")


@dataclass
class Candidate:
    """One media item found by ``Adapter.discover()`` (metadata only)."""

    source: str
    item_id: str
    media_type: str
    media_url: str
    origin_url: str
    timestamp: str | None = None
    ext: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def sample_id(self) -> str:
        return make_sample_id(self.source, self.item_id)


def make_sample_id(source: str, item_id: str) -> str:
    """Stable, filesystem-safe id: ``<source>-<sha1(item_id)[:16]>``."""
    digest = hashlib.sha1(f"{source}\x00{item_id}".encode()).hexdigest()[:16]
    return f"{source}-{digest}"


# Field order of a samples.jsonl row.
SAMPLE_FIELDS: tuple[str, ...] = (
    "sample_id",
    "source",
    "item_id",
    "media_type",
    "origin_url",
    "media_url",
    "licence",
    "licence_tier",
    "licence_level",
    "licence_url",
    "attribution",
    "lat",
    "lon",
    "depth_m",
    "geo_precision",
    "geo_source",
    "geo_inferred",
    "geo_uncertainty_m",
    "timestamp",
    "local_path",
    "bytes",
    "sha256",
    "status",
    "extra",
)


def sample_row(
    cand: Candidate,
    licence: Licence,
    geo: Geo,
    *,
    local_path: str | None = None,
    nbytes: int | None = None,
    sha256: str | None = None,
    status: str = "selected",
) -> dict[str, Any]:
    """Build one samples.jsonl row."""
    row = {
        "sample_id": cand.sample_id,
        "source": cand.source,
        "item_id": cand.item_id,
        "media_type": cand.media_type,
        "origin_url": cand.origin_url,
        "media_url": cand.media_url,
        "licence": licence.name,
        "licence_tier": licence.tier,
        "licence_level": licence.level,
        "licence_url": licence.url,
        "attribution": licence.attribution,
        **geo.to_dict(),
        "timestamp": cand.timestamp,
        "local_path": local_path,
        "bytes": nbytes,
        "sha256": sha256,
        "status": status,
        "extra": cand.extra or {},
    }
    return {k: row[k] for k in SAMPLE_FIELDS}
