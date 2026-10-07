"""Offline tests for the noaa_ncrmp adapter, run on the real fixtures in tests/fixtures/noaa_ncrmp/.

No test touches the network: the NCEI directory listings, site-info CSVs, ISO records and the reduced cover tables
are copied into metadata/raw/ (like the other adapter tests) and the Http client raises on any request. Expected
values come from tests/fixtures/noaa_ncrmp/SOURCE.md and research/noaa_ncrmp.md ("resolve_geo recipe").

What is real and what is synthetic
    * Real, unmodified: the three site-info CSVs, ``listing_0317534_excerpt.html`` (the image folder of 0317534) and
      ``cover_fixed_excerpt.csv`` of the fixture folder.
    * Real text, re-wrapped: the ``0-data/`` root listings (names, dates and sizes of the NCEI rows retrieved
      2026-10-07), the ``otherConstraints`` texts of the ISO records of 0317534 and 0159155 (inside a minimal ISO XML
      shell), the image rows of 0159155 / 0240600 / 0270550 and the site-info rows of 0176287 / 0270550 (header and
      rows as served, CRLF kept). Cases marked "synthetic" are built by hand to hit an edge case.
"""

import csv
import io
import json
import shutil
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from aquasource.adapters import noaa_ncrmp as nc
from aquasource.adapters.base import Context, MediaRef, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog
from aquasource.core.schema import Candidate
from aquasource.runner import run_source

TESTS = Path(__file__).parent
FIX = TESTS / "fixtures" / "noaa_ncrmp"
ARCH = "https://www.ncei.noaa.gov/data/oceans/archive"
LANDING = "https://www.ncei.noaa.gov/archive/accession/"
ACK = nc.ACK

CITE_0317534 = (
    "Cite as: Ecosystem Sciences Division, Pacific Islands Fisheries Science Center (2026). National Coral Reef Monitoring "
    "Program: Benthic Images Collected from Climate Stations across the Hawaiian Archipelago from 2024-05-29 to 2024-08-27 "
    "(NCEI Accession 0317534). https://www.ncei.noaa.gov/archive/accession/0317534. In NOAA Pacific Islands Fisheries Science "
    "Center, Ecosystem Sciences Division (2018). National Coral Reef Monitoring Program: Benthic cover derived from analysis of "
    "images collected from climate stations across the Hawaiian Archipelago. [indicate subset used]. NOAA National Centers for "
    "Environmental Information. Dataset. https://doi.org/10.7289/v5f47mff. Accessed [date]."
)
CITE_0159155 = (
    "Cite as: Coral Reef Ecosystem Program; Pacific Islands Fisheries Science Center (2017). National Coral Reef Monitoring "
    "Program: Benthic Images Collected from Climate Stations across the Pacific Remote Island Areas from 2015-01-26 to "
    "2015-04-27 (NCEI Accession 0159155). https://www.ncei.noaa.gov/archive/accession/0159155. In NOAA Pacific Islands "
    "Fisheries Science Center, Ecosystem Sciences Division (2018). National Coral Reef Monitoring Program: Benthic cover "
    "derived from analysis of images collected from climate stations across the Pacific Remote Island Areas. [indicate subset "
    "used]. NOAA National Centers for Environmental Information. Dataset. https://doi.org/10.7289/v54m92v0. Accessed [date]."
)
ACCESS = "accessLevel: public"
DISTRIBUTION = (
    "Distribution liability: NOAA and NCEI make no warranty, expressed or implied, regarding these data, nor does the fact of "
    "distribution constitute such a warranty. NOAA and NCEI cannot assume liability for any damages caused by any errors or "
    "omissions in these data. If appropriate, NCEI can only certify that the data it distributes are an authentic copy of the "
    "records that were accepted for inclusion in the NCEI archives."
)
USE_LIABILITY = (
    "Use liability: NOAA and NCEI cannot provide any warranty as to the accuracy, reliability, or completeness of furnished "
    "data. Users assume responsibility to determine the usability of these data. The user is responsible for the results of any "
    "application of this data for other than its intended purpose."
)
CC0_TEXT = "This dataset has been dedicated to the public domain under the Creative Commons CC0 1.0 Universal (CC0 1.0) Public Domain Dedication."
SPDX = "SPDX License: Creative Commons Zero v1.0 Universal (CC0-1.0)"
ISO_0317534 = [ACCESS, CITE_0317534, DISTRIBUTION, USE_LIABILITY, CC0_TEXT, SPDX]
ISO_0159155 = [ACCESS, CITE_0159155, DISTRIBUTION, USE_LIABILITY]

SRC_2024 = "NCEI 0317534 NCRMP_CLIMATE_SITEINFO_HAWAII_2024.csv LATITUDE/LONGITUDE (handheld GPS over the dive buoy, WGS 84), joined on SITE = {code}"
DEPTH_FIXED = "; depth: NCEI 0317416 NCRMP_BENTHIC_COVER_FIXED_PACIFIC_2012-2025.csv MIN_DEPTH/MAX_DEPTH (feet, mean x 0.3048) via IMAGE_NAME, DEPTH_SOURCE {src}"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


class Down(Http):
    def request(self, method, url, **k):
        raise HttpError(url, 503, "down")


