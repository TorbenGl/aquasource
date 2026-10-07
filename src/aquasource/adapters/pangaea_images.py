"""PANGAEA underwater image and video datasets (seed DOIs, curated extras, Elasticsearch discovery).

PANGAEA (AWI / MARUM) publishes seafloor imagery as "dataset publication series": each
child dataset is one camera deployment (OFOS / OFOBS towed camera, AUV, ROV, diver
transect) and its tab-separated table has one row per image (``Date/Time``, usually
``Latitude`` / ``Longitude`` / ``Depth water [m]`` and a media column). The seeds are all
CC BY (tier B); the licence is read per child dataset (record level) from the table
header ``License:`` line (or ``<md:license>`` of the pan_md for video datasets). Children
whose licence is NC / ND are not listed at all (tier X); a CC BY child under an NC / ND
parent series is tier U (the sources contradict each other).

How it works
    * Series -> children: ``?format=metadata_panmd`` of the series lists ``collectionChilds``.
      A series with ``loginOption`` != unrestricted (moratorium, e.g. SO295 994607 until
      2027-04-22) is skipped; its pan_md is re-read (not from the cache) once per run, so it is
      picked up once it opens.
    * Per child: ``?format=textfile`` (cached in metadata/raw/pangaea_<id>.tab). A dataset
      without a data matrix answers 303 to its media file (a video such as 898338): that
      redirect is never followed; the pan_md ``staticURL`` becomes one video candidate.
    * Media URL: the absolute ``URL image`` / ``URL movie`` / ``URL video`` value, else the
      file name of ``IMAGE water`` / ``IMAGE`` / ``VIDEO`` / ``Binary`` appended to
      ``https://download.pangaea.de/dataset/<id>/files/``; ``URL raw`` (24 MB TIFF) is the
      last resort. Sidecars (``Metadata``, ``URL file``, ``URL thumb``) are never fetched.
    * resolve_geo follows the "resolve_geo recipe" of research/pangaea_images.md: a per-image
      ``Latitude`` / ``Longitude`` that survives the outlier check is ``image`` precision;
      constant positions ("Positioning failed") and rows without a usable position fall back
      to the event position of the dataset (``station``, ``geo_inferred`` true, uncertainty
      4000 m for a point event or half the start-end distance + 500 m). A position that is
      constant over a whole event (the event coordinate copied into a multi-event table) is
      station, not image. A video listed in a table row with a position is ``segment``
      (position at the video start, geo_inferred true). Depth is ``abs(Depth water [m])``
      (MSM77 serves it negative), else -ELEVATION of the event, except for under-ice /
      upward-looking cameras (BEAST), whose event ELEVATION is the seafloor, not the camera.
      Coordinates are never invented and the sidecar ``Posidonia`` fields are never parsed.
    * Coordinate outliers: a fix farther than max(3 km, start-end distance of the event) from
      the child's median position (for 20+ fixes also 4 x the 75th percentile distance, so a
      long track with a point event is not cut), or one that implies > 3 m/s to both
      neighbours, is rejected. A USBL fix held over many frames raises
      ``geo_uncertainty_m`` to max(value, 0.3 m/s x duration of the run).
    * Deck / descent frames and bad rows are dropped before they become candidates: rows
      without position before the event time or before the first valid fix, depth < 0.9 x the
      child's median depth, AUV ``Ground vis [#]`` = 0, AUV altitude (``Distance [m]``)
      > 12 m. A date-only ``Date/Time`` (no clock time) is never compared with the event time.
      Black frames need pixel checks and are not handled here.
    * Budget-friendly order (``order=spread``): equal share per series (round robin), then per
      child (children and rows are visited in a bit-reversed order, so any prefix of the
      stream is spread over the whole series / time range), instead of the first N rows of
      the first child. Item ids are ``PANGAEA.<child id>/<file name>`` and stable.
    * Tape: files on hs.pangaea.de / download.pangaea.de may sit on tape and answer HTTP 503
      (``Retry-After``) until staged (1-3 min per file). ``fetch_media`` waits and retries,
      never saves an HTML body, and once staging has been seen it sends one HEAD per upcoming
      candidate (``stage_batch``) so that recalls overlap instead of queueing.
    * Politeness: <= 1 request/s per host, one transfer at a time. Large harvests need prior
      authorisation by PANGAEA (ToU 5.5), see manual_steps.

Adapter options (``--opt key=value``; values are JSON or comma separated lists)
    series            series / dataset ids to expand (default: the six seed series
                      989682 994607 935856 882349 911904 936205).
    datasets          single dataset ids used as they are (default with no ``series``:
                      898338, the HE153 ROV video).
    extras            true adds the curated extra series of the research note (other cruises,
                      GBR / Moreton Bay diver transects, MOSAiC under-ice ROV stills, ...).
    discovery         true adds the PANGAEA Elasticsearch discovery query (about 1,100 open
                      CC BY / CC0 underwater image / video datasets), grouped by parent series.
    discovery_max     stop after this many discovery hits.
    exclude           more dataset ids to skip.
    exclude_overlap   true (default) skips datasets that belong to other aquasource keys or are
                      derived copies (german_bight, obsea, 957274 ...); an excluded series id also
                      excludes all of its children (series group or the child's parent DOI).
    check_parent      true (default): compare the licence of the parent series (NC / ND -> U).
    order             ``spread`` (default) or ``table`` (series, children and rows in file order).
    max_per_child     at most N candidates per child dataset.
    max_per_series    at most N candidates per series.
    max_videos_per_series  at most N video files per series (default 2; one video is 2-3.5 GB), counted
                      over single-video datasets and video rows of tables alike.
    keep_flagged      true keeps rows that the filters would drop (they carry ``flags`` in extra).
    depth_filter      fraction of the median depth below which a row is a descent frame
                      (default 0.9, 0 disables).
    drop_sw_files     true also drops file names that start with ``SW_`` (release frames).
    prefer_raw        true prefers ``URL raw`` (TIFF) over ``URL image`` (JPEG).
    max_table_mb      skip a table larger than this (default 25).
    stage_batch       HEAD look-ahead per tape recall batch (default 20, 0 = off).
    stage_timeout_s   give up on one file after this long (default 900).
    refresh_metadata  core option: re-download cached metadata.
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import statistics
import time
import xml.etree.ElementTree as ET
from collections import Counter, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from itertools import chain, islice
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import quote, urlparse

from ..core.geo import haversine_m, parse_time, precision_at_least, to_float
from ..core.http import HttpError
from ..core.licence import classify, make_licence
from ..core.schema import Candidate, Geo, Licence
from ..providers import pangaea
from .base import Adapter, MediaRef, guess_ext, register

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------- constants
SEED_SERIES = ("989682", "994607", "935856", "882349", "911904", "936205")
SEED_DATASETS = ("898338",)

# Best extra series of research/pangaea_images.md (open, CC BY, underwater). The four last
# ones are under moratorium today and are skipped until PANGAEA opens them.
EXTRA_SERIES = (
    "894801", "958183", "846147", "877578", "890634", "872719", "871550", "971424", "928815",
    "891505", "943364", "971365", "932827", "894734", "971422", "862097", "921370", "961936",
    "615785",
    "995890", "987471", "988212", "987706",
)  # fmt: skip

# Datasets that other aquasource keys cover, or that are derived copies of seed images.
OVERLAP_EXCLUDE = {
    "957274": "processed copy of seed 935856 (SO268 analysis-ready images)",
    "946149": "OBSEA camera: key obsea",
    "946789": "OBSEA camera: key obsea",
    "936693": "OBSEA camera: key obsea",
    "907386": "seafloor videos: key german_bight",
    "909999": "seafloor videos: key german_bight",
    "831731": "seafloor videos: key german_bight",
    "912471": "re-references OFOS images published elsewhere",
    "849291": "re-references OFOS images published elsewhere",
    "897047": "re-references OFOS images published elsewhere",
    "892623": "same photos as 877578",
    "891736": "same photos as 891505",
}

# "Ocean Floor Observation and Bathymetry System" (OFOBS) is a camera, not a bathymetry product.
TITLE_EXCLUDE = re.compile(r"side[\s-]?scan|bathymetr(?!y system)|multibeam|parasound|quicklook|sky imager|aerial", re.I)

IMAGE_EXT = {"jpg", "jpeg", "png", "tif", "tiff"}
VIDEO_EXT = {"mpg", "mpeg", "mp4", "mov", "avi", "mkv", "wmv", "m4v", "webm"}

# Media columns in order of preference. Absolute-URL columns first (hs.pangaea.de is mostly
# disk cached), then file-name columns (download.pangaea.de), the TIFF column last.
URL_COLUMNS = ("URL image", "URL movie", "URL video")
FILE_COLUMNS = ("IMAGE water", "IMAGE", "VIDEO water", "VIDEO", "Binary")
RAW_COLUMNS = ("URL raw",)
DOWNLOAD_URL = "https://download.pangaea.de/dataset/{id}/files/{name}"
MEDIA_HOSTS = {"hs.pangaea.de", "download.pangaea.de"}

ES_URL = "https://ws.pangaea.de/es/pangaea/panmd/_search"
ES_QUERY = (
    "(techKeyword:param54243 OR techKeyword:param150836 OR techKeyword:param514706 OR techKeyword:param146419 "
    "OR techKeyword:param15651 OR techKeyword:param510678 OR techKeyword:param514838 OR techKeyword:param83431) "
    "AND (techKeyword:license21 OR techKeyword:license101 OR techKeyword:license29) AND sp-loginOption:1 "
    "AND (techKeyword:method11386 OR techKeyword:method11971 OR techKeyword:method10738 OR techKeyword:method11520 "
    'OR agg-method:"Remote operated vehicle" OR agg-method:"Remotely operated sensor platform BEAST" '
    'OR agg-method:"Sampling by diver" OR agg-method:"Underwater fish observatory")'
)
ES_PAGE = 500

# Uncertainty defaults of the research note (estimates, not provider values).
UNC_STATION_POINT_M = 4000.0
UNC_AUV_M = 50.0
UNC_OFOS_M = 20.0
HELD_FIX_SPEED_MS = 0.3
HELD_FIX_MIN_S = 60.0
OUTLIER_MIN_M = 3000.0
OUTLIER_SPEED_MS = 3.0
AUV_MAX_ALTITUDE_M = 12.0

PLATFORM_AUV = re.compile(r"autonomous underwater vehicle|\bAUV\b", re.I)
PLATFORM_TOWED = re.compile(r"OFOS|OFOBS|Ocean Floor Observation|\bROV\b|remote", re.I)
# Deck / descent rules are for towed cameras and AUVs. Under-ice ROV stills (BEAST, 0-20 m below the ice) and diver
# transects have no "descent", and ROV depth changes with the terrain, so the depth rule is limited further.
PLATFORM_NO_DECK_RULES = re.compile(r"BEAST|diver", re.I)
PLATFORM_NO_DEPTH_RULE = re.compile(r"\bROV\b|remote|BEAST|diver", re.I)
DEPTH_RULE_MIN_GAP_M = 10.0  # also needs this many metres above the median: shallow reefs vary by more than 10 %
# Under-ice / upward-looking cameras (MOSAiC BEAST, ROV under sea ice): the event ELEVATION is the seafloor depth
# (thousands of metres), not the camera depth, so it is never used as depth_m for them.
UNDER_ICE = re.compile(r"BEAST|under[\s-]?ice|upward[\s-]?looking", re.I)
SHIP_GPS_UNKNOWN_DEPTH_M = 2000.0  # cap of the layback heuristic, used when the depth is unknown
# Media types of a ?format=textfile answer that is a media file, not a data table (never read as metadata).
NON_TABLE_TYPES = ("image/", "video/", "audio/", "application/octet-stream", "application/zip", "application/x-tar")

# Flags that make a row a candidate for dropping (unless keep_flagged).
DROP_FLAGS = frozenset(
    {"pre_event_no_position", "pre_first_fix_no_position", "shallow_depth", "ground_vis_0", "altitude_high"}
)

MANUAL_STEPS = (
    "None for sampled runs (a few thousand files per day at <= 1 request/s per host). Before a full-archive harvest "
    "(more than ~100 GB or many thousand files per day) ask PANGAEA for prior authorisation (ToU section 5.5, "
    "https://www.pangaea.de/contact/). Files on tape answer HTTP 503 until staged (minutes) and are retried. "
    "Moratorium series (SO295 994607 until 2027-04-22) are skipped until PANGAEA opens them."
)


# --------------------------------------------------------------------------- small helpers
def num(x: object) -> float | None:
    """Parse a table cell: blank -> None, strip a leading PANGAEA QC flag character (? * / # < >)."""
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    if s[0] in "?*/#<>":
        s = s[1:].strip()
    return to_float(s)


def _first_number(text: str | None) -> float | None:
    if not text:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group(0)) if m else None


