"""CSIRO Marine National Facility (MNF): still images of RV Investigator voyage IN2023_V05 (SEA-MES Voyage 1).

The DAP image collection csiro:74006 (DOI 10.25919/gddy-hn24, https://data.csiro.au/collection/csiro:74006) holds
346,715 stills and 262 video-like files from the MNF Deep Towed Camera (DTC), 28 Jun - 30 Jul 2023, SE Australia
(36-43 S, 147-150 E). Access is anonymous (``dataRestricted`` FALSE, no token).

Geolocation: the stills are geolocated per image pair in one ``DTC_<deployment>_STILLS.CSV`` per deployment. Its
columns ``Key`` (the still's file name), ``Latitude``, ``Longitude`` and ``Depth`` (positive metres) give the camera
position of each still, so ``geo_precision = image``, ``geo_source = STILLS.CSV`` and ``geo_inferred = False``. Stills
without a Latitude/Longitude in the CSV are not yielded (the geo gate would drop them anyway). The 1-second video
navigation (``DTC_<deployment>.CSV``) is not used yet.

Licence: the collection record states "Creative Commons Attribution 4.0 International Licence" (DAP licence 1121,
the RDA record and the ISO 19115 record agree), so tier B at record level. The DAP ``rights`` field says "All Rights
(including copyright) CSIRO 2026."; that is standard boilerplate next to the explicit CC BY licence and is kept in
the attribution text. Videos are not harvested.

Access: the listing ``GET .../collections/74006/data`` answers with the complete file list in one response (about
1.36 GB, ``max`` and ``pageSize`` are ignored), so the adapter caches it once in metadata/raw/listing.json. Each file
is downloaded from ``https://data.csiro.au/dap/ws/v2/collections/74006/data/<id>``, which redirects to a presigned S3
link that expires after 2 days: presigned links are never stored, the redirect is followed at download time.

Options: ``deployments`` (list of deployment names such as ``"IN2023_V05_005"``, default all), ``max_rows`` (per
deployment, default all). See research/csiro_mnf.md.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
from pathlib import Path
from typing import Any, ClassVar, Iterable

from ..core.geo import check_coordinate, depth_from, to_float
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

COLLECTION = "74006"
DOI = "10.25919/gddy-hn24"
LANDING = f"https://data.csiro.au/collection/csiro:{COLLECTION}"
API = f"https://data.csiro.au/dap/ws/v2/collections/{COLLECTION}"
LISTING_URL = f"{API}/data"
LICENCE_NAME = "Creative Commons Attribution 4.0 International Licence"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"
ACK = "We acknowledge the use of the CSIRO Marine National Facility (https://ror.org/01mae9353) in undertaking this research."
ATTRIBUTION = (
    "CSIRO Marine National Facility (2026): Image Collection - RV Investigator Voyage IN2023_V05 - SEA-MES "
    f"Voyage 1. v1. CSIRO. Data Collection. https://doi.org/{DOI}. Licence: CC BY 4.0 ({LICENCE_URL}). {ACK}"
)
GEO_SOURCE = "STILLS.CSV Latitude/Longitude/Depth of the still's Key row (DAP collection 74006)"

# One file record of the listing, e.g. {"id":99348534,"filename":"IN2023_V05/data/DTC/IN2023_V05_005/...",
# "lastUpdated":"...","fileSize":378089,"link":{"relationship":"self","mediaType":"text/csv","href":"..."
FILE_RE = re.compile(
    r'\{"id":(\d+),"filename":"((?:[^"\\]|\\.)*)","lastUpdated":"[^"]*","fileSize":(\d+),'
    r'"link":\{"relationship":"self","mediaType":"([^"]*)","href":"([^"]*)"'
)
DEPLOYMENT_RE = re.compile(r"/DTC/([^/]+)/")


@register
class CsiroMnfAdapter(Adapter):
    key: ClassVar[str] = "csiro_mnf"
    name: ClassVar[str] = "CSIRO MNF RV Investigator voyage IN2023_V05 Deep Towed Camera stills"
    homepage: ClassVar[str] = LANDING
    citation: ClassVar[str] = ATTRIBUTION
    media_types: ClassVar[tuple[str, ...]] = ("image",)
    host_intervals: ClassVar[dict[str, float]] = {"data.csiro.au": 1.0, "s3.data.csiro.au": 1.0}
    manual_steps: ClassVar[str] = "none: anonymous access to the DAP collection 74006"

    def __init__(self, ctx):
        super().__init__(ctx)
        self._files: dict[str, list[tuple[int, str, int, str, str]]] | None = None

    # ------------------------------------------------------------ listing
    def _listing(self) -> dict[str, list[tuple[int, str, int, str, str]]]:
        """{deployment: [(id, filename, bytes, mediaType, href), ...]} from the one-shot full listing."""
        if self._files is None:
            text = self.ctx.cached_text(LISTING_URL, "listing.json", timeout=900)
            files: dict[str, list[tuple[int, str, int, str, str]]] = {}
            for m in FILE_RE.finditer(text):
                fid, fname, size, mtype, href = m.groups()
                dep = DEPLOYMENT_RE.search(fname)
                if not dep:
                    continue
                files.setdefault(dep.group(1), []).append((int(fid), fname, int(size), mtype, href))
            self._files = files
        return self._files

    # ------------------------------------------------------------ discover
    def discover(self) -> Iterable[Candidate]:
        files = self._listing()
        wanted = set(self.options.get("deployments") or []) or None
        max_rows = self.options.get("max_rows")
        for dep in sorted(files):
            if wanted and dep not in wanted:
                continue
            recs = files[dep]
            stills = [r for r in recs if r[1].upper().endswith("_STILLS.CSV")]
            if not stills:
                continue
            by_base = {os.path.basename(r[1]): r for r in recs if r[3].startswith("image/")}
            csv_name = f"stills/{dep}.csv"
            text = self.ctx.cached_text(stills[0][4], csv_name, timeout=300)
            n = 0
            for row in csv.DictReader(io.StringIO(text)):
                lat, lon = to_float(row.get("Latitude")), to_float(row.get("Longitude"))
                key = (row.get("Key") or "").strip()
                if lat is None or lon is None or not key:
                    continue
                img = by_base.get(key)
                if img is None:
                    self.ctx.fail(key, "discover", "still listed in STILLS.CSV but not in the DAP listing", deployment=dep)
                    continue
                fid, fname, size, _mtype, href = img
                yield Candidate(
                    source=self.key,
                    item_id=f"{COLLECTION}:{fid}",
                    media_type="image",
                    media_url=href,
                    origin_url=LANDING,
                    timestamp=(row.get("Date") or None),
                    ext="jpg",
                    raw={"row": row, "file_id": fid, "filename": fname, "bytes": size, "deployment": dep},
                    extra={
                        "voyage": "IN2023_V05",
                        "deployment": dep,
                        "camera": "DTC stereo still (SCP/SCS)",
                        "doi": f"https://doi.org/{DOI}",
                        "dap_file_id": fid,
                        "stills_csv": stills[0][1],
                    },
                )
                n += 1
                if max_rows and n >= int(max_rows):
                    break

    def estimate(self) -> dict[str, Any]:
        return {"images": 346715, "collection_bytes": 3779204083283, "listing_bytes_approx": 1_362_305_984}

    # ------------------------------------------------------------ metadata
    def resolve_licence(self, cand: Candidate) -> Licence:
        return make_licence(
            LICENCE_NAME, level="record", url=LICENCE_URL, attribution=ATTRIBUTION
        )

    def resolve_geo(self, cand: Candidate) -> Geo:
        row = cand.raw["row"]
        lat, lon = to_float(row.get("Latitude")), to_float(row.get("Longitude"))
        depth = depth_from(row.get("Depth"))
        reason = check_coordinate(lat, lon)
        if reason or lat is None or lon is None:
            return Geo.none(GEO_SOURCE, depth_m=depth)
        return Geo(lat, lon, depth, "image", GEO_SOURCE, False, None)

    def resolve_media(self, cand: Candidate) -> MediaRef:
        size = cand.raw.get("bytes")
        return MediaRef(url=cand.media_url, ext="jpg", expected_bytes=size or None)

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        # The /data/<id> link answers with a redirect to a short-lived presigned S3 URL; never store that URL.
        return self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes)
