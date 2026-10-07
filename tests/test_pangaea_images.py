"""Offline tests for the PANGAEA image adapter, run on the real fixtures in tests/fixtures/pangaea_images/.

No test touches the network: the provider exports are copied into metadata/raw/ (like test_german_bight.py)
or served by a small fake Http. Everything built by hand is marked "synthetic" (ids 9990xx never existed).
Expected values come from tests/fixtures/pangaea_images/SOURCE.md and research/pangaea_images.md.
"""

import json
import shutil
from pathlib import Path

import pytest

from aquasource.adapters import pangaea_images as pi
from aquasource.adapters.base import Context, MediaRef, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog
from aquasource.runner import run_source

FIX = Path(__file__).parent / "fixtures" / "pangaea_images"
TABS = {
    "989684": "989684_msm77_3-5_ofos_rows.tab",
    "989683": "989683_msm77_11-1_ofos_rows.tab",
    "879298": "879298_so242_auv_rows.tab",
    "935896": "935896_so268_ofos_constant_position_rows.tab",
    "936140": "936140_ps124_ofobs_outlier_rows.tab",
}
PANMD_898338 = FIX / "898338_he153_rov_video.panmd.xml"
# Retrieved 2026-10-07 from https://doi.pangaea.de/10.1594/PANGAEA.898338?format=citation_text
CITATION_898338 = (
    "Gutt, Julian (2019): Sea-bed videos (benthos) from the shelf west of Svalbard along ROV profile HE153/1274-3 "
    "[dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.898338, In: Gutt, J (2019): Sea bed videos of the Remote "
    "Operated Vehicle SPRINT from the shelf west of Spitzbergen along 25 profiles during cruise Heincke 153 [dataset "
    "publication series]. Alfred Wegener Institute, Helmholtz Centre for Polar and Marine Research, Bremerhaven, "
    "PANGAEA, https://doi.org/10.1594/PANGAEA.898362"
)
CC_BY_4 = "Creative Commons Attribution 4.0 International (CC-BY-4.0)"
CC_BY_4_URI = "https://creativecommons.org/licenses/by/4.0/"
CC_BY_3 = "Creative Commons Attribution 3.0 Unported (CC-BY-3.0)"
DL = "https://download.pangaea.de/dataset"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, tabs=tuple(TABS), *, video=False, http=None, dry_run=True, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "pangaea_images").ensure()
    for ds_id in tabs:
        shutil.copyfile(FIX / TABS[ds_id], layout.raw / f"pangaea_{ds_id}.tab")
    if video:  # the real server answers 303 (empty body) for a dataset without data matrix
        (layout.raw / "pangaea_898338.tab").write_text("", encoding="utf-8")
        shutil.copyfile(PANMD_898338, layout.raw / "pangaea_898338.panmd.xml")
        (layout.raw / "pangaea_898338.citation.txt").write_text(CITATION_898338, encoding="utf-8")
    opts = {"check_parent": False, **options}
    if "series" not in opts and "datasets" not in opts:
        opts["datasets"] = list(tabs) + (["898338"] if video else [])
    ctx = Context(cfg, http or NoNet(dry_run=dry_run), layout, opts, dry_run, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("pangaea_images")(ctx)


def by_file(cands):
    return {c.extra["filename"]: c for c in cands}


def failures(a):
    path = a.ctx.layout.failures_jsonl
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def write_raw(a, name, text):
    (a.ctx.layout.raw / name).write_text(text, encoding="utf-8")


def synthetic_table(ds_id, rows, *, licence=CC_BY_4, uri=CC_BY_4_URI, parent=None, extra_header="", event=None, cols="Date/Time\tLatitude\tLongitude\tDepth water [m]\tIMAGE"):
    """A hand-made PANGAEA table (synthetic: never served by the provider)."""
    cit = f"Synthetic, Test (2021): Seabed photographs {ds_id} [dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.{ds_id}, "
    if parent:
        cit += f"\n\tIn: Synthetic, Test (2021): Series [dataset publication series]. PANGAEA, https://doi.org/10.1594/PANGAEA.{parent}"
    ev = event or (
        "TEST_1 * LATITUDE: -74.85 * LONGITUDE: -31.85 * DATE/TIME: 2021-02-17T00:00:00 * ELEVATION: -600.0 m "
        "* METHOD/DEVICE: Ocean Floor Observation and Bathymetry System (OFOBS)"
    )
    head = f"/* DATA DESCRIPTION:\nCitation:\t{cit}\nEvent(s):\t{ev}\n"
    if licence:
        head += f"License:\t{licence} (URI: {uri})\n"
    head += extra_header + "*/\n" + cols + "\n"
    return head + "\n".join("\t".join(r) for r in rows) + "\n"


# ------------------------------------------------------------------ helpers
def test_spread_order_prefixes_are_spread():
    assert spread(1) == [0]
    assert spread(5) == [0, 4, 2, 1, 3]
    assert sorted(spread(37)) == list(range(37))
    assert spread(8)[:4] == [0, 4, 2, 6]
    assert spread(0) == []


def spread(n):
    return pi.spread_order(n)


def test_parse_event_line_point_and_start_end():
    cands = list(make_adapter_events())
    point, span = cands
    assert (point.label, point.lat, point.lon, point.elev, point.dt) == ("MSM77_3-5", 78.61677, 5.00115, -2313.0, "2018-09-17T03:29:00")
    assert "Ocean Floor Observation System" in point.method and point.depth() == 2313.0
    assert span.label.startswith("SO242/1_41-1") and span.base_label() == "SO242/1_41-1"
    assert (span.lat, span.lon, span.lat2, span.lon2) == (-7.07428, -88.45985, -7.13375, -88.4718)
    assert (span.elev, span.elev2) == (-4152.9, -4153.9) and span.depth() == 4153.4
    assert 6000 < span.span_m < 7000


def make_adapter_events():
    for name in ("989684_msm77_3-5_ofos_rows.tab", "879298_so242_auv_rows.tab"):
        t = pi.pangaea.parse_textfile((FIX / name).read_text(encoding="utf-8"))
        yield pi.parse_event_line(t.meta["Event(s)"][0])


def test_num_strips_qc_flags_and_blanks():
    assert pi.num("") is None and pi.num(None) is None and pi.num("  ") is None
    assert pi.num("-2361.4") == -2361.4
    assert pi.num("?12.5") == 12.5
    assert pi.num("abc") is None


# ------------------------------------------------------------------ MSM77 989684: per-image coordinates, negative depth
def test_msm77_ofos_per_image_geo_licence_and_urls(tmp_path):
    a = make_adapter(tmp_path, ["989684"], keep_flagged=True)
    cands = list(a.discover())
    assert len(cands) == 5  # one per JPG; the .txt sidecar column is never a media file
    c = by_file(cands)["TIMER_2018_09_17_at_03_48_00_4W9A2106.JPG"]
    assert c.item_id == "PANGAEA.989684/TIMER_2018_09_17_at_03_48_00_4W9A2106.JPG"
    assert c.media_url == f"{DL}/989684/files/TIMER_2018_09_17_at_03_48_00_4W9A2106.JPG"
    assert c.media_type == "image" and c.ext == "jpg"
    assert c.origin_url == "https://doi.pangaea.de/10.1594/PANGAEA.989684"
    assert c.timestamp == "2018-09-17T03:48:00"
    assert c.extra["doi"] == "10.1594/PANGAEA.989684" and c.extra["parent_doi"] == "10.1594/PANGAEA.989682"
    assert c.extra["media_column"] == "IMAGE water" and c.extra["event"] == "MSM77_3-5"
    lic = a.resolve_licence(c)
    assert (lic.tier, lic.level, lic.name, lic.url) == ("B", "record", CC_BY_4, CC_BY_4_URI)
    assert lic.attribution.startswith(
        "Boehringer, Lilian; Bergmann, Melanie (2026): Seabed photographs taken along OFOS profile MSM77_3-5 "
        "during RV MARIA S. MERIAN cruise MSM77 [dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.989684, In: "
        "Boehringer, L; Bergmann, M (2026):"
    )
    assert lic.attribution.endswith(f"PANGAEA.989682 Licence: {CC_BY_4} (URI: {CC_BY_4_URI})")
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (78.616649, 5.001493, 2361.4)  # the table serves the depth negative
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("image", False, 1.59)
    assert g.geo_source == "PANGAEA 10.1594/PANGAEA.989684 data table: Latitude/Longitude (WGS84) + Depth water [m]"


def test_msm77_rows_without_position_are_deck_frames_and_fall_back_to_the_event(tmp_path):
    a = make_adapter(tmp_path, ["989684"], keep_flagged=True)
    c = by_file(a.discover())["HOTKEY_2018_09_17_at_02_43_27_4W9A2081.JPG"]
    g = a.resolve_geo(c)  # empty Latitude / Longitude cells: the event position, never an invented fix
    assert (g.lat, g.lon, g.depth_m) == (78.61677, 5.00115, 2313.0)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 4000.0)
    assert g.geo_source == "PANGAEA 10.1594/PANGAEA.989684 Event(s) MSM77_3-5 LATITUDE/LONGITUDE (event metadata), depth from ELEVATION"
    assert set(c.extra["flags"]) == {"pre_event_no_position", "pre_first_fix_no_position"}


