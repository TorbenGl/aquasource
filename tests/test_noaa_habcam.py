"""Offline tests for the noaa_habcam adapter, run on the real fixtures in tests/fixtures/noaa_habcam/.

No test touches the network: the VIAME listing, metadata.txt and the R2R navigation are written into metadata/raw/
(as the adapter caches them), and the Http client raises on any request. Expected coordinates are the values of
tests/fixtures/noaa_habcam/SOURCE.md (linear interpolation between the bracketing 1-s ship fixes).
"""

import json
from pathlib import Path

import pytest

from aquasource.adapters import noaa_habcam as nh
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "noaa_habcam"
ITEMS = json.loads((FIX / "viame_items_page.json").read_text())  # 3 real items of the 2015 folder
NAV_HRS1506 = (FIX / "HRS1506_bestres_excerpt.geoCSV").read_text()
METADATA = (FIX / "metadata_txt_excerpt.csv").read_text()
N_A = "201503.20150517.160624359.187700.png"
N_B = "201503.20150517.160657817.187900.png"
N_C = "201503.20150517.160714563.188000.png"
N_FLAG = "201503.20150517.103817616.70150.png"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, items=None, *, metadata=METADATA, nav=NAV_HRS1506, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "noaa_habcam").ensure()
    (layout.raw / "viame").mkdir(parents=True, exist_ok=True)
    listing = ITEMS if items is None else items
    (layout.raw / f"viame/folder_{nh.FOLDER_2015}_offset0000000.json").write_text(json.dumps(listing))
    (layout.raw / "habcam_2015_metadata.txt").write_text(metadata or "Imagename,Altitude\n")
    if nav is not None:
        (layout.raw / "nav").mkdir(exist_ok=True)
        (layout.raw / "nav/HRS1506_bestres.geoCSV").write_text(nav)
    ctx = Context(cfg, NoNet(dry_run=True), layout, options, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("noaa_habcam")(ctx)


def item(name, size=5_000_000, iid=None):
    return {"_id": iid or f"id-{name}", "name": name, "size": size, "folderId": nh.FOLDER_2015}


def by_name(cands):
    return {c.raw["name"]: c for c in cands}


# --------------------------------------------------------------------------------------------- registry and helpers
def test_registered_and_metadata():
    cls = get_adapter_class("noaa_habcam")
    assert cls.key == "noaa_habcam" and cls.media_types == ("image",) and cls.env_vars == ()
    assert "27598" in cls.homepage and cls.manual_steps


def test_parse_name_and_leg():
    t, day = nh.parse_name(N_A)
    assert day == "2015-05-17"
    assert nh.leg_of(t) == "HRS1506"
    assert nh.parse_name("201509.20170708.060820993.10389.png") is None  # CFF naming, not the 2015 set
    assert nh.parse_name("201503.20150517.160624359.187700.jpg") is None
    t_1507, _ = nh.parse_name("201503.20150610.120000000.1.png")
    assert nh.leg_of(t_1507) == "HRS1507"
    assert nh.leg_of(nh.parse_name("201503.20150630.000000000.1.png")[0]) is None


def test_parse_bestres_flags_and_header_lines():
    fixes, flagged = nh.parse_bestres(NAV_HRS1506)
    times = [f.t for f in fixes]
    assert times == sorted(times) and len(set(times)) == len(times)
    assert len(flagged) == 4  # the #-prefixed rows bracketing 10:38:17Z
    assert len(fixes) == 9 + 4  # header and column line are not fixes


def test_resolve_geo_fixture_values(tmp_path):
    a = make_adapter(tmp_path)
    cands = by_name(a.discover())
    g = a.resolve_geo(cands[N_A])
    assert (g.lat, g.lon) == (37.687949, -74.6417)
    assert g.geo_precision == "segment" and g.geo_inferred is True and g.geo_uncertainty_m == 300.0
    assert g.depth_m is None and "R2R r2rnav HRS1506_bestres.geoCSV" in g.geo_source
    assert cands[N_A].extra["nav_flagged"] is False
    assert (a.resolve_geo(cands[N_B]).lat, a.resolve_geo(cands[N_B]).lon) == (37.687005, -74.642168)
    assert (a.resolve_geo(cands[N_C]).lat, a.resolve_geo(cands[N_C]).lon) == (37.686525, -74.642405)


def test_resolve_geo_flagged_nav_hour(tmp_path):
    a = make_adapter(tmp_path, items=[item(N_FLAG)])
    cand = by_name(a.discover())[N_FLAG]
    g = a.resolve_geo(cand)
    assert (g.lat, g.lon) == (37.90955, -74.449934)
    assert cand.extra["nav_flagged"] is True


def test_resolve_geo_gap_and_no_window(tmp_path):
    a = make_adapter(tmp_path)
    # 16:06:40 lies between the 16:06:25 and 16:06:56 fixes: 31 s apart, beyond the 10 s limit.
    gap = item("201503.20150517.160640000.1.png")
    cand = a._candidate(gap, *nh.parse_name(gap["name"]), None)
    g = a.resolve_geo(cand)
    assert g.geo_precision == "none" and g.lat is None and g.lon is None and "no fix pair" in g.geo_source
    off = item("201503.20150630.120000000.1.png")
    cand = a._candidate(off, *nh.parse_name(off["name"]), None)
    assert a.resolve_geo(cand).geo_precision == "none"


def test_licence_is_record_level_cc0(tmp_path):
    a = make_adapter(tmp_path)
    cand = by_name(a.discover())[N_A]
    lic = a.resolve_licence(cand)
    assert lic.tier == "A" and lic.level == "record" and "publicdomain/zero/1.0" in lic.url
    assert "Accession 0260576" in lic.attribution and "VIAME" in lic.attribution


# --------------------------------------------------------------------------------------------- discover
def test_discover_fixture_items_metadata_and_order(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=60)
    cands = list(a.discover())
    assert sorted(c.item_id for c in cands) == sorted(i["_id"] for i in ITEMS)
    by = by_name(cands)
    assert by[N_A].extra["altitude_m"] == 2.12 and by[N_B].extra["altitude_m"] == 1.72
    assert by[N_A].media_url == f"{nh.API}/item/{by[N_A].item_id}/download"
    assert by[N_A].extra["cruise"] == "HRS1506" and by[N_A].extra["image_day"] == "2015-05-17"
    assert by[N_A].extra["stereo_pair_px"] == [2720, 1024] and by[N_A].extra["left_half_px"] == [0, 0, 1360, 1024]
    # N_B (33 s after N_A) and N_C (50 s after N_A) are closer than 60 s: they follow the spaced frame N_A.
    assert cands[0].raw["name"] == N_A
    assert "maybe_not_underwater" not in by[N_A].extra


def test_discover_table_order_and_day_filter(tmp_path):
    a = make_adapter(tmp_path, order="table", **{"from": "2015-05-17", "to": "2015-05-17"})
    assert [c.raw["name"] for c in a.discover()] == sorted(i["name"] for i in ITEMS)
    b = make_adapter(tmp_path / "x", order="table", **{"from": "2015-05-18"})
    assert list(b.discover()) == []


def test_small_file_is_kept_and_marked(tmp_path):
    a = make_adapter(tmp_path, items=[item(N_A, size=9983), item(N_B)], metadata="Imagename,Altitude\n")
    by = by_name(a.discover())
    assert len(by) == 2
    assert by[N_A].extra["maybe_not_underwater"] is True
    assert "maybe_not_underwater" not in by[N_B].extra


def test_bad_options_are_rejected(tmp_path):
    with pytest.raises(ValueError):
        list(make_adapter(tmp_path, order="random").discover())
    with pytest.raises(ValueError):
        list(make_adapter(tmp_path / "y", **{"from": "17.05.2015"}).discover())


def test_spread_order_is_a_permutation():
    seq = list(range(11))
    out = list(nh._bitrev_order(seq))
    assert sorted(out) == seq and out[0] == 0 and out[1] == 8  # first frame, then the middle of the leg
    assert list(nh._bitrev_order([])) == []


# --------------------------------------------------------------------------------------------- media
def test_fetch_media_checks_png_magic(tmp_path):
    a = make_adapter(tmp_path)
    cand = by_name(a.discover())[N_A]
    ref = a.resolve_media(cand)
    assert ref.ext == "png" and ref.expected_bytes == 5894341

    def fake_download(url, dest, expected_bytes=None, headers=None):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"<html>not an image</html>")
        return 25, "x"

    a.http.download = fake_download
    dest = tmp_path / "out.png"
    with pytest.raises(HttpError):
        a.fetch_media(cand, ref, dest)
    assert not dest.exists()


def test_estimate_counts_listing(tmp_path):
    a = make_adapter(tmp_path)
    est = a.estimate()
    assert est["images_2015_png"] == len(ITEMS)
