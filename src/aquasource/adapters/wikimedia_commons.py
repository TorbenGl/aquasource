"""Wikimedia Commons: geotagged underwater photos and videos, read through the MediaWiki API.

Commons (https://commons.wikimedia.org, API https://commons.wikimedia.org/w/api.php, state 2026-10-08) hosts about 100 M
files. Each file keeps its own licence on its description page, so the licence is read per file (level ``file``) from
``imageinfo.extmetadata`` (``LicenseShortName``, ``LicenseUrl``; the ``License`` template key is a cross-check only).
The files stay on upload.wikimedia.org; the adapter downloads the original (``imageinfo.url``). Research note:
research/wikimedia_commons.md. Fixtures: tests/fixtures/wikimedia_commons/ (SOURCE.md).

Licence (per file): ``LicenseShortName`` is classified with :func:`aquasource.core.licence.classify` ("CC BY 4.0" B,
"CC BY-SA 4.0" C, "CC0" / "Public domain" A, "CC BY-NC" X, anything else U). When the ``License`` template key (e.g.
``cc-by-4.0``) classifies to a different known tier the file is tier U (contradiction, never upgraded). ``Restrictions``
(trademark, personality rights, ...) are kept in ``extra.restrictions`` and do not change the tier.

Geo (``resolve_geo``): ``prop=coordinates`` of the File page (GeoData; the value Commons stores from the EXIF GPS block or
the ``{{Location}}`` template). Precision ``image`` as in the catalog seed, geo_inferred false, no uncertainty published.
Caveat: many files share one coordinate (a dive site or the uploader's template place), so the checker should look at
the repeated coordinates. Files without coordinates are skipped (``geo_only=true``) or kept with geo ``none``.

Discovery (metadata only): ``GET api.php?action=query&generator=categorymembers&gcmtitle=Category:<name>&gcmtype=file
&prop=coordinates|imageinfo`` (50 files per page, ``continue`` paging, each page cached under metadata/raw/categories/).
Categories are the options ``categories`` (default ``Underwater photographs,Underwater videos``). Commons has no
underwater flag: ``extra.maybe_not_underwater`` is false only when the title or description contains a marine keyword.
Coordinates are rare (about 1 file in 8 in these categories), so a budget of 3 reads a few pages.

Adapter options (``--opt key=value``)
    categories     comma list of Commons category names (without ``Category:``).
    tiers          licence tiers to yield, default ``A,B,C`` (the runner's tier selection still applies).
    geo_only       skip files without coordinates (default true).
    max_bytes      skip originals larger than this (default 500000000, about 500 MB).
    refresh_metadata  core option: re-read the cached category pages.
"""

from __future__ import annotations

import html
import json
import logging
import re
from typing import Any, Iterable, Iterator
from urllib.parse import urlparse

from ..core.geo import to_float
from ..core.http import HttpError
from ..core.licence import classify, make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, register

log = logging.getLogger(__name__)

API = "https://commons.wikimedia.org/w/api.php"
PAGE_TITLE = "https://commons.wikimedia.org/wiki/"
DEFAULT_CATEGORIES = ("Underwater photographs", "Underwater videos")
DEFAULT_TIERS = ("A", "B", "C")
PAGE = 50  # gcmlimit / colimit for non-bot clients
DEFAULT_MAX_BYTES = 500_000_000
IMAGE_MIME = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
VIDEO_MIME = {"video/webm": "webm", "video/ogg": "ogv", "application/ogg": "ogv"}
UPLOAD_HOST = "upload.wikimedia.org"
GEO_SOURCE = (
    "MediaWiki GeoData prop=coordinates of the File page (commons.wikimedia.org api.php, primary coordinate); "
    "EXIF GPS or {{Location}} template as stored by Commons, not verified per file"
)
CITATION = "Wikimedia Commons (https://commons.wikimedia.org), files as read 2026-10-08"
MARINE_RE = re.compile(
    r"(underwater|under water|scuba|diver|diving|snorkel|\bdive\b|reef|coral|fish|marine|\bsea\b|ocean|aquarium|shark|"
    r"\brov\b|seabed|kelp|sponge|jellyfish|octopus|nudibranch|wreck|anemone|dolphin|turtle|starfish|crab|lobster|shrimp)",
    re.IGNORECASE,
)


