"""USGS Coastal and Marine Geology Program (CMGP) Video and Photograph Portal: seafloor still photographs.

Data release DOI 10.5066/F7JH3J7N (Golden, Ackerman and Dailey 2015), served by the Axiom Data Science portal
https://video.ioos.us/ (research/usgs_cmgp.md, verified 2026-10-08). The portal indexes USGS seafloor video navigation
(~2.5 M rows) and ~117,600 still photographs; about 70 more layers are above-water aerial coastline imagery that this
adapter never touches (it reads an explicit allowlist of underwater, photo-bearing GeoServer layers).

Scope of this adapter: the STILLS only (JPEG, plain HTTPS from the legacy Axiom photo server). The videos exist only as
YouTube uploads (channel "CMG Video"); whether they may be fetched is a human decision about YouTube's terms, so there is
no video route here (option ``videos=true`` makes ``check_ready`` report that). :func:`video_frame_geo` implements the
research note's geo recipe for frames extracted from the videos (interpolation on the ``frame`` seconds, 10 s gap limit,
5 m/s jump check) so that a later video route can reuse it; it is unit-tested but not wired into ``discover``.

Licence (tier A): "This work is marked with CC0 1.0 Universal" (USGS data release page) and the FGDC ``<useconst>``
"USGS-authored or produced data and information are in the public domain ... Please recognize and acknowledge the
U.S. Geological Survey as the originator(s) of the dataset". Level: record (the FGDC record of the data release; no
licence is stored per file). Only the six USGS-authored layers below are yielded; a candidate whose layer is not in that
list gets tier U. The non-USGS layers of the portal (CSU Monterey Bay "California Undersea Imagery Archive",
``csmp:*``) are not read. Attribution: the USGS citation of the note plus the photo-server id of the image.

Geo (``resolve_geo``): ``properties.lat`` / ``properties.lon`` of the WFS row of the still (WGS 84, 5-6 decimals; NOT
``geometry.coordinates`` and NOT ``outputFormat=csv``, which are rounded to 4 decimals). The coordinate is the survey
vessel's GPS fix matched by time to the photo, written by USGS into the row (and into the EXIF GPS tags of the file):
``geo_precision`` image, ``geo_inferred`` false, ``geo_uncertainty_m`` 10 (provider statement: the vessel position "may
have minimal offset from the subject of the imagery on the seafloor, typically on the order of +/- 10 meters").
``depth_m`` is always None (no depth field in any layer). Rows without a usable coordinate (null, out of range, (0, 0))
give ``Geo.none``. Known quality caveat: the layers contain navigation errors (a 3.7 km jump in 2 s in
``C0212SC_Tape65``); a single still cannot be speed-checked, so the downstream sanity checks apply.

Layers (WFS 1.0.0 ``typeName`` -> short name; photo rows = ``picasa_id`` not null and not empty, 2026-10-08):
    california        axiom:usgsvideoframe                             78,341  (California Seafloor Mapping Program)
    hawaii_pacific    usgs_pacific:videopoints_hw                      28,079  (rows are not all near Hawaii)
    massachusetts     usgs_imagery:woodshole_media_points               8,083
    rhode_island      usgs_imagery:woodshole_rhode_island_media_points  1,793
    puget_sound       usgs_pacific:videopoints_puget_sound                918
    california_old    usgs_imagery:california_imagery_17                  415

How it works
    * Enumeration: ``GET <wfs>?service=WFS&version=1.0.0&request=GetFeature&typeName=..&outputFormat=application/json
      &sortBy=id,picasa_id&startIndex=k*page_size&maxFeatures=page_size&cql_filter=picasa_id IS NOT NULL AND picasa_id <> ''``
      (``id`` alone is not unique in the Hawaii/Pacific layer, so ``picasa_id`` is the second sort key).
      The row count per layer comes from ``totalFeatures`` of a one-row request. Every answer is cached under
      metadata/raw/wfs/ so re-runs do not hit the provider. Item id = ``<picasa_album_id>/<picasa_id>`` (stable, and the
      same photo found in two layers is one item).
    * Budget-friendly order (``order=spread``, default): layers are interleaved in proportion to sqrt(row count);
      inside a layer the table is cut into windows of ``page_size`` rows that are visited in a low-discrepancy order
      (golden-ratio sequence, ``seed``), so even a budget of 30 touches many cruises. Per window at most ``per_window``
      evenly spaced photos are taken and per album (tape / cruise folder) at most ``max_per_album``.
    * Media: ``https://servomatic9000.axiomalaska.com/photo-server/usgs/<album>/<id>/photo?`` (full JPEG, HEAD-verified).
      The server ignores HTTP Range, so a retry restarts the file. ``fetch_media`` checks the JPEG magic number.
    * Timestamp: ``photo_date`` (EXIF time of the camera clock, written without the portal's ``Z``: the time zone is not
      verified) or ``date`` of the row when present (the California layer has none). The camera clock can be minutes off
      the navigation clock: never use it to re-derive a position. ``dateinfo`` is not used (inconsistent with the EXIF).
    * Politeness: 1 s between requests to data.axds.co and to the photo server (the defaults); no token, no account.
    * Not done: pixel filters (sled off the bottom, water column, deck, burned-in overlay text, laser dots), the videos,
      the other USGS layers without photos, dedup against other USGS ScienceBase releases of the same frames.

Adapter options (``--opt key=value``)
    layers         comma list of short names above (default: all six).
    order          ``spread`` (default) or ``table`` (window 0, 1, 2, ... of each layer in turn, layers one after another).
    seed           integer that shifts the window sequence (default 0).
    page_size      rows per WFS request (default 200).
    per_window     photos taken per window in spread order (default 5; ``0`` = all rows of the window).
    max_per_album  at most this many photos per album (default 5; ``0`` = no limit).
    windows        visit at most this many windows per layer (default: all).
    geo_only       skip rows without a usable coordinate (default true).
    videos         ``true`` is rejected by ``check_ready`` (YouTube route needs a human decision).
    refresh_metadata   core option: re-download cached metadata.
"""

