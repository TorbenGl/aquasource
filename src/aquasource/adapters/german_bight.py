"""German Bight seafloor drift videos on PANGAEA (R/V Heincke HE415/HE416, HE436, Helgoland 2011, six sibling cruises).

Every table is a PANGAEA data matrix with one ship-GPS position per video file
(``https://doi.pangaea.de/10.1594/PANGAEA.<id>?format=textfile``). All records are CC BY
(4.0 for the Heincke tables, 3.0 for Helgoland), read at record level, tier B. All geo is
``station`` precision with ``geo_inferred`` true: one position applies to every frame of a
video. The media are anonymous HTTPS files on hs.pangaea.de (Range supported).

Sources (research/german_bight.md)
    907386   HE415 / HE416, Feb-Mar 2014: 87 Kongsberg AVI + 55 GoPro MP4 (LRV / THM sidecars are skipped)
    909999   HE436, Nov 2014: 45 AVI + 44 GoPro MP4
    831731   Helgoland, Jun 2011: 13 MPEG-2 transects (start and end position)
    siblings (``siblings=true``, default): 907382 HE400 (114 MPG), 910009 HE474 and 910939 HE478
             (Dogger Bank, AVI + MP4), 907338 HE501 (MP4 + AVI), 907337 HE502 (3 stations, MP4 +
             ASF), 907340 HE505 (MP4 + ASF). Same authors, same format, CC BY 4.0. Their media
             columns are named differently, so the role of a file comes from its extension.

How it works
    * ``discover`` reads only the table exports (metadata/raw/pangaea_<id>.tab) and, for the
      checks below, the record JSON-LD and the DSHIP event lists. It yields one candidate per
      video file (``PANGAEA.<id>/<file name>``, stable across runs). Roles: ``station`` for the
      Kongsberg / C-Technics camera files (AVI, MPG, ASF, 0.03-0.3 GB), ``gopro`` for MP4
      (1080p, 1.3-2.2 GB). ``.LRV`` (GoPro proxy) and ``.THM`` (thumbnail) are never listed.
      A station video and its GoPro clip share ``extra.station_id`` (so they go to the same
      split); ``Spots_01-1/-2/-3`` and ``He436_012-1/-2`` are parts of one station.
    * resolve_geo follows the "resolve_geo recipe" of the research note. Columns are read by
      name (907386 has Longitude before Latitude). Heincke rows: ``Latitude`` / ``Longitude``,
      depth ``Bathy depth [m]`` (positive down; empty in He436_012-1/-2), uncertainty 200 m
      (drift 30-240 m, layback, GPS). Helgoland: midpoint of start (``Latitude`` /
      ``Longitude``) and end (``Latitude 2`` / ``Longitude 2``), uncertainty = half the
      transect length + 30 m (62-139 m), no depth. Coordinates outside 53-56.5 N, 3-9 E, or
      missing, give ``geo_precision`` none; nothing is ever invented.
    * GoPro clips are mapped to their table row by the station token in the file name, not by
      the row they are listed in: PANGAEA.907386 lists ``HE415_Greifer_AG1_006_HD.*`` in row
      AG1_005, 2.1 km from the real station (the MP4 ``mvhd`` time equals row AG1_006). Such a
      file carries ``extra.row_remapped``; a GoPro file with no row of its own has no position.
    * QC against the DSHIP "Video camera" events of the cruise (``qc=true``, default): the event
      whose start - 5 min <= row Date/Time <= end + 5 min is looked up; with ``d`` = the smaller
      distance from the table position to the event start / end, ``d > 300 m`` keeps the table
      coordinate, sets ``geo_uncertainty_m = round(d + 200, -1)`` and writes the disagreement
      into ``geo_source`` and ``extra`` (5 known longitude typos, 0.5-4.3 km, e.g. He436_029
      3,226 m off). No event, no change. HE505 (907340) times are not acquisition times
      (13 min for stations up to 30 km apart): its ``timestamp`` is left empty.
    * Licence: the ``License:`` line of the record header is cross-checked with the JSON-LD
      ``license`` and ``conditionsOfAccess`` (``licence_check=true``, default). A contradiction
      makes the dataset tier U, a restricted record is skipped. Attribution is the record's
      ``Citation:`` line plus ``CC BY <version>``.
    * Budget-friendly order (``order=spread``, default): all station videos first, then further
      parts of a station, then GoPro clips (only with ``media=gopro|all``); inside each phase a
      round robin over the cruises (HE415, HE416, HE436, Helgoland2011, ...) and, inside a
      cruise, over areas (Spots / AG1 / AG3 / AG4 for 907386, a 0.1 degree cell elsewhere), and
      inside an area in a spread order (first, last, middle, ...), so any prefix of the stream
      covers the whole region and period instead of the first N rows of the first table.
    * Tape: about 40 % of the files sit on tape. The first request (even a HEAD) answers HTTP
      503 with ``Retry-After`` and recalls the file; it is online after about 7-15 min. The
      project Http client gives up after a few retries, so ``fetch_media`` polls with HEAD (every
      ``stage_poll_s``, up to ``stage_timeout_s``), never keeps an HTML body, and once staging
      has been seen it HEADs the next ``stage_batch`` candidates so that recalls overlap.
      Whatever still fails is listed in metadata/failures.jsonl: rerun later.
    * Politeness: 1 request per second and host (doi.pangaea.de, www.pangaea.de, hs.pangaea.de),
      one transfer at a time. Downloaded video is data, it is never executed.
    * Not done here: trimming the first / last 60 s of a clip (deck and descent frames; hints
      ``extra.trim_start_s`` / ``trim_end_s``), dark / turbid frame filters, and Helgoland depth
      enrichment from PANGAEA.831686. Frame extraction is the job of ``aquasource frames``.

Adapter options (``--opt key=value``; values are JSON or comma separated lists)
    dataset_ids     explicit PANGAEA ids to read (default: the three seed tables, plus the six
                    siblings unless ``siblings=false``).
    siblings        false limits the default list to 907386, 909999 and 831731 (default true).
    cruises         only these groups, e.g. ``["HE436","Helgoland2011"]`` (group = cruise from the
                    ``Event`` column / header, ``Helgoland2011`` for 831731, ``PANGAEA.<id>`` else).
    media           ``station`` (default: AVI / MPG / ASF, about 8 GB for ~420 files), ``gopro``
                    (MP4 only, about 190 GB) or ``all``.
    order           ``spread`` (default) or ``table`` (table and column order).
    qc              false skips the DSHIP event check (default true).
    qc_reject_m     > 0: a row whose table position differs from its DSHIP event by more than this
                    many metres gets ``geo_precision`` none instead of an inflated uncertainty
                    (default 0 = keep, recipe step 6).
    licence_check   false skips the JSON-LD cross-check (default true).
    stage_batch     HEAD look-ahead per tape recall batch (default 10, 0 = off).
    stage_timeout_s give up on one tape file after this long (default 1800).
    stage_poll_s    seconds between tape polls (default 30).
    refresh_metadata  core option: re-download cached metadata.
"""

