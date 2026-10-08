"""SQUIDLE+ / IMOS AUV Facility seafloor imagery (AUV Sirius, AUV Nimbus, ACFR AUV Holt), Australia.

IMOS (Integrated Marine Observing System) AUV Facility, operated by ACFR (University of Sydney): downward-looking
stereo-pair still images taken about 2 m above the seabed at 1-2 Hz, 69 campaigns, 906 dives, 7.60 M images (one camera
per pair; about 8-9 TB at full resolution), 2007-09 to 2023-10 around Australia (GBR, Coral Sea, Ningaloo, Scott Reef,
WA, SA, Tasmania, Victoria, NSW, Qld). SQUIDLE+ (https://squidle.org) only indexes the imagery; the files sit in the
public anonymous AWS bucket ``imos-data`` (ap-southeast-2), which this adapter reads directly (research/squidle_imos.md).
Images only, no video. The other SQUIDLE+ platforms (SOI ROV, CSIRO, RLS, IMAS, BOSS dropcams, ...) are not in the bucket
and have no licence in SQUIDLE+: they are tier U (SOI: excluded) and are not enumerated here.

Licence, tier B (CC BY 4.0), record level. SQUIDLE+ has no licence field. The AODN catalogue records
(https://catalogue-imos.aodn.org.au/geonetwork/srv/api/records/<uuid>/formatters/xml, read at run time and cached under
metadata/raw/aodn/) carry ``MD_LegalConstraints`` "Creative Commons Attribution 4.0 International License"
(http://creativecommons.org/licenses/by/4.0/): Sirius ``fe81b24e-...`` and Nimbus ``8dfa2b64-...`` (record level, one per
platform), the facility ``af5d0ff9-...`` for ACFR AUV Holt (GeographeBay201505, no platform record: collection level; the
facility record links the whole ``IMOS/AUV/`` prefix). Dive-level UUIDs of the CSVs are not in the catalogue (404), and
the campaign README ("AUV data may be reused, provided ... appropriately acknowledged") is older wording compatible with
CC BY. An NC / ND / research-only term in a record gives tier X, a record that cannot be read gives tier U (never an
upgrade). Attribution = the acknowledgement quoted in the record ("Data was sourced from Australia's Integrated Marine
Observing System (IMOS) ..."), the citation form the record asks for (IMOS <year>, <title>, <URL>, accessed <date>) and the
credit lines of the record (ACFR, University of Sydney, ...).

Geo, ``image`` precision, ``geo_inferred`` false, ``geo_uncertainty_m`` empty: every image row of the per-dive CSV
``IMOS/AUV/auv_viewer_data/csv_outputs/<campaign>/DATA_<campaign>_<dive>.csv`` has its own post-processed AUV navigation fix
(``latitude``, ``longitude``, WGS 84; no interpolation). ``depth_m`` = ``depth_sensor`` (vehicle / camera depth; seafloor
depth ``depth`` = depth_sensor + altitude is kept in ``extra.seafloor_depth_m``); values outside 0-11000 are dropped.
SQUIDLE+ records (``route=squidle``, ``/api/deployment/<id>/export`` or ``/api/pose``) follow the research recipe:
``pose.lat`` / ``pose.lon``, vehicle depth = ``pose.data.dep`` if present else ``pose.dep`` (older imports: vehicle depth,
2021 Sirius import: ``pose.dep`` is the seafloor), WMS ortho-mosaic poses are not samples, station-type platforms (BRUV,
dropcam, diver, RLS, or many images on one coordinate) are ``station`` precision with ``geo_inferred`` true.

How it works
    * ``discover`` reads only S3 ListObjectsV2 listings and the dive CSVs (0.06-4 MB each, ~330 B per image row), cached
      under metadata/raw/ (``s3/``, ``csv/<campaign>/``, ``aodn/``), so a re-run does not hit AWS again. Item ids are
      ``<campaign>/<dive>/<image_filename>`` (the same for both routes), stable across runs.
    * Per dive: the 2-line dive header and the column header are parsed with the ``csv`` module (header names are stripped,
      some files have ``" geospatial_lon_min"``); the second camera of a stereo pair (``*_AC16``, from about 2020 the CSV
      has ``_FC16`` and ``_AC16`` rows with identical coordinates) is dropped; frames with an altitude outside
      ``altitude_min``-``altitude_max`` (water column, descent, ascent) or without a usable fix are skipped; the rest is thinned
      to frames at least ``min_spacing_s`` apart (about 15 m along track, no footprint overlap). The platform comes from
      the dive header (``SIRIUS`` / ``NIMBUS``); GeographeBay201505 is ACFR AUV Holt (the header says SIRIUS).
    * Budget-friendly order (``order=spread``, default, any prefix of the stream covers many campaigns): round 0 takes ONE
      frame of every campaign (campaigns in a spread order: oldest, newest, middle, ...), then a weighted round robin over
      the campaigns with weights sqrt(estimated images). Inside a campaign the dives go round robin (centre first, then
      quarters, ...), inside a dive the thinned frames follow the same van der Corput order. Campaigns and CSVs are listed /
      read lazily, so a budget of 30 costs about 30 listings and 30 CSVs, not the 906.
    * Not done: dark-frame (JPEG size / luminance) filter (needs the image bytes), dedup against benthicnet / BENTHOZ-2015
      (same ``(campaign, dive, image_filename)`` key in ``extra``), non-IMOS SQUIDLE+ platforms (tier U / X).
    * Politeness: 0.25 s between requests to the two S3 hosts (S3 sends no rate limit; sequential), 1 s to squidle.org and the
      catalogue. Images are plain HTTPS GETs (resume with Range works); every file is checked for the JPEG magic number.
      Never use the ``data.acfr.usyd.edu.au`` copies (different bytes). Downloaded files are data and never executed.

Adapter options (``--opt key=value``; values are JSON or comma separated lists)
    campaigns         only these campaign codes, e.g. ``GBR200709,Apollo202309`` (default: all 69 in the bucket).
    from, to          ISO dates (``2015-01-01``): keep dives that start inside (the date is in the dive code ``rYYYYMMDD_...``).
    min_spacing_s     minimum time between kept frames of a dive (default 30; ``0`` keeps every frame).
    altitude_min, altitude_max  altitude window in metres (default 0.5 and 6; frames without altitude are dropped).
    frames_per_dive   at most this many frames per dive (default: all thinned frames).
    twins             ``drop`` (default: drop ``*_AC16``) or ``keep``.
    image             ``full_res`` (default) or ``thumbnail`` (453x341, cheap low-resolution pass).
    order             ``spread`` (default, see above) or ``table`` (campaign by campaign, dives in name order).
    route             ``s3`` (default) or ``squidle``: with ``deployments=<ids>`` (SQUIDLE+ deployment ids) the poses come from
                      ``/api/deployment/<id>/export`` (background task, one at a time); licence B only for IMOS AUV images in the
                      bucket, tier U otherwise (dropped by default).
    accessed          date written in the citation (default: today, UTC).
    refresh_metadata  core option: re-download cached metadata.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
import re
import time
import xml.etree.ElementTree as ET
from collections import deque
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import quote, urlencode

from ..core.geo import to_float
from ..core.http import HttpError
from ..core.licence import classify, make_licence, most_specific
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

S3_LIST = "https://imos-data.s3-ap-southeast-2.amazonaws.com"
S3_MEDIA = "https://s3-ap-southeast-2.amazonaws.com/imos-data"
S3_HOSTS = ("imos-data.s3-ap-southeast-2.amazonaws.com", "s3-ap-southeast-2.amazonaws.com")
AUV_ROOT = "IMOS/AUV/"
CSV_PREFIX = AUV_ROOT + "auv_viewer_data/csv_outputs/"
CAMPAIGN_URL = S3_LIST + "/" + AUV_ROOT + "{campaign}/"
IMAGE_URL = S3_MEDIA + "/" + AUV_ROOT + "auv_viewer_data/images/{campaign}/{dive}/{kind}/{name}.jpg"
CSV_URL = S3_MEDIA + "/" + CSV_PREFIX + "{campaign}/DATA_{campaign}_{dive}.csv"
CAMPAIGN_RE = re.compile(r"^[A-Za-z_]+\d{6}[A-Za-z]*$")  # GBR200709, WA_SW_202103, TasVic201602SS (not seqld.csv.manifest)
IMOS_IMAGE_RE = re.compile(r"/imos-data/IMOS/AUV/auv_viewer_data/images/(?P<campaign>[^/]+)/(?P<dive>[^/]+)/(?P<kind>full_res|thumbnails)/(?P<name>[^/]+?)\.jpg$")

AODN_XML = "https://catalogue-imos.aodn.org.au/geonetwork/srv/api/records/{uuid}/formatters/xml"
AODN_PAGE = "https://catalogue-imos.aodn.org.au/geonetwork/srv/eng/catalog.search#/metadata/{uuid}"
FACILITY = "af5d0ff9-bb9c-4b7c-a63c-854a630b6984"  # IMOS - Autonomous Underwater Vehicles Facility (links IMOS/AUV/)
PLATFORM_RECORDS = {"IMOS AUV Sirius": "fe81b24e-adee-4c77-a8e1-e8a77cfd3dff", "IMOS AUV Nimbus": "8dfa2b64-4eed-491c-ba5e-645ea9409d4d"}
PLATFORM_NAMES = {"SIRIUS": "IMOS AUV Sirius", "NIMBUS": "IMOS AUV Nimbus", "HOLT": "ACFR AUV Holt"}
CAMPAIGN_PLATFORM = {"GeographeBay201505": "ACFR AUV Holt"}  # the dive header says SIRIUS, SQUIDLE+ and the facility say Holt
SHORT_PLATFORM = {"IMOS AUV Sirius": "Sirius", "IMOS AUV Nimbus": "Nimbus", "ACFR AUV Holt": "Holt"}
DEFAULT_ACK = (
    "Data was sourced from Australia’s Integrated Marine Observing System (IMOS) – IMOS is enabled by the "
    "National Collaborative Research Infrastructure strategy (NCRIS)."
)
CC_BY_URL = "http://creativecommons.org/licenses/by/4.0/"

SQUIDLE = "https://squidle.org"
SQ_DEPLOYMENT = SQUIDLE + "/api/deployment/{id}"
SQ_EXPORT_COLUMNS = [
    "id", "key", "path_best", "timestamp_start", "pose.timestamp", "pose.lat", "pose.lon", "pose.dep", "pose.alt", "pose.data",
    "media_type.name", "is_valid", "deployment.key", "deployment.campaign.key",
]  # fmt: skip
SQ_EXPORT_F = '{"operations":[{"module":"pandas","method":"json_normalize"}]}'
BROWSE = "https://squidle.org/"

# estimate(): provider totals of the research note (SQUIDLE+ deployment.media_count summed 2026-10-07, 69 campaigns)
RESEARCH_TOTALS = {"campaigns": 69, "dives": 906, "images_squidle": 7_595_565, "full_res_tb_estimate": "8-9 (+-30 %)"}
ROW_BYTES = 330  # bytes per image row of the dive CSVs (research)
ORDERS = ("spread", "table")
ROUTES = ("s3", "squidle")
DEFAULT_MIN_SPACING_S = 30.0
DEFAULT_ALT_MIN, DEFAULT_ALT_MAX = 0.5, 6.0
MAX_DEPTH_M = 11000.0
STATION_RE = re.compile(r"BRUV|Dropcam|Drop Camera|DIVER|Diver")
JPEG_MAGIC = b"\xff\xd8\xff"


# ----------------------------------------------------------------------------------------------- pure helpers
def _refuse_entities(text: str) -> None:
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise ValueError("XML with a DOCTYPE / entity declaration is refused")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _texts(el: ET.Element) -> list[str]:
    return [t.strip() for e in el.iter() if _local(e.tag) in ("CharacterString", "URL") and (t := e.text) and t.strip()]


def parse_listing(xml: str) -> tuple[list[str], list[tuple[str, int]], str | None]:
    """``(common prefixes, [(key, size)], next continuation token)`` of an S3 ListObjectsV2 answer."""
    _refuse_entities(xml)
    root = ET.fromstring(xml)
    prefixes: list[str] = []
    keys: list[tuple[str, int]] = []
    token: str | None = None
    truncated = False
    for el in root:
        tag = _local(el.tag)
        if tag == "CommonPrefixes":
            prefixes += [(c.text or "") for c in el if _local(c.tag) == "Prefix"]
        elif tag == "Contents":
            d = {_local(c.tag): (c.text or "") for c in el}
            keys.append((d.get("Key", ""), int(d.get("Size") or 0)))
        elif tag == "IsTruncated":
            truncated = (el.text or "").strip().lower() == "true"
        elif tag == "NextContinuationToken":
            token = el.text
    return prefixes, keys, (token if truncated else None)


def parse_aodn_record(xml: str) -> dict[str, Any]:
    """What the licence needs from an AODN ISO 19115-3 record.

    ``{licences: [{name, url, texts}], ack, credits}``: one ``licences`` entry per ``MD_LegalConstraints`` (``name``
    is the title of its ``reference``, ``url`` its licence link, ``texts`` the ``otherConstraints`` / ``useLimitation`` /
    ``accessConstraints`` strings), ``ack`` the quoted acknowledgement and ``credits`` the credit lines of the record.
    """
    _refuse_entities(xml)
    root = ET.fromstring(xml)
    out: dict[str, Any] = {"licences": [], "ack": "", "credits": []}
    for el in root.iter():
        name = _local(el.tag)
        if name == "MD_LegalConstraints":
            lic: dict[str, Any] = {"name": "", "url": "", "texts": []}
            for child in el:
                cname = _local(child.tag)
                if cname == "reference":
                    for t in child.iter():
                        if _local(t.tag) == "title" and (txt := _texts(t)) and not lic["name"]:
                            lic["name"] = txt[0]
                    urls = [u for u in _texts(child) if u.startswith("http") and "licen" in u.lower() and not u.endswith(".png")]
                    cc = [u for u in urls if "/licenses/" in u]
                    lic["url"] = (cc or urls or [""])[0]
                elif cname in ("otherConstraints", "useLimitation", "accessConstraints", "useConstraints"):
                    lic["texts"] += _texts(child)
            out["licences"].append(lic)
        elif name == "credit":
            out["credits"] += _texts(el)
    for lic in out["licences"]:
        for t in lic["texts"]:
            m = re.search(r'"(Data was sourced from[^"]+)"', t)
            if m:
                out["ack"] = m.group(1).strip()
    return out


def is_campaign(name: str) -> bool:
    return bool(CAMPAIGN_RE.match(name))


def dive_date(dive: str) -> str | None:
    """ISO date of a dive code ``rYYYYMMDD_hhmmss_name``, or None."""
    m = re.match(r"^[ri]?(\d{4})(\d{2})(\d{2})_\d{6}", dive)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
    except ValueError:
        return None


def parse_stamp(value: object) -> float | None:
    """Epoch seconds of ``YYYYMMDDThhmmssZ`` (the CSV ``time`` column) or an ISO timestamp, else None."""
    s = str(value or "").strip()
    m = re.match(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z?$", s)
    if m:
        try:
            return datetime(*(int(g) for g in m.groups()), tzinfo=timezone.utc).timestamp()
        except ValueError:
            return None
    from ..core.geo import parse_time

    return parse_time(s)


def name_stamp(name: str) -> float | None:
    """Epoch seconds (with milliseconds) of ``PR_20150526_024829_369_FC16``; None for other names."""
    m = re.search(r"_(\d{8})_(\d{6})_(\d{3})(?:_|$)", name)
    if not m:
        return None
    try:
        d = datetime.strptime(m[1] + m[2], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return d.timestamp() + int(m[3]) / 1000.0


def iso_z(epoch: float | None) -> str | None:
    return None if epoch is None else datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def camera_of(name: str) -> str:
    m = re.search(r"_([A-Za-z]{2}\d{2})$", name)
    return m[1] if m else ""


@dataclass
class DiveCsv:
    header: dict[str, str]  # the 2-line dive header (names stripped)
    rows: list[dict[str, str]]  # image rows (names and values stripped)


def parse_dive_csv(text: str) -> DiveCsv:
    """Parse an IMOS AUV ``DATA_<campaign>_<dive>.csv``: 2-line dive header, column header, one row per image."""
    records = list(csv.reader(io.StringIO(text.lstrip("﻿"))))
    idx = next((i for i, r in enumerate(records) if "image_filename" in [c.strip() for c in r]), None)
    if idx is None:
        raise ValueError("no 'image_filename' column header in the dive CSV")
    header: dict[str, str] = {}
    if idx >= 2:
        header = {k.strip(): v.strip() for k, v in zip(records[idx - 2], records[idx - 1])}
    cols = [c.strip() for c in records[idx]]
    rows = [{c: v.strip() for c, v in zip(cols, r)} for r in records[idx + 1 :] if any(x.strip() for x in r)]
    return DiveCsv(header, rows)


@dataclass
class Frame:
    """One image of a dive after filtering (``rec`` is what ``resolve_geo`` reads)."""

    name: str
    t: float
    rec: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)


@lru_cache(maxsize=256)
def pick_order(n: int) -> tuple[int, ...]:
    """0..n-1 with the centre first, then van der Corput fractions (1/4, 3/4, 1/8, ...): any prefix is evenly spread."""
    out: list[int] = []
    seen: set[int] = set()
    m = 1
    while len(out) < n and m <= 64 * n + 64:
        f, x, w = 0.0, m, 0.5
        while x:
            f += (x & 1) * w
            x >>= 1
            w /= 2
        i = min(n - 1, int(f * n))
        if i not in seen:
            seen.add(i)
            out.append(i)
        m += 1
    out.extend(i for i in range(n) if i not in seen)
    return tuple(out)


def spread_order(n: int) -> list[int]:
    """0..n-1 as first, last, then repeated midpoints."""
    if n <= 2:
        return list(range(n))
    out = [0, n - 1]
    queue = deque([(0, n - 1)])
    while queue:
        lo, hi = queue.popleft()
        mid = (lo + hi) // 2
        if mid in (lo, hi):
            continue
        out.append(mid)
        queue.append((lo, mid))
        queue.append((mid, hi))
    return out


def thin(frames: list[Frame], min_spacing_s: float) -> list[Frame]:
    """Frames sorted by time, at least ``min_spacing_s`` apart (the first of each stretch wins)."""
    out: list[Frame] = []
    last = -math.inf
    for f in sorted(frames, key=lambda f: (f.t, f.name)):
        if f.t - last >= min_spacing_s:
            out.append(f)
            last = f.t
    return out


def _depth(value: object) -> float | None:
    """Vehicle depth in metres: ``0 <= v <= 11000`` (negative values such as -1000.6 or -1.1 are invalid), else None."""
    v = to_float(value)
    if v is None or not 0.0 <= v <= MAX_DEPTH_M:
        return None
    return round(v, 2)


IMOS_CSV_SOURCE = "IMOS AUV csv_outputs/{campaign}/DATA_{campaign}_{dive}.csv: latitude,longitude (WGS84); depth_m=depth_sensor"
SQUIDLE_SOURCE = "SQUIDLE+ /api/pose lat,lon (WGS84); depth_m=pose.data.dep|pose.dep (vehicle depth)"


def geo_for_record(rec: dict[str, Any]) -> Geo | None:
    """The research ``resolve_geo`` recipe. ``None`` means the record is not a sample (WMS ortho-mosaic, not an image, invalid).

    ``rec["src"]`` is ``imos_csv`` (keys ``campaign_code``, ``dive_code``, ``latitude``, ``longitude``, ``depth_sensor``) or
    ``squidle`` (keys ``lat``, ``lon``, ``dep``, ``data_dep``, ``platform_name``, ``media_type``, ``is_valid``, ``media_key``,
    ``deployment_key``, ``path_best_thm``, ``n_img``, ``n_xy``).
    """
    src = rec.get("src")
    if src == "imos_csv":
        lat, lon = to_float(rec.get("latitude")), to_float(rec.get("longitude"))
        depth = _depth(rec.get("depth_sensor"))
        source = IMOS_CSV_SOURCE.format(campaign=rec.get("campaign_code", "?"), dive=rec.get("dive_code", "?"))
        platform = str(rec.get("platform_name") or "")
    elif src == "squidle":
        mt = rec.get("media_type")
        if mt not in (None, "", "image"):
            return None
        if rec.get("is_valid") is False or str(rec.get("is_valid")).lower() == "false":
            return None
        thm = str(rec.get("path_best_thm") or "")
        if (rec.get("media_key") and rec.get("media_key") == rec.get("deployment_key")) or "/api/media/" in thm:
            return None  # the WMS ortho-mosaic of the deployment, not a photo
        lat, lon = to_float(rec.get("lat")), to_float(rec.get("lon"))
        dd = to_float(rec.get("data_dep"))
        depth = _depth(dd if dd is not None else rec.get("dep"))
        source = SQUIDLE_SOURCE
        platform = str(rec.get("platform_name") or "")
    else:
        raise ValueError(f"unknown record source {src!r}")
    if lat is None or lon is None or abs(lat) > 90 or abs(lon) > 180 or (lat == 0 and lon == 0):
        return Geo.none(geo_source=source)
    n_img, n_xy = rec.get("n_img") or 0, rec.get("n_xy") or 0
    if platform in SHORT_PLATFORM or re.search(r"\bAUV\b|ROV|[Tt]owed", platform) and not STATION_RE.search(platform):
        return Geo(lat, lon, depth, "image", source, False, None)
    if "RLS" in platform:
        return Geo(lat, lon, depth, "station", source, True, 1000.0)
    if STATION_RE.search(platform) or (n_img > 1 and n_xy == 1):
        unc = 500.0 if re.search(r"DIVER|Diver", platform) else 100.0 if re.search(r"BRUV|Dropcam|Drop Camera", platform) else 500.0
        return Geo(lat, lon, depth, "station", source, True, unc)
    return Geo(lat, lon, depth, "image", source, False, None)


# ------------------------------------------------------------------------------------------------ the adapter
@dataclass
class _Dive:
    campaign: str
    dive: str
    key: str
    size: int


@dataclass
class _Stream:
    """One campaign: lazy listing + lazy CSV reads, yields candidates (round robin over dives)."""

    campaign: str
    gen: Iterator[Candidate]
    served: int = 0


@register
class SquidleImos(Adapter):
    key = "squidle_imos"
    name = "SQUIDLE+ / IMOS AUV Facility imagery (AUV Sirius, Nimbus, Holt), Australia"
    homepage = "https://squidle.org"
    citation = (
        "IMOS AUV Facility (ACFR, The University of Sydney), IMOS - Autonomous Underwater Vehicles, "
        "http://data.aodn.org.au/?prefix=IMOS/AUV/ (AODN record af5d0ff9-bb9c-4b7c-a63c-854a630b6984), CC BY 4.0. "
        "Imagery indexed by SQUIDLE+: Friedman A., Monk J., Pizarro O., et al. (2026), Front. Mar. Sci. 12:1677103, "
        "https://doi.org/10.3389/fmars.2025.1677103."
    )
    media_types = ("image",)
    env_vars: tuple[str, ...] = ()
    manual_steps = (
        "None for the IMOS AUV part (anonymous HTTPS on the public AWS bucket imos-data). Optional: a free SQUIDLE+ account "
        "and API token (X-Auth-Token) would enable /api/media/export; it is not needed. Optional: ask IMOS / ACFR for the "
        "licence of the campaigns served only from data.acfr.usyd.edu.au (Hawaii201801, TasFracture202106, PortPhillipBay202301): "
        "they are not in the bucket and are not read here."
    )
    host_intervals = {h: 0.25 for h in S3_HOSTS}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._records: dict[str, dict[str, Any] | None] = {}
        self._campaign_cache: list[str] | None = None
        self._weights: dict[str, float] = {}
        self._accessed = str(self.options.get("accessed") or datetime.now(timezone.utc).date().isoformat())
        self.skipped: dict[str, int] = {}

    # ------------------------------------------------------------------------------------------- options
    def _opt_list(self, name: str) -> list[str] | None:
        v = self.options.get(name)
        if v in (None, "", "all"):
            return None
        if isinstance(v, str):
            v = [x.strip() for x in v.strip("[]").replace('"', "").split(",") if x.strip()]
        return [str(x) for x in (v if isinstance(v, (list, tuple)) else [v])]

    def _opt_float(self, name: str, default: float) -> float:
        v = to_float(self.options.get(name))
        return default if v is None else v

    @property
    def min_spacing_s(self) -> float:
        return max(0.0, self._opt_float("min_spacing_s", DEFAULT_MIN_SPACING_S))

    # -------------------------------------------------------------------------------------- S3 listings
    def _list(self, prefix: str, name: str, delimiter: bool) -> tuple[list[str], list[tuple[str, int]]]:
        prefixes: list[str] = []
        keys: list[tuple[str, int]] = []
        token: str | None = None
        for page in range(1, 200):
            q = {"list-type": "2", "prefix": prefix}
            if delimiter:
                q["delimiter"] = "/"
            if token:
                q["continuation-token"] = token
            url = f"{S3_LIST}/?{urlencode(q, quote_via=quote)}"
            text = self.ctx.cached_text(url, f"s3/{name}_{page}.xml")
            p, k, token = parse_listing(text)
            prefixes += p
            keys += k
            if not token:
                break
        return prefixes, keys

    def campaigns(self) -> list[str]:
        """Campaign codes under csv_outputs/ (sorted by year-month, name)."""
        if self._campaign_cache is None:
            prefixes, _ = self._list(CSV_PREFIX, "campaigns", delimiter=True)
            names = sorted({p[len(CSV_PREFIX) :].strip("/") for p in prefixes if p.startswith(CSV_PREFIX)})
            names = [n for n in names if is_campaign(n)]
            self._campaign_cache = sorted(names, key=lambda n: (re.search(r"(\d{6})", n)[1], n))
        wanted = self._opt_list("campaigns")
        if wanted is None:
            return list(self._campaign_cache)
        known = set(self._campaign_cache)
        for w in wanted:
            if w not in known:
                log.warning("squidle_imos: campaign %s is not in the bucket listing", w)
        return [c for c in self._campaign_cache if c in wanted]

    def dives(self, campaign: str) -> list[_Dive]:
        _, keys = self._list(f"{CSV_PREFIX}{campaign}/", f"dives_{campaign}", delimiter=False)
        head, tail = f"{CSV_PREFIX}{campaign}/DATA_{campaign}_", ".csv"
        out = [_Dive(campaign, k[len(head) : -len(tail)], k, size) for k, size in keys if k.startswith(head) and k.endswith(tail)]
        lo, hi = self.options.get("from"), self.options.get("to")
        if lo or hi:
            out = [d for d in out if (dd := dive_date(d.dive)) is None or ((not lo or dd >= str(lo)) and (not hi or dd <= str(hi)))]
        return sorted(out, key=lambda d: d.dive)

    # ------------------------------------------------------------------------------------------ the CSVs
    def _read_dive(self, d: _Dive) -> list[Candidate]:
        url = f"{S3_MEDIA}/{d.key}"
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", d.dive)
        text = self.ctx.cached_text(url, f"csv/{d.campaign}/{safe}.csv")
        return self.candidates_from_csv(text, d.campaign, d.dive)

    def candidates_from_csv(self, text: str, campaign: str, dive: str) -> list[Candidate]:
        """Candidates of one dive CSV after the camera / altitude / fix filters and the time thinning."""
        parsed = parse_dive_csv(text)
        pcode = (parsed.header.get("platform_code") or "").upper()
        platform = CAMPAIGN_PLATFORM.get(campaign) or PLATFORM_NAMES.get(pcode) or (f"IMOS AUV {pcode.title()}" if pcode else "IMOS AUV")
        a_min = self._opt_float("altitude_min", DEFAULT_ALT_MIN)
        a_max = self._opt_float("altitude_max", DEFAULT_ALT_MAX)
        drop_twins = str(self.options.get("twins", "drop")).lower() != "keep"
        seen: set[str] = set()
        rows = []
        for r in parsed.rows:
            name = r.get("image_filename", "")
            if not name or name in seen or (drop_twins and name.endswith("_AC16")):
                continue
            seen.add(name)
            rows.append(r)
        n_img = len(rows)
        n_xy = len({(r.get("latitude"), r.get("longitude")) for r in rows})
        frames: list[Frame] = []
        for r in rows:
            name = r["image_filename"]
            lat, lon = to_float(r.get("latitude")), to_float(r.get("longitude"))
            if lat is None or lon is None or (lat == 0 and lon == 0):
                self._skip("no_fix")
                continue
            alt = to_float(r.get("altitude_sensor"))
            if alt is None or not a_min <= alt <= a_max:
                self._skip("altitude")
                continue
            t = name_stamp(name) or parse_stamp(r.get("time"))
            if t is None:
                self._skip("no_time")
                continue
            rec = {
                "src": "imos_csv", "campaign_code": campaign, "dive_code": dive, "image_filename": name,
                "latitude": r.get("latitude"), "longitude": r.get("longitude"), "depth_sensor": r.get("depth_sensor"),
                "altitude_sensor": r.get("altitude_sensor"), "depth": r.get("depth"), "time": r.get("time"),
                "platform_name": platform, "media_type": "image", "n_img": n_img, "n_xy": n_xy,
            }  # fmt: skip
            frames.append(Frame(name, t, rec, {"time": r.get("time"), "image_width_m": to_float(r.get("image_width"))}))
        kept = thin(frames, self.min_spacing_s)
        per = self.options.get("frames_per_dive")
        limit = None if per in (None, "", "all") else max(1, int(per))
        order = pick_order(len(kept))
        picked = [kept[i] for i in (order if limit is None else order[:limit])]
        return [self._candidate_s3(f, campaign, dive, platform) for f in picked]

    def _skip(self, why: str) -> None:
        self.skipped[why] = self.skipped.get(why, 0) + 1

    def _candidate_s3(self, f: Frame, campaign: str, dive: str, platform: str) -> Candidate:
        kind = "thumbnails" if str(self.options.get("image", "full_res")).lower().startswith("thumb") else "full_res"
        url = IMAGE_URL.format(campaign=campaign, dive=dive, kind=kind, name=f.name)
        seafloor = to_float(f.rec.get("depth"))
        alt = to_float(f.rec.get("altitude_sensor"))
        return Candidate(
            source=self.key,
            item_id=f"{campaign}/{dive}/{f.name}",
            media_type="image",
            media_url=url,
            origin_url=CSV_URL.format(campaign=campaign, dive=dive),
            timestamp=iso_z(parse_stamp(f.rec.get("time")) or f.t),
            ext="jpg",
            raw=f.rec,
            extra={
                "campaign": campaign, "dive": dive, "image_filename": f.name, "platform": platform, "camera": camera_of(f.name),
                "altitude_m": alt, "seafloor_depth_m": None if seafloor is None else round(seafloor, 2),
                "footprint_width_m": f.extra.get("image_width_m"),
                "thumbnail_url": IMAGE_URL.format(campaign=campaign, dive=dive, kind="thumbnails", name=f.name),
                "aodn_record": self._record_uuid(platform), "dedup_key": f"{campaign}/{dive}/{f.name}",
            },
        )  # fmt: skip

    # ------------------------------------------------------------------------------------------ discover
    def discover(self) -> Iterable[Candidate]:
        route = str(self.options.get("route", "s3")).lower()
        if route not in ROUTES:
            raise ValueError(f"route must be one of {ROUTES}")
        if route == "squidle":
            yield from self._discover_squidle()
            return
        order = str(self.options.get("order", "spread")).lower()
        if order not in ORDERS:
            raise ValueError(f"order must be one of {ORDERS}")
        camps = self.campaigns()
        if order == "table":
            for c in camps:
                yield from self._campaign_stream(c)
            return
        streams = [_Stream(camps[i], self._campaign_stream(camps[i])) for i in spread_order(len(camps))]
        # round 0: one frame of every campaign
        live: list[_Stream] = []
        for s in streams:
            cand = next(s.gen, None)
            if cand is None:
                continue
            s.served = 1
            live.append(s)
            yield cand
        # then a weighted round robin: always the campaign with the smallest (served + 1) / weight
        while live:
            best = min(range(len(live)), key=lambda i: ((live[i].served + 1) / max(self._weights.get(live[i].campaign, 1.0), 1e-9), i))
            cand = next(live[best].gen, None)
            if cand is None:
                live.pop(best)
                continue
            live[best].served += 1
            yield cand

    def _campaign_stream(self, campaign: str) -> Iterator[Candidate]:
        """Candidates of one campaign: round robin over its dives (centre first), CSVs read when first needed."""
        dives = self.dives(campaign)
        est = sum(d.size for d in dives) / ROW_BYTES
        self._weights[campaign] = math.sqrt(max(est, 1.0))
        per_dive: dict[int, list[Candidate]] = {}
        order = pick_order(len(dives))
        rnd = 0
        while True:
            more = False
            for i in order:
                if i not in per_dive:
                    try:
                        per_dive[i] = self._read_dive(dives[i])
                    except (HttpError, ValueError, csv.Error) as exc:
                        self.ctx.fail(f"{campaign}/{dives[i].dive}", "dive_csv", f"{type(exc).__name__}: {exc}", url=dives[i].key)
                        per_dive[i] = []
                if rnd < len(per_dive[i]):
                    more = True
                    yield per_dive[i][rnd]
            if not more:
                return
            rnd += 1

    # --------------------------------------------------------------------------------------------- estimate
    def estimate(self) -> dict[str, Any]:
        n = len(self.campaigns())
        return {
            "campaigns_in_bucket": n,
            "images_squidle_research": RESEARCH_TOTALS["images_squidle"],
            "dives_research": RESEARCH_TOTALS["dives"],
            "full_res_tb_research": RESEARCH_TOTALS["full_res_tb_estimate"],
        }

    # ------------------------------------------------------------------------------------------- licence
    @staticmethod
    def _record_uuid(platform: str) -> str:
        return PLATFORM_RECORDS.get(platform, FACILITY)

    def _cached_utf8(self, url: str, name: str) -> str:
        """Like ``ctx.cached_text`` but decoded as UTF-8 (the catalogue sends XML without a charset header)."""
        path = self.ctx.layout.raw / name
        if path.exists() and not self.options.get("refresh_metadata"):
            return path.read_text(encoding="utf-8")
        text = self.http.get(url).content.decode("utf-8", errors="replace")
        self.ctx.save_raw(name, text)
        return text

    def _record(self, uuid: str) -> dict[str, Any] | None:
        """The parsed AODN record (cached under metadata/raw/aodn/), or None when it cannot be read."""
        if uuid not in self._records:
            try:
                self._records[uuid] = parse_aodn_record(self._cached_utf8(AODN_XML.format(uuid=uuid), f"aodn/{uuid}.xml"))
            except (HttpError, ValueError, ET.ParseError) as exc:
                self.ctx.fail(uuid, "licence_record", f"{type(exc).__name__}: {exc}", url=AODN_XML.format(uuid=uuid))
                self._records[uuid] = None
        return self._records[uuid]

    @staticmethod
    def _licence_of(rec: dict[str, Any] | None) -> tuple[str | None, str | None, str]:
        """``(licence string, url, tier)`` of a record's legal constraints, or ``(None, None, 'U')`` when it states none."""
        if not rec or not rec["licences"]:
            return None, None, "U"
        tiers: list[str] = []
        lic = None
        for item in rec["licences"]:
            text = " ".join(x for x in (item["name"], item["url"]) if x)
            if not text:
                continue
            tier = classify(text)
            if classify(" ".join(item["texts"])) == "X":
                tier = "X"
            tiers.append(tier)
            lic = lic or item
        if not lic:
            return None, None, "U"
        known = [t for t in tiers if t != "U"]
        tier = "X" if "X" in tiers else (known[0] if known and len(set(known)) == 1 else "U")
        name = lic["name"]
        if "creativecommons.org/licenses/by/4.0" in (lic["url"] or "") and tier == "B":
            name = "CC-BY-4.0"
        return name, lic["url"] or None, tier

    def _imos_licence(self, platform: str, campaign: str) -> Licence:
        plat_uuid = PLATFORM_RECORDS.get(platform)
        plat = self._record(plat_uuid) if plat_uuid else None
        fac = self._record(FACILITY)
        p_name, _, _ = self._licence_of(plat)
        f_name, _, _ = self._licence_of(fac)
        level, _ = most_specific(("record", p_name), ("collection", f_name))
        src, uuid = (plat, plat_uuid) if level == "record" else (fac, FACILITY)
        name, url, tier = self._licence_of(src)
        if level == "unknown" or not name:
            return make_licence(None, level="unknown", url=None, attribution=self._attribution(campaign, platform, None), tier="U")
        return make_licence(name, level=level, url=url or CC_BY_URL, attribution=self._attribution(campaign, platform, src), tier=tier)

    def _attribution(self, campaign: str, platform: str, rec: dict[str, Any] | None) -> str:
        fac = self._record(FACILITY) or {}
        ack = (rec or {}).get("ack") or fac.get("ack") or DEFAULT_ACK
        credits = [c for c in ((rec or {}).get("credits") or fac.get("credits") or []) if "Integrated Marine Observing System" not in c]
        short = SHORT_PLATFORM.get(platform, platform.replace("IMOS ", ""))
        year = self._accessed[:4]
        parts = [
            ack,
            f"IMOS {year}, IMOS - Autonomous Underwater Vehicles - AUV {short} (campaign {campaign}), "
            f"{CAMPAIGN_URL.format(campaign=campaign)}, accessed {self._accessed}.",
        ]
        if credits:
            parts.append("Credit: " + "; ".join(credits) + ".")
        return " ".join(parts)

    def resolve_licence(self, cand: Candidate) -> Licence:
        platform = str(cand.extra.get("platform") or cand.raw.get("platform_name") or "")
        campaign = str(cand.extra.get("campaign") or cand.raw.get("campaign_code") or "")
        if cand.extra.get("licence_scope") == "other":
            return make_licence(
                None, level="unknown", url=None, tier="U",
                attribution=f"SQUIDLE+ platform {platform or 'unknown'}: no licence is published in SQUIDLE+ or was read at the custodian.",
            )  # fmt: skip
        return self._imos_licence(platform or "IMOS AUV", campaign)

    # ---------------------------------------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        geo = geo_for_record(cand.raw)
        if geo is None:
            return Geo.none(geo_source="SQUIDLE+ record is not a photo (WMS mosaic / not an image / invalid)")
        return geo

    # ------------------------------------------------------------------------------------------- media
    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(url=cand.media_url, ext="jpg")

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        n, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)
        with open(dest, "rb") as fh:
            head = fh.read(3)
        if head != JPEG_MAGIC:
            dest.unlink(missing_ok=True)
            raise HttpError(ref.url, None, f"not a JPEG (starts with {head!r})")
        return n, sha

    # ------------------------------------------------------------------------------------ squidle route
    def _discover_squidle(self) -> Iterator[Candidate]:
        ids = self._opt_list("deployments")
        if not ids:
            raise ValueError("route=squidle needs deployments=<SQUIDLE+ deployment ids>, e.g. deployments=213,22")
        streams: list[Iterator[Candidate]] = [self._deployment_candidates(int(i)) for i in ids]
        live = list(streams)
        while live:  # round robin over the deployments
            for s in list(live):
                cand = next(s, None)
                if cand is None:
                    live.remove(s)
                else:
                    yield cand

    def _deployment_candidates(self, dep_id: int) -> Iterator[Candidate]:
        try:
            meta = self.ctx.cached_json(SQ_DEPLOYMENT.format(id=dep_id), f"squidle/deployment_{dep_id}.json")
            text = self._squidle_export(dep_id)
        except (HttpError, ValueError, RuntimeError) as exc:
            self.ctx.fail(f"deployment/{dep_id}", "squidle_export", f"{type(exc).__name__}: {exc}")
            return
        platform = (meta.get("platform") or {}).get("name") or ""
        yield from self.candidates_from_export(text, platform, dep_id)

    def _squidle_export(self, dep_id: int) -> str:
        name = f"squidle/export_{dep_id}.csv"
        path = self.ctx.layout.raw / name
        if path.exists() and not self.options.get("refresh_metadata"):
            return path.read_text(encoding="utf-8")
        q = urlencode(
            {"template": "dataframe.csv", "disposition": "inline", "f": SQ_EXPORT_F, "include_columns": json.dumps(SQ_EXPORT_COLUMNS)},
            quote_via=quote,
        )
        resp = self.http.get(f"{SQUIDLE}/api/deployment/{dep_id}/export?{q}", headers={"Accept": "application/json"})
        if resp.status_code == 202:
            task = resp.json()["task_id"]
            deadline = time.monotonic() + float(self.options.get("export_timeout_s", 900))
            while True:
                st = self.http.get(f"{SQUIDLE}/task/{task}", headers={"Accept": "application/json"}).json()
                if st.get("result_available"):
                    break
                if st.get("status") in ("failed", "error") or time.monotonic() > deadline:
                    raise RuntimeError(f"SQUIDLE+ export task {task} did not finish: {str(st)[:200]}")
                time.sleep(3.0)
            text = self.http.get_text(f"{SQUIDLE}/task/{task}/result")
        else:
            text = resp.text
        self.ctx.save_raw(name, text)
        return text

    def candidates_from_export(self, text: str, platform: str, dep_id: int | str | None = None) -> list[Candidate]:
        """Candidates of a SQUIDLE+ deployment export CSV (``dataframe.csv`` of ``json_normalize``), thinned like the S3 route."""
        rows = list(csv.DictReader(io.StringIO(text)))
        imgs = [r for r in rows if (r.get("media_type.name") or "image") == "image" and str(r.get("is_valid", "True")).lower() != "false"]
        n_img = len(imgs)
        n_xy = len({(r.get("pose.lat"), r.get("pose.lon")) for r in imgs})
        a_min = self._opt_float("altitude_min", DEFAULT_ALT_MIN)
        a_max = self._opt_float("altitude_max", DEFAULT_ALT_MAX)
        station = geo_for_record({"src": "squidle", "lat": 1, "lon": 1, "platform_name": platform, "n_img": n_img, "n_xy": n_xy})
        frames: list[Frame] = []
        for r in imgs:
            alt = to_float(r.get("pose.alt"))
            if station and station.geo_precision == "image" and (alt is None or not a_min <= alt <= a_max):
                self._skip("altitude")
                continue
            t = parse_stamp(r.get("pose.timestamp")) or parse_stamp(r.get("timestamp_start")) or name_stamp(r.get("key") or "") or 0.0
            rec = {
                "src": "squidle", "lat": r.get("pose.lat"), "lon": r.get("pose.lon"), "dep": r.get("pose.dep"),
                "data_dep": r.get("pose.data.dep"), "alt": r.get("pose.alt"), "platform_name": platform,
                "media_type": r.get("media_type.name") or "image", "is_valid": True, "media_key": r.get("key"),
                "deployment_key": r.get("deployment.key"), "campaign_key": r.get("deployment.campaign.key"),
                "path_best": r.get("path_best"), "n_img": n_img, "n_xy": n_xy,
            }  # fmt: skip
            frames.append(Frame(r.get("key") or "", t, rec, {"id": r.get("id")}))
        # station platforms (one pose for many views) are not thinned by time: every view is kept, in order
        kept = frames if (station and station.geo_precision == "station") else thin(frames, self.min_spacing_s)
        order = pick_order(len(kept))
        out = []
        for i in order:
            c = self._candidate_squidle(kept[i], platform, dep_id)
            if c:
                out.append(c)
        return out

    def _candidate_squidle(self, f: Frame, platform: str, dep_id: int | str | None) -> Candidate | None:
        rec = f.rec
        url = rec.get("path_best") or ""
        if not url:
            return None
        m = IMOS_IMAGE_RE.search(url)
        imos = bool(m) and platform in SHORT_PLATFORM
        campaign = m["campaign"] if m else str(rec.get("campaign_key") or "")
        dive = m["dive"] if m else str(rec.get("deployment_key") or "")
        item_id = f"{campaign}/{dive}/{f.name}" if imos else f"squidle/{campaign}/{dive}/{f.name}"
        return Candidate(
            source=self.key,
            item_id=item_id,
            media_type="image",
            media_url=url,
            origin_url=f"{SQUIDLE}/api/deployment/{dep_id}" if dep_id else SQUIDLE,
            timestamp=iso_z(f.t) if f.t else None,
            ext="jpg",
            raw=rec,
            extra={
                "campaign": campaign, "dive": dive, "image_filename": f.name, "platform": platform, "route": "squidle",
                "squidle_deployment_id": dep_id, "altitude_m": to_float(rec.get("alt")),
                "licence_scope": "imos" if imos else "other", "aodn_record": self._record_uuid(platform) if imos else None,
                "dedup_key": f"{campaign}/{dive}/{f.name}" if imos else None,
            },
        )  # fmt: skip


