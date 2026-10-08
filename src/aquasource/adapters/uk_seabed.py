"""UK seabed still photographs under the Open Government Licence (JNCC offshore survey archives on data.defra.gov.uk).

Source: the CKAN package ``seabed-videos-from-bassurelle-sandbanks-sci1`` (data.gov.uk harvest, publisher JNCC,
licence id ``uk-ogl``, bbox in the package extras). Its one resource is the S3 zip
``JNCC2013_03BassSandRawBenthicSamplingvideo.zip`` (1.45 GB, 585 entries). Despite the file name, the archive holds
still photographs: 550 JPEG frames in ``still_photographs/<survey>_STN_<n>_A1/`` folders (one folder per station).

The adapter never downloads the archive in full. The zip central directory is read with HTTP Range requests (cached
as metadata/raw/uk_seabed/<archive>_entries.json); each JPEG becomes one candidate; fetch_media reads one Range
request per frame (local header + compressed bytes), inflates it and checks the size. Thumbs.db, schema.ini and
station text files are not media.

Licence: UK Open Government Licence, tier B, read at record level (CKAN ``license_id`` uk-ogl; the version is not
stated on this record). See research/uk_seabed.md.

Geo: the archive has no per-image or per-station coordinates (the station text file lists file names and
timestamps only). Each frame gets the centre of the survey bounding box from the CKAN extras
(sites/uk_seabed.csv): geo_precision region, geo_inferred true, geo_uncertainty_m 9900 (corner distance).
Coordinates are publication-derived; no station coordinate is invented.

Noisy data is kept: station frames may include dark, blurred or non-seabed scenes; none is dropped.

Adapter options (``--opt name=value``): none yet.
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
from pathlib import Path
from typing import Any, Iterable

from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from ..core.sites import load_sites
from .base import Adapter, MediaRef, register
from .seanoe_more import _RangeReader, inflate_member

log = logging.getLogger(__name__)

PACKAGE = "seabed-videos-from-bassurelle-sandbanks-sci1"
ORIGIN = f"https://ckan.publishing.service.gov.uk/dataset/{PACKAGE}"
ARCHIVES = [
    {
        "id": "bassurelle_sci_2013",
        "url": "http://s3-eu-west-1.amazonaws.com/data.defra.gov.uk/Marine/JNCC2013_03BassSandRawBenthicSamplingvideo.zip",
        "site_id": "bassurelle_sandbanks",
        "prefix": "still_photographs/",
    },
]
LICENCE_URL = "http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
ATTRIBUTION = (
    "Contains public sector information licensed under the Open Government Licence v3.0. JNCC, Bassurelle Sandbank "
    f"SCI seabed still photographs 2013 ({ORIGIN})"
)
LOCAL_HEADER = 30
STATION_RE = re.compile(r"_(STN_\d+)_A\d+$")
MEDIA_EXT = (".jpg", ".jpeg")


@register
class UkSeabedAdapter(Adapter):
    key = "uk_seabed"
    name = "UK seabed still photographs, JNCC offshore survey archives (OGL)"
    homepage = ORIGIN
    citation = ATTRIBUTION
    media_types = ("image",)
    host_intervals = {"s3-eu-west-1.amazonaws.com": 1.0, "ckan.publishing.service.gov.uk": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._site_table: dict[str, Any] | None = None
        self._sizes: dict[str, int] = {}

    # ---------------------------------------------------------------- metadata
    def _archive(self, archive_id: str) -> dict[str, Any]:
        return next(a for a in ARCHIVES if a["id"] == archive_id)

    def archive_size(self, url: str) -> int:
        if url not in self._sizes:
            resp = self.http.head(url)
            n = resp.headers.get("Content-Length")
            if not n:
                raise HttpError(url, resp.status_code, "no Content-Length")
            self._sizes[url] = int(n)
        return self._sizes[url]

    def entries(self, archive: dict[str, Any]) -> list[dict[str, Any]]:
        """Central-directory entries of one archive, cached in metadata/raw/uk_seabed/."""
        cache = f"uk_seabed/{archive['id']}_entries.json"
        path = self.ctx.layout.raw / cache
        if path.exists() and not self.options.get("refresh_metadata"):
            return json.loads(path.read_text(encoding="utf-8"))
        zf = zipfile.ZipFile(_RangeReader(self.http, archive["url"], self.archive_size(archive["url"])))
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
        self.ctx.save_raw(cache, json.dumps(out))
        return out

    def _site_map(self) -> dict[str, Any]:
        if self._site_table is None:
            self._site_table = load_sites("uk_seabed")
        return self._site_table

    # --------------------------------------------------------------- interface
    def discover(self) -> Iterable[Candidate]:
        for archive in ARCHIVES:
            for ent in self.entries(archive):
                name = ent["name"]
                if not name.startswith(archive["prefix"]) or not name.lower().endswith(MEDIA_EXT):
                    continue
                parts = name.split("/")
                station_dir = parts[-2] if len(parts) >= 3 else ""
                m = STATION_RE.search(station_dir)
                if not m:
                    self.ctx.fail(name, "discover", "station folder does not match *_STN_<n>_A<k>")
                    continue
                ext = "jpg"
                yield Candidate(
                    source=self.key,
                    item_id=f"{archive['url']}#{name}",
                    media_type="image",
                    media_url=archive["url"],
                    origin_url=ORIGIN,
                    timestamp=None,
                    ext=ext,
                    raw={
                        "archive_id": archive["id"],
                        "member": name,
                        "file_name": os.path.basename(name),
                        "file_size": ent["file_size"],
                        "compress_size": ent["compress_size"],
                        "method": ent["method"],
                        "header_offset": ent["header_offset"],
                        "station_dir": station_dir,
                    },
                    extra={
                        "package": PACKAGE,
                        "archive_url": archive["url"],
                        "station": m.group(1),
                        "site_id": archive["site_id"],
                        "timestamp_in_archive": "station text file (not parsed)",
                        "maybe_not_underwater": False,
                    },
                )

    def resolve_licence(self, cand: Candidate) -> Licence:
        return make_licence("UK Open Government Licence (OGL)", level="record", url=LICENCE_URL, attribution=ATTRIBUTION)

    def resolve_geo(self, cand: Candidate) -> Geo:
        site = self._site_map()[cand.extra["site_id"]]
        return site.geo(
            precision="region",
            geo_source=f"{site.source}; JNCC archive {cand.raw['archive_id']}",
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
        if content[:3] != b"\xff\xd8\xff":
            raise ValueError("member is not a JPEG (no FFD8FF signature)")
        sha = hashlib.sha256(content).hexdigest()
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(content)
        os.replace(part, dest)
        self.http.media_bytes += len(content)
        self.http.media_files += 1
        return len(content), sha
