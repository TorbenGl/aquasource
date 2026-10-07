"""NOAA National Coral Reef Monitoring Program (NCRMP) benthic photo-quadrats, US Pacific (PIFSC ESD), on NCEI.

Diver photo-quadrats shot straight down from a 1 m monopod, about 30 per site visit, at 0-30 m depth: Hawaii
(main and Northwestern islands), the Mariana Archipelago, American Samoa and the Pacific Remote Island Areas.
NCEI archives them in 38 accessions covering 2013-2019 and 2022-2025 (17 "climate station" accessions =
fixed sites, 21 stratified-random-site (StRS) accessions), about 0.22 M JPEGs and 1.57 TB (research/noaa_ncrmp.md).
The media are anonymous HTTPS files on www.ncei.noaa.gov (Apache directory listings, Range supported).
Still images only, no video.

Licence, tier A. The six 2024-2025 accessions (0317534, 0317535, 0317752, 0317753, 0317785, 0317786) carry an
explicit CC0 1.0 dedication in their NCEI record (ISO XML ``otherConstraints``, record level). All older ones,
the 2023 accessions included, state no licence: they are NOAA (US federal) works with ``accessLevel: public``
and a citation request only. Their tier A rests on the US-government-work status, read at collection level
(InPort 71813 / 71814: ``data-access-constraints`` "None", citation request). Attribution is the "Cite as"
line of each accession's record plus the ESD acknowledgement. An NC / ND / research-only term in a record would
make it tier X; nothing like it exists today.

Geo, ``station`` precision, ``geo_inferred`` true, ``geo_uncertainty_m`` 50. Every accession ships a site-info
CSV (``SITE`` [+ ``OCC_SITEID``], ``DATE_``, ``LATITUDE``, ``LONGITUDE``, WGS 84): the boat's handheld GPS
position over the divers' buoy, one per site visit, applied to every frame. The image name is
``SITE_YEAR[_REP]_NN.JPG`` and the site code joins to the CSV **of the same accession only** (codes are reused
across years and permanent sites were renamed, e.g. JOH-07 -> OCC-JOH-004). Depth is not in the image
accessions: it is joined from NCEI's benthic-cover tables (0317416 fixed sites, 0317464 StRS) as
mean(MIN_DEPTH, MAX_DEPTH) x 0.3048 (the tables are in feet), ``depth_m`` stays empty where a visit has none
(StRS Hawaii 2013, Marianas 2014, unannotated images). Nothing is ever invented: a site code missing from the CSV
falls back to the cover table, else the sample has ``geo_precision`` none (and is dropped by the runner).

How it works
    * The accession table (path, year, region, kind, counts) is built in: it is the verified list of the
      research note (InPort 71813 climate + 71814 StRS + 59193 bleaching). ``discover`` reads only listings and
      CSVs, cached under metadata/raw/ (``listing/<acc>/...``, ``siteinfo/<acc>/...``, ``iso/<acc>.xml``,
      ``cover/<table>.csv``), so a re-run does not hit NCEI again. Item ids are ``<accession>/<file name>``
      (e.g. ``0317534/OCC-FFS-001_2024_02.JPG``), stable across runs.
    * Listings: ``.../<arc>/<acc>/<ver>/data/0-data/`` is walked depth first (one request per directory, about
      1 s each); the ``DataDocumentation`` folders are skipped. The big flat folders (13-20 k files, 2-3 MB of
      HTML) take one request. 0176286, 0176287 and 0176288 keep the raw cruise tree
      (``Cruise/CruiseData/<cruise>/.../Optical/<ISL>/REA/{BENTHIC,FISH}/<SITE>/PHOTO_QUADS/[A|B/]``, about 1,600
      directories for 0176286): a directory whose name is a site code of the site-info CSV is a lazy site visit,
      its (about 4) directories are only listed when one of its frames is selected, so a small budget costs
      a few dozen requests, not hours.
    * The unit of sampling is the site visit (accession x site code, about 7,300 visits, about 30 adjacent
      correlated 1 m2 frames each). Budget-friendly order (``order=spread``, default): round 0 takes ONE
      frame of every visit, round 1 a second frame, and so on up to ``frames_per_visit`` (default 3; so every
      sample of a budget below ~7,300 has a distinct station). Within a round: weighted round robin over the
      accessions (equal weight per region = Hawaii / Marianas / Samoa / PRIA, within a region ``climate_share``
      0.25 for the climate accessions and the rest for StRS, equal inside a group, so every survey year
      appears), inside an accession the visits are sorted by survey date and taken in a spread order (first,
      last, middle, ...), inside a visit the frames follow a van der Corput order (centre, quarters, ...) that
      avoids the first and last frames (slate, transect marker). Any prefix of the stream covers all regions,
      years and the cruise tracks.
    * Frames numbered 0 (the slate) are dropped; numbers above 30 are kept (0159155 has 17 legitimate frames
      31-38). Names that do not parse become one-frame visits with geo none. Duplicate names inside one
      accession are listed once.
    * Not done here: slate / hand detectors, EXIF handling (frames carry ``extra.exif_note``: apply the
      ``Orientation`` tag, ``DateTimeOriginal`` is wrong on some cameras and is ignored; the survey date comes
      from the site-info CSV), black / on-deck frame filters. Frame extraction is not needed (images).
    * Politeness: 1 request per second to www.ncei.noaa.gov (listings, CSVs, images), one transfer at a time.
      The server sometimes drops TLS: the project Http client retries with back-off. Every image is checked for the
      JPEG magic number after the download. Downloaded files are data and are never executed.

Adapter options (``--opt key=value``; values are JSON or comma separated lists)
    accessions        only these NCEI accession numbers, e.g. ``0317534,0159155`` (default: all 38).
    kind              ``all`` (default), ``climate`` (fixed sites, 17 accessions) or ``strs`` (random sites, 21).
    regions           any of ``hawaii`` (MHI + NWHI), ``marianas``, ``samoa``, ``pria`` (default all).
    years             survey years of the accessions, e.g. ``2024,2025``.
    from, to          ISO dates (``2019-04-01``): keep site visits whose survey date lies inside (visits
                      without a parsable date are kept).
    frames_per_visit  frames taken per site visit: an integer (default 3) or ``all`` (every frame of every
                      visit: about 0.22 M images, 1.57 TB).
    order             ``spread`` (default, see above) or ``table`` (accession by accession, visits by site code).
    climate_share     share of the samples of a region that comes from climate accessions (default 0.25).
    depth             ``cover`` (default: join depth from the 5 cover tables, read once, about 545 MB streamed,
                      reduced to a ~0.5 MB table per file in metadata/raw/cover/) or ``off`` (``depth_m`` empty).
    refresh_metadata  core option: re-download cached metadata.
"""

from __future__ import annotations

import csv
import hashlib
import html
import io
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator
from urllib.parse import quote, unquote, urljoin, urlparse

from ..core.geo import depth_from, to_float
from ..core.http import HttpError
from ..core.licence import classify, combine, make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

