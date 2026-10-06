"""BenthicNet-1M and BenthicNet-Labelled seafloor photos on the Canadian FRDR.

One CSV row is one image with its own ``latitude`` / ``longitude`` (WGS 84) and a
modelled GEBCO depth. The licence is set per image set in
``00_Documentation/all_licenses_refs.csv`` and is joined case-insensitively on
``dataset``. Only tier A (U.S. Public Domain) and B (CC BY, OGL-Canada) sets are
yielded by default; NC/ND sets, the Schmidt Ocean ``FK*`` sets (listed as CC BY
but CC BY-NC-SA 4.0 at origin) and sets missing from the table are tier X or U
and never ingested. BenthicNet-11M has no published image list (see
research/benthicnet.md), so ``subset=11m`` is reported as "not ready".

How it works
    * The licence table and the two CSVs come from ``finalized_csvs.zip`` over
      anonymous HTTPS: the zip central directory is read with a 64 KiB Range
      request and only the wanted member is fetched (about 25 MB for 1M) and
      inflated into ``metadata/raw/``. Nothing is downloaded twice.
    * One pass over the CSV builds per-site and per-dataset coordinate
      statistics. They drive the precision classification of ``resolve_geo``
      (RLS and shared-coordinate sites are ``station``, one-coordinate datasets
      are ``region``, everything else is ``image``).
    * ``discover`` yields rows in a budget-friendly order (``order=spread``):
      weighted round robin over source groups (share ~ sqrt(images), at most
      15 % for Catlin, RLS and SQUIDLE+), then datasets, then sites, then evenly
      spaced in time inside a site. Any prefix of the stream is well spread, so
      ``--budget N`` does not simply take the first N rows of the file.
    * Item ids are ``<dataset>/<site>/<image>`` and are stable across runs.

Adapter options (``--opt key=value``; values are JSON or comma separated lists)
    subset            ``1m`` (default), ``labelled`` or ``both``. ``both`` yields the 1M rows first,
                      then the Labelled rows whose ``url`` is not in 1M. ``11m`` is not available.
    order             ``spread`` (default) or ``csv`` (file order, no global sort).
    sources           only these CSV ``source`` values (e.g. ``NGU,SEAM,MUN``), case-insensitive.
    exclude_sources   drop these ``source`` values.
    datasets          only these dataset names (tar names without ``.tar``), case-insensitive.
    exclude_datasets  drop these dataset names.
    exclude_overlap   true drops sources that other aquasource keys also cover (SQUIDLE+, Catlin,
                      PANGAEA, NOAA, USGS, NRCan, AADC).
    all_tiers         true also yields tier U/X rows (audit only; the runner still drops them).
    resolve_pangaea   true (default): a ``pangaea-<id>`` set missing from the licence table is promoted
                      to its own PANGAEA record licence (metainfo_xml) when that record is CC BY or CC0.
    media             ``original`` (default): GET the row ``url``; ``tar``: take the 512 px JPEG from the
                      per-dataset tar on FRDR (the whole tar is downloaded once and kept in
                      ``<root>/tars``); ``auto``: tar when it is at most ``tar_max_mb``, else original.
    tar_max_mb        size limit for ``media=auto`` (default 50).
    local_dir         folder with files you downloaded yourself: ``finalized_csvs.zip`` or the CSVs,
                      ``all_licenses_refs.csv`` and, optionally, individual ``<dataset>.tar`` files.
    refresh_metadata  core option: re-download cached metadata.

Always dropped: ``nrcan-71014`` (collages of 2-6 photos, the paper says it was excluded).
Not handled here (needs image-level checks): black, water-column and on-deck frames.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import math
import os
import re
import struct
import tarfile
import time
import zipfile
import zlib
from array import array
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import quote, urlparse

import requests

from ..core.geo import check_coordinate, parse_time, to_float
from ..core.http import HttpError
from ..core.licence import classify, combine, make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

# ---------------------------------------------------------------- provider constants
FRDR = "https://www.frdr-dfdr.ca"
PUB_PATH = "9/published/publication_1236/submitted_data"
FILES = f"{FRDR}/repo/files/{PUB_PATH}"
SIZE_CACHE = f"{FRDR}/cache/9/publication_1236/file_sizes"
LICENCE_TABLE_URL = f"{FILES}/00_Documentation/all_licenses_refs.csv"
LICENCE_TABLE_NAME = "all_licenses_refs.csv"
ZIP_URL = f"{FILES}/01_BenthicNet/csvs/finalized_csvs.zip"
ZIP_NAME = "finalized_csvs.zip"
RECORD_DOI = "https://doi.org/10.20383/103.01241"
URLS_PREFIX = f"{FRDR}/repo/files/9/published/publication_961/"

BENTHICNET_CITATION = (
    "Lowe, S.C., Misiuk, B., Xu, I., et al. (2025). BenthicNet: A global compilation of seafloor images for "
    "deep learning applications. Scientific Data 12, 230. https://doi.org/10.1038/s41597-025-04491-1; "
    "Misiuk, B., Lowe, S., Xu, I. (2024). BenthicNet. Federated Research Data Repository. "
    "https://doi.org/10.20383/103.01241"
)
URLS_CITATION = "Misiuk, B., Lowe, S., Xu, I. (2024). BenthicNet-URLs. FRDR. https://doi.org/10.20383/103.0966"
RLS_RECORD = "6e9c4980-1005-11dd-b28e-00188b4c0af8"
RLS_NOTE = (
    "Reef Life Survey (RLS) Habitat Quadrats, IMAS metadata record "
    f"https://metadata.imas.utas.edu.au/geonetwork/srv/api/records/{RLS_RECORD} "
    "(Creative Commons Attribution 3.0 Australia License)"
)

# Image sets that other aquasource keys also cover (for exclude_overlap).
OVERLAP_SOURCES = ("squidle+", "xl catlin seaview survey", "pangaea", "noaa", "usgs", "nrcan", "aadc")
# CSV `source` values that are NC/ND at origin whatever the table says (safety net).
EXCLUDED_SOURCES = ("fathomnet", "mgds", "usap-dc")
# Collages of 2-6 photos; the paper says the set was excluded, but its tar is present.
ALWAYS_DROP_DATASETS = ("nrcan-71014",)
# Schmidt Ocean Institute cruises (FK181210, FKt230115, fk180731 ...): listed CC BY, CC BY-NC-SA 4.0 at origin.
SOI_RX = re.compile(r"^fkt?\d{6}", re.I)
PANGAEA_RX = re.compile(r"^pangaea-(\d+)$", re.I)
# Source groups whose share of the budget is capped (RLS photo-quadrats are SQUIDLE+ rows named RLS_*).
CAPPED_GROUPS = ("rls", "squidle+", "xl catlin seaview survey")
GROUP_CAP = 0.15

LICENCE_URLS = {
    "cc-by-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "cc-by-3.0": "https://creativecommons.org/licenses/by/3.0/",
    "open government licence - canada": "https://open.canada.ca/en/open-government-licence-canada",
    # BenthicNet ships the CC0 1.0 text as LICENSE_Public_Domain.txt for these sets.
    "u.s. public domain": "https://creativecommons.org/publicdomain/zero/1.0/",
}

CORE_COLS = ("url", "source", "dataset", "site", "image", "latitude", "longitude", "datetime", "gebco_bathymetry")
REQUIRED_COLS = ("url", "source", "dataset", "site", "image", "latitude", "longitude")

IMAGE_EXTS = {"jpg", "jpeg", "png", "tif", "tiff", "bmp", "gif", "webp"}
MAX_TAR_MEMBER_BYTES = 256 * 1024 * 1024
MAX_MEMBER_USIZE = 4 * 1024**3


@dataclass(frozen=True)
class _Subset:
    name: str
    kind: str  # folder under 01_BenthicNet/images
    csv_name: str  # name of the CSV (zip member, raw file)
    derived_name: str | None  # compact one-row-per-image copy built from the Labelled member


SUB_1M = _Subset("1m", "unlabelled", "benthicnet_unlabelled_sub.csv", None)
SUB_LABELLED = _Subset("labelled", "labelled", "benthicnet_labelled.csv", "benthicnet_labelled_images.csv")
SUBSETS = {"1m": SUB_1M, "labelled": SUB_LABELLED}


@dataclass(frozen=True)
class _LicInfo:
    name: str
    tier: str
    level: str
    url: str | None
    citation: str
    listed: str  # licence string exactly as listed in all_licenses_refs.csv ("" if unlisted)
    note: str = ""


# ------------------------------------------------------------------ small helpers
def norm_url(url: str) -> str:
    """Key used to deduplicate images: http -> https, no trailing slash."""
    u = url.strip()
    if u.lower().startswith("http://"):
        u = "https://" + u[7:]
    return u.rstrip("/")


def https_url(url: str) -> str:
    u = url.strip()
    return "https://" + u[7:] if u.lower().startswith("http://") else u


def url_ext(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    return ext if ext in IMAGE_EXTS else "jpg"


def sanitize(name: str) -> str:
    """Path-safe name as written by BenthicNet's own tar builder (benthicnet/io.py, per the research note)."""
    s = name.encode("ascii", "ignore").decode("ascii").strip(" .")
    s = s.replace("/", "-")
    for ch in ':*?"<>|':
        s = s.replace(ch, "")
    return s


