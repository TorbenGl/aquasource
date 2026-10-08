"""Citizen-labelled deep-sea observatory images on SEANOE (DOI 10.17882/101899, Ifremer / DeepSeaSpy, 2024).

Source: https://www.seanoe.org/data/00907/101899/ , one archive ``data/115473.zip`` (798.7 MB, 3,979 JPEG frames
of two fixed cameras, about 0.78 GB of JPEG). Licence CC BY 4.0, read at record level (SEANOE page and DataCite
rights list). Authors: Lebeaud, A., Tosello, V., Borremans, C., Matabos, M.

The adapter never downloads the archive in full. The zip central directory is read with HTTP Range requests
(cached as metadata/raw/seanoe_more/101899_entries.json), each JPEG becomes one candidate, and fetch_media reads
one Range request per frame (local header + compressed bytes), inflates it when it is deflated, and checks the size.
The CSV annotation tables and the YOLO models in the archive are not media and are not fetched.

Geo: the archive names each frame with its camera (``CAM-TEMPO-MINI-2_<YYYYMMDDHHMMSS>.jpg``, 3,403 frames, the
TEMPO module that the README places at Juan de Fuca; ``MOMAR_<...>.jpg``, 576 frames, the Azores). The record gives
one DataCite geoLocationBox per observatory (sites/seanoe_more.csv). Each frame gets the coordinate of its camera:
geo_precision fixed_site, geo_inferred true, no published uncertainty. The record does not state the coordinate of
each camera in words, so the Juan de Fuca point is the second box (see research/seanoe_more.md).

Noisy data is kept: the frames are citizen-observed camera scenes, some dark or without a labelled animal.
Timestamps come from the file name and are taken as UTC (the README gives no time zone).

Adapter options (``--opt name=value``):
    cameras=CAM-TEMPO-MINI-2,MOMAR   only frames of these camera prefixes (default: all)
    per_day=N                        keep at most N frames per calendar day (default: all)
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import re
import struct
import zipfile
import zlib
from pathlib import Path
from typing import Any, Iterable

from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from ..core.sites import load_sites
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

RECORD_DOI = "101899"
LANDING = "https://www.seanoe.org/data/00907/101899/"
ZIP_URL = "https://www.seanoe.org/data/00907/101899/data/115473.zip"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"
ATTRIBUTION = (
    "Lebeaud, A., Tosello, V., Borremans, C., Matabos, M. (2024), Deep-sea observatories images labeled by citizen "
    "for object detection algorithms, SEANOE, https://doi.org/10.17882/101899, CC BY 4.0"
)
# File-name camera prefix -> site_id in sites/seanoe_more.csv.
CAMERA_SITES = {"CAM-TEMPO-MINI-2": "tempo_juan_de_fuca", "MOMAR": "momar_azores"}
FRAME_RE = re.compile(r"^(?P<camera>[A-Za-z0-9-]+?)_(?P<stamp>\d{14})\.jpg$", re.IGNORECASE)
ARCHIVE_DIR = "dataset_seanoe_101899/images/Images/"
LOCAL_HEADER = 30
ENTRIES_CACHE = f"seanoe_more/{RECORD_DOI}_entries.json"


class _RangeReader(io.RawIOBase):
    """Read-only file object over an HTTP resource, so that zipfile reads only the parts it needs."""

    def __init__(self, http: Any, url: str, size: int):
        self.http, self.url, self.size, self.pos = http, url, size, 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def tell(self) -> int:
        return self.pos

    def read(self, n: int = -1) -> bytes:
        end = self.size if n is None or n < 0 else min(self.pos + n, self.size)
        if self.pos >= end:
            return b""
        data = self.http.get_range(self.url, self.pos, end - 1)
        self.pos += len(data)
        return data


def frame_stamp(name: str) -> tuple[str, str] | None:
    """(camera prefix, ISO timestamp UTC) of a frame name, or None."""
    m = FRAME_RE.match(os.path.basename(name))
    if not m:
        return None
    s = m.group("stamp")
    iso = f"{s[0:4]}-{s[4:6]}-{s[6:8]}T{s[8:10]}:{s[10:12]}:{s[12:14]}Z"
    return m.group("camera"), iso


def inflate_member(raw: bytes, method: int, file_size: int) -> bytes:
    """Bytes of one zip member from its compressed bytes. Only stored (0) and deflate (8) are used by this archive."""
    if method == 0:
        data = raw
    elif method == 8:
        data = zlib.decompressobj(-15).decompress(raw)
    else:
        raise ValueError(f"unsupported zip compression method {method}")
    if len(data) != file_size:
        raise ValueError(f"member size {len(data)} != {file_size}")
    return data


@register
class SeanoeMoreAdapter(Adapter):
    key = "seanoe_more"
    name = "SEANOE citizen-labelled deep-sea observatory images (TEMPO Juan de Fuca, MOMAR Azores)"
    homepage = LANDING
    citation = ATTRIBUTION
    media_types = ("image",)
    host_intervals = {"www.seanoe.org": 1.0, "api.datacite.org": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._site_table: dict[str, Any] | None = None
        self._size: int | None = None

    # ------------------------------------------------------------------ options
    def _cameras(self) -> set[str]:
        return {c.strip() for c in str(self.options.get("cameras") or "").split(",") if c.strip()}

    def _per_day(self) -> int | None:
        try:
            n = int(self.options.get("per_day"))
        except (TypeError, ValueError):
            return None
        return n if n >= 1 else None

    # ---------------------------------------------------------------- metadata
    def archive_size(self) -> int:
        if self._size is None:
            resp = self.http.head(ZIP_URL)
            n = resp.headers.get("Content-Length")
            if not n:
                raise HttpError(ZIP_URL, resp.status_code, "no Content-Length")
            self._size = int(n)
        return self._size

    def entries(self) -> list[dict[str, Any]]:
        """Central-directory entries of the archive, cached in metadata/raw/seanoe_more/."""
        path = self.ctx.layout.raw / ENTRIES_CACHE
        if path.exists() and not self.options.get("refresh_metadata"):
            return json.loads(path.read_text(encoding="utf-8"))
        zf = zipfile.ZipFile(_RangeReader(self.http, ZIP_URL, self.archive_size()))
        out = [
            {
                "name": i.filename,
                "file_size": i.file_size,
                "compress_size": i.compress_size,
                "method": i.compress_type,
                "header_offset": i.header_offset,
            }
            for i in zf.infolist()
        ]
        self.ctx.save_raw(ENTRIES_CACHE, json.dumps(out))
        return out

    def _site_map(self) -> dict[str, Any]:
        if self._site_table is None:
            self._site_table = load_sites("seanoe_more")
        return self._site_table

    # --------------------------------------------------------------- interface
    def discover(self) -> Iterable[Candidate]:
        cams = self._cameras()
        per_day = self._per_day()
        counts: dict[str, int] = {}
        for ent in self.entries():
            name = ent["name"]
            if not name.startswith(ARCHIVE_DIR) or not name.lower().endswith(".jpg"):
                continue
            stamp = frame_stamp(name)
            if stamp is None:
                self.ctx.fail(name, "discover", "frame name does not match CAMERA_<YYYYMMDDHHMMSS>.jpg")
                continue
            camera, ts = stamp
            if camera not in CAMERA_SITES or (cams and camera not in cams):
                continue
            day = ts[:10]
            if per_day and counts.get(day, 0) >= per_day:
                continue
            counts[day] = counts.get(day, 0) + 1
            base = os.path.basename(name)
            yield Candidate(
                source=self.key,
                item_id=f"{ZIP_URL}#{name}",
                media_type="image",
                media_url=ZIP_URL,
                origin_url=f"https://doi.org/10.17882/{RECORD_DOI}",
                timestamp=ts,
                ext="jpg",
                raw={
                    "doi": f"10.17882/{RECORD_DOI}",
                    "landing": LANDING,
                    "member": name,
                    "file_name": base,
                    "file_size": ent["file_size"],
                    "compress_size": ent["compress_size"],
                    "method": ent["method"],
                    "header_offset": ent["header_offset"],
                    "camera": camera,
                },
                extra={
                    "seanoe_doi": f"10.17882/{RECORD_DOI}",
                    "camera_prefix": camera,
                    "site_id": CAMERA_SITES[camera],
                    "timestamp_from_name": True,
                    "timestamp_assumed_utc": True,
                    "annotations": "citizen labels in the archive CSVs, not loaded",
                },
            )

    def resolve_licence(self, cand: Candidate) -> Licence:
        return make_licence("CC-BY-4.0", level="record", url=LICENCE_URL, attribution=ATTRIBUTION)

    def resolve_geo(self, cand: Candidate) -> Geo:
        site = self._site_map()[cand.extra["site_id"]]
        return site.geo(
            precision="fixed_site",
            geo_source=(
                f"{site.source}; camera {cand.extra['camera_prefix']} from the file name; SEANOE {RECORD_DOI}"
            ),
            inferred=True,
        )

    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(
            url=cand.media_url,
            ext="jpg",
            expected_bytes=cand.raw["compress_size"] + LOCAL_HEADER,
            extra={
                "member": cand.raw["member"],
                "header_offset": cand.raw["header_offset"],
                "compress_size": cand.raw["compress_size"],
                "file_size": cand.raw["file_size"],
                "method": cand.raw["method"],
            },
        )

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        """One Range request for the member (local header + data), inflated and written atomically."""
        x = ref.extra
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        # The local header is 30 bytes plus name and extra fields; one request covers both for normal archives.
        head_room = 1024
        start = x["header_offset"]
        end = start + LOCAL_HEADER + head_room + x["compress_size"] - 1
        blob = self.http.get_range(ref.url, start, end, kind="media")
        if blob[:4] != b"PK\x03\x04":
            raise ValueError("no zip local header at the offset")
        n, m = struct.unpack("<HH", blob[26:30])
        if LOCAL_HEADER + n + m > len(blob):
            raise ValueError("local header longer than the fetched bytes")
        local_name = blob[LOCAL_HEADER : LOCAL_HEADER + n].decode("utf-8", "replace")
        if local_name != x["member"]:
            raise ValueError(f"local name {local_name!r} differs from the central directory")
        data_start = LOCAL_HEADER + n + m
        raw = blob[data_start : data_start + x["compress_size"]]
        if len(raw) != x["compress_size"]:
            raise HttpError(ref.url, 206, "short member read")
        content = inflate_member(raw, x["method"], x["file_size"])
        sha = hashlib.sha256(content).hexdigest()
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(content)
        os.replace(part, dest)
        self.http.media_bytes += len(content)
        self.http.media_files += 1
        return len(content), sha
