"""Offline tests for the noaa_dsc adapter, on the real ERDDAP rows in tests/fixtures/noaa_dsc/erddap_records.csv.

The ERDDAP answer is written into metadata/raw/ before the adapter runs, so no test touches the network. Row 948037 is a
second record of the image 948036.JPG; row 206126 is an MBARI record that the NOAA-only query would never return (the
adapter drops it as a guard). Tests that need other rows build synthetic copies from the real ones.
"""

import csv
import io
from pathlib import Path
from types import SimpleNamespace

from aquasource.adapters import noaa_dsc as dsc
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.http import Http

FIX = Path(__file__).parent / "fixtures" / "noaa_dsc"
FIXTURE_TEXT = (FIX / "erddap_records.csv").read_text(encoding="utf-8")
IMG_SHARED = "https://www.ncei.noaa.gov/waf/dsc-data/images/000948/948036.JPG"
IMG_NOAA_ONLY = "https://www.ncei.noaa.gov/waf/dsc-data/images/001045/1045200.jpg"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, text=FIXTURE_TEXT, **options):
    raw = tmp_path / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / dsc.RAW_NAME).write_text(text, encoding="utf-8")
    ctx = Context(
        config=None,
        http=NoNet(dry_run=True),
        layout=SimpleNamespace(raw=raw, key="noaa_dsc"),
        options=options,
        dry_run=True,
        failures=SimpleNamespace(write=lambda row: None),
    )
    return dsc.NoaaDscAdapter(ctx)


def rows_with(edit):
    """Real fixture text with rows changed by ``edit(row_dict)``; ``edit`` returns False to drop a row."""
    reader = csv.DictReader(io.StringIO(FIXTURE_TEXT))
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=reader.fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in reader:
        if not row["CatalogNumber"]:  # units row: keep as is
            writer.writerow(row)
            continue
        if edit(row) is not False:
            writer.writerow(row)
    return out.getvalue()


def test_fixture_is_real_erddap_answer():
    reader = list(csv.DictReader(io.StringIO(FIXTURE_TEXT)))
    assert reader[0]["CatalogNumber"] == ""  # units row
    assert [r["CatalogNumber"] for r in reader[1:]] == ["948036", "1045200", "206126", "948037"]
    assert all(r["ImageURL"].startswith("https://www.ncei.noaa.gov/waf/dsc-data/images/") for r in reader[1:])


def test_query_asks_only_noaa_image_records():
    assert 'DataProvider=~"NOAA.*"' in dsc.QUERY
    assert 'ImageURL!=""' in dsc.QUERY


def test_registered_under_key():
    assert get_adapter_class("noaa_dsc") is dsc.NoaaDscAdapter


def test_one_candidate_per_image_and_non_noaa_dropped(tmp_path):
    ad = make_adapter(tmp_path)
    cands = list(ad.discover())
    assert [c.item_id for c in cands] == [IMG_SHARED, IMG_NOAA_ONLY]
    assert ad.skipped.get("provider not NOAA") == 1
    shared = cands[0]
    assert shared.extra["catalog_numbers"] == [948036, 948037]
    assert shared.media_type == "image" and shared.media_url == IMG_SHARED
    assert shared.extra["geo_conflict"] is False


def test_licence_tiers(tmp_path):
    shared, noaa_only = list(make_adapter(tmp_path).discover())
    # "NOAA, Northeast Fisheries Science Center | University of Connecticut": partner co-provider, tier U.
    lic_u = make_adapter(tmp_path).resolve_licence(shared)
    assert lic_u.tier == "U"
    assert lic_u.level == "collection"
    # "NOAA, Office of Ocean Exploration and Research" alone: US government work, tier A.
    lic_a = make_adapter(tmp_path).resolve_licence(noaa_only)
    assert lic_a.tier == "A"
    assert lic_a.level == "collection"
    assert lic_a.url == dsc.ISO_LANDING
    assert "1045200" in lic_a.attribution
    assert dsc.DOI in lic_a.attribution


def test_geo_is_record_coordinates_at_image_precision(tmp_path):
    shared, noaa_only = list(make_adapter(tmp_path).discover())
    ad = make_adapter(tmp_path)
    geo = ad.resolve_geo(noaa_only)
    assert (geo.lat, geo.lon, geo.depth_m) == (28.25214, -79.59882, 802.0)
    assert geo.geo_precision == "image"
    assert geo.geo_inferred is False
    assert geo.geo_uncertainty_m is None
    assert geo.geo_source == dsc.GEO_SOURCE
    geo_shared = ad.resolve_geo(shared)
    assert (geo_shared.lat, geo_shared.lon, geo_shared.depth_m) == (43.3648, -67.81296, 225.0)


def test_media_ext_is_lowercase_jpg(tmp_path):
    shared, noaa_only = list(make_adapter(tmp_path).discover())
    ad = make_adapter(tmp_path)
    assert ad.resolve_media(shared).ext == "jpg"  # .JPG in the URL
    assert ad.resolve_media(noaa_only).ext == "jpg"


def test_conflicting_coordinates_are_flagged(tmp_path):
    def move_second(row):
        if row["CatalogNumber"] == "948037":
            row["latitude"] = "43.40"

    ad = make_adapter(tmp_path, text=rows_with(move_second))
    shared = next(c for c in ad.discover() if c.item_id == IMG_SHARED)
    assert shared.extra["geo_conflict"] is True
    assert ad.resolve_geo(shared).lat == 43.3648  # lowest CatalogNumber wins


def test_record_without_coordinates_is_skipped(tmp_path):
    def blank_lat(row):
        if row["CatalogNumber"] == "1045200":
            row["latitude"] = ""

    ad = make_adapter(tmp_path, text=rows_with(blank_lat))
    assert [c.item_id for c in ad.discover()] == [IMG_SHARED]
    assert ad.skipped.get("no coordinates") == 1


def test_depth_placeholder_is_none(tmp_path):
    def no_depth(row):
        if row["CatalogNumber"] == "1045200":
            row["DepthInMeters"] = "-999"

    ad = make_adapter(tmp_path, text=rows_with(no_depth))
    noaa_only = next(c for c in ad.discover() if c.item_id == IMG_NOAA_ONLY)
    assert ad.resolve_geo(noaa_only).depth_m is None


def test_estimate_counts_from_cache(tmp_path):
    est = make_adapter(tmp_path).estimate()
    assert est["image_records_noaa"] == 3  # 948036, 1045200, 948037 (MBARI row excluded)
    assert est["distinct_images_noaa"] == 2
    assert est["distinct_images_tier_U_co_provider"] == 1
    assert est["distinct_images_tier_A_candidates"] == 1
