"""Seatizen Atlas (Ifremer / SeatizenDOI): underwater and aerial session images with camera GPS (EXIF).

Source: Zenodo community ``seatizen-data``. The index deposit https://zenodo.org/records/18211765 ("Seatizen Atlas",
CC BY 4.0, collection level) lists 589 session deposits in ``session_doi.csv``. Every session is its own Zenodo record
with its own licence (``license.id``, read here at record level; the index licence is NOT used for the samples).
Contini et al. (2025) Sci. Data, https://doi.org/10.1038/s41597-024-04267-z. Research note: research/seatizen.md.

Per session record (sessions need METADATA.zip and an image archive, DCIM.zip or PROCESSED_DATA_FRAMES.zip):
    * ``METADATA.zip`` -> ``metadata.csv``: one row per image (EXIF): FileName, GPSLatitude, GPSLongitude, GPSDateTime,
      GPSMapDatum, CreateDate, Make, Model. Only this member is read, with range requests (the archive itself can be
      1.2 GB, it holds thumbnails); the csv is cached under metadata/raw/zip/.
    * ``DCIM.zip`` (scuba / UAV / KITE sessions) or ``PROCESSED_DATA_FRAMES.zip`` (ASV sessions, 1080p frames of a
      downward camera below the surface, PPK-corrected GPS per frame; the metadata.csv of ASV sessions has GPSsde /
      GPSsdn, the horizontal standard deviations in metres, used as geo_uncertainty_m = sqrt(sde^2 + sdn^2)). The JPEGs
      are about 0.3-4.5 MB each, the archives up to 16 GB. Media is NOT downloaded as a whole zip:
      the central directory is read with range requests (cached in metadata/raw/zipindex/) and ``fetch_media`` reads
      one local header and one member (range requests, zlib inflate, CRC32 check).

Licence: tier from the session record licence (``cc-by-4.0`` -> B, ``cc-zero`` -> A, NC / ND -> X, anything else or
access not ``open`` -> U). Records that are not in tier A / B are not yielded (``tiers`` option). Level: record.

Geo: fields GPSLatitude, GPSLongitude of metadata.csv (WGS 84, checked against GPSMapDatum). Precision ``image``,
geo_inferred false. Uncertainty: sqrt(GPSsde^2 + GPSsdn^2) where the csv has them (ASV sessions), else null. Depth: none
(GPSAltitude is not a depth; kept in raw). Rows with empty or invalid coordinates are dropped unless ``geo_only=false`` (then precision ``none``).

Platform (from the session name, third ``_`` field): scuba, uvc, asv, aerial (UAV, KITE, DRONE), otherwise unknown.
Aerial images are NOT dropped (pretraining data is kept as is); they are marked ``extra.maybe_not_underwater=true``
and ``extra.platform="aerial"``. ``platforms`` option restricts the platforms yielded (e.g. ``scuba,uvc``).

Not done (see HANDOFF in research/seatizen.md): sessions without a metadata.csv with GPS, or without an image archive
(about 15 sessions with PROCESSED_DATA only) are skipped and logged; GPS.zip / SENSORS.zip are not read.

Adapter options (``--opt key=value``)
    tiers              licence tiers to yield, default ``A,B``.
    order              ``spread`` (default: seeded shuffle of sessions and images) or ``table`` (session_doi.csv order).
    seed               integer for the shuffle (default 0).
    max_per_session    at most this many images per session (default 0 = all).
    geo_only           skip images without usable coordinates (default true).
    platforms          comma list of platforms to yield (default all: scuba, uvc, asv, aerial, unknown).
    refresh_metadata   core option: re-read the Zenodo records and metadata archives.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import math
import os
import random
import re
import struct
import zipfile
import zlib
from pathlib import Path
from typing import Any, Iterable, Iterator

from ..core.geo import to_float
from ..core.http import HttpError
from ..core.licence import classify, make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

INDEX_ID = "18211765"
INDEX_URL = f"https://zenodo.org/records/{INDEX_ID}"
SESSIONS_URL = f"https://zenodo.org/api/records/{INDEX_ID}/files/session_doi.csv/content"
RECORD_API = "https://zenodo.org/api/records/"
PAPER = (
    "Contini, M. et al. (2025) Seatizen Atlas: a collaborative dataset of underwater and aerial marine imagery. "
    "Scientific Data. https://doi.org/10.1038/s41597-024-04267-z"
)
LICENCE_URLS = {
    "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/legalcode",
    "cc-by-3.0": "https://creativecommons.org/licenses/by/3.0/legalcode",
    "cc-zero": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
    "cc0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/legalcode",
    "cc-by-sa-4.0": "https://creativecommons.org/licenses/by-sa/4.0/legalcode",
}
GEO_SOURCE = (
    "Zenodo session deposit METADATA.zip > metadata.csv, columns GPSLatitude and GPSLongitude "
    "(camera EXIF GPS, WGS 84 per GPSMapDatum; ASV sessions: PPK-corrected per frame)"
)
IMAGE_ARCHIVES = ("DCIM.zip", "PROCESSED_DATA_FRAMES.zip")
RAW_FIELDS = ("FileName", "relative_file_path", "GPSLatitude", "GPSLongitude", "GPSAltitude", "GPSAltitudeRef",
              "GPSDateTime", "SubSecDateTimeOriginal", "GPSMapDatum", "GPSfix", "GPSsde", "GPSsdn", "CreateDate",
              "Make", "Model")
PLATFORM_OF = {"SCUBA": "scuba", "UVC": "uvc", "ASV": "asv", "UAV": "aerial", "KITE": "aerial", "DRONE": "aerial"}
AERIAL = {"aerial"}
DEFAULT_TIERS = ("A", "B")
ORDERS = ("spread", "table")
MAGIC_JPEG = b"\xff\xd8\xff"


# ----------------------------------------------------------------------------------------------- pure helpers
def licence_tier(spdx: str, access: str | None) -> str:
    """Tier of a Zenodo licence id (``cc-by-4.0``, ``cc-zero``, ...). Never upgraded; not open access -> U."""
    if (access or "").lower() != "open" or not spdx:
        return "U"
    return classify(spdx)


def platform_of(session_name: str) -> str:
    """``20150611_REU-St-Gilles_scuba`` -> scuba; ``20240405_REU-HERMITAGE_UAV-01_01`` -> aerial."""
    parts = session_name.split("_")
    token = (parts[2] if len(parts) > 2 else parts[-1]).split("-")[0].upper()
    return PLATFORM_OF.get(token, "unknown")


def valid_coordinate(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return False
    return not (lat == 0 and lon == 0)


def exif_time_iso(value: str | None) -> str | None:
    """``2015:06:11 04:26:11Z`` (EXIF GPSDateTime, UTC) -> ``2015-06-11T04:26:11Z``."""
    m = re.match(r"^(\d{4}):(\d{2}):(\d{2}) (\d{2}):(\d{2}):(\d{2})Z?$", (value or "").strip())
    if not m:
        return None
    y, mo, d, h, mi, s = m.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}Z"


def _sigma_m(sde: object, sdn: object) -> float | None:
    """Horizontal 1-sigma from the east / north standard deviations (metres) of the PPK solution, if present."""
    e, n = to_float(sde), to_float(sdn)
    if e is None or n is None or e < 0 or n < 0:
        return None
    return round(math.hypot(e, n), 4)


def find_member(fname: str, entries: dict[str, Any]) -> dict[str, Any] | None:
    """Zip entry of an EXIF FileName. Exact name first; else the unique entry whose basename is the FileName's tail
    after the session prefix (GoPro sessions: ``100GOPRO/G0032181.JPG`` for ``<session>_G0032181.JPG``)."""
    if fname in entries:
        return entries[fname]
    tail = fname.rsplit("_", 1)[-1]
    hits = [e for n, e in entries.items() if n.rsplit("/", 1)[-1] in (fname, tail)]
    return hits[0] if len(hits) == 1 else None


def session_doi_id(doi: str) -> str | None:
    m = re.search(r"zenodo\.(\d+)", doi or "")
    return m.group(1) if m else None


def _flag(value: object, default: bool) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return value.strip().lower() not in ("0", "false", "no", "off")
    return bool(value)


def _list(value: object, default: tuple[str, ...]) -> tuple[str, ...]:
    if value in (None, ""):
        return default
    if isinstance(value, str):
        return tuple(x for x in re.split(r"[,\s\[\]\"']+", value.upper()) if x)
    return tuple(str(x).strip().upper() for x in value)


class _RangeReader(io.RawIOBase):
    """Read-only file object over an HTTP URL, using Range requests through the shared Http client."""

    def __init__(self, http: Any, url: str, size: int):
        self.http, self.url, self.size, self.pos = http, url, size, 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def tell(self) -> int:
        return self.pos

    def readinto(self, buf) -> int:  # type: ignore[override]
        n = min(len(buf), self.size - self.pos)
        if n <= 0:
            return 0
        data = self.http.get_range(self.url, self.pos, self.pos + n - 1, kind="metadata")
        buf[: len(data)] = data
        self.pos += len(data)
        return len(data)


# ------------------------------------------------------------------------------------------------- adapter
@register
class SeatizenAdapter(Adapter):
    key = "seatizen"
    name = "Seatizen Atlas: session images with camera GPS (underwater and aerial), per-session licence"
    homepage = INDEX_URL
    citation = PAPER
    media_types = ("image",)
    env_vars: tuple[str, ...] = ()
    manual_steps = "None (anonymous Zenodo API and file downloads)."
    host_intervals = {"zenodo.org": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self.skipped: dict[str, int] = {}
        self._tiers = _list(self.options.get("tiers"), DEFAULT_TIERS)

    # ---------------------------------------------------------------- options
    def check_ready(self) -> list[str]:
        problems = super().check_ready()
        order = str(self.options.get("order", "spread")).lower()
        if order not in ORDERS:
            problems.append(f"order must be one of {ORDERS}")
        return problems

    def _int(self, name: str, default: int) -> int:
        try:
            return int(self.options.get(name, default))
        except (TypeError, ValueError):
            raise ValueError(f"option {name} must be an integer") from None

    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    # ---------------------------------------------------------------- metadata
    def _sessions(self) -> list[dict[str, str]]:
        text = self.ctx.cached_text(SESSIONS_URL, "session_doi.csv")
        out = []
        for row in csv.DictReader(io.StringIO(text)):
            rid = session_doi_id(row.get("session_doi", ""))
            if rid and row.get("session_name"):
                out.append({"session_name": row["session_name"], "record_id": rid, "place": row.get("place", ""),
                            "date": row.get("date", "")})
        return out

    def _record(self, rid: str) -> dict[str, Any]:
        return self.ctx.cached_json(f"{RECORD_API}{rid}", f"records/{rid}.json", refresh=bool(self.options.get("refresh_metadata")))

    def _metadata_rows(self, rid: str, url: str, size: int) -> list[dict[str, str]]:
        """metadata.csv of METADATA.zip, read by range requests (some METADATA.zip files are 1.2 GB)."""
        name = f"zip/{rid}_metadata.csv"
        path = self.ctx.layout.raw / name
        if path.exists() and not self.options.get("refresh_metadata"):
            text = path.read_text(encoding="utf-8")
        else:
            entries = self._zip_index(rid, "METADATA", url, size)
            entry = next((e for n, e in entries.items() if n.lower().endswith("metadata.csv")), None)
            if entry is None:
                return []
            text = self._read_member(url, entry, kind="metadata").decode("utf-8", errors="replace")
            self.ctx.save_raw(name, text)
        return list(csv.DictReader(io.StringIO(text)))

    # ---------------------------------------------------------------- discover
    def discover(self) -> Iterable[Candidate]:
        order = str(self.options.get("order", "spread")).lower()
        if order not in ORDERS:
            raise ValueError(f"order must be one of {ORDERS}")
        seed = self._int("seed", 0)
        cap = self._int("max_per_session", 0)
        geo_only = _flag(self.options.get("geo_only"), True)
        platforms = _list(self.options.get("platforms"), ())
        rng = random.Random(seed)
        sessions = self._sessions()
        if order == "spread":
            rng.shuffle(sessions)
        for sess in sessions:
            rid = sess["record_id"]
            try:
                rec = self._record(rid)
            except HttpError as exc:
                self.ctx.fail(rid, "discover", f"session record: {exc}")
                continue
            rid = str(rec.get("id", rid))
            meta = rec.get("metadata") or {}
            files = {f["key"]: f for f in rec.get("files", [])}
            image_key = next((k for k in IMAGE_ARCHIVES if k in files), None)
            if image_key is None or "METADATA.zip" not in files:
                self._skip("session without DCIM.zip / PROCESSED_DATA_FRAMES.zip + METADATA.zip")
                self.ctx.fail(rid, "discover", "no image archive + METADATA.zip", session=sess["session_name"])
                continue
            platform = platform_of(sess["session_name"])
            if platforms and platform not in platforms:
                self._skip(f"platform {platform} not selected")
                continue
            licence_id = str((meta.get("license") or {}).get("id") or "")
            access = meta.get("access_right")
            if licence_tier(licence_id, access) not in self._tiers:
                self._skip(f"licence {licence_id or 'none'} / access {access} not in tiers")
                continue
            meta_file = files["METADATA.zip"]
            try:
                rows = self._metadata_rows(rid, meta_file["links"]["self"], int(meta_file.get("size") or 0))
            except (HttpError, zipfile.BadZipFile) as exc:
                self.ctx.fail(rid, "discover", f"METADATA.zip: {exc}")
                continue
            if order == "spread":
                rng.shuffle(rows)
            creators = "; ".join(c.get("name", "") for c in meta.get("creators", []) if c.get("name"))
            kept = 0
            for row in rows:
                if cap and kept >= cap:
                    break
                lat, lon = to_float(row.get("GPSLatitude")), to_float(row.get("GPSLongitude"))
                if geo_only and not valid_coordinate(lat, lon):
                    self._skip("no valid GPS in metadata.csv")
                    continue
                kept += 1
                yield self._candidate(sess, rid, rec, files[image_key], row, platform, licence_id, creators)

    def _candidate(self, sess, rid, rec, image_file, row, platform, licence_id, creators) -> Candidate:
        fname = row.get("FileName") or os.path.basename(row.get("relative_file_path", ""))
        raw = {k: row.get(k) for k in RAW_FIELDS}
        aerial = platform in AERIAL
        extra = {
            "session": sess["session_name"],
            "session_doi": f"https://doi.org/10.5281/zenodo.{rid}",
            "record_id": rid,
            "place": sess["place"],
            "date": sess["date"],
            "platform": platform,
            "licence_id": licence_id,
            "access": (rec.get("metadata") or {}).get("access_right"),
            "creators": creators,
            "member": fname,
            "zip_key": image_file["key"],
            "zip_bytes": int(image_file.get("size") or 0),
            "zip_url": image_file["links"]["self"],
        }
        if aerial:
            extra["maybe_not_underwater"] = True
        return Candidate(
            source=self.key,
            item_id=f"{rid}/{fname}",
            media_type="image",
            media_url=image_file["links"]["self"],
            origin_url=f"https://zenodo.org/records/{rid}",
            timestamp=exif_time_iso(row.get("GPSDateTime")),
            ext="jpg",
            raw=raw,
            extra=extra,
        )

    # ---------------------------------------------------------------- licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        spdx = str(cand.extra.get("licence_id") or "")
        tier = licence_tier(spdx, cand.extra.get("access"))
        url = LICENCE_URLS.get(spdx.lower()) or f"https://zenodo.org/records/{cand.extra['record_id']}"
        if tier not in ("A", "B"):
            return make_licence(spdx or "not stated", level="record", url=url, attribution=PAPER, tier=tier)
        attribution = (
            f"{cand.extra.get('creators') or 'Seatizen Atlas contributors'}. Seatizen Atlas session "
            f"{cand.extra['session']}, Zenodo {cand.extra['session_doi']}, image {cand.extra['member']}. "
            f"{PAPER}. Licence {spdx} ({url})."
        )
        return make_licence(spdx, level="record", url=url, attribution=attribution, tier=tier)

    # ---------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        raw = cand.raw
        lat, lon = to_float(raw.get("GPSLatitude")), to_float(raw.get("GPSLongitude"))
        if not valid_coordinate(lat, lon):
            return Geo.none(geo_source=GEO_SOURCE + " (empty or invalid)")
        datum = str(raw.get("GPSMapDatum") or "").strip().upper()
        if datum and datum.replace(" ", "") not in ("WGS-84", "WGS84"):
            return Geo.none(geo_source=f"{GEO_SOURCE}; GPSMapDatum {datum!r} is not WGS 84")
        return Geo(lat, lon, None, "image", GEO_SOURCE, False, _sigma_m(raw.get("GPSsde"), raw.get("GPSsdn")))

    # ---------------------------------------------------------------- media
    def _zip_index(self, rid: str, kind: str, url: str, size: int) -> dict[str, dict[str, Any]]:
        """Central directory of a zip on Zenodo (range requests), cached in metadata/raw/zipindex/."""
        name = f"zipindex/{rid}_{kind}.json"
        path = self.ctx.layout.raw / name
        if path.exists() and not self.options.get("refresh_metadata"):
            return {e["name"]: e for e in json.loads(path.read_text(encoding="utf-8"))}
        zf = zipfile.ZipFile(_RangeReader(self.http, url, size))
        entries = [
            {"name": zi.filename, "header_offset": zi.header_offset, "compress_type": zi.compress_type,
             "compress_size": zi.compress_size, "file_size": zi.file_size, "crc": zi.CRC}
            for zi in zf.infolist() if not zi.is_dir()
        ]
        self.ctx.save_raw(name, json.dumps(entries))
        return {e["name"]: e for e in entries}

    def _read_member(self, url: str, e: dict[str, Any], *, kind: str = "media") -> bytes:
        """One zip member by range requests: local header, then the compressed bytes; size and CRC32 checked."""
        head = self.http.get_range(url, e["header_offset"], e["header_offset"] + 29, kind=kind)
        if head[:4] != b"PK\x03\x04":
            raise HttpError(url, None, "no local zip header at the indexed offset")
        name_len, extra_len = struct.unpack("<HH", head[26:30])
        start = e["header_offset"] + 30 + name_len + extra_len
        packed = self.http.get_range(url, start, start + e["compress_size"] - 1, kind=kind) if e["compress_size"] else b""
        if e["compress_type"] == 0:
            data = packed
        elif e["compress_type"] == 8:
            inflater = zlib.decompressobj(-15)
            data = inflater.decompress(packed) + inflater.flush()
        else:
            raise HttpError(url, None, f"unsupported zip compression {e['compress_type']}")
        if len(data) != e["file_size"] or (zlib.crc32(data) & 0xFFFFFFFF) != e["crc"]:
            raise HttpError(url, None, f"CRC/size mismatch for {e['name']}")
        return data

    def resolve_media(self, cand: Candidate) -> MediaRef:
        rid, url, size = cand.extra["record_id"], cand.extra["zip_url"], cand.extra["zip_bytes"]
        kind = cand.extra["zip_key"].removesuffix(".zip")
        entries = self._zip_index(rid, kind, url, size)
        entry = find_member(cand.extra["member"], entries)
        if entry is None:
            raise HttpError(cand.media_url, None, f"member {cand.extra['member']} not (uniquely) in {cand.extra['zip_key']} of record {rid}")
        return MediaRef(url=cand.media_url, ext="jpg", expected_bytes=entry["file_size"], extra={"entry": entry})

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        data = self._read_member(ref.url, ref.extra["entry"], kind="media")
        if not data.startswith(MAGIC_JPEG):
            raise HttpError(ref.url, None, f"{ref.extra['entry']['name']} is not a JPEG (magic number)")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, dest)
        return len(data), hashlib.sha256(data).hexdigest()

    # ---------------------------------------------------------------- estimate
    def estimate(self) -> dict[str, Any]:
        return {"sessions_listed": len(self._sessions()), "note": "images are listed per session from METADATA.zip"}
