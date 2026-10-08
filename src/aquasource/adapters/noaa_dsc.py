"""NOAA National Deep-Sea Coral and Sponge Database: occurrence images with record coordinates.

Source: NCEI accession 0145037 (https://www.ncei.noaa.gov/archive/accession/0145037, DOI 10.25921/t8c0-yx22, the
DSCRTP national occurrence database). The database is read through its public ERDDAP table
``https://www.ncei.noaa.gov/erddap/tabledap/deep_sea_corals`` (landing page
https://www.ncei.noaa.gov/erddap/tabledap/deep_sea_corals.html). The seed's host deepseacoraldata.noaa.gov is the portal
front end; the ERDDAP data endpoint is on www.ncei.noaa.gov (research/noaa_dsc.md).

One query fetches every record whose ``DataProvider`` starts with ``NOAA`` and whose ``ImageURL`` is set (metadata only,
cached in metadata/raw/erddap_noaa_images.csv). Several records can point to the same image (one photo, one record per
taxon), so the adapter yields one candidate per ``ImageURL``; the record CatalogNumbers are kept in ``extra``.

Licence (record level for the image; the dataset level is the same): the ISO record states ``accessLevel: public`` and
no licence; the ERDDAP licence text says the data "may be used and redistributed for free" with a no-warranty
disclaimer. NOAA federal work is a US government work, so images whose ``DataProvider`` is NOAA alone are tier A
(same reading as noaa_oe). Images with a co-provider after ``|`` (e.g. "NOAA, ... | University of Hawaii") may carry a
partner's copyright: tier U, never downloaded by the default tiers. Non-NOAA providers (MBARI, Harbor Branch, Nova
Southeastern, Smithsonian, ...) are not queried at all: their image licences were not checked, so they are out of scope
for this adapter (research/noaa_dsc.md).

Geo: ``latitude``, ``longitude``, ``DepthInMeters`` of the record(s) of the image, precision ``image`` (the seed's
decision). If records of one image disagree on coordinates, the lowest CatalogNumber is used and
``extra.geo_conflict`` is set. Records without numeric coordinates are dropped from the candidate list (geo none).
"""

from __future__ import annotations

import csv
import io
import logging
import re
from typing import Any, Iterable

from ..core.geo import to_float
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, register

log = logging.getLogger(__name__)

ERDDAP = "https://www.ncei.noaa.gov/erddap/tabledap/deep_sea_corals.csv"
# Only NOAA-prefixed providers; the server-side regex keeps the transfer small (about 165 k image records of 1.48 M).
QUERY = (
    "CatalogNumber,ImageURL,DataProvider,Repository,DatasetID,ScientificName,latitude,longitude,DepthInMeters,"
    "ObservationDate,Citation,Locality,Ocean,Country"
    '&ImageURL!=""&DataProvider=~"NOAA.*"&orderBy("CatalogNumber")'
)
RAW_NAME = "erddap_noaa_images.csv"
ISO_LANDING = "https://www.ncei.noaa.gov/archive/accession/0145037"
DOI = "https://doi.org/10.25921/t8c0-yx22"
PORTAL = "https://deepseacoraldata.noaa.gov"
GEO_SOURCE = "ERDDAP deep_sea_corals latitude,longitude,DepthInMeters (record CatalogNumber)"
MISSING = -999.0
NOAA_RE = re.compile(r"^NOAA\b")


def _records(text: str) -> Iterable[dict[str, str]]:
    """Yield data rows of an ERDDAP CSV (row 2 is the units row)."""
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        if not row.get("CatalogNumber") or not row.get("ImageURL"):
            continue  # units row or incomplete row
        yield row