def test_default_filter_drops_deck_frames_and_logs_it(tmp_path):
    a = make_adapter(tmp_path, ["989684"])
    cands = list(a.discover())
    assert len(cands) == 3
    assert all(c.extra["filename"].startswith("TIMER_") for c in cands)
    (line,) = [f for f in failures(a) if f["stage"] == "filter"]
    assert line["item_id"] == "PANGAEA.989684" and "pre_event_no_position" in line["reason"]


# ------------------------------------------------------------------ MSM77 989683: station only
def test_msm77_without_coordinate_columns_is_station(tmp_path):
    a = make_adapter(tmp_path, ["989683"], keep_flagged=True)
    cands = list(a.discover())
    assert len(cands) == 3
    c = by_file(cands)["TIMER_2018_09_20_at_02_58_40_4W9A3131.JPG"]
    assert c.media_url == f"{DL}/989683/files/TIMER_2018_09_20_at_02_58_40_4W9A3131.JPG"
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (79.13221, 6.26172, 1290.0)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 4000.0)
    assert g.geo_source.startswith("PANGAEA 10.1594/PANGAEA.989683 Event(s) MSM77_11-1 LATITUDE/LONGITUDE (event metadata)")
    assert a.resolve_licence(c).tier == "B"
    # row 1 (00:39) is before the event time (01:07): deck / descent frame, dropped by default
    assert len(list(make_adapter(tmp_path / "x", ["989683"]).discover())) == 2


# ------------------------------------------------------------------ SO242 AUV 879298
def test_auv_rows_ground_vis_filter_and_geo(tmp_path):
    a = make_adapter(tmp_path, ["879298"], keep_flagged=True)
    cands = by_file(a.discover())
    assert cands["20150804_034740_IMG_1785.jpg"].extra["flags"] == ["ground_vis_0"]  # altitude 10.6 m is within 12 m
    c = cands["20150804_035324_IMG_2000.jpg"]
    assert c.media_url == "https://hs.pangaea.de/Images/Benthos/SO/SO242/SO242-1_41-1/20150804_035324_IMG_2000.jpg"
    assert c.item_id == "PANGAEA.879298/20150804_035324_IMG_2000.jpg"
    assert "flags" not in c.extra
    lic = a.resolve_licence(c)
    assert (lic.tier, lic.name, lic.url) == ("B", CC_BY_3, "https://creativecommons.org/licenses/by/3.0/")
    assert lic.attribution.startswith("Greinert, Jens; Schoening, Timm; Köser, Kevin; Rothenbeck, Marcel (2017): Seafloor images")
    assert "PANGAEA.879298, In supplement to: Schoening, Timm; Köser, Kevin; Greinert, Jens (2018): An acquisition" in lic.attribution
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (-7.1247861, -88.4512639, 4140.9)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("image", False, 50.0)
    # default: only the Ground vis = 1 row survives
    (only,) = list(make_adapter(tmp_path / "d", ["879298"]).discover())
    assert only.extra["filename"] == "20150804_035324_IMG_2000.jpg"


# ------------------------------------------------------------------ SO268 935896: constant position
def test_constant_position_is_station_not_image(tmp_path):
    a = make_adapter(tmp_path, ["935896"])
    cands = list(a.discover())
    assert len(cands) == 3
    c = by_file(cands)["00952019-03-0408-37-24.JPG"]
    assert c.media_url == f"{DL}/935896/files/00952019-03-0408-37-24.JPG"  # Binary column
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (11.930071, -117.021376, 4093.9)  # Longitude column comes first in this table
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 4000.0)
    assert g.geo_source == (
        "PANGAEA 10.1594/PANGAEA.935896 data table Latitude/Longitude, constant for whole deployment "
        "(Comment: positioning failed), depth from Event ELEVATION"
    )
    assert all(a.resolve_geo(x).geo_precision == "station" for x in cands)


# ------------------------------------------------------------------ PS124 936140: provider coordinate errors
def test_ps124_outliers_held_fixes_and_missing_position(tmp_path):
    a = make_adapter(tmp_path, ["936140"], keep_flagged=True)
    cands = by_file(a.discover())
    assert len(cands) == 6

    def geo(name):
        return a.resolve_geo(cands[name])

    g = geo("TIMER_2021_02_17_at_03_37_06_IMG_0706.JPG")
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == (
        -74.84855483, -31.93127283, 612.0, "image", False, 20.0)
    g = geo("TIMER_2021_02_17_at_00_31_03_IMG_0077.JPG")
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_uncertainty_m) == (-74.84792617, -31.85133917, 649.0, "image", 20.0)
    g = geo("TIMER_2021_02_17_at_00_29_22_IMG_0071.JPG")
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_uncertainty_m) == (-74.84796933, -31.84839767, 503.0, "image", 20.0)
    # row 191: latitude -48.36 is 2,945 km off the profile -> event midpoint, never the bad fix
    c191 = cands["TIMER_2021_02_17_at_00_30_03_IMG_0074.JPG"]
    g = a.resolve_geo(c191)
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_inferred) == (-74.84848, -31.89728, 649.0, "station", True)
    assert g.geo_uncertainty_m == pytest.approx(2125, abs=15)
    assert "Event(s) PS124_26-7 LATITUDE/LONGITUDE START/END (event metadata)" in g.geo_source
    assert "position_outlier" in c191.extra["flags"]
    # row 29: ~36 km off -> station, row depth kept (380 m), dropped by the depth filter
    c29 = cands["HOTKEY_2021_02_17_at_00_09_01_IMG_0005.JPG"]
    g = a.resolve_geo(c29)
    assert (g.lat, g.lon, g.depth_m, g.geo_precision) == (-74.84848, -31.89728, 380.0, "station")
    assert {"position_outlier", "shallow_depth"} <= set(c29.extra["flags"])
    # row 129: no position, precedes the first valid fix; depth = -mean(ELEVATION START, END)
    c129 = cands["TIMER_2021_02_17_at_00_08_50_IMG_0004.JPG"]
    g = a.resolve_geo(c129)
    assert (g.lat, g.lon, g.depth_m, g.geo_precision) == (-74.84848, -31.89728, 622.9, "station")
    assert "pre_first_fix_no_position" in c129.extra["flags"]
    # default: only rows 1, 191 (station fallback) and 194 survive the filters
    kept = {c.extra["filename"] for c in make_adapter(tmp_path / "d", ["936140"]).discover()}
    assert kept == {
        "TIMER_2021_02_17_at_03_37_06_IMG_0706.JPG",
        "TIMER_2021_02_17_at_00_30_03_IMG_0074.JPG",
        "TIMER_2021_02_17_at_00_31_03_IMG_0077.JPG",
    }