def make_adapter(tmp_path, *, http=None, dry_run=True, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "noaa_ncrmp").ensure()
    ctx = Context(cfg, http or NoNet(dry_run=dry_run), layout, options, dry_run, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("noaa_ncrmp")(ctx)


def failures(a):
    path = a.ctx.layout.failures_jsonl
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


# ----------------------------------------------------------------------------------------------- seed helpers
_FIXTURE_LISTING = (FIX / "listing_0317534_excerpt.html").read_text(encoding="utf-8")
_LINES = _FIXTURE_LISTING.splitlines()
_FIRST_IMG = next(i for i, ln in enumerate(_LINES) if "[IMG]" in ln)
_LAST_IMG = max(i for i, ln in enumerate(_LINES) if "[IMG]" in ln)


def entry(name, size="  - ", date="2024-08-08 18:19", kind=None):
    """One Apache autoindex row in the exact format of the fixture rows. A trailing ``/`` makes it a directory."""
    is_dir = name.endswith("/")
    icon = ("folder.gif", "DIR") if is_dir else (("text.gif", "TXT") if name.lower().endswith((".csv", ".xml")) else ("image2.gif", "IMG"))
    return (
        f'<tr><td valign="top"><img src="/icons/{icon[0]}" alt="[{icon[1]}]"></td><td><a href="{name}">{name}</a></td>'
        f'<td align="right">{date}  </td><td align="right">{"  - " if is_dir else size}</td><td>&nbsp;</td></tr>'
    )


def listing(*entries):
    """A directory listing with the header and footer of the real fixture (the parent-directory row included)."""
    return "\n".join([*_LINES[:_FIRST_IMG], *entries, *_LINES[_LAST_IMG + 1:]]) + "\n"


def seed_listing(a, acc, rel, text):
    """Cache the listing of ``0-data/<rel>`` ('' = the root) under the name the adapter reads."""
    url = nc.ACC_BY_ID[acc].root_url + rel
    path = a.ctx.layout.raw / a._listing_name(nc.ACC_BY_ID[acc], url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def seed_csv(a, acc, name, text):
    path = a.ctx.layout.raw / "siteinfo" / acc / nc._safe(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8")) if isinstance(text, str) else path.write_bytes(text)


def iso_xml(constraints):
    """A minimal ISO 19115-2 shell around real constraint texts (useLimitation first, as NCEI writes them)."""
    items = "".join(
        f"<gmd:resourceConstraints><gmd:MD_LegalConstraints><gmd:{'useLimitation' if t.startswith(('accessLevel', 'Distribution')) else 'otherConstraints'}>"
        f"<gco:CharacterString>{escape(t)}</gco:CharacterString></gmd:{'useLimitation' if t.startswith(('accessLevel', 'Distribution')) else 'otherConstraints'}>"
        "</gmd:MD_LegalConstraints></gmd:resourceConstraints>"
        for t in constraints
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?><gmi:MI_Metadata xmlns:gmi="http://www.isotc211.org/2005/gmi" '
        'xmlns:gmd="http://www.isotc211.org/2005/gmd" xmlns:gco="http://www.isotc211.org/2005/gco">'
        f"<gmd:identificationInfo><gmd:MD_DataIdentification>{items}</gmd:MD_DataIdentification></gmd:identificationInfo></gmi:MI_Metadata>"
    )


def seed_iso(a, acc, constraints):
    path = a.ctx.layout.raw / "iso" / f"{acc}.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(iso_xml(constraints), encoding="utf-8")


def seed_cover(a, table="fixed", source=FIX / "cover_fixed_excerpt.csv"):
    with open(source, newline="", encoding="utf-8") as fh:
        text, _n = nc.reduce_cover(fh)
    path = a.ctx.layout.raw / "cover" / f"{table}.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def seed_2024(a):
    """Accession 0317534 (climate, Hawaii 2024): real root rows, the real image folder fixture, the real CSV, the CC0 record."""
    seed_listing(
        a, "0317534", "",
        listing(
            entry("0L1MXX-ISO-19115-2.xml", "22K", "2026-07-16 18:30"), entry("DataDocumentation/", date="2026-08-13 14:31"),
            entry("NCRMP_CLIMATE_SITEINFO_HAWAII_2024.csv", "4.2K", "2026-07-16 18:16"), entry("NCRMP_FIXED_IMAGES_HAWAII_2024/", date="2026-08-18 15:23"),
            entry("SITEINFO_DATADICTIONARY_2024.csv", "395 ", "2026-07-16 18:16"),
        ),
    )  # fmt: skip
    seed_listing(a, "0317534", "NCRMP_FIXED_IMAGES_HAWAII_2024/", _FIXTURE_LISTING)
    shutil.copyfile(FIX / "site_info_climate_hawaii_2024.csv", _target(a, "0317534", "NCRMP_CLIMATE_SITEINFO_HAWAII_2024.csv"))
    seed_iso(a, "0317534", ISO_0317534)


def _target(a, acc, name):
    path = a.ctx.layout.raw / "siteinfo" / acc / nc._safe(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


PRIA_ROWS = ["BAK-11_2015_A_01.JPG", "BAK-11_2015_A_02.JPG", "BAK-11_2015_A_03.JPG", "BAK-11_2015_A_04.JPG"]


def seed_2015(a, frames=4):
    """Accession 0159155 (climate, PRIA 2015): real folder names, the real CSV rows (BAK-11, KIN-07, KIN-62), 4 synthetic frames per site."""
    seed_listing(
        a, "0159155", "",
        listing(
            entry("CMAPMH-ISO-19115-2.xml", " 20K", "2016-12-30 19:15"), entry("Climate_Images_PRIAs_2015/", date="2017-02-06 18:19"),
            entry("DataDocumentation/", date="2017-01-25 12:44"), entry("Site_Info_PRIAs_2015.csv", "1.6K", "2017-01-31 17:38"),
        ),
    )  # fmt: skip
    imgs = [entry(f"{s}_2015_A_{n:02d}.JPG", "3.0M", "2015-02-09 09:43") for s in ("BAK-11", "KIN-07", "KIN-62") for n in range(1, frames + 1)]
    seed_listing(a, "0159155", "Climate_Images_PRIAs_2015/", listing(*imgs))
    shutil.copyfile(FIX / "site_info_climate_pria_2015.csv", _target(a, "0159155", "Site_Info_PRIAs_2015.csv"))
    seed_iso(a, "0159155", ISO_0159155)


def seed_2019_nwhi(a):
    """Accession 0240600 (climate, Hawaii 2019), NWHI half only (the MHI folder and CSV are left out)."""
    seed_listing(
        a, "0240600", "",
        listing(
            entry("Benthic_Image_Site_Info_NWHI.csv", "2.0K", "2021-09-21 03:44"), entry("NWHI_Climate_PHOTQUADS_2019/", date="2021-09-21 05:58"),
        ),
    )  # fmt: skip
    seed_listing(a, "0240600", "NWHI_Climate_PHOTQUADS_2019/", listing(entry("OCC-FFS-009_2019_01.JPG", "8.9M", "2019-08-28 12:24"), entry("OCC-FFS-009_2019_02.JPG", "8.7M", "2019-08-28 12:24")))
    shutil.copyfile(FIX / "site_info_climate_nwhi_2019.csv", _target(a, "0240600", "Benthic_Image_Site_Info_NWHI.csv"))


def by_name(cands):
    return {c.item_id.split("/", 1)[1]: c for c in cands}


# ------------------------------------------------------------------------------------------------ pure helpers
def test_parse_listing_of_the_real_fixture():
    rows = nc.parse_listing(_FIXTURE_LISTING, nc.ACC_BY_ID["0317534"].root_url + "NCRMP_FIXED_IMAGES_HAWAII_2024/")
    assert [r.name for r in rows] == ["OCC-FFS-001_2024_02.JPG", "OCC-FFS-002_2024_03.JPG", "OCC-FFS-003_2024_01.JPG"]  # Parent Directory skipped
    assert rows[0].url == f"{ARCH}/arc0247/0317534/1.1/data/0-data/NCRMP_FIXED_IMAGES_HAWAII_2024/OCC-FFS-001_2024_02.JPG"
    assert [r.size for r in rows] == [13 << 20, 11 << 20, int(9.6 * (1 << 20))] and not any(r.is_dir for r in rows)


def test_parse_listing_directories_spaces_and_sort_links():
    """Synthetic: a folder with spaces comes back percent-encoded in the href and decoded in the name."""
    row = (
        '<tr><td valign="top"><img src="/icons/folder.gif" alt="[DIR]"></td><td><a href="Climate%20Images%20MARIAN%202014/">'
        'Climate Images MARIAN 2014/</a></td><td align="right">2014-01-01 00:00  </td><td align="right">  - </td><td>&nbsp;</td></tr>'
    )
    base = f"{ARCH}/arc0104/0157759/1.1/data/0-data/"
    rows = nc.parse_listing(listing(row, entry("Site Info MARIAN 2014.csv", "1.5K")), base)
    assert [(r.name, r.is_dir) for r in rows] == [("Climate Images MARIAN 2014", True), ("Site Info MARIAN 2014.csv", False)]
    assert rows[0].url == base + "Climate%20Images%20MARIAN%202014/"  # urljoin keeps the server's encoding: the sort links ?C=N;O=D are not entries


@pytest.mark.parametrize(
    "name, expected",
    [
        ("OCC-FFS-001_2024_02.JPG", {"site": "OCC-FFS-001", "year": 2024, "rep": "", "photo": 2, "variant": ""}),
        ("BAK-11_2015_A_08.JPG", {"site": "BAK-11", "year": 2015, "rep": "A", "photo": 8, "variant": ""}),
        ("SAI-1022_2017__01.JPG", {"site": "SAI-1022", "year": 2017, "rep": "", "photo": 1, "variant": ""}),  # empty replicate (0176286)
        ("kin-16_2015_a_31.jpg", {"site": "KIN-16", "year": 2015, "rep": "A", "photo": 31, "variant": ""}),  # case varies, frames above 30 exist
        ("OAH-B3259_2019_01_original.JPG", {"site": "OAH-B3259", "year": 2019, "rep": "", "photo": 1, "variant": "original"}),
        ("README.txt", None),
        ("notes.jpg", None),
    ],
)
def test_parse_name(name, expected):
    assert nc.parse_name(name) == expected


@pytest.mark.parametrize(
    "text, iso",
    [
        ("05-SEP-13", "2013-09-05"),
        ("15-Aug-16", "2016-08-15"),
        ('"10-Aug-24"', "2024-08-10"),
        ("7/10/2018", "2018-07-10"),  # month first
        ("8/28/2019 0:00", "2019-08-28"),
        ("29-APR-22 11.42.31", "2022-04-29"),
        ("18-OCT-19 00.00.00", "2019-10-18"),  # 0270550 as served
        ("2018-07-10", "2018-07-10"),
        ("31-FEB-20", None),
        ("", None),
        ("not a date", None),
    ],
)
def test_parse_survey_date(text, iso):
    assert nc.parse_survey_date(text) == iso


def test_is_site_info_picks_the_csv_not_the_dictionary():
    assert nc.is_site_info("NCRMP_CLIMATE_SITEINFO_HAWAII_2024.csv") and nc.is_site_info("Site Info MARIAN 2014.csv")
    assert nc.is_site_info("ESD_SiteInfo_MHI_BLEA_2019.csv") and nc.is_site_info("Benthic_Image_Site_Info_NWHI.csv")
    assert not nc.is_site_info("SITEINFO_DATADICTIONARY_2024.csv") and not nc.is_site_info("ESD_BenthicImage_Climate_2019_DataDictionary.csv")
    assert not nc.is_site_info("0L1MXX-ISO-19115-2.xml")


def test_pick_order_and_spread_order_are_permutations_with_even_prefixes():
    assert nc.pick_order(4) == (2, 1, 3, 0) and nc.pick_order(1) == (0,) and nc.pick_order(0) == ()
    assert nc.pick_order(30)[:4] == (15, 7, 22, 3)  # the centre, the quarters: never the first or the last frame first
    for n in (2, 3, 17, 30, 38, 100):
        assert sorted(nc.pick_order(n)) == list(range(n)) and sorted(nc.spread_order(n)) == list(range(n))
    assert nc.spread_order(5) == [0, 4, 2, 1, 3]


def test_interleave_is_a_weighted_round_robin():
    out = list(nc.interleave([(1.0, iter("aaaaaa")), (3.0, iter("bbbbbb")), (1.0, iter("cc"))]))
    assert out.count("a") == 6 and out.count("b") == 6 and out.count("c") == 2  # exhausted streams drop out, nothing is lost
    assert out[:8] == list("bbabcbba")  # smallest (served + 1) / weight first, ties to the earlier stream: b gets 5 of the first 8


def test_accession_table_matches_the_research_totals():
    assert len(nc.ACCESSIONS) == 38 and len(nc.ACC_BY_ID) == 38
    climate = [a for a in nc.ACCESSIONS if a.kind == "climate"]
    strs = [a for a in nc.ACCESSIONS if a.kind == "strs"]
    assert (len(climate), sum(a.images for a in climate), round(sum(a.gb for a in climate), 1)) == (17, 20068, 167.6)
    assert (len(strs), sum(a.images for a in strs if not a.approx), sum(a.images for a in strs if a.approx)) == (21, 176597, 20600)
    assert round(sum(a.gb for a in nc.ACCESSIONS) / 1000, 2) == 1.57  # TB
    assert nc.ACC_BY_ID["0159168"].path == "arc0103/0159168/2.2"  # the one accession that is not at version 1.1
    assert nc.ACC_BY_ID["0317534"].root_url == f"{ARCH}/arc0247/0317534/1.1/data/0-data/"


# ------------------------------------------------------------------------------------------- site-info CSVs
def test_site_info_fixtures_parse_with_their_quoting_and_date_formats():
    hawaii = nc.parse_site_info((FIX / "site_info_climate_hawaii_2024.csv").read_text(encoding="utf-8"), "h.csv")
    assert [(r.codes, r.lat, r.lon, r.date) for r in hawaii][0] == ((("SITE", "OCC-FFS-001"),), 23.878545, -166.290919, "2024-08-08")
    pria = nc.parse_site_info((FIX / "site_info_climate_pria_2015.csv").read_text(encoding="utf-8"), "p.csv")
    assert [(r.codes[0][1], r.date) for r in pria] == [("BAK-11", "2015-02-08"), ("KIN-07", "2015-04-26"), ("KIN-62", "2015-04-26")]
    assert (pria[1].lat, pria[1].lon) == (pria[2].lat, pria[2].lon) == (6.40213, -162.3857)  # two sites, identical coordinates in the source
    nwhi = nc.parse_site_info((FIX / "site_info_climate_nwhi_2019.csv").read_text(encoding="utf-8"), "n.csv")
    assert nwhi[0].codes == (("SITE", "FFS-4054"), ("OCC_SITEID", "OCC-FFS-009")) and nwhi[0].date == "2019-08-28"  # 8/28/2019 0:00


def test_site_info_skips_empty_rows_and_bad_coordinates():
    """Synthetic: SiteInfo_Wake_2017.csv really has 2 rows and 14 ',,,' rows; a swapped / sentinel coordinate is not kept."""
    text = 'SITE,DATE_,LATITUDE,LONGITUDE\r\nWAK-1,19-APR-17,19.3,166.6\r\n,,,\r\n,,,\r\nWAK-2,20-APR-17,-999,166.6\r\nWAK-3,20-APR-17,166.6,19.3\r\n'
    rows = nc.parse_site_info("﻿" + text, "wake.csv")
    assert [r.codes[0][1] for r in rows] == ["WAK-1", "WAK-2", "WAK-3"]
    assert [(r.lat, r.lon) for r in rows] == [(19.3, 166.6), (None, None), (None, None)]


def test_site_index_finds_by_either_id_column_and_by_year():
    idx = nc.SiteIndex()
    idx.add(nc.parse_site_info((FIX / "site_info_climate_nwhi_2019.csv").read_text(encoding="utf-8"), "n.csv"))
    (row, col), = idx.find("occ-ffs-009")
    assert col == "OCC_SITEID" and row.lat == 23.63488 and "FFS-4054" in idx and idx.find("FFS-4054")[0][1] == "SITE"
    assert idx.find("nope") == [] and "nope" not in idx


# ------------------------------------------------------------------------------------------ discover: 0317534
def test_discover_the_real_fixture_item_ids_media_url_and_type(tmp_path):
    a = make_adapter(tmp_path, accessions="0317534", depth="off")
    seed_2024(a)
    cands = list(a.discover())
    assert sorted(c.item_id for c in cands) == [
        "0317534/OCC-FFS-001_2024_02.JPG",
        "0317534/OCC-FFS-002_2024_03.JPG",
        "0317534/OCC-FFS-003_2024_01.JPG",
    ]
    c = by_name(cands)["OCC-FFS-001_2024_02.JPG"]
    assert (c.source, c.media_type, c.ext) == ("noaa_ncrmp", "image", "jpg")
    assert c.media_url == f"{ARCH}/arc0247/0317534/1.1/data/0-data/NCRMP_FIXED_IMAGES_HAWAII_2024/OCC-FFS-001_2024_02.JPG"
    assert c.origin_url == LANDING + "0317534"
    assert c.timestamp == "2024-08-08"  # the survey date of the site-info CSV, not the EXIF time
    assert c.extra["station_id"] == "0317534/OCC-FFS-001" and c.extra["ncei_accession"] == "0317534"
    assert (c.extra["survey_kind"], c.extra["replicate"], c.extra["photo_id"], c.extra["site_code"]) == ("climate", None, 2, "OCC-FFS-001")
    assert c.extra["size_hint_bytes"] == 13 << 20 and "Orientation" in c.extra["exif_note"]
    assert a.resolve_media(c).url == c.media_url and a.resolve_media(c).ext == "jpg"
    assert failures(a) == []


def test_licence_cc0_record_level_with_the_providers_citation(tmp_path):
    a = make_adapter(tmp_path, accessions="0317534", depth="off")
    seed_2024(a)
    lic = a.resolve_licence(next(iter(a.discover())))
    assert (lic.tier, lic.level) == ("A", "record")
    assert lic.name.startswith("CC0-1.0") and lic.url == "https://creativecommons.org/publicdomain/zero/1.0/"
    assert lic.attribution == (
        "Ecosystem Sciences Division, Pacific Islands Fisheries Science Center (2026). National Coral Reef Monitoring Program: "
        "Benthic Images Collected from Climate Stations across the Hawaiian Archipelago from 2024-05-29 to 2024-08-27 "
        f"(NCEI Accession 0317534). https://www.ncei.noaa.gov/archive/accession/0317534. {ACK}"
    )  # the "In NOAA ... [indicate subset used] ... Accessed [date]" template tail is not copied into every sample


def test_licence_older_accession_is_us_government_work_at_collection_level(tmp_path):
    a = make_adapter(tmp_path, accessions="0159155", depth="off")
    seed_2015(a)
    lic = a.resolve_licence(next(iter(a.discover())))
    assert (lic.tier, lic.level, lic.url) == ("A", "collection", "https://www.fisheries.noaa.gov/inport/item/71813")
    assert lic.name.startswith("US government work (NOAA PIFSC), no licence stated")
    assert lic.attribution.startswith("Coral Reef Ecosystem Program; Pacific Islands Fisheries Science Center (2017). National Coral Reef Monitoring Program:")
    assert lic.attribution.endswith(f"(NCEI Accession 0159155). https://www.ncei.noaa.gov/archive/accession/0159155. {ACK}")


def test_licence_without_the_iso_record_falls_back_to_the_collection_and_says_so(tmp_path):
    a = make_adapter(tmp_path, http=Down(dry_run=True), accessions="0317534", depth="off")
    seed_2024(a)
    (a.ctx.layout.raw / "iso" / "0317534.xml").unlink()
    lic = a.resolve_licence(next(iter(a.discover())))
    assert (lic.tier, lic.level) == ("A", "collection")  # never CC0 without having read it
    assert "(NCEI Accession 0317534)" in lic.attribution and lic.attribution.endswith(ACK)
    assert [f["stage"] for f in failures(a)] == ["licence_record"]


@pytest.mark.parametrize(
    "extra_text",
    [
        "Use is restricted to non-commercial research purposes.",
        "Creative Commons Attribution-NoDerivatives 4.0 International (CC BY-ND 4.0)",
        "These images are for research use only.",
    ],
)
def test_an_nc_nd_or_research_only_term_in_the_record_makes_the_accession_excluded(tmp_path, extra_text):
    """Synthetic: nothing like this exists today; the adapter must never keep treating such a record as US government work."""
    a = make_adapter(tmp_path, accessions="0159155", depth="off")
    seed_2015(a)
    seed_iso(a, "0159155", [*ISO_0159155, extra_text])
    lic = a.resolve_licence(next(iter(a.discover())))
    assert lic.tier == "X" and lic.level == "record"


def test_contradicting_licence_statements_are_held_as_unknown(tmp_path):
    """Synthetic: a CC0 statement next to a CC BY one is a contradiction (core combine -> U), never silently A."""
    a = make_adapter(tmp_path, accessions="0159155", depth="off")
    seed_2015(a)
    seed_iso(a, "0159155", [*ISO_0159155, CC0_TEXT, "Licensed under Creative Commons Attribution 4.0 (CC BY 4.0)"])
    assert a.resolve_licence(next(iter(a.discover()))).tier == "U"


def test_iso_parser_refuses_entities_and_returns_texts_in_order():
    assert nc.parse_iso_constraints(iso_xml([ACCESS, CITE_0159155]))[:2] == [ACCESS, CITE_0159155]
    with pytest.raises(ValueError):
        nc.parse_iso_constraints('<!DOCTYPE x [<!ENTITY a "b">]><x/>')
    assert nc.short_citation(CITE_0159155, "0159155").endswith("(NCEI Accession 0159155). https://www.ncei.noaa.gov/archive/accession/0159155.")


# ------------------------------------------------------------------------------------------------ resolve_geo
@pytest.mark.parametrize(
    "name, lat, lon, depth, src",
    [
        ("OCC-FFS-001_2024_02.JPG", 23.878545, -166.290919, 24.4, "occ"),  # 80.1 ft
        ("OCC-FFS-002_2024_03.JPG", 23.878185, -166.291118, 17.7, "occ"),  # 58.1 ft
        ("OCC-FFS-003_2024_01.JPG", 23.875517, -166.292174, 6.4, "occ"),  # 21 ft
    ],
)
def test_resolve_geo_hawaii_2024_fixture_with_depth(tmp_path, name, lat, lon, depth, src):
    a = make_adapter(tmp_path, accessions="0317534")
    seed_2024(a)
    seed_cover(a)
    c = by_name(a.discover())[name]
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (lat, lon, depth)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 50.0)
    assert g.geo_source == SRC_2024.format(code=name.split("_")[0]) + DEPTH_FIXED.format(src=src)


def test_resolve_geo_pria_2015_depth_is_the_mean_of_the_inverted_min_max(tmp_path):
    """MIN_DEPTH 48 / MAX_DEPTH 47 ft in the source (inverted): 47.5 ft = 14.5 m. The site-info position is the 5-decimal one."""
    a = make_adapter(tmp_path, accessions="0159155")
    seed_2015(a)
    seed_cover(a)
    g = a.resolve_geo(by_name(a.discover())["BAK-11_2015_A_03.JPG"])
    assert (g.lat, g.lon, g.depth_m) == (0.19864, -176.48489, 14.5)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 50.0)
    assert g.geo_source == (
        "NCEI 0159155 Site_Info_PRIAs_2015.csv LATITUDE/LONGITUDE (handheld GPS over the dive buoy, WGS 84), joined on SITE = BAK-11"
        + DEPTH_FIXED.format(src="site")
    )


def test_resolve_geo_joins_the_nwhi_2019_images_through_occ_siteid_and_has_no_depth(tmp_path):
    a = make_adapter(tmp_path, accessions="0240600")
    seed_2019_nwhi(a)
    seed_cover(a)  # the fixture cover table has no row for this site (as in the research)
    c = by_name(a.discover())["OCC-FFS-009_2019_01.JPG"]
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (23.63488, -166.185688, None)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 50.0)
    assert g.geo_source == (
        "NCEI 0240600 Benthic_Image_Site_Info_NWHI.csv LATITUDE/LONGITUDE (handheld GPS over the dive buoy, WGS 84), joined on OCC_SITEID = OCC-FFS-009"
    )
    assert c.timestamp == "2019-08-28"  # 8/28/2019 0:00


def test_two_sites_with_identical_coordinates_are_both_kept(tmp_path):
    a = make_adapter(tmp_path, accessions="0159155", depth="off")
    seed_2015(a)
    cands = by_name(a.discover())
    g7, g62 = a.resolve_geo(cands["KIN-07_2015_A_03.JPG"]), a.resolve_geo(cands["KIN-62_2015_A_03.JPG"])
    assert (g7.lat, g7.lon) == (g62.lat, g62.lon) == (6.40213, -162.3857)
    assert g7.geo_source != g62.geo_source and g7.geo_precision == g62.geo_precision == "station"  # not unique site identifiers, but still positions


def test_unknown_site_code_gives_geo_none_not_an_invented_position(tmp_path):
    """A made-up code in the real 0317534 listing (SOURCE.md: OCC-FFS-099 -> none) and a nameless file."""
    a = make_adapter(tmp_path, accessions="0317534")
    seed_2024(a)
    seed_cover(a)
    ghost = Candidate("noaa_ncrmp", "0317534/OCC-FFS-099_2024_01.JPG", "image", "u", "o", raw={"acc": "0317534", "name": "OCC-FFS-099_2024_01.JPG"})
    g = a.resolve_geo(ghost)
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == (None, None, None, "none", False, None)
    assert g.geo_source == "site code OCC-FFS-099 not in the site-info CSV of 0317534; no row in the cover table"
    odd = Candidate("noaa_ncrmp", "0317534/readme.jpg", "image", "u", "o", raw={"acc": "0317534", "name": "readme.jpg"})
    assert a.resolve_geo(odd).geo_source == "filename not parseable" and a.resolve_geo(odd).geo_precision == "none"


def test_cover_table_is_the_coordinate_fallback_when_the_code_is_not_in_the_csv(tmp_path):
    """BAK-11 is not a site of 0317534, but the cover table knows the visit BAK-11_2015 (0.19864247, -176.48489233)."""
    a = make_adapter(tmp_path, accessions="0317534")
    seed_2024(a)
    seed_cover(a)
    c = Candidate("noaa_ncrmp", "0317534/BAK-11_2015_A_08.JPG", "image", "u", "o", raw={"acc": "0317534", "name": "BAK-11_2015_A_08.JPG"})
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == (0.198642, -176.484892, 14.5, "station", True, 50.0)
    assert g.geo_source.startswith(
        "NCEI 0317416 NCRMP_BENTHIC_COVER_FIXED_PACIFIC_2012-2025.csv LATITUDE/LONGITUDE via IMAGE_NAME site visit BAK-11_2015 "
        "(site code is not in the site-info CSV of 0317534)"
    )


def test_missing_code_of_the_2019_bleaching_accession_is_real_data(tmp_path):
    """0270550: OAH-B3096 (12 images) has no row in ESD_SiteInfo_MHI_BLEA_2019.csv (127 rows for 128 image site codes)."""
    a = make_adapter(tmp_path, accessions="0270550", depth="off")
    seed_listing(a, "0270550", "", listing(entry("ESD_SiteInfo_DataDictionary.csv", "1.0K"), entry("ESD_SiteInfo_MHI_BLEA_2019.csv", "9.0K"), entry("MHI_PQ_Bleaching_2019/")))
    seed_listing(
        a, "0270550", "MHI_PQ_Bleaching_2019/",
        listing(
            entry("HAW-B4311_2019_01.JPG", " 12M", "2022-11-30 15:53"), entry("HAW-B4311_2019_02.JPG", " 11M", "2022-11-30 15:53"),
            entry("OAH-B3096_2019_01.JPG", " 11M", "2022-11-30 19:33"), entry("OAH-B3096_2019_02.JPG", "8.5M", "2022-11-30 19:33"),
        ),
    )  # fmt: skip
    seed_csv(a, "0270550", "ESD_SiteInfo_MHI_BLEA_2019.csv", '"SITE","DATE_","LATITUDE","LONGITUDE"\r\n"HAW-B4311",18-OCT-19 00.00.00,19.59218,-155.97185\r\n"HAW-B4313",18-OCT-19 00.00.00,19.31344,-155.88832\r\n')
    seed_iso(a, "0270550", [ACCESS, "Cite as: Ecosystem Sciences Division, Pacific Islands Fisheries Science Center (2022). Benthic Images from Stratified Random Site (StRS) Surveys in the Main Hawaiian Islands from 2019-10-08 to 2019-11-14 During the 2019 Bleaching Event (NCEI Accession 0270550). https://www.ncei.noaa.gov/archive/accession/0270550. Accessed [date]."])
    cands = by_name(a.discover())
    ok = a.resolve_geo(cands["HAW-B4311_2019_01.JPG"])
    assert (ok.lat, ok.lon, ok.geo_precision) == (19.59218, -155.97185, "station")
    assert cands["HAW-B4311_2019_01.JPG"].timestamp == "2019-10-18"
    miss = a.resolve_geo(cands["OAH-B3096_2019_01.JPG"])
    assert (miss.lat, miss.lon, miss.geo_precision, miss.geo_inferred) == (None, None, "none", False)
    assert "OAH-B3096" in miss.geo_source and "0270550" in miss.geo_source
    lic = a.resolve_licence(cands["OAH-B3096_2019_01.JPG"])
    assert lic.url == "https://www.fisheries.noaa.gov/inport/item/59193" and "0270550" in lic.attribution  # the bleaching set has its own InPort record


def test_ambiguous_site_code_is_not_guessed(tmp_path):
    """Synthetic: the same code twice in one CSV with two different positions and the same year."""
    a = make_adapter(tmp_path, accessions="0159155", depth="off")
    seed_2015(a)
    seed_csv(a, "0159155", "Site_Info_PRIAs_2015.csv", '"SITE","DATE_","LATITUDE","LONGITUDE"\r\n"BAK-11",08-FEB-15,0.19864,-176.48489\r\n"BAK-11",09-FEB-15,0.5,-176.4\r\n')
    g = a.resolve_geo(by_name(a.discover())["BAK-11_2015_A_03.JPG"])
    assert g.geo_precision == "none" and g.lat is None and "2 rows with different coordinates" in g.geo_source


def test_position_outside_the_pacific_box_or_out_of_range_is_rejected(tmp_path):
    """Synthetic: a plausible but non-Pacific position, and latitude / longitude swapped (|lat| > 90 cannot be a latitude)."""
    a = make_adapter(tmp_path / "box", accessions="0159155", depth="off")
    seed_2015(a)
    seed_csv(a, "0159155", "Site_Info_PRIAs_2015.csv", '"SITE","DATE_","LATITUDE","LONGITUDE"\r\n"BAK-11",08-FEB-15,45.0,10.0\r\n')
    g = a.resolve_geo(by_name(a.discover())["BAK-11_2015_A_03.JPG"])
    assert g.geo_precision == "none" and g.lat is None and "outside the Pacific sanity box" in g.geo_source
    b = make_adapter(tmp_path / "swap", accessions="0159155", depth="off")
    seed_2015(b)
    seed_csv(b, "0159155", "Site_Info_PRIAs_2015.csv", '"SITE","DATE_","LATITUDE","LONGITUDE"\r\n"BAK-11",08-FEB-15,-176.48489,0.19864\r\n')
    g = b.resolve_geo(by_name(b.discover())["BAK-11_2015_A_03.JPG"])
    assert g.geo_precision == "none" and "has no valid LATITUDE/LONGITUDE" in g.geo_source


def test_depth_off_leaves_the_position_alone(tmp_path):
    a = make_adapter(tmp_path, accessions="0317534", depth="off")
    seed_2024(a)
    g = a.resolve_geo(by_name(a.discover())["OCC-FFS-001_2024_02.JPG"])  # NoNet: no cover table is read
    assert (g.lat, g.lon, g.depth_m) == (23.878545, -166.290919, None) and g.geo_source == SRC_2024.format(code="OCC-FFS-001")


# --------------------------------------------------------------------------------------------- cover tables
def test_reduce_cover_keeps_one_row_per_site_visit():
    with open(FIX / "cover_fixed_excerpt.csv", newline="", encoding="utf-8") as fh:
        text, n = nc.reduce_cover(fh)
    assert n == 5
    rows = list(csv.DictReader(io.StringIO(text)))
    assert [r["KEY"] for r in rows] == ["BAK-11_2015", "OCC-FFS-001_2024", "OCC-FFS-002_2024", "OCC-FFS-003_2024"]  # BAK-11 has two point rows
    bak = nc.load_cover(text)["BAK-11_2015"]
    assert (bak.site, bak.visit_id, bak.min_depth, bak.max_depth, bak.depth_source, bak.rows) == ("OCC-BAK-011", "8034", 48.0, 47.0, "site", 2)
    assert nc.depth_m_of(bak) == 14.5 and nc.depth_m_of(None) is None


def test_reduce_cover_does_not_guess_when_the_rows_of_a_visit_disagree():
    """Synthetic: two point rows of one visit with different depths."""
    text = "SITE,SITEVISITID,LATITUDE,LONGITUDE,MIN_DEPTH,MAX_DEPTH,DEPTH_SOURCE,IMAGE_NAME\nX,1,1.5,-170.5,10,12,site,AAA-1_2016_A_01.JPG\nX,1,1.5,-170.5,30,32,site,AAA-1_2016_A_02.JPG\nX,1,1.5,-170.5,NA,,site,BBB-2_2016_01.JPG\n"
    rec = nc.load_cover(nc.reduce_cover(io.StringIO(text))[0])
    assert nc.depth_m_of(rec["AAA-1_2016"]) is None and (rec["AAA-1_2016"].lat, rec["AAA-1_2016"].lon) == (1.5, -170.5)
    assert nc.depth_m_of(rec["BBB-2_2016"]) is None  # NA / empty


class FakeStream:
    def __init__(self, path, status=200):
        self.status_code = status
        self._lines = Path(path).read_bytes().splitlines()

    def iter_lines(self):
        return iter(self._lines)

    def close(self):
        pass


def test_cover_table_is_streamed_once_reduced_and_cached(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, accessions="0317534")
    seed_2024(a)
    calls = []

    def request(method, url, **kw):
        calls.append((method, url, kw.get("stream")))
        return FakeStream(FIX / "cover_fixed_excerpt.csv")

    monkeypatch.setattr(a.http, "request", request)
    g = a.resolve_geo(by_name(a.discover())["OCC-FFS-001_2024_02.JPG"])
    assert g.depth_m == 24.4
    assert calls == [("GET", f"{ARCH}/arc0247/0317416/1.1/data/0-data/NCRMP_BENTHIC_COVER_FIXED_PACIFIC_2012-2025.csv", True)]
    saved = a.ctx.layout.raw / "cover" / "fixed.csv"
    assert saved.exists() and saved.stat().st_size < 2000  # a reduced table, not the 49 MB file
    again = make_adapter(tmp_path, accessions="0317534")  # a re-run reads the reduced table: NoNet would raise
    assert again.resolve_geo(by_name(again.discover())["OCC-FFS-003_2024_01.JPG"]).depth_m == 6.4


def test_an_unreadable_cover_table_costs_only_the_depth_and_is_recorded_once(tmp_path):
    a = make_adapter(tmp_path, http=Down(dry_run=True), accessions="0317534")
    seed_2024(a)
    for c in a.discover():
        g = a.resolve_geo(c)
        assert g.geo_precision == "station" and g.depth_m is None
    assert [f["stage"] for f in failures(a)] == ["depth"]  # one record, not one per image


# --------------------------------------------------------------------------------------------- ordering
def test_round_zero_takes_one_frame_of_every_visit_in_a_spread_order(tmp_path):
    a = make_adapter(tmp_path, accessions="0159155", depth="off", frames_per_visit=2)
    seed_2015(a)
    names = [c.item_id.split("/")[1] for c in a.discover()]
    # visits by survey date: BAK-11 (02-08), KIN-07 and KIN-62 (04-26) -> first, last, middle; frame 03 (centre of 4) then 02
    assert names == [
        "BAK-11_2015_A_03.JPG", "KIN-62_2015_A_03.JPG", "KIN-07_2015_A_03.JPG",
        "BAK-11_2015_A_02.JPG", "KIN-62_2015_A_02.JPG", "KIN-07_2015_A_02.JPG",
    ]  # fmt: skip


def test_frames_per_visit_all_and_table_order(tmp_path):
    a = make_adapter(tmp_path / "all", accessions="0159155", depth="off", frames_per_visit="all")
    seed_2015(a)
    cands = list(a.discover())
    assert len(cands) == 12 and len({c.item_id for c in cands}) == 12
    assert len({c.extra["station_id"] for c in cands[:3]}) == 3  # distinct stations first
    t = make_adapter(tmp_path / "tab", accessions="0159155", depth="off", frames_per_visit=3, order="table")
    seed_2015(t)
    names = [c.item_id.split("/")[1] for c in t.discover()]
    assert names[:3] == ["BAK-11_2015_A_02.JPG", "BAK-11_2015_A_03.JPG", "BAK-11_2015_A_04.JPG"] and names[3].startswith("KIN-07")  # sites in code order
    assert len(names) == 9


def test_slate_frames_and_original_twins_are_dropped(tmp_path):
    """Synthetic names in the real listing format: photo 00 is the slate; an _original twin is dropped only when the plain image exists."""
    a = make_adapter(tmp_path, accessions="0159155", depth="off", frames_per_visit="all")
    seed_2015(a, frames=0)
    seed_listing(
        a, "0159155", "Climate_Images_PRIAs_2015/",
        listing(
            entry("BAK-11_2015_A_00.JPG"), entry("BAK-11_2015_A_01.JPG"), entry("BAK-11_2015_A_01_original.JPG"),
            entry("BAK-11_2015_A_02_original.JPG"), entry("BAK-11_2015_A_31.JPG"), entry("BAK-11_2015_A_31.JPG"),
        ),
    )  # fmt: skip
    assert sorted(by_name(a.discover())) == ["BAK-11_2015_A_01.JPG", "BAK-11_2015_A_02_original.JPG", "BAK-11_2015_A_31.JPG"]  # >30 is kept, a duplicate row once


def test_a_name_that_does_not_parse_is_a_one_frame_visit_with_geo_none(tmp_path):
    a = make_adapter(tmp_path, accessions="0159155", depth="off", frames_per_visit="all")
    seed_2015(a, frames=1)
    seed_listing(a, "0159155", "Climate_Images_PRIAs_2015/", listing(entry("BAK-11_2015_A_01.JPG"), entry("stray_photo.jpg")))
    c = by_name(a.discover())["stray_photo.jpg"]
    assert a.resolve_geo(c).geo_precision == "none" and c.extra["site_code"] is None


def test_date_window_and_filters(tmp_path):
    a = make_adapter(tmp_path / "w", accessions="0159155", depth="off", frames_per_visit=1, **{"from": "2015-04-01"})
    seed_2015(a)
    assert sorted(c.extra["site_code"] for c in a.discover()) == ["KIN-07", "KIN-62"]  # the Baker visit of 2015-02-08 is outside
    b = make_adapter(tmp_path / "f", **{"kind": "climate", "regions": "marianas,samoa", "years": "2017,2018"})
    assert [x.acc for x in b.selected_accessions()] == ["0202138", "0187561"]
    assert [x.acc for x in make_adapter(tmp_path / "g", kind="strs", regions="pria", years=[2016, 2017]).selected_accessions()] == ["0176287", "0176288"]
    assert [x.acc for x in make_adapter(tmp_path / "h", accessions=[317534, "0159155"]).selected_accessions()] == ["0159155", "0317534"]
    assert len(make_adapter(tmp_path / "i").selected_accessions()) == 38
    assert [x.acc for x in make_adapter(tmp_path / "j", **{"to": "2013-12-31"}).selected_accessions()] == ["0159172", "0159144"]


def test_weights_give_every_region_the_same_share_and_climate_a_quarter(tmp_path):
    a = make_adapter(tmp_path)
    w = a._weights(a.selected_accessions())
    assert round(sum(w.values()), 9) == 1.0
    for area in nc.AREAS:
        accs = [x for x in nc.ACCESSIONS if x.area == area]
        assert round(sum(w[x.acc] for x in accs), 9) == 0.25
        assert round(sum(w[x.acc] for x in accs if x.kind == "climate"), 9) == round(0.25 * 0.25, 9)
    only = make_adapter(tmp_path / "s", kind="strs", climate_share=0.5)._weights([x for x in nc.ACCESSIONS if x.kind == "strs"])
    assert round(sum(only.values()), 9) == 1.0  # one kind present: it gets the whole share of its region


def test_budget_prefix_spreads_over_accessions_before_going_deeper(tmp_path):
    a = make_adapter(tmp_path, accessions="0317534,0159155,0240600", depth="off")
    seed_2024(a)
    seed_2015(a)
    seed_2019_nwhi(a)
    first = list(a.discover())[:5]
    assert {c.extra["ncei_accession"] for c in first} == {"0317534", "0159155", "0240600"}  # all three accessions inside the first five
    assert len({c.extra["station_id"] for c in first}) == 5  # five distinct stations
    ids1 = [c.item_id for c in a.discover()]
    b = make_adapter(tmp_path / "again", accessions="0317534,0159155,0240600", depth="off")
    seed_2024(b)
    seed_2015(b)
    seed_2019_nwhi(b)
    assert ids1 == [c.item_id for c in b.discover()] and len(set(ids1)) == len(ids1)  # stable ids and stable order across runs


# ------------------------------------------------------------------------------------ nested cruise trees
NESTED = "Cruise/CruiseData/SE1602_Jarvis/SE1602_Jarvis/Optical/JAR/REA/"
JAR_CSV = (  # real header and rows of Site_Info_PRIAs_2016.csv (0176287), CRLF as served
    '"SITE","DATE_","LATITUDE","LONGITUDE"\r\n"JAR-736",22-MAY-16,-0.38202,-160.005707\r\n"JAR-738",16-MAY-16,-0.36317,-160.004883\r\n"JAR-850",17-MAY-16,-0.374871,-159.972405\r\n'
)


def seed_jarvis(a):
    """Accession 0176287 as NCEI serves it: the raw cruise tree (folder names verified live 2026-10-07); JAR-850 under BENTHIC, JAR-738 and JAR-736 under FISH."""
    seed_listing(a, "0176287", "", listing(entry("Cruise/"), entry("FCMT29-ISO-19115-2.xml", "21K"), entry("Site_Info_PRIAs_2016.csv", "1.6K")))
    chain = ["Cruise/", "CruiseData/", "SE1602_Jarvis/", "SE1602_Jarvis/", "Optical/", "JAR/", "REA/"]
    for i, child in enumerate(chain[1:], 1):  # every level below the root lists its single child
        seed_listing(a, "0176287", "".join(chain[:i]), listing(entry(child)))
    seed_listing(a, "0176287", NESTED, listing(entry("BENTHIC/"), entry("FISH/")))
    seed_listing(a, "0176287", NESTED + "BENTHIC/", listing(entry("JAR-850/")))
    seed_listing(a, "0176287", NESTED + "FISH/", listing(entry("JAR-736/"), entry("JAR-738/")))
    seed_csv(a, "0176287", "Site_Info_PRIAs_2016.csv", JAR_CSV)
    seed_iso(a, "0176287", [ACCESS, "Cite as: Ecosystem Sciences Division, Pacific Islands Fisheries Science Center (2018). National Coral Reef Monitoring Program: Benthic images collected from stratified random sites (StRS) across Jarvis Island in the Pacific Remote Island Areas (NCEI Accession 0176287). https://www.ncei.noaa.gov/archive/accession/0176287. Accessed [date]."])


def seed_jarvis_sites(a):
    b = NESTED + "BENTHIC/JAR-850/"
    seed_listing(a, "0176287", b, listing(entry("PHOTO_QUADS/")))
    seed_listing(a, "0176287", b + "PHOTO_QUADS/", listing(entry("A/"), entry("B/")))
    seed_listing(a, "0176287", b + "PHOTO_QUADS/A/", listing(*[entry(f"JAR-850_2016_A_{n:02d}.JPG", " 3M") for n in (1, 2, 3, 4)]))
    seed_listing(a, "0176287", b + "PHOTO_QUADS/B/", listing(*[entry(f"JAR-850_2016_B_{n:02d}.JPG", " 3M") for n in (1, 2, 3)]))
    f = NESTED + "FISH/JAR-738/"
    seed_listing(a, "0176287", f, listing(entry("PHOTO_QUADS/"), entry("JAR-738_2016_A_01.JPG", " 3M")))  # synthetic: an image next to PHOTO_QUADS/ that PHOTO_QUADS/ lists as well
    seed_listing(a, "0176287", f + "PHOTO_QUADS/", listing(*[entry(f"JAR-738_2016_A_{n:02d}.JPG", " 3M") for n in (1, 2)]))
    seed_listing(a, "0176287", NESTED + "FISH/JAR-736/", listing())


def test_cruise_tree_site_folders_are_lazy_visits(tmp_path):
    """Listing the tree down to the site folders is enough to know every visit; a site folder is read only when one of its frames is picked."""
    a = make_adapter(tmp_path, accessions="0176287", depth="off")
    seed_jarvis(a)  # the site folders themselves are NOT seeded: reading one would raise AssertionError from NoNet
    visits = a._visits(nc.ACC_BY_ID["0176287"])
    assert sorted(v.site for v in visits) == ["JAR-736", "JAR-738", "JAR-850"] and all(v.frames is None for v in visits)
    assert [v.date for v in sorted(visits, key=lambda v: v.site)] == ["2016-05-22", "2016-05-16", "2016-05-17"]
    with pytest.raises(AssertionError, match="unexpected network request"):
        next(iter(a.discover()))  # the first pick needs the frames of a site folder


def test_cruise_tree_frames_geo_and_ids(tmp_path):
    a = make_adapter(tmp_path, accessions="0176287", depth="off", frames_per_visit="all")
    seed_jarvis(a)
    seed_jarvis_sites(a)
    cands = list(a.discover())
    names = [c.item_id for c in cands]
    assert len(cands) == 4 + 3 + 2 and len(set(names)) == len(names)  # JAR-850 A/ + B/, JAR-738 PHOTO_QUADS/ (the same name next to it counts once)
    assert "JAR-736" not in {c.extra["site_code"] for c in cands}  # a site folder without images yields nothing
    c = by_name(cands)["JAR-850_2016_B_02.JPG"]
    assert c.item_id == "0176287/JAR-850_2016_B_02.JPG"
    assert c.media_url == f"{ARCH}/arc0125/0176287/1.1/data/0-data/{NESTED}BENTHIC/JAR-850/PHOTO_QUADS/B/JAR-850_2016_B_02.JPG"
    assert (c.extra["replicate"], c.extra["station_id"], c.timestamp) == ("B", "0176287/JAR-850", "2016-05-17")
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_inferred) == (-0.374871, -159.972405, None, "station", True)
    assert g.geo_source.startswith("NCEI 0176287 Site_Info_PRIAs_2016.csv LATITUDE/LONGITUDE") and g.geo_source.endswith("joined on SITE = JAR-850")
    # one frame per visit first: the two stations come before any second frame of either
    assert len({x.extra["station_id"] for x in cands[:2]}) == 2
    assert a.resolve_licence(c).attribution.startswith("Ecosystem Sciences Division, Pacific Islands Fisheries Science Center (2018).")