@register
class NoaaDscAdapter(Adapter):
    key = "noaa_dsc"
    name = "NOAA National Deep-Sea Coral and Sponge Database (image records)"
    homepage = ISO_LANDING
    citation = (
        "Deep Sea Coral Research and Technology Program (DSCRTP) (2016). Observations of Deep-Sea Coral and Sponge "
        "Occurrences from the NOAA National Deep-Sea Coral and Sponge Database, NCEI Accession 0145037. "
        f"{DOI}"
    )
    media_types = ("image",)
    manual_steps = "None. Anonymous HTTPS to the public ERDDAP table; no token."
    host_intervals = {"www.ncei.noaa.gov": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self.skipped: dict[str, int] = {}

    def _skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    # ------------------------------------------------------------------------------------------- metadata I/O
    def _rows(self) -> list[dict[str, str]]:
        """NOAA-provider image records of the cached ERDDAP answer."""
        timeout = float(self.options.get("timeout_s", 900))
        text = self.ctx.cached_text(ERDDAP + "?" + QUERY, RAW_NAME, timeout=timeout)
        rows = []
        for row in _records(text):
            if not NOAA_RE.match(row.get("DataProvider", "").strip()):
                self._skip("provider not NOAA")  # the query already filters; guard against a changed answer
                continue
            rows.append(row)
        return rows

    # ------------------------------------------------------------------------------------------- discover
    def discover(self) -> Iterable[Candidate]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for row in self._rows():
            lat, lon = to_float(row.get("latitude")), to_float(row.get("longitude"))
            if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                self._skip("no coordinates")
                continue
            groups.setdefault(row["ImageURL"].strip(), []).append({**row, "_lat": lat, "_lon": lon})

        for image_url, recs in groups.items():
            recs.sort(key=lambda r: int(r["CatalogNumber"]))
            first = recs[0]
            conflict = any(abs(r["_lat"] - first["_lat"]) > 1e-6 or abs(r["_lon"] - first["_lon"]) > 1e-6 for r in recs)
            provider = first["DataProvider"].strip()
            names = sorted({r["ScientificName"].strip() for r in recs if r.get("ScientificName")})
            extra: dict[str, Any] = {
                "catalog_numbers": [int(r["CatalogNumber"]) for r in recs],
                "dataset_ids": sorted({r["DatasetID"] for r in recs}),
                "data_provider": provider,
                "repository": first.get("Repository", ""),
                "scientific_names": names[:20],
                "locality": first.get("Locality", ""),
                "ocean": first.get("Ocean", ""),
                "country": first.get("Country", ""),
                "geo_conflict": conflict,
                "maybe_not_underwater": False,
            }
            yield Candidate(
                source=self.key,
                item_id=image_url,
                media_type="image",
                media_url=image_url,
                origin_url=f"{PORTAL}/data",
                timestamp=first.get("ObservationDate") or None,
                ext=None,
                raw={
                    "provider": provider,
                    "lat": first["_lat"],
                    "lon": first["_lon"],
                    "depth": to_float(first.get("DepthInMeters")),
                    "citation": first.get("Citation", ""),
                    "catalog": first["CatalogNumber"],
                },
                extra=extra,
            )

    # ------------------------------------------------------------------------------------------- licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        provider = str(cand.raw.get("provider") or "")
        attribution = (
            f"{provider}; NOAA National Deep-Sea Coral and Sponge Database record(s) "
            f"{', '.join(str(c) for c in cand.extra.get('catalog_numbers', [])[:5])}; "
            f"cite {self.citation}"
        )
        if NOAA_RE.match(provider) and "|" not in provider:
            return make_licence(
                "US government work (NOAA), no licence stated; ISO accessLevel public",
                level="collection",
                url=ISO_LANDING,
                attribution=attribution,
                tier="A",
            )
        return make_licence(
            "NOAA co-provider with a partner institution: partner image licence not stated",
            level="collection",
            url=ISO_LANDING,
            attribution=attribution,
            tier="U",
        )

    # ------------------------------------------------------------------------------------------- geo
    def resolve_geo(self, cand: Candidate) -> Geo:
        raw = cand.raw
        depth = raw.get("depth")
        if depth is not None and depth <= MISSING:
            depth = None
        return Geo(raw["lat"], raw["lon"], depth, "image", GEO_SOURCE, False, None)

    # ------------------------------------------------------------------------------------------- estimate
    def estimate(self) -> dict[str, Any]:
        rows = self._rows()
        images = {r["ImageURL"].strip() for r in rows}
        joint = {r["ImageURL"].strip() for r in rows if "|" in r["DataProvider"]}
        return {
            "image_records_noaa": len(rows),
            "distinct_images_noaa": len(images),
            "distinct_images_tier_A_candidates": len(images - joint),
            "distinct_images_tier_U_co_provider": len(joint),
        }