def test_held_usbl_fix_raises_the_uncertainty(tmp_path):
    # synthetic: one USBL fix held for 800 s (13 min), then a moving profile
    rows = [
        ("2021-02-17T01:00:00", "-74.8500", "-31.8500", "600", "A0.JPG"),
        ("2021-02-17T01:06:40", "-74.8500", "-31.8500", "600", "A1.JPG"),
        ("2021-02-17T01:13:20", "-74.8500", "-31.8500", "600", "A2.JPG"),
        ("2021-02-17T01:13:40", "-74.8501", "-31.8501", "600", "B0.JPG"),
        ("2021-02-17T01:14:00", "-74.8502", "-31.8502", "600", "C0.JPG"),
    ]
    a = make_adapter(tmp_path, [], datasets=["999001"])
    write_raw(a, "pangaea_999001.tab", synthetic_table("999001", rows))
    c = by_file(a.discover())
    for name in ("A0.JPG", "A1.JPG", "A2.JPG"):
        g = a.resolve_geo(c[name])
        assert (g.geo_precision, g.geo_uncertainty_m) == ("image", 240.0)  # 0.3 m/s x 800 s
        assert "held_fix" in c[name].extra["flags"]
    assert a.resolve_geo(c["B0.JPG"]).geo_uncertainty_m == 20.0


def test_speed_spike_inside_the_radius_is_rejected(tmp_path):
    # synthetic: the third fix jumps 2 km in 20 s and back (inside the 3 km radius, so only the speed test sees it)
    rows = [
        ("2021-02-17T01:00:00", "-74.8500", "-31.8500", "600", "S0.JPG"),
        ("2021-02-17T01:00:20", "-74.8501", "-31.8501", "600", "S1.JPG"),
        ("2021-02-17T01:00:40", "-74.8320", "-31.8502", "600", "S2.JPG"),
        ("2021-02-17T01:01:00", "-74.8502", "-31.8503", "600", "S3.JPG"),
        ("2021-02-17T01:01:20", "-74.8503", "-31.8504", "600", "S4.JPG"),
    ]
    a = make_adapter(tmp_path, [], datasets=["999003"], keep_flagged=True)
    write_raw(a, "pangaea_999003.tab", synthetic_table("999003", rows))
    c = by_file(a.discover())
    assert a.resolve_geo(c["S2.JPG"]).geo_precision == "station" and "position_outlier" in c["S2.JPG"].extra["flags"]
    assert a.resolve_geo(c["S3.JPG"]).geo_precision == "image"


# ------------------------------------------------------------------ platform rules, media columns, memory
BEAST_EVENT = (
    "BEAST_1 * LATITUDE: 85.8 * LONGITUDE: 120.7 * DATE/TIME: 2019-11-19T09:07:00 * ELEVATION: -4404.6 m "
    "* METHOD/DEVICE: Remotely operated sensor platform BEAST (BEAST)"
)
ROV_EVENT = BEAST_EVENT.replace("Remotely operated sensor platform BEAST (BEAST)", "Remote operated vehicle (ROV)")


def test_under_ice_rov_has_no_deck_or_depth_rules(tmp_path):
    # synthetic: BEAST stills 0-20 m below the ice, no coordinate columns, some before the event time
    rows = [(f"2019-11-19T08:{m:02d}:00", d, f"S{m}.JPG") for m, d in zip(range(40, 58, 2), ("1", "6", "20", "2", "8", "12", "3", "15", "5"))]
    cols = "Date/Time\tDepth water [m]\tIMAGE"
    a = make_adapter(tmp_path, [], datasets=["999070", "999071"])
    write_raw(a, "pangaea_999070.tab", synthetic_table("999070", rows, event=BEAST_EVENT, cols=cols))
    write_raw(a, "pangaea_999071.tab", synthetic_table("999071", rows, event=ROV_EVENT, cols=cols))
    by_ds = {}
    for c in a.discover():
        by_ds.setdefault(c.extra["dataset_id"], []).append(c)
    assert len(by_ds["999070"]) == 9  # BEAST: nothing is dropped
    g = a.resolve_geo(by_ds["999070"][0])
    assert (g.geo_precision, g.lat, g.lon, g.geo_uncertainty_m) == ("station", 85.8, 120.7, 4000.0)
    assert g.depth_m in (1.0, 6.0, 20.0, 2.0, 8.0, 12.0, 3.0, 15.0, 5.0)  # the Depth water column, not the 4,404 m seafloor
    # ROV: no depth rule (terrain), but rows without position before the event time are still deck frames
    assert "999071" not in by_ds  # every row (08:40-08:56) is before the 09:07 event and has no position


def test_qualified_image_columns_and_stereo_pairs(tmp_path):
    # synthetic, after the column names of PANGAEA.921370 (left / right camera, size columns are not media)
    cols = "Date/Time\tLatitude\tLongitude\tIMAGE (left camera (LC))\tIMAGE (right camera (RM))\tIMAGE (Size) [Bytes] (left camera (LC))"
    rows = [
        ("2016-09-30T20:50:00", "86.7283", "61.6245", "L1.png", "", "896 kBytes"),
        ("2016-09-30T21:39:59", "86.7081", "61.3382", "", "R2.png", ""),
        ("2016-09-30T21:40:09", "86.7080", "61.3380", "", "", "1 kBytes"),
    ]
    a = make_adapter(tmp_path, [], datasets=["999072"], keep_flagged=True)
    write_raw(a, "pangaea_999072.tab", synthetic_table("999072", rows, cols=cols))
    c = by_file(a.discover())
    assert set(c) == {"L1.png", "R2.png"}  # the third row has no media file
    assert c["L1.png"].extra["media_column"] == "IMAGE (left camera (LC))" and c["L1.png"].media_type == "image"
    assert c["R2.png"].extra["media_column"] == "IMAGE (right camera (RM))"
    assert c["L1.png"].ext == "png"


