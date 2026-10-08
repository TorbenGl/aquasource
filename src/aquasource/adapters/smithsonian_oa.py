"""Smithsonian Open Access (EDAN metadata on the public AWS bucket): CC0 images with a marine locality.

The metadata is read from the public bucket ``smithsonian-open-access`` (no key; api.si.edu needs an api.data.gov key
and is not used). Each unit (e.g. ``nmnhinv`` = NMNH Invertebrate Zoology) has 256 line-delimited JSON shards
``metadata/edan/<unit>/<NN>.txt`` (5-20 MB each). A shard is streamed record by record and never stored, so a budget
of 3 reads only the first shard of the first unit (research note). Media are the ``Screen Image`` derivative of the
``ids.si.edu`` delivery service, a JPEG of a few thousand pixels (not the TIFF / high-resolution originals).

Yielded (per record, first CC0 media item with a Screen Image resource):
    * ``usage.access == "CC0"`` on the media (tier A, record level). Any other access value is skipped.
    * a point coordinate in ``indexedStructured.geoLocation[].points.point`` (the published collection locality of the
      specimen). Records without one are skipped (``require_coords``).
    * by default a marine locality (``marine_only``: ocean / sea / gulf / reef / ... in the place labels or the geoLocation
      L1 ocean name). Terrestrial specimen photos are not underwater data and are not downloaded by default.
    * Noisy data is kept, not dropped: ``extra.maybe_not_underwater`` is true when no in-situ / underwater keyword
      (underwater, in situ, ROV, submersible, diver, reef, seafloor, benthic, camera, dive) appears in the record.
      Most Smithsonian records are specimen photographs, so the flag is true for the majority of marine records.

Geo: ``region`` precision, lat / lon from the record (WGS 84), geo_inferred false, geo_uncertainty_m None (the locality
is a collection locality, not the camera position). depth_m from freetext ``Depth (m)`` (collection depth; a range
gives its midpoint), not the camera depth.

Licence: record level (``usage.access`` of the media). Metadata licence: CC0 1.0 for the GitHub metadata repository
(https://github.com/Smithsonian/OpenAccess/blob/master/LICENSE).

Adapter options (``--opt key=value``)
    units          comma list of unit codes (default ``nmnhinv,nmnhfishes``; index: metadata/edan/<unit>/index.txt).
    shards         at most this many shards per unit (default all 256; ``1`` is the cheapest sample).
    marine_only    keep marine localities only (default true).
    require_coords skip records without a coordinate (default true).
    refresh_metadata core option: re-read the unit index files.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Iterable, Iterator

from ..core.geo import to_float
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, register

log = logging.getLogger(__name__)

BUCKET = "https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan"
UNIT_NAMES = {
    "nmnhinv": "NMNH Invertebrate Zoology",
    "nmnhfishes": "NMNH Vertebrate Zoology, Fishes",
    "nmnhherps": "NMNH Vertebrate Zoology, Herpetology",
    "nmnhmammals": "NMNH Vertebrate Zoology, Mammals",
    "nmnhbirds": "NMNH Vertebrate Zoology, Birds",
    "nmnhpaleo": "NMNH Paleobiology",
    "nmnhbotany": "NMNH Botany",
}
DEFAULT_UNITS = ("nmnhinv", "nmnhfishes")
SHARDS_PER_UNIT = 256
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
METADATA_LICENCE_URL = "https://github.com/Smithsonian/OpenAccess/blob/master/LICENSE"
GEO_SOURCE = (
    "EDAN record indexedStructured.geoLocation[].points.point.latitude/longitude (published collection locality of the "
    "specimen, not the camera position)"
)
DEPTH_SOURCE = "freetext physicalDescription 'Depth (m)' (collection depth; range = midpoint)"
MARINE_RE = re.compile(
    r"\b(ocean|sea|gulf|reef|bay|coast|atoll|lagoon|strait|channel|sound|inlet|seamount|canyon|bank|"
    r"islands?|archipelago|fjord|sea)\b",
    re.IGNORECASE,
)
UNDERWATER_RE = re.compile(
    r"underwater|in[ -]situ|\bROV\b|submersible|diver|\breef|seafloor|benthic|seascape|\bARMS\b|camera|\bdive",
    re.IGNORECASE,
)
MAGIC_JPEG = b"\xff\xd8\xff"


# ----------------------------------------------------------------------------------------------- pure helpers
def _labels(section: object) -> list[dict[str, Any]]:
    return [x for x in section if isinstance(x, dict)] if isinstance(section, list) else []


def place_text(rec: dict[str, Any]) -> str:
    """Place, ocean and geoLocation names of a record, joined (for the marine test)."""
    c = rec.get("content", {})
    parts = [str(x.get("content", "")) for x in _labels(c.get("freetext", {}).get("place"))]
    parts += [str(x.get("content", "")) for x in _labels(c.get("freetext", {}).get("name")) if "Ocean" in str(x.get("label"))]
    for g in c.get("indexedStructured", {}).get("geoLocation", []) or []:
        for key in ("L1", "L2", "L3"):
            if isinstance(g.get(key), dict):
                parts.append(str(g[key].get("content", "")))
    return " | ".join(p for p in parts if p)


def is_marine(rec: dict[str, Any]) -> bool:
    return bool(MARINE_RE.search(place_text(rec)))


def point_of(rec: dict[str, Any]) -> tuple[float, float] | None:
    """First valid (lat, lon) of indexedStructured.geoLocation[].points.point."""
    for g in rec.get("content", {}).get("indexedStructured", {}).get("geoLocation", []) or []:
        pts = g.get("points") if isinstance(g, dict) else None
        point = pts.get("point") if isinstance(pts, dict) else None
        if not isinstance(point, dict):
            continue
        lat = to_float((point.get("latitude") or {}).get("content") if isinstance(point.get("latitude"), dict) else point.get("latitude"))
        lon = to_float((point.get("longitude") or {}).get("content") if isinstance(point.get("longitude"), dict) else point.get("longitude"))
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            continue
        return lat, lon
    return None


def depth_of(rec: dict[str, Any]) -> float | None:
    for x in _labels(rec.get("content", {}).get("freetext", {}).get("physicalDescription")):
        if str(x.get("label", "")).strip().lower() != "depth (m)":
            continue
        nums = [to_float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", str(x.get("content", "")))]
        nums = [n for n in nums if n is not None]
        if len(nums) == 1:
            return abs(nums[0])
        if len(nums) >= 2:
            return abs((nums[0] + nums[1]) / 2)
    return None


def cc0_screen_media(rec: dict[str, Any]) -> tuple[dict[str, Any], str] | None:
    """First media item with usage.access == CC0 and a Screen Image resource url."""
    for m in (rec.get("content", {}).get("descriptiveNonRepeating", {}).get("online_media", {}) or {}).get("media", []) or []:
        if not isinstance(m, dict) or (m.get("usage") or {}).get("access") != "CC0":
            continue
        for r in m.get("resources", []) or []:
            if isinstance(r, dict) and r.get("label") == "Screen Image" and r.get("url"):
                return m, str(r["url"])
    return None


def light_raw(rec: dict[str, Any], unit: str, media: dict[str, Any], screen_url: str) -> dict[str, Any]:
    """The fields the adapter needs. The full EDAN record is not stored (size, and no unused fields)."""
    c = rec.get("content", {})
    dn = c.get("descriptiveNonRepeating", {})
    return {
        "record_id": rec.get("id"),
        "unit": unit,
        "title": rec.get("title"),
        "record_link": dn.get("record_link") or dn.get("guid"),
        "media_id": media.get("id"),
        "ids_id": media.get("idsId"),
        "access": (media.get("usage") or {}).get("access"),
        "screen_url": screen_url,
        "point": point_of(rec),
        "depth_m": depth_of(rec),
        "place": place_text(rec),
        "marine": is_marine(rec),
        "text": json.dumps(c.get("freetext", {}), ensure_ascii=False)[:4000] + " " + str(rec.get("title", "")),
    }


def iter_shard_lines(lines: Iterable[bytes | str]) -> Iterator[dict[str, Any]]:
    """Parse JSON lines; malformed lines (truncated shard, bad encoding) are skipped."""
    for line in lines:
        if not line or not line.strip():
            continue
        try:
            yield json.loads(line)
        except (ValueError, UnicodeDecodeError):
            continue


def check_options(options: dict[str, Any]) -> list[str]:
    problems = []
    units = _unit_list(options.get("units"))
    bad = [u for u in units if not re.fullmatch(r"[a-z0-9]+", u)]
    if bad:
        problems.append(f"option units must be unit codes like nmnhinv (got {bad})")
    n = to_float(options.get("shards"))
    if options.get("shards") not in (None, "") and (n is None or not 1 <= n <= SHARDS_PER_UNIT):
        problems.append(f"option shards must be 1..{SHARDS_PER_UNIT}")
    return problems


def _unit_list(value: object) -> list[str]:
    if value in (None, ""):
        return list(DEFAULT_UNITS)
    if isinstance(value, str):
        value = [x for x in re.split(r"[,\s\[\]\"']+", value) if x]
    return [str(x).strip().lower() for x in (value if isinstance(value, (list, tuple)) else [value]) if str(x).strip()]


def _flag(value: object, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("0", "false", "no", "off")
    return bool(value)


@register
class SmithsonianOpenAccessAdapter(Adapter):
    key = "smithsonian_oa"
    name = "Smithsonian Open Access: CC0 images with a marine locality (EDAN metadata on AWS)"
    homepage = "https://www.si.edu/openaccess"
    citation = (
        "Smithsonian Institution, Smithsonian Open Access (https://www.si.edu/openaccess), metadata from the AWS Open Data "
        "bucket smithsonian-open-access (https://registry.opendata.aws/smithsonian-open-access/)."
    )
    media_types = ("image",)
    env_vars: tuple[str, ...] = ()
    manual_steps = (
        "None for the metadata and the CC0 Screen Images (public AWS bucket, no key). api.si.edu needs an api.data.gov key "
        "and is not used."
    )
    host_intervals = {"smithsonian-open-access.s3-us-west-2.amazonaws.com": 1.0, "ids.si.edu": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._units = _unit_list(self.options.get("units"))
        self._seen: set[str] = set()

    def check_ready(self) -> list[str]:
        return super().check_ready() + check_options(self.options)

    # ------------------------------------------------------------------------------------------- discover
    def _shard_urls(self, unit: str) -> list[str]:
        text = self.ctx.cached_text(f"{BUCKET}/{unit}/index.txt", f"smithsonian_oa/{unit}_index.txt")
        urls = [u.strip() for u in text.splitlines() if u.strip().endswith(".txt")]
        limit = to_float(self.options.get("shards"))
        return urls[: int(limit)] if limit else urls

    def _stream_shard(self, url: str) -> Iterator[dict[str, Any]]:
        resp = self.http.get(url, stream=True)
        try:
            yield from iter_shard_lines(resp.iter_lines())
        finally:
            resp.close()

    def discover(self) -> Iterable[Candidate]:
        marine_only = _flag(self.options.get("marine_only"), True)
        need_coords = _flag(self.options.get("require_coords"), True)
        for unit in self._units:
            for url in self._shard_urls(unit):
                log.info("smithsonian_oa: reading %s", url)
                for rec in self._stream_shard(url):
                    cand = self._candidate(rec, unit, marine_only, need_coords)
                    if cand is not None:
                        yield cand

    def _candidate(self, rec: dict[str, Any], unit: str, marine_only: bool, need_coords: bool) -> Candidate | None:
        if not isinstance(rec, dict) or not rec.get("id"):
            return None
        hit = cc0_screen_media(rec)
        if hit is None:
            return None
        media, screen_url = hit
        raw = light_raw(rec, unit, media, screen_url)
        if need_coords and raw["point"] is None:
            return None
        if marine_only and not raw["marine"]:
            return None
        item_id = str(media.get("id") or f"{rec['id']}-0")
        if item_id in self._seen:
            return None
        self._seen.add(item_id)
        extra = {
            "record_id": rec.get("id"),
            "unit": unit,
            "unit_name": UNIT_NAMES.get(unit, unit),
            "maybe_not_underwater": not UNDERWATER_RE.search(raw["text"]),
            "marine_place": raw["marine"],
            "media_resource": "Screen Image",
            "ids_url": f"https://ids.si.edu/ids/deliveryService/id/{media.get('idsId')}" if media.get("idsId") else None,
        }
        return Candidate(
            source=self.key,
            item_id=item_id,
            media_type="image",
            media_url=screen_url,
            origin_url=str(raw["record_link"] or f"https://collections.si.edu/search/detail/{rec.get('url', '')}"),
            timestamp=None,
            ext="jpg",
            raw=raw,
            extra=extra,
        )

    # ------------------------------------------------------------------------------------------- licence / geo
    def resolve_licence(self, cand: Candidate) -> Licence:
        access = str(cand.raw.get("access") or "").strip()
        attribution = (
            f"Smithsonian Institution, {UNIT_NAMES.get(cand.raw.get('unit'), cand.raw.get('unit'))}: "
            f"{cand.raw.get('title') or cand.item_id}. Smithsonian Open Access, CC0 1.0 (usage access {access}). "
            f"Record {cand.raw.get('record_link')}"
        )
        return make_licence(access or "not stated", level="record", url=CC0_URL, attribution=attribution)

    def resolve_geo(self, cand: Candidate) -> Geo:
        point = cand.raw.get("point")
        depth = cand.raw.get("depth_m")
        if not point:
            return Geo.none(geo_source="EDAN indexedStructured.geoLocation points (absent)", depth_m=depth)
        lat, lon = point
        return Geo(lat, lon, depth, "region", GEO_SOURCE, False, None)

    # ------------------------------------------------------------------------------------------- media
    def fetch_media(self, cand: Candidate, ref, dest: Path) -> tuple[int, str]:
        nbytes, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)
        with open(dest, "rb") as fh:
            ok = fh.read(len(MAGIC_JPEG)).startswith(MAGIC_JPEG)
        if not ok:
            dest.unlink(missing_ok=True)
            raise RuntimeError(f"ids.si.edu answer for {cand.item_id} is not a JPEG")
        return nbytes, sha