def _first_set(*values: Any) -> Any:
    for v in values:
        if v is not None:
            return v
    return None


def _as_list(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, (str, int)):
        return [x.strip() for x in str(v).split(",") if x.strip()]
    return [str(x).strip() for x in v if str(x).strip()]


def _flag(v: Any, default: bool) -> bool:
    if v is None:
        return default
    if isinstance(v, str):
        return v.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(v)


def spread_order(n: int) -> list[int]:
    """Indices 0..n-1 in bit-reversed order: every prefix is spread evenly over the range."""
    if n <= 0:
        return []
    bits = max(1, (n - 1).bit_length())
    out = []
    for i in range(1 << bits):
        r = int(format(i, f"0{bits}b")[::-1], 2)
        if r < n:
            out.append(r)
    return out


def _interleave(streams: Iterable[Iterator[Any]]) -> Iterator[Any]:
    """Round robin over lazily started iterators."""
    active = list(streams)
    while active:
        keep = []
        for s in active:
            try:
                item = next(s)
            except StopIteration:
                continue
            yield item
            keep.append(s)
        active = keep


def _midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    if lon2 - lon1 > 180:
        lon2 -= 360
    elif lon2 - lon1 < -180:
        lon2 += 360
    lon = (lon1 + lon2) / 2
    if lon > 180:
        lon -= 360
    elif lon < -180:
        lon += 360
    return round((lat1 + lat2) / 2, 7), round(lon, 7)


def media_type_for(url: str) -> str:
    ext = os.path.splitext(urlparse(url).path)[1].lstrip(".").lower()
    return "video" if ext in VIDEO_EXT else "image"


def _media_ext(url: str) -> str:
    return os.path.splitext(urlparse(url).path)[1].lstrip(".").lower()


def _looks_like_html(path: Path) -> bool:
    try:
        with open(path, "rb") as fh:
            head = fh.read(512).lstrip().lower()
    except OSError:
        return False
    return head.startswith((b"<!doctype html", b"<html", b"<head", b"<?xml")) or b"<html" in head[:200]


# --------------------------------------------------------------------------- metadata model
@dataclass
class Event:
    """One PANGAEA event (station / deployment) with an optional end point."""

    label: str
    lat: float | None = None
    lon: float | None = None
    lat2: float | None = None
    lon2: float | None = None
    elev: float | None = None
    elev2: float | None = None
    dt: str | None = None
    dt2: str | None = None
    method: str = ""

    @property
    def has_end(self) -> bool:
        return None not in (self.lat, self.lon, self.lat2, self.lon2)

    @property
    def span_m(self) -> float:
        return haversine_m(self.lat, self.lon, self.lat2, self.lon2) if self.has_end else 0.0

    def depth(self) -> float | None:
        """Bottom depth in m from the event ELEVATION (negative below sea level)."""
        els = [e for e in (self.elev, self.elev2) if e is not None]
        if not els:
            return None
        d = -sum(els) / len(els)
        return round(d, 2) if d > 0 else None

    def base_label(self) -> str:
        return self.label.split(" (")[0].strip()


def parse_event_line(line: str) -> Event | None:
    """Parse one ``Event(s):`` header line: ``label * LATITUDE: x * LONGITUDE: y * ELEVATION: -z m ...``."""
    parts = [p.strip() for p in line.split(" * ")]
    if not parts or not parts[0]:
        return None
    fields: dict[str, str] = {}
    for p in parts[1:]:
        k, sep, v = p.partition(":")
        if sep:
            fields[k.strip().upper()] = v.strip()

    def f(*keys: str) -> float | None:
        return _first_set(*(_first_number(fields.get(k)) for k in keys))

    return Event(
        label=parts[0],
        lat=f("LATITUDE", "LATITUDE START"),
        lon=f("LONGITUDE", "LONGITUDE START"),
        lat2=f("LATITUDE END"),
        lon2=f("LONGITUDE END"),
        elev=f("ELEVATION", "ELEVATION START"),
        elev2=f("ELEVATION END"),
        dt=fields.get("DATE/TIME") or fields.get("DATE/TIME START"),
        dt2=fields.get("DATE/TIME END"),
        method=fields.get("METHOD/DEVICE", ""),
    )