# Trimmed copy of https://doi.pangaea.de/10.1594/PANGAEA.961934?format=textfile (retrieved 2026-10-07 by the
# adapter's extras dry run): header lines Citation, Event(s), License and both data rows, values unchanged.
TABLE_961934 = (
    "/* DATA DESCRIPTION:\n"
    "Citation:\tAnhaus, Philipp; Schiller, Martin; Planat, Noémie; Katlein, Christian; Nicolaus, Marcel (2023): Video "
    "screenshots from ROV survey ARTofMELT2023/1_22-6 on 2023-06-02, survey 2 [dataset]. PANGAEA, "
    "https://doi.org/10.1594/PANGAEA.961934, \n"
    "Event(s):\tARTofMELT2023/1_22-6 * LATITUDE: 80.089857 * LONGITUDE: 2.732341 * DATE/TIME START: 2023-06-02T09:57:00 "
    "* DATE/TIME END: 2023-06-02T15:38:00 * CAMPAIGN: ARTofMELT2023 * BASIS: Oden * METHOD/DEVICE: Remote operated vehicle (ROV)\n"
    f"License:\t{CC_BY_4} (URI: {CC_BY_4_URI})\n"
    "*/\n"
    "Date/Time\tSurvey ID\tIMAGE\n"
    "2023-06-02\t2\tARTofMELT2023_1_22_6_20230602_2_ROV_HD_camera_video_screenshot_0001.png\n"
    "2023-06-02\t2\tARTofMELT2023_1_22_6_20230602_2_ROV_HD_camera_video_screenshot_0002.png\n"
)


def test_date_only_timestamps_are_not_deck_frames(tmp_path):
    # Date/Time "2023-06-02" (no clock time) parses to midnight, before the 09:57 event start: not a deck frame
    a = make_adapter(tmp_path, [], datasets=["961934"])
    write_raw(a, "pangaea_961934.tab", TABLE_961934)
    cands = list(a.discover())
    assert len(cands) == 2 and all("flags" not in c.extra for c in cands)
    g = a.resolve_geo(cands[0])
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == (
        80.089857, 2.732341, None, "station", True, 4000.0)
    assert cands[0].timestamp == "2023-06-02"


def test_under_ice_camera_never_gets_the_seafloor_depth(tmp_path):
    # synthetic BEAST stills: one row without depth, one table without a depth column; the event ELEVATION
    # (-4404.6 m) is the seafloor below the floe, not the camera depth
    rows = [("2019-11-19T09:10:00", "0.25", "U0.JPG"), ("2019-11-19T09:10:10", "", "U1.JPG")]
    a = make_adapter(tmp_path, [], datasets=["999074", "999075"])
    write_raw(a, "pangaea_999074.tab", synthetic_table("999074", rows, event=BEAST_EVENT, cols="Date/Time\tDepth water [m]\tIMAGE"))
    write_raw(a, "pangaea_999075.tab", synthetic_table("999075", [(r[0], "W" + r[2][1:]) for r in rows], event=BEAST_EVENT, cols="Date/Time\tIMAGE"))
    c = by_file(a.discover())
    assert a.resolve_geo(c["U0.JPG"]).depth_m == 0.25
    for name in ("U1.JPG", "W0.JPG", "W1.JPG"):
        g = a.resolve_geo(c[name])
        assert (g.geo_precision, g.lat, g.depth_m) == ("station", 85.8, None)
        assert "ELEVATION" not in g.geo_source
    # the same table on a seafloor platform keeps the event depth
    b = make_adapter(tmp_path / "b", [], datasets=["999076"], keep_flagged=True)  # rows predate the synthetic OFOBS event
    write_raw(b, "pangaea_999076.tab", synthetic_table("999076", [(r[0], r[2]) for r in rows], cols="Date/Time\tIMAGE"))
    assert {b.resolve_geo(x).depth_m for x in b.discover()} == {600.0}


def test_event_coordinates_copied_into_a_multi_event_table_are_station(tmp_path):
    # synthetic: two events, the Latitude / Longitude columns repeat each event position (no per-image fix)
    ev = (
        "ST_1 * LATITUDE: -18.25 * LONGITUDE: 147.70 * DATE/TIME: 2017-01-10T00:00:00 * ELEVATION: -8.0 m * METHOD/DEVICE: Sampling by diver\n"
        "\tST_2 * LATITUDE: -18.30 * LONGITUDE: 147.75 * DATE/TIME: 2017-01-11T00:00:00 * ELEVATION: -9.0 m * METHOD/DEVICE: Sampling by diver"
    )
    rows = [
        ("ST_1", "2017-01-10T01:00:00", "-18.25", "147.70", "Q1.JPG"),
        ("ST_1", "2017-01-10T01:00:30", "-18.25", "147.70", "Q2.JPG"),
        ("ST_2", "2017-01-11T01:00:00", "-18.30", "147.75", "Q3.JPG"),
        ("ST_2", "2017-01-11T01:00:30", "-18.30", "147.75", "Q4.JPG"),
    ]
    a = make_adapter(tmp_path, [], datasets=["999077"])
    write_raw(a, "pangaea_999077.tab", synthetic_table("999077", rows, event=ev, cols="Event\tDate/Time\tLatitude\tLongitude\tIMAGE"))
    c = by_file(a.discover())
    g = a.resolve_geo(c["Q3.JPG"])
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == (-18.3, 147.75, 9.0, "station", True, 4000.0)
    assert g.geo_source.startswith("PANGAEA 10.1594/PANGAEA.999077 data table Latitude/Longitude, constant for event ST_2")
    # the same two stations with real per-photo fixes: image precision. The stations are 7.6 km apart, so the
    # outlier radius (3 km) must be applied per event, not around one median of the whole table
    moving = [(e, t, f"{float(la) - k * 0.0001:.4f}", lo, n) for k, (e, t, la, lo, n) in enumerate(rows)]
    moving += [("ST_1", "2017-01-10T01:01:00", "-18.2503", "147.70", "Q5.JPG"), ("ST_2", "2017-01-11T01:01:00", "-18.3006", "147.75", "Q6.JPG")]
    b = make_adapter(tmp_path / "b", [], datasets=["999079"])
    write_raw(b, "pangaea_999079.tab", synthetic_table("999079", moving, event=ev, cols="Event\tDate/Time\tLatitude\tLongitude\tIMAGE"))
    geos = {c.extra["filename"]: b.resolve_geo(c) for c in b.discover()}
    assert {x.geo_precision for x in geos.values()} == {"image"} and geos["Q3.JPG"].lat == -18.3002


def test_video_rows_are_segment_and_capped_per_series(tmp_path):
    # synthetic, after the column layout of PANGAEA.962099 (one .mpg per row), plus Latitude / Longitude
    rows = [(f"2023-05-31T15:{m:02d}:00", f"80.26{m:02d}", "2.7951", f"V{m}.mpg") for m in range(30, 36)]
    cols = "Date/Time\tLatitude\tLongitude\tVIDEO"
    a = make_adapter(tmp_path, [], datasets=["999078"], keep_flagged=True)
    write_raw(a, "pangaea_999078.tab", synthetic_table("999078", rows, event=ROV_EVENT, cols=cols))
    cands = list(a.discover())
    assert len(cands) == 2 and {c.media_type for c in cands} == {"video"}  # max_videos_per_series defaults to 2
    assert any("4 video rows skipped: max_videos_per_series=2" in f["reason"] for f in failures(a))
    g = a.resolve_geo(cands[0])
    assert (g.geo_precision, g.geo_inferred) == ("segment", True) and "position at the video start time" in g.geo_source
    b = make_adapter(tmp_path / "b", [], datasets=["999078"], keep_flagged=True, max_videos_per_series=5)
    write_raw(b, "pangaea_999078.tab", synthetic_table("999078", rows, event=ROV_EVENT, cols=cols))
    assert len(list(b.discover())) == 5


