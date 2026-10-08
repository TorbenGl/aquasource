"""Offline tests for the usgs_cmgp adapter, run on the real fixtures in tests/fixtures/usgs_cmgp/.

No test touches the network: the WFS answers (one-row count requests and window pages) are written into metadata/raw/wfs/
like the other adapter tests and the Http client raises on any request. The WFS fixtures are real GeoServer answers
(2026-10-08); the count files and the hand-built rows marked "synthetic" are not. HAWAII_ROW is a real row copied from a live
metadata request of 2026-10-08 (no fixture file; it shows the second column set: UUID-free numeric ids, ``photoname``,
``photo_date``).
"""

import copy
import hashlib
import json
from pathlib import Path

import pytest

from aquasource.adapters import usgs_cmgp as uc
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.licence import classify
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog
from aquasource.runner import run_source

FIX = Path(__file__).parent / "fixtures" / "usgs_cmgp"
VIDEO_ROWS = json.loads((FIX / "wfs_usgsvideoframe_video_rows.json").read_text())
PHOTO_ROWS = json.loads((FIX / "wfs_usgsvideoframe_photo_rows.json").read_text())
WOODS_ROW = json.loads((FIX / "wfs_woodshole_photo_row.json").read_text())
FRAMES = json.loads((FIX / "neighborhoodFrames_seafloor_video.json").read_text())[0]
FGDC = (FIX / "fgdc_metadata.xml").read_text(encoding="utf-8")

HAWAII_ROW = {  # live sample 2026-10-08, usgs_pacific:videopoints_hw
    "type": "Feature", "id": "videopoints_hw.fid--4b7425b6_1a11a1eee52_-c15", "geometry": {"type": "Point", "coordinates": [-156.6781, 20.5017]},
    "properties": {
        "lat": 20.501675, "lon": -156.678098, "frame": 0, "dateinfo": "41900.837303", "video": "awb_01161001", "photoname": "234.jpg",
        "picasa_id": "6256897544911358706", "picasa_album_id": "6256893359406483025", "id": -1, "cruiseid": "A-1-13-HW/Kahoolawe",
        "youtube_id": "bZdoUhjmOTg", "uid": 6, "exif_date": "2013:02:09 20:05:40", "photo_date": "2013-02-09T20:05:40Z",
    },
}  # fmt: skip

CA_PHOTO_1 = "5821795439133956497/5832451157254664642"  # row id 161881
CA_PHOTO_2 = "5821795439133956497/5832451099039975682"  # row id 161893
WOODS_ID = "6034562320271237953/6034585989059783106"  # row id 44957
GEO_CA = "WFS axiom:usgsvideoframe properties.lat/lon (row id 161881)"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def collection(features):
    return {"type": "FeatureCollection", "features": features, "numberReturned": len(features)}


def feature(props):
    return {"type": "Feature", "id": f"x.{props.get('id')}", "geometry": None, "properties": props}


