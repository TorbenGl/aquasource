"""Offline tests for the canada_ogl (GSC seafloor photographs) adapter.

No test touches the network. The two per-station CSVs are the real provider files cut to 3 rows (tests/fixtures/canada_ogl,
see SOURCE.md). The Apache directory indexes are minimal synthetic pages in the same href format as the live listing.
The Http client raises on any request, so every answer must come from metadata/raw/gsc/.
"""

from pathlib import Path

import pytest

from aquasource.adapters import canada_ogl as co
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "canada_ogl"
CSV_LOW_PRECISION = (FIX / "gsc_photos_95006_7392_sample.csv").read_text(encoding="utf-8")  # station-level, 1995
CSV_USBL = (FIX / "gsc_photos_2010020_0026_sample.csv").read_text(encoding="utf-8")  # image-level, 2010
ROOT_HTML = (
    '<html><body><a href="?C=N;O=D">Name</a><a href="/pub/nrcan_rncan/raster/marine_geoscience/">Parent</a>'
    '<a href="2010020/">2010020/</a><a href="95006/">95006/</a></body></html>'
)
FOLDER_95006 = (
    '<a href="95006_7392.csv">95006_7392.csv</a><a href="7392_290_1.png">7392_290_1.png</a>'
    '<a href="7392_290_1_full_res.png">x</a>'
)
FOLDER_2010020 = '<a href="2010020_0026.csv">2010020_0026.csv</a><a href="0026_7_1_full_res.png">x</a>'


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "canada_ogl").ensure()
    raw = layout.raw / "gsc"
    (raw / "index").mkdir(parents=True, exist_ok=True)
    (raw / "index" / "root.html").write_text(ROOT_HTML)
    (raw / "index" / "95006.html").write_text(FOLDER_95006)
    (raw / "index" / "2010020.html").write_text(FOLDER_2010020)
    (raw / "csv" / "95006").mkdir(parents=True, exist_ok=True)
    (raw / "csv" / "2010020").mkdir(parents=True, exist_ok=True)
    (raw / "csv" / "95006" / "95006_7392.csv").write_text(CSV_LOW_PRECISION, encoding="utf-8")
    (raw / "csv" / "2010020" / "2010020_0026.csv").write_text(CSV_USBL, encoding="utf-8")
    ctx = Context(cfg, NoNet(dry_run=True), layout, options, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("canada_ogl")(ctx)


def by_id(cands):
    return {c.item_id: c for c in cands}


# ----------------------------------------------------------------------------------------------- pure helpers
def test_expedition_year_and_timestamp():
    assert co.expedition_year("95006") == 1995
    assert co.expedition_year("2010020") == 2010
    assert co.expedition_year("82FOGO_ISLE") == 1982
    assert co.capture_timestamp("95006", "149", "18:25:00") == "1995-05-29T18:25:00"
    assert co.capture_timestamp("95006", "149", "Unknown") == "1995-05-29"
    assert co.capture_timestamp("95006", "", "18:25:00") is None


def test_https_rewrite_and_index_parsing():
    assert co.https_url("http://ftp.maps.canada.ca/a.png") == "https://ftp.maps.canada.ca/a.png"
    assert co.folder_names(ROOT_HTML) == ["2010020", "95006"]
    assert co.file_names(FOLDER_95006) == ["95006_7392.csv", "7392_290_1.png", "7392_290_1_full_res.png"]


def test_geo_station_level_when_all_photos_share_one_position():
    rows = co.parse_station_csv(CSV_LOW_PRECISION)
    assert co.distinct_positions(rows) == 1
    geo = co.gsc_geo(rows[0], 1, "95006_7392.csv")
    assert geo.geo_precision == "station"
    assert geo.geo_inferred is True
    assert geo.lat == pytest.approx(46.963330) and geo.lon == pytest.approx(-60.3550)
    assert geo.depth_m == 60
    # pre-1990 is not the case here (1995): no-correction floor 100 m, but station minimum 500 m
    assert geo.geo_uncertainty_m == 500
    assert geo.geo_source.startswith("GSC 95006_7392.csv PHOTO_LAT/PHOTO_LONG")


def test_geo_image_level_usbl():
    rows = co.parse_station_csv(CSV_USBL)
    n = co.distinct_positions(rows)
    assert n > 1
    geo = co.gsc_geo(rows[0], n, "2010020_0026.csv")
    assert geo.geo_precision == "image"
    assert geo.geo_inferred is False
    assert geo.depth_m == 89
    assert geo.geo_uncertainty_m == 10  # USBL: 5 % of 89 m is 4.45 m, floor 10 m


def test_geo_none_without_coordinates():
    geo = co.gsc_geo({"PHOTO_LAT": "", "PHOTO_LONG": "", "WATER_DEPTH": "Unknown"}, 1, "x.csv")
    assert geo.geo_precision == "none" and geo.lat is None and geo.depth_m is None


def test_unknown_depth_is_none_and_uses_1000m_default_before_1990():
    row = {"EXPED_CD": "65034", "PHOTO_LAT": "45.0", "PHOTO_LONG": "-60.0", "WATER_DEPTH": "Unknown",
           "HORIZONTAL_POSITIONAL_ACCURACY": "no correction made"}  # fmt: skip
    geo = co.gsc_geo(row, 2, "65034_0001.csv")
    assert geo.depth_m is None
    assert geo.geo_precision == "image"
    assert geo.geo_uncertainty_m == 1000


# ----------------------------------------------------------------------------------------------- adapter
def test_discover_builds_candidates_offline(tmp_path):
    adapter = make_adapter(tmp_path, per_station=0, max_per_expedition=0)
    cands = list(adapter.discover())
    ids = by_id(cands)
    assert "95006/7392/290/1" in ids
    assert "2010020/0026/7/1" in ids
    assert len(cands) == 3 + 3  # three rows per cut CSV
    c = ids["95006/7392/290/1"]
    assert c.media_url.startswith("https://ftp.maps.canada.ca/")
    assert c.media_url.endswith("7392_290_1_full_res.png")
    assert c.ext == "png"
    assert c.timestamp == "1995-05-29T18:25:00"
    assert c.extra["positions_at_station"] == 1
    assert c.extra["film_scan"] is True
    assert c.extra["burned_in_labels_unchecked"] is True


def test_discover_respects_per_station_and_expedition_cap(tmp_path):
    adapter = make_adapter(tmp_path, per_station=1, max_per_expedition=1)
    cands = list(adapter.discover())
    assert len(cands) == 2  # one photo per expedition
    assert {c.item_id.split("/")[0] for c in cands} == {"95006", "2010020"}


def test_licence_is_tier_b_record_level(tmp_path):
    adapter = make_adapter(tmp_path, per_station=1, max_per_expedition=1)
    cand = next(iter(adapter.discover()))
    lic = adapter.resolve_licence(cand)
    assert lic.tier == "B"
    assert lic.level == "record"
    assert lic.url == co.OGL_URL
    assert "Open Government Licence" in lic.attribution


def test_no_network_for_cached_metadata(tmp_path):
    adapter = make_adapter(tmp_path, per_station=0, max_per_expedition=0)
    cands = list(adapter.discover())
    for cand in cands:
        assert adapter.resolve_licence(cand).tier == "B"
        geo = adapter.resolve_geo(cand)
        assert geo.geo_precision in ("image", "station", "none")