def test_ship_gps_positions_get_the_layback_uncertainty(tmp_path):
    # synthetic legacy OFOS table with ship's Course / Speed columns (after the layout of PANGAEA.615785)
    cols = "Date/Time\tLatitude\tLongitude\tCourse [deg]\tSpeed [kn]\tURL raw"
    rows = [("1999-07-21T10:00:00", "79.06", "4.18", "90", "0.5", "https://hs.pangaea.de/Images/x/a.tif"),
            ("1999-07-21T10:00:30", "79.0601", "4.1802", "90", "0.5", "https://hs.pangaea.de/Images/x/b.tif")]
    deep = "OFOS_1 * LATITUDE: 79.06 * LONGITUDE: 4.18 * DATE/TIME: 1999-07-21T09:00:00 * ELEVATION: -2500.0 m * METHOD/DEVICE: Ocean Floor Observation System (OFOS)"
    nodepth = deep.replace(" * ELEVATION: -2500.0 m", "")
    a = make_adapter(tmp_path, [], datasets=["999083", "999084"])
    write_raw(a, "pangaea_999083.tab", synthetic_table("999083", rows, event=deep, cols=cols))
    write_raw(a, "pangaea_999084.tab", synthetic_table("999084", rows, event=nodepth, cols=cols))
    got = {(c.extra["dataset_id"], a.resolve_geo(c).geo_uncertainty_m) for c in a.discover()}
    assert got == {("999083", 1250.0), ("999084", 2000.0)}  # 0.5 x 2500 m; the 2000 m cap when the depth is unknown


def test_same_file_name_in_two_folders_keeps_stable_ids(tmp_path):
    # synthetic: two different files with one name; the second one is a deck frame (shallow) in the default run
    cols = "Date/Time\tLatitude\tLongitude\tDepth water [m]\tURL image"
    rows = [
        ("2021-02-17T01:00:00", "-74.8500", "-31.8500", "50", "https://hs.pangaea.de/Images/A/IMG_1.JPG"),
        ("2021-02-17T01:00:20", "-74.8501", "-31.8501", "600", "https://hs.pangaea.de/Images/B/IMG_1.JPG"),
        ("2021-02-17T01:00:40", "-74.8502", "-31.8502", "600", "https://hs.pangaea.de/Images/B/IMG_2.JPG"),
        ("2021-02-17T01:01:00", "-74.8503", "-31.8503", "600", "https://hs.pangaea.de/Images/B/IMG_3.JPG"),
    ]
    ids = {}
    for keep in (True, False):
        a = make_adapter(tmp_path / str(keep), [], datasets=["999085"], keep_flagged=keep)
        write_raw(a, "pangaea_999085.tab", synthetic_table("999085", rows, cols=cols))
        ids[keep] = {c.media_url: c.item_id for c in a.discover()}
    assert ids[True]["https://hs.pangaea.de/Images/A/IMG_1.JPG"] == "PANGAEA.999085/IMG_1.JPG"
    assert ids[True]["https://hs.pangaea.de/Images/B/IMG_1.JPG"] == "PANGAEA.999085/IMG_1.JPG~1"
    assert ids[False]["https://hs.pangaea.de/Images/B/IMG_1.JPG"] == "PANGAEA.999085/IMG_1.JPG~1"  # same id when row 0 is dropped
    assert all(ids[True][u] == i for u, i in ids[False].items())


def test_urls_are_quoted_and_http_is_upgraded_and_non_media_files_are_ignored(tmp_path):
    cols = "Date/Time\tLatitude\tLongitude\tURL image\tBinary"
    rows = [
        ("2016-09-30T20:50:00", "86.7283", "61.6245", "http://hs.pangaea.de/Images/a b.jpg", ""),
        ("2016-09-30T20:51:00", "86.7284", "61.6246", "", "side scan.xtf"),
        ("2016-09-30T20:52:00", "86.7285", "61.6247", "", "with space.JPG"),
        ("2016-09-30T20:53:00", "86.7286", "61.6248", "", "../evil.JPG"),
    ]
    a = make_adapter(tmp_path, [], datasets=["999073"], keep_flagged=True)
    write_raw(a, "pangaea_999073.tab", synthetic_table("999073", rows, cols=cols))
    urls = sorted(c.media_url for c in a.discover())
    assert urls == [f"{DL}/999073/files/with%20space.JPG", "https://hs.pangaea.de/Images/a b.jpg"]  # .xtf and ../ are not media


def test_tables_are_freed_after_listing_and_discover_can_run_twice(tmp_path):
    a = make_adapter(tmp_path, ["989684"], keep_flagged=True)
    first = list(a.discover())
    assert a._datasets["989684"].table is None  # only the compact per-row arrays are kept
    again = list(a.discover())
    assert [c.item_id for c in again] == [c.item_id for c in first]
    assert a.resolve_geo(again[2]).lat == 78.616649


# ------------------------------------------------------------------ HE153 ROV video (no data matrix)
def test_rov_video_from_panmd_static_url(tmp_path):
    a = make_adapter(tmp_path, [], video=True)
    (c,) = list(a.discover())
    assert c.item_id == "PANGAEA.898338/HE153_1274-3.mpeg"
    assert c.media_url == "https://hs.pangaea.de/Movies/HE/HE153/HE153_1274-3.mpeg"
    assert (c.media_type, c.ext) == ("video", "mpeg")
    assert c.origin_url == "https://doi.pangaea.de/10.1594/PANGAEA.898338"
    assert c.timestamp == "2001-09-07T11:57:42"
    assert c.extra["parent_doi"] == "10.1594/PANGAEA.898362"
    lic = a.resolve_licence(c)
    assert (lic.tier, lic.level, lic.name, lic.url) == ("B", "record", CC_BY_4, CC_BY_4_URI)
    assert lic.attribution == f"{CITATION_898338} Licence: {CC_BY_4} (URI: {CC_BY_4_URI})"
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == pytest.approx((78.2599, 9.399692, 416.5), abs=1e-6)
    assert (g.geo_precision, g.geo_inferred) == ("station", True)
    assert g.geo_uncertainty_m == pytest.approx(1137, abs=2)  # half of the 1,273 m start-end distance + 500 m
    assert g.geo_source == (
        "PANGAEA 10.1594/PANGAEA.898338 Event(s) HE153/1274-3 LATITUDE/LONGITUDE START/END (event metadata), depth from ELEVATION"
    )
    assert a.resolve_media(c).url == c.media_url


def test_video_cap_per_series(tmp_path):
    a = make_adapter(tmp_path, [], video=True, max_videos_per_series=0)
    assert list(a.discover()) == []
    assert any("video limit" in f["reason"] for f in failures(a))


# ------------------------------------------------------------------ licences
def test_nc_child_is_not_listed_and_unknown_child_is_tier_u(tmp_path):
    rows = [("2021-02-17T01:00:00", "-74.85", "-31.85", "600", "N0.JPG"), ("2021-02-17T01:00:20", "-74.86", "-31.86", "600", "N1.JPG")]
    a = make_adapter(tmp_path, [], datasets=["999010", "999011"])
    write_raw(a, "pangaea_999010.tab", synthetic_table("999010", rows, licence="Creative Commons Attribution-NonCommercial 3.0 Unported (CC-BY-NC-3.0)", uri="https://creativecommons.org/licenses/by-nc/3.0/"))
    write_raw(a, "pangaea_999011.tab", synthetic_table("999011", rows, licence=None))
    cands = list(a.discover())
    assert {c.extra["dataset_id"] for c in cands} == {"999011"}  # the NC dataset yields nothing
    assert any(f["item_id"] == "PANGAEA.999010" and "tier X" in f["reason"] for f in failures(a))
    lic = a.resolve_licence(cands[0])
    assert (lic.tier, lic.level, lic.name) == ("U", "unknown", "not stated")