def _val(ext: dict[str, Any], key: str) -> str:
    """Text of one extmetadata entry (HTML stripped)."""
    raw = (ext.get(key) or {}).get("value") or ""
    return html.unescape(re.sub(r"<[^>]+>", " ", str(raw))).strip()


def _ext_of(url: str) -> str:
    name = urlparse(url).path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def media_type_of(mime: str) -> str | None:
    if mime in IMAGE_MIME:
        return "image"
    if mime in VIDEO_MIME:
        return "video"
    return None


def file_licence(ext: dict[str, Any]) -> tuple[str, str, str | None, bool]:
    """(tier, licence name, licence URL, template conflict) for one file. Never upgraded."""
    short = _val(ext, "LicenseShortName")
    url = _val(ext, "LicenseUrl") or None
    template = _val(ext, "License")
    tier = classify(short) if short else "U"
    conflict = False
    if template:
        t_tier = classify(template)
        if t_tier != "U" and tier != "U" and t_tier != tier:
            tier, conflict = "U", True  # contradiction: hold as U (an unknown short name is never upgraded by the template)
    return tier, short or "not stated", url, conflict


def valid_coordinate(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    return not (lat == 0 and lon == 0)


@register
class WikimediaCommonsAdapter(Adapter):
    key = "wikimedia_commons"
    name = "Wikimedia Commons: geotagged underwater photos and videos, licence per file (A/B/C)"
    homepage = "https://commons.wikimedia.org/wiki/Category:Underwater_photographs"
    citation = CITATION
    media_types = ("image", "video")
    env_vars: tuple[str, ...] = ()
    manual_steps = (
        "None (anonymous MediaWiki API). Each file keeps its own licence and author: put the per-file attribution "
        "into the dataset card. Commons requires attribution for CC BY and CC BY-SA files."
    )
    host_intervals = {"commons.wikimedia.org": 1.0, UPLOAD_HOST: 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self.skipped: dict[str, int] = {}

    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def _categories(self) -> list[str]:
        raw = self.options.get("categories", DEFAULT_CATEGORIES)
        if isinstance(raw, str):
            raw = raw.split(",")
        return [str(c).strip().removeprefix("Category:").replace("_", " ") for c in raw if str(c).strip()]

    def _tiers(self) -> set[str]:
        raw = self.options.get("tiers", ",".join(DEFAULT_TIERS))
        items = raw if isinstance(raw, list) else str(raw).split(",")
        return {str(t).strip().upper() for t in items} & set(DEFAULT_TIERS)

    # ------------------------------------------------------------------------------------------ discover
    def _params(self, category: str, cont: dict[str, str]) -> dict[str, Any]:
        return {
            "action": "query",
            "format": "json",
            "generator": "categorymembers",
            "gcmtitle": f"Category:{category}",
            "gcmtype": "file",
            "gcmlimit": PAGE,
            "prop": "coordinates|imageinfo",
            "colimit": PAGE,
            "iiprop": "url|extmetadata|size|mime|timestamp",
            "iiextmetadatafilter": "LicenseShortName|LicenseUrl|License|Artist|DateTimeOriginal|ImageDescription|Restrictions",
            **cont,
        }

    def _pages(self, category: str) -> Iterator[dict[str, Any]]:
        slug = re.sub(r"[^A-Za-z0-9]+", "_", category).strip("_").lower()
        cont: dict[str, str] = {}
        index = 0
        while True:
            name = f"categories/{slug}_{index:05d}.json"
            try:
                data = json.loads(self.ctx.cached_text(API, name, params=self._params(category, cont)))
            except HttpError as exc:
                self.ctx.fail("", "discover", f"category {category!r} page {index}: {exc}")
                return
            if "error" in data:
                self.ctx.fail("", "discover", f"category {category!r} page {index}: {data['error'].get('code')}")
                return
            yield data
            if "continue" not in data:
                return
            cont = {k: str(v) for k, v in data["continue"].items()}
            index += 1

    def discover(self) -> Iterable[Candidate]:
        seen: set[str] = set()
        tiers = self._tiers()
        max_bytes = int(self.options.get("max_bytes", DEFAULT_MAX_BYTES))
        geo_only = bool(self.options.get("geo_only", True))
        for category in self._categories():
            for data in self._pages(category):
                pages = (data.get("query") or {}).get("pages") or {}
                for page in sorted(pages.values(), key=lambda p: p.get("index", 0)):
                    cand = self._candidate(category, page, seen, tiers, max_bytes, geo_only)
                    if cand is not None:
                        yield cand

    def _candidate(self, category, page, seen, tiers, max_bytes, geo_only) -> Candidate | None:
        title = str(page.get("title") or "")
        if not title or title in seen:
            return None
        seen.add(title)
        infos = page.get("imageinfo") or []
        if not infos:
            self._skip("no imageinfo")
            return None
        info = infos[0]
        mtype = media_type_of(str(info.get("mime") or ""))
        if mtype is None:
            self._skip("not a jpeg/png/webp/webm/ogg file")
            return None
        url = str(info.get("url") or "")
        if urlparse(url).hostname != UPLOAD_HOST:
            self._skip("no upload.wikimedia.org original")
            return None
        size = int(info.get("size") or 0)
        if size > max_bytes:
            self._skip("larger than max_bytes")
            return None
        ext = info.get("extmetadata") or {}
        tier, lname, lurl, conflict = file_licence(ext)
        if tier not in tiers:
            self._skip(f"tier {tier} not in tiers option")
            return None
        coords = page.get("coordinates") or []
        lat = to_float(coords[0].get("lat")) if coords else None
        lon = to_float(coords[0].get("lon")) if coords else None
        if geo_only and not valid_coordinate(lat, lon):
            self._skip("no coordinate")
            return None
        description = _val(ext, "ImageDescription")
        restrictions = _val(ext, "Restrictions")
        artist = _val(ext, "Artist")
        date_taken = _val(ext, "DateTimeOriginal")
        return Candidate(
            source=self.key,
            item_id=title,
            media_type=mtype,
            media_url=url,
            origin_url=PAGE_TITLE + title.replace(" ", "_"),
            timestamp=None,
            ext=_ext_of(url) or None,
            raw={
                "licence": {"tier": tier, "name": lname, "url": lurl, "conflict": conflict, "artist": artist},
                "geo": {"lat": lat, "lon": lon} if valid_coordinate(lat, lon) else None,
                "size": size,
            },
            extra={
                "category": category,
                "title": title,
                "pageid": page.get("pageid"),
                "mime": info.get("mime"),
                "width": info.get("width"),
                "height": info.get("height"),
                "date_taken": date_taken or None,
                "creator": artist,
                "licence_level": "file",
                "licence_name": lname,
                "licence_conflict": conflict,
                "restrictions": restrictions or None,
                "maybe_not_underwater": not MARINE_RE.search(f"{title} {description}"),
            },
        )

    # ------------------------------------------------------------------------------------------ licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        lic = cand.raw["licence"]
        who = lic.get("artist") or "author not stated"
        attribution = (
            f"{who}. {cand.extra.get('title')}, licence {lic['name']}"
            f"{' (' + lic['url'] + ')' if lic.get('url') else ''}. {PAGE_TITLE}{cand.item_id.replace(' ', '_')}, "
            f"via Wikimedia Commons ({CITATION})."
        )
        return make_licence(lic["name"], level="file", url=lic.get("url"), attribution=attribution, tier=lic["tier"])

    # ------------------------------------------------------------------------------------------ geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        geo = cand.raw.get("geo")
        if not geo:
            return Geo.none(GEO_SOURCE)
        return Geo(geo["lat"], geo["lon"], None, "image", GEO_SOURCE, False, None)
