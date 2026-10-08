"""NOAA HabCam (NEFSC): towed stereo seabed camera, 2015 Sea Scallop Survey, via the public VIAME Web training data.

Scope of this adapter: the 2015 NEFSC subset only (VIAME folder ``US_NE_2015_NEFSC_HABCAM/Corrected``, 119,461 PNG,
stereo pairs 2720x1024 = left | right, 1360x1024 each). The CFF (Coonamessett Farm Foundation, 2017-2019) subsets are
NOT yielded: no licence is stated anywhere (tier U) and they have no navigation (research/noaa_habcam.md).
Full NEFSC archive is not public (InPort 27598: formal request), so nothing else is read.

Licence (tier A): record level. data.gov DCAT entry of the HabCam dataset (harvested from NOAA InPort 27598) states
``license https://creativecommons.org/publicdomain/zero/1.0/``. The VIAME items carry no licence (file level empty), the
VIAME collection only a usage statement. The NOAA ISO record says ``useConstraints otherRestrictions`` and the access
level is non-public: this is a contradiction, flagged for review (research note, Licence). The R2R navigation files are
CC0 / Public Domain Mark 1.0 (file level ``R2R-License``).

Geo (``resolve_geo``): no public file carries a coordinate for an image. The filename holds the UTC timestamp
(``<cruise>.<YYYYMMDD>.<HHMMSSmmm>.<frame>.png``). It is matched to the 1-s ship GPS track of the R2R ``r2rnav``
"Best Resolution" GeoCSV of the cruise (HRS1506, HRS1507, HRS1508; NCEI 0260576, 0206224, 0206225) and linearly
interpolated between the two bracketing fixes (at most 10 s apart, implied speed at most 8 m/s). ``geo_precision``
segment, ``geo_inferred`` true, ``geo_uncertainty_m`` 300 (towed layback + clock). Fixes written as ``#``-prefixed
commented lines (R2R flag, about 01:00-12:00 UTC) are used but marked ``extra.nav_flagged``. ``depth_m`` is None: the
``Altitude`` column of metadata.txt is the height above the seabed, never depth (it goes to ``extra.altitude_m``).

Noisy data is kept: files under 500 kB (blank or black frames, about 0.1 %) are yielded with
``extra.maybe_not_underwater=true``. Nothing is dropped for content.

How it works
    * Enumeration: ``GET /api/v1/item?folderId=<2015 folder>&limit=1000&offset=N&sort=name`` (cached under
      metadata/raw/viame/, about 120 requests at 1 request/s). Only ``*.png`` names of the stereo pattern are kept.
    * Metadata: ``metadata.txt`` (9.5 MB, cached) gives ``Altitude`` per image (joined on the file stem).
    * Media: ``GET /api/v1/item/<id>/download`` (plain HTTPS; size checked against the listing; PNG magic checked).
    * Order (``order=spread``, default): images are grouped by cruise leg and sampled with the research note's shares
      (HRS1506 40 %, HRS1507 25 %, HRS1508 35 %). Within a leg a bit-reversal (van der Corput) order over time gives
      even coverage of the period for any prefix. Frames closer than ``min_spacing_s`` (default 60 s, about 200 m)
      come first in the stream; the near-duplicates follow at the end of the stream, so nothing is skipped.
      Frames without a cruise window (none in the 2015 set) come last. ``order=table`` yields name order.

Adapter options (``--opt key=value``)
    order            ``spread`` (default) or ``table``.
    min_spacing_s    minimum time between frames of one leg in the first part of the spread order (default 60).
    from, to         only frames whose UTC image day is in [from, to], ``YYYY-MM-DD`` (default: all 25 days).
    list_pages       N > 0: list only N evenly spread pages of 1000 names (quick sample, cold cache ~N s); default all (~120).
    altitude         false skips the metadata.txt join (default true).
    refresh_metadata core option: re-download cached metadata.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from ..core.geo import NavFix, NavTrack, haversine_m, parse_time, to_float
from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

API = "https://viame.kitware.com/api/v1"
COLLECTION = "5e4c256ca0fc86aa03120c34"  # VIAME Web public "Training Data"
FOLDER_2015 = "5e4eed5478ed364cd0f98b40"  # US_NE_2015_NEFSC_HABCAM/Corrected
METADATA_ITEM = "5e4eee2e78ed364cd0fabfa0"  # metadata.txt in the same folder
LIST_LIMIT = 1000
PNG_MAGIC = b"\x89PNG"
NAME_RE = re.compile(r"^201503\.(\d{8})\.(\d{6})(\d{3})\.(\d+)\.png$")

HOMEPAGE = "https://www.fisheries.noaa.gov/inport/item/27598"
DATA_GOV = "https://catalog.data.gov/dataset/habitat-mapping-camera-habcam"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/legalcode"
LICENCE_NAME = "CC0 1.0 (NOAA InPort 27598 HabCam record; data.gov licence field)"
CITATION = (
    "Northeast Fisheries Science Center, [Date of Access]: Habitat Mapping Camera (HABCAM) [2015-05-17/2015-06-21], "
    "https://www.fisheries.noaa.gov/inport/item/27598."
)
IMAGE_CREDIT = (
    "Image: NOAA Northeast Fisheries Science Center, HabCam V4, 2015 Sea Scallop Survey (R/V Hugh R. Sharp cruise S1 15-01, "
    "HabCam cruise 201503); obtained from the VIAME Web public training data (Kitware, https://viame.kitware.com)."
)

MAX_GAP_S = 10.0  # two bracketing 1-s fixes at most this far apart
MAX_SPEED_MS = 8.0  # implied speed between the bracketing fixes (research note, recipe step 6)
NAV_UNCERTAINTY_M = 300.0  # towed layback + clock (research note)
SMALL_BYTES = 500_000  # blank or black frames (research note): kept, marked
DEFAULT_SPACING_S = 60.0
RANGED_LOOKUPS = 150  # per leg, before the full navigation file is downloaded
ORDERS = ("spread", "table")

# Cruise legs of the 2015 survey: UTC window of the image timestamps, navigation file, weight of the spread order.
LEGS: dict[str, dict[str, Any]] = {
    "HRS1506": {
        "window": ("2015-05-16T11:52:00", "2015-05-26T00:00:00"),
        "accession": "0260576",
        "nav": "https://www.ncei.noaa.gov/data/oceans/archive/arc0207/0260576/4.6/data/0-data/HRS1506_616376_r2rnav/data/HRS1506_bestres.geoCSV",
        "weight": 0.40,
    },
    "HRS1507": {
        "window": ("2015-05-27T00:00:00", "2015-06-11T00:00:00"),
        "accession": "0206224",
        "nav": "https://www.ncei.noaa.gov/data/oceans/archive/arc0148/0206224/4.6/data/0-data/HRS1507_608881_r2rnav/data/HRS1507_bestres.geoCSV",
        "weight": 0.25,
    },
    "HRS1508": {
        "window": ("2015-06-11T00:00:00", "2015-06-24T00:00:00"),
        "accession": "0206225",
        "nav": "https://www.ncei.noaa.gov/data/oceans/archive/arc0148/0206225/3.4/data/0-data/HRS1508_608882_r2rnav/data/HRS1508_bestres.geoCSV",
        "weight": 0.35,
    },
}


def _utc(iso: str) -> float:
    return datetime.fromisoformat(iso).replace(tzinfo=timezone.utc).timestamp()


def parse_name(name: str) -> tuple[float, str] | None:
    """``201503.20150517.160624359.187700.png`` -> (UTC epoch seconds, ``2015-05-17``), or None."""
    m = NAME_RE.match(name)
    if not m:
        return None
    date, hms, ms, _ = m.groups()
    dt = datetime.strptime(date + hms, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    day = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    return dt.timestamp() + int(ms) / 1000.0, day


def leg_of(t: float) -> str | None:
    for leg, spec in LEGS.items():
        start, end = _utc(spec["window"][0]), _utc(spec["window"][1])
        if start <= t < end:
            return leg
    return None


def parse_bestres(text: str) -> tuple[list[NavFix], set[float]]:
    """Read an R2R ``*_bestres.geoCSV``. Returns the fixes (one per second, sorted) and the times of R2R-flagged fixes.

    Flagged rows are commented lines (``#2015-05-17T10:38:17Z,...``). When a second has both, the unflagged row wins.
    GeoCSV header lines (``#dataset: ...``) and the column line (``iso_time,...``) are skipped.
    """
    best: dict[float, tuple[bool, NavFix]] = {}
    for raw in text.splitlines():
        line = raw.strip()
        flagged = line.startswith("#")
        if flagged:
            line = line[1:]
        if not line[:1].isdigit():
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        t = parse_time(parts[0])
        lon, lat = to_float(parts[1]), to_float(parts[2])
        if t is None or lat is None or lon is None:
            continue
        prev = best.get(t)
        if prev is None or (prev[0] and not flagged):
            best[t] = (flagged, NavFix(t, lat, lon))
    fixes = [best[t][1] for t in sorted(best)]
    return fixes, {t for t, (f, _) in best.items() if f}


def _bitrev_order(seq: list[Any]) -> Iterator[Any]:
    """Every element once, in van der Corput order: any prefix covers the whole sequence evenly."""
    n = len(seq)
    if n == 0:
        return
    bits = (n - 1).bit_length()
    for k in range(1 << bits):
        i = int(format(k, f"0{bits}b")[::-1], 2) if bits else 0
        if i < n:
            yield seq[i]


def spread_order(cands: list[Candidate], min_spacing_s: float) -> list[Candidate]:
    """Spread order for the candidates of ONE leg (sorted by time): spaced frames first, near-duplicates last."""
    spaced: list[Candidate] = []
    rest: list[Candidate] = []
    last: float | None = None
    for c in cands:
        t = c.raw["t"]
        if last is None or t - last >= min_spacing_s:
            spaced.append(c)
            last = t
        else:
            rest.append(c)
    return list(_bitrev_order(spaced)) + list(_bitrev_order(rest))


def interleave_legs(per_leg: dict[str, list[Candidate]]) -> Iterator[Candidate]:
    """Round robin over the legs, each leg taking its share (LEGS weight) of the stream."""
    streams = {leg: iter(seq) for leg, seq in per_leg.items() if seq and leg in LEGS}
    taken: Counter[str] = Counter()
    order = list(streams)
    while streams:
        leg = min(streams, key=lambda k: ((taken[k] + 1) / LEGS[k]["weight"], order.index(k)))
        try:
            cand = next(streams[leg])
        except StopIteration:
            del streams[leg]
            continue
        taken[leg] += 1
        yield cand
    for leg, seq in per_leg.items():
        if leg not in LEGS:
            yield from seq


@register
class NoaaHabcamAdapter(Adapter):
    key = "noaa_habcam"
    name = "NOAA HabCam (NEFSC) 2015 Sea Scallop Survey stereo images (VIAME Web public training data)"
    homepage = HOMEPAGE
    citation = CITATION + " " + IMAGE_CREDIT
    media_types = ("image",)
    env_vars: tuple[str, ...] = ()
    manual_steps = (
        "None (public Girder API, no token). The NEFSC archive itself (about 2012-present, 7.9 M pairs in 2015) is not "
        "public: a formal written request to NEFSC (InPort 27598) would be needed for more years or for the per-image "
        "lat/lon/bottom_depth of the NEFSC database."
    )

    def __init__(self, ctx):
        super().__init__(ctx)
        self._items: list[dict[str, Any]] | None = None
        self._alt: dict[str, float] | None = None
        self._navs: dict[str, tuple[NavTrack, set[float]]] = {}
        self._ranged: Counter[str] = Counter()

    # ------------------------------------------------------------------------------------------- options
    def _options(self) -> tuple[str, float, str | None, str | None, bool]:
        order = str(self.options.get("order", "spread")).lower()
        if order not in ORDERS:
            raise ValueError(f"order must be one of {ORDERS}")
        spacing = float(self.options.get("min_spacing_s", DEFAULT_SPACING_S))
        day_from, day_to = self.options.get("from"), self.options.get("to")
        for d in (day_from, day_to):
            if d is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(d)):
                raise ValueError(f"from/to must be YYYY-MM-DD, got {d!r}")
        altitude = str(self.options.get("altitude", "true")).lower() not in ("false", "0", "no")
        return order, spacing, (str(day_from) if day_from else None), (str(day_to) if day_to else None), altitude

    # ------------------------------------------------------------------------------------------- metadata
    def _listing(self) -> list[dict[str, Any]]:
        """All PNG items of the 2015 folder (name order). Each page is cached under metadata/raw/viame/."""
        if self._items is None:
            items: list[dict[str, Any]] = []
            offset = 0
            pages = int(self.options.get("list_pages", 0) or 0)
            if pages > 0:
                # Quick mode: only N evenly spread pages (van der Corput order over the page index), not the whole folder.
                n_items = int(self.ctx.cached_json(f"{API}/folder/{FOLDER_2015}/details", "viame/folder_details.json")["nItems"])
                n_pages = -(-n_items // LIST_LIMIT)
                for p in sorted(list(_bitrev_order(list(range(n_pages))))[:pages]):
                    url = f"{API}/item?folderId={FOLDER_2015}&limit={LIST_LIMIT}&offset={p * LIST_LIMIT}&sort=name"
                    items.extend(self.ctx.cached_json(url, f"viame/folder_{FOLDER_2015}_offset{p * LIST_LIMIT:07d}.json"))
                self._items = [i for i in items if isinstance(i, dict) and NAME_RE.match(str(i.get("name", "")))]
                return self._items
            while True:
                url = f"{API}/item?folderId={FOLDER_2015}&limit={LIST_LIMIT}&offset={offset}&sort=name"
                batch = self.ctx.cached_json(url, f"viame/folder_{FOLDER_2015}_offset{offset:07d}.json")
                items.extend(batch)
                if len(batch) < LIST_LIMIT:
                    break
                offset += LIST_LIMIT
            self._items = [i for i in items if isinstance(i, dict) and NAME_RE.match(str(i.get("name", "")))]
        return self._items

    def _altitudes(self) -> dict[str, float]:
        """``Altitude`` (m above the seabed) per image stem, from metadata.txt (not depth)."""
        if self._alt is None:
            text = self.ctx.cached_text(f"{API}/item/{METADATA_ITEM}/download", "habcam_2015_metadata.txt")
            alt: dict[str, float] = {}
            for row in csv.DictReader(io.StringIO(text)):
                stem = (row.get("Imagename") or "").strip()
                value = to_float(row.get("Altitude"))
                if stem and value is not None:
                    alt[stem] = value
            self._alt = alt
        return self._alt

    def _nav(self, leg: str, t: float) -> tuple[NavTrack, set[float]]:
        """Nav track for ``leg``. The full bestres file is 45-50 MB: the first RANGED_LOOKUPS lookups per leg use small
        HTTP range windows around ``t`` (a sample run stays fast); after that the whole file is downloaded and cached."""
        if leg in self._navs:
            return self._navs[leg]
        name = f"nav/{LEGS[leg]['nav'].rsplit('/', 1)[-1]}"
        if not (self.ctx.layout.raw / name).exists() and self._ranged[leg] < RANGED_LOOKUPS:
            self._ranged[leg] += 1
            fixes, flagged = parse_bestres(self._nav_window(LEGS[leg]["nav"], t))
            return NavTrack(fixes, max_gap_s=MAX_GAP_S), flagged
        text = self.ctx.cached_text(LEGS[leg]["nav"], name)
        fixes, flagged = parse_bestres(text)
        self._navs[leg] = (NavTrack(fixes, max_gap_s=MAX_GAP_S), flagged)
        return self._navs[leg]

    def _nav_window(self, url: str, t: float) -> str:
        """About 64 kB of the time-sorted nav file starting shortly before ``t`` (byte bisection, 8 kB probes)."""
        size = int(self.http.head(url).headers["Content-Length"])
        target = t - 30.0

        def time_at(off: int) -> float | None:
            lines = self.http.get_range(url, off, off + 8191).decode("utf-8", "replace").splitlines()[1:-1]
            for ln in lines:
                if ln.lstrip("#")[:1].isdigit():
                    return parse_time(ln.lstrip("#").split(",")[0])
            return None

        lo, hi = 0, size
        while hi - lo > 16384:
            mid = (lo + hi) // 2
            tm = time_at(mid)
            if tm is None or tm > target:
                hi = mid
            else:
                lo = mid
        return self.http.get_range(url, lo, min(size - 1, lo + 65535)).decode("utf-8", "replace")

    # ------------------------------------------------------------------------------------------- discover
    def discover(self) -> Iterable[Candidate]:
        order, spacing, day_from, day_to, altitude = self._options()
        alt = self._altitudes() if altitude else {}
        per_leg: dict[str | None, list[Candidate]] = {leg: [] for leg in [*LEGS, None]}
        for item in sorted(self._listing(), key=lambda i: i["name"]):
            t, day = parse_name(item["name"])
            if (day_from and day < day_from) or (day_to and day > day_to):
                continue
            cand = self._candidate(item, t, day, alt.get(item["name"][:-4]))
            per_leg[cand.raw["leg"]].append(cand)
        if order == "table":
            for leg in per_leg:
                yield from per_leg[leg]
            return
        ordered = {leg: spread_order(seq, spacing) for leg, seq in per_leg.items() if leg is not None}
        ordered[None] = per_leg[None]
        yield from interleave_legs({k: v for k, v in ordered.items() if v})

    def _candidate(self, item: dict[str, Any], t: float, day: str, altitude: float | None) -> Candidate:
        iid, name = str(item["_id"]), str(item["name"])
        size = int(item.get("size") or 0)
        leg = leg_of(t)
        extra: dict[str, Any] = {
            "collection": f"VIAME Web public training data {COLLECTION}",
            "viame_folder": FOLDER_2015,
            "cruise": leg,
            "cruise_code": "201503",
            "cruise_accession": LEGS[leg]["accession"] if leg else None,
            "image_day": day,
            "file_bytes": size,
            "stereo_pair": True,
            "stereo_pair_px": [2720, 1024],
            "left_half_px": [0, 0, 1360, 1024],
            "altitude_m": altitude,
        }
        if size < SMALL_BYTES:
            extra["maybe_not_underwater"] = True
            extra["maybe_not_underwater_reason"] = f"file of {size} B (blank or black frame, research note)"
        return Candidate(
            source=self.key,
            item_id=iid,
            media_type="image",
            media_url=f"{API}/item/{iid}/download",
            origin_url=f"{API}/item/{iid}",
            timestamp=datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            ext="png",
            raw={"name": name, "size": size, "t": t, "leg": leg},
            extra=extra,
        )

    # ------------------------------------------------------------------------------------------- licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        leg = cand.raw.get("leg")
        nav = (
            f"Ship navigation: Rolling Deck to Repository (R2R) Program, cruise {leg} (R/V Hugh R. Sharp), NOAA NCEI "
            f"Accession {LEGS[leg]['accession']} (CC0 / Public Domain Mark 1.0)."
            if leg
            else ""
        )
        return make_licence(
            LICENCE_NAME,
            level="record",
            url=CC0_URL,
            attribution=f"{IMAGE_CREDIT} Cite: {CITATION} {nav}".strip(),
            tier="A",
        )

    # ------------------------------------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        leg, t = cand.raw.get("leg"), float(cand.raw["t"])
        if leg is None:
            return Geo.none(geo_source="no R2R navigation window for the filename timestamp")
        track, flagged = self._nav(leg, t)
        src = (
            f"R2R r2rnav {leg}_bestres.geoCSV ship_latitude/ship_longitude interpolated at filename UTC time "
            f"(NCEI {LEGS[leg]['accession']})"
        )
        hit = track.locate(t)
        if hit is None:
            return Geo.none(geo_source=f"{src} (no fix pair within {MAX_GAP_S:g} s)")
        i = bisect_left(track.times, t)
        if hit.gap_s > 0:
            a, b = track.fixes[i - 1], track.fixes[i]
            speed = haversine_m(a.lat, a.lon, b.lat, b.lon) / (b.t - a.t)
            if speed > MAX_SPEED_MS:
                return Geo.none(geo_source=f"{src} (fixes imply {speed:.1f} m/s: navigation jump)")
            cand.extra["nav_flagged"] = a.t in flagged or b.t in flagged
        else:
            cand.extra["nav_flagged"] = track.times[i] in flagged
        return Geo(
            lat=round(hit.lat, 6),
            lon=round(hit.lon, 6),
            depth_m=None,
            geo_precision="segment",
            geo_source=src,
            geo_inferred=True,
            geo_uncertainty_m=NAV_UNCERTAINTY_M,
        )

    # ------------------------------------------------------------------------------------------- media
    def resolve_media(self, cand: Candidate) -> MediaRef:
        size = int(cand.raw.get("size") or 0) or None
        return MediaRef(url=cand.media_url, ext="png", expected_bytes=size)

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        nbytes, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)
        with open(dest, "rb") as fh:
            magic = fh.read(4)
        if magic != PNG_MAGIC:
            dest.unlink(missing_ok=True)
            raise HttpError(ref.url, None, "not a PNG (magic number)")
        return nbytes, sha

    # ------------------------------------------------------------------------------------------- estimate
    def estimate(self) -> dict[str, Any]:
        items = self._listing()
        total = sum(int(i.get("size") or 0) for i in items)
        return {"images_2015_png": len(items), "gb_estimate": round(total / 1e9, 1)}