PARENT_NC = """<?xml version="1.0" encoding="UTF-8"?><md:MetaData xmlns:md="http://www.pangaea.de/MetaData">
<md:citation id="dataset999020"><md:title>Synthetic NC series</md:title><md:year>2020</md:year></md:citation>
<md:license id="license104"><md:label>CC-BY-NC-3.0</md:label><md:name>Creative Commons Attribution-NonCommercial 3.0 Unported</md:name>
<md:URI>https://creativecommons.org/licenses/by-nc/3.0/</md:URI></md:license>
<md:technicalInfo><md:entry key="hierarchyLevel" value="parent"/><md:entry key="collectionChilds" value="D999021"/>
<md:entry key="loginOption" value="unrestricted"/></md:technicalInfo></md:MetaData>"""


def test_cc_by_child_of_an_nc_parent_is_tier_u(tmp_path):
    rows = [("2021-02-17T01:00:00", "-74.85", "-31.85", "600", "P0.JPG"), ("2021-02-17T01:00:20", "-74.86", "-31.86", "600", "P1.JPG")]
    a = make_adapter(tmp_path, [], series=["999020"], check_parent=True)
    write_raw(a, "pangaea_999020.panmd.xml", PARENT_NC)
    write_raw(a, "pangaea_999021.tab", synthetic_table("999021", rows, parent="999020"))
    cands = list(a.discover())
    assert len(cands) == 2 and cands[0].extra["parent_doi"] == "10.1594/PANGAEA.999020"
    lic = a.resolve_licence(cands[0])
    assert lic.tier == "U" and "parent series PANGAEA.999020" in lic.name and CC_BY_4 in lic.name
    assert lic.level == "record" and lic.url == CC_BY_4_URI


# ------------------------------------------------------------------ series, moratorium, order
SERIES_XML = """<?xml version="1.0" encoding="UTF-8"?><md:MetaData xmlns:md="http://www.pangaea.de/MetaData">
<md:citation id="dataset{sid}"><md:title>Synthetic series</md:title></md:citation>
<md:license id="license21"><md:label>CC-BY-4.0</md:label><md:name>Creative Commons Attribution 4.0 International</md:name><md:URI>https://creativecommons.org/licenses/by/4.0/</md:URI></md:license>
<md:technicalInfo><md:entry key="hierarchyLevel" value="parent"/><md:entry key="collectionChilds" value="{kids}"/>
<md:entry key="loginOption" value="{login}"/>{extra}</md:technicalInfo></md:MetaData>"""


def series_xml(sid, kids, login="unrestricted", extra=""):
    return SERIES_XML.format(sid=sid, kids=",".join("D" + k for k in kids), login=login, extra=extra)


def test_series_expansion_moratorium_and_interleaving(tmp_path):
    restricted = series_xml(
        "999032", ["936140"], login="access rights needed", extra='<md:entry key="moratoriumUntil" value="2999-01-01"/>')
    panmd_url = "https://doi.pangaea.de/10.1594/PANGAEA.999032?format=metadata_panmd"
    http = FakeHttp({("GET", panmd_url): lambda: Resp(200, restricted.encode())}, dry_run=True)
    a = make_adapter(tmp_path, ["989684", "989683", "879298", "935896", "936140"], http=http,
                     series=["999030", "999031", "999032"], keep_flagged=True)
    write_raw(a, "pangaea_999030.panmd.xml", series_xml("999030", ["989684", "989683"]))
    write_raw(a, "pangaea_999031.panmd.xml", series_xml("999031", ["879298", "935896"]))
    write_raw(a, "pangaea_999032.panmd.xml", restricted)
    cands = list(a.discover())
    assert {c.extra["dataset_id"] for c in cands} == {"989684", "989683", "879298", "935896"}  # the moratorium series is skipped
    assert any(f["item_id"] == "PANGAEA.999032" and "moratorium until 2999-01-01" in f["reason"] for f in failures(a))
    # the restricted record is re-read once per run (not from the cache), the open ones are not
    assert [c[1] for c in http.calls] == [panmd_url]
    list(a.discover())
    assert len(http.calls) == 1
    # round robin over series, then over children: the first four candidates come from four different children
    first = cands[:4]
    assert {c.extra["series"] for c in first} == {"999030", "999031"} and len({c.extra["dataset_id"] for c in first}) == 4
    # every prefix of a child is spread over its time range: first the earliest row, then the latest
    seq = [c for c in cands if c.extra["dataset_id"] == "879298"]
    assert [c.extra["row_index"] for c in seq] == [0, 2, 1]
    assert [c.extra["filename"] for c in seq][:2] == ["20150804_034740_IMG_1785.jpg", "20150804_035324_IMG_2000.jpg"]
    # estimate counts children from the cached series metadata (no request: NoNet would fail)
    assert a.estimate() == {"series": 3, "children_open": 4, "children_restricted": 1}


def test_table_order_and_caps(tmp_path):
    a = make_adapter(tmp_path, ["989684", "879298"], order="table", keep_flagged=True, max_per_child=2)
    got = [(c.extra["dataset_id"], c.extra["row_index"]) for c in a.discover()]
    assert got == [("989684", 0), ("989684", 1), ("879298", 0), ("879298", 1)]
    a = make_adapter(tmp_path / "s", ["989684", "879298"], keep_flagged=True, max_per_series=3, series=["999040"])
    write_raw(a, "pangaea_999040.panmd.xml", series_xml("999040", ["989684", "879298"]))
    assert len(list(a.discover())) == 3


def test_overlap_and_explicit_excludes(tmp_path):
    a = make_adapter(tmp_path, [], datasets=["957274", "946149", "989684"], exclude=["989684"])
    assert list(a.discover()) == []
    reasons = " | ".join(f["reason"] for f in failures(a))
    assert "processed copy" in reasons and "obsea" in reasons and "excluded by option exclude" in reasons
    # with exclude_overlap=false the overlap ids are tried (and fail here: nothing cached, no network)
    assert make_adapter(tmp_path / "o", [], datasets=["957274"], exclude_overlap=False).excluded == {}


def test_title_filter_keeps_bathymetry_system_cameras_and_drops_side_scan(tmp_path):
    assert not pi.TITLE_EXCLUDE.search("Ocean Floor Observation and Bathymetry System (OFOBS) seafloor images")
    assert pi.TITLE_EXCLUDE.search("Side scan sonar mosaic of ...") and pi.TITLE_EXCLUDE.search("Multibeam bathymetric grid")
    rows = [("2021-02-17T01:00:00", "-74.85", "-31.85", "600", "T0.JPG")]
    a = make_adapter(tmp_path, [], datasets=["999050"])
    write_raw(a, "pangaea_999050.tab", synthetic_table("999050", rows).replace("Seabed photographs", "Side scan quicklook"))
    assert list(a.discover()) == []
    assert any("not underwater imagery" in f["reason"] for f in failures(a))


def test_items_are_stable_and_unique_across_runs(tmp_path):
    ids = [c.item_id for c in make_adapter(tmp_path, keep_flagged=True).discover()]
    again = [c.item_id for c in make_adapter(tmp_path, keep_flagged=True).discover()]
    assert ids == again and len(set(ids)) == len(ids)
    assert all(i.startswith("PANGAEA.") and "/" in i for i in ids)


