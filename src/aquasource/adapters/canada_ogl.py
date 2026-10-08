"""Canada open data (Open Government Licence): GSC seafloor photographs (`canada_ogl`).

Scope of this adapter: the Geological Survey of Canada (NRCan) "Seafloor photographs, offshore Canada" collection,
record https://open.canada.ca/data/en/dataset/44cbbdc0-d33d-abe7-b08a-f5872bc0a48a (research/canada_ogl.md). About 20,017
full-resolution PNG stills from 1,804 stations on 78 expeditions (1965-2015), served over plain HTTPS from the Apache
folder tree https://ftp.maps.canada.ca/pub/nrcan_rncan/raster/marine_geoscience/Seabed_Photo_Collection/ with Range support.

NOT in this adapter (see research/canada_ogl.md, Open questions): the DFO Fundy Isles drift-camera imagery (record
f9098f77 / 8ea6c28a). Its 2022 stills sit in nested ZIPs of 350-500 MB and the MP4s are 1-2 GB each, so it needs a
member-level reader before it can be a budget-friendly route. The 2023-2024 media are not online (request to DFO).

Licence (tier B): "Open Government Licence - Canada" (CKAN ``license_id`` ca-ogl-lgo on the record, ISO 19115
``resourceConstraints`` of the record), read at record level: no file carries a licence. Attribution: the OGL default
sentence plus the GSC citation (no specific statement is given). See research/canada_ogl.md for the verification URLs.

Geo (``resolve_geo``, research note recipe A): ``PHOTO_LAT`` / ``PHOTO_LONG`` of the photo's row in the per-station CSV
(decimal degrees, EPSG:4326), ``WATER_DEPTH`` (m, positive; "Unknown" -> None). A station whose photos all share one
coordinate is ``station`` (``geo_inferred`` true, uncertainty >= 500 m); a station with distinct per-photo positions is
``image``. Uncertainty from ``HORIZONTAL_POSITIONAL_ACCURACY`` (USBL: 5 % of depth, floor 10 m; antenna-offset corrected:
20 %, floor 50 m; otherwise 20 %, floor 100 m; expeditions before 1990: floor 1000 m). Rows without a coordinate give
``Geo.none``; the MapServer station fallback of the note is not used (no extra request).

Media: ``FullResolutionImageURL`` of the row (http rewritten to https). Item id = ``<EXPED>/<STN>/<CAM>/<PHOTO>``.
Timestamp: ``JULIAN_DAY`` of the expedition year plus ``PHOTO_GMT`` (assumed GMT, not verified).

Enumeration is lazy and metadata-only: the root folder listing and expedition folder listings are cached under
metadata/raw/gsc/, then station CSVs are read one at a time in a spread order (golden-ratio sequence shifted by ``seed``).
Options: ``per_station`` (photos taken per station CSV, default 1; 0 = all), ``max_per_expedition`` (default 3; 0 = no
limit), ``seed`` (default 0).
"""

from __future__ import annotations

import csv
import io
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from ..core.geo import to_float
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

HOMEPAGE = "https://open.canada.ca/data/en/dataset/44cbbdc0-d33d-abe7-b08a-f5872bc0a48a"
GSC_ROOT = "https://ftp.maps.canada.ca/pub/nrcan_rncan/raster/marine_geoscience/Seabed_Photo_Collection"
OGL_URL = "https://open.canada.ca/en/open-government-licence-canada"
LICENCE_NAME = "Open Government Licence - Canada"
CITATION = (
    "Contains information licensed under the Open Government Licence – Canada. Source: Geological Survey of Canada "
    "(Natural Resources Canada), Seafloor photographs, offshore Canada (2020), " + HOMEPAGE
)
PNG_MAGIC = b"\x89PNG"
MIN_PNG_BYTES = 1000
GOLDEN = 0.6180339887498949
DEFAULT_PER_STATION = 1
DEFAULT_MAX_PER_EXPED = 3
NO_VALUES = {"", "na", "n/a", "unknown", "none", "null"}


# ----------------------------------------------------------------------------------------------- pure helpers
def num(value: object) -> float | None:
    """Float, or None for empty / NA / Unknown values (the GSC CSVs use all of these)."""
    if value is None or str(value).strip().lower() in NO_VALUES:
        return None
    return to_float(str(value).strip())


def expedition_year(exped: str) -> int | None:
    """Year from an expedition code: ``2010020`` -> 2010, ``95006`` -> 1995, ``82FOGO-ISLE`` -> 1982."""
    m = re.match(r"^(19[6-9]\d|20[0-2]\d)(\d{3}|[A-Z])", exped)
    if m:
        return int(m.group(1))
    m = re.match(r"^(\d{2})", exped)
    return 1900 + int(m.group(1)) if m else None