def test_listing_that_cannot_be_read_is_recorded_and_skipped(tmp_path):
    a = make_adapter(tmp_path, http=Down(dry_run=True), accessions="0317534", depth="off")
    assert list(a.discover()) == []
    assert [f["stage"] for f in failures(a)] == ["listing"]  # recorded once, the accession is skipped


# ---------------------------------------------------------------------------------- options / estimate / media
def test_estimate_reports_the_provider_totals(tmp_path):
    est = make_adapter(tmp_path).estimate()
    assert (est["accessions"], est["climate_accessions"], est["strs_accessions"]) == (38, 17, 21)
    assert est["images_in_accessions"] == 20068 + 176597 + 20600 and est["images_estimated_counts"] == 20600
    assert est["approx_gb_all_images"] == pytest.approx(1573.5, abs=0.1) and est["frames_per_visit"] == 3
    small = make_adapter(tmp_path / "s", kind="climate", regions="samoa", frames_per_visit="all").estimate()
    assert small["accessions"] == 3 and small["frames_per_visit"] == "all" and small["images_in_accessions"] == 1439 + 894 + 1137


def test_check_ready_flags_bad_options(tmp_path):
    assert make_adapter(tmp_path / "ok").check_ready() == []
    assert make_adapter(tmp_path / "ok2", accessions="0317534", regions="Hawaii,MHI", frames_per_visit="all", depth="off").check_ready() == []
    bad = make_adapter(tmp_path / "bad", order="random", depth="deep", kind="fixed", frames_per_visit="few", accessions="1234567", regions="atlantis", years="x", climate_share=2, **{"from": "yesterday"}).check_ready()
    assert len(bad) == 9, bad
    assert any("unknown accession" in p for p in bad) and any("regions" in p or "region(s)" in p for p in bad)


