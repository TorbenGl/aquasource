"""Offline tests for the german_bight adapter, run on the real fixtures in tests/fixtures/german_bight/.

No test touches the network: the PANGAEA exports, the DSHIP event list and the JSON-LD record are copied
into metadata/raw/ (like the other adapter tests) and the Http client raises on any request. Expected values
come from tests/fixtures/german_bight/SOURCE.md and research/german_bight.md ("resolve_geo recipe").
Rows that were built by hand are marked "synthetic"; the sibling-cruise excerpts are verbatim rows of the live
exports retrieved 2026-10-07 (header trimmed to Citation, Event(s) and License).
"""

import json
import shutil
from pathlib import Path

import pytest

from aquasource.adapters import german_bight as gb
from aquasource.adapters.base import Context, MediaRef, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.geo import haversine_m
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog
from aquasource.runner import run_source

TESTS = Path(__file__).parent
FIX = TESTS / "fixtures" / "german_bight"
FULL_907386 = TESTS / "fixtures" / "_core" / "pangaea_907386.tab"
TABS = {
    "907386": FIX / "pangaea_907386_excerpt.tab",
    "909999": FIX / "pangaea_909999_excerpt.tab",
    "831731": FIX / "pangaea_831731_excerpt.tab",
}
EVENTS_HE436 = FIX / "events_HE436_excerpt.tab"
JSONLD_909999 = FIX / "pangaea_909999_jsonld.json"