def make_adapter(tmp_path, layers=None, *, dry_run=True, http=None, **options):
    """``layers``: {short name: (total photo rows, {window number: FeatureCollection})}. Seeds metadata/raw/wfs/."""
    layers = layers or {"california": (2, {0: PHOTO_ROWS})}
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "usgs_cmgp").ensure()
    size = int(options.get("page_size", uc.DEFAULT_PAGE_SIZE))
    for layer, (total, windows) in layers.items():
        d = layout.raw / "wfs" / layer
        d.mkdir(parents=True, exist_ok=True)
        (d / "count.json").write_text(json.dumps({"features": [], "totalFeatures": total, "numberMatched": total}))
        for w, data in windows.items():
            (d / f"ps{size}_w{w:06d}.json").write_text(json.dumps(data))
    options.setdefault("layers", ",".join(layers))
    ctx = Context(cfg, http or NoNet(dry_run=dry_run), layout, options, dry_run, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("usgs_cmgp")(ctx)


def by_id(cands):
    return {c.item_id: c for c in cands}


def synth(i, album="ALBUM", lat=36.5, lon=-122.0, **kw):
    """A hand-made still row (synthetic)."""
    return feature({"id": i, "lat": lat, "lon": lon, "video": "v", "frame": i, "picasa_id": f"p{i}", "picasa_album_id": album, **kw})


# --------------------------------------------------------------------------------------------- registration
def test_registered_metadata():
    cls = get_adapter_class("usgs_cmgp")
    assert cls.key == "usgs_cmgp" and cls.media_types == ("image",) and cls.env_vars == ()
    assert "10.5066/F7JH3J7N" in cls.citation and "YouTube" in cls.manual_steps


# --------------------------------------------------------------------------------------------- discover + licence + geo (real fixtures)
def test_california_stills_from_fixture(tmp_path):
    a = make_adapter(tmp_path, order="table", windows=1)
    c = by_id(a.discover())
    assert list(c) == [CA_PHOTO_1, CA_PHOTO_2]  # sortBy=id order, stable ids
    one = c[CA_PHOTO_1]
    assert one.media_type == "image" and one.ext == "jpg" and one.timestamp is None
    assert one.media_url == "https://servomatic9000.axiomalaska.com/photo-server/usgs/5821795439133956497/5832451157254664642/photo?"
    assert one.extra["video"] == "C109NC_Tape19" and one.extra["frame_s"] == 3 and one.extra["row_id"] == 161881
    assert one.extra["youtube_id"] is None and one.extra["type_name"] == "axiom:usgsvideoframe"

    lic = a.resolve_licence(one)
    assert (lic.tier, lic.level, lic.url) == ("A", "record", "https://creativecommons.org/publicdomain/zero/1.0/")
    assert lic.name.startswith("CC0 1.0")
    assert lic.attribution.startswith("U.S. Geological Survey, Coastal and Marine Geology Program. Golden, N.E., Ackerman, S.D., and Dailey, E.T., 2015")
    assert "https://doi.org/10.5066/F7JH3J7N" in lic.attribution and "5821795439133956497/5832451157254664642" in lic.attribution

    g = a.resolve_geo(one)
    assert (g.lat, g.lon, g.depth_m) == (41.151148, -124.181668, None)  # properties.lat/lon, not the 4-decimal geometry
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m, g.geo_source) == ("image", False, 10.0, GEO_CA)
    g2 = a.resolve_geo(c[CA_PHOTO_2])
    assert (g2.lat, g2.lon) == (41.15125, -124.181523)


def test_geometry_is_rounded_but_properties_are_used():
    props = PHOTO_ROWS["features"][0]["properties"]
    assert PHOTO_ROWS["features"][0]["geometry"]["coordinates"] == [-124.1817, 41.1511]
    assert uc.row_coordinate(props) == (41.151148, -124.181668)


def test_woods_hole_row_other_column_set(tmp_path):
    a = make_adapter(tmp_path, {"massachusetts": (1, {0: WOODS_ROW})}, order="table")
    (cand,) = list(a.discover())
    assert cand.item_id == WOODS_ID
    assert cand.media_url == "https://servomatic9000.axiomalaska.com/photo-server/usgs/6034562320271237953/6034585989059783106/photo?"
    assert cand.extra["photo_name"] == "IMG_1463.JPG" and cand.extra["video"] == "12035_Station_248.m4v" and cand.extra["youtube_id"] == "symjHrq59R8"
    g = a.resolve_geo(cand)
    assert (g.lat, g.lon, g.geo_precision, g.geo_inferred) == (42.369143, -70.661438, "image", False)
    assert g.geo_source == "WFS usgs_imagery:woodshole_media_points properties.lat/lon (row id 44957)"
    lic = a.resolve_licence(cand)
    assert lic.tier == "A" and "Video: YouTube channel CMG Video, id symjHrq59R8" in lic.attribution


def test_hawaii_row_timestamp_and_negative_row_id(tmp_path):
    a = make_adapter(tmp_path, {"hawaii_pacific": (1, {0: collection([HAWAII_ROW])})}, order="table")
    (cand,) = list(a.discover())
    assert cand.item_id == "6256893359406483025/6256897544911358706"
    assert cand.timestamp == "2013-02-09T20:05:40Z" and cand.extra["photo_name"] == "234.jpg" and cand.extra["cruise"] == "A-1-13-HW/Kahoolawe"
    g = a.resolve_geo(cand)
    assert (g.lat, g.lon) == (20.501675, -156.678098) and g.geo_source.endswith("(row id -1)")


def test_fgdc_fixture_carries_the_public_domain_statement():
    assert "USGS-authored or produced data and information are in the public domain" in FGDC
    assert "Please recognize and acknowledge the U.S. Geological Survey" in FGDC
    assert classify(uc.LICENCE_NAME) == "A"


# --------------------------------------------------------------------------------------------- licence edge cases
def test_non_usgs_layer_is_tier_u(tmp_path):
    a = make_adapter(tmp_path, order="table", windows=1)
    cand = list(a.discover())[0]
    other = copy.deepcopy(cand)
    other.raw["type_name"] = "axiom:cuia_points"  # CSU Monterey Bay California Undersea Imagery Archive: licence not read
    assert a.resolve_licence(other).tier == "U"
    assert a.resolve_licence(cand).tier == "A"


