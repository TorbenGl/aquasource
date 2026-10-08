"""OBSEA seabed station pictures (UPC / EMSO, Vilanova i la Geltru, NW Mediterranean, 20 m).

Still images from the cameras of the OBSEA seabed station, 2009 to 2025 (research/obsea.md). Each year is one
Zenodo record (``10.5281/zenodo.<id>``, title "Underwater photography at OBSEA seabed station during <year>"),
licence ``cc-by-4.0``, tier B, read at record level (the ERDDAP dataset says CC-BY-4.0 too). The records are monthly
zip files; every zip holds ``index.csv`` with one row per picture:

    timestamp (UTC), URL (https://files.obsea.es/pictures/<sensor>/<yyyy>/<mm>/<dd>/<name>.jpeg), sensor_id,
    platform_id, foi (field of view / biotope label), files (zip member path)

The adapter never downloads the zips (about 275 GB in total). It reads only the zip central directory and
``index.csv`` of each monthly zip with HTTP Range requests (cached in metadata/raw/obsea/), then downloads each
picture directly from files.obsea.es (plain HTTPS, no token, JPEG).

Geo (``resolve_geo``): the station is fixed. The publication gives one position for all pictures, latitude 41.18212 N,
longitude 1.75257 E, depth 20.0 m (Zenodo description, ERDDAP geospatial attributes). It is kept in
``src/aquasource/adapters/sites/obsea.csv`` and applied to every picture: ``geo_precision`` fixed_site, inferred, no
uncertainty value is published. The index has no per-picture coordinate.

Noisy data is kept (pretraining): night / dark frames, the PopUp camera, lab or sample photos and turbid frames are not
removed. Nothing is flagged by pixels yet (see research/obsea.md, doubts).

Adapter options (``--opt name=value``):
    from=YYYY-MM-DD      first picture day to keep (inclusive, UTC day of the index timestamp)
    to=YYYY-MM-DD        last picture day to keep (inclusive)
    per_day=N            keep at most N pictures per calendar day (default: all)
    years=2013,2014      only these Zenodo record years (default: all)
    sensors=a,b          only these sensor_id values (default: all)
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
from typing import Any, Iterable

from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from ..core.sites import load_sites
from .base import Adapter, register

log = logging.getLogger(__name__)

SEARCH = "https://zenodo.org/api/records"
SEARCH_QUERY = 'title:"Underwater photography at OBSEA seabed station during"'
PAGE_SIZE = 25
MAX_PAGES = 10
TITLE_RE = re.compile(r"Underwater photography at OBSEA seabed station during (\d{4})$")
INDEX_NAME = "index.csv"
BLOCK = 1 << 20  # Range read granularity for zip central directories and index members
SITE_ID = "obsea"
MEDIA_EXT = {"jpeg": "jpg", "jpg": "jpg", "png": "png"}
DOI_PREFIX = "10.5281/zenodo."


class RangeReader:
    """Read-only, seekable view of a remote file through HTTP Range requests (1 MiB blocks, cached)."""

    def __init__(self, http: Any, url: str, size: int):
        self.http = http
        self.url = url
        self.size = size
        self.pos = 0
        self._blocks: dict[int, bytes] = {}

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def tell(self) -> int:
        return self.pos

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def _block(self, b: int) -> bytes:
        if b not in self._blocks:
            start = b * BLOCK
            end = min(self.size, start + BLOCK) - 1
            self._blocks[b] = self.http.get_range(self.url, start, end)
        return self._blocks[b]

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.size - self.pos
        end = min(self.size, self.pos + n)
        if self.pos >= end:
            return b""
        out = bytearray()
        for b in range(self.pos // BLOCK, (end - 1) // BLOCK + 1):
            data = self._block(b)
            lo = max(self.pos, b * BLOCK) - b * BLOCK
            hi = min(end, (b + 1) * BLOCK) - b * BLOCK
            out += data[lo:hi]
        self.pos = end
        return bytes(out)


def read_index_csv(fileobj: Any) -> str:
    """Return the text of the top-level ``index.csv`` member of an open zip (any file-like with seek/tell/read)."""
    with zipfile.ZipFile(fileobj) as zf:
        names = [i.filename for i in zf.infolist() if i.filename.rsplit("/", 1)[-1] == INDEX_NAME]
        if not names:
            raise KeyError(INDEX_NAME)
        name = min(names, key=len)
        return zf.read(name).decode("utf-8", "replace")


def parse_index(text: str) -> list[dict[str, str]]:
    """Rows of an OBSEA index.csv as dicts (csv module; header ``timestamp,URL,sensor_id,platform_id,foi,files``)."""
    import csv

    return list(csv.DictReader(io.StringIO(text)))


def iso_utc(stamp: str) -> str | None:
    """``2013-01-09 18:17:42+00:00`` -> ``2013-01-09T18:17:42Z``; None if the shape is unexpected."""
    m = re.match(r"^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})(?:\.\d+)?(?:\+00:00|Z)?$", stamp.strip())
    return f"{m.group(1)}T{m.group(2)}Z" if m else None


def _list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]


@register
class ObseaAdapter(Adapter):
    key = "obsea"
    name = "OBSEA seabed station pictures (UPC / EMSO, 2009 to 2025)"
    homepage = "https://zenodo.org/communities/obsea/records"
    citation = (
        "Martinez, E. et al. and del Rio, J. (UPC): Underwater photography at OBSEA seabed station during <year>, "
        "Zenodo, https://doi.org/10.5281/zenodo.<record id> (CC BY 4.0). Cite each year's record, see each sample's attribution."
    )
    media_types = ("image",)
    host_intervals = {"zenodo.org": 1.0, "files.obsea.es": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._records: list[dict[str, Any]] | None = None
        self._site = None

    # ------------------------------------------------------------------ options
    def _day(self, name: str) -> str | None:
        v = self.options.get(name)
        return str(v).strip()[:10] if v not in (None, "") else None

    def _per_day(self) -> int | None:
        v = self.options.get("per_day")
        try:
            n = int(v)
        except (TypeError, ValueError):
            return None
        return n if n >= 1 else None

    # ---------------------------------------------------------------- metadata
    def records(self) -> list[dict[str, Any]]:
        """The yearly Zenodo records (search hits fetched as full records), oldest year first. Cached."""
        if self._records is None:
            hits: list[dict[str, Any]] = []
            for page in range(1, MAX_PAGES + 1):
                data = self.ctx.cached_json(
                    SEARCH,
                    f"zenodo_search_p{page}.json",
                    params={"q": SEARCH_QUERY, "size": PAGE_SIZE, "page": page},
                )
                batch = (data.get("hits") or {}).get("hits") or []
                hits.extend(batch)
                if len(batch) < PAGE_SIZE:
                    break
            years: dict[int, dict[str, Any]] = {}
            for hit in hits:
                title = (hit.get("metadata") or {}).get("title", "")
                m = TITLE_RE.search(title.strip())
                if not m:
                    continue
                rec = self.ctx.cached_json(
                    f"https://zenodo.org/api/records/{hit['id']}", f"zenodo_{hit['id']}.json"
                )
                years[int(m.group(1))] = rec
            self._records = [years[y] for y in sorted(years)]
        return self._records

    def index_rows(self, rec: dict[str, Any], zip_file: dict[str, Any]) -> list[dict[str, str]]:
        """Rows of one monthly zip's index.csv: read from metadata/raw/obsea/ or fetched by Range requests."""
        name = zip_file["key"]
        cache = f"obsea/{name}.index.csv"
        path = self.ctx.layout.raw / cache
        if path.exists() and not self.options.get("refresh_metadata"):
            text = path.read_text(encoding="utf-8")
        else:
            url = zip_file["links"]["self"]
            reader = RangeReader(self.ctx.http, url, int(zip_file["size"]))
            text = read_index_csv(reader)
            self.ctx.save_raw(cache, text)
        return parse_index(text)

    # --------------------------------------------------------------- interface
    def discover(self) -> Iterable[Candidate]:
        lo, hi, per_day = self._day("from"), self._day("to"), self._per_day()
        years = {int(y) for y in _list(self.options.get("years"))}
        sensors = set(_list(self.options.get("sensors")))
        counts: dict[str, int] = {}
        for rec in self.records():
            year = int(TITLE_RE.search(rec["metadata"]["title"].strip()).group(1))
            if years and year not in years:
                continue
            lic = rec["metadata"].get("license", {}).get("id", "")
            for zf in sorted(rec.get("files", []), key=lambda f: f["key"]):
                if not zf["key"].lower().endswith(".zip"):
                    continue
                try:
                    rows = self.index_rows(rec, zf)
                except (HttpError, KeyError, zipfile.BadZipFile, ValueError, OSError) as exc:
                    self.ctx.fail(zf["key"], "discover", f"index.csv not readable: {exc}")
                    continue
                for i, row in enumerate(rows):
                    url = (row.get("URL") or "").strip()
                    ts = iso_utc(row.get("timestamp") or "")
                    sensor = (row.get("sensor_id") or "").strip()
                    if not url or not ts:
                        self.ctx.fail(zf["key"], "discover", f"row {i}: no URL or timestamp")
                        continue
                    if sensors and sensor not in sensors:
                        continue
                    day = ts[:10]
                    if (lo and day < lo) or (hi and day > hi):
                        continue
                    if per_day and counts.get(day, 0) >= per_day:
                        continue
                    counts[day] = counts.get(day, 0) + 1
                    ext = MEDIA_EXT.get(url.rsplit(".", 1)[-1].lower(), "jpg")
                    yield Candidate(
                        source=self.key,
                        item_id=url,
                        media_type="image",
                        media_url=url,
                        origin_url=f"https://doi.org/{DOI_PREFIX}{rec['id']}",
                        timestamp=ts,
                        ext=ext,
                        raw={
                            "record_id": str(rec["id"]),
                            "doi": rec.get("doi") or f"{DOI_PREFIX}{rec['id']}",
                            "licence_id": lic,
                            "year": year,
                            "zip": zf["key"],
                        },
                        extra={
                            "zenodo_record": str(rec["id"]),
                            "zip": zf["key"],
                            "zip_member": (row.get("files") or "").strip(),
                            "sensor_id": sensor,
                            "platform_id": (row.get("platform_id") or "").strip(),
                            "field_of_view": (row.get("foi") or "").strip(),
                        },
                    )

    def resolve_licence(self, cand: Candidate) -> Licence:
        rec_id = cand.raw["record_id"]
        spdx = cand.raw.get("licence_id") or ""
        name = "CC-BY-4.0" if spdx.lower() == "cc-by-4.0" else spdx
        return make_licence(
            name,
            level="record",
            url=f"https://zenodo.org/records/{rec_id}",
            attribution=(
                f"OBSEA seabed station pictures {cand.raw['year']}, UPC / EMSO (del Rio, J. et al.), "
                f"https://doi.org/{cand.raw['doi']}, CC BY 4.0"
            ),
        )

    def resolve_geo(self, cand: Candidate) -> Geo:
        if self._site is None:
            self._site = load_sites(SITE_ID)[SITE_ID]
        site = self._site
        return site.geo(
            precision="fixed_site",
            geo_source=(
                f"{site.source}; applied to every picture (index.csv has no coordinate); "
                f"Zenodo {cand.raw['record_id']}"
            ),
            inferred=True,
        )