BASE = "https://hs.pangaea.de/platforms/towed_systems/video/exdata"
CIT_907386 = (
    "Papenmeier, Svenja; Hass, H Christian (2019): Video observation during R/V Heincke cruise HE415 and HE416 in the "
    "German Bight with link to raw data files [dataset]. Alfred Wegener Institute - Wadden Sea Station Sylt, PANGAEA, "
    "https://doi.org/10.1594/PANGAEA.907386. CC BY 4.0"
)
CIT_909999 = (
    "Papenmeier, Svenja; Hass, H Christian (2019): Video observation during R/V Heincke cruise HE436 in the German "
    "Bight with link to raw data files [dataset]. Alfred Wegener Institute - Wadden Sea Station Sylt, PANGAEA, "
    "https://doi.org/10.1594/PANGAEA.909999. CC BY 4.0"
)
CIT_831731 = (
    "Mielck, Finn; Bartsch, Inka; Hass, H Christian; Wölfl, Anne-Cathrin; Bürk, Dietmar; Betzler, Christian (2014): "
    "Links to sea-bottom video files along 13 transects off Helgoland [dataset]. PANGAEA, "
    "https://doi.org/10.1594/PANGAEA.831731. CC BY 3.0"
)
CC_BY_4 = "Creative Commons Attribution 4.0 International (CC-BY-4.0)"
CC_BY_3 = "Creative Commons Attribution 3.0 Unported (CC-BY-3.0)"
SRC_HEINCKE = "PANGAEA.{id} data table columns Latitude/Longitude (ship GPS at drift-video station, WGS 84)"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, tabs=("907386", "909999", "831731"), *, full=False, events=False, jsonld=False, http=None, dry_run=True, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "german_bight").ensure()
    for ds_id in tabs:
        src = FULL_907386 if (full and ds_id == "907386") else TABS[ds_id]
        shutil.copyfile(src, layout.raw / f"pangaea_{ds_id}.tab")
    if events:
        shutil.copyfile(EVENTS_HE436, layout.raw / "dship_events_HE436.tab")
    if jsonld:
        shutil.copyfile(JSONLD_909999, layout.raw / "pangaea_909999.jsonld")
    opts = {"dataset_ids": list(tabs), "licence_check": jsonld, "qc": events, **options}
    ctx = Context(cfg, http or NoNet(dry_run=dry_run), layout, opts, dry_run, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("german_bight")(ctx)


def by_file(cands):
    return {c.item_id.split("/", 1)[1]: c for c in cands}


def failures(a):
    path = a.ctx.layout.failures_jsonl
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


def table_text(ds_id, cols, rows, *, event_campaign="HE501", licence=f"{CC_BY_4} (URI: https://creativecommons.org/licenses/by/4.0/)"):
    """A PANGAEA export with a trimmed header (Citation, Event(s), License) around the given rows."""
    return (
        "/* DATA DESCRIPTION:\n"
        f"Citation:\tAuthor, A (2019): Synthetic test table [dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.{ds_id}\n"
        f"Event(s):\t{event_campaign}-track * LOCATION: North Sea * CAMPAIGN: {event_campaign} * BASIS: Heincke\n"
        f"License:\t{licence}\n"
        "*/\n" + "\t".join(cols) + "\n" + "\n".join("\t".join(r) for r in rows) + "\n"
    )


def seed(a, ds_id, text):
    (a.ctx.layout.raw / f"pangaea_{ds_id}.tab").write_text(text, encoding="utf-8")


# ----------------------------------------------------------------------------- the classic reference case
def test_discover_and_resolve_full_export(tmp_path):
    """The full, untrimmed PANGAEA.907386 export (87 rows): one AVI per station, GoPro MP4s on request."""
    a = make_adapter(tmp_path, ("907386",), full=True)
    cands = list(a.discover())
    assert len(cands) == 87  # Kongsberg AVIs only by default: the 55 GoPro MP4 (~1.7 GB each) are opt-in
    assert len({x.item_id for x in cands}) == len(cands)
    c = cands[0]
    assert c.item_id == "PANGAEA.907386/He415_Spots_01-1.avi"
    assert c.media_type == "video" and c.ext == "avi"
    assert c.media_url == f"{BASE}/HE415/He415_Spots_01-1.avi"
    assert c.origin_url == "https://doi.pangaea.de/10.1594/PANGAEA.907386"
    assert c.timestamp == "2014-02-19T10:18:00"
    lic = a.resolve_licence(c)
    assert (lic.tier, lic.level, lic.name) == ("B", "record", CC_BY_4)
    assert lic.url == "https://creativecommons.org/licenses/by/4.0/"
    assert lic.attribution == CIT_907386
    geo = a.resolve_geo(c)
    assert (geo.lat, geo.lon, geo.depth_m) == (54.86993, 6.7144, 45.0)
    assert geo.geo_precision == "station" and geo.geo_inferred is True and geo.geo_uncertainty_m == 200.0
    assert geo.geo_source == SRC_HEINCKE.format(id="907386") + "; depth: Bathy depth [m]"


def test_all_media_counts_on_full_export(tmp_path):
    cands = list(make_adapter(tmp_path, ("907386",), full=True, media="all").discover())
    roles = [c.extra["role"] for c in cands]
    assert roles.count("station") == 87 and roles.count("gopro") == 55  # LRV / THM are never listed
    assert not [c for c in cands if c.media_url.lower().endswith((".lrv", ".thm"))]
    gopro = list(make_adapter(tmp_path / "g", ("907386",), full=True, media="gopro").discover())
    assert len(gopro) == 55 and all(c.ext == "mp4" for c in gopro)


# ---------------------------------------------------------------------------------------------- PANGAEA.907386
def test_907386_gopro_clip_is_mapped_by_station_token_not_by_listing_row(tmp_path):
    a = make_adapter(tmp_path, ("907386",), media="all")
    cands = by_file(a.discover())
    assert sorted(cands) == [
        "HE415_Greifer_AG1_005.avi",
        "HE415_Greifer_AG1_006.avi",
        "HE415_Greifer_AG1_006_HD.MP4",
        "HE415_Greifer_AG3_024.avi",
        "HE415_Greifer_AG3_024_HD.MP4",
        "He415_Spots_01-1.avi",
    ]
    mp4 = cands["HE415_Greifer_AG1_006_HD.MP4"]
    assert mp4.media_url == f"{BASE}/HE415/HE415_Greifer_AG1_006_HD.MP4"
    assert mp4.extra["role"] == "gopro" and mp4.extra["row_remapped"] is True
    assert mp4.timestamp == "2014-02-21T11:38:00"  # row AG1_006, the camera clock agrees (mvhd 12:38:36 CET)
    g = a.resolve_geo(mp4)
    assert (g.lat, g.lon, g.depth_m, g.geo_uncertainty_m) == (54.98333, 6.66713, 41.0, 200.0)
    avi005 = a.resolve_geo(cands["HE415_Greifer_AG1_005.avi"])
    assert (avi005.lat, avi005.lon, avi005.depth_m) == (54.97638, 6.69785, 41.12)
    assert 2000 < haversine_m(avi005.lat, avi005.lon, g.lat, g.lon) < 2200  # the 2.1 km the research found
    # the station video and its GoPro clip share the station id (same split); the two cruises are told apart
    assert cands["HE415_Greifer_AG1_006.avi"].extra["station_id"] == mp4.extra["station_id"] == "HE415/greifer_ag1_006"
    assert cands["HE415_Greifer_AG3_024.avi"].extra["station_id"] == cands["HE415_Greifer_AG3_024_HD.MP4"].extra["station_id"] == "HE416/greifer_ag3_024"
    assert cands["HE415_Greifer_AG3_024.avi"].extra["cruise"] == "HE416"
    assert cands["HE415_Greifer_AG1_006.avi"].extra.get("row_remapped") is None


def test_907386_columns_are_read_by_name_longitude_first(tmp_path):
    a = make_adapter(tmp_path, ("907386",))
    g = a.resolve_geo(by_file(a.discover())["HE415_Greifer_AG3_024.avi"])
    assert (g.lat, g.lon, g.depth_m) == (54.54667, 7.03933, 38.0)  # Longitude column comes before Latitude


def test_gopro_file_without_row_of_its_own_gets_no_position(tmp_path):
    """Synthetic: a GoPro file whose station token matches no row must not borrow the listing row."""
    a = make_adapter(tmp_path, ("907386",), media="all")
    text = TABS["907386"].read_text(encoding="utf-8").replace("HE415_Greifer_AG3_024_HD.MP4", "HE415_Greifer_AG9_999_HD.MP4")
    seed(a, "907386", text)
    c = by_file(a.discover())["HE415_Greifer_AG9_999_HD.MP4"]
    g = a.resolve_geo(c)
    assert g.geo_precision == "none" and g.lat is None and g.geo_inferred is False
    assert "no table row for station token 'Greifer_AG9_999'" in g.geo_source


# ---------------------------------------------------------------------------------------------- PANGAEA.909999
def test_909999_rows_files_and_licence(tmp_path):
    a = make_adapter(tmp_path, ("909999",), media="all")
    cands = by_file(a.discover())
    assert sorted(cands) == [
        "HE436_GOPRO_001.MP4",
        "HE436_GOPRO_012-1.MP4",
        "HE436_GOPRO_029.MP4",
        "He436_001.avi",
        "He436_012-1.avi",
        "He436_014.avi",  # He436_014 has no GoPro clip
        "He436_029.avi",
    ]
    c = cands["He436_001.avi"]
    assert c.item_id == "PANGAEA.909999/He436_001.avi"
    assert c.media_url == f"{BASE}/HE436/He436_001.avi"
    assert c.timestamp == "2014-11-17T03:05:51"
    lic = a.resolve_licence(c)
    assert (lic.tier, lic.level, lic.name) == ("B", "record", CC_BY_4)
    assert lic.attribution == CIT_909999
    # AVI and GoPro share the station id; the parts -1/-2 of one station share it too
    assert c.extra["station_id"] == cands["HE436_GOPRO_001.MP4"].extra["station_id"] == "HE436/001"
    assert cands["He436_012-1.avi"].extra["station_id"] == "HE436/012" and cands["He436_012-1.avi"].extra["part"] == 1


def test_909999_geo_normal_row_matches_dship_event(tmp_path):
    a = make_adapter(tmp_path, ("909999",), events=True)
    c = by_file(a.discover())["He436_001.avi"]
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (54.79, 6.00733, 41.6)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 200.0)
    assert g.geo_source == SRC_HEINCKE.format(id="909999") + "; depth: Bathy depth [m]"
    assert c.extra["qc_event"] == "HE436/003-2" and c.extra["qc_distance_m"] == 37  # table to event start, SOURCE.md
    assert "qc_flag" not in c.extra