def test_fetch_media_checks_for_a_jpeg(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, dry_run=False, http=NoNet(dry_run=False), accessions="0317534", depth="off")
    seed_2024(a)
    cand = by_name(a.discover())["OCC-FFS-001_2024_02.JPG"]
    dest = tmp_path / "out" / "x.jpg"

    def download(url, dst, expected_bytes=None, headers=None):
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"\xff\xd8\xff\xe1 jpeg bytes")
        return 15, "abc"

    monkeypatch.setattr(a.http, "download", download)
    assert a.fetch_media(cand, a.resolve_media(cand), dest) == (15, "abc") and dest.exists()

    def html_page(url, dst, expected_bytes=None, headers=None):
        dst.write_bytes(b"<html>Service unavailable</html>")
        return 32, "def"

    monkeypatch.setattr(a.http, "download", html_page)
    with pytest.raises(HttpError, match="not a JPEG"):
        a.fetch_media(cand, MediaRef(url=cand.media_url), dest)
    assert not dest.exists()  # an error page is never kept as an image


def test_adapter_metadata_for_the_catalogue():
    cls = get_adapter_class("noaa_ncrmp")
    assert cls.key == "noaa_ncrmp" and cls.media_types == ("image",) and cls.env_vars == ()
    assert cls.host_intervals == {"www.ncei.noaa.gov": 1.0} and cls.manual_steps.startswith("None.")
    assert cls.homepage == "https://www.fisheries.noaa.gov/inport/item/71813"


# ------------------------------------------------------------------------------------------------ the runner
def test_runner_dry_run_end_to_end(tmp_path, monkeypatch):
    seed = make_adapter(tmp_path, accessions="0317534")
    seed_2024(seed)
    seed_cover(seed)
    monkeypatch.setattr(Http, "request", lambda self, *a, **k: (_ for _ in ()).throw(AssertionError(f"unexpected network request: {a[:2]}")))
    cfg = load_config(None, data_root=tmp_path)
    s = run_source(cfg, "noaa_ncrmp", "dry-run", options={"accessions": "0317534"})
    assert s.error is None and s.candidates == 3 and s.selected == 3
    assert dict(s.selected_by_tier) == {"A": 3} and dict(s.selected_by_precision) == {"station": 3}
    assert dict(s.media_types) == {"image": 3} and s.estimate["images_in_accessions"] == 2577
    assert s.bbox == [-166.292174, 23.875517, -166.290919, 23.878545]
