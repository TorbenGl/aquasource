"""GBIF occurrence media: still photos of marine / underwater occurrences with coordinates, read per media file.

GBIF (https://www.gbif.org, occurrence search https://api.gbif.org/v1/occurrence/search, GBIF.org 2026-10-08) links
about 4 billion media items to occurrence records. The files stay on the publishers' hosts (iNaturalist, Artsobservasjoner,
museums, ...); GBIF keeps the URL, the licence and the coordinates. Research note: research/gbif_marine_media.md.

Licence (tier A / B only, read per media file): the field ``media[].license`` of the occurrence is the most specific level
(level ``file``). When a media item states no licence, the occurrence field ``license`` is used (level ``record``).
Stated licences that classify as X (NC / ND / "All rights reserved"), and anything unknown, are not downloaded. The
occurrence licence is NOT used when the media item states a different one: a record marked CC0 whose photo says
CC BY-NC is excluded (checked on the Shell Museum example in the fixtures). GBIF's occurrence ``license`` filter is
therefore not used: the API ignores ``mediaLicense`` (counts were identical for CC0 and CC BY).

Geo (``resolve_geo``): ``decimalLatitude``, ``decimalLongitude`` of the occurrence (WGS 84), ``coordinateUncertaintyInMeters``
and ``depth`` (positive down, metres). Geo precision is ``image`` as in the catalog seed, but the coordinate belongs to the
occurrence (the place where the organism was recorded), so the checker should treat it as a record-level position. Records
with GBIF geospatial issues are skipped (``hasGeospatialIssue=false``); (0, 0) and out-of-range coordinates become ``none``.

Underwater filter: none is available in the API (``habitat`` and ``waterBody`` are not search parameters). The pool is
``mediaType=StillImage`` with coordinates and ``depth`` within ``depth`` (default ``0,200`` m). Every candidate is kept;
``extra.maybe_not_underwater`` is false only if the occurrence says ``habitat=marine`` or names a ``waterBody``. Most
terrestrial birds and plants are in the pool and are marked true.

How it works
    * Paging: ``GET /occurrence/search?mediaType=StillImage&hasCoordinate=true&hasGeospatialIssue=false&depth=...&limit=300&offset=N``.
      GBIF caps offset paging at 100,000 (``max_offset`` option, default 100000). Pages are not cached on disk (about 2 MB
      each); each page is requested once per run.
    * One candidate per distinct media URL (``identifier``) with an image format. Item id = the media URL (stable).
    * Politeness: 1 request/s to api.gbif.org, 1 s to media hosts (default). No token. Identifying User-Agent from core/http.py.

Adapter options (``--opt key=value``)
    depth          GBIF ``depth`` range in metres, default ``0,200``.
    max_offset     largest offset read (default 100000, GBIF maximum).
"""

from __future__ import annotations

import logging
from typing import Any, Iterable, Iterator
from urllib.parse import urlparse

from ..core.geo import depth_from, to_float
from ..core.http import HttpError
from ..core.licence import classify, make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, register

log = logging.getLogger(__name__)

API = "https://api.gbif.org/v1/occurrence/search"
PAGE = 300
MAX_OFFSET = 100_000
DEFAULT_DEPTH = "0,200"
GEO_SOURCE = "GBIF occurrence decimalLatitude/decimalLongitude (+ coordinateUncertaintyInMeters, depth); occurrence-level position"
IMAGE_EXT = {"jpg", "jpeg", "png", "tif", "tiff", "webp"}
IMAGE_FORMATS = ("image/jpeg", "image/png", "image/tiff", "image/webp")
CITATION = "GBIF.org (2026-10-08) GBIF occurrence search, https://www.gbif.org/occurrence/search"


def _ext_of(url: str) -> str:
    path = urlparse(url).path
    return path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""


def is_image(media: dict[str, Any], url: str) -> bool:
    """A still image by URL extension (when there is one) or by the GBIF format field."""
    ext = _ext_of(url)
    if ext:
        return ext in IMAGE_EXT
    return str(media.get("format") or "").lower().startswith(IMAGE_FORMATS)