def test_909999_missing_depth_is_none_not_zero(tmp_path):
    a = make_adapter(tmp_path, ("909999",), events=True)
    c = by_file(a.discover())["He436_012-1.avi"]
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (54.90007, 6.646, None)
    assert g.geo_precision == "station" and g.geo_uncertainty_m == 200.0
    assert g.geo_source == SRC_HEINCKE.format(id="909999")  # no depth field to cite
    assert c.extra["qc_event"] == "HE436/014-1" and c.extra["qc_distance_m"] == 8


def test_909999_longitude_typo_keeps_coordinate_and_inflates_uncertainty(tmp_path):
    a = make_adapter(tmp_path, ("909999",), events=True)
    c = by_file(a.discover())["He436_029.avi"]
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (54.69607, 7.10933, 33.2)  # the table value is kept, never replaced
    assert g.geo_precision == "station" and g.geo_inferred is True
    assert g.geo_uncertainty_m == 3430.0  # round(3226 + 200, -1)
    assert g.geo_source == (
        SRC_HEINCKE.format(id="909999") + "; depth: Bathy depth [m]; QC: table position differs by 3226 m from DSHIP event HE436/032-2"
    )
    assert c.extra["qc_flag"] == "position_disagrees_with_dship_event" and c.extra["qc_event"] == "HE436/032-2"


def test_qc_off_and_qc_reject(tmp_path):
    a = make_adapter(tmp_path / "off", ("909999",), events=True, qc=False)
    g = a.resolve_geo(by_file(a.discover())["He436_029.avi"])
    assert g.geo_uncertainty_m == 200.0 and "QC" not in g.geo_source
    b = make_adapter(tmp_path / "rej", ("909999",), events=True, qc_reject_m=1000)
    gb_ = b.resolve_geo(by_file(b.discover())["He436_029.avi"])
    assert gb_.geo_precision == "none" and gb_.lat is None and gb_.depth_m == 33.2
    assert "rejected" in gb_.geo_source and "3226 m" in gb_.geo_source