_MD = "{http://www.pangaea.de/MetaData}"


@dataclass
class PanMd:
    """The parts of a ``?format=metadata_panmd`` document that the adapter uses."""

    dataset_id: str = ""
    title: str = ""
    year: str = ""
    authors: list[str] = field(default_factory=list)
    parent_uri: str | None = None
    licence_id: str | None = None
    licence_label: str | None = None
    licence_name: str | None = None
    licence_uri: str | None = None
    licence_preliminary: bool = False
    technical: dict[str, str] = field(default_factory=dict)
    events: list[Event] = field(default_factory=list)
    comment: str = ""

    @property
    def children(self) -> list[str]:
        raw = self.technical.get("collectionChilds", "")
        return [re.sub(r"\D", "", x) for x in raw.split(",") if re.sub(r"\D", "", x)]

    @property
    def login_ok(self) -> bool:
        return self.technical.get("loginOption", "unrestricted") == "unrestricted"

    @property
    def moratorium_until(self) -> str | None:
        return self.technical.get("moratoriumUntil") or None

    @property
    def licence_text(self) -> str | None:
        if not (self.licence_name or self.licence_label):
            return None
        name = self.licence_name or self.licence_label or ""
        label = f" ({self.licence_label})" if self.licence_label and self.licence_name else ""
        uri = f" (URI: {self.licence_uri})" if self.licence_uri else ""
        return f"{name}{label}{uri}"

    def restricted_reason(self, today: str) -> str | None:
        until = self.moratorium_until
        if until and until > today:
            return f"moratorium until {until} (loginOption={self.technical.get('loginOption')})"
        if not self.login_ok and not until:
            return f"loginOption={self.technical.get('loginOption')}"
        return None


def parse_panmd(text: str) -> PanMd:
    """Parse pan_md XML. Documents with a DOCTYPE / ENTITY declaration are refused (untrusted data)."""
    head = text[:4096].lower()
    if "<!doctype" in head or "<!entity" in text[:65536].lower():
        raise ValueError("pan_md with DOCTYPE / ENTITY declaration refused")
    root = ET.fromstring(text)
    pm = PanMd()
    cit = root.find(f"{_MD}citation")
    if cit is not None:
        pm.dataset_id = re.sub(r"\D", "", cit.get("id") or "")
        pm.title = (cit.findtext(f"{_MD}title") or "").strip()
        pm.year = (cit.findtext(f"{_MD}year") or "").strip()
        pm.parent_uri = (cit.findtext(f"{_MD}parentURI") or "").strip() or None
        for a in cit.findall(f"{_MD}author"):
            last = (a.findtext(f"{_MD}lastName") or "").strip()
            first = (a.findtext(f"{_MD}firstName") or "").strip()
            if last:
                pm.authors.append(f"{last}, {first}" if first else last)
    lic = root.find(f"{_MD}license")
    if lic is not None:
        pm.licence_id = lic.get("id")
        pm.licence_preliminary = (lic.get("preliminary") or "").lower() == "true"
        pm.licence_label = (lic.findtext(f"{_MD}label") or "").strip() or None
        pm.licence_name = (lic.findtext(f"{_MD}name") or "").strip() or None
        pm.licence_uri = (lic.findtext(f"{_MD}URI") or "").strip() or None
    for entry in root.findall(f"{_MD}technicalInfo/{_MD}entry"):
        if entry.get("key"):
            pm.technical[entry.get("key")] = entry.get("value") or ""
    pm.comment = " ".join((root.findtext(f"{_MD}comment") or "").split())
    for ev in root.findall(f"{_MD}event"):
        method = ev.find(f"{_MD}method")
        pm.events.append(
            Event(
                label=(ev.findtext(f"{_MD}label") or "").strip(),
                lat=num(ev.findtext(f"{_MD}latitude")),
                lon=num(ev.findtext(f"{_MD}longitude")),
                lat2=num(ev.findtext(f"{_MD}latitude2")),
                lon2=num(ev.findtext(f"{_MD}longitude2")),
                elev=num(ev.findtext(f"{_MD}elevation")),
                elev2=num(ev.findtext(f"{_MD}elevation2")),
                dt=(ev.findtext(f"{_MD}dateTime") or None),
                dt2=(ev.findtext(f"{_MD}dateTime2") or None),
                method=" ".join(
                    x for x in ((method.findtext(f"{_MD}name") or ""), (method.findtext(f"{_MD}optionalName") or "")) if x
                )
                if method is not None
                else "",
            )
        )
    return pm


def _col(columns: list[str], *names: str) -> str | None:
    """First column equal to (case-insensitive), else starting with, one of ``names``."""
    for n in names:
        for c in columns:
            if c.lower() == n.lower():
                return c
    for n in names:
        for c in columns:
            if c.lower().startswith(n.lower()):
                return c
    return None


@dataclass
class TableGeo:
    """Per-table coordinate analysis, computed once per child dataset."""

    lat_col: str | None = None
    lon_col: str | None = None
    depth_col: str | None = None
    time_col: str | None = None
    unc_col: str | None = None
    event_col: str | None = None
    pairs: list[tuple[float, float] | None] = field(default_factory=list)  # valid lat/lon per row
    times: list[float | None] = field(default_factory=list)
    # compact per-row values, so that the full table rows can be freed once the candidates are listed
    depths: list[float | None] = field(default_factory=list)  # "Depth water [m]" as served
    uncs: list[float | None] = field(default_factory=list)  # "Coord unc [m]"
    ev_labels: list[str] = field(default_factory=list)  # "Event" column
    outliers: set[int] = field(default_factory=set)
    n_valid: int = 0
    n_unique: int = 0
    median_pos: tuple[float, float] | None = None
    first_fix_t: float | None = None
    run_s: dict[int, float] = field(default_factory=dict)
    median_depth: float | None = None
    ship_gps: bool = False
    flags: list[list[str]] = field(default_factory=list)
    # Event labels ("" = no Event column) whose rows all carry one position: the event coordinate copied into
    # the table (or a failed positioning), never a per-image fix.
    constant_groups: set[str] = field(default_factory=set)

    def has_position(self, i: int) -> bool:
        return self.pairs[i] is not None and i not in self.outliers

    def is_constant(self, i: int) -> bool:
        return self.ev_labels[i] in self.constant_groups


@dataclass
class PanDataset:
    """One child dataset: either a data table or a single static media file."""

    dataset_id: str
    kind: str  # "table" | "static"
    citation: str
    licence_text: str | None
    licence_name: str | None
    licence_uri: str | None
    events: list[Event]
    comment: str = ""
    title: str = ""
    parent_id: str | None = None
    table: pangaea.PangaeaTable | None = None
    geo: TableGeo | None = None
    static_url: str | None = None
    tier_override: str | None = None
    override_note: str | None = None

    @property
    def doi(self) -> str:
        return f"{pangaea.DOI_PREFIX}{self.dataset_id}"

    @property
    def landing(self) -> str:
        return pangaea.landing_url(self.dataset_id)

    @property
    def platform(self) -> str:
        return "; ".join(e.method for e in self.events if e.method)

    @property
    def under_ice(self) -> bool:
        return bool(UNDER_ICE.search(self.platform) or UNDER_ICE.search(self.title or ""))

    def event_at(self, idx: int | None) -> Event | None:
        """Event of table row ``idx`` (its ``Event`` column), else the only / first event."""
        if self.geo is not None and idx is not None:
            return _event_by_label(self.events, self.geo.ev_labels[idx])
        return self.events[0] if self.events else None


