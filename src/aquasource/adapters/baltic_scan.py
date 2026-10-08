"""SE Baltic reef imagery with ROV and SCUBA video (Mendeley Data 10.17632/wsd42v8mk5.1, 2022, Klaipeda University).

Source: https://data.mendeley.com/datasets/wsd42v8mk5/1 . Licence CC BY 4.0 (Mendeley ``data_licence`` field of the
public API record, read at record level). Authors: Medelyte, S. et al., Klaipedos universitetas.

The record is one archive (about 3.4 GB) with a Raw data folder: 7 AVI videos (DE01_1, DE01_2 from the ROV; SM02_1,
SM02_2, SM07_1, SM07_2, SM08_1 from SCUBA transects, 254 to 493 MB each, deflated) and 8 JPEG 2D video mosaics
(one per transect part, 0.19 to 7.9 MB). The Frames and Mosaics folders are RAR files with annotation masks and
are not read by this adapter.

The adapter never downloads the archive in full. The public API answers with a redirect to a short-lived signed
S3 URL; the central directory (about 3 KB) is read with two Range requests and cached in metadata/raw/. fetch_media
resolves a fresh signed URL, reads the local header, then streams the member bytes (inflated when deflated) to disk
with a size and sha256 check.

Geo: the record gives station coordinates in its description (WGS84, "Y, X"), one per file prefix: DE01 (ROV),
SM02, SM07, SM08 (coastal transects). Each file gets the coordinate of its station: geo_precision station,
geo_inferred true (the publication gives one point per station, not per frame). No depth and no uncertainty are
published. No timestamps are published.

Noisy data is kept: the coastal transects are SCUBA GoPro footage with changing visibility.

Adapter options (``--opt name=value``):
    kinds=image,video     only mosaics (image) and/or videos (video) (default: both)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import struct
import zlib
from pathlib import Path
from typing import Any, Iterable

from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from ..core.sites import load_sites
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

RECORD_ID = "wsd42v8mk5"
VERSION = 1
DOI = "10.17632/wsd42v8mk5.1"
LANDING = "https://data.mendeley.com/datasets/wsd42v8mk5/1"
ZIP_API = "https://data.mendeley.com/public-api/zip/wsd42v8mk5/download/1"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"
ATTRIBUTION = (
    "Medelyte, S., Siaulys, A., et al. (2022), A fully-annotated imagery dataset of sublittoral benthic species in "
    "South Eastern Baltic Sea reefs, Mendeley Data, https://doi.org/10.17632/wsd42v8mk5.1, CC BY 4.0"
)
RAW_DIR = (
    "A fully-annotated imagery dataset of sublittoral benthic species in South Eastern Baltic Sea reefs/Raw data/"
)
# File-name prefix -> site_id in sites/baltic_scan.csv (coordinates from the record description).
STATION_SITES = {
    "DE01": "de01_rov",
    "SM02": "sm02_coastal",
    "SM07": "sm07_coastal",
    "SM08": "sm08_coastal",
}
MEDIA_EXT = {".jpg": "image", ".avi": "video"}
LOCAL_HEADER = 30
LOCAL_ROOM = 2048  # room for the local file name and extra field
CHUNK = 1 << 20
ENTRIES_CACHE = f"baltic_scan/{RECORD_ID}_entries.json"


def parse_central_directory(tail: bytes, cd_bytes_for: Any) -> list[dict[str, Any]]:
    """Central directory entries from the last bytes of a zip. ``cd_bytes_for(start, end)`` reads a byte range."""
    i = tail.rfind(b"PK\x05\x06")
    if i < 0:
        raise ValueError("no end-of-central-directory record in the tail of the archive")
    _, n_entries, cd_size, cd_off = struct.unpack("<HHII", tail[i + 8 : i + 20])
    if cd_off == 0xFFFFFFFF or cd_size == 0xFFFFFFFF:
        raise ValueError("zip64 archives are not supported here")
    cd = cd_bytes_for(cd_off, cd_off + cd_size - 1)
    out: list[dict[str, Any]] = []
    p = 0
    while p < len(cd) and len(out) < n_entries:
        if cd[p : p + 4] != b"PK\x01\x02":
            raise ValueError(f"bad central directory entry at {p}")
        method, = struct.unpack("<H", cd[p + 10 : p + 12])
        csz, usz = struct.unpack("<II", cd[p + 20 : p + 28])
        nl, el, cl = struct.unpack("<HHH", cd[p + 28 : p + 34])
        hoff, = struct.unpack("<I", cd[p + 42 : p + 46])
        name = cd[p + 46 : p + 46 + nl].decode("utf-8", "replace")
        out.append({"name": name, "file_size": usz, "compress_size": csz, "method": method, "header_offset": hoff})
        p += 46 + nl + el + cl
    if len(out) != n_entries:
        raise ValueError(f"read {len(out)} of {n_entries} central directory entries")
    return out


@register
class BalticScanAdapter(Adapter):
    key = "baltic_scan"
    name = "SE Baltic reef ROV and SCUBA video with 2D mosaics (Mendeley wsd42v8mk5)"
    homepage = LANDING
    citation = ATTRIBUTION
    media_types = ("image", "video")
    host_intervals = {"data.mendeley.com": 1.0, "prod-dcd-datasets-cache-zipfiles.s3.eu-west-1.amazonaws.com": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._site_table: dict[str, Any] | None = None

    # ------------------------------------------------------------------ options
    def _kinds(self) -> set[str]:
        raw = str(self.options.get("kinds") or "")
        return {k.strip() for k in raw.split(",") if k.strip()} or {"image", "video"}

    # ---------------------------------------------------------------- metadata
    def signed_url(self) -> tuple[str, int]:
        """Resolve the public API redirect to the signed S3 URL and its total size (Content-Range)."""
        resp = self.http.request("GET", ZIP_API, allow_redirects=False, stream=True)
        try:
            if resp.status_code not in (301, 302, 303, 307, 308) or not resp.headers.get("Location"):
                raise HttpError(ZIP_API, resp.status_code, "expected a redirect to the archive")
            loc = resp.headers["Location"]
        finally:
            resp.close()
        probe = self.http.request("GET", loc, kind="metadata", headers={"Range": "bytes=0-0"}, stream=True)
        try:
            cr = probe.headers.get("Content-Range", "")
        finally:
            probe.close()
        if "/" not in cr:
            raise HttpError(loc, probe.status_code, "no Content-Range for the archive size")
        return loc, int(cr.rsplit("/", 1)[1])

    def entries(self) -> list[dict[str, Any]]:
        """Central-directory entries of the archive, cached in metadata/raw/baltic_scan/."""
        path = self.ctx.layout.raw / ENTRIES_CACHE
        if path.exists() and not self.options.get("refresh_metadata"):
            return json.loads(path.read_text(encoding="utf-8"))
        url, size = self.signed_url()
        tail_len = min(65536, size)
        tail = self.http.get_range(url, size - tail_len, size - 1)
        out = parse_central_directory(
            tail, lambda a, b: self.http.get_range(url, a, b)
        )
        self.ctx.save_raw(ENTRIES_CACHE, json.dumps(out))
        return out

    def _site_map(self) -> dict[str, Any]:
        if self._site_table is None:
            self._site_table = load_sites("baltic_scan")
        return self._site_table

    # --------------------------------------------------------------- interface
    def discover(self) -> Iterable[Candidate]:
        kinds = self._kinds()
        for ent in self.entries():
            name = ent["name"]
            if not name.startswith(RAW_DIR):
                continue
            base = name[len(RAW_DIR) :]
            if "/" in base:
                continue
            stem, ext = os.path.splitext(base)
            ext = ext.lower()
            media_type = MEDIA_EXT.get(ext)
            if media_type is None or media_type not in kinds:
                continue
            prefix = stem.split("_")[0].upper()
            site_id = STATION_SITES.get(prefix)
            if site_id is None:
                self.ctx.fail(name, "discover", f"no station coordinates for prefix {prefix}")
                continue
            yield Candidate(
                source=self.key,
                item_id=f"{ZIP_API}#{name}",
                media_type=media_type,
                media_url=ZIP_API,
                origin_url=LANDING,
                timestamp=None,
                ext=ext.lstrip("."),
                raw={
                    "doi": DOI,
                    "landing": LANDING,
                    "member": name,
                    "file_name": base,
                    "file_size": ent["file_size"],
                    "compress_size": ent["compress_size"],
                    "method": ent["method"],
                    "header_offset": ent["header_offset"],
                    "station": prefix,
                },
                extra={
                    "doi": DOI,
                    "station": prefix,
                    "site_id": site_id,
                    "kind": "2D video mosaic" if media_type == "image" else "raw video",
                    "timestamp_available": False,
                },
            )

    def resolve_licence(self, cand: Candidate) -> Licence:
        return make_licence("CC-BY-4.0", level="record", url=LICENCE_URL, attribution=ATTRIBUTION)

    def resolve_geo(self, cand: Candidate) -> Geo:
        site = self._site_map()[cand.extra["site_id"]]
        return site.geo(
            precision="station",
            geo_source=f"{site.source}; station from file-name prefix {cand.extra['station']}",
            inferred=True,
        )

    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(
            url=cand.media_url,
            ext=cand.ext,
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
        """Stream one archive member through a fresh signed URL (Range request, inflated, checked)."""
        x = ref.extra
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        url, _ = self.signed_url()
        start = x["header_offset"]
        blob = self.http.get_range(url, start, start + LOCAL_HEADER + LOCAL_ROOM - 1, kind="media")
        if blob[:4] != b"PK\x03\x04":
            raise ValueError("no zip local header at the offset")
        n, m = struct.unpack("<HH", blob[26:30])
        local_name = blob[LOCAL_HEADER : LOCAL_HEADER + n].decode("utf-8", "replace")
        if local_name != x["member"]:
            raise ValueError(f"local name {local_name!r} differs from the central directory")
        data_start = start + LOCAL_HEADER + n + m
        end = data_start + x["compress_size"] - 1
        resp = self.http.request(
            "GET", url, kind="media", headers={"Range": f"bytes={data_start}-{end}"}, stream=True
        )
        if resp.status_code != 206:
            resp.close()
            raise HttpError(url, resp.status_code, "member range not 206")
        method = x["method"]
        if method not in (0, 8):
            resp.close()
            raise ValueError(f"unsupported zip compression method {method}")
        dec = zlib.decompressobj(-15) if method == 8 else None
        sha = hashlib.sha256()
        total = 0
        part = dest.with_name(dest.name + ".part")
        try:
            with open(part, "wb") as fh:
                for chunk in resp.iter_content(CHUNK):
                    data = dec.decompress(chunk) if dec else chunk
                    if data:
                        fh.write(data)
                        sha.update(data)
                        total += len(data)
                if dec:
                    tail = dec.flush()
                    fh.write(tail)
                    sha.update(tail)
                    total += len(tail)
        finally:
            resp.close()
        if total != x["file_size"]:
            part.unlink(missing_ok=True)
            raise ValueError(f"member size {total} != {x['file_size']}")
        os.replace(part, dest)
        self.http.media_bytes += total
        self.http.media_files += 1
        return total, sha.hexdigest()