# --------------------------------------------------------------------------------------------- missing coordinates
def test_missing_coordinates(tmp_path):
    rows = collection([synth(1, lat=None, lon=None), synth(2), synth(3, lat=0.0, lon=0.0), synth(4, lat=95.0, lon=10.0)])
    a = make_adapter(tmp_path, {"california": (4, {0: rows})}, order="table")
    assert list(by_id(a.discover())) == ["ALBUM/p2"]  # default geo_only=true
    assert a.skipped["no coordinates"] == 3
    b = make_adapter(tmp_path, {"california": (4, {0: rows})}, order="table", geo_only="false", max_per_album=0)
    c = by_id(b.discover())
    assert sorted(c) == ["ALBUM/p1", "ALBUM/p2", "ALBUM/p3", "ALBUM/p4"]
    for iid in ("ALBUM/p1", "ALBUM/p3", "ALBUM/p4"):
        g = b.resolve_geo(c[iid])
        assert (g.lat, g.lon, g.geo_precision, g.depth_m) == (None, None, "none", None)
        assert "properties.lat/lon" in g.geo_source
    assert b.resolve_geo(c["ALBUM/p2"]).geo_precision == "image"


def test_rows_without_photo_id_are_skipped(tmp_path):
    rows = collection([synth(1, picasa_id=""), feature({"id": 2, "lat": 1.0, "lon": 1.0, "picasa_id": None, "picasa_album_id": None}), synth(3)])
    rows["features"][0]["properties"]["picasa_id"] = ""
    a = make_adapter(tmp_path, {"california": (3, {0: rows})}, order="table")
    assert list(by_id(a.discover())) == ["ALBUM/p3"] and a.skipped["no photo id"] == 2


# --------------------------------------------------------------------------------------------- ordering and caps
def test_album_cap_duplicates_and_per_window(tmp_path):
    rows = collection([synth(i, album="A1") for i in range(1, 9)] + [synth(20, album="A2"), synth(20, album="A2")])
    a = make_adapter(tmp_path, {"california": (10, {0: rows})}, order="table")
    ids = [c.item_id for c in a.discover()]
    assert ids == [f"A1/p{i}" for i in range(1, 6)] + ["A2/p20"]  # <= 5 per album, duplicate photo once
    assert a.skipped["max_per_album cap"] == 3 and a.skipped["duplicate photo"] == 1
    b = make_adapter(tmp_path, {"california": (10, {0: rows})}, order="table", max_per_album=0)
    assert len(list(b.discover())) == 9
    c = make_adapter(tmp_path, {"california": (10, {0: rows})}, order="spread", per_window=3, max_per_album=0)
    assert [x.item_id for x in c.discover()] == ["A1/p2", "A1/p6", "A2/p20"]  # 3 evenly spaced rows of the window


