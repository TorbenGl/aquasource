"""FathomNet (MBARI): open database of annotated ocean images, read through its anonymous REST API.

FathomNet (https://database.fathomnet.org, Katija et al. 2022, Sci. Rep. 12, 15914) stores 481 k image records (2026-10-08)
from 17 institutions. The images stay on the contributors' hosts; the database only holds URL, geolocation, licence and
bounding boxes (research/fathomnet.md). Licence is a field of every image record (``imageLicense``) and is dominated by
non-commercial terms, so this adapter keeps only what the per-image licence allows:

    * ``CC0-1.0`` (tier A): 231,631 NOAA NMFS SEFSC (Mississippi Laboratories) SEAMAP reef-fish drop-camera video frames,
      Gulf of Mexico (24.5-30.2 N, 83.1-97.0 W), JPEG 1920x1080 / 1920x1200, cut at 5 fps from ~526 videos at ~95
      deployment positions, hosted in the public GCS bucket ``gs://nmfs_odp_hq/nodd_tools/datasets/gfisher/``.
    * ``CC-BY-4.0`` (tier B): 7,948 images, of which only 16 have coordinates (POSCO macroalgae photos off Korea, 2 positions);
      the rest are 224x224 CENCOOS plankton crops without coordinates (dropped by the geo gate).
    * Every record whose licence contains NC or ND (CC-BY-NC-4.0, CC-BY-NC-ND-4.0, ...: MBARI, Schmidt Ocean Institute,
      NOAA Ocean Exploration, Ocean Networks Canada, ...), is null, ``JPL-image`` or unknown is NOT yielded. The licence is
      never upgraded: the tier comes from :func:`aquasource.core.licence.classify` on the SPDX id of the record.

Licence level: record (``imageLicense`` of the image; the upload-level ``darwinCore.license`` and the Terms of Use agree).
Attribution: the FathomNet data paper citation, the image uuid / url / SPDX id, and for the NOAA frames the acknowledgement
NOAA asks for. Soft conditions of the FathomNet Data Use Policy (acknowledge FathomNet, "benevolent use" = UN SDGs, the Terms
of Use mention account registration while the read API is open) are not part of CC0 / CC BY; put them in the dataset card.

Geo (``resolve_geo``): fields ``latitude``, ``longitude``, ``depthMeters`` of the image record (WGS 84, west negative,
depth positive down). The coordinate of the NOAA frames is ONE deployment position per video folder, copied to every frame
and to the 4-5 camera views of a drop -> ``station`` precision, ``geo_inferred`` true, ``geo_uncertainty_m`` 200
(assumption of the research note: nothing is published). The 16 POSCO images share one coordinate per upload folder ->
``station``, inferred, 2000 m. Null / out-of-range / (0, 0) coordinates -> ``geo_precision`` none (depth kept).

How it works
    * Enumeration: ``GET /api/geoimages?size=<page_size>&page=N&sort=uuid`` (stable paging; ``POST .../query`` offset paging
      is NOT stable and is never used for paging). 161 pages of 3000 light records (~1.2 MB each) cover the 481 k images.
      Records are filtered client side (``valid``, licence tier, coordinates) and each page is cached under
      metadata/raw/geoimages/. Item id = image ``uuid`` (stable across runs).
    * Budget-friendly order (``order=spread``, default): ``uuid`` is random, so every page is a uniform sample of the
      database. Pages are visited in a seeded pseudo-random order, so a budget of 30 reads ONE page; inside a page the
      records are interleaved station by station (seeded order), then video by video inside a station, so any prefix covers
      many deployment positions. The 16 georeferenced CC-BY records are fetched with one small ``POST /geoimages/query``
      (all 16 fit in one answer, offset 0) and join the first page as two more stations.
    * Redundancy limits (the frames are 5 fps): per video folder at most ``frames_per_video`` frames (default 5), at least
      ``min_spacing_s`` apart (default 10 s) in video time (the offset is in the file name), optionally ``max_per_station``.
    * Media: plain HTTPS GET of ``url`` (GCS supports Range / resume). ``resolve_media`` reads the full record
      ``GET /api/images/<uuid>`` once for ``sha256`` (and re-checks ``valid`` and the licence tier: contributors can
      withdraw or change images); ``fetch_media`` verifies the sha256 and the image magic number and deletes a bad file.
    * Not done: pixel filters (deck / surface / black frames at the ends of a drop; the 16 POSCO macroalgae photos may be
      intertidal or above water: apply the usual above-water filter), the 140 source ``.mp4`` videos of the
      bucket (same station coordinate, not in the FathomNet DB), dedup against BenthicNet (excluded there anyway) and the
      candidate ``noaa_fisheries_nodd`` (dedup by ``sha256`` / video name, kept in ``extra.video``).
    * Politeness: 1 s between requests to database.fathomnet.org (no limit documented, a connection reset every ~15th call
      through proxies is retried by the HTTP client), 0.25 s to the GCS bucket, 1 s to other hosts. No token, no account.
      The records carry institutional ``contributorsEmail`` values; they are removed before the answer is cached in
      metadata/raw/ and never stored or copied. A missing page (HTTP 4xx) or a failed CC-BY query is logged in the failures
      file and skipped; a server outage stops the run (cached pages are reused on the next run).

Adapter options (``--opt key=value``; booleans and lists as JSON or comma separated)
    tiers              licence tiers to yield, default ``A,B`` (``A,B,C`` adds CC-BY-SA, 0 images today).
    order              ``spread`` (default) or ``table`` (pages 0..N in order, records in uuid order, still capped).
    seed               integer for the pseudo-random page / station order (default 0).
    page_size          records per ``GET /geoimages`` page (default 3000, the size the research note tested).
    pages              visit at most this many pages (default: all). ``pages=1`` is the cheapest sample.
    frames_per_video   at most this many frames per video folder (default 5; ``0`` = all frames).
    min_spacing_s      minimum video-time distance of two kept frames of a video (default 10; ``0`` = no limit).
    max_per_station    at most this many frames per (lat, lon) deployment position (default: no limit).
    include_ccby       fetch the georeferenced CC-BY records with one POST query (default true; needs tier B).
    geo_only           skip records without usable coordinates (default true; ``false`` yields them with geo ``none``).
    verify_sha256      read the full record and verify the download against its sha256 (default true).
    refresh_metadata   core option: re-download cached metadata.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from collections import deque
from pathlib import Path
from typing import Any, Iterable, Iterator

from ..core.geo import depth_from, to_float
from ..core.http import HttpError
from ..core.licence import classify, make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

API = "https://database.fathomnet.org/api"
HOME = "https://database.fathomnet.org/fathomnet/"
TERMS = "https://www.fathomnet.org/terms"
GFISHER_PREFIX = "https://storage.googleapis.com/nmfs_odp_hq/nodd_tools/datasets/gfisher/"
GFISHER_BUCKET_PAGE = "https://www.fisheries.noaa.gov/inport/item/30062"

PAPER = (
    "Katija, K. et al. (2022) FathomNet: A global image database for enabling artificial intelligence in the ocean. "
    "Scientific Reports 12, 15914. https://doi.org/10.1038/s41598-022-19939-2"
)
NOAA_CREDIT = (
    "Image: NOAA NMFS Southeast Fisheries Science Center (Mississippi Laboratories), SEAMAP reef fish video survey, "
    "via FathomNet"
)
LICENCE_URLS = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/legalcode",
    "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/legalcode",
}
LICENSES_LIST = API + "/licenses/list/all"
# SPDX ids of FathomNet that the generic classifier does not recognise (research note, "Licence").
PUBLIC_DOMAIN_IDS = {"NCBI-PD", "NIST-PD", "NTIA-PD", "CC-PDM-1.0"}

GEO_SOURCE = (
    "fathomnet API /geoimages (and /geoimages/query, /images/query) fields latitude, longitude, depthMeters; "
    "coordinate is per video deployment (shared by all frames of the folder)"
)
GEO_SOURCE_UPLOAD = (
    "fathomnet API /geoimages (and /geoimages/query, /images/query) fields latitude, longitude (depthMeters null); "
    "coordinate is shared by all images of the upload folder"
)
STATION_UNCERTAINTY_M = 200.0  # assumption (research note): deployment position of a camera rig, nothing published
UPLOAD_UNCERTAINTY_M = 2000.0  # assumption (research note): POSCO position shared by an upload folder, 3 decimals
POSCO_HINT = "POSCO (owner institution of the georeferenced CC BY uploads FN2511*, state 2026-10-08)"
POSCO_RE = re.compile(r"^https://oer\.hpc\.msstate\.edu/FathomNet/staging/FN2511\d+/")

DEFAULT_PAGE_SIZE = 3000
DEFAULT_FRAMES_PER_VIDEO = 5
DEFAULT_MIN_SPACING_S = 10.0
ORDERS = ("spread", "table")
TIERS_ALLOWED = ("A", "B", "C")
CCBY_QUERY_LIMIT = 200
WORLD_BOX = {"minLatitude": -90, "maxLatitude": 90, "minLongitude": -180, "maxLongitude": 180}
FRAME_RE = re.compile(r"\.(\d{2})\.(\d{2})\.(\d{2})\.(\d{6})\.jpe?g$", re.IGNORECASE)
MAGIC = {"jpg": b"\xff\xd8\xff", "jpeg": b"\xff\xd8\xff", "png": b"\x89PNG"}
# estimate(): size of one CC0 frame, 345-643 kB measured on 3 files (research note)
CC0_FRAME_BYTES = 500_000


# ----------------------------------------------------------------------------------------------- pure helpers
def licence_tier(spdx: object) -> str:
    """Tier of the SPDX id in ``imageLicense``: A / B / C / X (any NC or ND) / U (null or not recognised). Never upgraded."""
    s = str(spdx or "").strip()
    if not s:
        return "U"
    tier = classify(s)
    if tier == "U" and s in PUBLIC_DOMAIN_IDS:
        return "A"
    return tier


def video_of(url: str) -> str:
    """Folder part of a frame url (``.../gfisher/<video>/<video>.<ext>.HH.MM.SS.ffffff.jpg`` -> ``<video>``)."""
    parts = url.rsplit("/", 2)
    return parts[-2] if len(parts) >= 3 else ""


def frame_offset_s(url: str) -> float | None:
    """Video time of a frame in seconds from its file name (``...mp4.00.00.02.400000.jpg`` -> 2.4), else None."""
    m = FRAME_RE.search(url)
    if not m:
        return None
    h, mi, s, frac = (int(g) for g in m.groups())
    return h * 3600 + mi * 60 + s + frac / 1_000_000


def valid_coordinate(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    return not (lat == 0 and lon == 0)


def station_of(rec: dict[str, Any]) -> tuple[float, float] | None:
    lat, lon = to_float(rec.get("latitude")), to_float(rec.get("longitude"))
    return (round(lat, 5), round(lon, 5)) if valid_coordinate(lat, lon) else None


def _hash_key(*parts: object) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()


def page_order(n_pages: int, seed: int) -> list[int]:
    """Pages 0..n-1 in a seeded pseudo-random order (uuid is random, so each page is a uniform sample)."""
    return sorted(range(n_pages), key=lambda p: _hash_key(seed, "page", p))


def interleave(records: list[dict[str, Any]], seed: int) -> Iterator[dict[str, Any]]:
    """Round robin over stations (seeded order), inside a station over videos, inside a video over frames (uuid order)."""
    stations: dict[Any, dict[str, list[dict[str, Any]]]] = {}
    for rec in sorted(records, key=lambda r: str(r.get("uuid"))):
        st = station_of(rec) or ("none", str(rec.get("uuid")))  # records without a position are their own stations
        stations.setdefault(st, {}).setdefault(video_of(str(rec.get("url") or "")), []).append(rec)
    queue: deque[deque[deque[dict[str, Any]]]] = deque()
    for st in sorted(stations, key=lambda s: _hash_key(seed, "station", s)):
        videos = stations[st]
        queue.append(deque(deque(videos[v]) for v in sorted(videos, key=lambda v: _hash_key(seed, "video", st, v))))
    while queue:
        st_videos = queue.popleft()
        frames = st_videos.popleft()
        yield frames.popleft()
        if frames:
            st_videos.append(frames)
        if st_videos:
            queue.append(st_videos)


def light_record(rec: dict[str, Any]) -> dict[str, Any]:
    """The fields of a record this adapter needs. ``contributorsEmail`` and all other fields are dropped on purpose."""
    keys = ("uuid", "url", "latitude", "longitude", "depthMeters", "timestamp", "imageLicense", "valid", "sha256")
    return {k: rec[k] for k in keys if k in rec}


def _scrub(data: Any) -> str:
    """JSON text of an API answer without ``contributorsEmail`` (institutional e-mail addresses are never stored)."""
    rows = data if isinstance(data, list) else data.get("content") if isinstance(data, dict) else None
    for row in rows if isinstance(rows, list) else ():
        if isinstance(row, dict):
            row.pop("contributorsEmail", None)
    return json.dumps(data)


def check_options(options: dict[str, Any]) -> list[str]:
    problems = []
    if str(options.get("order", "spread")).lower() not in ORDERS:
        problems.append(f"option order must be one of {ORDERS}")
    for name in ("seed", "page_size", "pages", "frames_per_video", "min_spacing_s", "max_per_station"):
        v = options.get(name)
        if v not in (None, "") and to_float(v) is None:
            problems.append(f"option {name} must be a number, got {v!r}")
    if (to_float(options.get("page_size")) or 1) < 1:
        problems.append("option page_size must be >= 1")
    bad = [t for t in _tier_list(options.get("tiers")) if t not in TIERS_ALLOWED]
    if bad:
        problems.append(f"option tiers may only contain A, B, C (got {bad})")
    return problems


def _tier_list(value: object) -> list[str]:
    if value in (None, ""):
        return ["A", "B"]
    if isinstance(value, str):
        value = [x for x in re.split(r"[,\s\[\]\"']+", value) if x]
    return [str(x).strip().upper() for x in (value if isinstance(value, (list, tuple)) else [value])]


def _flag(value: object, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("0", "false", "no", "off")
    return bool(value)


@register
class FathomNetAdapter(Adapter):
    key = "fathomnet"
    name = "FathomNet (MBARI): annotated ocean images, CC0 and CC BY records only"
    homepage = "https://database.fathomnet.org/fathomnet/"
    citation = PAPER
    media_types = ("image",)
    env_vars: tuple[str, ...] = ()
    manual_steps = (
        "None for the CC0 / CC BY records (anonymous read API, public GCS bucket). Optional: the FathomNet Terms of Use say that "
        "an account is needed to use the Database although the read API is open; consider a free account and/or ask "
        "fathomnet@mbari.org to confirm bulk metadata / URL use of the CC0 and CC BY images for model pretraining. The Data "
        "Use Policy asks to acknowledge FathomNet and to use the data consistently with the UN Sustainable Development "
        "Goals: put both in the dataset card."
    )
    host_intervals = {"database.fathomnet.org": 1.0, "storage.googleapis.com": 0.25}

    def __init__(self, ctx):
        super().__init__(ctx)
        self.skipped: dict[str, int] = {}
        self._tiers = _tier_list(self.options.get("tiers"))

    # ------------------------------------------------------------------------------------------- options
    def check_ready(self) -> list[str]:
        return super().check_ready() + check_options(self.options)

    def _int(self, name: str, default: int) -> int:
        v = to_float(self.options.get(name))
        return default if v is None else int(v)

    @property
    def page_size(self) -> int:
        return max(1, self._int("page_size", DEFAULT_PAGE_SIZE))

    # ------------------------------------------------------------------------------------------- metadata I/O
    def _post_json(self, url: str, body: dict[str, Any], name: str) -> Any:
        """POST a read-only query once and keep the answer in metadata/raw/<name>."""
        path = self.ctx.layout.raw / name
        if path.exists() and not self.options.get("refresh_metadata"):
            return json.loads(path.read_text(encoding="utf-8"))
        resp = self.http.request("POST", url, json=body, headers={"Accept": "application/json"})
        if resp.status_code >= 400:
            raise HttpError(url, resp.status_code, resp.text[:300])
        data = resp.json()
        self.ctx.save_raw(name, _scrub(data))  # keeps no personal data (institutional e-mail addresses) in the cache
        return data

    def _count(self) -> int:
        data = self.ctx.cached_json(f"{API}/images/count", "images_count.json")
        return int(data["count"])

    def _page(self, page: int) -> list[dict[str, Any]]:
        """One ``GET /geoimages`` page. Cached under metadata/raw/geoimages/ WITHOUT the institutional e-mail addresses.

        A missing page (HTTP 4xx) is logged in the failures file and skipped; other errors (outage) stop the run, and
        the pages already cached are reused by the next run.
        """
        size = self.page_size
        url = f"{API}/geoimages?size={size}&page={page}&sort=uuid"
        name = f"geoimages/size{size}_page{page:04d}.json"
        path = self.ctx.layout.raw / name
        if path.exists() and not self.options.get("refresh_metadata"):
            text = path.read_text(encoding="utf-8")
            if "contributorsEmail" in text:  # cache written by an older version: scrub it in place
                text = _scrub(json.loads(text))
                self.ctx.save_raw(name, text)
            data = json.loads(text)
        else:
            try:
                data = self.http.get_json(url)
            except HttpError as exc:
                if exc.status is not None and 400 <= exc.status < 500:
                    self.ctx.fail(f"page{page}", "discover", f"{exc}", url=url)
                    return []
                raise
            self.ctx.save_raw(name, _scrub(data))
        content = data.get("content") if isinstance(data, dict) else data
        return list(content or [])

    def _ccby_records(self) -> list[dict[str, Any]]:
        """Georeferenced non-CC0 records that are allowed by the tiers (CC-BY-4.0: 16 images). One small POST."""
        want = ["CC-BY-4.0"] + (["CC-BY-SA-4.0"] if "C" in self._tiers else [])
        body = {"imageLicenses": want, "limit": CCBY_QUERY_LIMIT, "offset": 0, **WORLD_BOX}
        try:
            data = self._post_json(f"{API}/geoimages/query", body, "geoimages_query_ccby.json")
        except HttpError as exc:  # optional extra: the pages themselves still work
            self.ctx.fail("ccby-query", "discover", f"{exc}")
            return []
        return list(data if isinstance(data, list) else data.get("content", []))

    # ------------------------------------------------------------------------------------------- discover
    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def _usable(self, rec: dict[str, Any]) -> bool:
        if not rec.get("uuid") or not rec.get("url"):
            self._skip("no uuid / url")
            return False
        if rec.get("valid") is not True:
            self._skip("not valid")
            return False
        tier = licence_tier(rec.get("imageLicense"))
        if tier not in self._tiers:
            self._skip(f"licence tier {tier}")
            return False
        if _flag(self.options.get("geo_only"), True) and station_of(rec) is None:
            self._skip("no coordinates")
            return False
        return True

    def _page_stream(self) -> Iterator[list[dict[str, Any]]]:
        size = self.page_size
        n_pages = max(1, math.ceil(self._count() / size))
        seed = self._int("seed", 0)
        order = str(self.options.get("order", "spread")).lower()
        pages = page_order(n_pages, seed) if order == "spread" else list(range(n_pages))
        limit = self.options.get("pages")
        if to_float(limit) is not None:
            pages = pages[: max(1, int(to_float(limit)))]
        first = True
        for page in pages:
            recs = self._page(page)
            if first:
                first = False
                if _flag(self.options.get("include_ccby"), True) and _flag(self.options.get("geo_only"), True) and "B" in self._tiers:
                    seen = {r.get("uuid") for r in recs}
                    recs = recs + [r for r in self._ccby_records() if r.get("uuid") not in seen]
            yield recs

    def discover(self) -> Iterable[Candidate]:
        order = str(self.options.get("order", "spread")).lower()
        if order not in ORDERS:
            raise ValueError(f"order must be one of {ORDERS}")
        seed = self._int("seed", 0)
        cap_video = self._int("frames_per_video", DEFAULT_FRAMES_PER_VIDEO)
        sp = to_float(self.options.get("min_spacing_s"))
        spacing = DEFAULT_MIN_SPACING_S if sp is None else max(0.0, sp)
        cap_station = self._int("max_per_station", 0)
        kept_video: dict[str, list[float]] = {}
        count_video: dict[str, int] = {}
        count_station: dict[Any, int] = {}
        yielded: set[str] = set()
        for recs in self._page_stream():
            usable = [r for r in recs if self._usable(r)]
            stream = interleave(usable, seed) if order == "spread" else iter(sorted(usable, key=lambda r: str(r["uuid"])))
            for rec in stream:
                uuid = str(rec["uuid"])
                if uuid in yielded:
                    continue
                video = video_of(str(rec["url"]))
                station = station_of(rec)
                off = frame_offset_s(str(rec["url"]))
                # the per-video limits are for video frames (the offset is in the file name), not for still photos
                if off is not None and cap_video and count_video.get(video, 0) >= cap_video:
                    self._skip("frames_per_video cap")
                    continue
                if cap_station and station is not None and count_station.get(station, 0) >= cap_station:
                    self._skip("max_per_station cap")
                    continue
                if off is not None and spacing > 0 and any(abs(off - o) < spacing for o in kept_video.get(video, ())):
                    self._skip("min_spacing_s")
                    continue
                if off is not None:
                    kept_video.setdefault(video, []).append(off)
                count_video[video] = count_video.get(video, 0) + 1
                if station is not None:
                    count_station[station] = count_station.get(station, 0) + 1
                yielded.add(uuid)
                yield self._candidate(rec, video, off)

    def _candidate(self, rec: dict[str, Any], video: str, off: float | None) -> Candidate:
        light = light_record(rec)
        url = str(rec["url"])
        ext = url.rsplit("?", 1)[0].rsplit(".", 1)[-1].lower()
        extra: dict[str, Any] = {"video": video, "frame_offset_s": off, "image_license": light.get("imageLicense")}
        if light.get("sha256"):
            extra["sha256_listed"] = light["sha256"]
        return Candidate(
            source=self.key,
            item_id=str(rec["uuid"]),
            media_type="image",
            media_url=url,
            origin_url=f"{API}/images/{rec['uuid']}",
            timestamp=light.get("timestamp"),
            ext=ext if ext in ("jpg", "jpeg", "png") else "jpg",
            raw=light,
            extra=extra,
        )

    # ------------------------------------------------------------------------------------------- licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        rec = cand.raw
        spdx = str(rec.get("imageLicense") or "").strip()
        tier = licence_tier(spdx)
        lic_url = LICENCE_URLS.get(spdx) or (LICENSES_LIST if spdx else None)
        if rec.get("valid") is False:
            tier = "U"  # withdrawn / failed validation: never ingest
        if tier in ("X", "U"):
            return make_licence(spdx or "not stated", level="record", url=lic_url, attribution=PAPER, tier=tier)
        who = self._credit(rec, spdx)
        attribution = f"{who}. {PAPER} FathomNet image {cand.item_id}, {cand.media_url}; licence {spdx}"
        if lic_url:
            attribution += f" ({lic_url})"
        attribution += "."
        return make_licence(spdx, level="record", url=lic_url, attribution=attribution, tier=tier)

    @staticmethod
    def _credit(rec: dict[str, Any], spdx: str) -> str:
        url = str(rec.get("url") or "")
        if url.startswith(GFISHER_PREFIX):
            text = f"{NOAA_CREDIT}; {spdx.replace('CC0-1.0', 'CC0 1.0')}"
            return text
        if POSCO_RE.search(url):
            return f"Image: {POSCO_HINT}, via FathomNet"
        return "Image: contributing institution recorded in FathomNet (see the image record), via FathomNet"

    # ------------------------------------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        rec = cand.raw
        depth = depth_from(rec.get("depthMeters"))
        lat, lon = to_float(rec.get("latitude")), to_float(rec.get("longitude"))
        if not valid_coordinate(lat, lon):
            return Geo.none(geo_source="fathomnet API latitude/longitude (null)", depth_m=depth)
        if str(rec.get("url") or "").startswith(GFISHER_PREFIX):
            return Geo(lat, lon, depth, "station", GEO_SOURCE, True, STATION_UNCERTAINTY_M)
        return Geo(lat, lon, depth, "station", GEO_SOURCE_UPLOAD, True, UPLOAD_UNCERTAINTY_M)

    # ------------------------------------------------------------------------------------------- media
    def resolve_media(self, cand: Candidate) -> MediaRef:
        ref = MediaRef(url=cand.media_url, ext=cand.ext)
        if not _flag(self.options.get("verify_sha256"), True):
            return ref
        rec = self.http.get_json(f"{API}/images/{cand.item_id}")
        if rec.get("valid") is not True:
            raise RuntimeError(f"FathomNet image {cand.item_id} is no longer valid")
        tier = licence_tier(rec.get("imageLicense"))
        if tier not in self._tiers:
            raise RuntimeError(f"licence of {cand.item_id} is now {rec.get('imageLicense')!r} (tier {tier})")
        if rec.get("url") and rec["url"] != cand.media_url:
            ref.url = str(rec["url"])
        if rec.get("sha256"):
            ref.extra["sha256"] = str(rec["sha256"]).lower()
        return ref

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        nbytes, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)
        expected = ref.extra.get("sha256")
        problem = None
        if expected and sha.lower() != expected:
            problem = f"sha256 {sha} != FathomNet record {expected}"
        else:
            magic = MAGIC.get((ref.ext or "").lower())
            if magic:
                with open(dest, "rb") as fh:
                    if not fh.read(len(magic)).startswith(magic):
                        problem = f"not a {ref.ext} file (magic number)"
        if problem:
            dest.unlink(missing_ok=True)
            raise HttpError(ref.url, None, problem)
        return nbytes, sha

    # ------------------------------------------------------------------------------------------- estimate
    def estimate(self) -> dict[str, Any]:
        """Provider totals (4 cheap calls, cached): images overall, CC0, CC-BY and georeferenced CC-BY."""
        total = self._count()
        out: dict[str, Any] = {"images_total": total}
        for label, lic, box in (("cc0_images", "CC0-1.0", False), ("ccby_images", "CC-BY-4.0", False), ("ccby_georeferenced", "CC-BY-4.0", True)):
            body: dict[str, Any] = {"imageLicenses": [lic], **(WORLD_BOX if box else {})}
            data = self._post_json(f"{API}/geoimages/count", body, f"count_{label}.json")
            out[label] = int(data["count"])
        out["cc0_gb_estimate"] = round(out["cc0_images"] * CC0_FRAME_BYTES / 1e9)
        out["pages"] = math.ceil(total / self.page_size)
        out["note"] = "CC0 frames are 5 fps video frames at ~95 stations; frames_per_video caps the redundancy"
        return out
