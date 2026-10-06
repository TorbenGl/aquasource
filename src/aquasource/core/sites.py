"""Site tables: coordinates for stations, fixed cameras and publication-derived sites.

Adapters whose samples have no per-sample coordinates can ship a CSV in
``src/aquasource/adapters/sites/<key>.csv`` with the columns

    site_id, site_name, lat, lon, depth_m, uncertainty_m, source

``source`` cites where the coordinate comes from (DOI + table/section, or the
provider metadata field). Coordinates are never invented: they are copied from
the publication / provider, or geocoded from a place name quoted there.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .geo import to_float
from .schema import Geo

SITES_DIR = Path(__file__).resolve().parents[1] / "adapters" / "sites"

# Above this uncertainty a publication-derived location only counts as "region".
STATION_MAX_UNCERTAINTY_M = 5000.0


@dataclass(frozen=True)
class Site:
    site_id: str
    site_name: str
    lat: float
    lon: float
    depth_m: float | None
    uncertainty_m: float | None
    source: str

    def geo(self, *, precision: str | None = None, geo_source: str | None = None, inferred: bool = True) -> Geo:
        """Geo for a sample at this site.

        Default precision: ``station`` if uncertainty <= 5 km (or unknown), else ``region``.
        """
        if precision is None:
            precision = "region" if (self.uncertainty_m or 0) > STATION_MAX_UNCERTAINTY_M else "station"
        return Geo(
            lat=self.lat,
            lon=self.lon,
            depth_m=self.depth_m,
            geo_precision=precision,
            geo_source=geo_source or self.source,
            geo_inferred=inferred,
            geo_uncertainty_m=self.uncertainty_m,
        )


def load_sites(path_or_key: str | Path) -> dict[str, Site]:
    path = Path(path_or_key)
    if not path.suffix:
        path = SITES_DIR / f"{path_or_key}.csv"
    out: dict[str, Site] = {}
    with open(path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            lat, lon = to_float(row.get("lat")), to_float(row.get("lon"))
            if lat is None or lon is None:
                continue
            out[row["site_id"].strip()] = Site(
                site_id=row["site_id"].strip(),
                site_name=(row.get("site_name") or "").strip(),
                lat=lat,
                lon=lon,
                depth_m=to_float(row.get("depth_m")),
                uncertainty_m=to_float(row.get("uncertainty_m")),
                source=(row.get("source") or "").strip(),
            )
    return out


def fixed_site_geo(lat: float, lon: float, depth_m: float | None, geo_source: str, uncertainty_m: float | None = None) -> Geo:
    """A fixed camera: its known position applied to every frame."""
    return Geo(lat=lat, lon=lon, depth_m=depth_m, geo_precision="fixed_site", geo_source=geo_source, geo_inferred=True, geo_uncertainty_m=uncertainty_m)
