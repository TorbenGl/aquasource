"""Offline tests for the noaa_oe adapter, on the real OneStop answer in tests/fixtures/noaa_oe/onestop_granules.json.

The index answer (3 granules of EX2503 DIVE16, 2026-10-08) is written into metadata/raw/ before the adapter runs, so no
test touches the network. All three granules have a low-res MP4 link; only record 3 (CRROBO_RECOVERY) has a
spatialBounding polygon. Tests that need a granule without an MP4 or with other text use copies marked "synthetic".
"""

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aquasource.adapters import noaa_oe as oe
from aquasource.adapters.base import get_adapter_class
from aquasource.core.http import Http

FIX = Path(__file__).parent / "fixtures" / "noaa_oe"
ANSWER = json.loads((FIX / "onestop_granules.json").read_text())
REC1, REC2, REC3 = (d["attributes"] for d in ANSWER["data"])
REC1_ID = "EX2503_DIVE16_20250501T025000Z_ROVHD"
REC2_ID = "EX2503_DIVE16_20250501T024938Z_ROVAUX1_RECOVERY"
REC3_ID = "EX2503_DIVE16_20250501T024928Z_CRROBO_RECOVERY"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


class FakeCtx(SimpleNamespace):
    def save_raw(self, name, content):
        path = self.layout.raw / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content if isinstance(content, str) else content.decode(), encoding="utf-8")
        return path


def make_adapter(tmp_path, answer=ANSWER, **options):
    options.setdefault("pages", 1)  # the real answer reports 112,060 granules: read one page only in tests
    raw = tmp_path / "raw"
    cache = raw / "search" / f"offset0000000_max{oe.DEFAULT_PAGE_MAX}_x_x.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(answer))
    ctx = FakeCtx(
        http=NoNet(dry_run=True),
        options=options,
        layout=SimpleNamespace(raw=raw, key="noaa_oe"),
        dry_run=True,
        failures=SimpleNamespace(write=lambda row: None),
    )
    return oe.NoaaOeAdapter(ctx)


def answer_of(*attrs_list):
    """Synthetic index answer wrapping the given attribute dicts."""
    return {"meta": {"total": len(attrs_list)}, "data": [{"attributes": a, "id": a["fileIdentifier"], "type": "granule"} for a in attrs_list]}


def test_fixture_is_real_and_ordered():
    assert [r["fileIdentifier"] for r in (REC1, REC2, REC3)] == [REC1_ID, REC2_ID, REC3_ID]
    assert ANSWER["meta"]["total"] > 100000


def test_candidates_from_real_answer(tmp_path):
    ad = make_adapter(tmp_path)
    cands = list(ad.discover())
    assert [c.item_id for c in cands] == [REC1_ID, REC2_ID, REC3_ID]
    c = cands[0]
    assert c.media_type == "video" and c.ext == "mp4"
    assert c.media_url.endswith("EX2503_VID_20250501T025000Z_ROVHD_Low.mp4")  # the _Low.mp4 link, not the oerkey page
    assert c.origin_url.startswith("https://www.nodc.noaa.gov/oer/video/?oerkey=fileIdentifier:")
    assert c.extra["cruise"] == "ex2503" and c.extra["dive"] == "DIVE16"
    assert c.timestamp == "2025-05-01T02:50:00Z"


def test_granule_without_mp4_is_skipped(tmp_path):
    no_mp4 = copy.deepcopy(REC1)
    no_mp4["links"] = [l for l in no_mp4["links"] if not l["linkUrl"].endswith(".mp4")]  # synthetic
    ad = make_adapter(tmp_path, answer=answer_of(no_mp4, REC3))
    assert [c.item_id for c in ad.discover()] == [REC3_ID]
    assert ad.skipped == {"no mp4 link": 1}


def test_noise_marker(tmp_path):
    ad = make_adapter(tmp_path)
    flags = {c.item_id: c.extra["maybe_not_underwater"] for c in ad.discover()}
    assert flags == {REC1_ID: False, REC2_ID: True, REC3_ID: True}  # ROVAUX1_RECOVERY and CRROBO_RECOVERY


def test_geo_none_without_bounding_box(tmp_path):
    ad = make_adapter(tmp_path)
    c = next(c for c in ad.discover() if c.item_id == REC1_ID)
    geo = ad.resolve_geo(c)
    assert geo.geo_precision == "none" and geo.lat is None and geo.lon is None
    assert geo.geo_source == oe.GEO_SOURCE_NONE
    assert geo.depth_m is None  # description says "between 0.0 m and 0.0 m": placeholder


def test_geo_centre_of_polygon(tmp_path):
    ad = make_adapter(tmp_path)
    c = next(c for c in ad.discover() if c.item_id == REC3_ID)
    geo = ad.resolve_geo(c)
    # ring of record 3: lon -172.53944116666668 .. -172.53876033333333, lat 23.449327166666666 .. 23.449436666666667
    assert geo.geo_precision == "segment"
    assert geo.geo_inferred is True
    assert geo.lat == pytest.approx((23.449327166666666 + 23.449436666666667) / 2)
    assert geo.lon == pytest.approx((-172.53944116666668 + -172.53876033333333) / 2)
    assert 20 < geo.geo_uncertainty_m < 60  # about 12 m x 68 m box: half diagonal about 35 m
    assert geo.depth_m is None


def test_licence_tier_a_and_copyright_tier_u(tmp_path):
    ad = make_adapter(tmp_path)
    c = next(c for c in ad.discover() if c.item_id == REC1_ID)
    lic = ad.resolve_licence(c)
    assert lic.tier == "A" and lic.level == "collection"
    assert "EX2503" in lic.attribution and "Cite the cruise" in lic.attribution

    marked = copy.deepcopy(REC1)  # synthetic
    marked["description"] += " Copyright 2025 Example Partner, all rights reserved."
    ad2 = make_adapter(tmp_path / "u", answer=answer_of(marked))
    (c2,) = list(ad2.discover())
    assert ad2.resolve_licence(c2).tier == "U"


def test_depth_from_description_range():
    assert oe.depth_range_m("recorded at Paul Seamount between 0.0 m and 0.0 m. Keywords") is None
    assert oe.depth_range_m("between 1200.0 m and 1300.0 m") == 1250.0
    assert oe.depth_range_m("no depth here") is None


def test_bbox_rejects_bad_geometry():
    assert oe.bbox_of({"spatialBounding": None}) is None
    assert oe.bbox_of({"spatialBounding": {"type": "Point", "coordinates": [1, 2]}}) is None
    assert oe.bbox_of({"spatialBounding": {"type": "Polygon", "coordinates": [[[200, 1], [201, 2]]]}}) is None


def test_options_check():
    assert oe.check_options({"from": "2025-01-01", "to": "2025-06-30", "pages": 2}) == []
    assert oe.check_options({"from": "01/01/2025"})
    assert oe.check_options({"page_max": 500})


def test_date_filter_in_request_body(tmp_path):
    ad = make_adapter(tmp_path, **{"from": "2025-05-01", "to": "2025-05-31"})
    body = ad._body(0, 100)
    dt = [f for f in body["filters"] if f["type"] == "datetime"][0]
    assert dt == {"type": "datetime", "after": "2025-05-01T00:00:00Z", "before": "2025-05-31T23:59:59Z"}
    assert body["filters"][0] == {"type": "facet", "name": "projects", "values": ["NOAAOceanExploration"]}


def test_adapter_is_registered():
    assert get_adapter_class("noaa_oe").key == "noaa_oe"