from __future__ import annotations

import bisect
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import quote, urlencode

from ..core.geo import NavFix, NavTrack, check_coordinate, haversine_m, parse_time, to_float
from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

DOI = "https://doi.org/10.5066/F7JH3J7N"
HOMEPAGE = "https://www.usgs.gov/data/coastal-and-marine-geology-video-and-photograph-portal"
FGDC_URL = "https://data.usgs.gov/datacatalog/metadata/USGS.fa1a6827-fbde-442a-80f6-b607892854a5.xml"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
PHOTO_BASE = "https://servomatic9000.axiomalaska.com/photo-server/usgs"

WFS_ROOT = "https://data.axds.co/gs"
LAYERS: dict[str, dict[str, str]] = {
    "california": {"type_name": "axiom:usgsvideoframe", "wfs": f"{WFS_ROOT}/wfs", "area": "California (CA Seafloor Mapping Program)"},
    "hawaii_pacific": {"type_name": "usgs_pacific:videopoints_hw", "wfs": f"{WFS_ROOT}/usgs_pacific/wfs", "area": "Hawaii / Pacific"},
    "massachusetts": {"type_name": "usgs_imagery:woodshole_media_points", "wfs": f"{WFS_ROOT}/usgs_imagery/wfs", "area": "Massachusetts"},
    "rhode_island": {
        "type_name": "usgs_imagery:woodshole_rhode_island_media_points",
        "wfs": f"{WFS_ROOT}/usgs_imagery/wfs",
        "area": "Rhode Island / Long Island Sound",
    },
    "puget_sound": {"type_name": "usgs_pacific:videopoints_puget_sound", "wfs": f"{WFS_ROOT}/usgs_pacific/wfs", "area": "Puget Sound"},
    "california_old": {"type_name": "usgs_imagery:california_imagery_17", "wfs": f"{WFS_ROOT}/usgs_imagery/wfs", "area": "California (older imagery)"},
}
TYPE_NAME_TO_KEY = {v["type_name"]: k for k, v in LAYERS.items()}
# Photo rows per layer (research note, re-queried 2026-10-08) and mean file size in bytes where measured (HEAD).
PHOTO_ROWS = {"california": 78341, "hawaii_pacific": 28079, "massachusetts": 8083, "rhode_island": 1793, "puget_sound": 918, "california_old": 415}
MEAN_BYTES = {  # one HEAD per layer (2026-10-08); sizes vary per file, so the estimate is rough
    "california": 2_650_000, "hawaii_pacific": 100_000, "massachusetts": 1_330_000,
    "rhode_island": 3_090_000, "puget_sound": 3_050_000, "california_old": 3_750_000,
}  # fmt: skip
DEFAULT_MEAN_BYTES = 1_330_000
PHOTO_FILTER = "picasa_id IS NOT NULL AND picasa_id <> ''"
# ``id`` alone is not unique (Hawaii/Pacific: 117 distinct ids in 200 rows), so paging on it would skip or repeat rows between
# windows. (id, picasa_id) orders every photo row; remaining ties are the same photo twice, which the item id merges.
SORT_BY = "id,picasa_id"

