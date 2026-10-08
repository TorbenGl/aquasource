"""MAREANO (Norway, HI / NGU / Kartverket): geolocated seabed frame grabs (`mareano`).

Scope: the 340 curated video frame grabs of the open point layer ``mareano_stasjoner:bilder_biologi`` (2006-2021,
62-80 N, 1-37 E, up to 2,731 m), research/mareano.md. The raw video archive (3,908 lines) is NOT public: it is shared on
request through IMR's S3 store (datahjelp@hi.no), so it is not implemented here.

Licence (tier C, read at collection level): the image files are hosted in the HI media archive (Imageshop). Its terms
say "Bileta i dette arkivet er til fri deling og gjenbruk med CC-BY-SA 4.0 lisens dersom ikkje anna er oppgitt"
(https://hi.imageshop.no/1636899/StaticText/TermsOfUse). The Geonorge record of the point layer says CC BY 4.0
(record level, https://kartkatalog.geonorge.no/metadata/305852ff-5686-4454-ab11-b3ef55a9f5c7). That is a contradiction.
The stricter reading (share-alike) is kept, so the samples go to the ``_sharealike`` shard and are off by default
(``include_sharealike``). Never upgraded to B without IMR confirmation.

Geo (``resolve_geo``, research note "resolve_geo recipe"): ``Latitude`` / ``Longitude`` of the layer row, taken from the
full-precision WKT / JSON properties (the geometry in the feed is rounded to 4 decimals). Depth ``DYBDE`` (0 = missing,
then the station ``BottomDepth`` of ``videostasjoner_aarlig`` for ``REFSTASJ``). The coordinate is compared with its own
reference station: < 2 m -> station (inferred, 500 m); <= 2 km or no station -> image (50 m); <= 50 km -> region (QC
conflict, uncertainty = distance); further -> none.

Media: the layer row has no file. The image is found on Imageshop by its title (``TITTEL_N``, accepted only when the
``Skildring`` is identical; fallback: the legacy ``HI-xxxxxx`` id). The 1,024 px preview JPG is downloaded through its
presigned ``data-previewurl`` (~176 KB; the full-size TIF/JPG needs an untested session POST). Presigned URLs expire
after about 7 days, so they are resolved right before the download and never cached.

Politeness: 1 request/s per host, metadata cached in metadata/raw/. No token, no account.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote
from zoneinfo import ZoneInfo

from ..core.geo import haversine_m, to_float
from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

KART = "https://kart.hi.no/mareano/ogc/features/v1/collections"
LAYER_JSON = f"{KART}/mareano_stasjoner:bilder_biologi/items?f=application%2Fgeo%2Bjson&limit=1000"
STATIONS_CSV = f"{KART}/mareano_stasjoner:videostasjoner_aarlig/items?f=text%2Fcsv&limit=5000"
IMAGESHOP = "https://hi.imageshop.no/1636899"
HOMEPAGE = "https://www.mareano.no/bilder-og-video"
LAYER_RECORD = "https://kartkatalog.geonorge.no/metadata/305852ff-5686-4454-ab11-b3ef55a9f5c7"
ARCHIVE_TERMS = f"{IMAGESHOP}/StaticText/TermsOfUse"
LICENCE_NAME = "CC BY-SA 4.0"
LICENCE_URL = "https://creativecommons.org/licenses/by-sa/4.0/deed.no"
ATTRIBUTION = (
    "Photo: MAREANO / Havforskningsinstituttet (Institute of Marine Research, Norway), www.mareano.no. "
    "Licence CC BY-SA 4.0 (HI media archive terms)."
)
JPEG_MAGIC = b"\xff\xd8\xff"
MIN_JPEG_BYTES = 2_000
TZ = ZoneInfo("Europe/Oslo")

# Distance thresholds of the research note (metres)
STATION_POINT_M = 2.0
IMAGE_MAX_M = 2_000.0
REGION_MAX_M = 50_000.0
IMAGE_UNCERTAINTY_M = 50.0
STATION_UNCERTAINTY_M = 500.0
GEO_SOURCE = (
    "kart.hi.no mareano_stasjoner:bilder_biologi Latitude/Longitude (WGS 84, full precision of the WKT / JSON), "
    "DYBDE (m); station check against videostasjoner_aarlig by REFSTASJ"
)

_THUMB_RE = re.compile(r'thumb-holder comparableAsset" data-documentid="(\d+)"')
_PREVIEW_RE = re.compile(r'data-previewurl="([^"]+)"')
_SKILD_RE = re.compile(r"Skildring:</strong>(.*?)</li>", re.S)
_KODE_RE = re.compile(r"Kode:</strong>\s*(HAV-\d+)")
_KRED_RE = re.compile(r"Kreditering:</strong>(.*?)</li>", re.S)
_HI_ID_RE = re.compile(r"HI-(\d+)")
_POINT_RE = re.compile(r"POINT\s*\(\s*([-\d.eE]+)\s+([-\d.eE]+)\s*\)")


def _key(*parts: object) -> int:
    return int(hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:12], 16)


def _text(fragment: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())


def parse_stations(text: str) -> dict[int, dict[str, Any]]:
    """videostasjoner_aarlig CSV -> {RefStation: {lat, lon, bottom_depth}} (lat/lon from the_geom, full precision)."""
    out: dict[int, dict[str, Any]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        ref = to_float(row.get("RefStation"))
        m = _POINT_RE.search(row.get("the_geom") or "")
        if ref is None or not m:
            continue
        lon, lat = float(m.group(1)), float(m.group(2))
        out[int(ref)] = {"lat": lat, "lon": lon, "bottom_depth": to_float(row.get("BottomDepth"))}
    return out


def parse_imageshop(page: str) -> list[dict[str, Any]]:
    """Imageshop search page -> one dict per thumbnail (document id, preview url, Skildring, Kode, Kreditering)."""
    starts = [(m.start(), m.group(1)) for m in _THUMB_RE.finditer(page)]
    hits = []
    for i, (pos, doc_id) in enumerate(starts):
        block = page[pos : starts[i + 1][0] if i + 1 < len(starts) else len(page)]
        prev = _PREVIEW_RE.search(block)
        skild = _SKILD_RE.search(block)
        kode = _KODE_RE.search(block)
        kred = _KRED_RE.search(block)
        hits.append(
            {
                "document_id": doc_id,
                "preview_url": html.unescape(prev.group(1)) if prev else None,
                "skildring": _text(skild.group(1)) if skild else "",
                "kode": kode.group(1) if kode else None,
                "kreditering": _text(kred.group(1)) if kred else None,
            }
        )
    return hits


def local_timestamp(dato: object, tid: object) -> tuple[str | None, bool]:
    """``DATO`` is local midnight stored as UTC (2007-03-30T22:00:00Z = 2007-03-31). Returns (timestamp, has_time)."""
    if not dato:
        return None, False
    try:
        local = datetime.fromisoformat(str(dato).replace("Z", "+00:00")).astimezone(TZ)
    except ValueError:
        return None, False
    t = str(tid or "").strip()
    if t:
        return f"{local.date().isoformat()}T{t}", True
    return local.date().isoformat(), False


@register
class MareanoAdapter(Adapter):
    key = "mareano"
    name = "MAREANO (Norway): geolocated seabed frame grabs, bilder_biologi"
    homepage = HOMEPAGE
    citation = (
        "MAREANO, Havforskningsinstituttet, Norges geologiske undersøkelse, Kartverket. Mareanobilder, biologi "
        f"(Geonorge record 305852ff). {HOMEPAGE}"
    )
    media_types = ("image",)
    manual_steps = (
        "None for the 340 frame grabs (anonymous HTTPS). Not implemented: the raw video archive (3,908 lines) is on request "
        "via IMR S3 (datahjelp@hi.no); the licence of that archive is unknown (tier U)."
    )
    host_intervals = {"kart.hi.no": 1.0, "hi.imageshop.no": 1.0, "s3.eu-west-1.amazonaws.com": 0.5}

    def _layer(self) -> dict[str, Any]:
        return self.ctx.cached_json(LAYER_JSON, "mareano/bilder_biologi.json")

    def _stations(self) -> dict[int, dict[str, Any]]:
        if not hasattr(self, "_station_map"):
            self._station_map = parse_stations(self.ctx.cached_text(STATIONS_CSV, "mareano/videostasjoner_aarlig.csv"))
        return self._station_map

    # ------------------------------------------------------------------------------------------- discover
    def discover(self) -> Iterable[Candidate]:
        seed = int(to_float(self.options.get("seed")) or 0)
        max_per_line = int(to_float(self.options.get("max_per_line")) or 0)
        feats = [f for f in self._layer().get("features", []) if f.get("id")]
        groups: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
        for f in feats:
            p = f.get("properties") or {}
            groups.setdefault((p.get("TOKT"), p.get("REFSTASJ"), p.get("VLINJE")), []).append(f)
        ranked: list[tuple[int, int, dict[str, Any]]] = []
        for members in groups.values():
            members.sort(key=lambda f: _key(seed, f["id"]))
            for k, f in enumerate(members):
                if max_per_line and k >= max_per_line:
                    continue
                ranked.append((k, _key(seed, f["id"]), f))
        # Round 1 takes one still per video line, so a short sample covers many lines; later rounds take the rest.
        for _, _, f in sorted(ranked, key=lambda t: (t[0], t[1])):
            yield self._candidate(f)

    def _candidate(self, feat: dict[str, Any]) -> Candidate:
        p = feat.get("properties") or {}
        bilde_url = str(p.get("BILDEURL") or "")
        hi_id = _HI_ID_RE.search(bilde_url)
        title = str(p.get("TITTEL_N") or "")
        ts, has_time = local_timestamp(p.get("DATO"), p.get("TID"))
        extra = {
            "title": title or None,
            "taxon": p.get("TITTEL_E") or None,
            "cruise": p.get("TOKT"),
            "station": p.get("REFSTASJ"),
            "video_line": p.get("VLINJE"),
            "bilde_fil": p.get("BILDEFIL") or None,
            "legacy_hi_id": f"HI-{hi_id.group(1)}" if hi_id else None,
            "time_zone_assumed": "Europe/Oslo" if has_time else None,
            "resolution": "1024 px preview (Imageshop presigned URL)",
            "maybe_not_underwater": False,
            "licence_conflict": "Geonorge record CC BY 4.0 vs HI archive CC BY-SA 4.0; tier C kept",
        }
        search = f"{IMAGESHOP}/Search?Q={quote(title)}"
        return Candidate(
            source=self.key,
            item_id=str(feat["id"]),
            media_type="image",
            media_url=search,
            origin_url=LAYER_RECORD,
            timestamp=ts,
            ext="jpg",
            raw={"props": p, "dyb": p.get("DYBDE")},
            extra=extra,
        )

    # ------------------------------------------------------------------------------------------- licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        return make_licence(LICENCE_NAME, level="collection", url=ARCHIVE_TERMS, attribution=ATTRIBUTION, tier="C")

    # ------------------------------------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        p = cand.raw.get("props") or {}
        lat, lon = to_float(p.get("Latitude")), to_float(p.get("Longitude"))
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            return Geo.none(geo_source="layer row without a usable Latitude/Longitude")
        depth = to_float(p.get("DYBDE"))
        depth = depth if depth and depth > 0 else None
        source = GEO_SOURCE
        st = self._stations().get(int(to_float(p.get("REFSTASJ")) or -1))
        if depth is None and st and st["bottom_depth"] is not None:
            depth = st["bottom_depth"]
            source += "; depth from videostasjoner_aarlig.BottomDepth"
        if st is None:
            return Geo(lat, lon, depth, "image", source, False, IMAGE_UNCERTAINTY_M)
        d = haversine_m(lat, lon, st["lat"], st["lon"])
        cand.extra["station_distance_m"] = round(d, 1)
        if d < STATION_POINT_M:
            return Geo(lat, lon, depth, "station", source + "; equals the station point", True, STATION_UNCERTAINTY_M)
        if d <= IMAGE_MAX_M:
            return Geo(lat, lon, depth, "image", source, False, IMAGE_UNCERTAINTY_M)
        if d <= REGION_MAX_M:
            cand.extra["qc_conflict"] = "frame position is %.0f m from its reference station" % d
            return Geo(lat, lon, depth, "region", source + "; QC conflict with REFSTASJ", False, round(d))
        cand.extra["qc_conflict"] = "frame position is %.0f km from its reference station" % (d / 1000)
        return Geo.none(geo_source=source + "; rejected, far from REFSTASJ")

    # ------------------------------------------------------------------------------------------- media
    def resolve_media(self, cand: Candidate) -> MediaRef:
        title = cand.extra.get("title") or ""
        hits = self._search(cand, title, cand.item_id)
        exact = [h for h in hits if h["skildring"] == title and h["preview_url"]]
        if not exact and cand.extra.get("legacy_hi_id"):
            hits = self._search(cand, cand.extra["legacy_hi_id"], cand.item_id + "-hi")
            exact = [h for h in hits if h["preview_url"] and h["skildring"] == title] or (
                [h for h in hits if h["preview_url"]] if len(hits) == 1 else []
            )
        if not exact:
            raise RuntimeError(f"no Imageshop asset matches the title {title!r} ({len(hits)} hits)")
        hit = exact[0]
        cand.extra.update(
            {
                "imageshop_document_id": hit["document_id"],
                "imageshop_kode": hit["kode"],
                "imageshop_kreditering": hit["kreditering"],
                "imageshop_matches": len(exact),
            }
        )
        return MediaRef(url=hit["preview_url"], ext="jpg")

    def _search(self, cand: Candidate, query: str, name: str) -> list[dict[str, Any]]:
        url = f"{IMAGESHOP}/Search?Q={quote(query)}"
        page = self.ctx.cached_text(url, f"mareano/imageshop/{name}.html")
        return parse_imageshop(page)

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        nbytes, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)
        with open(dest, "rb") as fh:
            magic = fh.read(3)
        if nbytes < MIN_JPEG_BYTES or magic != JPEG_MAGIC:
            dest.unlink(missing_ok=True)
            raise ValueError(f"{ref.url}: not a JPEG ({nbytes} bytes)")
        return nbytes, sha
