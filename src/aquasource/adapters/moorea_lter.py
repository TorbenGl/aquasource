"""Moorea Labeled Corals: 2,055 benthic photo-quadrats, Moorea LTER 2008 to 2010 (EDI knb-lter-mcr.5006.3, rev 3).

Source: https://doi.org/10.6073/pasta/88dde0e68ab5232a470389f4bedd1892 (research/moorea_lter.md). Three year zips
(2008, 2009, 2010; 5.6 GB together), each holding nadir 0.5 x 0.5 m photo-quadrats (.jpg, some .png in 2010) and one
200-point annotation file (.txt) per image. Licence CC BY 4.0, read at record level (EML intellectualRights).

Geo: every image is ``station`` precision, inferred. The filename carries site (lter1..lter6), habitat
(fringingreef, out10m, out17m) and date; the lookup table sites/moorea_lter.csv (EML site polygon centroids, BCO-DMO
10 m fore-reef points for LTER1/2) gives lat, lon, depth_m and uncertainty_m. Images that do not match the filename
pattern fall back to the dataset bounding box with precision ``region``.

Access: no per-image endpoint exists and the DataONE member node (gmn.lternet.edu) ignores HTTP Range, so each year zip
is downloaded whole into ``<data_root>/moorea_lter/archives/`` (MD5 from the EML checked). discover() reads the zip
directory from that file. A sample run therefore needs the zip of each year it touches; use ``years=`` to limit this.
Downloads of the zip are the only bytes fetched in discover(); dry runs never download them (they yield no candidates
until a zip is present).

Adapter options (``--opt name=value``):
    years=2008,2010     only these year zips (default: 2008,2009,2010; zips are processed in this order)
    habitats=out17m     only these habitats (fringingreef, out10m, out17m; comma separated)

Order (budget): inside a year zip the candidates are interleaved over the 18 site x habitat cells, so a small budget
covers many transects and depths of that year before the next year is read.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import struct
import zlib
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Iterable

from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from ..core.sites import load_sites
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

SITE_TABLE = "moorea_lter"
PACKAGE = "knb-lter-mcr.5006.3"
DOI = "https://doi.org/10.6073/pasta/88dde0e68ab5232a470389f4bedd1892"
PASTA_BASE = "https://pasta.lternet.edu/package/data/eml/knb-lter-mcr/5006/3"
# DataONE member node (anonymous, works while PASTA needs an EDI key). Object id = URL-encoded PASTA data URL.
GMN_BASE = "https://gmn.lternet.edu/mn/v2/object/https:%2F%2Fpasta.lternet.edu%2Fpackage%2Fdata%2Feml%2Fknb-lter-mcr%2F5006%2F3%2F"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"
ATTRIBUTION = (
    "Moorea Coral Reef LTER and P. Edmunds. 2019. MCR LTER: Coral Reef: Computer Vision: Moorea Labeled Corals ver 3. "
    f"Environmental Data Initiative. {DOI}. Licence: CC BY 4.0 ({LICENCE_URL}). "
    "Also cite Beijbom et al. 2012, Automated Annotation of Coral Reef Survey Images, IEEE CVPR. Image unmodified."
)
# Region fallback (research note, resolve_geo step 4): centre of the EML bounding box.
REGION_LAT, REGION_LON, REGION_UNCERTAINTY_M = -17.535, -149.835, 20000.0

# year -> (PASTA entity id, zip file name, bytes, MD5 from the EML physical/authentication, DataONE SHA-1)
ZIPS: dict[int, tuple[str, str, int, str, str]] = {
    2008: (
        "28c6c36ed93e699e0550361ee871bdc9",
        "MCR_LTER_ComputerVision_LabeledCorals_2008_20120521.zip",
        2_044_220_065,
        "743d62088ac2be456b8d50c02725bcc3",
        "4af4b83f3f964b3d7f234178130bc196e599ca18",
    ),
    2009: (
        "1b90487f445a82fe072c43871dfcd1ef",
        "MCR_LTER_ComputerVision_LabeledCorals_2009_20120523.zip",
        2_628_754_087,
        "4b265a33d32ebd6a7efc68c477d65e97",
        "9ccadaa2c5293542a861f6ea661c8c02ec7c799c",
    ),
    2010: (
        "41afbdac7aac223ff92dea751ea39530",
        "MCR_LTER_ComputerVision_LabeledCorals_2010_20120521.zip",
        962_738_166,
        "d708520d6822d9701bf02e64f8817b39",
        "86e79281b658113de8358df895864811bd99aa31",
    ),
}
HABITATS = ("fringingreef", "out10m", "out17m")
# mcr_lter6_out17m_pole5-6_qu3_20090331.jpg  (case-insensitive; annotation = same name + .txt)
IMAGE_RE = re.compile(
    r"^mcr_lter(?P<site>[1-6])_(?P<hab>fringingreef|out10m|out17m)_pole(?P<pa>\d+)-(?P<pb>\d+)"
    r"_qu(?P<q>\d+)_(?P<date>\d{4})(?P<mm>\d{2})(?P<dd>\d{2})\.(?P<ext>jpe?g|png)$"
)
MAGIC = {"jpg": b"\xff\xd8\xff", "png": b"\x89PNG\r\n\x1a\n"}


def parse_name(name: str) -> dict | None:
    """Filename tokens of one image, or None if the name does not follow the MCR pattern."""
    m = IMAGE_RE.match(name.lower())
    if not m:
        return None
    g = m.groupdict()
    ext = "jpg" if g["ext"].startswith("jp") else "png"
    return {
        "site": int(g["site"]),
        "habitat": g["hab"],
        "sid": f"LTER{g['site']}_{g['hab']}",
        "poles": f"{int(g['pa'])}-{int(g['pb'])}",
        "quadrat": int(g["q"]),
        "date": f"{g['date']}-{g['mm']}-{g['dd']}",
        "ext": ext,
    }


def scan_zip(path: Path) -> dict[str, tuple[int, int, int, int]]:
    """Walk the local file headers of a (possibly truncated) zip: name -> (data offset, method, compressed, size).

    Only members that lie completely inside the file are returned. Stops at the first non-local-header signature
    (central directory) or at members that use data descriptors (sizes 0 in the header).
    """
    out: dict[str, tuple[int, int, int, int]] = {}
    total = Path(path).stat().st_size
    with open(path, "rb") as fh:
        pos = 0
        while pos + 30 <= total:
            fh.seek(pos)
            sig, _v, flag, method, _t, _d, _crc, csize, usize, nlen, elen = struct.unpack("<IHHHHHIIIHH", fh.read(30))
            if sig != 0x04034B50 or (flag & 8):
                break
            name = fh.read(nlen).decode("utf-8", "replace")
            data_off = pos + 30 + nlen + elen
            if data_off + csize > total:
                break
            if not name.endswith("/"):
                out[PurePosixPath(name).name] = (data_off, method, csize, usize)
            pos = data_off + csize
    return out


def read_member(path: Path, entries: dict, base: str) -> bytes:
    if base not in entries:
        raise RuntimeError(f"{base} not found (complete) in zip")
    off, method, csize, _ = entries[base]
    with open(path, "rb") as fh:
        fh.seek(off)
        raw = fh.read(csize)
    if method == 0:
        return raw
    if method == 8:
        return zlib.decompress(raw, -15)
    raise RuntimeError(f"{base}: unsupported zip method {method}")


@register
class MooreaLterAdapter(Adapter):
    key = "moorea_lter"
    name = "Moorea Labeled Corals, Moorea Coral Reef LTER photo-quadrats 2008-2010"
    homepage = DOI
    citation = (
        "Moorea Coral Reef LTER and P. Edmunds (2019), MCR LTER: Coral Reef: Computer Vision: Moorea Labeled Corals ver 3, "
        f"EDI, {DOI} (CC BY 4.0)."
    )
    media_types = ("image",)
    host_intervals = {"gmn.lternet.edu": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._sites = None

    # ------------------------------------------------------------------ helpers
    def _years(self) -> list[int]:
        raw = str(self.options.get("years") or "").strip()
        years = [int(y) for y in raw.split(",") if y.strip()] if raw else sorted(ZIPS)
        bad = [y for y in years if y not in ZIPS]
        if bad:
            raise ValueError(f"unknown year(s) {bad}; available {sorted(ZIPS)}")
        return years

    def _habitats(self) -> set[str] | None:
        raw = str(self.options.get("habitats") or "").strip()
        if not raw:
            return None
        hab = {h.strip() for h in raw.split(",") if h.strip()}
        unknown = hab - set(HABITATS)
        if unknown:
            raise ValueError(f"unknown habitat(s) {sorted(unknown)}; available {HABITATS}")
        return hab

    def _zip_url(self, year: int) -> str:
        return GMN_BASE + ZIPS[year][0]

    def _archive(self, year: int) -> Path:
        return self.ctx.layout.root / "archives" / ZIPS[year][1]

    def _ensure_archive(self, year: int) -> Path:
        """Return the year zip: complete (MD5-checked) or, if the stream is cut off, the truncated ``.part`` head.

        The member node resets long streams (about 19 MB seen) and ignores Range. Local file headers carry the sizes
        (checked for 2010), so complete members of a truncated zip are still readable by ``scan_zip``. Option
        ``head_mb=N`` stops after N MB on purpose (small samples).
        """
        _, name, size, md5, _ = ZIPS[year]
        path = self._archive(year)
        if path.exists() and path.stat().st_size == size:
            return path
        part = path.with_name(path.name + ".part")
        if part.exists() and part.stat().st_size > 1_000_000 and not self.options.get("refetch"):
            return part
        head = int(self.options.get("head_mb") or 0) * 1_000_000 or None
        try:
            self.http.download(self._zip_url(year), path, expected_bytes=None if head else size, max_bytes=head)
        except Exception as exc:  # cut-off stream, size limit reached, connection reset
            if part.exists() and part.stat().st_size > 1_000_000:
                log.warning("moorea_lter: %d zip truncated at %d bytes (%s); using complete members only", year, part.stat().st_size, exc)
                return part
            raise
        digest = hashlib.md5()
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                digest.update(block)
        if digest.hexdigest() != md5:
            path.unlink(missing_ok=True)
            raise RuntimeError(f"{name}: MD5 {digest.hexdigest()} != EML {md5}; file removed, rerun to retry")
        return path

    @property
    def sites(self):
        if self._sites is None:
            self._sites = load_sites(SITE_TABLE)
        return self._sites

    # --------------------------------------------------------------- interface
    def discover(self) -> Iterable[Candidate]:
        habitats = self._habitats()
        for year in self._years():
            if self.ctx.dry_run and not self._archive(year).exists():
                log.info("moorea_lter: %d zip not downloaded; dry run lists no %d images", year, year)
                continue
            try:
                path = self._ensure_archive(year)
            except (HttpError, RuntimeError, OSError) as exc:
                self.ctx.fail(self._zip_url(year), "discover", f"{type(exc).__name__}: {exc}")
                continue
            cells: dict[str, list[Candidate]] = defaultdict(list)
            names = scan_zip(path)
            for base, ent in names.items():
                tok = parse_name(base)
                if tok is None or (habitats and tok["habitat"] not in habitats):
                    continue
                cells[tok["sid"]].append(self._candidate(year, base, ent[3], tok, f"{base}.txt" in names))
            # round-robin over the cells of this year, each cell in (poles, quadrat, date) order
            for lst in cells.values():
                lst.sort(key=lambda c: (c.raw["poles"], c.raw["quadrat"], c.raw["date"]))
            queues = [cells[k] for k in sorted(cells)]
            while any(queues):
                for q in queues:
                    if q:
                        yield q.pop(0)

    def _candidate(self, year: int, base: str, nbytes: int, tok: dict, has_anno: bool) -> Candidate:
        return Candidate(
            source=self.key,
            item_id=f"{year}/{base}",
            media_type="image",
            media_url=self._zip_url(year),
            origin_url=f"{PASTA_BASE}/{ZIPS[year][0]}#{year}/{base}",
            timestamp=tok["date"],
            ext=tok["ext"],
            raw={
                "year": year,
                "member": base,
                "bytes": nbytes,
                "annotation": f"{base}.txt" if has_anno else None,
                **tok,
            },
            extra={
                "year": year,
                "site": tok["site"],
                "habitat": tok["habitat"],
                "transect_poles": tok["poles"],
                "quadrat": tok["quadrat"],
                "dataset": PACKAGE,
                "annotation_file": f"metadata/annotations/{year}/{base}.txt" if has_anno else None,
            },
        )

    def resolve_licence(self, cand: Candidate) -> Licence:
        return make_licence(
            "CC-BY-4.0",
            level="record",
            url=LICENCE_URL,
            attribution=ATTRIBUTION,
        )

    def resolve_geo(self, cand: Candidate) -> Geo:
        sid = cand.raw.get("sid")
        site = self.sites.get(sid) if sid else None
        if site is None:
            return Geo(
                lat=REGION_LAT,
                lon=REGION_LON,
                depth_m=None,
                geo_precision="region",
                geo_source=(
                    "knb-lter-mcr.5006.3 EML geographicCoverage 'Moorea, French Polynesia' bbox "
                    "W-150.00 E-149.67 N-17.45 S-17.62 (centre); filename did not resolve to a site"
                ),
                geo_inferred=True,
                geo_uncertainty_m=REGION_UNCERTAINTY_M,
            )
        return site.geo(
            precision="station",
            geo_source=f"sites/moorea_lter.csv:{sid} (from filename tokens lter{cand.raw['site']}/{cand.raw['habitat']}); {site.source}",
            inferred=True,
        )

    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(url=cand.media_url, ext=cand.ext or "jpg", extra={"year": cand.raw["year"], "member": cand.raw["member"]})

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        """Copy one image out of its year zip (and its annotation file) to ``dest``; verify the magic bytes."""
        year, member = ref.extra["year"], ref.extra["member"]
        archive = self._archive(year)
        if not archive.exists():
            archive = archive.with_name(archive.name + ".part")
        if not archive.exists():
            raise RuntimeError(f"{ZIPS[year][1]} is not downloaded (discover() must run first)")
        entries = scan_zip(archive)
        data = read_member(archive, entries, member)
        anno_name = cand.raw.get("annotation")
        anno = read_member(archive, entries, anno_name) if anno_name else None
        magic = MAGIC[ref.ext if ref.ext in MAGIC else "jpg"]
        if not data.startswith(magic):
            raise RuntimeError(f"{member}: not a valid {ref.ext} file (bad magic bytes)")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, dest)
        if anno is not None:
            ap = self.ctx.layout.metadata / "annotations" / str(year) / anno_name
            ap.parent.mkdir(parents=True, exist_ok=True)
            ap.write_bytes(anno)
        return len(data), hashlib.sha256(data).hexdigest()

    def estimate(self) -> dict:
        return {"images": 2055, "zip_bytes": sum(z[2] for z in ZIPS.values()), "years": sorted(ZIPS)}