from __future__ import annotations

import logging
import math
import os
import re
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence
from urllib.parse import urlparse

from ..core.geo import depth_from, haversine_m, parse_time, to_float
from ..core.http import HttpError
from ..core.licence import classify, make_licence, most_specific
from ..core.schema import Candidate, Geo, Licence
from ..providers import pangaea
from .base import Adapter, MediaRef, guess_ext, register

log = logging.getLogger(__name__)

SEED_IDS = ("907386", "909999", "831731")
SIBLING_IDS = ("907382", "910009", "910939", "907338", "907337", "907340")
GROUP_LABELS = {"831731": "Helgoland2011"}
# Tables whose files are mapped to rows by the station token of the file name (research: 907386 lists a GoPro clip in the wrong row).
TOKEN_MAPPED = {"907386"}
# HE505: 26 Date/Time values fall in 13 minutes for stations up to 30 km apart, so they are not acquisition times.
NO_TIME_IDS = {"907340"}

EVENTS_URL = (
    "https://www.pangaea.de/ddi/{cruise}.tab?retr=events/Heincke/{cruise}.retr"
    "&conf=events/CruiseReportText.conf&format=textfile"
)
HEINCKE_UNCERTAINTY_M = 200.0
TRANSECT_FALLBACK_LENGTH_M = 440.0  # twice the longest Helgoland transect, used when the end position is missing
BOX = (53.0, 56.5, 3.0, 9.0)  # lat_min, lat_max, lon_min, lon_max: German Bight and Dogger Bank sanity box
QC_WINDOW_S = 300.0
QC_THRESHOLD_M = 300.0
TRIM_S = 60