NCEI = "https://www.ncei.noaa.gov"
ARCHIVE = f"{NCEI}/data/oceans/archive"
LANDING = NCEI + "/archive/accession/{acc}"
ISO_URL = NCEI + "/access/metadata/landing-page/bin/iso?id=gov.noaa.nodc:{acc}&view=xml"
INPORT = "https://www.fisheries.noaa.gov/inport/item/{n}"
CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/"
ACK = (
    "This work makes use of data products provided by the Ecosystem Sciences Division (ESD), Pacific Islands Fisheries "
    "Science Center (PIFSC), NOAA, with funding support from the NOAA Coral Reef Conservation Program (CRCP)."
)
STATION_UNCERTAINTY_M = 50.0  # handheld GPS (5-10 m) + buoy offset + two 18 m transects around the buoy (research)
FT_TO_M = 0.3048
MAX_DEPTH_M = 200.0  # NCRMP photo-quadrats are shot at 0-30 m; anything deeper is a data error, not a depth
BOX = (-20.0, 30.0)  # latitude sanity range: Samoa 14.6 S ... Kure 28.5 N
LON_RANGES = ((140.0, 180.0), (-180.0, -150.0))  # Marianas (144.6 E) across the antimeridian to Hawaii (154.8 W)
LISTING_TIMEOUT_S = 600
MAX_DIRS_PER_ACCESSION = 6000
MAX_DEPTH_LEVELS = 12
SKIP_DIRS = {"datadocumentation", "documentation"}
AREAS = ("hawaii", "marianas", "samoa", "pria")
AREA_ALIASES = {
    "hawaii": "hawaii", "hawaiʻi": "hawaii", "mhi": "hawaii", "nwhi": "hawaii", "hawaiian": "hawaii",
    "marianas": "marianas", "mari": "marianas", "marian": "marianas", "guam": "marianas", "cnmi": "marianas",
    "samoa": "samoa", "american_samoa": "samoa", "pria": "pria", "pacific_remote_islands": "pria",
}  # fmt: skip
ORDERS = ("spread", "table")
DEPTH_MODES = ("cover", "off")
KINDS = ("all", "climate", "strs")
DEFAULT_FRAMES_PER_VISIT = 3
DEFAULT_CLIMATE_SHARE = 0.25

# Image names: SITE_YEAR_R_NN.JPG (R = REPLICATE letter), SITE_YEAR_NN.JPG (climate 2019+), SITE_YEAR__NN.JPG (empty
# replicate, 0176286), SITE_YEAR_NN_original.JPG (the unprocessed twin of 30 images of 0270550).
NAME_RE = re.compile(
    r"^(?P<site>.+?)_(?P<year>\d{4})_(?:(?P<rep>[A-Za-z]?)_)?(?P<photo>\d{1,3})(?P<variant>_original)?\.jpe?g$", re.IGNORECASE
)


@dataclass(frozen=True)
class Acc:
    """One NCEI accession of NCRMP Pacific benthic images (research/noaa_ncrmp.md, table of 2026-10-06)."""

    acc: str
    path: str  # <arc>/<acc>/<ver>
    kind: str  # climate | strs
    year: int
    area: str  # hawaii | marianas | samoa | pria (sampling stratum and cover table)
    detail: str  # region as NCEI words it
    images: int
    gb: float
    first: str  # first / last survey date
    last: str
    site_info: tuple[str, ...]
    approx: bool = False  # image count is an estimate (nested cruise trees 0176286, 0176288)
    inport: str = "71813"  # InPort collection record (71813 climate, 71814 StRS, 59193 bleaching 2019)

    @property
    def root_url(self) -> str:
        return f"{ARCHIVE}/{self.path}/data/0-data/"

    @property
    def landing(self) -> str:
        return LANDING.format(acc=self.acc)

    @property
    def kind_title(self) -> str:
        return "Climate Stations" if self.kind == "climate" else "Stratified Random Sites (StRS)"


def _a(acc, path, kind, year, area, detail, images, gb, first, last, *site_info, approx=False, inport=None) -> Acc:
    return Acc(acc, path, kind, year, area, detail, images, gb, first, last, tuple(site_info), approx,
               inport or ("71813" if kind == "climate" else "71814"))  # fmt: skip