def capture_timestamp(exped: str, julian_day: object, gmt: object) -> str | None:
    """``YYYY-MM-DDTHH:MM:SS`` from the expedition year, JULIAN_DAY and PHOTO_GMT (GMT assumed); None when unknown."""
    year, day = expedition_year(exped), num(julian_day)
    if year is None or day is None or not (1 <= day <= 366):
        return None
    date = (datetime(year, 1, 1) + timedelta(days=int(day) - 1)).strftime("%Y-%m-%d")
    t = str(gmt or "").strip()
    return f"{date}T{t}" if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", t) else date


def https_url(url: str) -> str:
    return "https://" + url[len("http://"):] if url.startswith("http://") else url


def parse_station_csv(text: str) -> list[dict[str, str]]:
    """Rows of a per-station CSV (UTF-8 with or without BOM; keys and values stripped)."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    rows = []
    for row in reader:
        rows.append({(k or "").strip(): (v or "").strip() for k, v in row.items()})
    return rows


def distinct_positions(rows: Iterable[dict[str, str]]) -> int:
    """Number of distinct (PHOTO_LAT, PHOTO_LONG) pairs over the rows of one station."""
    return len({(r.get("PHOTO_LAT", ""), r.get("PHOTO_LONG", "")) for r in rows if num(r.get("PHOTO_LAT")) is not None})


def gsc_geo(row: dict[str, str], n_distinct: int, csv_name: str) -> Geo:
    """Research note recipe A, step 1-5. ``n_distinct``: distinct positions over the whole station CSV."""
    lat, lon = num(row.get("PHOTO_LAT")), num(row.get("PHOTO_LONG"))
    depth = num(row.get("WATER_DEPTH"))
    if lat is None or lon is None:
        return Geo.none(geo_source=f"GSC {csv_name} PHOTO_LAT/PHOTO_LONG empty", depth_m=depth)
    acc = row.get("HORIZONTAL_POSITIONAL_ACCURACY", "")
    if "USBL" in acc:
        frac, floor = 0.05, 10.0
    elif "antenna offset corrected" in acc:
        frac, floor = 0.20, 50.0
    else:  # "no correction made ..." (the most common text)
        frac, floor = 0.20, 100.0
    year = expedition_year(row.get("EXPED_CD", ""))
    if year is not None and year < 1990:
        floor = max(floor, 1000.0)  # pre-GPS navigation: estimate, not in the record
    unc = max(frac * depth, floor) if depth else max(floor, 1000.0)
    source = f"GSC {csv_name} PHOTO_LAT/PHOTO_LONG; WATER_DEPTH; HORIZONTAL_POSITIONAL_ACCURACY"
    if n_distinct > 1:
        return Geo(lat, lon, depth, "image", source, False, round(unc))
    return Geo(lat, lon, depth, "station", source + " (one position for all photos of the station)", True, round(max(unc, 500.0)))


def spread_order(n: int, seed: int) -> list[int]:
    """All indices 0..n-1 in a low-discrepancy order (golden ratio shifted by ``seed``)."""
    out: list[int] = []
    seen: set[int] = set()
    shift = (0.5 + seed * 0.7548776662466927) % 1.0
    for k in range(4 * n + 8):
        i = min(n - 1, int(((shift + k * GOLDEN) % 1.0) * n))
        if i not in seen:
            seen.add(i)
            out.append(i)
        if len(out) == n:
            return out
    out.extend(i for i in range(n) if i not in seen)
    return out


def evenly(rows: list[Any], k: int) -> list[Any]:
    n = len(rows)
    if k <= 0 or k >= n:
        return list(rows)
    return [rows[min(n - 1, int((i + 0.5) * n / k))] for i in range(k)]


def folder_names(index_html: str) -> list[str]:
    """Sub-folder names of an Apache directory index."""
    return [m for m in re.findall(r'href="([^"?/][^"?]*)/"', index_html)]


def file_names(index_html: str) -> list[str]:
    return [m for m in re.findall(r'href="([^"?/][^"?]*)"', index_html) if not m.endswith("/")]


def media_item_id(row: dict[str, str]) -> str:
    return f"{row['EXPED_CD']}/{row['STATION_NUM']}/{row['CAMERA_NUM']}/{row['PHOTO_NUM']}"


# ----------------------------------------------------------------------------------------------- adapter
@register
class CanadaOglAdapter(Adapter):
    key = "canada_ogl"
    name = "Canada open data: GSC seafloor photographs, offshore Canada"
    homepage = HOMEPAGE
    citation = "Geological Survey of Canada (NRCan). Seafloor photographs, offshore Canada (2020). " + HOMEPAGE
    media_types = ("image",)
    manual_steps = (
        "None for the GSC stills (anonymous HTTPS). Not implemented: DFO Fundy Isles imagery (record f9098f77, 2022 media in "
        "record 8ea6c28a: nested ZIPs of 350-2100 MB). The 2023-2024 Fundy media are not online: request them from DFO "
        "(record f9098f77 contact), a human step."
    )
    host_intervals = {"ftp.maps.canada.ca": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self.skipped: Counter[str] = Counter()

    def _int(self, name: str, default: int) -> int:
        v = to_float(self.options.get(name))
        return default if v is None else int(v)

    # ------------------------------------------------------------------------------------------- listing (cached)
    def _root_expeditions(self) -> list[str]:
        html = self.ctx.cached_text(GSC_ROOT + "/", "gsc/index/root.html")
        return sorted(folder_names(html))

    def _expedition_files(self, exped: str) -> list[str]:
        html = self.ctx.cached_text(f"{GSC_ROOT}/{exped}/", f"gsc/index/{exped}.html")
        return sorted(f for f in file_names(html) if re.match(rf"^{re.escape(exped)}_\d+\.csv$", f))

    def _station_rows(self, exped: str, csv_name: str) -> list[dict[str, str]]:
        text = self.ctx.cached_text(f"{GSC_ROOT}/{exped}/{csv_name}", f"gsc/csv/{exped}/{csv_name}")
        return parse_station_csv(text)

    # ------------------------------------------------------------------------------------------- discover
    def discover(self) -> Iterable[Candidate]:
        seed = self._int("seed", 0)
        per_station = self._int("per_station", DEFAULT_PER_STATION)
        cap = self._int("max_per_expedition", DEFAULT_MAX_PER_EXPED)
        expeditions = self._root_expeditions()
        seen: set[str] = set()
        for ei in spread_order(len(expeditions), seed):
            exped = expeditions[ei]
            taken = 0
            try:
                csv_names = self._expedition_files(exped)
            except Exception as exc:  # one broken folder must not stop the run
                self.ctx.fail(exped, "discover", f"{type(exc).__name__}: {exc}")
                continue
            for si in spread_order(len(csv_names), seed):
                if cap and taken >= cap:
                    break
                csv_name = csv_names[si]
                try:
                    rows = self._station_rows(exped, csv_name)
                except Exception as exc:
                    self.ctx.fail(f"{exped}/{csv_name}", "discover", f"{type(exc).__name__}: {exc}")
                    continue
                n_distinct = distinct_positions(rows)
                usable = [r for r in rows if r.get("FullResolutionImageURL") and r.get("EXPED_CD") and r.get("STATION_NUM")]
                for row in evenly(usable, per_station):
                    if cap and taken >= cap:
                        break
                    iid = media_item_id(row)
                    if iid in seen:
                        self.skipped["duplicate"] += 1
                        continue
                    seen.add(iid)
                    taken += 1
                    yield self._candidate(row, csv_name, n_distinct, f"{GSC_ROOT}/{exped}/{csv_name}")

    def _candidate(self, row: dict[str, str], csv_name: str, n_distinct: int, origin: str) -> Candidate:
        exped = row["EXPED_CD"]
        photo_comments = row.get("PHOTO_COMMENTS", "")
        extra = {
            "expedition": exped,
            "station": row["STATION_NUM"],
            "camera_num": row["CAMERA_NUM"],
            "photo_num": row["PHOTO_NUM"],
            "camera_type": row.get("CAMERA_TYPE") or None,
            "film_type": row.get("FILM_TYPE") or None,
            "film_scan": row.get("FILM_TYPE", "").lower() in ("print", "slide", "ektachrome"),
            "positions_at_station": n_distinct,
            "photo_comments": photo_comments or None,
            "maybe_dark": "dark" in photo_comments.lower(),
            "burned_in_labels_unchecked": True,  # film borders / data imprints not inspected
            "gsc_photo_link": row.get("PHOTO_GIS_LINK") or None,
        }
        return Candidate(
            source=self.key,
            item_id=media_item_id(row),
            media_type="image",
            media_url=https_url(row["FullResolutionImageURL"]),
            origin_url=origin,
            timestamp=capture_timestamp(exped, row.get("JULIAN_DAY"), row.get("PHOTO_GMT")),
            ext="png",
            raw={"csv": csv_name, "n_distinct": n_distinct, **row},
            extra=extra,
        )

    # ------------------------------------------------------------------------------------------- licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        attribution = f"{CITATION} Photo: {cand.item_id}."
        return make_licence(LICENCE_NAME, level="record", url=OGL_URL, attribution=attribution, tier="B")

    # ------------------------------------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        raw = cand.raw
        return gsc_geo(raw, int(raw.get("n_distinct", 0)), str(raw.get("csv", "")))

    # ------------------------------------------------------------------------------------------- media
    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(url=cand.media_url, ext="png")

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        nbytes, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)
        problem = None
        if nbytes < MIN_PNG_BYTES:
            problem = f"only {nbytes} bytes"
        else:
            with open(dest, "rb") as fh:
                if not fh.read(4).startswith(PNG_MAGIC):
                    problem = "not a PNG (magic number)"
        if problem:
            dest.unlink(missing_ok=True)
            raise ValueError(f"{ref.url}: {problem}")
        return nbytes, sha