def test_qc_without_matching_event_keeps_step_five(tmp_path):
    """Synthetic: a row 20 minutes after the last video event has no event to compare with."""
    a = make_adapter(tmp_path, ("909999",), events=True)
    text = TABS["909999"].read_text(encoding="utf-8").replace("2014-11-17T14:46:06", "2014-11-17T20:00:00")
    seed(a, "909999", text)
    c = by_file(a.discover())["He436_014.avi"]
    g = a.resolve_geo(c)
    assert g.geo_uncertainty_m == 200.0 and "QC" not in g.geo_source and "qc_event" not in c.extra


def test_qc_event_list_unavailable_is_recorded_and_not_fatal(tmp_path):
    class Down(Http):
        def request(self, *a, **k):
            raise HttpError(a[1], 503, "down")

    a = make_adapter(tmp_path, ("909999",), qc=True, http=Down(dry_run=True))
    g = a.resolve_geo(by_file(a.discover())["He436_029.avi"])
    assert g.geo_uncertainty_m == 200.0
    assert [f["stage"] for f in failures(a)] == ["qc_events"]


# ---------------------------------------------------------------------------------------------- PANGAEA.831731
def test_831731_transect_midpoint_and_uncertainty(tmp_path):
    a = make_adapter(tmp_path, ("831731",))
    cands = by_file(a.discover())
    assert sorted(cands) == [
        "Video01_2011-06-15T15_06_00.mpg",
        "Video06_2011-06-16T15_20_00.mpg",
        "Video13_2011-06-17T16_11_50.mpg",
    ]
    c = cands["Video01_2011-06-15T15_06_00.mpg"]
    assert c.item_id == "PANGAEA.831731/Video01_2011-06-15T15_06_00.mpg"
    assert c.media_url == "https://hs.pangaea.de/Movies/mielck_etal_2014/Video01_2011-06-15T15_06_00.mpg"
    assert (c.media_type, c.ext, c.timestamp) == ("video", "mpg", "2011-06-15T15:06:00")
    assert c.extra["group"] == "Helgoland2011" and c.extra["cruise"] is None and c.extra["size_kb"] == 287996
    lic = a.resolve_licence(c)
    assert (lic.tier, lic.level, lic.name) == ("B", "record", CC_BY_3)
    assert lic.url == "https://creativecommons.org/licenses/by/3.0/"
    assert lic.attribution == CIT_831731  # the Citation line ends with ", " in the export
    expected = {  # SOURCE.md: midpoint, uncertainty = L/2 + 30 m
        "Video01_2011-06-15T15_06_00.mpg": (54.2102501, 7.8941948, 108.0),
        "Video06_2011-06-16T15_20_00.mpg": (54.2253556, 7.8736778, 84.0),
        "Video13_2011-06-17T16_11_50.mpg": (54.1789196, 7.9156956, 107.0),
    }
    for name, (lat, lon, unc) in expected.items():
        g = a.resolve_geo(cands[name])
        assert (g.lat, g.lon, g.depth_m, g.geo_uncertainty_m) == (pytest.approx(lat, abs=1e-7), pytest.approx(lon, abs=1e-7), None, unc)
        assert (g.geo_precision, g.geo_inferred) == ("station", True)
    assert a.resolve_geo(c).geo_source == (
        "PANGAEA.831731 midpoint of Latitude/Longitude (start) and Latitude 2/Longitude 2 (end) of the video transect, WGS 84"
    )


def test_831731_without_end_position_uses_the_start_point(tmp_path):
    """Synthetic: end position blanked."""
    a = make_adapter(tmp_path, ("831731",))
    lines = TABS["831731"].read_text(encoding="utf-8").splitlines()
    out = []
    for ln in lines:
        if ln.startswith("Video01_"):
            f = ln.split("\t")
            f[8] = f[9] = ""  # Latitude 2, Longitude 2
            ln = "\t".join(f)
        out.append(ln)
    seed(a, "831731", "\n".join(out) + "\n")
    g = a.resolve_geo(by_file(a.discover())["Video01_2011-06-15T15_06_00.mpg"])
    assert (g.lat, g.lon, g.geo_uncertainty_m) == (54.2096123, 7.8946811, 250.0)  # L = 440 m -> 220 + 30
    assert "no end position" in g.geo_source and g.geo_precision == "station"


# ----------------------------------------------------------------------------------- missing / bad coordinates
def test_row_without_coordinates_has_geo_none_and_keeps_depth(tmp_path):
    """Synthetic: the real tables have no empty coordinates, so blank them."""
    a = make_adapter(tmp_path, ("909999",))
    text = TABS["909999"].read_text(encoding="utf-8").replace("54.83072\t6.78097", "\t")
    seed(a, "909999", text)
    c = by_file(a.discover())["He436_014.avi"]
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == (None, None, "none", False, None)
    assert g.depth_m == 41.4
    assert g.geo_source == "PANGAEA.909999: no Latitude/Longitude in row"