SKIP_EXT = {"lrv", "thm"}  # GoPro low-res proxy and thumbnail
GOPRO_EXT = {"mp4"}
STATION_EXT = {"avi", "mpg", "mpeg", "asf", "mov", "mkv", "wmv", "m4v", "mts"}
MEDIA_HOSTS = {"hs.pangaea.de"}
# Projected sizes (research/german_bight.md, HEAD measurements) for estimate().
MEAN_BYTES = {"avi": 32e6, "mp4": 1.72e9}
DEFAULT_BYTES = 32e6

MEDIA_MODES = ("station", "gopro", "all")
ORDERS = ("spread", "table")


@dataclass
class _Unit:
    """One media file of one table row (metadata only)."""

    ds_id: str
    group: str
    cruise: str | None
    role: str  # station | gopro
    part: int | None
    station: str
    area: str
    url: str
    ext: str
    row: dict[str, str]
    row_index: int
    listing_index: int
    matched: bool
    token: str

    @property
    def group_key(self) -> tuple[str, str]:
        return (self.ds_id, self.group)


@dataclass
class _Event:
    label: str
    t0: float
    t1: float
    start: tuple[float, float]
    end: tuple[float, float] | None


def _spread_order(n: int) -> list[int]:
    """0..n-1 in a spread order (first, last, middle, quarters, ...): any prefix is evenly spaced."""
    if n <= 2:
        return list(range(n))
    bits = (n - 1).bit_length()
    return sorted(range(n), key=lambda i: int(format(i, f"0{bits}b")[::-1], 2))


def _round_robin(lists: Sequence[Sequence[Any]]) -> Iterator[Any]:
    iters = [iter(x) for x in lists]
    while iters:
        alive = []
        for it in iters:
            try:
                yield next(it)
            except StopIteration:
                continue
            alive.append(it)
        iters = alive


def _role(ext: str) -> str | None:
    if ext in SKIP_EXT:
        return None
    if ext in GOPRO_EXT:
        return "gopro"
    if ext in STATION_EXT:
        return "station"
    return None


def _file_tokens(stem: str) -> str:
    """File name without cruise prefix, GoPro marker and ``_HD``: ``HE415_Greifer_AG1_006_HD`` -> ``Greifer_AG1_006``."""
    parts = stem.split("_")
    if parts and re.fullmatch(r"(?i)he\d{3}", parts[0]):
        parts = parts[1:]
    if parts and parts[-1].lower() == "hd":
        parts = parts[:-1]
    parts = [p for p in parts if p.lower() != "gopro"]
    return "_".join(parts)


def _looks_like_html(path: Path) -> bool:
    try:
        with open(path, "rb") as fh:
            head = fh.read(1024)
    except OSError:
        return False
    return head.lstrip()[:1] == b"<" or b"<html" in head.lower()


