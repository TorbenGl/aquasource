"""Offline tests for the ooi_cameras adapter on the real listing fixtures in tests/fixtures/ooi_cameras/ (2026-10-08).

No test touches the network. Listings are parsed with the adapter's pure helpers; licence and geo are resolved
through the adapter's own methods on an object built without a live Http client.
"""

from datetime import date
from pathlib import Path

from aquasource.adapters import ooi_cameras as oc
from aquasource.core.schema import Candidate

FIX = Path(__file__).parent / "fixtures" / "ooi_cameras"
REFDES = "RS01SBPS-PC01A-07-CAMDSC102"
DAY_URL = oc.ROOT + "RS01SBPS/PC01A/CAMDSC102/2025/06/01/"


def _adapter():
    ad = object.__new__(oc.OoiCamerasAdapter)
    ad._sites = None
    return ad


def _cand(refdes=REFDES):
    return Candidate(
        source="ooi_cameras", item_id="x", media_type="image", media_url=DAY_URL, origin_url=DAY_URL, raw={"refdes": refdes}
    )


def test_refdes_path():
    assert oc.refdes_path(REFDES) == "RS01SBPS/PC01A/CAMDSC102/"
    assert oc.refdes_path("CE04OSBP-LV01C-06-CAMDSB106") == "CE04OSBP/LV01C/CAMDSB106/"


def test_day_listing_yields_all_frames_including_suffixed_names():
    html = (FIX / "listing_2025-06-01.html").read_text()
    rows = oc.parse_day_listing(html, DAY_URL, date(2025, 6, 1))
    assert len(rows) == 325
    assert all(r["ext"] == "jpg" for r in rows)
    first = rows[0]
    assert first["name"] == "CAMDSC102_10.33.3.146_20250601T001521_UTC.jpg"
    assert first["timestamp"] == "2025-06-01T00:15:21Z"
    assert first["url"] == DAY_URL + first["name"]
    assert first["size"] == 16 * 1024**2
    suffixed = [r for r in rows if r["name"].endswith("_1.jpg")]
    assert suffixed and suffixed[0]["name"] == "CAMDSC102_10.33.3.146_20250601T011549_UTC_1.jpg"
    assert suffixed[0]["size"] == 10 * 1024**2


def test_year_and_month_listings_give_directories():
    assert oc.dir_links((FIX / "listing_2025.html").read_text())[:3] == ["01", "02", "03"]
    assert oc.dir_links((FIX / "listing_2025-06.html").read_text())[-1] == "30"
    root = oc.dir_links((FIX / "listing_camera_root.html").read_text())
    assert "2014" in root and "2026" in root


def test_parse_size():
    assert oc.parse_size("16M") == 16 * 1024**2
    assert oc.parse_size("8.4M") == int(8.4 * 1024**2)
    assert oc.parse_size("n/a") is None


def test_licence_is_tier_b_collection_level():
    lic = _adapter().resolve_licence(_cand())
    assert lic.tier == "B"
    assert lic.level == "collection"
    assert lic.url == oc.POLICY_URL


def test_geo_is_fixed_site_from_site_table():
    geo = _adapter().resolve_geo(_cand())
    assert geo.geo_precision == "fixed_site"
    assert abs(geo.lat - 44.528953) < 1e-6 and abs(geo.lon + 125.389591) < 1e-6
    assert geo.depth_m == 191.0
    assert geo.geo_inferred is False
    assert geo.geo_uncertainty_m == 20.0


def test_every_camera_in_site_table_has_a_geo():
    ad = _adapter()
    for refdes in ad._site_table():
        geo = ad.resolve_geo(_cand(refdes))
        assert -90 <= geo.lat <= 90 and -180 <= geo.lon <= 180