def test_evenly_and_window_order():
    assert uc.evenly(list(range(10)), 5) == [1, 3, 5, 7, 9]
    assert uc.evenly([1, 2], 5) == [1, 2] and uc.evenly([1, 2, 3], 0) == [1, 2, 3]
    for n in (1, 2, 7, 392):
        for seed in (0, 3):
            order = uc.window_order(n, seed)
            assert sorted(order) == list(range(n))
    first = uc.window_order(392, 0)[:8]
    assert len(set(w // 49 for w in first)) >= 7  # the first windows are spread over the table, not adjacent


def test_spread_interleaves_layers_by_sqrt_and_is_deterministic(tmp_path):
    def page(prefix, n):
        return collection([synth(i, album=f"{prefix}{i}") for i in range(1, n + 1)])

    layers = {"california": (400, {0: page("c", 40)}), "massachusetts": (100, {0: page("m", 40)})}
    kw = dict(page_size=400, per_window=0)
    first = [c.item_id for c in make_adapter(tmp_path, layers, **kw).discover()]
    again = [c.item_id for c in make_adapter(tmp_path, layers, **kw).discover()]
    assert first == again  # idempotent ids and order
    head = first[:6]
    assert sum(i.startswith("c") for i in head) == 4 and sum(i.startswith("m") for i in head) == 2  # sqrt weights 20 : 10


def test_check_ready_rejects_bad_options_and_videos(tmp_path):
    assert make_adapter(tmp_path).check_ready() == []
    bad = make_adapter(tmp_path, videos="true", order="random")
    bad.options["layers"] = "nope"
    probs = bad.check_ready()
    assert len(probs) == 3 and any("YouTube" in p for p in probs)


# --------------------------------------------------------------------------------------------- estimate
def test_estimate_reads_cached_counts(tmp_path):
    layers = {"california": (78341, {}), "hawaii_pacific": (28079, {})}
    est = make_adapter(tmp_path, layers).estimate()
    assert est["images_california"] == 78341 and est["images_total"] == 106420
    assert est["gb_estimate"] == pytest.approx((78341 * 2.65e6 + 28079 * 1.0e5) / 1e9, abs=0.1)


# --------------------------------------------------------------------------------------------- video-frame geo recipe
def nav_rows(frames):
    return [{"video": "C0212SC_Tape65", "youtube_id": "dnEQPtch7k8", "frame": v["frame"], "lat": v["lat"], "lon": v["lon"]} for v in frames.values()]


def test_video_frame_geo_on_row_interpolated_and_jump():
    rows = nav_rows(FRAMES["frames"])
    on = uc.video_frame_geo(rows, 2756.0, "axiom:usgsvideoframe")
    assert (on.lat, on.lon, on.geo_precision, on.geo_inferred, on.geo_uncertainty_m) == (36.878388, -122.02922, "image", False, 10.0)
    mid = uc.video_frame_geo(rows, 2751.0, "axiom:usgsvideoframe", youtube_id="dnEQPtch7k8")
    assert mid.geo_precision == "segment" and mid.geo_inferred is True and mid.depth_m is None
    assert mid.lat == pytest.approx((36.878378 + 36.878383) / 2, abs=1e-7) and mid.lon == pytest.approx((-122.029232 - 122.02923) / 2, abs=1e-7)
    assert mid.geo_source == "WFS axiom:usgsvideoframe properties.lat/lon interpolated on properties.frame"
    jump = uc.video_frame_geo(rows, 2757.0, "axiom:usgsvideoframe")  # 3.7 km in 2 s between frames 2756 and 2758
    assert jump.geo_precision == "none" and jump.lat is None and "navigation jump" in jump.geo_source
    assert uc.video_frame_geo(rows, 3000.0, "axiom:usgsvideoframe").geo_precision == "none"  # outside the table: no extrapolation


def test_video_frame_geo_on_ten_second_fixture_rows():
    rows = [f["properties"] for f in VIDEO_ROWS["features"]]
    g0 = uc.video_frame_geo(rows, 0, "axiom:usgsvideoframe")
    assert (g0.lat, g0.lon, g0.geo_precision, g0.geo_inferred) == (33.88664, -118.43536, "image", False)
    g5 = uc.video_frame_geo(rows, 5, "axiom:usgsvideoframe")
    assert (round(g5.lat, 5), round(g5.lon, 5), g5.geo_precision, g5.geo_inferred) == (33.88661, -118.43534, "segment", True)
    far = [dict(rows[0]), dict(rows[1], frame=25)]  # 25 s gap > 10 s
    assert uc.video_frame_geo(far, 12, "axiom:usgsvideoframe").geo_precision == "none"


# --------------------------------------------------------------------------------------------- runner dry run
def test_dry_run_through_runner(tmp_path):
    make_adapter(tmp_path, {"california": (2, {0: PHOTO_ROWS})})  # seeds the cache
    cfg = load_config(None, data_root=tmp_path)
    s = run_source(cfg, "usgs_cmgp", "dry-run", options={"layers": "california", "order": "table"})
    assert s.error is None and s.candidates == 2 and s.selected == 2
    assert dict(s.selected_by_tier) == {"A": 2} and dict(s.selected_by_precision) == {"image": 2}
    assert s.estimate["images_total"] == 2


# --------------------------------------------------------------------------------------------- media
class FakeHttp(NoNet):
    def __init__(self, payload):
        super().__init__(dry_run=False)
        self.payload, self.urls = payload, []

    def download(self, url, dest, **kw):
        self.urls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.payload)
        return len(self.payload), hashlib.sha256(self.payload).hexdigest()


def test_fetch_media_checks_jpeg_magic(tmp_path):
    good = b"\xff\xd8\xff\xe0" + b"x" * 2000
    a = make_adapter(tmp_path, dry_run=False, http=FakeHttp(good), order="table", windows=1)
    cand = list(a.discover())[0]
    ref = a.resolve_media(cand)
    assert ref.url == cand.media_url and ref.ext == "jpg"
    dest = tmp_path / "images" / "x.jpg"
    n, sha = a.fetch_media(cand, ref, dest)
    assert n == len(good) and sha == hashlib.sha256(good).hexdigest() and dest.exists()
    bad = make_adapter(tmp_path, dry_run=False, http=FakeHttp(b"<html>" + b"x" * 2000), order="table", windows=1)
    dest2 = tmp_path / "images" / "y.jpg"
    with pytest.raises(HttpError):
        bad.fetch_media(cand, ref, dest2)
    assert not dest2.exists()