def iso_time(value: str) -> str | None:
    """ISO 8601 string for a BenthicNet datetime (mixed formats; treated as UTC)."""
    v = (value or "").strip()
    if not v:
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return v
    t = parse_time(v)
    if t is None:
        return None
    try:
        return datetime.fromtimestamp(t, timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [p.strip() for p in value.split(",") if p.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(p).strip() for p in value if str(p).strip()]
    return [str(value)]


def decode_text(data: bytes) -> str:
    """UTF-8 when valid, else Windows-1252 (the licence table is cp1252)."""
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def parse_licence_table(text: str) -> dict[str, dict[str, str]]:
    """``dataset.lower()`` -> {source, dataset, licence, citation, tier}."""
    table: dict[str, dict[str, str]] = {}
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿"), newline=""))
    for row in reader:
        dataset = (row.get("Dataset") or "").strip()
        if not dataset:
            continue
        licence = (row.get("License") or "").strip()
        rec = {
            "source": (row.get("Source") or "").strip(),
            "dataset": dataset,
            "licence": licence,
            "citation": (row.get("Citation") or "").strip(),
            "tier": classify(licence),
        }
        key = dataset.lower()
        old = table.get(key)
        if old and old["licence"] != licence:  # contradictory duplicate rows: hold (X wins, otherwise U)
            rec["licence"] = f"{old['licence']} / {licence}"
            rec["tier"] = combine(old["tier"], rec["tier"])
            rec["citation"] = old["citation"] or rec["citation"]
        table[key] = rec
    return table


def allocate_weights(counts: dict[str, int], capped: Iterable[str] = CAPPED_GROUPS, cap: float = GROUP_CAP) -> dict[str, float]:
    """Share per group ~ sqrt(images); groups named in ``capped`` get at most ``cap`` (water filling)."""
    raw = {g: math.sqrt(n) for g, n in counts.items() if n > 0}
    if not raw:
        return {}
    capped_l = {c.lower() for c in capped}
    total = sum(raw.values())
    share = {g: v / total for g, v in raw.items()}
    fixed: dict[str, float] = {}
    while True:
        over = [g for g in share if g.lower() in capped_l and g not in fixed and share[g] > cap + 1e-12]
        if not over:
            break
        for g in over:
            fixed[g] = cap
        free = [g for g in raw if g not in fixed]
        rest = 1.0 - cap * len(fixed)
        if not free or rest <= 0:
            break
        ftotal = sum(raw[g] for g in free)
        share = {**{g: raw[g] / ftotal * rest for g in free}, **fixed}
    s = sum(share.values())
    return {g: v / s for g, v in share.items()}


_PERM_CACHE: dict[int, tuple[int, ...]] = {}


def spread_perm(m: int) -> tuple[int, ...]:
    """Pick order for ``m`` time-sorted items so that every prefix is evenly spread (bit reversal)."""
    if m <= 1:
        return tuple(range(m))
    hit = _PERM_CACHE.get(m)
    if hit is not None:
        return hit
    bits = (m - 1).bit_length()
    out = tuple(r for r in (int(format(i, f"0{bits}b")[::-1], 2) for i in range(1 << bits)) if r < m)
    if m <= 50_000:
        _PERM_CACHE[m] = out
    return out


def sniff_image(path: Path) -> bool:
    """True when the first bytes look like an image (downloaded content is untrusted)."""
    with open(path, "rb") as fh:
        head = fh.read(16)
    return (
        head.startswith(b"\xff\xd8\xff")
        or head.startswith(b"\x89PNG\r\n\x1a\n")
        or head[:4] in (b"II*\x00", b"MM\x00*", b"GIF8")
        or head.startswith(b"BM")
        or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")
    )


def _iter_lines(chunks: Iterable[bytes]) -> Iterator[str]:
    tail = b""
    for chunk in chunks:
        parts = (tail + chunk).split(b"\n")
        tail = parts.pop()
        for p in parts:
            yield p.decode("utf-8", "replace") + "\n"
    if tail:
        yield tail.decode("utf-8", "replace")


# ----------------------------------------------------------------------- the index
class _Index:
    """Compact per-CSV index: row offsets, ordering keys and the coordinate statistics for resolve_geo."""

    def __init__(self, sub: _Subset, path: Path, header: list[str]):
        self.sub = sub
        self.path = path
        self.header = header
        self.col = {name.strip(): i for i, name in enumerate(header)}
        self.offsets = array("Q")
        self.row_site = array("I")
        self.row_t = array("I")
        self.order: array | None = None
        # sites, keyed by (dataset, site)
        self.site_tab: dict[tuple[str, str], int] = {}
        self.site_n = array("I")  # unique urls
        self.site_nc = array("I")  # of which with a valid coordinate
        self.site_lat0 = array("d")
        self.site_lon0 = array("d")
        self.site_has = bytearray()  # at least one valid coordinate
        self.site_multi = bytearray()  # more than one distinct coordinate
        self.site_ds = array("I")
        self.site_hash = array("I")
        # datasets
        self.ds_tab: dict[str, int] = {}
        self.ds_group: list[str] = []
        self.ds_hash = array("I")
        self.ds_rows = array("I")
        self.ds_nsites = array("I")
        self.ds_lat0 = array("d")
        self.ds_lon0 = array("d")
        self.ds_has = bytearray()
        self.ds_multi_coord = bytearray()
        self.ds_multi = array("I")  # sites with n > 1
        self.ds_shared = array("I")  # sites with n > 1 and exactly one coordinate
        self.seen: set[int] | None = None
        self.skipped: Counter = Counter()
        self.rows_total = 0
        self.bad_rows = 0
        self._fh: Any = None

    # ---- statistics
    def add_site(self, dataset: str, site: str, di: int) -> int:
        si = len(self.site_n)
        self.site_tab[(dataset, site)] = si
        self.site_n.append(0)
        self.site_nc.append(0)
        self.site_lat0.append(0.0)
        self.site_lon0.append(0.0)
        self.site_has.append(0)
        self.site_multi.append(0)
        self.site_ds.append(di)
        self.site_hash.append(zlib.crc32(f"{dataset}\x00{site}".encode("utf-8", "replace")) & 0xFFFFFF)
        self.ds_nsites[di] += 1
        return si

    def add_dataset(self, dataset: str, group: str) -> int:
        di = len(self.ds_group)
        self.ds_tab[dataset] = di
        self.ds_group.append(group)
        self.ds_hash.append(zlib.crc32(dataset.encode("utf-8", "replace")) & 0xFFFFFF)
        for arr in (self.ds_rows, self.ds_nsites, self.ds_multi, self.ds_shared):
            arr.append(0)
        self.ds_lat0.append(0.0)
        self.ds_lon0.append(0.0)
        self.ds_has.append(0)
        self.ds_multi_coord.append(0)
        return di

    def finish_stats(self) -> None:
        for si in range(len(self.site_n)):
            if self.site_n[si] > 1:
                di = self.site_ds[si]
                self.ds_multi[di] += 1
                if self.site_has[si] and not self.site_multi[si]:
                    self.ds_shared[di] += 1

    # ---- precision (research/benthicnet.md "resolve_geo recipe", step 4)
    def classify_site(self, dataset: str, source: str, si: int) -> tuple[str, bool, float | None]:
        if dataset.upper().startswith("RLS_"):
            return "station", True, 1000.0
        di = self.ds_tab[dataset]
        if self.ds_nsites[di] >= 2 and self.ds_has[di] and not self.ds_multi_coord[di]:
            return "region", True, None
        n = self.site_n[si]
        one_coord = bool(self.site_has[si]) and not self.site_multi[si]
        multi = self.ds_multi[di]
        station = (n > 1 and one_coord) or (n == 1 and multi > 0 and self.ds_shared[di] / multi >= 0.5)
        if station:
            src = source.upper()
            if src in ("NOAA", "USGS", "USAP-DC"):
                unc = 5000.0
            elif src == "MGDS" or dataset.lower().startswith("fk"):
                unc = 2000.0
            else:
                unc = 1000.0
            return "station", True, unc
        return "image", False, None

    def precision_counts(self, sources: dict[int, str]) -> dict[str, int]:
        out: Counter = Counter()
        for (dataset, _site), si in self.site_tab.items():
            prec, _inf, _unc = self.classify_site(dataset, sources.get(self.site_ds[si], ""), si)
            out[prec] += self.site_nc[si]
            out["none"] += self.site_n[si] - self.site_nc[si]
        return dict(out)

    # ---- rows
    def open(self) -> None:
        if self._fh is None:
            self._fh = open(self.path, "rb")

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def split(self, line: str) -> list[str]:
        if '"' in line:
            return next(csv.reader([line]), [])
        return line.rstrip("\r\n").split(",")

    def read_row(self, i: int) -> dict[str, str]:
        self.open()
        self._fh.seek(self.offsets[i])
        fields = self.split(self._fh.readline().decode("utf-8", "replace"))
        return {c: fields[self.col[c]].strip() for c in CORE_COLS if c in self.col and self.col[c] < len(fields)}


# ---------------------------------------------------------------------- the adapter
@register
class BenthicNetAdapter(Adapter):
    key = "benthicnet"
    name = "BenthicNet (BenthicNet-1M and BenthicNet-Labelled seafloor photos, FRDR)"
    homepage = RECORD_DOI
    citation = BENTHICNET_CITATION
    media_types = ("image",)
    env_vars = ()
    manual_steps = (
        "None: every file is reachable over anonymous HTTPS (no Globus account). Optional: put already "
        "downloaded files (finalized_csvs.zip, all_licenses_refs.csv, <dataset>.tar) in a folder and pass "
        "--opt local_dir=<folder>. BenthicNet-11M has no published image list."
    )
    host_intervals = {"www.frdr-dfdr.ca": 1.0, "doi.pangaea.de": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._table: dict[str, dict[str, str]] | None = None
        self._lic_memo: dict[tuple[str, str], _LicInfo] = {}
        self._indexes: dict[str, _Index] = {}
        self._seen_1m: set[int] | None = None
        self._sizes: dict[str, dict[str, int]] = {}
        self._tar_lower: dict[str, dict[str, str]] = {}
        self._tars: dict[Path, tuple[tarfile.TarFile, dict[str, tarfile.TarInfo]]] = {}
        o = self.options
        self._inc_sources = {s.lower() for s in as_list(o.get("sources"))}
        self._exc_sources = {s.lower() for s in as_list(o.get("exclude_sources"))}
        self._inc_ds = {s.lower() for s in as_list(o.get("datasets"))}
        self._exc_ds = {s.lower() for s in as_list(o.get("exclude_datasets"))} | set(ALWAYS_DROP_DATASETS)
        self._exc_overlap = bool(o.get("exclude_overlap", False))
        self._all_tiers = bool(o.get("all_tiers", False))
        self._resolve_pangaea = bool(o.get("resolve_pangaea", True))

    # ------------------------------------------------------------ option checks
    def _subsets(self) -> list[_Subset]:
        s = str(self.options.get("subset", "1m")).strip().lower()
        if s == "both":
            return [SUB_1M, SUB_LABELLED]
        if s in SUBSETS:
            return [SUBSETS[s]]
        if s == "11m":
            raise ValueError(
                "subset=11m: BenthicNet-11M has no published image list (finalized_csvs.zip holds only the 1M "
                "and Labelled CSVs). The 11M images stay at their origin repositories: use the keys squidle_imos, "
                "catlin_seaview and pangaea_images, or subset=1m / labelled / both."
            )
        raise ValueError(f"unknown subset {s!r}; use 1m, labelled or both")

    def check_ready(self) -> list[str]:
        problems = super().check_ready()
        try:
            self._subsets()
        except ValueError as exc:
            problems.append(str(exc))
        if str(self.options.get("order", "spread")) not in ("spread", "csv"):
            problems.append("option order must be spread or csv")
        if str(self.options.get("media", "original")) not in ("original", "tar", "auto"):
            problems.append("option media must be original, tar or auto")
        return problems

    # ---------------------------------------------------------------- metadata IO
    def _local(self, *names: str) -> Path | None:
        ld = self.options.get("local_dir")
        if not ld:
            return None
        base = Path(str(ld)).expanduser()
        for n in names:
            p = base / n
            if p.is_file():
                return p
        return None

    def _licence_table(self) -> dict[str, dict[str, str]]:
        if self._table is None:
            raw = self.ctx.layout.raw / LICENCE_TABLE_NAME
            refresh = bool(self.options.get("refresh_metadata"))
            if raw.exists() and not refresh:
                data = raw.read_bytes()
            else:
                local = self._local(LICENCE_TABLE_NAME, f"00_Documentation/{LICENCE_TABLE_NAME}")
                data = local.read_bytes() if local else self.http.get(LICENCE_TABLE_URL).content
                self.ctx.save_raw(LICENCE_TABLE_NAME, data)  # exactly as downloaded (cp1252)
            self._table = parse_licence_table(decode_text(data))
            log.info("benthicnet: licence table has %d datasets", len(self._table))
        return self._table

    def _tar_sizes(self, kind: str) -> dict[str, int]:
        """Tar file name -> bytes, from the FRDR size cache of the per-dataset tar folder.

        Names are kept exactly: FathomNet_misc.tar and fathomnet_misc.tar are two different tars.
        """
        if kind not in self._sizes:
            folder = f"01_BenthicNet/images/{kind}/individual_dataset_tars"
            digest = hashlib.sha256(folder.encode()).hexdigest()
            data = self.ctx.cached_json(f"{SIZE_CACHE}/file_sizes-{digest}.json", f"frdr_tar_sizes_{kind}.json")
            entries = data.get("contents", []) if isinstance(data, dict) else data
            self._sizes[kind] = {e["name"]: int(e["size"]) for e in entries if str(e.get("name", "")).endswith(".tar")}
        return self._sizes[kind]

    def _tar_lookup(self, kind: str, name: str) -> tuple[str, int] | None:
        """(listed tar name, bytes): exact name first, then case-insensitively."""
        sizes = self._tar_sizes(kind)
        if name in sizes:
            return name, sizes[name]
        low = self._tar_lower.get(kind)
        if low is None:
            low = self._tar_lower[kind] = {}
            for n in sizes:
                low.setdefault(n.lower(), n)
        hit = low.get(name.lower())
        return (hit, sizes[hit]) if hit else None

    def estimate(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "images_1m": 1_345_096,
            "images_labelled": 188_688,
            "images_11m_not_distributed": 11_408_887,
        }
        for sub in self._subsets():
            try:
                sizes = self._tar_sizes(sub.kind)
            except Exception as exc:  # estimate is optional
                log.info("benthicnet: size cache unavailable: %s", exc)
                continue
            tag = "1m" if sub.kind == "unlabelled" else "labelled"
            out[f"tars_{tag}"] = len(sizes)
            out[f"tar_gb_{tag}"] = round(sum(sizes.values()) / 1e9, 2)
        return out

    # ------------------------------------------------------- remote zip member
    def _remote_member(self, member: str) -> Iterator[bytes]:
        """Decompressed bytes of one zip member, fetched with HTTP Range requests (no full zip download)."""
        url = ZIP_URL
        size = int(self.http.head(url).headers.get("Content-Length") or 0)
        if size <= 0:
            raise HttpError(url, None, "no Content-Length from HEAD; cannot read the zip central directory")
        tail_start = max(0, size - 65536)
        tail = self.http.get_range(url, tail_start, size - 1)
        eocd = tail.rfind(b"PK\x05\x06")
        if eocd < 0:
            raise RuntimeError("zip end-of-central-directory record not found")
        _sig, _d, _d2, _n, total, cd_size, cd_off, _clen = struct.unpack("<4s4H2LH", tail[eocd : eocd + 22])
        if cd_off == 0xFFFFFFFF or total == 0xFFFF:
            raise NotImplementedError("zip64 archives are not supported")
        cd = tail[cd_off - tail_start : cd_off - tail_start + cd_size] if cd_off >= tail_start else self.http.get_range(url, cd_off, cd_off + cd_size - 1)
        entry = None
        pos = 0
        while pos + 46 <= len(cd) and cd[pos : pos + 4] == b"PK\x01\x02":
            f = struct.unpack("<4s6H3L5H2L", cd[pos : pos + 46])
            nlen, elen, clen = f[10], f[11], f[12]
            name = cd[pos + 46 : pos + 46 + nlen].decode("utf-8", "replace")
            if name == member or name.endswith("/" + member):
                entry = {"method": f[4], "crc": f[7], "csize": f[8], "usize": f[9], "off": f[16], "name": name}
                break
            pos += 46 + nlen + elen + clen
        if entry is None:
            raise RuntimeError(f"{member} not found in {ZIP_NAME}")
        if 0xFFFFFFFF in (entry["csize"], entry["usize"], entry["off"]):
            raise NotImplementedError("zip64 member")
        if entry["usize"] > MAX_MEMBER_USIZE or entry["method"] not in (0, 8):
            raise RuntimeError(f"unsupported zip member {entry}")
        lh = self.http.get_range(url, entry["off"], entry["off"] + 29)
        lsig, *_rest = struct.unpack("<4s5H3L2H", lh)
        if lsig != b"PK\x03\x04":
            raise RuntimeError("bad zip local header")
        nlen, elen = struct.unpack("<2H", lh[26:30])
        start = entry["off"] + 30 + nlen + elen
        end = start + entry["csize"] - 1
        resp = self.http.request("GET", url, headers={"Range": f"bytes={start}-{end}"}, stream=True)
        try:
            if resp.status_code != 206:
                raise HttpError(url, resp.status_code, "server did not honour the Range request")
            dec = zlib.decompressobj(-15) if entry["method"] == 8 else None
            crc = 0
            got = 0
            for chunk in resp.iter_content(1 << 20):
                out = dec.decompress(chunk) if dec else chunk
                if out:
                    got += len(out)
                    if got > entry["usize"]:
                        raise RuntimeError("zip member larger than its header says")
                    crc = zlib.crc32(out, crc)
                    yield out
            if dec:
                out = dec.flush()
                if out:
                    got += len(out)
                    crc = zlib.crc32(out, crc)
                    yield out
            if got != entry["usize"] or (crc & 0xFFFFFFFF) != entry["crc"]:
                raise RuntimeError(f"zip member {member} failed its size/CRC check")
        finally:
            resp.close()

    def _local_zip_member(self, zip_path: Path, member: str) -> Iterator[bytes]:
        with zipfile.ZipFile(zip_path) as zf:
            name = next((n for n in zf.namelist() if n == member or n.endswith("/" + member)), None)
            if name is None:
                raise RuntimeError(f"{member} not found in {zip_path}")
            with zf.open(name) as fh:
                while True:
                    chunk = fh.read(1 << 20)
                    if not chunk:
                        break
                    yield chunk

    def _member_stream(self, member: str) -> Iterator[bytes]:
        local = self._local(ZIP_NAME, f"01_BenthicNet/csvs/{ZIP_NAME}")
        if local:
            return self._local_zip_member(local, member)
        return self._remote_member(member)

    def _with_retries(self, fn, what: str, attempts: int = 3):
        for attempt in range(attempts):
            try:
                return fn()
            except (requests.RequestException, HttpError) as exc:
                if attempt == attempts - 1:
                    raise
                delay = 2.0 ** (attempt + 1)
                log.warning("benthicnet: %s failed (%s); retry in %.0fs", what, exc, delay)
                time.sleep(delay)

    def _save_plain(self, member: str, dest: Path) -> None:
        def run() -> None:
            tmp = dest.with_name(dest.name + ".part")
            with open(tmp, "wb") as fh:
                for chunk in self._member_stream(member):
                    fh.write(chunk)
            os.replace(tmp, dest)

        self._with_retries(run, f"fetching {member}")

    def _derive_labelled(self, member: str, dest: Path) -> None:
        """One row per image (first label row wins), CATAMI label columns dropped."""

        def run() -> None:
            tmp = dest.with_name(dest.name + ".part")
            reader = csv.reader(_iter_lines(self._member_stream(member)))
            header = [h.strip() for h in next(reader)]
            col = {h: i for i, h in enumerate(header)}
            missing = [c for c in REQUIRED_COLS if c not in col]
            if missing:
                raise RuntimeError(f"{member}: missing columns {missing}")
            keep = [c for c in CORE_COLS if c in col]
            seen: set[int] = set()
            with open(tmp, "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh, lineterminator="\n")
                w.writerow(keep)
                for row in reader:
                    if len(row) < len(header):
                        continue
                    h = hash(norm_url(row[col["url"]]))
                    if h in seen:
                        continue
                    seen.add(h)
                    w.writerow([row[col[c]].replace("\n", " ").replace("\r", " ") for c in keep])
            os.replace(tmp, dest)

        self._with_retries(run, f"fetching {member}")

    def _ensure_csv(self, sub: _Subset) -> Path:
        raw = self.ctx.layout.raw
        refresh = bool(self.options.get("refresh_metadata"))
        names = [sub.csv_name] + ([sub.derived_name] if sub.derived_name else [])
        if not refresh:
            for n in names:
                p = raw / n
                if p.exists() and p.stat().st_size > 0:
                    return p
        local = self._local(sub.csv_name, f"finalized_csvs/{sub.csv_name}")
        if local:
            return local
        raw.mkdir(parents=True, exist_ok=True)
        if sub.derived_name:
            dest = raw / sub.derived_name
            self._derive_labelled(sub.csv_name, dest)
        else:
            dest = raw / sub.csv_name
            self._save_plain(sub.csv_name, dest)
        return dest

    # ----------------------------------------------------------------- licences
    def _compute_licence(self, dataset: str, source: str) -> _LicInfo:
        row = self._licence_table().get(dataset.lower())
        listed = row["licence"] if row else ""
        citation = row["citation"] if row else ""
        table_source = row["source"] if row else ""
        if source.lower() in EXCLUDED_SOURCES or table_source.lower() in EXCLUDED_SOURCES:
            return _LicInfo(
                f"{listed or 'not stated'} (BenthicNet source {source or table_source}: NC/ND at origin)",
                "X", "record", LICENCE_URLS.get(listed.lower()), citation, listed,
            )
        if row:
            tier = row["tier"]
            url = LICENCE_URLS.get(listed.lower())
            if tier == "X":
                return _LicInfo(listed, "X", "record", url, citation, listed)
            if SOI_RX.match(dataset):
                return _LicInfo(
                    f"{listed} (BenthicNet table); Schmidt Ocean Institute applies CC BY-NC-SA 4.0 at origin, held as U",
                    "U", "record", None, citation, listed,
                    note="SOI cruise listed as CC BY by BenthicNet but CC BY-NC-SA 4.0 at origin",
                )
            if dataset.upper().startswith("RLS_") and tier in ("A", "B"):
                return _LicInfo(
                    f"{listed} (BenthicNet table; RLS origin record states CC BY 3.0 Australia)",
                    tier, "record", url, citation, listed, note=RLS_NOTE,
                )
            return _LicInfo(listed, tier, "record", url, citation, listed)
        m = PANGAEA_RX.match(dataset)
        if m and self._resolve_pangaea:
            info = self._pangaea_licence(m.group(1))
            if info:
                return info
        return _LicInfo(
            "not listed in BenthicNet all_licenses_refs.csv (collection licence: custom, per image set)",
            "U", "collection", LICENCE_TABLE_URL, "", "",
        )

    def _pangaea_licence(self, ds_id: str) -> _LicInfo | None:
        """Record-level licence of a pangaea-<id> set that is missing from the BenthicNet table."""
        url = f"https://doi.pangaea.de/10.1594/PANGAEA.{ds_id}?format=metainfo_xml"
        try:
            xml = self.ctx.cached_text(url, f"pangaea_{ds_id}_metainfo.xml")
        except Exception as exc:
            self.ctx.fail(f"pangaea-{ds_id}", "licence", f"PANGAEA metainfo unavailable: {exc}")
            return None
        lic = re.search(r"<md:license\b.*?</md:license>", xml, re.S)
        if not lic:
            return None
        block = lic.group(0)

        def tag(name: str, text: str = block) -> str:
            m = re.search(rf"<md:{name}>(.*?)</md:{name}>", text, re.S)
            return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""

        label, lname, uri = tag("label"), tag("name"), tag("URI")
        tier = combine(classify(label or lname), classify(uri)) if uri else classify(label or lname)
        cit = re.search(r"<md:citation\b.*?</md:citation>", xml, re.S)
        citation = ""
        if cit:
            c = cit.group(0)
            authors = []
            for a in re.findall(r"<md:author\b.*?</md:author>", c, re.S):
                last, first = tag("lastName", a), tag("firstName", a)
                authors.append(f"{last}, {first[:1]}." if first else last)
            title, year, doi = tag("title", c), tag("year", c), re.findall(r"<md:URI>(.*?)</md:URI>", c)[-1:]
            citation = f"{', '.join(authors)} ({year}): {title}. PANGAEA, {doi[0] if doi else ''}".strip()
        return _LicInfo(
            label or lname, tier, "record", uri or None, citation, "",
            note=f"not in BenthicNet's table; licence read from its PANGAEA record {ds_id}",
        )

    def _lic_info(self, dataset: str, source: str) -> _LicInfo:
        key = (dataset.lower(), source.lower())
        info = self._lic_memo.get(key)
        if info is None:
            info = self._lic_memo[key] = self._compute_licence(dataset, source)
        return info

    def resolve_licence(self, cand: Candidate) -> Licence:
        ex = cand.extra
        dataset, source = ex.get("dataset", ""), ex.get("bn_source", "")
        info = self._lic_info(dataset, source)
        parts = []
        if info.citation:
            parts.append(info.citation if info.citation.rstrip().endswith((".", ")")) else info.citation.rstrip("; ") + ".")
        listed = info.listed or info.name
        parts.append(
            f"Image set {dataset} ({source}), licence {listed} as listed in BenthicNet 00_Documentation/{LICENCE_TABLE_NAME}; "
            f"image {ex.get('site', '')}/{ex.get('image', '')}; origin {ex.get('url', '')}."
        )
        if info.note:
            parts.append(info.note + ".")
        parts.append(f"Compiled in BenthicNet: {BENTHICNET_CITATION}.")
        if str(ex.get("url", "")).startswith(URLS_PREFIX):
            parts.append(f"Served from BenthicNet-URLs: {URLS_CITATION}.")
        return make_licence(info.name, level=info.level, url=info.url, attribution=" ".join(parts), tier=info.tier)

    # ---------------------------------------------------------------- the index
    def _drop_reason(self, source: str, dataset: str) -> str | None:
        s, d = source.lower(), dataset.lower()
        if d in self._exc_ds:
            return "dataset excluded"
        if self._inc_ds and d not in self._inc_ds:
            return "dataset filter"
        if self._inc_sources and s not in self._inc_sources:
            return "source filter"
        if s in self._exc_sources:
            return "source excluded"
        if self._exc_overlap and s in OVERLAP_SOURCES:
            return "overlaps other catalog keys"
        info = self._lic_info(dataset, source)
        if info.tier not in ("A", "B") and not self._all_tiers:
            return f"tier {info.tier}"
        return None

    def _index(self, sub: _Subset) -> _Index:
        idx = self._indexes.get(sub.name)
        if idx is None:
            idx = self._indexes[sub.name] = self._build_index(sub)
        return idx

    def _build_index(self, sub: _Subset) -> _Index:
        self._licence_table()
        path = self._ensure_csv(sub)
        skip = self._seen_1m if sub is SUB_LABELLED else None
        t0 = time.time()
        with open(path, "rb") as fh:
            head = fh.readline()
            header = next(csv.reader([head.decode("utf-8-sig", "replace")]), [])
            idx = _Index(sub, path, header)
            missing = [c for c in REQUIRED_COLS if c not in idx.col]
            if missing:
                raise RuntimeError(f"{path.name}: missing columns {missing}")
            c = idx.col
            ncols = len(header)
            c_dt = c.get("datetime", -1)
            seen: set[int] = set()
            decision: dict[tuple[str, str], str | None] = {}
            pos = len(head)
            for raw in fh:
                off = pos
                pos += len(raw)
                line = raw.decode("utf-8", "replace")
                if not line.strip():
                    continue
                f = idx.split(line)
                if len(f) != ncols:
                    idx.bad_rows += 1
                    continue
                url, source, dataset, site = f[c["url"]].strip(), f[c["source"]].strip(), f[c["dataset"]].strip(), f[c["site"]].strip()
                if not url or not dataset:
                    idx.bad_rows += 1
                    continue
                idx.rows_total += 1
                h = hash(norm_url(url))
                if h in seen:
                    idx.skipped["duplicate url"] += 1
                    continue
                seen.add(h)
                dkey = (source, dataset)
                if dkey not in decision:
                    decision[dkey] = self._drop_reason(source, dataset)
                reason = decision[dkey]
                if reason:
                    idx.skipped[reason] += 1
                    continue
                # --- statistics (per CSV, over every kept dataset row)
                di = idx.ds_tab.get(dataset)
                if di is None:
                    di = idx.add_dataset(dataset, "RLS" if dataset.upper().startswith("RLS_") else source)
                si = idx.site_tab.get((dataset, site))
                if si is None:
                    si = idx.add_site(dataset, site, di)
                idx.site_n[si] += 1
                idx.ds_rows[di] += 1
                lat, lon = to_float(f[c["latitude"]]), to_float(f[c["longitude"]])
                if lat is not None and lon is not None and check_coordinate(lat, lon) is None:
                    idx.site_nc[si] += 1
                    if not idx.site_has[si]:
                        idx.site_has[si], idx.site_lat0[si], idx.site_lon0[si] = 1, lat, lon
                    elif lat != idx.site_lat0[si] or lon != idx.site_lon0[si]:
                        idx.site_multi[si] = 1
                    if not idx.ds_has[di]:
                        idx.ds_has[di], idx.ds_lat0[di], idx.ds_lon0[di] = 1, lat, lon
                    elif lat != idx.ds_lat0[di] or lon != idx.ds_lon0[di]:
                        idx.ds_multi_coord[di] = 1
                if skip is not None and h in skip:
                    idx.skipped["already in 1M"] += 1
                    continue
                t = parse_time(f[c_dt]) if c_dt >= 0 else None
                tk = 0 if t is None else max(0, min(2**32 - 1, int(t) + 2**31))
                idx.offsets.append(off)
                idx.row_site.append(si)
                idx.row_t.append(tk)
        idx.finish_stats()
        if sub is SUB_1M and str(self.options.get("subset", "1m")).lower() == "both":
            self._seen_1m = seen
        idx.order = self._build_order(idx)
        self._write_summary(idx, time.time() - t0)
        return idx

    def _build_order(self, idx: _Index) -> array:
        n = len(idx.offsets)
        if str(self.options.get("order", "spread")) == "csv" or n < 2:
            return array("I", range(n))
        rs, rt = idx.row_site, idx.row_t
        # level 1: evenly spaced in time inside each site (van der Corput / bit reversal)
        keys = [(rs[i] << 32) | rt[i] for i in range(n)]
        by_site = sorted(range(n), key=keys.__getitem__)
        k = array("I", [0]) * n
        i = 0
        while i < n:
            s = rs[by_site[i]]
            j = i
            while j < n and rs[by_site[j]] == s:
                j += 1
            block = by_site[i:j]
            for rank, p in enumerate(spread_perm(len(block))):
                k[block[p]] = rank
            i = j
        # level 2: round robin over the sites of a dataset
        ds_of, sh = idx.site_ds, idx.site_hash
        keys = [((ds_of[rs[i]] << 24 | min(k[i], 0xFFFFFF)) << 24) | sh[rs[i]] for i in range(n)]
        pos2 = array("I", [0]) * n
        cur, c = -1, 0
        for r in sorted(range(n), key=keys.__getitem__):
            d = ds_of[rs[r]]
            if d != cur:
                cur, c = d, 0
            pos2[r] = c
            c += 1
        # level 3: round robin over the datasets of a source group
        gid = {g: n_ for n_, g in enumerate(sorted(set(idx.ds_group)))}
        grp = [gid[g] for g in idx.ds_group]
        dh = idx.ds_hash
        keys = [(((grp[ds_of[rs[i]]] << 32) | pos2[i]) << 24) | dh[ds_of[rs[i]]] for i in range(n)]
        pos3 = array("I", [0]) * n
        cur, c = -1, 0
        for r in sorted(range(n), key=keys.__getitem__):
            g = grp[ds_of[rs[r]]]
            if g != cur:
                cur, c = g, 0
            pos3[r] = c
            c += 1
        # level 4: weighted interleave of the groups (share ~ sqrt(images), capped for the big three)
        counts: Counter = Counter()
        for di, g in enumerate(idx.ds_group):
            counts[g] += idx.ds_rows[di]
        share = allocate_weights(dict(counts))
        w = [share.get(g, 1e-9) for g in sorted(set(idx.ds_group))]
        gkeys = array("d", ((pos3[i] + 0.5) / w[grp[ds_of[rs[i]]]] for i in range(n)))
        return array("I", sorted(range(n), key=gkeys.__getitem__))

    def _write_summary(self, idx: _Index, seconds: float) -> None:
        sources = {di: g for di, g in enumerate(idx.ds_group)}
        summary = {
            "csv": idx.path.name,
            "subset": idx.sub.name,
            "rows_read": idx.rows_total,
            "rows_selectable": len(idx.offsets),
            "rows_skipped": dict(idx.skipped),
            "bad_rows": idx.bad_rows,
            "datasets": len(idx.ds_tab),
            "sites": len(idx.site_tab),
            "geo_precision_rows": idx.precision_counts(sources),
            "seconds": round(seconds, 1),
        }
        try:
            (self.ctx.layout.metadata / f"index_{idx.sub.name}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        except OSError as exc:  # summary is informational only
            log.info("benthicnet: cannot write index summary: %s", exc)
        log.info("benthicnet: indexed %s: %s", idx.sub.name, summary)

    # ----------------------------------------------------------------- discover
    def discover(self) -> Iterable[Candidate]:
        for sub in self._subsets():
            idx = self._index(sub)
            assert idx.order is not None
            try:
                for i in idx.order:
                    row = idx.read_row(i)
                    cand = self._candidate(sub, idx, row)
                    if cand is not None:
                        yield cand
            finally:
                idx.close()

    def _candidate(self, sub: _Subset, idx: _Index, row: dict[str, str]) -> Candidate | None:
        dataset, site, image, source, url = row["dataset"], row["site"], row["image"], row["source"], row["url"]
        ts = iso_time(row.get("datetime", ""))
        extra: dict[str, Any] = {
            "dataset": dataset,
            "site": site,
            "image": image,
            "bn_source": source,
            "bn_subset": sub.name,
            "url": url,
            "url_norm": norm_url(url),
            "tar": f"{dataset}.tar",
        }
        if dataset.upper().startswith("RLS_"):
            extra["datetime_synthetic"] = True  # RLS photo times count up from 00:00:00 in 1-20 s steps
        if source.lower() == "nrcan" and ts and int(ts[:4]) < 1978:
            extra["greyscale_film_scan"] = True
        return Candidate(
            source=self.key,
            item_id=f"{dataset}/{site}/{image}",
            media_type="image",
            media_url=https_url(url),
            origin_url=RECORD_DOI,
            timestamp=ts,
            ext=url_ext(url),
            raw={"row": row, "csv": idx.path.name, "subset": sub.name},
            extra=extra,
        )

    # --------------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        row, csv_name = cand.raw["row"], cand.raw["csv"]
        base = f"{csv_name}:latitude,longitude (WGS84 dd); depth_m=-gebco_bathymetry (GEBCO_2022 bilinear, modelled)"
        lat, lon = to_float(row.get("latitude")), to_float(row.get("longitude"))
        if lat is None or lon is None or check_coordinate(lat, lon) is not None:
            return Geo.none(geo_source=f"{base}: latitude/longitude empty, out of range or (0, 0)")
        g = to_float(row.get("gebco_bathymetry"))
        depth = round(-g, 1) if g is not None and g < 0 else None  # >= 0 is land / shoreline: not a depth
        sub = SUBSETS[cand.raw["subset"]]
        idx = self._index(sub)
        dataset, site = row["dataset"], row["site"]
        si = idx.site_tab.get((dataset, site))
        if si is None:
            return Geo(lat, lon, depth, "image", base, False, None)
        prec, inferred, unc = idx.classify_site(dataset, row.get("source", ""), si)
        return Geo(lat, lon, depth, prec, base, inferred, unc)

    # ------------------------------------------------------------------- media
    def _tar_candidates(self, name: str, kind: str) -> list[Path]:
        ld = self.options.get("local_dir")
        if not ld:
            return []
        base = Path(str(ld)).expanduser()
        return [base / name, base / "individual_dataset_tars" / name, base / f"01_BenthicNet/images/{kind}/individual_dataset_tars" / name]

    def _route(self, cand: Candidate) -> str:
        media = str(self.options.get("media", "original"))
        if media != "auto":
            return media
        kind = SUBSETS[cand.extra.get("bn_subset", "1m")].kind
        hit = self._tar_lookup(kind, str(cand.extra["tar"]))
        limit = float(self.options.get("tar_max_mb", 50)) * 1e6
        return "tar" if hit and hit[1] <= limit else "original"

    def resolve_media(self, cand: Candidate) -> MediaRef:
        route = self._route(cand)
        cand.extra["image_route"] = route
        if route == "tar":
            kind = SUBSETS[cand.extra["bn_subset"]].kind
            name = str(cand.extra["tar"])
            hit = self._tar_lookup(kind, name)
            tar_name, size = hit if hit else (name, None)
            member = f"{sanitize(cand.extra['dataset'])}/{sanitize(cand.extra['site'])}/{sanitize(cand.extra['image'])}.jpg"
            url = f"{FILES}/01_BenthicNet/images/{kind}/individual_dataset_tars/{quote(tar_name)}"
            return MediaRef(url=url, ext="jpg", expected_bytes=size, extra={"route": "tar", "member": member, "kind": kind, "tar_name": tar_name})
        return MediaRef(url=cand.media_url, ext=cand.ext or url_ext(cand.media_url), extra={"route": "original", "fallback": cand.extra.get("url")})

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        if ref.extra.get("route") == "tar":
            return self._fetch_from_tar(ref, dest)
        try:
            nbytes, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes)
        except HttpError:
            alt = ref.extra.get("fallback")
            if not alt or alt == ref.url:
                raise
            dest.with_name(dest.name + ".part").unlink(missing_ok=True)  # do not resume across hosts/schemes
            nbytes, sha = self.http.download(alt, dest, expected_bytes=ref.expected_bytes)
        if not sniff_image(dest):
            dest.unlink(missing_ok=True)
            raise HttpError(ref.url, None, "response is not an image (content sniff failed)")
        return nbytes, sha

    def _tar_index(self, path: Path) -> dict[str, tarfile.TarInfo]:
        if path not in self._tars:
            tf = tarfile.open(path, "r:")
            self._tars[path] = (tf, {m.name: m for m in tf.getmembers() if m.isfile()})
        return self._tars[path][1]

    def _fetch_from_tar(self, ref: MediaRef, dest: Path) -> tuple[int, str]:
        kind, tar_name, member = ref.extra["kind"], ref.extra["tar_name"], ref.extra["member"]
        tar_path = next((p for p in self._tar_candidates(tar_name, kind) if p.is_file()), None)
        if tar_path is None:
            safe = re.sub(r"[^\w.()+ -]", "_", tar_name)
            tar_path = self.ctx.layout.root / "tars" / kind / f"{hashlib.sha1(tar_name.encode()).hexdigest()[:8]}_{safe}"
            if not tar_path.exists():
                self.http.download(ref.url, tar_path, expected_bytes=ref.expected_bytes)
        index = self._tar_index(tar_path)
        info = index.get(member)
        if info is None:  # tolerate case / separator differences in the stored path
            low = {k.lower(): v for k, v in index.items()}
            info = low.get(member.lower())
        if info is None:
            raise RuntimeError(f"{member} not found in {tar_path.name}")
        if info.size > MAX_TAR_MEMBER_BYTES:
            raise RuntimeError(f"{member} is {info.size} bytes; refusing to extract")
        tf = self._tars[tar_path][0]
        src = tf.extractfile(info)
        if src is None:
            raise RuntimeError(f"{member} is not a regular file")
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        h = hashlib.sha256()
        total = 0
        with src, open(part, "wb") as out:
            while True:
                chunk = src.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
                h.update(chunk)
                total += len(chunk)
        if not sniff_image(part):
            part.unlink(missing_ok=True)
            raise RuntimeError(f"{member} in {tar_path.name} is not an image")
        os.replace(part, dest)
        return total, h.hexdigest()
