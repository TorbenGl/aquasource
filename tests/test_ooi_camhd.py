"""Offline tests for the ooi_camhd adapter on the real listing fixtures in tests/fixtures/ooi_camhd/ (2026-10-08).

No test touches the network. Listings are parsed with the adapter's pure helpers; licence and geo are resolved
through the adapter's own methods on an object built without a live Http client.
"""

from datetime import date
from pathlib import Path

from aquasource.adapters import ooi_camhd as oc
from aquasource.core.schema import Candidate

FIX = Path(__file__).parent / "fixtures" / "ooi_camhd"
DAY_URL = oc.ROOT + "2016/01/01/"


def _adapter():
    ad = object.__new__(oc.OoiCamhdAdapter)
    ad._site = None
    return ad


def test_day_listing_yields_mp4_only():
    html = (FIX / "listing_2016-01-01.html").read_text()
    rows = oc.parse_day_listing(html, DAY_URL, date(2016, 1, 1))
    assert len(rows) == 8
    assert all(r["name"].endswith(".mp4") for r in rows)
    first = rows[0]
    assert first["name"] == "CAMHDA301-20160101T000000Z.mp4"
    assert first["timestamp"] == "2016-01-01T00:00:00Z"
    assert first["url"] == DAY_URL + first["name"]
    assert first["size"] == 852 * 1024**2


def test_month_and_root_listings_give_directories():
    assert oc.dir_links((FIX / "listing_2016.html").read_text())[:3] == ["01", "02", "03"]
    root = oc.dir_links((FIX / "listing_root.html").read_text())
    assert "2016" in root and "2026" in root


def test_parse_size():
    assert oc.parse_size("852M") == 852 * 1024**2
    assert oc.parse_size("13G") == 13 * 1024**3
    assert oc.parse_size("n/a") is None


def test_licence_is_tier_b():
    cand = Candidate(source="ooi_camhd", item_id="x", media_type="video", media_url=DAY_URL, origin_url=DAY_URL)
    lic = _adapter().resolve_licence(cand)
    assert lic.tier == "B"
    assert lic.level == "collection"
    assert lic.url == oc.POLICY_URL


def test_geo_is_region_from_site_table():
    cand = Candidate(source="ooi_camhd", item_id="x", media_type="video", media_url=DAY_URL, origin_url=DAY_URL)
    geo = _adapter().resolve_geo(cand)
    assert geo.geo_precision == "fixed_site"
    assert abs(geo.lat - 45.93364) < 1e-4 and abs(geo.lon + 130.01364) < 1e-4
    assert geo.depth_m == 1543.0
    assert geo.geo_inferred is False
