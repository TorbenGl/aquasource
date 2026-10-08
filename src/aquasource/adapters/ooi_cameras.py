"""OOI still cameras (CAMDS digital still cameras, CAMDSB / CAMDSC), Oregon shelf, slope and Axial Base, 2014 to now.

Source: OOI raw data server https://rawdata.oceanobservatories.org/files/<site>/<platform>/<instrument>/<yyyy>/<mm>/<dd>/
(Apache directory listings, anonymous). One JPEG per frame, about 10-16 MB each, about 300 frames per day in bursts.
Video cameras (CAMHD, e.g. RS03ASHS/PN03B/CAMHDA301) are NOT handled here: see adapters/ooi_camhd.py.

Licence: same OOI Data Use Policy v2-00 as CamHD (1102-00010, s4.1; read via a web.archive.org copy of
https://oceanobservatories.org/wp-content/uploads/2024/01/1102-00010_Data_Use_Policy_OOI.pdf). Collection level,
tier B (free use, derivatives allowed, no named licence), see research/ooi_cameras.md.

Geo: fixed camera. ``geo_precision`` fixed_site, ``geo_source`` = sites/ooi_cameras.csv (latest deployment position of the
OOI asset-management deployment table, one row per camera reference designator). ``geo_inferred`` false.

Adapter options (``--opt key=value``)
    from / to     first and last day to list, YYYY-MM-DD (default: 2014-01-01 to today, oldest first)
    per_day       at most N frames per camera per calendar day (default: all; a day can be about 5 GB)
    cameras       comma list of reference designators to use (default: every camera in the site table)
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from typing import Any, Iterable, Iterator

from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from ..core.sites import load_sites
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

ROOT = "https://rawdata.oceanobservatories.org/files/"
POLICY_URL = "https://oceanobservatories.org/wp-content/uploads/2024/01/1102-00010_Data_Use_Policy_OOI.pdf"
SITE_ID = "ooi_cameras"
FIRST_YEAR = 2014

DIR_RE = re.compile(r'href="(\d{2,4})/"')
# Frame names: CAMDSC102_10.33.3.146_20250601T001521_UTC.jpg (instrument, camera IP, UTC timestamp)
# Some names carry a collision suffix (..._UTC_1.jpg), so the optional ``_\d+`` is part of the name.
FRAME_RE = re.compile(r'href="([A-Z0-9]+_[\d.]+_(\d{8})T(\d{6})_UTC(?:_\d+)?\.(jpe?g|JPE?G|png))"[^\n]*?\s(\d+(?:\.\d+)?[KMGT]?)\s*\n')
UNIT = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}


def parse_size(text: str) -> int | None:
    """Apache listing size such as ``16M`` -> bytes (approximate, the listing rounds)."""
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*([KMGT]?)\s*$", text or "")
    if not m:
        return None
    return int(float(m.group(1)) * UNIT[m.group(2)])


def refdes_path(refdes: str) -> str:
    """``RS01SBPS-PC01A-07-CAMDSC102`` -> ``RS01SBPS/PC01A/CAMDSC102/`` (site / platform / instrument)."""
    site, platform, _port, instrument = refdes.split("-", 3)
    return f"{site}/{platform}/{instrument}/"


def parse_day_listing(html: str, day_url: str, day: date) -> list[dict[str, Any]]:
    """Image frames of one day folder, in listing (name) order."""
    rows = []
    for m in FRAME_RE.finditer(html):
        name, stamp, ext, size = m.group(1), m.group(3), m.group(4), m.group(5)
        ts = datetime(day.year, day.month, day.day, int(stamp[:2]), int(stamp[2:4]), int(stamp[4:6]), tzinfo=timezone.utc)
        rows.append(
            {
                "name": name,
                "url": day_url + name,
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ext": "jpg" if ext.lower().startswith("jp") else ext.lower(),
                "size": parse_size(size),
            }
        )
    return rows


def dir_links(html: str) -> list[str]:
    return DIR_RE.findall(html)


def _parse_day_opt(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


@register
class OoiCamerasAdapter(Adapter):
    key = "ooi_cameras"
    name = "OOI still cameras (CAMDS, Oregon shelf / slope / Axial Base)"
    homepage = "https://oceanobservatories.org/"
    citation = "Ocean Observatories Initiative, CAMDS still cameras (raw data, https://rawdata.oceanobservatories.org)"
    media_types = ("image",)
    host_intervals = {"rawdata.oceanobservatories.org": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._sites = None

    def _site_table(self):
        if self._sites is None:
            self._sites = load_sites(SITE_ID)
        return self._sites

    def _cameras(self) -> list[str]:
        wanted = [c.strip() for c in str(self.options.get("cameras") or "").split(",") if c.strip()]
        known = sorted(self._site_table())
        return [c for c in known if not wanted or c in wanted]

    def discover(self) -> Iterable[Candidate]:
        per_day = int(self.options.get("per_day") or 0) or None
        start = _parse_day_opt(self.options.get("from")) or date(FIRST_YEAR, 1, 1)
        end = _parse_day_opt(self.options.get("to")) or datetime.now(timezone.utc).date()
        for refdes in self._cameras():
            base = f"{ROOT}{refdes_path(refdes)}"
            try:
                root_html = self.ctx.cached_text(base, f"listing/{refdes}/index.html")
            except Exception as exc:  # noqa: BLE001
                self.ctx.fail(refdes, "discover", f"camera root listing: {exc}")
                continue
            years = [int(y) for y in dir_links(root_html) if len(y) == 4 and start.year <= int(y) <= end.year]
            for y in sorted(years):
                year_url = f"{base}{y:04d}/"
                try:
                    year_html = self.ctx.cached_text(year_url, f"listing/{refdes}/{y:04d}.html")
                except Exception as exc:  # noqa: BLE001 - a missing year is logged and skipped
                    self.ctx.fail(f"{refdes}/{y:04d}", "discover", f"year listing: {exc}")
                    continue
                for mm in sorted(dir_links(year_html), key=int):
                    if not (1 <= int(mm) <= 12) or (y, int(mm)) < (start.year, start.month) or (y, int(mm)) > (end.year, end.month):
                        continue
                    month_url = f"{year_url}{int(mm):02d}/"
                    try:
                        month_html = self.ctx.cached_text(month_url, f"listing/{refdes}/{y:04d}-{int(mm):02d}.html")
                    except Exception as exc:  # noqa: BLE001
                        self.ctx.fail(f"{refdes}/{y:04d}-{mm}", "discover", f"month listing: {exc}")
                        continue
                    for dd in sorted(dir_links(month_html), key=int):
                        if not (1 <= int(dd) <= 31):
                            continue
                        try:
                            day = date(y, int(mm), int(dd))
                        except ValueError:
                            continue
                        if day < start or day > end:
                            continue
                        day_url = f"{month_url}{int(dd):02d}/"
                        try:
                            html = self.ctx.cached_text(day_url, f"listing/{refdes}/{day.isoformat()}.html")
                        except Exception as exc:  # noqa: BLE001
                            self.ctx.fail(f"{refdes}/{day.isoformat()}", "discover", f"day listing: {exc}")
                            continue
                        for row in parse_day_listing(html, day_url, day)[:per_day]:
                            yield Candidate(
                                source=self.key,
                                item_id=f"{refdes}_{row['name']}",
                                media_type="image",
                                media_url=row["url"],
                                origin_url=day_url,
                                timestamp=row["timestamp"],
                                ext=row["ext"],
                                raw={"size": row["size"], "day": day.isoformat(), "refdes": refdes},
                            )

    def resolve_licence(self, cand: Candidate) -> Licence:
        return make_licence(
            "OOI Data Use Policy v2-00 s4.1 (free public use, derivatives allowed; no named licence)",
            level="collection",
            url=POLICY_URL,
            attribution=(
                f"OOI still camera {cand.raw.get('refdes', '')}, Ocean Observatories Initiative, "
                "https://rawdata.oceanobservatories.org"
            ),
            tier="B",
        )

    def resolve_geo(self, cand: Candidate) -> Geo:
        refdes = cand.raw["refdes"]
        site = self._site_table()[refdes]
        return site.geo(
            precision="fixed_site",
            geo_source=f"{site.source}; fixed camera, applied to every frame",
            inferred=False,
        )

    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(
            url=cand.media_url,
            ext=cand.ext or "jpg",
            expected_bytes=None,  # listing sizes are rounded (16M): never a strict check
        )