def analyse_table(
    table: pangaea.PangaeaTable,
    events: list[Event],
    platform: str,
    *,
    depth_filter: float = 0.9,
) -> TableGeo:
    """Validate the per-row coordinates of a child table and flag deck / descent / bad rows."""
    cols = table.columns
    g = TableGeo(
        lat_col=_col(cols, "Latitude"),
        lon_col=_col(cols, "Longitude"),
        depth_col=_col(cols, "Depth water [m]", "Depth water"),
        time_col=_col(cols, "Date/Time"),
        unc_col=_col(cols, "Coord unc"),
        event_col=_col(cols, "Event"),
        ship_gps=any(re.match(r"(course|speed)\b", c, re.I) for c in cols),
    )
    rows = table.rows
    n = len(rows)
    # Times with a clock time. A date-only "Date/Time" (e.g. 2023-06-02 in ARTofMELT 961934) is fine for ordering
    # but must not be compared with an event time or used for speeds: midnight is not when the photo was taken.
    exact: list[float | None] = []
    for row in rows:
        lat = num(row.get(g.lat_col)) if g.lat_col else None
        lon = num(row.get(g.lon_col)) if g.lon_col else None
        ok = (
            lat is not None
            and lon is not None
            and -90.0 <= lat <= 90.0
            and -180.0 <= lon <= 180.0
            and not (lat == 0.0 and lon == 0.0)
        )
        g.pairs.append((lat, lon) if ok else None)
        stamp = (row.get(g.time_col) or "").strip() if g.time_col else ""
        t = parse_time(stamp) if stamp else None
        g.times.append(t)
        exact.append(t if ":" in stamp else None)
        g.depths.append(num(row.get(g.depth_col)) if g.depth_col else None)
        g.uncs.append(num(row.get(g.unc_col)) if g.unc_col else None)
        g.ev_labels.append((row.get(g.event_col) or "").strip() if g.event_col else "")
    valid = [i for i, p in enumerate(g.pairs) if p is not None]
    g.n_valid = len(valid)

    # 1) distance from the median position, per event: a multi-event table (several stations km apart, rows
    #    labelled in an Event column) is checked station by station, never against one median of all stations
    if valid:
        g.median_pos = (
            statistics.median(g.pairs[i][0] for i in valid),
            statistics.median(g.pairs[i][1] for i in valid),
        )
    by_event: dict[str, list[int]] = {}
    for i in valid:
        by_event.setdefault(g.ev_labels[i], []).append(i)
    for label, idxs in by_event.items():
        if len(idxs) <= 2:
            continue
        med = (statistics.median(g.pairs[i][0] for i in idxs), statistics.median(g.pairs[i][1] for i in idxs))
        ev = _event_by_label(events, label) if label else None
        span = ev.span_m if ev is not None else max((e.span_m for e in events), default=0.0)
        dist = {i: haversine_m(med[0], med[1], *g.pairs[i]) for i in idxs}
        limit = max(OUTLIER_MIN_M, span)
        if len(idxs) >= 20:
            ds = sorted(dist.values())
            limit = max(limit, 4.0 * ds[int(0.75 * (len(ds) - 1))])
        g.outliers |= {i for i, d in dist.items() if d > limit}
    # 2) spikes: implied speed above 3 m/s to both time neighbours
    seq = sorted((exact[i], i) for i in valid if i not in g.outliers and exact[i] is not None)
    for k in range(1, len(seq) - 1):
        (t0, i0), (t1, i1), (t2, i2) = seq[k - 1], seq[k], seq[k + 1]
        if t1 <= t0 or t2 <= t1:
            continue
        v_prev = haversine_m(*g.pairs[i0], *g.pairs[i1]) / (t1 - t0)
        v_next = haversine_m(*g.pairs[i1], *g.pairs[i2]) / (t2 - t1)
        if v_prev > OUTLIER_SPEED_MS and v_next > OUTLIER_SPEED_MS:
            g.outliers.add(i1)
    # distinct positions, overall and per event, counted on the fixes that survived the outlier tests
    kept = [i for i in valid if i not in g.outliers]
    g.n_unique = len({g.pairs[i] for i in kept})
    per_group: dict[str, set[tuple[float, float]]] = {}
    per_group_n: Counter = Counter()
    for i in kept:
        per_group.setdefault(g.ev_labels[i], set()).add(g.pairs[i])
        per_group_n[g.ev_labels[i]] += 1
    g.constant_groups = {lab for lab, s in per_group.items() if len(s) == 1 and per_group_n[lab] >= 2}
    good = sorted((exact[i], i) for i in valid if i not in g.outliers and exact[i] is not None)
    if good:
        g.first_fix_t = good[0][0]
    # 3) runs of one held USBL fix
    k = 0
    while k < len(good):
        j = k
        while j + 1 < len(good) and g.pairs[good[j + 1][1]] == g.pairs[good[k][1]]:
            j += 1
        dur = good[j][0] - good[k][0]
        for _, i in good[k : j + 1]:
            g.run_s[i] = dur
        k = j + 1

    # 4) per-row flags
    depths = [abs(d) for d in g.depths if d is not None and d != 0]
    if len(depths) >= 3:
        g.median_depth = statistics.median(depths)
    vis_col = _col(cols, "Ground vis")
    alt_col = _col(cols, "Distance [m]")
    auv = bool(PLATFORM_AUV.search(platform))
    deck_rules = not PLATFORM_NO_DECK_RULES.search(platform)
    depth_rule = not PLATFORM_NO_DEPTH_RULE.search(platform)
    for i, row in enumerate(rows):
        fl: list[str] = []
        if i in g.outliers:
            fl.append("position_outlier")
        if deck_rules and not g.has_position(i):
            t = exact[i]
            ev = _event_by_label(events, g.ev_labels[i])
            ev_t = parse_time(ev.dt) if ev and ev.dt else None
            if ev is None and events:
                times = [parse_time(e.dt) for e in events if e.dt]
                ev_t = min((x for x in times if x is not None), default=None)
            if t is not None and ev_t is not None and t < ev_t:
                fl.append("pre_event_no_position")
            if t is not None and g.first_fix_t is not None and t < g.first_fix_t:
                fl.append("pre_first_fix_no_position")
        d = g.depths[i]
        if (
            depth_rule
            and depth_filter
            and g.median_depth
            and d is not None
            and abs(d) < depth_filter * g.median_depth
            and g.median_depth - abs(d) > DEPTH_RULE_MIN_GAP_M
        ):
            fl.append("shallow_depth")
        if vis_col and num(row.get(vis_col)) == 0:
            fl.append("ground_vis_0")
        if auv and vis_col and alt_col:
            alt = num(row.get(alt_col))
            if alt is not None and alt > AUV_MAX_ALTITUDE_M:
                fl.append("altitude_high")
        if g.run_s.get(i, 0.0) > HELD_FIX_MIN_S:
            fl.append("held_fix")
        g.flags.append(fl or _NO_FLAGS)
    assert len(g.flags) == n
    return g


_NO_FLAGS: list[str] = []  # shared, never mutated (callers copy)


def _event_by_label(events: list[Event], label: str) -> Event | None:
    label = (label or "").strip()
    if label:
        for ev in events:
            if label in (ev.label, ev.base_label()):
                return ev
    return events[0] if len(events) == 1 else None


# --------------------------------------------------------------------------- series groups
@dataclass
class Group:
    """A series (or single dataset) whose children are interleaved as one unit."""

    series_id: str
    children: list[str] | None = None  # None: expand through the series pan_md
    titles: dict[str, str] = field(default_factory=dict)


class _Skip(Exception):
    """A dataset that is skipped on purpose; the message is the reason."""