def test_coordinate_outside_the_sanity_box_is_rejected(tmp_path):
    """Synthetic: a latitude / longitude swap would land in the Gulf of Guinea."""
    a = make_adapter(tmp_path, ("909999",))
    text = TABS["909999"].read_text(encoding="utf-8").replace("54.83072\t6.78097", "6.78097\t54.83072")
    seed(a, "909999", text)
    g = a.resolve_geo(by_file(a.discover())["He436_014.avi"])
    assert g.geo_precision == "none" and g.lat is None and g.depth_m == 41.4
    assert "outside the German Bight sanity box" in g.geo_source


# -------------------------------------------------------------------------------------------- sibling cruises
HE501_ROWS = [
    ["Profile 1_Hydro1", "7.08498", "54.60657", "2017-11-20T12:29:07", "35.1", f"{BASE}/HE501/HE501_Hydro1_001.MP4", f"{BASE}/HE501/HE501_Hydro1_001.avi"],
    ["Profile 2_Hydro1", "7.08886", "54.60278", "2017-11-20T12:52:16", "35.5", f"{BASE}/HE501/HE501_Hydro1_002.MP4", f"{BASE}/HE501/HE501_Hydro1_002.avi"],
]
HE502_ROWS = [
    ["Profile 1", "7.117404667", "54.6117490", "2017-12-15T12:57:17", "35.1", f"{BASE}/HE502/HE502_GOPRO_VProfil_01.MP4", "", "", f"{BASE}/HE502/HE502_VProfil_01.asf"],
    [
        "Profile 2", "7.088280950", "54.6031341", "2017-12-15T13:46:55", "35.5", f"{BASE}/HE502/HE502_GOPRO_Vprofil_02_1.MP4",
        f"{BASE}/HE502/HE502_GOPRO_VProfil_02_2.MP4", "", f"{BASE}/HE502/HE502_VProfil_02.asf",
    ],
]  # fmt: skip
HE505_ROWS = [
    ["Profile 01_Hydro3", "7.095352", "54.767765", "2018-03-14T18:10:49", "27.9", f"{BASE}/HE505/HE505_001_Hydro3.MP4", f"{BASE}/HE505/HE505_001_Hydro3.asf"],
]
HE400_ROWS = [["HE400_001", "54.96568", "7.00867", "2013-05-17T10:35:19", "32.4", f"{BASE}/HE400/Station_001.mpg"]]
HE474_ROWS = [["55.78117", "3.9375", "2016-10-18T18:57:00", "44.5", f"{BASE}/HE474/HE474_01_Dogger.avi", f"{BASE}/HE474/HE474_01_GOPRO_Dogger.MP4"]]


def sibling_adapter(tmp_path, **options):
    a = make_adapter(tmp_path, (), dataset_ids=["907338", "907337", "907340", "907382", "910009"], **options)
    seed(a, "907338", table_text("907338", ["Content", "Longitude", "Latitude", "Date/Time", "Bathy depth [m]", "URL movie", "URL file"], HE501_ROWS, event_campaign="HE501"))
    seed(
        a, "907337",
        table_text("907337", ["Content", "Longitude", "Latitude", "Date/Time", "Bathy depth [m]", "URL movie (part 1)", "URL movie (part 2)", "URL movie (part 3)", "URL file (asf file)"], HE502_ROWS, event_campaign="HE502"),
    )  # fmt: skip
    seed(a, "907340", table_text("907340", ["Content", "Longitude", "Latitude", "Date/Time", "Bathy depth [m]", "URL movie", "URL file"], HE505_ROWS, event_campaign="HE505"))
    seed(a, "907382", table_text("907382", ["Content", "Latitude", "Longitude", "Date/Time", "Bathy depth [m]", "URL movie"], HE400_ROWS, event_campaign="HE400"))
    seed(a, "910009", table_text("910009", ["Latitude", "Longitude", "Date/Time", "Bathy depth [m]", "URL file (avi)", "URL file (MP4)"], HE474_ROWS, event_campaign="HE474"))
    return a


def test_siblings_role_comes_from_the_extension_not_the_column(tmp_path):
    a = sibling_adapter(tmp_path, media="all")
    cands = by_file(a.discover())
    assert cands["HE501_Hydro1_001.MP4"].extra["role"] == "gopro"  # HE501 puts the MP4 under "URL movie" and the AVI under "URL file"
    assert cands["HE501_Hydro1_001.avi"].extra["role"] == "station"
    assert cands["HE501_Hydro1_001.avi"].extra["station_id"] == cands["HE501_Hydro1_001.MP4"].extra["station_id"] == "HE501/hydro1_001"
    assert cands["Station_001.mpg"].extra["role"] == "station" and cands["Station_001.mpg"].extra["station_id"] == "HE400/station_001"
    assert cands["HE474_01_GOPRO_Dogger.MP4"].extra["station_id"] == cands["HE474_01_Dogger.avi"].extra["station_id"] == "HE474/01_dogger"
    g = a.resolve_geo(cands["HE501_Hydro1_001.avi"])
    assert (g.lat, g.lon, g.depth_m, g.geo_uncertainty_m) == (54.60657, 7.08498, 35.1, 200.0)
    dogger = a.resolve_geo(cands["HE474_01_Dogger.avi"])
    assert (dogger.lat, dogger.lon) == (55.78117, 3.9375)  # Dogger Bank is inside the sanity box
    assert a.resolve_licence(cands["HE501_Hydro1_001.avi"]).attribution.endswith("PANGAEA.907338. CC BY 4.0")