# ------------------------------------------------------------------ fake provider
class Resp:
    def __init__(self, status=200, body=b"", headers=None):
        self.status_code, self.headers, self._body = status, headers or {}, body
        self.encoding = "utf-8"

    @property
    def text(self):
        return self._body.decode()

    def json(self):
        return json.loads(self.text)

    def iter_content(self, n):
        yield self._body

    def close(self):
        pass


class FakeHttp(Http):
    def __init__(self, routes=None, **kw):
        super().__init__(min_interval_s=0, **kw)
        self.routes, self.calls = routes or {}, []

    def request(self, method, url, *, kind="metadata", **kwargs):
        self.calls.append((method, url, kind, kwargs))
        r = self.routes.get((method, url))
        if r is None:
            raise AssertionError(f"unexpected {method} {url}")
        return r() if callable(r) else r


def test_textfile_redirect_is_not_followed_and_401_is_a_skip(tmp_path):
    base = "https://doi.pangaea.de/10.1594/PANGAEA."
    http = FakeHttp({
        ("GET", base + "999060?format=textfile"): Resp(401, b"<html>Error 401</html>"),
        ("GET", base + "999061?format=textfile"): Resp(303, b"", {"Location": "https://hs.pangaea.de/Movies/x.mpeg"}),
        ("GET", base + "999061?format=metadata_panmd"): Resp(200, PANMD_898338.read_bytes()),
        ("GET", base + "999061?format=citation_text"): Resp(200, b"Synthetic citation"),
    }, dry_run=True)
    a = make_adapter(tmp_path, [], http=http, datasets=["999060", "999061"])
    cands = list(a.discover())
    assert [c.extra["dataset_id"] for c in cands] == ["999061"]
    textfile = [c for c in http.calls if c[1].endswith("999061?format=textfile")][0]
    assert textfile[3]["allow_redirects"] is False  # a 303 would otherwise download the video
    assert any("restricted: HTTP 401" in f["reason"] for f in failures(a))
    assert a.resolve_licence(cands[0]).attribution.startswith("Synthetic citation Licence: ")
    # the redirect is cached as an empty table: a re-run makes no further textfile request
    assert (a.ctx.layout.raw / "pangaea_999061.tab").read_text() == ""


def test_textfile_answer_with_a_media_body_is_not_read(tmp_path):
    class MediaResp(Resp):
        def iter_content(self, n):
            raise AssertionError("the media body must not be read as metadata")

    url = "https://doi.pangaea.de/10.1594/PANGAEA.999063?format=textfile"
    http = FakeHttp({("GET", url): MediaResp(200, b"", {"Content-Type": "video/mpeg", "Content-Length": "3454525444"})}, dry_run=True)
    a = make_adapter(tmp_path, [], http=http, datasets=["999063"])
    assert a._table_text("999063") == ""  # treated like the 303 of a dataset without data matrix
    assert (a.ctx.layout.raw / "pangaea_999063.tab").read_text() == ""


def test_oversized_table_is_skipped(tmp_path):
    base = "https://doi.pangaea.de/10.1594/PANGAEA.999062?format=textfile"
    http = FakeHttp({("GET", base): Resp(200, b"x", {"Content-Length": str(40_000_000)})}, dry_run=True)
    a = make_adapter(tmp_path, [], http=http, datasets=["999062"])
    assert list(a.discover()) == []
    assert any("max_table_mb" in f["reason"] for f in failures(a))


ES_PAGE = {
    "hits": {
        "total": 3,
        "hits": [
            {"_id": "100001", "sort": [100001], "_source": {"URI": "https://doi.org/10.1594/PANGAEA.100001", "parentIdDataSet": "100000",
             "xml-thumb": "<md:SearchResult><md:citation><md:title>Seabed photographs along OFOS profile A</md:title></md:citation>"}},
            {"_id": "100002", "sort": [100002], "_source": {"URI": "https://doi.org/10.1594/PANGAEA.100002", "parentIdDataSet": "100000",
             "xml-thumb": "<md:SearchResult><md:citation><md:title>Side scan mosaic B</md:title></md:citation>"}},
            {"_id": "200001", "sort": [200001], "_source": {"URI": "https://doi.org/10.1594/PANGAEA.200001"}},
        ],
    }
}


def test_es_discovery_groups_children_by_parent(tmp_path):
    a = make_adapter(tmp_path, [], discovery=True, series=[], datasets=[])
    write_raw(a, "es_discovery_p000.json", json.dumps(ES_PAGE))  # synthetic ES answer
    groups = a._groups()
    assert [(g.series_id, g.children) for g in groups] == [("100000", ["100001", "100002"]), ("200001", ["200001"])]
    assert a.estimate()["es_discovery_datasets"] == 3
    m = make_adapter(tmp_path / "m", [], discovery=True, series=[], datasets=[], discovery_max=1)
    write_raw(m, "es_discovery_p000.json", json.dumps(ES_PAGE))
    assert [(g.series_id, g.children) for g in m._groups()] == [("100000", ["100001"])]


def test_excluded_series_also_excludes_its_children(tmp_path):
    # synthetic ES answer: two children of 957274 (processed copies of seed 935856) and one of an open series
    page = {"hits": {"total": 3, "hits": [
        {"_id": "957259", "sort": [957259], "_source": {"parentIdDataSet": "957274"}},
        {"_id": "957262", "sort": [957262], "_source": {"parentIdDataSet": "957274"}},
        {"_id": "999080", "sort": [999080], "_source": {"parentIdDataSet": "999081"}},
    ]}}
    rows = [("2021-02-17T01:00:00", "-74.85", "-31.85", "600", "E0.JPG"), ("2021-02-17T01:00:20", "-74.86", "-31.86", "600", "E1.JPG")]
    a = make_adapter(tmp_path, [], discovery=True, series=[], datasets=["999082"])
    write_raw(a, "es_discovery_p000.json", json.dumps(page))
    write_raw(a, "pangaea_999080.tab", synthetic_table("999080", rows))
    # a child reached directly (datasets=) whose citation names the excluded series as its parent
    write_raw(a, "pangaea_999082.tab", synthetic_table("999082", rows, parent="957274"))
    cands = list(a.discover())  # NoNet: the 957274 children are never even requested
    assert {c.extra["dataset_id"] for c in cands} == {"999080"}
    reasons = [f for f in failures(a) if f["stage"] == "discover"]
    assert any(f["item_id"] == "PANGAEA.957274" and "excluded series: processed copy" in f["reason"] for f in reasons)
    assert any(f["item_id"] == "PANGAEA.999082" and "parent series PANGAEA.957274" in f["reason"] for f in reasons)
    # exclude_overlap=false lets them through again
    b = make_adapter(tmp_path / "b", [], discovery=True, series=[], datasets=["999082"], exclude_overlap=False)
    write_raw(b, "es_discovery_p000.json", json.dumps({"hits": {"total": 0, "hits": []}}))
    write_raw(b, "pangaea_999082.tab", synthetic_table("999082", rows, parent="957274"))
    assert len(list(b.discover())) == 2


# ------------------------------------------------------------------ tape staging
class TapeHttp(Http):
    """download() answers 503 (tape) or an HTML page for the first calls, then the JPEG; HEAD follows head_script."""

    def __init__(self, script, head_script=()):
        super().__init__(min_interval_s=0)
        self.script, self.head_script = list(script), list(head_script)
        self.downloads, self.heads = 0, []

    def download(self, url, dest, **kw):
        self.downloads += 1
        step = self.script.pop(0) if self.script else "ok"
        if step == "503":
            raise HttpError(url, 503, "download failed")
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(b"<!DOCTYPE html><html>loading from tape</html>" if step == "html" else b"\xff\xd8\xff\xe0jpeg")
        return Path(dest).stat().st_size, "sha"

    def request(self, method, url, *, kind="metadata", **kwargs):
        self.heads.append((method, url, kind, self.max_retries))
        step = self.head_script.pop(0) if self.head_script else "200"
        if step == "503":
            return Resp(503, b"", {"Retry-After": "2", "Content-Type": "text/html"})
        if step == "html200":
            return Resp(200, b"", {"Content-Type": "text/html"})
        return Resp(200, b"", {"Content-Type": "image/jpeg"})