@register
class PangaeaImagesAdapter(Adapter):
    key = "pangaea_images"
    name = "PANGAEA underwater image and video datasets (seed DOIs + discovery)"
    homepage = "https://www.pangaea.de/"
    citation = (
        "PANGAEA Data Publisher (AWI / MARUM), https://www.pangaea.de/. Each sample's attribution is the citation string "
        "of its dataset (child DOI 10.1594/PANGAEA.<id>) plus the licence."
    )
    media_types = ("image", "video")
    env_vars: tuple[str, ...] = ()
    manual_steps = MANUAL_STEPS
    host_intervals = {
        "doi.pangaea.de": 1.0,
        "hs.pangaea.de": 1.0,
        "download.pangaea.de": 1.0,
        "ws.pangaea.de": 1.0,
    }

    def __init__(self, ctx):
        super().__init__(ctx)
        self._datasets: dict[str, PanDataset] = {}
        self._series: dict[str, PanMd] = {}
        self._claimed: set[str] = set()
        self._seen_urls: set[str] = set()
        self._videos: Counter = Counter()
        self._lookahead: deque[Candidate] = deque()
        self._warmed: dict[str, bool] = {}  # url -> already on disk when the warm-up HEAD asked
        self._staging_seen = False
        self._rechecked: set[str] = set()  # restricted records re-read in this run
        self.excluded = self._excluded_ids()

    # ----------------------------------------------------------------- options
    def _excluded_ids(self) -> dict[str, str]:
        out: dict[str, str] = {}
        if _flag(self.options.get("exclude_overlap"), True):
            out.update(OVERLAP_EXCLUDE)
        for x in _as_list(self.options.get("exclude")):
            out[pangaea.dataset_id(x)] = "excluded by option exclude"
        return out

    def _opt_int(self, name: str, default: int | None) -> int | None:
        v = self.options.get(name)
        if v is None or v == "":
            return default
        return int(v)

    def check_ready(self) -> list[str]:
        problems = super().check_ready()
        if self.options.get("order", "spread") not in ("spread", "table"):
            problems.append("option order must be 'spread' or 'table'")
        return problems

    # ----------------------------------------------------------------- metadata fetch
    def _panmd(self, ds_id: str, *, refresh: bool = False) -> PanMd:
        text = self.ctx.cached_text(
            pangaea.landing_url(ds_id) + "?format=metadata_panmd", f"pangaea_{ds_id}.panmd.xml", refresh=refresh
        )
        return parse_panmd(text)

    def _open_panmd(self, ds_id: str, today: str) -> tuple[PanMd, str | None]:
        """pan_md plus the reason it is restricted. A restricted record is re-read once per run (not from the
        cache), so a moratorium that PANGAEA lifts or changes is noticed on the next run."""
        pm = self._panmd(ds_id)
        why = pm.restricted_reason(today)
        if why and ds_id not in self._rechecked:
            self._rechecked.add(ds_id)
            try:
                pm = self._panmd(ds_id, refresh=True)
                why = pm.restricted_reason(today)
            except HttpError as exc:
                log.info("re-check of restricted PANGAEA.%s failed: %s", ds_id, exc)
        return pm, why

    def _table_text(self, ds_id: str) -> str:
        """The ``?format=textfile`` export, cached. "" means: no data matrix (the server redirects to the file).

        The redirect is never followed (it would download the media file). 401 / 403 is a
        moratorium or other access restriction; oversized tables are skipped.
        """
        name = f"pangaea_{ds_id}.tab"
        path = self.ctx.layout.raw / name
        if path.exists() and not self.options.get("refresh_metadata"):
            return path.read_text(encoding="utf-8")
        url = pangaea.textfile_url(ds_id)
        limit = int(float(self.options.get("max_table_mb") or 25) * 1_000_000)
        resp = self.http.request("GET", url, stream=True, allow_redirects=False)
        try:
            if resp.status_code in (301, 302, 303, 307, 308):
                self.ctx.save_raw(name, "")
                return ""
            if resp.status_code in (401, 403):
                raise _Skip(f"restricted: HTTP {resp.status_code} (access rights needed or moratorium)")
            if resp.status_code >= 400:
                raise HttpError(url, resp.status_code, "textfile request failed")
            if (resp.headers.get("Content-Type") or "").lower().startswith(NON_TABLE_TYPES):
                # the server handed out the media file itself: no data matrix, and the body is never read
                self.ctx.save_raw(name, "")
                return ""
            if int(resp.headers.get("Content-Length") or 0) > limit:
                raise _Skip(f"table larger than max_table_mb={limit / 1e6:g}")
            buf = bytearray()
            for chunk in resp.iter_content(1 << 16):
                buf += chunk
                if len(buf) > limit:
                    raise _Skip(f"table larger than max_table_mb={limit / 1e6:g}")
        finally:
            resp.close()
        text = bytes(buf).decode("utf-8", errors="replace")
        self.ctx.save_raw(name, text)
        return text

    def _cached_post(self, url: str, name: str, body: dict[str, Any]) -> Any:
        path = self.ctx.layout.raw / name
        if path.exists() and not self.options.get("refresh_metadata"):
            return json.loads(path.read_text(encoding="utf-8"))
        resp = self.http.request("POST", url, json=body, headers={"Accept": "application/json"})
        if resp.status_code >= 400:
            raise HttpError(url, resp.status_code, resp.text[:300])
        self.ctx.save_raw(name, resp.text)
        return resp.json()

    # ----------------------------------------------------------------- series / groups
    def _base_groups(self) -> list[Group]:
        """Seeds (or the ``series`` / ``datasets`` options) plus the curated extras."""
        opts = self.options
        explicit = "series" in opts or "datasets" in opts
        series = _as_list(opts.get("series")) if "series" in opts else ([] if explicit else list(SEED_SERIES))
        datasets = _as_list(opts.get("datasets")) if "datasets" in opts else ([] if explicit else list(SEED_DATASETS))
        groups: list[Group] = []
        seen: set[str] = set()

        def add(g: Group) -> None:
            if g.series_id not in seen:
                seen.add(g.series_id)
                groups.append(g)

        for s in series:
            add(Group(pangaea.dataset_id(s)))
        for d in datasets:
            did = pangaea.dataset_id(d)
            add(Group(did, [did]))
        if _flag(opts.get("extras"), False):
            for s in EXTRA_SERIES:
                add(Group(s))
        return groups

    def _groups(self) -> list[Group]:
        groups = self._base_groups()
        if _flag(self.options.get("discovery"), False):
            known = {g.series_id for g in groups}
            groups += [g for g in self._es_groups() if g.series_id not in known]
        return groups

    @staticmethod
    def _es_body(after: Any = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "query": {"query_string": {"query": ES_QUERY}},
            "size": ES_PAGE,
            "sort": [{"sf-idDataSet": "asc"}],
            "_source": ["URI", "parentIdDataSet", "nDataPoints", "sp-loginOption", "xml-thumb"],
        }
        if after is not None:
            body["search_after"] = after
        return body

    def _es_pages(self) -> Iterator[dict[str, Any]]:
        after = None
        page = 0
        while True:
            data = self._cached_post(ES_URL, f"es_discovery_p{page:03d}.json", self._es_body(after))
            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                return
            yield data
            if len(hits) < ES_PAGE:
                return
            after = hits[-1].get("sort")
            if after is None:
                return
            page += 1

    def _es_groups(self) -> list[Group]:
        limit = self._opt_int("discovery_max", None)
        by_parent: dict[str, Group] = {}
        n = 0
        try:
            for data in self._es_pages():
                for hit in data["hits"]["hits"]:
                    if limit is not None and n >= limit:
                        return list(by_parent.values())
                    n += 1
                    src = hit.get("_source", {})
                    did = pangaea.dataset_id(hit.get("_id") or src.get("URI") or "")
                    parent = src.get("parentIdDataSet")
                    if isinstance(parent, list):
                        parent = parent[0] if parent else None
                    pid = pangaea.dataset_id(parent) if parent else did
                    m = re.search(r"<md:title>(.*?)</md:title>", src.get("xml-thumb") or "", re.S)
                    g = by_parent.setdefault(pid, Group(pid, []))
                    g.children.append(did)
                    if m:
                        g.titles[did] = m.group(1).strip()
        except (HttpError, ValueError, KeyError) as exc:
            self.ctx.fail("ES discovery", "discover", f"{type(exc).__name__}: {exc}")
        return list(by_parent.values())

    def _expand(self, g: Group) -> list[str]:
        """Children of a series (via its pan_md), skipping restricted series."""
        today = date.today().isoformat()
        if g.children is not None:
            return list(g.children)
        sid = g.series_id
        try:
            pm, why = self._open_panmd(sid, today)
        except (HttpError, ET.ParseError, ValueError) as exc:
            self.ctx.fail(f"PANGAEA.{sid}", "discover", f"series metadata: {type(exc).__name__}: {exc}")
            return []
        self._series[sid] = pm
        if why:
            self.ctx.fail(f"PANGAEA.{sid}", "licence", f"series skipped, {why}")
            return []
        return pm.children or [sid]

    # ----------------------------------------------------------------- dataset loading
    def _load_dataset(self, ds_id: str, g: Group | None) -> PanDataset | None:
        if ds_id in self._datasets:
            return self._datasets[ds_id]
        item = f"PANGAEA.{ds_id}"
        try:
            text = self._table_text(ds_id)
            if text.strip():
                ds = self._table_dataset(ds_id, text, g)
            else:
                if g is not None and self._videos[g.series_id] >= (self._opt_int("max_videos_per_series", 2) or 0):
                    raise _Skip("video limit per series reached (max_videos_per_series)")
                ds = self._static_dataset(ds_id, g)
        except _Skip as exc:
            self.ctx.fail(item, "discover", str(exc))
            return None
        except (HttpError, ET.ParseError, ValueError) as exc:
            self.ctx.fail(item, "discover", f"{type(exc).__name__}: {exc}")
            return None
        if ds is None:
            return None
        if ds.parent_id and ds.parent_id in self.excluded:
            # e.g. a child of 957274 reached through datasets= or another series: excluded with its series
            self.ctx.fail(item, "discover", f"excluded: parent series PANGAEA.{ds.parent_id}: {self.excluded[ds.parent_id]}")
            return None
        self._apply_parent_licence(ds)
        if classify(ds.licence_name) == "X" and not ds.tier_override:
            self.ctx.fail(item, "licence", f"excluded (tier X): {ds.licence_name}")
            return None
        self._datasets[ds_id] = ds
        return ds

    def _table_dataset(self, ds_id: str, text: str, g: Group | None) -> PanDataset | None:
        t = pangaea.parse_textfile(text, ds_id)
        today = date.today().isoformat()
        if t.moratorium_until and t.moratorium_until > today:
            raise _Skip(f"moratorium until {t.moratorium_until}")
        events = [e for e in (parse_event_line(line) for line in t.meta.get("Event(s)", [])) if e]
        citation = " ".join(x for x in t.meta.get("Citation", []) if x).strip() or t.citation
        title = (re.search(r"\(\d{4}\):\s*(.*?)\s*\[dataset\]", citation) or [None, ""])[1]
        if title and TITLE_EXCLUDE.search(title):
            raise _Skip(f"not underwater imagery (title: {title[:80]})")
        parent = None
        m = re.search(r"\bIn:.*PANGAEA\.(\d+)\s*$", citation)
        if m:
            parent = m.group(1)
        elif g is not None and g.series_id != ds_id:
            parent = g.series_id
        ds = PanDataset(
            dataset_id=ds_id,
            kind="table",
            citation=citation,
            licence_text=t.licence_text,
            licence_name=t.licence_name,
            licence_uri=t.licence_url,
            events=events,
            comment=" ".join(" ".join(t.meta.get("Comment", [])).split()),
            title=title or "",
            parent_id=parent,
            table=t,
        )
        if not self._media_columns(t):
            raise _Skip(f"no media column among {list(URL_COLUMNS + FILE_COLUMNS + RAW_COLUMNS)}")
        ds.geo = analyse_table(t, events, ds.platform, depth_filter=float(self.options.get("depth_filter", 0.9) or 0))
        return ds

    def _static_dataset(self, ds_id: str, g: Group | None) -> PanDataset | None:
        today = date.today().isoformat()
        pm, why = self._open_panmd(ds_id, today)
        if why:
            raise _Skip(f"restricted: {why}")
        url = pm.technical.get("staticURL")
        mime = pm.technical.get("mimeType", "")
        if not url:
            raise _Skip("no data matrix and no staticURL (series parent or zip-only dataset)")
        ext = _media_ext(url)
        if ext not in VIDEO_EXT | IMAGE_EXT and not mime.startswith(("video/", "image/")):
            raise _Skip(f"staticURL is not an image or video ({mime or ext})")
        if TITLE_EXCLUDE.search(pm.title):
            raise _Skip(f"not underwater imagery (title: {pm.title[:80]})")
        if pm.licence_preliminary:
            raise _Skip("licence is preliminary (moratorium)")
        authors = "; ".join(pm.authors)
        citation = self._static_citation(ds_id, pm, authors)
        parent = re.sub(r"\D", "", (pm.parent_uri or "").rsplit(".", 1)[-1]) or (g.series_id if g and g.series_id != ds_id else "")
        return PanDataset(
            dataset_id=ds_id,
            kind="static",
            citation=citation,
            licence_text=pm.licence_text,
            licence_name=f"{pm.licence_name} ({pm.licence_label})" if pm.licence_name and pm.licence_label else (pm.licence_name or pm.licence_label),
            licence_uri=pm.licence_uri,
            events=pm.events,
            comment=pm.comment,
            title=pm.title,
            parent_id=parent or None,
            static_url=url,
        )

    def _static_citation(self, ds_id: str, pm: PanMd, authors: str) -> str:
        """Provider citation string (``?format=citation_text``), else one built from the pan_md."""
        try:
            text = self.ctx.cached_text(pangaea.landing_url(ds_id) + "?format=citation_text", f"pangaea_{ds_id}.citation.txt").strip()
            if text:
                return text
        except HttpError as exc:
            log.info("citation_text of %s unavailable: %s", ds_id, exc)
        cit = f"{authors} ({pm.year}): {pm.title} [dataset]. PANGAEA, https://doi.org/{pangaea.DOI_PREFIX}{ds_id}"
        if pm.parent_uri:
            cit += f", In: {pm.parent_uri}"
        return cit

    # ----------------------------------------------------------------- parent licence
    def _parent_md(self, pid: str) -> PanMd | None:
        if pid in self._series:
            return self._series[pid]
        try:
            pm = self._panmd(pid)
        except (HttpError, ET.ParseError, ValueError) as exc:
            self.ctx.fail(f"PANGAEA.{pid}", "licence", f"parent series metadata unreadable: {type(exc).__name__}: {exc}")
            return None
        self._series[pid] = pm
        return pm

    def _apply_parent_licence(self, ds: PanDataset) -> None:
        """A CC BY child under an NC / ND parent is tier U: PANGAEA's sources contradict each other."""
        if not ds.parent_id or not _flag(self.options.get("check_parent"), True) or ds.tier_override:
            return
        child_tier = classify(ds.licence_name)
        if child_tier in ("X", "U"):
            return
        pm = self._parent_md(ds.parent_id)
        if pm is None or not pm.licence_text:
            return
        if classify(pm.licence_text) == "X":
            ds.tier_override = "U"
            ds.override_note = f"parent series PANGAEA.{ds.parent_id} is {pm.licence_text}, the child says {ds.licence_name}"

    # ----------------------------------------------------------------- discovery
    def discover(self) -> Iterable[Candidate]:
        self._claimed.clear()
        self._seen_urls.clear()
        self._videos.clear()
        self._datasets.clear()  # tables are freed after listing: reload from the metadata cache
        self._lookahead.clear()  # a previous run may have stopped at its budget with candidates still buffered
        stream = self._stream()
        n = self._opt_int("stage_batch", 20) or 0
        if self.ctx.dry_run or n <= 0:
            yield from stream
            return
        buf = self._lookahead
        for cand in stream:
            buf.append(cand)
            if len(buf) > n:
                yield buf.popleft()
        while buf:
            yield buf.popleft()

    def _stream(self) -> Iterator[Candidate]:
        groups = self._groups()
        series = [self._series_stream(g) for g in groups]
        if self.options.get("order", "spread") == "table":
            return chain.from_iterable(series)
        return _interleave(series)

    def _series_stream(self, g: Group) -> Iterator[Candidate]:
        if g.series_id in self.excluded and g.children != [g.series_id]:
            # a whole series that another key covers or that copies seed images (e.g. 957274, 892623): its
            # children have their own ids, so the check on the child id alone would let them through
            self.ctx.fail(f"PANGAEA.{g.series_id}", "discover", f"excluded series: {self.excluded[g.series_id]}")
            return
        kids = self._expand(g)
        if not kids:
            return
        table_order = self.options.get("order", "spread") == "table"
        if not table_order:
            kids = [kids[i] for i in spread_order(len(kids))]
        streams = [self._child_stream(k, g) for k in kids]
        it = chain.from_iterable(streams) if table_order else _interleave(streams)
        cap = self._opt_int("max_per_series", None)
        yield from (islice(it, cap) if cap else it)

    def _child_stream(self, ds_id: str, g: Group) -> Iterator[Candidate]:
        if ds_id in self._claimed:
            return
        self._claimed.add(ds_id)
        if ds_id in self.excluded:
            self.ctx.fail(f"PANGAEA.{ds_id}", "discover", f"excluded: {self.excluded[ds_id]}")
            return
        title = g.titles.get(ds_id)
        if title and TITLE_EXCLUDE.search(title):
            self.ctx.fail(f"PANGAEA.{ds_id}", "discover", f"not underwater imagery (title: {title[:80]})")
            return
        ds = self._load_dataset(ds_id, g)
        if ds is None:
            return
        it = self._static_candidates(ds, g) if ds.kind == "static" else self._row_candidates(ds, g)
        cap = self._opt_int("max_per_child", None)
        yield from (islice(it, cap) if cap else it)

    def _static_candidates(self, ds: PanDataset, g: Group) -> Iterator[Candidate]:
        url = ds.static_url or ""
        if url in self._seen_urls:
            return
        self._seen_urls.add(url)
        self._videos[g.series_id] += 1
        ev = ds.events[0] if ds.events else None
        fn = os.path.basename(urlparse(url).path)
        yield Candidate(
            source=self.key,
            item_id=f"PANGAEA.{ds.dataset_id}/{fn}",
            media_type=media_type_for(url),
            media_url=url,
            origin_url=ds.landing,
            timestamp=ev.dt if ev else None,
            ext=_media_ext(url) or None,
            raw={"dataset_id": ds.dataset_id},
            extra=self._extra(ds, g, filename=fn, media_column="staticURL"),
        )

    @staticmethod
    def _media_columns(t: pangaea.PangaeaTable) -> list[tuple[str, str]]:
        """(column, kind) pairs in order of preference; kind is url / file / raw."""
        out: list[tuple[str, str]] = []
        cols = t.columns
        for kind, names in (("url", URL_COLUMNS), ("file", FILE_COLUMNS), ("raw", RAW_COLUMNS)):
            for n in names:
                for c in cols:
                    # "IMAGE (left camera (LC))" is a file column, "IMAGE (Size) [Bytes] ..." is not
                    qualified = kind == "file" and c.startswith(n + " (") and "[" not in c
                    if c == n or qualified or (kind != "file" and c.startswith(n)):
                        if (c, kind) not in out:
                            out.append((c, kind))
        return out

    def _pick_media(self, ds: PanDataset, row: dict[str, str], cols: list[tuple[str, str]]) -> tuple[str, str] | None:
        for col, kind in cols:
            val = (row.get(col) or "").strip()
            if not val:
                continue
            if val.lower().startswith(("http://", "https://")):
                url = val.replace("http://", "https://", 1) if urlparse(val).netloc.endswith("pangaea.de") else val
            elif kind == "url":
                continue
            elif "/" in val or val.startswith("."):
                continue
            else:
                url = DOWNLOAD_URL.format(id=ds.dataset_id, name=quote(val, safe=""))
            if _media_ext(url) in IMAGE_EXT | VIDEO_EXT:
                return url, col
        return None

    def _row_candidates(self, ds: PanDataset, g: Group) -> Iterator[Candidate]:
        t, geo = ds.table, ds.geo
        assert t is not None and geo is not None
        cols = self._media_columns(t)
        if self.options.get("prefer_raw") and any(k == "raw" for _, k in cols):
            cols = [c for c in cols if c[1] == "raw"] + [c for c in cols if c[1] != "raw"]
        keep_flagged = _flag(self.options.get("keep_flagged"), False)
        drop_sw = _flag(self.options.get("drop_sw_files"), False)
        entries: list[tuple[float, int, str, str, list[str], str | None]] = []
        dropped: Counter = Counter()
        local: set[str] = set()
        # first row of each file name (all rows, before any filter): a second file with the same name gets the
        # suffix ~<row>, whatever the options and the order, so item ids stay stable across runs
        first_row: dict[str, tuple[int, str]] = {}
        for i, row in enumerate(t.rows):
            pick = self._pick_media(ds, row, cols)
            if pick is None:
                dropped["no_media_file"] += 1
                continue
            url, col = pick
            first_row.setdefault(os.path.basename(urlparse(url).path), (i, url))
            if url in self._seen_urls or url in local:
                dropped["duplicate_url"] += 1
                continue
            flags = list(geo.flags[i])
            if drop_sw and os.path.basename(urlparse(url).path).startswith("SW_"):
                flags.append("sw_file")
            bad = [f for f in flags if f in DROP_FLAGS or f == "sw_file"]
            if bad and not keep_flagged:
                dropped.update(bad)
                continue
            local.add(url)
            tt = geo.times[i]
            stamp = (row.get(geo.time_col) or None) if geo.time_col else None
            entries.append((tt if tt is not None else math.inf, i, url, col, flags, stamp))
        if dropped:
            self.ctx.fail(
                f"PANGAEA.{ds.dataset_id}",
                "filter",
                f"dropped {sum(dropped.values())} flags on rows of {len(t.rows)}: {dict(dropped)}",
            )
        ds.table = None  # the per-row values that resolve_geo needs live in ds.geo: free the rows
        table_order = self.options.get("order", "spread") == "table"
        entries.sort(key=lambda e: (e[1],) if table_order else (e[0], e[1]))
        order = range(len(entries)) if table_order else spread_order(len(entries))
        video_cap = self._opt_int("max_videos_per_series", 2) or 0
        capped = 0
        for k in order:
            _, i, url, col, flags, stamp = entries[k]
            if url in self._seen_urls:
                continue
            mtype = media_type_for(url)
            if mtype == "video":
                # one video is up to a few GB: the per-series cap applies to table rows as well (ARTofMELT tables
                # list 15-20 videos each), not only to single-video datasets
                if self._videos[g.series_id] >= video_cap:
                    capped += 1
                    continue
                self._videos[g.series_id] += 1
            self._seen_urls.add(url)
            fn = os.path.basename(urlparse(url).path)
            first_i, first_url = first_row.get(fn, (i, url))
            item_id = f"PANGAEA.{ds.dataset_id}/{fn}" if (first_i == i or first_url == url) else f"PANGAEA.{ds.dataset_id}/{fn}~{i}"
            extra = self._extra(ds, g, filename=fn, media_column=col, row_index=i, flags=flags)
            ev = ds.event_at(i)
            if ev:
                extra["event"] = ev.base_label()
            yield Candidate(
                source=self.key,
                item_id=item_id,
                media_type=mtype,
                media_url=url,
                origin_url=ds.landing,
                timestamp=stamp,
                ext=_media_ext(url) or None,
                raw={"dataset_id": ds.dataset_id, "row_index": i},
                extra=extra,
            )
        if capped:
            self.ctx.fail(
                f"PANGAEA.{ds.dataset_id}", "filter", f"{capped} video rows skipped: max_videos_per_series={video_cap} reached"
            )

    def _extra(self, ds: PanDataset, g: Group, *, filename: str, media_column: str, row_index: int | None = None, flags: list[str] | None = None) -> dict[str, Any]:
        extra: dict[str, Any] = {
            "dataset_id": ds.dataset_id,
            "doi": ds.doi,
            "series": g.series_id,
            "parent_doi": f"{pangaea.DOI_PREFIX}{ds.parent_id}" if ds.parent_id else None,
            "platform": ds.platform or None,
            "media_column": media_column,
            "filename": filename,
        }
        if row_index is not None:
            extra["row_index"] = row_index
        if flags:
            extra["flags"] = flags
        return extra

    # ----------------------------------------------------------------- licence
    def _dataset(self, cand: Candidate) -> PanDataset:
        did = cand.extra.get("dataset_id") or cand.raw["dataset_id"]
        ds = self._datasets.get(did)
        if ds is None:
            ds = self._load_dataset(did, None)
        if ds is None:
            raise RuntimeError(f"PANGAEA.{did} metadata is not available")
        return ds

    def resolve_licence(self, cand: Candidate) -> Licence:
        ds = self._dataset(cand)
        text = ds.licence_text
        tier = ds.tier_override
        name = ds.licence_name
        if ds.override_note:
            name = f"{name} (unresolved: {ds.override_note})"
        attribution = ds.citation + (f" Licence: {text}" if text else "")
        return make_licence(
            name,
            level="record" if text else "unknown",
            url=ds.licence_uri or ds.landing,
            attribution=attribution,
            tier=tier,
        )

    # ----------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        ds = self._dataset(cand)
        idx = cand.extra.get("row_index")
        g = ds.geo
        doi = ds.doi

        # depth: the row first (sign normalised), else the event ELEVATION
        ev = ds.event_at(idx)
        depth, depth_src = None, ""
        d = g.depths[idx] if g is not None and idx is not None else None
        if d is not None:
            depth, depth_src = round(abs(d), 3), g.depth_col
        elif ev is not None and ev.depth() is not None and not ds.under_ice:
            # ELEVATION is the seafloor depth of the event: a fair camera depth for seafloor imaging, never for an
            # upward-looking camera under the sea ice
            depth, depth_src = ev.depth(), "Event ELEVATION"

        have_pos = bool(g and idx is not None and g.has_position(idx))
        if g is not None and idx is not None and "flags" not in cand.extra and g.flags[idx]:
            cand.extra["flags"] = list(g.flags[idx])
        comment = (ds.comment or "").lower()
        constant = have_pos and ("positioning failed" in comment or g.is_constant(idx))

        if have_pos and not constant:
            lat, lon = g.pairs[idx]
            unc = g.uncs[idx]
            if unc is None:
                if PLATFORM_AUV.search(ds.platform):
                    unc = UNC_AUV_M
                elif PLATFORM_TOWED.search(ds.platform):
                    unc = UNC_OFOS_M
                if g.ship_gps:  # ship's GPS, not the camera: layback heuristic of the research note
                    unc = max(200.0, min(2000.0, 0.5 * depth)) if depth is not None else SHIP_GPS_UNKNOWN_DEPTH_M
            run = g.run_s.get(idx, 0.0)
            if run > HELD_FIX_MIN_S:
                unc = float(round(max(unc or 0.0, HELD_FIX_SPEED_MS * run)))
            src = f"PANGAEA {doi} data table: Latitude/Longitude (WGS84)"
            if depth_src:
                src += f" + {depth_src}"
            if cand.media_type == "video":
                # one table row per video file: the fix is where the video starts, the frames cover a track
                return Geo(lat, lon, depth, "segment", src + " (position at the video start time)", True, unc)
            return Geo(lat, lon, depth, "image", src, False, unc)
        if have_pos and constant:
            lat, lon = g.pairs[idx]
            label = g.ev_labels[idx]
            if label and len(ds.events) > 1 and "positioning failed" not in comment:
                src = f"PANGAEA {doi} data table Latitude/Longitude, constant for event {label}"
            else:
                src = f"PANGAEA {doi} data table Latitude/Longitude, constant for whole deployment"
            if "positioning failed" in comment:
                src += " (Comment: positioning failed)"
            if depth_src == "Event ELEVATION":
                src += ", depth from Event ELEVATION"
            return Geo(lat, lon, depth, "station", src, True, UNC_STATION_POINT_M)
        if ev is not None and ev.lat is not None and ev.lon is not None:
            if ev.has_end:
                lat, lon = _midpoint(ev.lat, ev.lon, ev.lat2, ev.lon2)
                unc = round(ev.span_m / 2 + 500)
                where = "LATITUDE/LONGITUDE START/END"
            else:
                lat, lon, unc, where = ev.lat, ev.lon, UNC_STATION_POINT_M, "LATITUDE/LONGITUDE"
            src = f"PANGAEA {doi} Event(s) {ev.base_label()} {where} (event metadata)"
            if depth_src == "Event ELEVATION":
                src += ", depth from ELEVATION"
            return Geo(lat, lon, depth, "station", src, True, float(unc))
        checked = "Latitude/Longitude columns" if g and g.lat_col else "no Latitude/Longitude columns"
        return Geo.none(geo_source=f"PANGAEA {doi}: {checked} and no event position", depth_m=depth)

    # ----------------------------------------------------------------- media
    def estimate(self) -> dict[str, Any]:
        """Cheap totals: series / children from the (cached) series metadata and the ES hit count."""
        out: dict[str, Any] = {}
        groups = [g for g in self._base_groups() if g.children is None]
        children = restricted = 0
        today = date.today().isoformat()
        for g in groups:
            try:
                pm = self._panmd(g.series_id)
            except (HttpError, ET.ParseError, ValueError):
                continue
            self._series[g.series_id] = pm
            kids = pm.children or [g.series_id]
            if pm.restricted_reason(today):
                restricted += len(kids)
            else:
                children += len(kids)
        out["series"] = len(groups)
        out["children_open"] = children
        out["children_restricted"] = restricted
        if "series" not in self.options and "datasets" not in self.options:
            out["approx_open_images_research_note"] = 437000
        if _flag(self.options.get("discovery"), False):
            try:
                data = self._cached_post(ES_URL, "es_discovery_p000.json", self._es_body())
                total = data["hits"]["total"]
                out["es_discovery_datasets"] = total["value"] if isinstance(total, dict) else total
            except (HttpError, KeyError, ValueError) as exc:
                log.info("ES estimate failed: %s", exc)
        return out

    def _would_select(self, cand: Candidate) -> bool:
        cfg = self.ctx.config
        try:
            lic = self.resolve_licence(cand)
            geo = self.resolve_geo(cand)
        except Exception:
            return False
        if lic.tier not in cfg.selected_tiers:
            return False
        if geo.geo_precision == "none":
            return not cfg.require_geo
        return precision_at_least(geo.geo_precision, cfg.min_geo_precision)

    @contextmanager
    def _no_retries(self):
        saved = self.http.max_retries
        self.http.max_retries = 0
        try:
            yield
        finally:
            self.http.max_retries = saved

    def _warm(self, cand: Candidate) -> None:
        """HEAD the next files so that tape recalls overlap (a HEAD triggers the recall)."""
        n = self._opt_int("stage_batch", 20) or 0
        if n <= 0 or self.ctx.dry_run or not self._staging_seen:
            return
        todo = []
        for c in [cand, *self._lookahead]:
            if len(todo) > n:
                break
            if c.media_type != "image" or c.media_url in self._warmed:
                continue
            if urlparse(c.media_url).netloc not in MEDIA_HOSTS or not self._would_select(c):
                continue
            todo.append(c)
        for c in todo:
            self._warmed[c.media_url] = self._head_state(c.media_url)[0]

    def resolve_media(self, cand: Candidate) -> MediaRef:
        self._warm(cand)
        return MediaRef(url=cand.media_url, ext=cand.ext or guess_ext(cand.media_url, cand.media_type))

    def _head_state(self, url: str) -> tuple[bool, float]:
        """(file is on disk, seconds the server asks us to wait). One HEAD, no retries; it also triggers a tape recall."""
        try:
            with self._no_retries():
                resp = self.http.request("HEAD", url, kind="media")
            try:
                ctype = (resp.headers.get("Content-Type") or "").lower()
                retry = float(resp.headers.get("Retry-After") or 0)
                return resp.status_code == 200 and not ctype.startswith("text/html"), retry
            finally:
                resp.close()
        except (HttpError, ValueError):
            return False, 0.0

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        """Download with tape-staging handling.

        HTTP 503 (``Retry-After``) or an HTML page means "loading from tape" (minutes). The file is then
        polled with HEAD every max(Retry-After, 15) s and fetched once it answers 200 with a non-HTML type;
        an HTML body is never kept. A file that a warm-up HEAD already asked for is polled before the first GET.
        """
        deadline = time.monotonic() + float(self.options.get("stage_timeout_s") or 900)
        staged = self._warmed.get(ref.url) is False
        wait = 15.0
        while True:
            if staged:
                ready, retry = self._head_state(ref.url)
                if not ready:
                    if time.monotonic() >= deadline:
                        raise HttpError(ref.url, 503, "still on tape after stage_timeout_s")
                    time.sleep(max(15.0, retry))
                    continue
            try:
                nbytes, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)
            except HttpError as exc:
                if exc.status != 503 or time.monotonic() >= deadline:
                    raise
                self._staging_seen = staged = True
                log.info("%s is on tape (HTTP 503); polling every %.0fs", ref.url, wait)
                time.sleep(wait)
                continue
            if _looks_like_html(dest):
                dest.unlink(missing_ok=True)
                self._staging_seen = staged = True
                if time.monotonic() >= deadline:
                    raise HttpError(ref.url, 503, "HTML page (tape staging) instead of media")
                log.info("%s returned an HTML page (tape staging); polling every %.0fs", ref.url, wait)
                time.sleep(wait)
                continue
            return nbytes, sha
