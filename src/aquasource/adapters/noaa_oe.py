"""NOAA Ocean Exploration video portal (NCEI): ROV video segments of the Okeanos Explorer dives, 2013 to date.

Portal https://www.ncei.noaa.gov/access/ocean-exploration/video/ searches the OneStop granule index of data.noaa.gov
(``POST https://data.noaa.gov/onestop/api/search/search/granule``, the same request the portal's page sends). Every
hit is one video segment (about 5 minutes) of one camera of one dive (``fileIdentifier`` such as
``EX2503_DIVE16_20250501T025000Z_ROVHD``). Only the low-resolution MP4 (``..._Low.mp4``, 360P H.264, about 1.5 Mbit/s)
is downloaded; the high-resolution .mov (ProRes) and the still frames are not. Filtering by project
``NOAAOceanExploration`` gives about 112 k granules (2026-10-08; the index also holds the mapping and BEDI records).

Licence, tier A (read at collection level, no per-file or per-record licence is published): NOAA / NCEI is a US federal
agency and these are US government works (17 U.S.C. 105), public domain. The ISO records of the accessions say
``accessLevel: public`` and "available to the public for a wide variety of uses" (research/noaa_oe.md). A record whose
text says "copyright", "all rights reserved" or the copyright sign is tier U (never upgraded). Attribution: the
cruise citation (the segment record says "use the citation from the cruise"; the cruise landing page is given), the
segment id and the portal URL.

Geo (``resolve_geo``): ``attributes.spatialBounding`` (GeoJSON Polygon, WGS 84) of the segment, present on about
half of the records (the others have none: geo ``none``, kept with the reason). Lat / lon = centre of the box,
``geo_precision`` segment, ``geo_inferred`` true (a box centre, not a published point), ``geo_uncertainty_m`` = half
the box diagonal. Depth: the description says "between A m and B m" and A = B = 0.0 m is a placeholder: then
``depth_m`` is empty; otherwise the mean of A and B. No coordinate is invented.

Noisy data is kept and marked: ``extra.maybe_not_underwater`` is true for LAUNCH / RECOVERY segments of the ROV, the
PTROBO / SBROBO / CPHD camera names of the ship's deck cameras and the still-camera ``Still_Cam`` clips.

How it works
    * Paging: ``POST`` with ``page.offset`` / ``page.max`` (max 100), sorted by ``beginDate`` descending. Each answer is
      cached under metadata/raw/search/ so a re-run does not hit the index again. Discovery is lazy: a small budget
      reads only the first pages.
    * Item id = ``fileIdentifier`` (stable). Only granules with a ``.mp4`` link are candidates; the rest are counted as
      skipped (``no mp4 link``).
    * Media: plain HTTPS GET of the low-resolution MP4 on www.ncei.noaa.gov (``/data/oceans/oer/video/<cruise>/Video/
      <dive>/Compressed/<file>_Low.mp4``), Range supported.

Adapter options (``--opt key=value``)
    from, to     ISO dates (``2025-01-01``): keep granules whose start lies inside (datetime filter of the index).
    pages        visit at most this many index pages of ``page_max`` granules (default: all, about 1,121 pages).
    page_max     granules per index request (default 100, the portal's value is 100).
    refresh_metadata  core option: re-read the cached index pages.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Iterable, Iterator

from ..core.geo import haversine_m, to_float
from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

API = "https://data.noaa.gov/onestop/api/search/search/granule"
PORTAL = "https://www.ncei.noaa.gov/access/ocean-exploration/video/"
CRUISE_PAGE = "https://www.ncei.noaa.gov/waf/okeanos-rov-cruises/{cruise}/"
PROJECT = "NOAAOceanExploration"
FORMATS = [
    "MP4 WRAPPED/.MP4, CODEC=H.264, 360P, 1.5MBPS",
    "HIGH RESOLUTION FILE: MP4 (MPEG 4), CODEC=H.264, 720X480 PIXELS, 63MB/MIN, AUDIO 48 KHZ & 128 KBPS. LOW RESOLUTION: MP4 WRAPPED/.MP4, CODEC=H.264, 360P, 1.5MBPS.",
    "JPEG",
]  # fmt: skip
DEFAULT_PAGE_MAX = 100
MAX_PAGE = 100  # the portal asks for 100 per page
GEO_SOURCE = "OneStop granule attributes.spatialBounding (Polygon, WGS 84): centre of the segment's box"
GEO_SOURCE_NONE = "OneStop granule attributes.spatialBounding (null on this granule)"
BETWEEN_RE = re.compile(r"between\s+(-?[\d.]+)\s*m\s+and\s+(-?[\d.]+)\s*m", re.IGNORECASE)
COPYRIGHT_RE = re.compile(r"copyright|all rights reserved|©", re.IGNORECASE)
NOISY_RE = re.compile(r"LAUNCH|RECOVERY|PTROBO|SBROBO|CPHD|Still_Cam", re.IGNORECASE)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ----------------------------------------------------------------------------------------------- pure helpers
def cruise_of(file_id: str) -> str:
    """``EX2503_DIVE16_20250501T025000Z_ROVHD`` -> ``EX2503`` (lower case: the WAF folder name)."""
    return file_id.split("_", 1)[0].lower()


def dive_of(file_id: str) -> str:
    parts = file_id.split("_")
    return parts[1] if len(parts) > 1 else ""


def mp4_url(attrs: dict[str, Any]) -> str | None:
    """The low-resolution MP4 link of a granule (the ``_Low.mp4`` one when there are several)."""
    urls = [str(link.get("linkUrl") or "") for link in attrs.get("links") or []]
    mp4 = [u for u in urls if u.lower().split("?")[0].endswith(".mp4")]
    if not mp4:
        return None
    return next((u for u in mp4 if u.endswith("_Low.mp4")), mp4[0])


def oerkey_url(attrs: dict[str, Any]) -> str | None:
    for link in attrs.get("links") or []:
        url = str(link.get("linkUrl") or "")
        if "oerkey=" in url:
            return url
    return None


def bbox_of(attrs: dict[str, Any]) -> tuple[float, float, float, float] | None:
    """(min_lat, min_lon, max_lat, max_lon) of a Polygon ``spatialBounding``, else None."""
    sb = attrs.get("spatialBounding")
    if not isinstance(sb, dict) or sb.get("type") != "Polygon":
        return None
    ring = (sb.get("coordinates") or [[]])[0]
    lons = [to_float(p[0]) for p in ring if len(p) >= 2]
    lats = [to_float(p[1]) for p in ring if len(p) >= 2]
    if not lons or not lats or None in lons or None in lats:
        return None
    min_lat, max_lat, min_lon, max_lon = min(lats), max(lats), min(lons), max(lons)
    if not (-90 <= min_lat and max_lat <= 90 and -180 <= min_lon and max_lon <= 180):
        return None
    if min_lat == max_lat == 0 and min_lon == max_lon == 0:
        return None
    return min_lat, min_lon, max_lat, max_lon


def depth_range_m(text: str) -> float | None:
    """Mean of 'between A m and B m' in the granule description; None for the 0.0 m / 0.0 m placeholder."""
    m = BETWEEN_RE.search(text or "")
    if not m:
        return None
    a, b = float(m.group(1)), float(m.group(2))
    if a == 0 and b == 0:
        return None
    return round(abs((a + b) / 2), 2)


def light_record(attrs: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "fileIdentifier", "title", "description", "beginDate", "endDate", "parentIdentifier",
        "gcmdLocations", "gcmdInstruments", "keywords", "spatialBounding", "citeAsStatements",
    )  # fmt: skip
    return {k: attrs[k] for k in keys if k in attrs}


def check_options(options: dict[str, Any]) -> list[str]:
    problems = []
    for name in ("from", "to"):
        value = options.get(name)
        if value not in (None, "") and not (isinstance(value, str) and ISO_DATE_RE.match(value)):
            problems.append(f"option {name} must be an ISO date (YYYY-MM-DD), got {value!r}")
    for name in ("pages", "page_max"):
        v = options.get(name)
        if v not in (None, "") and (to_float(v) is None or to_float(v) < 1):
            problems.append(f"option {name} must be a number >= 1, got {v!r}")
    if (to_float(options.get("page_max")) or 0) > MAX_PAGE:
        problems.append(f"option page_max must be <= {MAX_PAGE}")
    return problems


@register
class NoaaOeAdapter(Adapter):
    key = "noaa_oe"
    name = "NOAA Ocean Exploration video portal: ROV dive video segments (low-res MP4)"
    homepage = PORTAL
    citation = "NOAA Ocean Exploration, Okeanos Explorer ROV dives, NCEI (cruise citations in each record)"
    media_types = ("video",)
    manual_steps = "None. Anonymous HTTPS and the public OneStop index; no token."
    host_intervals = {"data.noaa.gov": 1.0, "www.ncei.noaa.gov": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self.skipped: dict[str, int] = {}

    def check_ready(self) -> list[str]:
        return super().check_ready() + check_options(self.options)

    # ------------------------------------------------------------------------------------------- metadata I/O
    def _opt(self, name: str) -> str | None:
        value = self.options.get(name)
        return None if value in (None, "") else str(value)

    def _body(self, offset: int, page_max: int) -> dict[str, Any]:
        filters: list[dict[str, Any]] = [
            {"type": "facet", "name": "projects", "values": [PROJECT]},
            {"type": "facet", "name": "dataFormats", "values": FORMATS},
        ]
        frm, to = self._opt("from"), self._opt("to")
        if frm or to:
            dt: dict[str, Any] = {"type": "datetime"}
            if frm:
                dt["after"] = f"{frm}T00:00:00Z"
            if to:
                dt["before"] = f"{to}T23:59:59Z"
            filters.append(dt)
        return {
            "queries": [],
            "sort": [{"beginDate": "desc"}],
            "filters": filters,
            "facets": False,
            "page": {"max": page_max, "offset": offset},
            "summary": False,
        }

    def _page(self, offset: int, page_max: int) -> dict[str, Any]:
        """One index answer, cached in metadata/raw/search/ (re-runs do not hit the index)."""
        name = f"search/offset{offset:07d}_max{page_max}_{self._opt('from') or 'x'}_{self._opt('to') or 'x'}.json"
        path = self.ctx.layout.raw / name
        if path.exists() and not self.options.get("refresh_metadata"):
            return json.loads(path.read_text(encoding="utf-8"))
        resp = self.http.request("POST", API, json=self._body(offset, page_max), headers={"Accept": "application/json"})
        if resp.status_code >= 400:
            raise HttpError(API, resp.status_code, resp.text[:300])
        data = resp.json()
        self.ctx.save_raw(name, json.dumps(data))
        return data

    def _pages(self) -> Iterator[list[dict[str, Any]]]:
        page_max = int(to_float(self.options.get("page_max")) or DEFAULT_PAGE_MAX)
        limit = int(to_float(self.options.get("pages")) or 0)
        offset, n = 0, 0
        total: int | None = None
        while total is None or offset < total:
            if limit and n >= limit:
                break
            data = self._page(offset, page_max)
            total = int((data.get("meta") or {}).get("total") or 0)
            hits = data.get("data") or []
            if not hits:
                break
            yield hits
            offset += len(hits)
            n += 1

    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    # ------------------------------------------------------------------------------------------- discover
    def discover(self) -> Iterable[Candidate]:
        for hits in self._pages():
            for hit in hits:
                cand = self._candidate(hit)
                if cand is not None:
                    yield cand

    def _candidate(self, hit: dict[str, Any]) -> Candidate | None:
        attrs = hit.get("attributes") or {}
        fid = str(attrs.get("fileIdentifier") or "")
        url = mp4_url(attrs)
        if not fid or not url:
            self._skip("no mp4 link")
            return None
        text = f"{attrs.get('title', '')} {attrs.get('description', '')}"
        extra: dict[str, Any] = {
            "cruise": cruise_of(fid),
            "dive": dive_of(fid),
            "locations": attrs.get("gcmdLocations") or [],
            "instruments": attrs.get("gcmdInstruments") or [],
            "description": attrs.get("description"),
            "maybe_not_underwater": bool(NOISY_RE.search(fid)),
        }
        if oerkey_url(attrs):
            extra["portal_key"] = oerkey_url(attrs)
        return Candidate(
            source=self.key,
            item_id=fid,
            media_type="video",
            media_url=url,
            origin_url=oerkey_url(attrs) or PORTAL,
            timestamp=attrs.get("beginDate"),
            ext="mp4",
            raw={"attrs": light_record(attrs), "text": text},
            extra=extra,
        )

    # ------------------------------------------------------------------------------------------- licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        text = str(cand.raw.get("text") or "")
        cruise = cand.extra.get("cruise", "")
        cruise_url = CRUISE_PAGE.format(cruise=cruise) if cruise else PORTAL
        if COPYRIGHT_RE.search(text):
            return make_licence(
                "copyright marked in the granule record", level="record", url=PORTAL, attribution=cand.item_id, tier="U"
            )
        cites = (cand.raw.get("attrs") or {}).get("citeAsStatements") or []
        attribution = (
            f"NOAA Ocean Exploration, {cruise.upper()} ROV video segment {cand.item_id} (NOAA NCEI video portal {PORTAL}). "
            f"Cite the cruise: see the cruise landing page under Documentation, {cruise_url}. "
            f"{' '.join(str(c) for c in cites[:1])}"
        ).strip()
        return make_licence(
            "US government work (NOAA), no licence stated; ISO accessLevel public",
            level="collection",
            url=cruise_url,
            attribution=attribution,
            tier="A",
        )

    # ------------------------------------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        attrs = cand.raw.get("attrs") or {}
        depth = depth_range_m(str(cand.raw.get("text") or ""))
        box = bbox_of(attrs)
        if box is None:
            return Geo.none(geo_source=GEO_SOURCE_NONE, depth_m=depth)
        min_lat, min_lon, max_lat, max_lon = box
        lat, lon = (min_lat + max_lat) / 2, (min_lon + max_lon) / 2
        unc = round(haversine_m(min_lat, min_lon, max_lat, max_lon) / 2, 1)
        return Geo(lat, lon, depth, "segment", GEO_SOURCE, True, unc)

    # ------------------------------------------------------------------------------------------- media
    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(url=cand.media_url, ext="mp4")

    # ------------------------------------------------------------------------------------------- estimate
    def estimate(self) -> dict[str, Any]:
        data = self._page(0, 1)
        return {"granules_total": int((data.get("meta") or {}).get("total") or 0), "note": "all formats in the project"}