CITATION = (
    "U.S. Geological Survey, Coastal and Marine Geology Program. Golden, N.E., Ackerman, S.D., and Dailey, E.T., 2015, "
    f"Coastal and Marine Geology Program video and photograph portal: U.S. Geological Survey data release, {DOI}. "
    "Public domain (CC0 1.0)."
)
LICENCE_NAME = "CC0 1.0 Universal (USGS public domain)"

GEO_SOURCE = "WFS {type_name} properties.lat/lon (row id {row_id})"
GEO_UNCERTAINTY_M = 10.0  # provider statement: vessel position, typically +/- 10 m of the seafloor subject
MAX_SPEED_MS = 5.0  # a towed sled faster than this between two fixes is a navigation error
MAX_GAP_S = 10.0
DEFAULT_PAGE_SIZE = 200
DEFAULT_PER_WINDOW = 5
DEFAULT_MAX_PER_ALBUM = 5
ORDERS = ("spread", "table")
GOLDEN = 0.6180339887498949
MAGIC_JPEG = b"\xff\xd8\xff"
MIN_JPEG_BYTES = 1000


# ----------------------------------------------------------------------------------------------- pure helpers
def valid_coordinate(lat: float | None, lon: float | None) -> bool:
    return lat is not None and lon is not None and check_coordinate(lat, lon) is None


def row_coordinate(props: dict[str, Any]) -> tuple[float, float] | None:
    """(lat, lon) from ``properties`` (never from ``geometry``), or None when null / out of range / (0, 0)."""
    lat, lon = to_float(props.get("lat")), to_float(props.get("lon"))
    return (lat, lon) if valid_coordinate(lat, lon) else None


def is_still(props: dict[str, Any]) -> bool:
    pid = props.get("picasa_id")
    album = props.get("picasa_album_id")
    return bool(str(pid or "").strip()) and bool(str(album or "").strip())


def photo_url(album: str, picasa_id: str) -> str:
    return f"{PHOTO_BASE}/{quote(album, safe='')}/{quote(picasa_id, safe='')}/photo?"


def item_id_of(props: dict[str, Any]) -> str:
    return f"{str(props['picasa_album_id']).strip()}/{str(props['picasa_id']).strip()}"