ACCESSIONS: tuple[Acc, ...] = (
    # climate stations (fixed sites): 17 accessions, 20,068 images, 167.6 GB
    _a("0159172", "arc0106/0159172/1.1", "climate", 2013, "hawaii", "Hawaiian Archipelago (MHI + NWHI)", 2205, 6.9, "2013-07-12", "2013-10-30", "Site_Info_HAWAII_2013.csv"),
    _a("0157759", "arc0104/0157759/1.1", "climate", 2014, "marianas", "Mariana Archipelago", 1373, 5.0, "2014-03-25", "2014-05-05", "Site Info MARIAN 2014.csv"),
    _a("0159139", "arc0104/0159139/1.1", "climate", 2014, "pria", "Pacific Remote Island Areas (Wake)", 216, 0.7, "2014-03-16", "2014-03-19", "Site_Info_PRIAs_2014.csv"),
    _a("0159170", "arc0104/0159170/1.1", "climate", 2015, "samoa", "American Samoa", 1439, 4.7, "2015-02-15", "2015-03-26", "Site Info SAMOA 2015.csv"),
    _a("0159155", "arc0104/0159155/1.1", "climate", 2015, "pria", "Pacific Remote Island Areas", 1216, 3.7, "2015-01-26", "2015-04-27", "Site_Info_PRIAs_2015.csv"),
    _a("0164296", "arc0111/0164296/1.1", "climate", 2016, "hawaii", "Hawaiian Archipelago", 656, 2.6, "2016-07-17", "2016-09-21", "Site_Info_HAWAII_2016.csv"),
    _a("0202138", "arc0145/0202138/1.1", "climate", 2017, "marianas", "Mariana Archipelago", 947, 3.9, "2017-05-03", "2017-06-21", "SiteInfo_Marianas_2017.csv"),
    _a("0202139", "arc0145/0202139/1.1", "climate", 2017, "pria", "Pacific Remote Island Areas (Wake)", 57, 0.2, "2017-04-19", "2017-04-20", "SiteInfo_Wake_2017.csv"),
    _a("0187561", "arc0135/0187561/1.1", "climate", 2018, "samoa", "American Samoa", 894, 10.2, "2018-06-19", "2018-07-16", "Site_Info_SAMOA_2018.csv"),
    _a("0187562", "arc0135/0187562/1.1", "climate", 2018, "pria", "Pacific Remote Island Areas", 704, 7.8, "2018-06-08", "2018-08-10", "Site_Info_PRIAs_2018.csv"),
    _a("0240600", "arc0188/0240600/1.1", "climate", 2019, "hawaii", "Hawaiian Archipelago (MHI + NWHI)", 1893, 21.9, "2019-04-26", "2019-09-04", "Benthic_Image_Site_Info_MHI.csv", "Benthic_Image_Site_Info_NWHI.csv"),
    _a("0279443", "arc0219/0279443/1.1", "climate", 2022, "marianas", "Mariana Archipelago", 1891, 22.0, "2022-04-12", "2022-08-06", "NCRMP_CLIMATE_SITEINFO_MARIAN_2022.csv"),
    _a("0289892", "arc0223/0289892/1.1", "climate", 2023, "samoa", "American Samoa", 1137, 13.7, "2023-06-30", "2023-08-08", "NCRMP_CLIMATE_SITEINFO_SAMOA_2023.csv"),
    _a("0289907", "arc0226/0289907/1.1", "climate", 2023, "pria", "Pacific Remote Island Areas", 449, 4.8, "2023-03-15", "2023-03-19", "NCRMP_CLIMATE_SITEINFO_PRIA_2023.csv"),
    _a("0317534", "arc0247/0317534/1.1", "climate", 2024, "hawaii", "Hawaiian Archipelago", 2577, 30.7, "2024-05-29", "2024-08-27", "NCRMP_CLIMATE_SITEINFO_HAWAII_2024.csv"),
    _a("0317752", "arc0247/0317752/1.1", "climate", 2025, "pria", "Pacific Remote Island Areas (Wake)", 300, 3.4, "2025-04-03", "2025-04-08", "NCRMP_CLIMATE_SITEINFO_PRIA_2025.csv"),
    _a("0317786", "arc0247/0317786/1.1", "climate", 2025, "marianas", "Mariana Archipelago", 2114, 25.4, "2025-05-09", "2025-06-28", "NCRMP_CLIMATE_SITEINFO_MARIAN_2025.csv"),
    # stratified random sites: 21 accessions, 176,597 counted + about 20,600 estimated images, 1.41 TB
    _a("0159144", "arc0104/0159144/1.1", "strs", 2013, "hawaii", "Hawaiian Archipelago", 12628, 39.4, "2013-04-30", "2013-10-31", "Site_Info_HAWAII_2013.csv"),
    _a("0159142", "arc0104/0159142/1.1", "strs", 2014, "marianas", "Mariana Archipelago", 13326, 40.5, "2014-03-25", "2014-05-07", "Site_Info_MARIAN_2014.csv"),
    _a("0159157", "arc0104/0159157/1.1", "strs", 2014, "pria", "Pacific Remote Island Areas (Wake)", 599, 1.3, "2014-03-16", "2014-03-20", "Site_Info_PRIAs_2014.csv"),
    _a("0159168", "arc0103/0159168/2.2", "strs", 2015, "samoa", "American Samoa", 17387, 74.1, "2015-02-15", "2015-11-13", "Site_Info_SAMOA_2015.csv"),
    _a("0159153", "arc0104/0159153/1.1", "strs", 2015, "pria", "Pacific Remote Island Areas", 13271, 55.9, "2015-01-26", "2015-04-28", "Site_Info_PRIAs_2015.csv"),
    _a("0268773", "arc0208/0268773/1.1", "strs", 2015, "hawaii", "Main Hawaiian Islands (Reef Fish cruise HA1503)", 10259, 38.7, "2015-06-15", "2015-07-02", "MHI_RFS_PQ_siteinfo_2015.csv"),
    _a("0276273", "arc0211/0276273/1.1", "strs", 2015, "hawaii", "Northwestern Hawaiian Islands (PMNM RAMP HA1505)", 4159, 16.3, "2015-07-30", "2015-08-21", "NWHI_PMNM_PQ_siteinfo_2015.csv"),
    _a("0164293", "arc0111/0164293/1.1", "strs", 2016, "hawaii", "Hawaiian Archipelago", 19667, 93.2, "2016-07-13", "2016-09-27", "Site_Info_HAWAII_2016.csv"),
    _a("0176287", "arc0125/0176287/1.1", "strs", 2016, "pria", "Pacific Remote Island Areas (Jarvis)", 1751, 7.9, "2016-05-16", "2016-05-22", "Site_Info_PRIAs_2016.csv"),
    _a("0176286", "arc0190/0176286/1.1", "strs", 2017, "marianas", "Mariana Archipelago", 15200, 104.2, "2017-05-03", "2017-06-21", "Site_Info_MARIAN_2017.csv", approx=True),
    _a("0176288", "arc0190/0176288/1.1", "strs", 2017, "pria", "Pacific Remote Island Areas (Wake, Baker, Howland, Jarvis)", 5400, 38.4, "2017-04-02", "2017-04-23", "Site_Info_PRIAs_2017.csv", approx=True),
    _a("0187563", "arc0180/0187563/1.1", "strs", 2018, "samoa", "American Samoa", 7008, 76.4, "2018-06-19", "2018-07-18", "Site_Info_SAMOA_2018.csv"),
    _a("0187564", "arc0180/0187564/1.1", "strs", 2018, "pria", "Pacific Remote Island Areas", 7964, 74.8, "2018-06-08", "2018-08-11", "Site_Info_PRIAs_2018.csv"),
    _a("0211063", "arc0157/0211063/1.1", "strs", 2019, "hawaii", "Main Hawaiian Islands", 14445, 122.4, "2019-04-21", "2019-10-31", "Site_Info_HAWAII_2019.csv"),
    _a("0279441", "arc0219/0279441/1.1", "strs", 2022, "marianas", "Mariana Archipelago", 13450, 155.9, "2022-04-12", "2022-08-10", "NCRMP_STRS_SITEINFO_MARIAN_2022.csv"),
    _a("0289904", "arc0223/0289904/1.1", "strs", 2023, "pria", "Pacific Remote Island Areas", 1721, 19.9, "2023-03-15", "2023-05-07", "NCRMP_STRS_SITEINFO_PRIAS_2023.csv"),
    _a("0289905", "arc0223/0289905/1.1", "strs", 2023, "samoa", "American Samoa", 9139, 100.1, "2023-03-30", "2023-08-09", "NCRMP_STRS_SITEINFO_SAMOA_2023.csv"),
    _a("0317535", "arc0247/0317535/1.1", "strs", 2024, "hawaii", "Hawaiian Archipelago", 13165, 151.9, "2024-05-13", "2024-08-27", "NCRMP_STRS_SITEINFO_HAWAII_2024.csv"),
    _a("0317753", "arc0247/0317753/1.1", "strs", 2025, "pria", "Pacific Remote Island Areas (Wake)", 1051, 12.0, "2025-04-03", "2025-04-08", "NCRMP_STRS_SITEINFO_PRIA_2025.csv"),
    _a("0317785", "arc0248/0317785/1.1", "strs", 2025, "marianas", "Mariana Archipelago", 11796, 148.5, "2025-04-23", "2025-06-27", "NCRMP_STRS_SITEINFO_MARIAN_2025.csv"),
    _a("0270550", "arc0209/0270550/1.1", "strs", 2019, "hawaii", "Main Hawaiian Islands (2019 bleaching event)", 3811, 34.1, "2019-10-08", "2019-11-14", "ESD_SiteInfo_MHI_BLEA_2019.csv", inport="59193"),
)  # fmt: skip
ACC_BY_ID: dict[str, Acc] = {a.acc: a for a in ACCESSIONS}

# Benthic-cover tables (CoralNet point annotations, one row per point): the depth source (and coordinate fallback).
COVER_BASE = ARCHIVE + "/{path}/data/0-data/{name}"
COVER_TABLES: dict[str, tuple[str, str, str]] = {  # table id -> (NCEI accession, path, file)
    "fixed": ("0317416", "arc0247/0317416/1.1", "NCRMP_BENTHIC_COVER_FIXED_PACIFIC_2012-2025.csv"),
    "hawaii": ("0317464", "arc0247/0317464/2.2", "NCRMP_BENTHIC_COVER_STRS_HAWAII_2015-2024.csv"),
    "marianas": ("0317464", "arc0247/0317464/2.2", "NCRMP_BENTHIC_COVER_STRS_MARI_2017-2025.csv"),
    "pria": ("0317464", "arc0247/0317464/2.2", "NCRMP_BENTHIC_COVER_STRS_PRIA_2012-2025.csv"),
    "samoa": ("0317464", "arc0247/0317464/2.2", "NCRMP_BENTHIC_COVER_STRS_SAMOA_2010-2025.csv"),
}
COVER_FIELDS = ("KEY", "SITE", "SITEVISITID", "LATITUDE", "LONGITUDE", "MIN_DEPTH", "MAX_DEPTH", "DEPTH_SOURCE", "ROWS")