@register
class GermanBightAdapter(Adapter):
    key = "german_bight"
    name = "German Bight seafloor video (HE415/HE416, HE436, Helgoland 2011)"
    homepage = "https://doi.pangaea.de/10.1594/PANGAEA.907386"
    citation = (
        "Papenmeier & Hass (2019), PANGAEA.907386 and PANGAEA.909999; Mielck et al. (2014), PANGAEA.831731; "
        "see each sample's attribution for the exact dataset citation"
    )
    media_types = ("video",)
    env_vars: tuple[str, ...] = ()
    manual_steps = ""
    host_intervals = {"doi.pangaea.de": 1.0, "www.pangaea.de": 1.0, "hs.pangaea.de": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._tables: dict[str, pangaea.PangaeaTable] = {}
        self._units: list[_Unit] | None = None
        self._jsonld: dict[str, dict | None] = {}
        self._licences: dict[str, Licence] = {}
        self._events: dict[str, list[_Event]] = {}
        self._lookahead: deque[Candidate] = deque()
        self._warmed: dict[str, bool] = {}
        self._sizes: dict[str, int] = {}
        self._staging_seen = False

    # ---------------------------------------------------------------- options
    def _flag(self, name: str, default: bool) -> bool:
        v = self.options.get(name, default)
        if isinstance(v, str):
            return v.strip().lower() not in ("", "0", "false", "no", "off")
        return bool(v)

    def _num(self, name: str, default: float) -> float:
        v = self.options.get(name)
        try:
            return float(v) if v not in (None, "") else default
        except (TypeError, ValueError):
            return default

    def _list(self, name: str) -> list[str]:
        v = self.options.get(name)
        if v in (None, ""):
            return []
        if isinstance(v, (str, int)):
            v = str(v).split(",")
        return [str(x).strip() for x in v if str(x).strip()]

    def check_ready(self) -> list[str]:
        problems = super().check_ready()
        media = str(self.options.get("media", "station")).lower()
        if media not in MEDIA_MODES:
            problems.append(f"option media={media!r} must be one of {', '.join(MEDIA_MODES)}")
        order = str(self.options.get("order", "spread")).lower()
        if order not in ORDERS:
            problems.append(f"option order={order!r} must be one of {', '.join(ORDERS)}")
        return problems

    @contextmanager
    def _quick(self):
        """At most one retry for optional metadata (event lists, JSON-LD): a missing one must not stall the run."""
        saved = self.http.max_retries
        self.http.max_retries = min(saved, 1)
        try:
            yield
        finally:
            self.http.max_retries = saved

    # ------------------------------------------------------------------ tables
    def ids(self) -> list[str]:
        explicit = self._list("dataset_ids")
        ids = explicit or [*SEED_IDS, *(SIBLING_IDS if self._flag("siblings", True) else ())]
        out: list[str] = []
        for i in ids:
            ds = pangaea.dataset_id(i)
            if ds and ds not in out:
                out.append(ds)
        return out

    def table(self, ds_id: str) -> pangaea.PangaeaTable:
        if ds_id not in self._tables:
            text = self.ctx.cached_text(pangaea.textfile_url(ds_id), f"pangaea_{ds_id}.tab")
            self._tables[ds_id] = pangaea.parse_textfile(text, ds_id)
        return self._tables[ds_id]

    def _record_json(self, ds_id: str) -> dict | None:
        """JSON-LD of the record (licence and access terms), or None when not read."""
        if ds_id not in self._jsonld:
            doc = None
            if self._flag("licence_check", True):
                try:
                    with self._quick():
                        doc = self.ctx.cached_json(pangaea.landing_url(ds_id) + "?format=metadata_jsonld", f"pangaea_{ds_id}.jsonld")
                except (HttpError, ValueError) as exc:
                    self.ctx.fail(f"PANGAEA.{ds_id}", "licence_check", f"JSON-LD not read, header licence only: {exc}")
            self._jsonld[ds_id] = doc if isinstance(doc, dict) else None
        return self._jsonld[ds_id]

    @staticmethod
    def _jsonld_licence(doc: dict) -> str | None:
        v = doc.get("license")
        if isinstance(v, list):
            v = v[0] if v else None
        if isinstance(v, dict):
            v = v.get("@id") or v.get("url")
        return v if isinstance(v, str) and v.strip() else None

    def _restricted(self, ds_id: str) -> str | None:
        doc = self._record_json(ds_id)
        if not doc:
            return None
        access = doc.get("conditionsOfAccess")
        if isinstance(access, str) and access.strip().lower() not in ("", "unrestricted"):
            return f"conditionsOfAccess is {access!r}"
        if doc.get("isAccessibleForFree") is False:
            return "isAccessibleForFree is false"
        return None

    def _cruise(self, t: pangaea.PangaeaTable, row: dict[str, str]) -> str | None:
        m = re.match(r"(HE\d{3})\b", row.get("Event", ""))
        if m:
            return m.group(1)
        found = set(re.findall(r"CAMPAIGN:\s*(HE\d{3})\b", " ".join(t.meta.get("Event(s)", []))))
        return next(iter(found)) if len(found) == 1 else None

    # -------------------------------------------------------------------- plan
    def _plan(self) -> list[_Unit]:
        """Every media file of every readable table, in table and column order."""
        if self._units is not None:
            return self._units
        units: list[_Unit] = []
        seen: set[str] = set()
        today = date.today().isoformat()
        for ds_id in self.ids():
            try:
                t = self.table(ds_id)
            except HttpError as exc:
                self.ctx.fail(f"PANGAEA.{ds_id}", "discover", f"table not read: {exc}")
                continue
            if t.moratorium_until and t.moratorium_until > today:
                self.ctx.fail(f"PANGAEA.{ds_id}", "licence", f"moratorium until {t.moratorium_until}")
                continue
            why = self._restricted(ds_id)
            if why:
                self.ctx.fail(f"PANGAEA.{ds_id}", "licence", f"record is not open: {why}")
                continue
            cols = [c for c in t.columns if c.lower().startswith("url")]
            if not cols:
                self.ctx.fail(f"PANGAEA.{ds_id}", "discover", "no URL column in the table")
                continue
            token_rows: dict[str, int] | None = None
            if ds_id in TOKEN_MAPPED and "Content" in t.columns:
                token_rows = {re.sub(r"^Profile\s+", "", r.get("Content", "")).strip(): i for i, r in enumerate(t.rows)}
            for i, row in enumerate(t.rows):
                for c in cols:
                    url = row.get(c, "")
                    if not url.startswith("http") or url in seen:
                        continue
                    path = urlparse(url).path
                    ext = os.path.splitext(path)[1].lstrip(".").lower()
                    role = _role(ext)
                    if role is None:
                        continue
                    seen.add(url)
                    units.append(self._unit(ds_id, t, i, row, c, url, ext, role, token_rows))
        self._units = units
        return units

    def _unit(self, ds_id, t, i, row, col, url, ext, role, token_rows) -> _Unit:
        stem = os.path.splitext(os.path.basename(urlparse(url).path))[0]
        token = _file_tokens(stem)
        use_i, use_row, matched = i, row, True
        if token_rows is not None:
            j = token_rows.get(token)
            if j is None:
                matched = False
            else:
                use_i, use_row = j, t.rows[j]
        cruise = self._cruise(t, use_row)
        group = cruise or GROUP_LABELS.get(ds_id) or f"PANGAEA.{ds_id}"
        # part: "(part N)" column, else a "-N" suffix of a Heincke file name.
        part: int | None = None
        rest = token
        m = re.search(r"part\s*(\d+)", col, re.I)
        if m:
            part = int(m.group(1))
            if rest.endswith(f"_{part}"):
                rest = rest[: -len(f"_{part}")]
        elif cruise:
            m = re.search(r"-(\d{1,2})$", rest)
            if m:
                part = int(m.group(1))
                rest = rest[: m.start()]
        if token_rows is not None:
            words = rest.split("_")
            area = words[1] if words[0].lower() == "greifer" and len(words) > 2 else words[0]
        else:
            lat, lon = to_float(use_row.get("Latitude")), to_float(use_row.get("Longitude"))
            area = "none" if lat is None or lon is None else f"{math.floor(lat * 10) / 10:.1f}N{math.floor(lon * 10) / 10:.1f}E"
        return _Unit(
            ds_id=ds_id,
            group=group,
            cruise=cruise,
            role=role,
            part=part,
            station=f"{cruise or group}/{rest.lower()}",
            area=area,
            url=url,
            ext=ext,
            row=use_row,
            row_index=use_i,
            listing_index=i,
            matched=matched,
            token=token,
        )

    def _wanted(self, u: _Unit) -> bool:
        media = str(self.options.get("media", "station")).lower()
        if media == "station" and u.role != "station":
            return False
        if media == "gopro" and u.role != "gopro":
            return False
        cruises = {c.lower() for c in self._list("cruises")}
        return not cruises or u.group.lower() in cruises

    # ------------------------------------------------------------------- order
    def _ordered(self) -> list[_Unit]:
        units = [u for u in self._plan() if self._wanted(u)]
        if str(self.options.get("order", "spread")).lower() == "table":
            return units
        phases: list[list[_Unit]] = [[], [], [], []]
        for u in units:
            first = (u.part or 1) == 1
            phases[(0 if first else 1) if u.role == "station" else (2 if first else 3)].append(u)
        out: list[_Unit] = []
        for phase in phases:
            out.extend(self._spread(phase))
        return out

    @staticmethod
    def _spread(units: list[_Unit]) -> list[_Unit]:
        groups: dict[tuple[str, str], dict[str, list[_Unit]]] = {}
        for u in units:
            groups.setdefault(u.group_key, {}).setdefault(u.area, []).append(u)
        per_group = []
        for areas in groups.values():
            lists = [[lst[i] for i in _spread_order(len(lst))] for lst in areas.values()]
            per_group.append(list(_round_robin(lists)))
        return list(_round_robin(per_group))

    # --------------------------------------------------------------- interface
    def discover(self) -> Iterable[Candidate]:
        self._lookahead.clear()  # a previous run may have stopped at its budget with candidates still buffered
        stream = (self._candidate(u) for u in self._ordered())
        n = int(self._num("stage_batch", 10))
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

    def _candidate(self, u: _Unit) -> Candidate:
        extra: dict[str, Any] = {
            "pangaea_id": u.ds_id,
            "group": u.group,
            "cruise": u.cruise,
            "station_id": u.station,
            "role": u.role,
            "part": u.part,
            "area": u.area,
            "row_index": u.row_index,
            "trim_start_s": TRIM_S,
            "trim_end_s": TRIM_S,
        }
        if u.listing_index != u.row_index:
            extra["row_remapped"] = True
            extra["listing_row_index"] = u.listing_index
        if u.role == "gopro":
            extra["camera_clock"] = "CET (UTC+1)"
        size_kb = to_float(u.row.get("File size [kByte]"))
        if size_kb:
            extra["size_kb"] = size_kb
        if u.ds_id in NO_TIME_IDS:
            extra["time_note"] = "table Date/Time is not an acquisition time"
        return Candidate(
            source=self.key,
            item_id=f"PANGAEA.{u.ds_id}/{os.path.basename(urlparse(u.url).path)}",
            media_type="video",
            media_url=u.url,
            origin_url=pangaea.landing_url(u.ds_id),
            timestamp=None if u.ds_id in NO_TIME_IDS else (u.row.get("Date/Time") or None),
            ext=u.ext,
            raw={
                "dataset_id": u.ds_id,
                "row": u.row,
                "cruise": u.cruise,
                "row_matched": u.matched,
                "station_token": u.token,
                "listing_row_index": u.listing_index,
            },
            extra=extra,
        )

    def estimate(self) -> dict[str, Any]:
        units = [u for u in self._plan() if self._wanted(u)]
        total = 0.0
        for u in units:
            size_kb = to_float(u.row.get("File size [kByte]"))
            total += size_kb * 1024 if size_kb else MEAN_BYTES.get(u.ext, DEFAULT_BYTES)
        return {
            "videos": len(units),
            "station_videos": sum(1 for u in units if u.role == "station"),
            "gopro_videos": sum(1 for u in units if u.role == "gopro"),
            "tables": len({u.ds_id for u in units}),
            "approx_gb": round(total / 1e9, 1),
        }

    # ----------------------------------------------------------------- licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        return self._licence(cand.raw["dataset_id"])

    def _licence(self, ds_id: str) -> Licence:
        if ds_id in self._licences:
            return self._licences[ds_id]
        t = self.table(ds_id)
        # No file-level licence exists (the media are served with content-disposition only) and the
        # collection (831732) agrees with the record, so the record header is the most specific level.
        level, text = most_specific(("file", None), ("record", t.licence_text), ("collection", None))
        name, url = t.licence_name, t.licence_url
        doc = self._record_json(ds_id)
        j_url = self._jsonld_licence(doc) if doc else None
        if not (name or url) and j_url:  # header silent, the record JSON-LD states the licence (still record level)
            name, url, level = j_url, j_url, "record"
        tier = classify(name or url)
        if j_url:
            j_tier = classify(j_url)
            if j_tier != "U" and tier != "U" and j_tier != tier:
                name = f"conflict: header {name!r} vs JSON-LD {j_url!r}"
                tier = "U"
        m = re.search(r"licenses/by/(\d\.\d)", url or j_url or "")
        short = f"CC BY {m.group(1)}" if m else (name or "")
        attribution = f"{re.sub(r'[\s,;.]+$', '', t.citation)}. {short}".strip()
        lic = make_licence(
            name,
            level=level,
            url=url or j_url or pangaea.landing_url(ds_id),
            attribution=attribution,
            tier=tier,
        )
        self._licences[ds_id] = lic
        return lic

    # --------------------------------------------------------------------- geo
    def _in_box(self, lat: float, lon: float) -> bool:
        return BOX[0] <= lat <= BOX[1] and BOX[2] <= lon <= BOX[3]

    def resolve_geo(self, cand: Candidate) -> Geo:
        ds_id = cand.raw["dataset_id"]
        row = cand.raw["row"]
        depth = depth_from(row.get("Bathy depth [m]"))  # never the Elevation coverage line
        if cand.raw.get("row_matched") is False:
            return Geo.none(
                geo_source=f"PANGAEA.{ds_id}: no table row for station token {cand.raw.get('station_token')!r} (file listed in another row)",
                depth_m=None,
            )
        lat, lon = to_float(row.get("Latitude")), to_float(row.get("Longitude"))
        if lat is None or lon is None:
            return Geo.none(geo_source=f"PANGAEA.{ds_id}: no Latitude/Longitude in row", depth_m=depth)

        if "Latitude 2" in row or "Longitude 2" in row:  # a transect with start and end position
            lat2, lon2 = to_float(row.get("Latitude 2")), to_float(row.get("Longitude 2"))
            if lat2 is not None and lon2 is not None:
                length = haversine_m(lat, lon, lat2, lon2)
                lat, lon = round((lat + lat2) / 2, 7), round((lon + lon2) / 2, 7)
                source = (
                    f"PANGAEA.{ds_id} midpoint of Latitude/Longitude (start) and Latitude 2/Longitude 2 (end) "
                    "of the video transect, WGS 84"
                )
            else:
                length = TRANSECT_FALLBACK_LENGTH_M
                source = f"PANGAEA.{ds_id} Latitude/Longitude (start of the video transect; no end position in the row), WGS 84"
            uncertainty = float(math.floor(length / 2 + 30 + 0.5))
            if not self._in_box(lat, lon):
                return self._outside(ds_id, lat, lon, depth)
            return Geo(lat, lon, depth, "station", source, True, uncertainty)

        if not self._in_box(lat, lon):
            return self._outside(ds_id, lat, lon, depth)
        source = f"PANGAEA.{ds_id} data table columns Latitude/Longitude (ship GPS at drift-video station, WGS 84)"
        if depth is not None:
            source += "; depth: Bathy depth [m]"
        uncertainty = HEINCKE_UNCERTAINTY_M
        qc = self._qc(cand, row, lat, lon)
        if qc is not None:
            dist, label = qc
            cand.extra["qc_event"] = label
            cand.extra["qc_distance_m"] = round(dist)
            if dist > QC_THRESHOLD_M:
                note = f"QC: table position differs by {round(dist)} m from DSHIP event {label}"
                cand.extra["qc_flag"] = "position_disagrees_with_dship_event"
                reject = self._num("qc_reject_m", 0)
                if reject > 0 and dist > reject:
                    return Geo.none(geo_source=f"PANGAEA.{ds_id}: rejected, {note}", depth_m=depth)
                uncertainty = float(round(dist + 200, -1))
                source += f"; {note}"
        return Geo(lat, lon, depth, "station", source, True, uncertainty)

    def _outside(self, ds_id: str, lat: float, lon: float, depth: float | None) -> Geo:
        return Geo.none(
            geo_source=(
                f"PANGAEA.{ds_id}: position ({lat}, {lon}) outside the German Bight sanity box "
                f"{BOX[0]}-{BOX[1]} N, {BOX[2]}-{BOX[3]} E"
            ),
            depth_m=depth,
        )

    # --------------------------------------------------------------------- QC
    def _event_list(self, cruise: str) -> list[_Event]:
        if cruise in self._events:
            return self._events[cruise]
        events: list[_Event] = []
        if re.fullmatch(r"HE\d{3}", cruise):
            try:
                with self._quick():
                    text = self.ctx.cached_text(EVENTS_URL.format(cruise=cruise), f"dship_events_{cruise}.tab")
            except (HttpError, ValueError) as exc:
                self.ctx.fail(cruise, "qc_events", f"DSHIP event list not read, no position QC: {exc}")
                text = ""
            for r in pangaea.parse_textfile(text).rows:
                if (r.get("Method/Device") or "").strip().lower() != "video camera":
                    continue
                t0 = parse_time(r.get("Date/Time"))
                lat, lon = to_float(r.get("Latitude")), to_float(r.get("Longitude"))
                if t0 is None or lat is None or lon is None:
                    continue
                t1 = parse_time(r.get("Date/Time end")) or t0
                lat2, lon2 = to_float(r.get("Latitude end")), to_float(r.get("Longitude end"))
                end = (lat2, lon2) if lat2 is not None and lon2 is not None else None
                events.append(_Event(r.get("Event label", ""), t0, t1, (lat, lon), end))
        self._events[cruise] = events
        return events

    def _qc(self, cand: Candidate, row: dict[str, str], lat: float, lon: float) -> tuple[float, str] | None:
        """(distance in m, event label) of the nearest matching DSHIP video event, or None."""
        cruise = cand.raw.get("cruise")
        if not cruise or not self._flag("qc", True) or cand.raw["dataset_id"] in NO_TIME_IDS:
            return None
        t = parse_time(row.get("Date/Time"))
        if t is None:
            return None
        best: tuple[float, str] | None = None
        for ev in self._event_list(cruise):
            if ev.t0 - QC_WINDOW_S <= t <= ev.t1 + QC_WINDOW_S:
                d = haversine_m(lat, lon, *ev.start)
                if ev.end:
                    d = min(d, haversine_m(lat, lon, *ev.end))
                if best is None or d < best[0]:
                    best = (d, ev.label)
        return best

    # ------------------------------------------------------------------- media
    def _head_state(self, url: str) -> tuple[int | None, bool, float]:
        """(status, file is online, seconds the server asks us to wait). One HEAD without retries.

        A HEAD on a tape file triggers the recall (no login needed). Also records ``content-length``.
        """
        saved = self.http.max_retries
        self.http.max_retries = 0
        try:
            resp = self.http.request("HEAD", url, kind="media")
        except HttpError:
            return None, False, 0.0
        finally:
            self.http.max_retries = saved
        try:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            try:
                retry = float(resp.headers.get("Retry-After") or 0)
            except ValueError:
                retry = 0.0
            online = resp.status_code == 200 and not ctype.startswith("text/html")
            if online and (resp.headers.get("Content-Length") or "").isdigit():
                self._sizes[url] = int(resp.headers["Content-Length"])
            return resp.status_code, online, retry
        finally:
            resp.close()

    def _warm(self, cand: Candidate) -> None:
        """HEAD the next files so that tape recalls overlap instead of queueing (only once staging has been seen)."""
        n = int(self._num("stage_batch", 10))
        if n <= 0 or self.ctx.dry_run or not self._staging_seen:
            return
        todo: list[Candidate] = []
        for c in [cand, *self._lookahead]:
            if len(todo) > n:
                break
            if c.media_url in self._warmed or urlparse(c.media_url).netloc not in MEDIA_HOSTS:
                continue
            if c.raw.get("row_matched") is False or self.resolve_licence(c).tier not in self.ctx.config.selected_tiers:
                continue
            todo.append(c)
        for c in todo:
            self._warmed[c.media_url] = self._head_state(c.media_url)[1]

    def resolve_media(self, cand: Candidate) -> MediaRef:
        self._warm(cand)
        return MediaRef(
            url=cand.media_url,
            ext=cand.ext or guess_ext(cand.media_url, cand.media_type),
            expected_bytes=self._sizes.get(cand.media_url),
        )

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        """Download with tape-staging handling.

        HTTP 503 (``Retry-After``) or an HTML page means "loading from tape" (minutes). The file is then
        polled with HEAD every max(``stage_poll_s``, Retry-After) s and fetched once it answers 200 with a
        non-HTML type; an HTML body is never kept. Gives up after ``stage_timeout_s`` (default 1800 s).
        """
        deadline = time.monotonic() + self._num("stage_timeout_s", 1800)
        poll = max(1.0, self._num("stage_poll_s", 30))
        staged = self._warmed.get(ref.url) is False
        while True:
            if staged:
                status, online, retry = self._head_state(ref.url)
                if status is not None and status >= 400 and status != 503:
                    raise HttpError(ref.url, status, "HEAD failed while waiting for tape staging")
                if not online:
                    if time.monotonic() >= deadline:
                        raise HttpError(ref.url, 503, "still on tape after stage_timeout_s")
                    time.sleep(max(poll, retry))
                    continue
                staged = False
                ref.expected_bytes = ref.expected_bytes or self._sizes.get(ref.url)
            try:
                nbytes, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)
            except HttpError as exc:
                if exc.status != 503 or time.monotonic() >= deadline:
                    raise
                self._staging_seen = staged = True
                log.info("%s is on tape (HTTP 503); polling every %.0fs", ref.url, poll)
                time.sleep(poll)
                continue
            if _looks_like_html(dest):
                dest.unlink(missing_ok=True)
                self._staging_seen = staged = True
                if time.monotonic() >= deadline:
                    raise HttpError(ref.url, 503, "HTML page (tape staging) instead of media")
                log.info("%s returned an HTML page (tape staging); polling every %.0fs", ref.url, poll)
                time.sleep(poll)
                continue
            return nbytes, sha