def test_siblings_asf_and_gopro_parts(tmp_path):
    a = sibling_adapter(tmp_path, media="all")
    cands = by_file(a.discover())
    asf = cands["HE502_VProfil_02.asf"]
    assert (asf.ext, asf.media_type, asf.extra["role"]) == ("asf", "video", "station")
    parts = {n: cands[n] for n in ("HE502_GOPRO_Vprofil_02_1.MP4", "HE502_GOPRO_VProfil_02_2.MP4")}
    assert [p.extra["part"] for p in parts.values()] == [1, 2]
    assert {p.extra["station_id"] for p in parts.values()} == {asf.extra["station_id"]} == {"HE502/vprofil_02"}
    assert cands["HE502_GOPRO_VProfil_01.MP4"].extra["part"] == 1


def test_he505_timestamps_are_not_acquisition_times(tmp_path):
    a = sibling_adapter(tmp_path, media="all")
    c = by_file(a.discover())["HE505_001_Hydro3.asf"]
    assert c.timestamp is None and "not an acquisition time" in c.extra["time_note"]
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (54.767765, 7.095352, 27.9)  # coordinates are fine


def test_siblings_switch_and_default_ids(tmp_path):
    on = make_adapter(tmp_path / "a", (), dataset_ids=None)
    assert on.ids() == [*gb.SEED_IDS, *gb.SIBLING_IDS]
    off = make_adapter(tmp_path / "b", (), dataset_ids=None, siblings=False)
    assert off.ids() == ["907386", "909999", "831731"]
    custom = make_adapter(tmp_path / "c", (), dataset_ids="909999,PANGAEA.831731")
    assert custom.ids() == ["909999", "831731"]


# ------------------------------------------------------------------------------------------ licence handling
def test_licence_cross_check_with_jsonld_agrees(tmp_path):
    a = make_adapter(tmp_path, ("909999",), jsonld=True)
    cands = list(a.discover())
    assert len(cands) == 4
    lic = a.resolve_licence(cands[0])
    assert lic.tier == "B" and lic.level == "record" and lic.attribution == CIT_909999
    assert failures(a) == []


def test_licence_contradiction_between_header_and_jsonld_is_tier_u(tmp_path):
    a = make_adapter(tmp_path, ("909999",), jsonld=True)
    doc = json.loads(JSONLD_909999.read_text(encoding="utf-8"))
    doc["license"] = "https://creativecommons.org/licenses/by-nc/4.0/"
    (a.ctx.layout.raw / "pangaea_909999.jsonld").write_text(json.dumps(doc), encoding="utf-8")
    lic = a.resolve_licence(next(iter(a.discover())))
    assert lic.tier == "U" and "conflict" in lic.name


def test_nc_header_licence_is_never_upgraded(tmp_path):
    a = make_adapter(tmp_path, ("909999",))
    text = TABS["909999"].read_text(encoding="utf-8").replace(
        "Creative Commons Attribution 4.0 International (CC-BY-4.0) (URI: https://creativecommons.org/licenses/by/4.0/)",
        "Creative Commons Attribution-NonCommercial 4.0 International (CC-BY-NC-4.0) (URI: https://creativecommons.org/licenses/by-nc/4.0/)",
    )
    seed(a, "909999", text)
    assert a.resolve_licence(next(iter(a.discover()))).tier == "X"


def test_restricted_record_and_moratorium_are_skipped(tmp_path):
    a = make_adapter(tmp_path / "r", ("909999",), jsonld=True)
    doc = json.loads(JSONLD_909999.read_text(encoding="utf-8"))
    doc["conditionsOfAccess"] = "restricted"
    (a.ctx.layout.raw / "pangaea_909999.jsonld").write_text(json.dumps(doc), encoding="utf-8")
    assert list(a.discover()) == []
    assert failures(a)[0]["stage"] == "licence" and "restricted" in failures(a)[0]["reason"]
    b = make_adapter(tmp_path / "m", ("909999",))
    text = TABS["909999"].read_text(encoding="utf-8").replace("Size:\t132 data points", "Status:\tModerated by embargo until 2999-01-01\nSize:\t132 data points")
    seed(b, "909999", text)
    assert list(b.discover()) == []
    assert "moratorium until 2999-01-01" in failures(b)[0]["reason"]


