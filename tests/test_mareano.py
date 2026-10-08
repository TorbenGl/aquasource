"""Offline tests for the mareano (MAREANO frame grabs, bilder_biologi) adapter.

No test touches the network. The fixtures are real provider answers cut down (tests/fixtures/mareano, see SOURCE.md).
The Http client raises on any request, so every answer must come from metadata/raw/mareano/.
"""

from pathlib import Path

import pytest

from aquasource.adapters import mareano as mr
from aquasource.adapters.base import Context, MediaRef, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "mareano"
LAYER = (FIX / "bilder_biologi_wfs_sample.json").read_text(encoding="utf-8")
STATIONS = (FIX / "videostasjoner_sample.csv").read_text(encoding="utf-8")
SEARCH = (FIX / "imageshop_search_sample.html").read_text(encoding="utf-8")


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, **options):
    cfg = load_config(None, data_root=tmp_path, include_sharealike=True)
    layout = DatasetLayout(tmp_path, "mareano").ensure()
    raw = layout.raw / "mareano"
    (raw / "imageshop").mkdir(parents=True, exist_ok=True)
    (raw / "bilder_biologi.json").write_text(LAYER, encoding="utf-8")
    (raw / "videostasjoner_aarlig.csv").write_text(STATIONS, encoding="utf-8")
    ctx = Context(cfg, NoNet(dry_run=True), layout, options, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("mareano")(ctx), raw


def by_id(cands):
    return {c.item_id: c for c in cands}


# ----------------------------------------------------------------------------------------------- pure helpers
def test_local_timestamp_is_oslo_date():
    # DATO is local midnight stored as UTC: 22:00Z on 30 March is 31 March in Oslo (CEST, +2 h)
    assert mr.local_timestamp("2007-03-30T22:00:00Z", "") == ("2007-03-31", False)
    assert mr.local_timestamp("2006-05-26T22:00:00Z", "10:15:00") == ("2006-05-27T10:15:00", True)
    assert mr.local_timestamp(None, None) == (None, False)


def test_parse_stations_uses_wkt_full_precision():
    st = mr.parse_stations(STATIONS)
    assert st[449]["lon"] == pytest.approx(15.84851)
    assert st[449]["lat"] == pytest.approx(71.552138)
    assert st[449]["bottom_depth"] == pytest.approx(967.59)


def test_parse_imageshop_extracts_asset_fields():
    (hit,) = mr.parse_imageshop(SEARCH)
    assert hit["document_id"] == "8759556"
    assert hit["skildring"] == "Svampen Asbestopluma pennatula. Tromsøflaket, Slam, 422 m dyp"
    assert hit["kode"] == "HAV-056035"
    assert hit["kreditering"] == "Havforskningsinstituttet/MAREANO"
    assert hit["preview_url"].startswith("https://s3.eu-west-1.amazonaws.com/s.imgi.no/")
    assert "&amp;" not in hit["preview_url"]


# ----------------------------------------------------------------------------------------------- discover / licence
def test_discover_yields_all_layer_rows(tmp_path):
    ad, _ = make_adapter(tmp_path)
    cands = by_id(ad.discover())
    assert set(cands) == {"bilder_biologi.1", "bilder_biologi.10", "bilder_biologi.164"}
    c = cands["bilder_biologi.1"]
    assert c.media_type == "image" and c.ext == "jpg"
    assert c.timestamp == "2006-05-27"  # DATO 2006-05-26T22:00Z, empty TID
    assert c.extra["station"] == 5 and c.extra["cruise"] == 2006112


def test_licence_is_tier_c_at_collection_level(tmp_path):
    ad, _ = make_adapter(tmp_path)
    cand = by_id(ad.discover())["bilder_biologi.1"]
    lic = ad.resolve_licence(cand)
    assert lic.tier == "C" and lic.level == "collection"
    assert "BY-SA" in lic.name and lic.url == mr.ARCHIVE_TERMS


# ----------------------------------------------------------------------------------------------- geo
def test_geo_image_precision_from_layer_row(tmp_path):
    ad, _ = make_adapter(tmp_path)
    cand = by_id(ad.discover())["bilder_biologi.10"]
    g = ad.resolve_geo(cand)
    assert g.geo_precision == "image" and g.geo_inferred is False
    assert g.lat == pytest.approx(70.26431547) and g.lon == pytest.approx(22.481867621)
    assert g.depth_m == 257
    assert g.geo_uncertainty_m == 50
    assert g.geo_source.startswith("kart.hi.no mareano_stasjoner:bilder_biologi")


def test_geo_image_about_365_m_from_station_is_still_image(tmp_path):
    ad, _ = make_adapter(tmp_path)
    cand = by_id(ad.discover())["bilder_biologi.1"]
    g = ad.resolve_geo(cand)
    assert g.geo_precision == "image" and g.geo_inferred is False
    assert g.lat == pytest.approx(71.291374) and g.lon == pytest.approx(22.538244)
    assert g.depth_m == 422
    assert 300 < cand.extra["station_distance_m"] < 450


def test_geo_zero_depth_falls_back_to_station_bottom_depth(tmp_path):
    ad, _ = make_adapter(tmp_path)
    cand = by_id(ad.discover())["bilder_biologi.164"]
    g = ad.resolve_geo(cand)
    assert g.geo_precision == "station" and g.geo_inferred is True
    assert g.geo_uncertainty_m == 500
    assert g.depth_m == pytest.approx(270.49)
    assert "BottomDepth" in g.geo_source


# ----------------------------------------------------------------------------------------------- media
def test_resolve_media_matches_title_exactly(tmp_path, monkeypatch):
    ad, raw = make_adapter(tmp_path)
    cand = by_id(ad.discover())["bilder_biologi.1"]
    # The fixture is the search page of this title; another title must not match it.
    (raw / "imageshop" / "bilder_biologi.1.html").write_text(SEARCH, encoding="utf-8")
    ref = ad.resolve_media(cand)
    assert isinstance(ref, MediaRef) and ref.url.startswith("https://s3.eu-west-1.amazonaws.com/")
    assert cand.extra["imageshop_kode"] == "HAV-056035"
    assert cand.extra["imageshop_matches"] == 1


def test_resolve_media_rejects_non_matching_title(tmp_path):
    ad, raw = make_adapter(tmp_path)
    cand = by_id(ad.discover())["bilder_biologi.10"]
    (raw / "imageshop" / "bilder_biologi.10.html").write_text(SEARCH, encoding="utf-8")
    # legacy HI-id fallback: an empty result page, so nothing matches
    (raw / "imageshop" / "bilder_biologi.10-hi.html").write_text("<html></html>", encoding="utf-8")
    with pytest.raises(RuntimeError):
        ad.resolve_media(cand)


def test_discover_order_is_seeded_and_round_one_covers_lines(tmp_path):
    ad, _ = make_adapter(tmp_path)
    a = [c.item_id for c in ad.discover()]
    ad2, _ = make_adapter(tmp_path, seed=7)
    assert sorted(a) == sorted(c.item_id for c in ad2.discover())
    assert len(a) == 3