MONTHS = {m: i for i, m in enumerate(("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1)}


# --------------------------------------------------------------------------------------------- pure helpers
def parse_name(name: str) -> dict[str, Any] | None:
    """``{site, year, rep, photo, variant}`` of an image file name, or None. ``site`` is upper case."""
    m = NAME_RE.match(name.strip())
    if not m:
        return None
    return {
        "site": m["site"].strip().upper(),
        "year": int(m["year"]),
        "rep": (m["rep"] or "").upper(),
        "photo": int(m["photo"]),
        "variant": "original" if m["variant"] else "",
    }


def parse_survey_date(text: object) -> str | None:
    """ISO date of a site-info ``DATE_`` value: ``05-SEP-13``, ``15-Aug-16``, ``"10-Aug-24"``, ``7/10/2018``
    (month first), ``8/28/2019 0:00``, ``29-APR-22 11.42.31``, ``2018-07-10``. None when it does not parse."""
    s = str(text or "").strip().strip('"').strip()
    if not s:
        return None
    m = re.match(r"^(\d{1,2})-([A-Za-z]{3})[A-Za-z]*-(\d{4}|\d{2})\b", s)
    if m:
        d, mon, y = int(m[1]), MONTHS.get(m[2].upper()), m[3]
    else:
        m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})\b", s)
        if m:
            mon, d, y = int(m[1]), int(m[2]), m[3]
        else:
            m = re.match(r"^(\d{4})-(\d{2})-(\d{2})\b", s)
            if not m:
                return None
            y, mon, d = m[1], int(m[2]), int(m[3])
    if mon is None:
        return None
    year = int(y) + (2000 if len(y) == 2 else 0)
    try:
        return date(year, mon, d).isoformat()
    except ValueError:
        return None


def _size(text: str) -> int | None:
    """Approximate bytes of an Apache listing size column (``13M``, ``9.6M``, ``395``, ``-``)."""
    m = re.match(r"^\s*([\d.]+)\s*([KMGT]?)\s*$", text or "")
    if not m:
        return None
    return int(float(m[1]) * {"": 1, "K": 1 << 10, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40}[m[2]])


@dataclass(frozen=True)
class Entry:
    """One row of an Apache ``mod_autoindex`` listing."""

    name: str
    url: str
    is_dir: bool
    size: int | None  # approximate (the listing rounds)


_ROW_RE = re.compile(r'<td><a href="(?P<href>[^"]+)">(?P<text>[^<]*)</a></td><td[^>]*>[^<]*</td><td[^>]*>(?P<size>[^<]*)</td>')


def parse_listing(text: str, base_url: str) -> list[Entry]:
    """Rows of an NCEI directory listing (parent-directory and sort links are skipped)."""
    out: list[Entry] = []
    for m in _ROW_RE.finditer(text):
        href = html.unescape(m["href"])
        if href.startswith(("/", "?", "#")) or "://" in href:
            continue
        is_dir = href.endswith("/")
        name = unquote(href.rstrip("/"))
        out.append(Entry(name=name, url=urljoin(base_url, href), is_dir=is_dir, size=None if is_dir else _size(m["size"])))
    return out


def is_site_info(name: str) -> bool:
    n = re.sub(r"[\s_\-]+", "", name.lower())
    return n.endswith(".csv") and "siteinfo" in n and "datadictionary" not in n


def _safe(segment: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]", "_", segment).lstrip(".") or "_"
    return s if s == segment else f"{s}-{hashlib.sha1(segment.encode()).hexdigest()[:6]}"


@lru_cache(maxsize=512)
def pick_order(n: int) -> tuple[int, ...]:
    """Frame indices of a visit with ``n`` frames: the centre first, then van der Corput fractions (1/4, 3/4, 1/8, ...).

    Every prefix is evenly spread over the visit and avoids the first and last frames (slate, transect markers).
    """
    out: list[int] = []
    seen: set[int] = set()
    m = 1
    while len(out) < n and m <= 64 * n + 64:
        f, x, w = 0.0, m, 0.5
        while x:
            f += (x & 1) * w
            x >>= 1
            w /= 2
        i = min(n - 1, int(f * n))
        if i not in seen:
            seen.add(i)
            out.append(i)
        m += 1
    out.extend(i for i in range(n) if i not in seen)
    return tuple(out)


def spread_order(n: int) -> list[int]:
    """0..n-1 in a spread order (first, last, middle, quarters, ...): any prefix is evenly spaced."""
    if n <= 2:
        return list(range(n))
    bits = (n - 1).bit_length()
    return sorted(range(n), key=lambda i: int(format(i, f"0{bits}b")[::-1], 2))


def interleave(streams: list[tuple[float, Iterator[Any]]]) -> Iterator[Any]:
    """Weighted round robin: always pull from the stream with the smallest (served + 1) / weight."""
    live = [[max(w, 1e-9), it, 0] for w, it in streams]
    while live:
        best = min(range(len(live)), key=lambda i: ((live[i][2] + 1) / live[i][0], i))
        try:
            item = next(live[best][1])
        except StopIteration:
            live.pop(best)
            continue
        live[best][2] += 1
        yield item


# ------------------------------------------------------------------------------------------- site-info CSVs
@dataclass(frozen=True)
class SiteRow:
    codes: tuple[tuple[str, str], ...]  # (column, upper-case code) for SITE / OCC_SITEID
    lat: float | None
    lon: float | None
    date: str | None
    file: str


class SiteIndex:
    """The site-info rows of one accession, indexed by every id column (``SITE`` and ``OCC_SITEID``)."""

    def __init__(self) -> None:
        self.rows: list[SiteRow] = []
        self.by_code: dict[str, list[tuple[SiteRow, str]]] = {}

    def add(self, rows: Iterable[SiteRow]) -> None:
        for r in rows:
            self.rows.append(r)
            for col, code in r.codes:
                bucket = self.by_code.setdefault(code, [])
                if all(x[0] is not r for x in bucket):
                    bucket.append((r, col))

    def __contains__(self, code: str) -> bool:
        return code.upper() in self.by_code

    def find(self, code: str, year: int | None = None) -> list[tuple[SiteRow, str]]:
        hits = self.by_code.get(code.upper(), [])
        if len(hits) > 1 and year:
            same_year = [h for h in hits if h[0].date and h[0].date.startswith(str(year))]
            if same_year:
                return same_year
        return hits


def parse_site_info(text: str, filename: str) -> list[SiteRow]:
    """Rows of a site-info CSV (BOM, quoting and CRLF vary; rows without a site code are skipped)."""
    reader = csv.reader(io.StringIO(text.lstrip("﻿"), newline=""))
    header = next(reader, None)
    if not header:
        return []
    cols = {h.strip().strip('"').strip().upper(): i for i, h in enumerate(header)}
    id_cols = [c for c in ("SITE", "OCC_SITEID") if c in cols]
    date_col = "DATE_" if "DATE_" in cols else ("DATE" if "DATE" in cols else None)
    out: list[SiteRow] = []

    def cell(row: list[str], col: str | None) -> str:
        i = cols.get(col) if col else None
        return row[i].strip().strip('"').strip() if i is not None and i < len(row) else ""

    for row in reader:
        codes = tuple((c, cell(row, c).upper()) for c in id_cols if cell(row, c))
        if not codes:
            continue
        lat, lon = to_float(cell(row, "LATITUDE")), to_float(cell(row, "LONGITUDE"))
        if lat is None or lon is None or abs(lat) > 90 or abs(lon) > 180:
            lat = lon = None
        else:
            lat, lon = round(lat, 6), round(lon, 6)
        out.append(SiteRow(codes, lat, lon, parse_survey_date(cell(row, date_col)), filename))
    return out


def in_pacific_box(lat: float, lon: float) -> bool:
    return BOX[0] <= lat <= BOX[1] and any(lo <= lon <= hi for lo, hi in LON_RANGES)


# --------------------------------------------------------------------------------------- cover tables (depth)
@dataclass(frozen=True)
class CoverRec:
    site: str
    visit_id: str
    lat: float | None
    lon: float | None
    min_depth: float | None  # feet
    max_depth: float | None
    depth_source: str
    rows: int


def reduce_cover(lines: Iterable[str]) -> tuple[str, int]:
    """Reduce a benthic-cover CSV (one row per annotated point) to one row per ``<SITE>_<YEAR>`` of ``IMAGE_NAME``.

    Depth and position are constant per site visit. When the rows of one key disagree (different depth or
    position), that value is left empty rather than guessed. Returns (reduced CSV text, number of input rows).
    """
    reader = csv.reader(lines)
    header = next(reader, None)
    if not header:
        return ",".join(COVER_FIELDS) + "\r\n", 0
    col = {h.strip().strip('"').strip().upper(): i for i, h in enumerate(header)}
    for need in ("IMAGE_NAME", "MIN_DEPTH", "MAX_DEPTH"):
        if need not in col:
            raise ValueError(f"cover table without column {need}")

    def get(row: list[str], name: str) -> str:
        i = col.get(name)
        return row[i].strip() if i is not None and i < len(row) else ""

    keys: dict[str, dict[str, Any]] = {}
    n = 0
    for row in reader:
        n += 1
        parsed = parse_name(get(row, "IMAGE_NAME"))
        if not parsed:
            continue
        key = f"{parsed['site']}_{parsed['year']}"
        rec = keys.get(key)
        if rec is None:
            rec = keys[key] = {"site": get(row, "SITE"), "visit": get(row, "SITEVISITID"), "depth": set(), "pos": set(), "src": set(), "rows": 0}
        rec["rows"] += 1
        rec["depth"].add((get(row, "MIN_DEPTH"), get(row, "MAX_DEPTH")))
        rec["pos"].add((get(row, "LATITUDE"), get(row, "LONGITUDE")))
        rec["src"].add(get(row, "DEPTH_SOURCE"))
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerow(COVER_FIELDS)
    for key in sorted(keys):
        r = keys[key]
        depth = next(iter(r["depth"])) if len(r["depth"]) == 1 else ("", "")
        pos = next(iter(r["pos"])) if len(r["pos"]) == 1 else ("", "")
        src = next(iter(r["src"])) if len(r["src"]) == 1 else ""
        w.writerow([key, r["site"], r["visit"] if r["rows"] else "", pos[0], pos[1], depth[0], depth[1], src, r["rows"]])
    return out.getvalue(), n


def load_cover(text: str) -> dict[str, CoverRec]:
    out: dict[str, CoverRec] = {}
    for row in csv.DictReader(io.StringIO(text, newline="")):
        lat, lon = to_float(row.get("LATITUDE")), to_float(row.get("LONGITUDE"))
        if lat is None or lon is None or abs(lat) > 90 or abs(lon) > 180:
            lat = lon = None
        out[(row.get("KEY") or "").upper()] = CoverRec(
            site=row.get("SITE") or "",
            visit_id=row.get("SITEVISITID") or "",
            lat=lat,
            lon=lon,
            min_depth=depth_from(row.get("MIN_DEPTH")),
            max_depth=depth_from(row.get("MAX_DEPTH")),
            depth_source=row.get("DEPTH_SOURCE") or "",
            rows=int(to_float(row.get("ROWS")) or 0),
        )
    return out


def depth_m_of(rec: CoverRec | None) -> float | None:
    """mean(MIN_DEPTH, MAX_DEPTH) feet -> metres, one decimal. None when no value or an implausible one."""
    if rec is None:
        return None
    vals = [v for v in (rec.min_depth, rec.max_depth) if v is not None]
    if not vals:
        return None
    d = round(sum(vals) / len(vals) * FT_TO_M, 1)
    return d if 0 <= d <= MAX_DEPTH_M else None


# ---------------------------------------------------------------------------------------------- the plan
@dataclass
class _Frame:
    name: str
    url: str
    size: int | None
    site: str | None  # upper-case site code, None when the name does not parse
    year: int | None
    rep: str
    photo: int | None
    variant: str = ""


@dataclass
class _Visit:
    site: str  # upper-case site code (the whole name for a file that does not parse)
    date: str | None
    frames: list[_Frame] | None  # None: nested site folder, listed on first use
    dirs: list[str] = field(default_factory=list)


@dataclass
class _Scan:
    files: list[tuple[str, str]]  # site-info CSVs: (file name, url)
    frames: list[_Frame]
    visit_dirs: dict[str, list[str]]  # site code -> folder urls (lazy visits of a cruise tree)
    dirs_listed: int = 0


def _frame_of(e: Entry) -> _Frame:
    p = parse_name(e.name)
    return _Frame(
        e.name, e.url, e.size, p["site"] if p else None, p["year"] if p else None, p["rep"] if p else "", p["photo"] if p else None,
        p["variant"] if p else "",
    )


def drop_variants(frames: list[_Frame]) -> list[_Frame]:
    """Frames without the slate (photo 0) and without ``_original`` twins of an image that is listed as well."""
    plain = {(f.site, f.year, f.rep, f.photo) for f in frames if not f.variant}
    return [f for f in frames if f.photo != 0 and not (f.variant and (f.site, f.year, f.rep, f.photo) in plain)]


# ----------------------------------------------------------------------------------------------- licence
def parse_iso_constraints(xml_text: str) -> list[str]:
    """``useLimitation`` / ``otherConstraints`` texts of an NCEI ISO 19115-2 record (document order, deduplicated)."""
    if "<!ENTITY" in xml_text or len(xml_text) > 8_000_000:
        raise ValueError("refusing an XML document with entities or over 8 MB")
    gmd = "http://www.isotc211.org/2005/gmd"
    root = ET.fromstring(xml_text)
    out: list[str] = []
    for tag in ("useLimitation", "otherConstraints"):
        for el in root.iter(f"{{{gmd}}}{tag}"):
            text = " ".join("".join(el.itertext()).split())
            if text and text not in out:
                out.append(text)
    return out


def short_citation(cite: str, acc: str) -> str:
    """The accession's own citation from a "Cite as:" line, up to its landing URL (no "In ... [indicate subset]" tail)."""
    text = re.sub(r"(?i)^cite as:\s*", "", cite).strip()
    m = re.match(rf"^(.*?/archive/accession/{re.escape(acc)})\.?", text)
    if m:
        return m[1] + "."
    return re.sub(r"\s*Accessed \[date\]\.?\s*$", "", text)


# ----------------------------------------------------------------------------------------------- adapter
@register
class NoaaNcrmpAdapter(Adapter):
    key = "noaa_ncrmp"
    name = "NOAA NCRMP benthic photo-quadrats, US Pacific (PIFSC ESD, NCEI)"
    homepage = "https://www.fisheries.noaa.gov/inport/item/71813"
    citation = (
        "Ecosystem Sciences Division, Pacific Islands Fisheries Science Center, NOAA: National Coral Reef Monitoring "
        "Program, Benthic Images (38 NCEI accessions, 2013-2025; InPort 71813, 71814, 59193); see each sample's "
        "attribution for the accession's own citation"
    )
    media_types = ("image",)
    env_vars: tuple[str, ...] = ()
    manual_steps = (
        "None. Anonymous HTTPS, no token. The default frames_per_visit=3 takes about 22 k images (about 200 GB); "
        "frames_per_visit=all is the whole archive: about 0.22 M images, 1.57 TB. Optional: ask PIFSC ESD (InPort 71813 "
        "steward) for the 2010-2012 RAMP photo-quadrats, which exist but are not at NCEI."
    )
    host_intervals = {"www.ncei.noaa.gov": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._scans: dict[str, _Scan | None] = {}
        self._index: dict[str, SiteIndex] = {}
        self._plans: dict[str, list[_Visit]] = {}
        self._orders: dict[str, list[int]] = {}
        self._licences: dict[str, Licence] = {}
        self._covers: dict[str, dict[str, CoverRec] | None] = {}
        self._bad_urls: set[str] = set()

    # ---------------------------------------------------------------- options
    def _list(self, name: str) -> list[str]:
        v = self.options.get(name)
        if v in (None, ""):
            return []
        if isinstance(v, (str, int)):
            v = str(v).split(",")
        return [str(x).strip() for x in v if str(x).strip()]

    def _acc_ids(self) -> list[str]:
        out = []
        for x in self._list("accessions"):
            x = x.removeprefix("NCEI").strip()
            out.append(x.zfill(7) if x.isdigit() else x)
        return out

    def _frames_per_visit(self) -> int | None:
        v = self.options.get("frames_per_visit", DEFAULT_FRAMES_PER_VISIT)
        if isinstance(v, str) and v.strip().lower() in ("all", "0", ""):
            return None
        if v in (0, None):
            return None
        return max(1, int(v))

    def _climate_share(self) -> float:
        return float(self.options.get("climate_share", DEFAULT_CLIMATE_SHARE))

    def _areas(self) -> set[str]:
        return {AREA_ALIASES.get(a.lower(), a.lower()) for a in self._list("regions")}

    def check_ready(self) -> list[str]:
        problems = super().check_ready()
        o = self.options
        if str(o.get("order", "spread")).lower() not in ORDERS:
            problems.append(f"option order={o.get('order')!r} must be one of {', '.join(ORDERS)}")
        if str(o.get("depth", "cover")).lower() not in DEPTH_MODES:
            problems.append(f"option depth={o.get('depth')!r} must be one of {', '.join(DEPTH_MODES)}")
        if str(o.get("kind", "all")).lower() not in KINDS:
            problems.append(f"option kind={o.get('kind')!r} must be one of {', '.join(KINDS)}")
        try:
            self._frames_per_visit()
        except (TypeError, ValueError):
            problems.append(f"option frames_per_visit={o.get('frames_per_visit')!r} must be an integer or 'all'")
        try:
            if not 0.0 < self._climate_share() < 1.0:
                problems.append("option climate_share must be between 0 and 1")
        except (TypeError, ValueError):
            problems.append(f"option climate_share={o.get('climate_share')!r} is not a number")
        bad = [a for a in self._acc_ids() if a not in ACC_BY_ID]
        if bad:
            problems.append(f"unknown accession(s) {', '.join(bad)} (see ACCESSIONS in the adapter; 38 are known)")
        badr = [a for a in self._areas() if a not in AREAS]
        if badr:
            problems.append(f"unknown region(s) {', '.join(sorted(badr))}; use {', '.join(AREAS)}")
        try:
            [int(y) for y in self._list("years")]
        except ValueError:
            problems.append("option years must be integers, e.g. 2019,2024")
        for k in ("from", "to"):
            if o.get(k) and not parse_survey_date(o.get(k)):
                problems.append(f"option {k}={o.get(k)!r} is not an ISO date (YYYY-MM-DD)")
        return problems

    def selected_accessions(self) -> list[Acc]:
        ids = self._acc_ids()
        kind = str(self.options.get("kind", "all")).lower()
        areas = self._areas()
        years = {int(y) for y in self._list("years")}
        lo, hi = parse_survey_date(self.options.get("from")), parse_survey_date(self.options.get("to"))
        out = []
        for a in ACCESSIONS:
            if ids and a.acc not in ids:
                continue
            if kind != "all" and a.kind != kind:
                continue
            if areas and a.area not in areas:
                continue
            if years and a.year not in years:
                continue
            if lo and a.last < lo or hi and a.first > hi:
                continue
            out.append(a)
        return out

    # ---------------------------------------------------------------- estimate
    def estimate(self) -> dict[str, Any]:
        sel = self.selected_accessions()
        images = sum(a.images for a in sel)
        k = self._frames_per_visit()
        return {
            "accessions": len(sel),
            "climate_accessions": sum(1 for a in sel if a.kind == "climate"),
            "strs_accessions": sum(1 for a in sel if a.kind == "strs"),
            "images_in_accessions": images,
            "images_estimated_counts": sum(a.images for a in sel if a.approx),
            "approx_gb_all_images": round(sum(a.gb for a in sel), 1),
            "frames_per_visit": "all" if k is None else k,
            "note": "about 7,300 site visits of about 30 frames in all 38 accessions; the default takes 3 frames per visit",
        }

    # --------------------------------------------------------------- listings
    def _listing_name(self, acc: Acc, url: str) -> str:
        root = acc.root_url
        rel = unquote(url[len(root):] if url.startswith(root) else urlparse(url).path)
        segs = [_safe(s) for s in rel.strip("/").split("/") if s] or ["_root"]
        return f"listing/{acc.acc}/" + "/".join([*segs[:-1], segs[-1] + ".html"])

    def _listing(self, acc: Acc, url: str) -> list[Entry] | None:
        if url in self._bad_urls:
            return None
        try:
            text = self.ctx.cached_text(url, self._listing_name(acc, url), timeout=LISTING_TIMEOUT_S)
        except (HttpError, OSError) as exc:
            self._bad_urls.add(url)
            self.ctx.fail(acc.acc, "listing", f"directory listing not read: {url}: {exc}")
            return None
        return parse_listing(text, url)

    def _site_files(self, acc: Acc) -> list[tuple[str, str]]:
        """The site-info CSVs of an accession: (file name, url). Files named in the research table win, else any ``*siteinfo*.csv``."""
        rows = self._listing(acc, acc.root_url) or []
        csvs = [(e.name, e.url) for e in rows if not e.is_dir and is_site_info(e.name)]
        known = [c for c in csvs if c[0] in acc.site_info]
        if known:
            return known
        if csvs:
            return csvs
        return [(n, acc.root_url + quote(n)) for n in acc.site_info]

    def _siteinfo(self, acc: Acc) -> SiteIndex:
        if acc.acc in self._index:
            return self._index[acc.acc]
        idx = SiteIndex()
        for fname, url in self._site_files(acc):
            if url in self._bad_urls:
                continue
            try:
                text = self.ctx.cached_text(url, f"siteinfo/{acc.acc}/{_safe(fname)}", timeout=120)
            except (HttpError, OSError) as exc:
                self._bad_urls.add(url)
                self.ctx.fail(acc.acc, "site_info", f"site-info CSV not read: {url}: {exc}")
                continue
            idx.add(parse_site_info(text, fname))
        if not idx.rows:
            self.ctx.fail(acc.acc, "site_info", "no site-info rows: every frame of this accession gets geo none unless the cover table knows its site")
        self._index[acc.acc] = idx
        return idx

    def _scan(self, acc: Acc) -> _Scan | None:
        """Depth-first walk of ``0-data/``: image files, and the lazy site folders of a cruise tree."""
        if acc.acc in self._scans:
            return self._scans[acc.acc]
        root_rows = self._listing(acc, acc.root_url)
        if root_rows is None:
            self._scans[acc.acc] = None
            return None
        idx = self._siteinfo(acc)
        scan = _Scan(files=self._site_files(acc), frames=[], visit_dirs={}, dirs_listed=1)
        stack: list[tuple[list[Entry], int]] = [(root_rows, 0)]
        seen_names: set[str] = set()
        while stack:
            rows, depth = stack.pop()
            subdirs: list[tuple[Entry, int]] = []
            for e in rows:
                if e.is_dir:
                    if e.name.lower() in SKIP_DIRS or depth >= MAX_DEPTH_LEVELS:
                        continue
                    if e.name.upper() in idx:
                        scan.visit_dirs.setdefault(e.name.upper(), []).append(e.url)
                    else:
                        subdirs.append((e, depth + 1))
                elif e.name.lower().endswith((".jpg", ".jpeg")) and e.name.upper() not in seen_names:
                    seen_names.add(e.name.upper())
                    scan.frames.append(_frame_of(e))
            # preserve listing order: the stack pops the last pushed first
            for e, d in reversed(subdirs):
                if scan.dirs_listed >= MAX_DIRS_PER_ACCESSION:
                    self.ctx.fail(acc.acc, "listing", f"more than {MAX_DIRS_PER_ACCESSION} directories: walk stopped")
                    stack.clear()
                    break
                sub = self._listing(acc, e.url)
                scan.dirs_listed += 1
                if sub is not None:
                    stack.append((sub, d))
        self._scans[acc.acc] = scan
        return scan

    def _folder_frames(self, acc: Acc, url: str, seen: set[str], depth: int = 0) -> list[_Frame]:
        """All images under one site folder of a cruise tree (PHOTO_QUADS/, PHOTO_QUADS/A/, ...)."""
        rows = self._listing(acc, url)
        out: list[_Frame] = []
        for e in rows or []:
            if e.is_dir:
                if depth < MAX_DEPTH_LEVELS and e.name.lower() not in SKIP_DIRS:
                    out.extend(self._folder_frames(acc, e.url, seen, depth + 1))
            elif e.name.lower().endswith((".jpg", ".jpeg")) and e.name.upper() not in seen:
                seen.add(e.name.upper())
                out.append(_frame_of(e))
        return out

    # ------------------------------------------------------------------- plan
    def _visits(self, acc: Acc) -> list[_Visit]:
        """The site visits of an accession in the spread order (sorted by survey date, then first / last / middle ...)."""
        if acc.acc in self._plans:
            return self._plans[acc.acc]
        scan = self._scan(acc)
        visits: list[_Visit] = []
        if scan is not None:
            idx = self._siteinfo(acc)

            def date_of(site: str) -> str | None:
                dates = [r.date for r, _ in idx.find(site) if r.date]
                return min(dates) if dates else None

            groups: dict[str, list[_Frame]] = {}
            for f in drop_variants(scan.frames):
                groups.setdefault(f.site or f.name.upper(), []).append(f)
            for site, frames in groups.items():
                visits.append(_Visit(site, date_of(site) if frames[0].site else None, frames))
            for site, dirs in scan.visit_dirs.items():
                if site in groups:
                    visits[[v.site for v in visits].index(site)].dirs.extend(dirs)
                else:
                    visits.append(_Visit(site, date_of(site), None, list(dirs)))
            lo, hi = parse_survey_date(self.options.get("from")), parse_survey_date(self.options.get("to"))
            visits = [v for v in visits if not (v.date and (lo and v.date < lo or hi and v.date > hi))]
            visits.sort(key=lambda v: (v.date or "9999-99-99", v.site))
            visits = [visits[i] for i in spread_order(len(visits))]
        self._plans[acc.acc] = visits
        return visits

    def _frames(self, acc: Acc, v: _Visit) -> list[_Frame]:
        if v.frames is None:
            seen: set[str] = set()
            frames: list[_Frame] = []
            for d in v.dirs:
                frames.extend(self._folder_frames(acc, d, seen))
            v.frames = drop_variants(frames)
            v.dirs = []
        elif v.dirs:  # a site with images in the flat part and a folder of the tree: one visit
            seen = {f.name.upper() for f in v.frames}
            for d in v.dirs:
                v.frames.extend(self._folder_frames(acc, d, seen))
            v.frames = drop_variants(v.frames)
            v.dirs = []
        v.frames.sort(key=lambda f: (f.rep, f.photo if f.photo is not None else -1, f.name))
        return v.frames

    def _weights(self, accs: list[Acc]) -> dict[str, float]:
        """Equal share per region; inside a region ``climate_share`` for the climate accessions, the rest for StRS."""
        areas = sorted({a.area for a in accs})
        share = self._climate_share()
        out: dict[str, float] = {}
        for area in areas:
            groups = {k: [a for a in accs if a.area == area and a.kind == k] for k in ("climate", "strs")}
            present = {k: v for k, v in groups.items() if v}
            total = sum(share if k == "climate" else 1 - share for k in present)
            for k, members in present.items():
                s = (share if k == "climate" else 1 - share) / total
                for a in members:
                    out[a.acc] = s / len(members) / len(areas)
        return out

    # ---------------------------------------------------------------- discover
    def discover(self) -> Iterable[Candidate]:
        accs = self.selected_accessions()
        k = self._frames_per_visit()
        if str(self.options.get("order", "spread")).lower() == "table":
            for a in accs:
                visits = sorted(self._visits(a), key=lambda v: v.site)
                for v in visits:
                    frames = self._frames(a, v)
                    picks = pick_order(len(frames))[: len(frames) if k is None else k]
                    for i in sorted(picks):
                        yield self._candidate(a, v, frames[i])
            return
        weights = self._weights(accs)
        r = 0
        while k is None or r < k:
            got = False
            for cand in interleave([(weights[a.acc], self._round(a, r)) for a in accs]):
                got = True
                yield cand
            if not got:
                break
            r += 1

    def _round(self, acc: Acc, r: int) -> Iterator[Candidate]:
        """The r-th frame (van der Corput order) of every visit of the accession."""
        for v in self._visits(acc):
            frames = self._frames(acc, v)
            if r < len(frames):
                yield self._candidate(acc, v, frames[pick_order(len(frames))[r]])

    def _candidate(self, acc: Acc, v: _Visit, f: _Frame) -> Candidate:
        ext = (f.name.rsplit(".", 1)[-1] if "." in f.name else "jpg").lower()
        station = f"{acc.acc}/{v.site}"
        extra: dict[str, Any] = {
            "ncei_accession": acc.acc,
            "landing_url": acc.landing,
            "survey_kind": acc.kind,
            "survey_year": acc.year,
            "region": acc.detail,
            "area": acc.area,
            "station_id": station,
            "site_code": f.site,
            "replicate": f.rep or None,
            "photo_id": f.photo,
            "survey_date": v.date,
            "exif_note": "apply the EXIF Orientation tag; DateTimeOriginal is wrong on some cameras (use survey_date)",
        }
        if f.size:
            extra["size_hint_bytes"] = f.size
        return Candidate(
            source=self.key,
            item_id=f"{acc.acc}/{f.name}",
            media_type="image",
            media_url=f.url,
            origin_url=acc.landing,
            timestamp=v.date,
            ext=ext,
            raw={"acc": acc.acc, "name": f.name, "site": f.site, "year": f.year, "photo": f.photo},
            extra=extra,
        )

    # ----------------------------------------------------------------- licence
    def resolve_licence(self, cand: Candidate) -> Licence:
        return self._licence(ACC_BY_ID[cand.raw["acc"]])

    def _record(self, acc: Acc) -> list[str] | None:
        """Constraint texts of the accession's ISO record, or None when it cannot be read."""
        try:
            text = self.ctx.cached_text(ISO_URL.format(acc=acc.acc), f"iso/{acc.acc}.xml", timeout=120)
            return parse_iso_constraints(text)
        except (HttpError, OSError, ValueError, ET.ParseError) as exc:
            self.ctx.fail(acc.acc, "licence_record", f"ISO record not read, collection-level licence used: {exc}")
            return None

    def _licence(self, acc: Acc) -> Licence:
        if acc.acc in self._licences:
            return self._licences[acc.acc]
        texts = self._record(acc)
        cite = next((t for t in texts or [] if t.lower().startswith("cite as:")), None)
        if cite:
            citation = short_citation(cite, acc.acc)
        else:
            citation = (
                f"Ecosystem Sciences Division, Pacific Islands Fisheries Science Center. National Coral Reef Monitoring Program: "
                f"Benthic Images Collected from {acc.kind_title} across {acc.detail} from {acc.first} to {acc.last} "
                f"(NCEI Accession {acc.acc}). NOAA National Centers for Environmental Information. {acc.landing}"
            )
        attribution = f"{citation} {ACK}"
        # Tiers of every constraint text of the record: a CC0 statement gives A, any NC / ND / research-only term X.
        record_tiers = [classify(t) for t in texts or [] if not t.lower().startswith("cite as:")]
        known = [t for t in record_tiers if t != "U"]
        if "X" in known:
            bad = next(t for t in texts or [] if classify(t) == "X")
            lic = make_licence(f"excluded term in the NCEI record: {bad[:160]}", level="record", url=acc.landing, attribution=attribution, tier="X")
        elif known:
            statement = " ".join(t for t in texts or [] if classify(t) != "U")
            url = acc.landing
            if len(set(known)) > 1:  # e.g. a CC0 dedication next to a CC BY line: held as unknown (combine -> U), never silently A
                name = f"conflicting licence statements in the NCEI record: {statement[:200]}"
            elif "cc0" in statement.lower():
                name, url = "CC0-1.0 (Creative Commons CC0 1.0 Universal Public Domain Dedication)", CC0_URL
            else:
                name = statement[:200]
            lic = make_licence(name, level="record", url=url, attribution=attribution, tier=combine(*known))
        else:
            # No licence field in the record (accessLevel: public + citation request only): NOAA PIFSC data are US
            # federal government works (17 U.S.C. 105); the collection record (InPort) states "data-access-constraints: None".
            name = "US government work (NOAA PIFSC), no licence stated; collection record: data-access-constraints None, citation requested"
            lic = make_licence(name, level="collection", url=INPORT.format(n=acc.inport), attribution=attribution, tier=classify(name))
        self._licences[acc.acc] = lic
        return lic

    # --------------------------------------------------------------------- geo
    def _cover(self, table: str) -> dict[str, CoverRec] | None:
        """The reduced cover table (one row per ``<SITE>_<YEAR>``), streamed once and cached; None when unavailable."""
        if table in self._covers:
            return self._covers[table]
        name = f"cover/{table}.csv"
        path = self.ctx.layout.raw / name
        rec: dict[str, CoverRec] | None = None
        try:
            if path.exists() and not self.options.get("refresh_metadata"):
                text = path.read_text(encoding="utf-8")
            else:
                text = self._download_cover(table)
                self.ctx.save_raw(name, text)
            rec = load_cover(text)
        except (HttpError, OSError, ValueError, csv.Error) as exc:
            self.ctx.fail(f"cover:{table}", "depth", f"cover table not read, no depth / coordinate fallback from it: {exc}")
        self._covers[table] = rec
        return rec

    def _download_cover(self, table: str) -> str:
        acc, path, fname = COVER_TABLES[table]
        url = COVER_BASE.format(path=path, name=quote(fname))
        log.info("noaa_ncrmp: streaming cover table %s (NCEI %s) to build the depth table", fname, acc)
        resp = self.http.request("GET", url, stream=True, timeout=120)
        try:
            if resp.status_code >= 400:
                raise HttpError(url, resp.status_code, "cover table not available")
            text, _n = reduce_cover(line.decode("utf-8", errors="replace") for line in resp.iter_lines())
        finally:
            resp.close()
        return text

    def _cover_id(self, acc: Acc) -> str:
        return "fixed" if acc.kind == "climate" else acc.area

    def resolve_geo(self, cand: Candidate) -> Geo:
        acc = ACC_BY_ID[cand.raw["acc"]]
        name = cand.raw["name"]
        p = parse_name(name)
        if not p:
            return Geo.none(geo_source="filename not parseable")
        site, year = p["site"], p["year"]
        cover_id = self._cover_id(acc)
        cover = self._cover(cover_id) if str(self.options.get("depth", "cover")).lower() != "off" else None
        crec = cover.get(f"{site}_{year}") if cover else None
        depth = depth_m_of(crec)
        cacc, _cpath, cfile = COVER_TABLES[cover_id]
        depth_note = (
            f"; depth: NCEI {cacc} {cfile} MIN_DEPTH/MAX_DEPTH (feet, mean x 0.3048) via IMAGE_NAME, DEPTH_SOURCE {crec.depth_source}"
            if depth is not None and crec is not None
            else ""
        )

        hits = self._siteinfo(acc).find(site, year)
        usable = [(r, c) for r, c in hits if r.lat is not None and r.lon is not None]
        if usable:
            coords = {(r.lat, r.lon) for r, _ in usable}
            if len(coords) > 1:
                return Geo.none(
                    geo_source=f"site code {site} has {len(usable)} rows with different coordinates in the site-info CSV of {acc.acc} ({usable[0][0].file})",
                    depth_m=depth,
                )
            row, col = usable[0]
            lat, lon = row.lat, row.lon
            if not in_pacific_box(lat, lon):
                return Geo.none(geo_source=f"NCEI {acc.acc} {row.file} position ({lat}, {lon}) outside the Pacific sanity box", depth_m=depth)
            source = (
                f"NCEI {acc.acc} {row.file} LATITUDE/LONGITUDE (handheld GPS over the dive buoy, WGS 84), "
                f"joined on {col} = {site}{depth_note}"
            )
            return Geo(lat, lon, depth, "station", source, True, STATION_UNCERTAINTY_M)
        if crec is not None and crec.lat is not None and crec.lon is not None and in_pacific_box(crec.lat, crec.lon):
            why = "has no valid LATITUDE/LONGITUDE in the site-info CSV" if hits else "is not in the site-info CSV"
            source = (
                f"NCEI {cacc} {cfile} LATITUDE/LONGITUDE via IMAGE_NAME site visit {site}_{year} "
                f"(site code {why} of {acc.acc}){depth_note}"
            )
            return Geo(round(crec.lat, 6), round(crec.lon, 6), depth, "station", source, True, STATION_UNCERTAINTY_M)
        why = "has no valid LATITUDE/LONGITUDE in" if hits else "not in"
        return Geo.none(geo_source=f"site code {site} {why} the site-info CSV of {acc.acc}; no row in the cover table", depth_m=depth)

    # ------------------------------------------------------------------- media
    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(url=cand.media_url, ext=cand.ext or "jpg")

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        """Plain GET (resumable, Range supported); the file must start with the JPEG magic number."""
        nbytes, sha = self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)
        with open(dest, "rb") as fh:
            head = fh.read(3)
        if head != b"\xff\xd8\xff":
            dest.unlink(missing_ok=True)
            raise HttpError(ref.url, None, "downloaded file is not a JPEG (error page?)")
        return nbytes, sha