# ---------------------------------------------------------------------------------------- order and budget
def test_spread_order_covers_cruises_and_areas_first(tmp_path):
    a = make_adapter(tmp_path, ("907386",), full=True)
    cands = list(a.discover())
    first4 = cands[:4]
    assert [(c.extra["cruise"], c.extra["area"]) for c in first4] == [
        ("HE415", "Spots"),
        ("HE416", "AG3"),
        ("HE415", "AG1"),
        ("HE416", "AG4"),
    ]
    # the first N is not the first N rows of the table: the table order would give 9 Spots stations then AG1 ...
    assert len({c.extra["area"] for c in cands[:8]}) == 4
    # further parts of a station (Spots_01-2, -3) come after every first part
    assert [c.media_url.rsplit("/", 1)[1] for c in cands[-2:]] == ["He415_Spots_01-2.avi", "He415_Spots_01-3.avi"]
    assert all((c.extra["part"] or 1) == 1 for c in cands[:-2])


def test_gopro_clips_come_after_all_station_videos(tmp_path):
    cands = list(make_adapter(tmp_path, ("907386",), full=True, media="all").discover())
    roles = [c.extra["role"] for c in cands]
    assert roles == ["station"] * 87 + ["gopro"] * 55


def test_round_robin_over_datasets(tmp_path):
    cands = list(make_adapter(tmp_path).discover())
    # one group per cruise, in table order: HE415 and HE416 (both in 907386), HE436, the Helgoland transects
    assert [c.extra["group"] for c in cands[:4]] == ["HE415", "HE416", "HE436", "Helgoland2011"]
    assert len(cands) == 4 + 4 + 3  # AVIs of 907386 (4), 909999 (4), MPGs of 831731 (3)


def test_table_order_and_cruise_filter(tmp_path):
    table = list(make_adapter(tmp_path / "t", ("907386",), full=True, order="table").discover())
    assert [c.media_url.rsplit("/", 1)[1] for c in table[:3]] == ["He415_Spots_01-1.avi", "He415_Spots_01-2.avi", "He415_Spots_01-3.avi"]
    only = list(make_adapter(tmp_path / "f", full=True, cruises="HE416,Helgoland2011").discover())
    assert {c.extra["group"] for c in only} == {"HE416", "Helgoland2011"}


def test_item_ids_are_stable_across_runs(tmp_path):
    ids1 = [c.item_id for c in make_adapter(tmp_path / "1", media="all").discover()]
    ids2 = [c.item_id for c in make_adapter(tmp_path / "2", media="all").discover()]
    assert ids1 == ids2 and len(set(ids1)) == len(ids1)
    assert all(i.startswith("PANGAEA.") and "/" in i for i in ids1)


def test_estimate_reports_provider_totals(tmp_path):
    est = make_adapter(tmp_path).estimate()
    assert est["videos"] == 11 and est["station_videos"] == 11 and est["gopro_videos"] == 0 and est["tables"] == 3
    est_all = make_adapter(tmp_path / "x", media="all").estimate()
    assert est_all["gopro_videos"] == 2 + 3  # MP4: 2 in 907386, 3 in 909999 (He436_014 has none)
    assert est_all["approx_gb"] > est["approx_gb"] * 10


def test_check_ready_flags_bad_options(tmp_path):
    assert make_adapter(tmp_path / "ok").check_ready() == []
    bad = make_adapter(tmp_path / "bad", media="mp4", order="random").check_ready()
    assert len(bad) == 2 and "media" in bad[0] and "order" in bad[1]


# -------------------------------------------------------------------------------------------- the runner
def test_runner_dry_run_end_to_end(tmp_path):
    seed_dir = DatasetLayout(tmp_path, "german_bight").ensure().raw
    shutil.copyfile(TABS["909999"], seed_dir / "pangaea_909999.tab")
    shutil.copyfile(EVENTS_HE436, seed_dir / "dship_events_HE436.tab")
    shutil.copyfile(JSONLD_909999, seed_dir / "pangaea_909999.jsonld")
    cfg = load_config(None, data_root=tmp_path)
    s = run_source(cfg, "german_bight", "dry-run", options={"dataset_ids": ["909999"], "media": "all"})
    assert s.error is None and s.candidates == 7 and s.selected == 7
    assert dict(s.selected_by_tier) == {"B": 7} and dict(s.selected_by_precision) == {"station": 7}
    assert dict(s.media_types) == {"video": 7}
    assert s.estimate["videos"] == 7


# ----------------------------------------------------------------------------------------- tape handling
class FakeResp:
    def __init__(self, status=200, headers=None):
        self.status_code = status
        self.headers = headers or {}

    def close(self):
        pass


@pytest.fixture
def no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr(gb.time, "sleep", lambda s: slept.append(s))
    return slept