def candidates_from_pose_json(adapter: SquidleImos, obj: dict[str, Any]) -> list[Candidate]:
    """Candidates of one ``/api/pose`` page (WMS mosaics are skipped, as the recipe says)."""
    out = []
    for p in obj.get("objects", []):
        media = p.get("media") or {}
        rec = {
            "src": "squidle", "lat": p.get("lat"), "lon": p.get("lon"), "dep": p.get("dep"),
            "data_dep": (p.get("data") or {}).get("dep"), "alt": p.get("alt"),
            "platform_name": (p.get("platform") or {}).get("name"), "media_type": "image", "is_valid": True,
            "media_key": media.get("key"), "deployment_key": (p.get("deployment") or {}).get("key"),
            "campaign_key": (p.get("campaign") or {}).get("key"), "path_best_thm": media.get("path_best_thm"),
            "n_img": 0, "n_xy": 0,
        }  # fmt: skip
        if geo_for_record(rec) is None:
            continue
        thumb = rec["path_best_thm"] or ""
        url = thumb.replace("/thumbnails/", "/full_res/")
        f = Frame(rec["media_key"] or "", parse_stamp(p.get("timestamp")) or 0.0, {**rec, "path_best": url})
        cand = adapter._candidate_squidle(f, rec["platform_name"] or "", (p.get("deployment") or {}).get("id"))
        if cand:
            out.append(cand)
    return out