def valid_coordinate(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    return not (lat == 0 and lon == 0)


def media_licence(media: dict[str, Any], record: dict[str, Any]) -> tuple[str, str]:
    """(level, licence text): the media item's own licence first, the occurrence licence only when the item states none."""
    own = str(media.get("license") or "").strip()
    if own:
        return "file", own
    rec = str(record.get("license") or "").strip()
    if rec:
        return "record", rec
    return "unknown", ""


def maybe_not_underwater(record: dict[str, Any]) -> bool:
    habitat = str(record.get("habitat") or "").strip().lower()
    water = str(record.get("waterBody") or "").strip()
    return not (habitat == "marine" or water)


@register
class GbifMarineMediaAdapter(Adapter):
    key = "gbif_marine_media"
    name = "GBIF occurrence media: marine still photos with coordinates, CC0 / CC BY per media file"
    homepage = "https://www.gbif.org/occurrence/search?media_type=StillImage"
    citation = CITATION
    media_types = ("image",)
    env_vars: tuple[str, ...] = ()
    manual_steps = (
        "None (anonymous GBIF API). Each photo keeps its own licence and creator: put the attribution of each sample "
        "into the dataset card and check that the publishers' terms of the media hosts allow model pretraining."
    )
    host_intervals = {"api.gbif.org": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self.skipped: dict[str, int] = {}

    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def _params(self, offset: int) -> dict[str, Any]:
        return {
            "mediaType": "StillImage",
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "depth": str(self.options.get("depth", DEFAULT_DEPTH)),
            "limit": PAGE,
            "offset": offset,
        }

    def _pages(self) -> Iterator[list[dict[str, Any]]]:
        max_offset = min(int(self.options.get("max_offset", MAX_OFFSET)), MAX_OFFSET)
        offset = 0
        while offset < max_offset:
            try:
                data = self.http.get_json(API, params=self._params(offset))
            except HttpError as exc:
                self.ctx.fail("", "discover", f"GBIF page offset={offset}: {exc}")
                return
            results = data.get("results") or []
            if results:
                yield results
            if data.get("endOfRecords") or not results:
                return
            offset += PAGE

    # ------------------------------------------------------------------------------------------ discover
    def discover(self) -> Iterable[Candidate]:
        seen: set[str] = set()
        for page in self._pages():
            for rec in page:
                yield from self._candidates(rec, seen)

    def _candidates(self, rec: dict[str, Any], seen: set[str]) -> Iterator[Candidate]:
        lat, lon = to_float(rec.get("decimalLatitude")), to_float(rec.get("decimalLongitude"))
        if not valid_coordinate(lat, lon):
            self._skip("no valid coordinate")
            return
        key = str(rec.get("key") or rec.get("gbifID") or "")
        for media in rec.get("media") or []:
            if str(media.get("type") or "").lower() != "stillimage":
                continue
            url = str(media.get("identifier") or "").strip()
            if not url.startswith(("http://", "https://")):
                self._skip("media without http url")
                continue
            if url in seen:
                continue
            seen.add(url)
            if not is_image(media, url):
                self._skip("not an image file")
                continue
            level, text = media_licence(media, rec)
            raw_licence = str(rec.get("license") or "")
            yield Candidate(
                source=self.key,
                item_id=url,
                media_type="image",
                media_url=url,
                origin_url=f"https://www.gbif.org/occurrence/{key}",
                timestamp=rec.get("eventDate") or None,
                ext=_ext_of(url) or None,
                raw={"occurrence": rec, "media": media, "licence_level": level, "licence_text": text},
                extra={
                    "occurrence_key": key,
                    "dataset_key": rec.get("datasetKey"),
                    "basis_of_record": rec.get("basisOfRecord"),
                    "scientific_name": rec.get("scientificName"),
                    "country": rec.get("country"),
                    "habitat": rec.get("habitat"),
                    "water_body": rec.get("waterBody"),
                    "licence_level": level,
                    "licence_name": text,
                    "record_licence": raw_licence,
                    "licence_conflict": bool(text and raw_licence and classify(text) != classify(raw_licence)),
                    "creator": media.get("creator") or media.get("rightsHolder") or "",
                    "maybe_not_underwater": maybe_not_underwater(rec),
                },
            )

    # ------------------------------------------------------------------------------------------ licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        text = str(cand.raw.get("licence_text") or "")
        level = str(cand.raw.get("licence_level") or "unknown")
        tier = classify(text) if text else "U"
        url = text if text.startswith("http") else None
        who = cand.extra.get("creator") or "creator not stated"
        attribution = (
            f"{who}. Image {cand.media_url}, licence {text or 'not stated'}. GBIF occurrence {cand.extra.get('occurrence_key')}"
            f" (https://www.gbif.org/occurrence/{cand.extra.get('occurrence_key')}), dataset {cand.extra.get('dataset_key')},"
            f" via GBIF.org ({CITATION})."
        )
        return make_licence(text or "not stated", level=level, url=url, attribution=attribution, tier=tier)

    # ------------------------------------------------------------------------------------------ geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        rec = cand.raw["occurrence"]
        lat, lon = to_float(rec.get("decimalLatitude")), to_float(rec.get("decimalLongitude"))
        depth = depth_from(rec.get("depth"))
        if not valid_coordinate(lat, lon):
            return Geo.none(GEO_SOURCE, depth_m=depth)
        return Geo(lat, lon, depth, "image", GEO_SOURCE, False, to_float(rec.get("coordinateUncertaintyInMeters")))