def row_timestamp(props: dict[str, Any]) -> str | None:
    """Capture time of the photo when the layer has one (``photo_date``, else ``date``); None otherwise.

    ``photo_date`` is the EXIF time of the camera clock; the portal appends a ``Z`` although the camera time zone and clock
    offset are not verified (23 min off the navigation clock in the checked case), so the ``Z`` is dropped and the value
    is only a rough capture time. ``dateinfo`` (Excel day of the navigation row) is not used: for the Hawaii row with
    ``id`` -1 it says 2014-09-05 while the photo EXIF says 2013-02-09.
    """
    for key in ("photo_date", "date"):
        raw = props.get(key)
        if raw in (None, ""):
            continue
        s = str(raw).strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}Z?", s):
            return s.rstrip("Z")
        if parse_time(s) is not None:
            return s.rstrip("Z")
    return None


def window_order(n: int, seed: int) -> list[int]:
    """All windows 0..n-1, best spread first (golden-ratio sequence shifted by ``seed``), each exactly once."""
    out: list[int] = []
    seen: set[int] = set()
    shift = (0.5 + seed * 0.7548776662466927) % 1.0
    for k in range(4 * n + 8):
        w = min(n - 1, int(((shift + k * GOLDEN) % 1.0) * n))
        if w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) == n:
            return out
    out.extend(w for w in range(n) if w not in seen)  # safety net: every window is visited once
    return out


def evenly(rows: list[Any], k: int) -> list[Any]:
    """``k`` evenly spaced elements of ``rows`` (all of them when k <= 0 or k >= len)."""
    n = len(rows)
    if k <= 0 or k >= n:
        return list(rows)
    return [rows[min(n - 1, int((i + 0.5) * n / k))] for i in range(k)]


def layer_weights(counts: dict[str, int]) -> dict[str, float]:
    """Interleaving weights: sqrt of the photo-row count of each layer."""
    return {k: math.sqrt(max(c, 0)) for k, c in counts.items() if c > 0}


def interleave_layers(streams: dict[str, Iterator[Candidate]], weights: dict[str, float]) -> Iterator[Candidate]:
    """Weighted round robin: always advance the stream with the smallest (taken + 1) / weight."""
    taken = {k: 0 for k in streams}
    live = dict(streams)
    while live:
        key = min(live, key=lambda k: ((taken[k] + 1) / max(weights.get(k, 1.0), 1e-9), list(streams).index(k)))
        try:
            cand = next(live[key])
        except StopIteration:
            del live[key]
            continue
        taken[key] += 1
        yield cand


def video_frame_geo(rows: Iterable[dict[str, Any]], t: float, type_name: str, *, youtube_id: str | None = None) -> Geo:
    """Geo of a frame extracted at ``t`` seconds into a video (research note, resolve_geo recipe, steps 3-5).

    ``rows`` are the WFS ``properties`` of ONE video (same ``video``; ``youtube_id`` further narrows them), ``frame`` =
    seconds into the video. Exact hit on a row -> ``image``; two rows at most 10 s apart -> linear interpolation,
    ``segment``, ``geo_inferred`` true; a gap > 10 s, ``t`` outside the table, or an implied speed above 5 m/s between the
    two rows (navigation error such as the 3.7 km jump of C0212SC_Tape65 at 2756 -> 2758 s) -> ``Geo.none``.
    """
    fixes: list[NavFix] = []
    for r in rows:
        if youtube_id and str(r.get("youtube_id") or "") not in ("", youtube_id):
            continue
        frame, c = to_float(r.get("frame")), row_coordinate(r)
        if frame is not None and c is not None:
            fixes.append(NavFix(frame, c[0], c[1]))
    fixes.sort(key=lambda f: f.t)
    src = f"WFS {type_name} properties.lat/lon"
    track = NavTrack(fixes, max_gap_s=MAX_GAP_S)
    hit = track.locate(t)
    if hit is None:
        return Geo.none(geo_source=f"{src} (no row pair within {MAX_GAP_S:g} s of frame {t:g})")
    if hit.gap_s == 0:
        return Geo(hit.lat, hit.lon, None, "image", f"{src} (row frame {t:g})", False, GEO_UNCERTAINTY_M)
    times = [f.t for f in track.fixes]
    i = bisect.bisect_left(times, t)
    a, b = track.fixes[i - 1], track.fixes[i]
    speed = haversine_m(a.lat, a.lon, b.lat, b.lon) / (b.t - a.t)
    if speed > MAX_SPEED_MS:
        return Geo.none(geo_source=f"{src} (rows {a.t:g}-{b.t:g} s imply {speed:.0f} m/s: navigation jump)")
    return Geo(
        round(hit.lat, 7), round(hit.lon, 7), None, "segment",
        f"{src} interpolated on properties.frame", True, GEO_UNCERTAINTY_M,
    )  # fmt: skip


