"""SMOOVE video, EMSO-Azores Lucky Strike TEMPO module (Ifremer, 2013 to 2025), 10-minute 1080p videos.

Source: SEANOE, one dataset per deployment period (DOIs in research/emso_azores.md). Each dataset holds one or two
plain ``.tar`` archives (tens of GB). Licence CC BY 4.0, read at record level (landing page JSON-LD and icon).

The adapter never downloads the tars in full. For each tar it reads the ustar member headers with HTTP Range requests
(512-byte blocks, cached as metadata/raw/emso_azores/<record>_<n>.members.json), keeps the video members and fetches
each video with one Range request for its byte span.

Geo: the camera sits on the TEMPO module at a fixed position. The publication gives Latitude 37 deg 17.334 N,
Longitude 32 deg 16.534 W, depth 1695 m (sites/emso_azores.csv). Applied to every video, geo_precision fixed_site,
inferred. No uncertainty is published.

Noisy data is kept: the videos show the mussel assemblage and the camera scene, but some frames may be dark, blurred or
show the module, not fauna (extra.maybe_not_underwater is set to true for those with a dark-frame hint only).

Adapter options (``--opt name=value``):
    from=YYYY-MM-DD      first day to keep (UTC day of the start time parsed from the file name)
    to=YYYY-MM-DD        last day to keep (inclusive)
    per_day=N            keep at most N videos per calendar day (default: all)
    years=2013,2024      only these deployment periods (the first year of the period, e.g. 2023 = 2023-2024)
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any, Iterable

from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from ..core.sites import load_sites
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

SITE_ID = "emso_azores"
SEANOE = "https://www.seanoe.org/data/"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"
VIDEO_EXT = (".mp4", ".avi", ".mov", ".mkv")  # 2023-24 tar holds .mkv (about 1.2 GB each, 10 min)
BLOCK = 512
# Each entry: first year of the period, DOI id, landing path, tar paths (relative to SEANOE host).
RECORDS: tuple[tuple[int, str, str, tuple[str, ...]], ...] = (
    (2013, "48592", "00375/48592", ("data/48926.tar",)),
    (2015, "48594", "00375/48594", ("data/48928.tar",)),
    (2016, "51551", "00404/51551", ("data/52158.tar",)),
    (2017, "83937", "00727/83937", ("data/88867.tar", "data/88868.tar")),
    (2018, "83946", "00727/83946", ("data/88871.tar", "data/88872.tar")),
    (2019, "83947", "00727/83947", ("data/88873.tar", "data/88874.tar")),
    (2020, "83948", "00727/83948", ("data/88875.tar", "data/88876.tar")),
    (2021, "101828", "00906/101828", ("data/112943.tar", "data/112944.tar")),
    (2022, "101834", "00906/101834", ("data/112941.tar", "data/112942.tar")),
    (2023, "101838", "00906/101838", ("data/112940.tar",)),
)
# Start time in the member name, e.g. smoove-24-08-17_00-06-37-46.mp4 -> 2024-08-17T00:06:37Z (assumed UTC).
NAME_RE = re.compile(r"(\d{2})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})")


def parse_octal(raw: bytes) -> int:
    s = raw.split(b"\0")[0].strip() or b"0"
    return int(s, 8)


def parse_members(read_block: Any, total_size: int) -> list[dict[str, Any]]:
    """Walk the tar's headers. ``read_block(offset)`` returns 512 bytes at offset. Returns name, offset, size."""
    out: list[dict[str, Any]] = []
    pos = 0
    long_name: str | None = None
    while pos + BLOCK <= total_size:
        hdr = read_block(pos)
        if hdr == b"\0" * BLOCK:
            break
        size = parse_octal(hdr[124:136])
        typ = hdr[156:157]
        name = hdr[0:100].split(b"\0")[0].decode("utf-8", "replace")
        prefix = hdr[345:500].split(b"\0")[0].decode("utf-8", "replace")
        if prefix and b"ustar" in hdr[257:263]:
            name = f"{prefix}/{name}"
        data_pos = pos + BLOCK
        if typ == b"L":  # GNU long name: the data block is the real name of the next member
            long_name = read_block_span(read_block, data_pos, size).split(b"\0")[0].decode("utf-8", "replace")
        elif typ in (b"0", b"\0", b""):
            out.append({"name": long_name or name, "offset": data_pos, "size": size})
            long_name = None
        pos = data_pos + ((size + BLOCK - 1) // BLOCK) * BLOCK
    return out


def read_block_span(read_block: Any, offset: int, size: int) -> bytes:
    data = b""
    for off in range(offset, offset + size, BLOCK):
        data += read_block(off)
    return data[:size]


def _day_of(name: str) -> str | None:
    m = NAME_RE.search(name)
    if not m:
        return None
    yy, mo, dd, hh, mi, ss = (int(x) for x in m.groups())
    return f"{2000 + yy:04d}-{mo:02d}-{dd:02d}T{hh:02d}:{mi:02d}:{ss:02d}Z"


@register
class EmsoAzoresAdapter(Adapter):
    key = "emso_azores"
    name = "SMOOVE video, EMSO-Azores Lucky Strike TEMPO module (2013 to 2025)"
    homepage = "https://www.seanoe.org/data/00906/101838/"
    citation = (
        "Sarrazin, J. et al. (2024), SMOOVE, video data from EMSO-Azores observatory, 2023-2024, SEANOE, "
        "https://doi.org/10.17882/101838 (CC BY 4.0). Cite the record of each period."
    )
    media_types = ("video",)
    host_intervals = {"www.seanoe.org": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._site = None

    # ------------------------------------------------------------------ options
    def _day(self, name: str) -> str | None:
        v = self.options.get(name)
        return str(v).strip()[:10] if v not in (None, "") else None

    def _per_day(self) -> int | None:
        try:
            n = int(self.options.get("per_day"))
        except (TypeError, ValueError):
            return None
        return n if n >= 1 else None

    # ---------------------------------------------------------------- metadata
    def members(self, year: int, doi: str, rel_path: str, tar_rel: str, idx: int) -> list[dict[str, Any]]:
        """Video members of one tar, cached in metadata/raw/emso_azores/."""
        cache = f"emso_azores/{doi}_{idx}.members.json"
        path = self.ctx.layout.raw / cache
        if path.exists() and not self.options.get("refresh_metadata"):
            import json

            return json.loads(path.read_text(encoding="utf-8"))
        url = f"{SEANOE}{rel_path}/{tar_rel}"
        size = self._tar_size(url)
        blocks: dict[int, bytes] = {}

        def read_block(off: int) -> bytes:
            if off not in blocks:
                blocks[off] = self.http.get_range(url, off, min(off + BLOCK, size) - 1)
            return blocks[off]

        members = [m for m in parse_members(read_block, size) if m["name"].lower().endswith(VIDEO_EXT)]
        import json

        self.ctx.save_raw(cache, json.dumps(members, indent=1))
        return members

    def _tar_size(self, url: str) -> int:
        resp = self.http.head(url)
        n = resp.headers.get("Content-Length")
        if not n:
            raise HttpError(url, resp.status_code, "no Content-Length")
        return int(n)

    # --------------------------------------------------------------- interface
    def discover(self) -> Iterable[Candidate]:
        lo, hi, per_day = self._day("from"), self._day("to"), self._per_day()
        years = {int(y) for y in str(self.options.get("years") or "").split(",") if y.strip()}
        counts: dict[str, int] = {}
        for year, doi, rel_path, tars in RECORDS:
            if years and year not in years:
                continue
            for idx, tar_rel in enumerate(tars):
                url = f"{SEANOE}{rel_path}/{tar_rel}"
                try:
                    members = self.members(year, doi, rel_path, tar_rel, idx)
                except (HttpError, ValueError, OSError) as exc:
                    self.ctx.fail(url, "discover", f"tar headers not readable: {exc}")
                    continue
                for m in members:
                    ts = _day_of(m["name"])
                    day = ts[:10] if ts else None
                    if (lo and (day is None or day < lo)) or (hi and (day is None or day > hi)):
                        continue
                    if per_day and day and counts.get(day, 0) >= per_day:
                        continue
                    if day:
                        counts[day] = counts.get(day, 0) + 1
                    ext = m["name"].rsplit(".", 1)[-1].lower()
                    yield Candidate(
                        source=self.key,
                        item_id=f"{url}#{m['name']}",
                        media_type="video",
                        media_url=url,
                        origin_url=f"https://doi.org/10.17882/{doi}",
                        timestamp=ts,
                        ext=ext,
                        raw={
                            "doi": f"10.17882/{doi}",
                            "landing": f"https://www.seanoe.org/data/{rel_path}/",
                            "tar_url": url,
                            "member": m["name"],
                            "offset": m["offset"],
                            "size": m["size"],
                            "period_year": year,
                        },
                        extra={
                            "seanoe_doi": f"10.17882/{doi}",
                            "tar": tar_rel,
                            "tar_member": m["name"],
                            "period_start_year": year,
                            "timestamp_from_name": bool(ts),
                        },
                    )

    def resolve_licence(self, cand: Candidate) -> Licence:
        return make_licence(
            "CC-BY-4.0",
            level="record",
            url=cand.raw["landing"],
            attribution=(
                f"SMOOVE, video data from EMSO-Azores observatory ({cand.raw['period_year']}-"
                f"{cand.raw['period_year'] + 1}), Sarrazin, J. et al., https://doi.org/{cand.raw['doi']}, CC BY 4.0"
            ),
        )

    def resolve_geo(self, cand: Candidate) -> Geo:
        if self._site is None:
            self._site = load_sites(SITE_ID)[SITE_ID]
        return self._site.geo(
            precision="fixed_site",
            geo_source=(
                f"{self._site.source}; applied to every video (tar member names carry no coordinate); "
                f"SEANOE {cand.raw['doi']}"
            ),
            inferred=True,
        )

    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(
            url=cand.media_url,
            ext=cand.ext or "mp4",
            expected_bytes=cand.raw["size"],
            extra={"offset": cand.raw["offset"], "size": cand.raw["size"]},
        )

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        """One Range request for the member's byte span, streamed to ``dest`` (atomic, sha256 returned)."""
        start = ref.extra["offset"]
        end = start + ref.extra["size"] - 1
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        have = part.stat().st_size if part.exists() else 0
        if have >= ref.extra["size"]:
            part.unlink()
            have = 0
        resp = self.http.request(
            "GET", ref.url, kind="media", headers={"Range": f"bytes={start + have}-{end}"}, stream=True
        )
        if resp.status_code != 206:
            resp.close()
            raise HttpError(ref.url, resp.status_code, "range request did not return 206")
        h = hashlib.sha256()
        if have:  # resume: hash what is already on disk, then append the rest
            with open(part, "rb") as old:
                for block in iter(lambda: old.read(1 << 20), b""):
                    h.update(block)
        total = have
        try:
            with open(part, "ab" if have else "wb") as fh:
                for chunk in resp.iter_content(1 << 20):
                    if chunk:
                        fh.write(chunk)
                        h.update(chunk)
                        total += len(chunk)
        finally:
            resp.close()
        if total != ref.extra["size"]:
            raise HttpError(ref.url, 206, f"size {total} != {ref.extra['size']} (kept .part to resume)")
        os.replace(part, dest)
        self.http.media_bytes += total - have
        self.http.media_files += 1
        return total, h.hexdigest()