def test_fetch_media_polls_with_head_until_the_tape_recall_is_done(tmp_path, monkeypatch):
    sleeps = []
    monkeypatch.setattr(pi.time, "sleep", lambda s: sleeps.append(s))
    http = TapeHttp(["503", "html"], head_script=["503", "html200", "200", "200"])
    a = make_adapter(tmp_path, ["989684"], http=http, dry_run=False)
    c = next(iter(a.discover()))
    dest = tmp_path / "out" / "f.jpg"
    n, _sha = a.fetch_media(c, a.resolve_media(c), dest)
    # GET 503 -> HEAD 503 -> HEAD text/html -> HEAD 200 -> GET returns an HTML page (dropped) -> HEAD 200 -> GET ok
    assert http.downloads == 3 and len(http.heads) == 4
    assert sleeps == [15.0, 15.0, 15.0, 15.0]
    assert all(h[0] == "HEAD" and h[2] == "media" and h[3] == 0 for h in http.heads)  # HEAD polls do not retry
    assert http.max_retries == 5  # restored
    assert dest.read_bytes().startswith(b"\xff\xd8") and n == len(dest.read_bytes())  # the HTML body was never kept
    assert a._staging_seen is True


def test_fetch_media_without_tape_is_one_plain_get(tmp_path):
    http = TapeHttp([])
    a = make_adapter(tmp_path, ["989684"], http=http, dry_run=False)
    c = next(iter(a.discover()))
    a.fetch_media(c, a.resolve_media(c), tmp_path / "f.jpg")
    assert http.downloads == 1 and http.heads == []


def test_fetch_media_gives_up_after_the_timeout(tmp_path, monkeypatch):
    clock = iter(range(0, 10000, 400))
    monkeypatch.setattr(pi.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(pi.time, "sleep", lambda s: None)
    http = TapeHttp(["503"] * 20, head_script=["503"] * 20)
    a = make_adapter(tmp_path, ["989684"], http=http, dry_run=False, stage_timeout_s=900)
    c = next(iter(a.discover()))
    with pytest.raises(HttpError) as exc:
        a.fetch_media(c, MediaRef(c.media_url), tmp_path / "x.jpg")
    assert exc.value.status == 503 and "still on tape" in str(exc.value) and http.downloads == 1


def test_non_503_errors_are_not_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(pi.time, "sleep", lambda s: pytest.fail("must not wait for a 404"))

    class Gone(TapeHttp):
        def download(self, url, dest, **kw):
            raise HttpError(url, 404, "download failed")

    a = make_adapter(tmp_path, ["989684"], http=Gone([]), dry_run=False)
    c = next(iter(a.discover()))
    with pytest.raises(HttpError) as exc:
        a.fetch_media(c, MediaRef(c.media_url), tmp_path / "x.jpg")
    assert exc.value.status == 404


def test_head_poll_goes_through_the_real_http_client_without_retries(tmp_path):
    import requests

    class Session(requests.Session):
        def __init__(self):
            super().__init__()
            self.calls = []

        def request(self, method, url, **kw):
            self.calls.append((method, url))
            r = requests.Response()
            r.status_code = 503
            r._content, r._content_consumed = b"", True
            r.headers["Retry-After"] = "30"
            r.headers["Content-Type"] = "text/html"
            return r

    sess = Session()
    a = make_adapter(tmp_path, ["989684"], http=Http(min_interval_s=0, session=sess), dry_run=False)
    assert a._head_state("https://hs.pangaea.de/x.jpg") == (False, 30.0)
    assert sess.calls == [("HEAD", "https://hs.pangaea.de/x.jpg")]  # one request: a 503 is not retried or slept on
    assert a.http.max_retries == 5


def test_warm_up_heads_only_upcoming_selectable_images_after_tape_was_seen(tmp_path):
    http = TapeHttp([], head_script=["503", "200", "200", "200"])
    a = make_adapter(tmp_path, ["989684"], http=http, dry_run=False, keep_flagged=True, stage_batch=3)
    stream = a.discover()
    first = next(stream)
    assert len(a._lookahead) == 3  # the generator keeps a look-ahead window of stage_batch candidates
    a.resolve_media(first)
    assert http.heads == []  # no tape seen yet: no extra requests
    a._staging_seen = True
    a.resolve_media(first)
    urls = [h[1] for h in http.heads]
    assert urls == [first.media_url] + [c.media_url for c in a._lookahead]
    assert all(h[0] == "HEAD" and h[2] == "media" and h[3] == 0 for h in http.heads)  # no retry storm while warming
    assert http.max_retries == 5  # restored
    assert a._warmed[first.media_url] is False and all(a._warmed[u] for u in urls[1:])  # first one is still on tape
    http.heads.clear()
    a.resolve_media(first)
    assert http.heads == []  # each file is warmed once


def test_a_new_discover_does_not_replay_the_previous_look_ahead(tmp_path):
    a = make_adapter(tmp_path, ["989684"], http=TapeHttp([]), dry_run=False, keep_flagged=True, stage_batch=2)
    first = next(iter(a.discover()))  # a budget-limited run stops here with two candidates still buffered
    assert len(a._lookahead) == 2
    again = list(a.discover())
    assert again[0].item_id == first.item_id and len(again) == len({c.item_id for c in again}) == 5


# ------------------------------------------------------------------ end to end through the runner
def test_runner_dry_run_on_all_fixtures(tmp_path):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "pangaea_images").ensure()
    for ds_id, name in TABS.items():
        shutil.copyfile(FIX / name, layout.raw / f"pangaea_{ds_id}.tab")
    (layout.raw / "pangaea_898338.tab").write_text("", encoding="utf-8")
    shutil.copyfile(PANMD_898338, layout.raw / "pangaea_898338.panmd.xml")
    (layout.raw / "pangaea_898338.citation.txt").write_text(CITATION_898338, encoding="utf-8")
    stats = run_source(cfg, "pangaea_images", "dry-run", options={"datasets": [*TABS, "898338"], "check_parent": False})
    assert stats.error is None
    assert stats.candidates == 13 and stats.selected == 13  # deck frames, Ground vis 0 and outlier rows are not candidates
    assert dict(stats.selected_by_tier) == {"B": 13}
    assert dict(stats.selected_by_precision) == {"image": 6, "station": 7}
    assert dict(stats.media_types) == {"image": 12, "video": 1}
    west, south, east, north = stats.bbox
    assert -118 < west < -117 and -75 < south < -74.8 and 9.3 < east < 9.5 and 78.6 < north < 79.2


def test_adapter_metadata():
    cls = get_adapter_class("pangaea_images")
    assert cls.key == "pangaea_images" and cls.media_types == ("image", "video") and cls.env_vars == ()
    assert "prior authorisation" in cls.manual_steps and cls.host_intervals["download.pangaea.de"] >= 1.0
    assert "series" in pi.__doc__ and "extras" in pi.__doc__ and "discovery" in pi.__doc__