def _tokens(value: object) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple)):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x for x in re.split(r"[,\s\[\]\"']+", str(value)) if x]


def _flag(value: object, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("0", "false", "no", "off")
    return bool(value)


def check_options(options: dict[str, Any]) -> list[str]:
    problems = []
    if str(options.get("order", "spread")).lower() not in ORDERS:
        problems.append(f"option order must be one of {ORDERS}")
    bad = [x for x in _tokens(options.get("layers")) if x not in LAYERS]
    if bad:
        problems.append(f"option layers: unknown {bad}; choose from {sorted(LAYERS)}")
    for name in ("seed", "page_size", "per_window", "max_per_album", "windows"):
        v = options.get(name)
        if v not in (None, "") and to_float(v) is None:
            problems.append(f"option {name} must be a number, got {v!r}")
    if (to_float(options.get("page_size")) or 1) < 1:
        problems.append("option page_size must be >= 1")
    if _flag(options.get("videos"), False):
        problems.append(
            "option videos=true: the videos exist only on YouTube (channel CMG Video); fetching them is a human decision about "
            "YouTube's terms and is not implemented (see manual_steps)"
        )
    return problems


# ----------------------------------------------------------------------------------------------- adapter
@register
class UsgsCmgpAdapter(Adapter):
    key = "usgs_cmgp"
    name = "USGS CMGP Video and Photograph Portal: seafloor still photographs"
    homepage = HOMEPAGE
    citation = CITATION + f" {DOI}"
    media_types = ("image",)
    env_vars: tuple[str, ...] = ()
    manual_steps = (
        "None for the ~117,600 seafloor stills (public WFS, public photo server, no token). The videos exist only as YouTube "
        "uploads (channel CMG Video, https://www.youtube.com/@USGSCMG): decide whether fetching them is acceptable under "
        "YouTube's terms (the content is public domain, but scripted watch-page requests got HTTP 429); this adapter does not "
        "download them. Alternative: ask the USGS PCMSC data coordinator for the original video files. Check the layer "
        "allowlist once against the layers shown at https://video.ioos.us/."
    )
    # data.axds.co answers 1,000 rows in ~2 s; the legacy photo server is old infrastructure: stay polite.
    host_intervals = {"data.axds.co": 1.0, "servomatic9000.axiomalaska.com": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self.skipped: Counter[str] = Counter()
        self._counts: dict[str, int] = {}

    # ------------------------------------------------------------------------------------------- options
    def check_ready(self) -> list[str]:
        return super().check_ready() + check_options(self.options)

    def _int(self, name: str, default: int) -> int:
        v = to_float(self.options.get(name))
        return default if v is None else int(v)

    def _layer_keys(self) -> list[str]:
        wanted = _tokens(self.options.get("layers"))
        return [k for k in LAYERS if not wanted or k in wanted]

    @property
    def page_size(self) -> int:
        return max(1, self._int("page_size", DEFAULT_PAGE_SIZE))

    # ------------------------------------------------------------------------------------------- WFS access
    def _wfs_url(self, layer: str, *, start: int, count: int) -> str:
        spec = LAYERS[layer]
        params = {
            "service": "WFS", "version": "1.0.0", "request": "GetFeature", "typeName": spec["type_name"],
            "outputFormat": "application/json", "sortBy": SORT_BY, "startIndex": start, "maxFeatures": count,
            "cql_filter": PHOTO_FILTER,
        }  # fmt: skip
        return spec["wfs"] + "?" + urlencode(params, quote_via=quote)

    def _wfs_json(self, url: str, name: str) -> dict[str, Any]:
        """Cached WFS answer. GeoServer reports errors as XML with HTTP 200: such an answer is not kept in the cache."""
        text = self.ctx.cached_text(url, name)
        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("not a JSON object")
        except ValueError:
            (self.ctx.layout.raw / name).unlink(missing_ok=True)
            raise HttpError(url, None, f"answer is not a GeoJSON FeatureCollection: {text[:200]!r}") from None
        return data

    def layer_count(self, layer: str) -> int:
        """Number of photo rows of a layer (``totalFeatures`` of a one-row request, cached; 0 and logged when it fails)."""
        if layer not in self._counts:
            url = self._wfs_url(layer, start=0, count=1)
            try:
                data = self._wfs_json(url, f"wfs/{layer}/count.json")
                self._counts[layer] = int(data.get("totalFeatures") or data.get("numberMatched") or 0)
            except HttpError as exc:
                self.ctx.fail(f"{layer}/count", "discover", f"{exc}", url=url)
                self._counts[layer] = 0
        return self._counts[layer]

    def _window(self, layer: str, w: int) -> list[dict[str, Any]]:
        """``properties`` of the photo rows of window ``w`` (cached). A failing window is logged and skipped."""
        size = self.page_size
        url = self._wfs_url(layer, start=w * size, count=size)
        try:
            data = self._wfs_json(url, f"wfs/{layer}/ps{size}_sid_w{w:06d}.json")
        except HttpError as exc:
            self.ctx.fail(f"{layer}/window{w}", "discover", f"{exc}", url=url)
            return []
        return [f.get("properties") or {} for f in data.get("features", [])]

    # ------------------------------------------------------------------------------------------- discover
    def _usable(self, layer: str, props: dict[str, Any]) -> bool:
        if not is_still(props):
            self.skipped["no photo id"] += 1
            return False
        if _flag(self.options.get("geo_only"), True) and row_coordinate(props) is None:
            self.skipped["no coordinates"] += 1
            return False
        return True

    def _layer_stream(self, layer: str, seen: set[str], albums: Counter[str]) -> Iterator[Candidate]:
        total = self.layer_count(layer)
        if total <= 0:
            return
        size = self.page_size
        n_windows = math.ceil(total / size)
        order = str(self.options.get("order", "spread")).lower()
        windows = window_order(n_windows, self._int("seed", 0)) if order == "spread" else list(range(n_windows))
        limit = self.options.get("windows")
        if to_float(limit) is not None:
            windows = windows[: max(1, int(to_float(limit)))]
        per_window = self._int("per_window", DEFAULT_PER_WINDOW) if order == "spread" else 0
        cap_album = self._int("max_per_album", DEFAULT_MAX_PER_ALBUM)
        for w in windows:
            rows = [p for p in self._window(layer, w) if self._usable(layer, p)]
            rows.sort(key=lambda p: (to_float(p.get("id")) or 0, str(p.get("picasa_id"))))
            for props in evenly(rows, per_window) if per_window else rows:
                iid = item_id_of(props)
                album = str(props["picasa_album_id"]).strip()
                if iid in seen:
                    self.skipped["duplicate photo"] += 1
                    continue
                if cap_album and albums[album] >= cap_album:
                    self.skipped["max_per_album cap"] += 1
                    continue
                seen.add(iid)
                albums[album] += 1
                yield self._candidate(layer, props)

    def discover(self) -> Iterable[Candidate]:
        order = str(self.options.get("order", "spread")).lower()
        if order not in ORDERS:
            raise ValueError(f"order must be one of {ORDERS}")
        keys = self._layer_keys()
        seen: set[str] = set()
        albums: Counter[str] = Counter()
        streams = {k: self._layer_stream(k, seen, albums) for k in keys}
        if order == "table":
            for k in keys:
                yield from streams[k]
            return
        counts = {k: self.layer_count(k) for k in keys}
        yield from interleave_layers(streams, layer_weights(counts))

    def _candidate(self, layer: str, props: dict[str, Any]) -> Candidate:
        album, pid = str(props["picasa_album_id"]).strip(), str(props["picasa_id"]).strip()
        spec = LAYERS[layer]
        keep = ("id", "lat", "lon", "frame", "video", "youtube_id", "photo", "photoname", "picasa_id", "picasa_album_id", "cruiseid", "cam_angle")
        raw = {k: props[k] for k in keep if k in props}
        raw["type_name"] = spec["type_name"]
        extra = {
            "layer": layer,
            "type_name": spec["type_name"],
            "row_id": props.get("id"),
            "video": props.get("video"),
            "frame_s": props.get("frame"),
            "youtube_id": props.get("youtube_id") or None,
            "cruise": props.get("cruiseid") or None,
            "photo_name": props.get("photoname") or props.get("photo"),
            "area": spec["area"],
        }
        return Candidate(
            source=self.key,
            item_id=item_id_of(props),
            media_type="image",
            media_url=photo_url(album, pid),
            origin_url=f"{spec['wfs']}?service=WFS&version=1.0.0&request=GetFeature&typeName={spec['type_name']}",
            timestamp=row_timestamp(props),
            ext="jpg",
            raw=raw,
            extra=extra,
        )

    # ------------------------------------------------------------------------------------------- licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        type_name = str(cand.raw.get("type_name") or "")
        if type_name not in TYPE_NAME_TO_KEY:
            # Not one of the USGS-authored layers (e.g. CSU Monterey Bay content in the same portal): licence not read.
            return make_licence("not stated (non-USGS layer)", level="collection", url=HOMEPAGE, attribution=CITATION, tier="U")
        album, pid = cand.item_id.split("/", 1)
        attribution = f"{CITATION} Photo: photo-server id {album}/{pid}."
        if cand.raw.get("youtube_id"):
            attribution += f" Video: YouTube channel CMG Video, id {cand.raw['youtube_id']}."
        return make_licence(LICENCE_NAME, level="record", url=CC0_URL, attribution=attribution, tier="A")

    # ------------------------------------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        raw = cand.raw
        type_name = str(raw.get("type_name") or "")
        coord = row_coordinate(raw)
        if coord is None:
            return Geo.none(geo_source=f"WFS {type_name} properties.lat/lon (null or invalid)")
        return Geo(
            lat=coord[0], lon=coord[1], depth_m=None, geo_precision="image",
            geo_source=GEO_SOURCE.format(type_name=type_name, row_id=raw.get("id")),
            geo_inferred=False, geo_uncertainty_m=GEO_UNCERTAINTY_M,
        )  # fmt: skip

    # ------------------------------------------------------------------------------------------- media
    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        nbytes, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)
        problem = None
        if nbytes < MIN_JPEG_BYTES:
            problem = f"only {nbytes} bytes"
        else:
            with open(dest, "rb") as fh:
                if not fh.read(3).startswith(MAGIC_JPEG):
                    problem = "not a JPEG (magic number)"
        if problem:
            dest.unlink(missing_ok=True)
            raise HttpError(ref.url, None, problem)
        return nbytes, sha

    # ------------------------------------------------------------------------------------------- estimate
    def estimate(self) -> dict[str, Any]:
        """Photo rows per layer from the provider (``totalFeatures``; one cached request per layer) and a size estimate."""
        out: dict[str, Any] = {}
        total = 0
        size = 0
        for k in self._layer_keys():
            n = self.layer_count(k)
            out[f"images_{k}"] = n
            total += n
            size += n * MEAN_BYTES.get(k, DEFAULT_MEAN_BYTES)
        out["images_total"] = total
        out["gb_estimate"] = round(size / 1e9, 1)
        return out