def live_adapter(tmp_path, **options):
    a = make_adapter(tmp_path, ("909999",), dry_run=False, http=NoNet(dry_run=False), **options)
    cand = by_file(a.discover())["He436_001.avi"]
    return a, cand, tmp_path / "out" / "x.avi"


def test_fetch_media_waits_for_tape_then_downloads(tmp_path, monkeypatch, no_sleep):
    a, cand, dest = live_adapter(tmp_path)
    calls = []

    def download(url, dst, expected_bytes=None, headers=None):
        calls.append(("GET", expected_bytes))
        if len([c for c in calls if c[0] == "GET"]) == 1:
            raise HttpError(url, 503, "download failed")  # the recall has started
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(b"RIFF\x00\x00\x00\x00AVI LIST")
        return 16, "abc"

    heads = iter([FakeResp(503, {"Retry-After": "7", "Content-Type": "text/html"}), FakeResp(200, {"Content-Type": "video/x-msvideo", "Content-Length": "16"})])

    def request(method, url, **kw):
        assert method == "HEAD" and kw["kind"] == "media"
        calls.append(("HEAD", None))
        return next(heads)

    monkeypatch.setattr(a.http, "download", download)
    monkeypatch.setattr(a.http, "request", request)
    assert a.fetch_media(cand, a.resolve_media(cand), dest) == (16, "abc")
    assert [c[0] for c in calls] == ["GET", "HEAD", "HEAD", "GET"]
    assert calls[-1][1] == 16  # content-length of the HEAD that said "online" becomes the expected size
    assert len(no_sleep) == 2 and no_sleep[0] == 30 and no_sleep[1] == 30  # max(stage_poll_s, Retry-After)


def test_fetch_media_never_keeps_an_html_body(tmp_path, monkeypatch, no_sleep):
    a, cand, dest = live_adapter(tmp_path, stage_timeout_s=0.0)
    page = b"<html><body>The requested file He436_001.avi is loading from tape...</body></html>"

    def download(url, dst, expected_bytes=None, headers=None):
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(page)
        return len(page), "abc"

    monkeypatch.setattr(a.http, "download", download)
    with pytest.raises(HttpError) as exc:
        a.fetch_media(cand, MediaRef(url=cand.media_url), dest)
    assert exc.value.status == 503 and "HTML page" in str(exc.value)
    assert not dest.exists()


def test_fetch_media_gives_up_after_the_stage_timeout(tmp_path, monkeypatch, no_sleep):
    a, cand, dest = live_adapter(tmp_path, stage_timeout_s=0.0)

    def download(url, dst, expected_bytes=None, headers=None):
        raise HttpError(url, 503, "download failed")

    monkeypatch.setattr(a.http, "download", download)
    with pytest.raises(HttpError) as exc:
        a.fetch_media(cand, MediaRef(url=cand.media_url), dest)
    assert exc.value.status == 503


def test_fetch_media_does_not_retry_a_real_error(tmp_path, monkeypatch, no_sleep):
    a, cand, dest = live_adapter(tmp_path)

    def download(url, dst, expected_bytes=None, headers=None):
        raise HttpError(url, 404, "gone")

    monkeypatch.setattr(a.http, "download", download)
    with pytest.raises(HttpError) as exc:
        a.fetch_media(cand, MediaRef(url=cand.media_url), dest)
    assert exc.value.status == 404 and no_sleep == []


def test_resolve_media_does_not_touch_the_network_before_staging_was_seen(tmp_path):
    a, cand, _ = live_adapter(tmp_path)
    ref = a.resolve_media(cand)  # NoNet raises on any request
    assert ref.url == cand.media_url and ref.ext == "avi" and ref.expected_bytes is None


def test_dry_run_discover_and_geo_never_send_a_request(tmp_path):
    """NoNet raises on any request, a HEAD on hs.pangaea.de included (it would recall a tape file)."""
    a = make_adapter(tmp_path, ("909999",), media="all", events=True)
    for c in a.discover():
        a.resolve_licence(c)
        a.resolve_geo(c)
    assert a.estimate()["videos"] == 7


def test_helpers():
    assert gb._spread_order(5) == [0, 4, 2, 1, 3]
    assert gb._spread_order(2) == [0, 1] and gb._spread_order(0) == []
    assert list(gb._round_robin([[1, 2, 3], [4], [5, 6]])) == [1, 4, 5, 2, 6, 3]
    assert gb._file_tokens("HE415_Greifer_AG1_006_HD") == "Greifer_AG1_006"
    assert gb._file_tokens("HE436_GOPRO_012-1") == "012-1"
    assert gb._file_tokens("HE474_01_GOPRO_Dogger") == "01_Dogger"
    assert gb._role("avi") == gb._role("mpg") == gb._role("asf") == "station"
    assert gb._role("mp4") == "gopro" and gb._role("lrv") is None and gb._role("thm") is None and gb._role("jpg") is None
