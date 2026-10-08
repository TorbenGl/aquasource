"""Offline tests for the moorea_lter adapter, on the fixtures in tests/fixtures/moorea_lter/.

No test touches the network. The EML fixture gives the licence and the zip MD5s, the DataONE solr fixture the zip sizes
and SHA-1s, and the example annotation filename the geo expectation. The year zips are synthetic (built in tmp_path with
the real member layout <year>/<name>.jpg + .txt) and stand in for the 2 GB provider zips, which are never fetched here.
The Http client raises on any request.
"""

import json
import zipfile
from pathlib import Path

import pytest

from aquasource.adapters import moorea_lter as ml
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "moorea_lter"
EXAMPLE = "mcr_lter6_out17m_pole5-6_qu3_20090331.jpg"
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
ANNO = b"# Row; Col; Label\n"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, *, dry_run=False, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "moorea_lter").ensure()
    ctx = Context(cfg, NoNet(dry_run=dry_run), layout, options, dry_run, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("moorea_lter")(ctx)


def synthetic_2008(a) -> None:
    """Zip stand-in: two cells, one bad-magic image, one PNG, a non-image text file, and no annotation for one image."""
    members = {
        "2008/mcr_lter1_out10m_pole1-2_qu1_20080415.jpg": JPEG,
        "2008/mcr_lter1_out10m_pole1-2_qu1_20080415.jpg.txt": ANNO,
        "2008/mcr_lter1_out10m_pole3-4_qu2_20080415.jpg": JPEG,
        "2008/mcr_lter1_out10m_pole3-4_qu2_20080415.jpg.txt": ANNO,
        "2008/mcr_lter6_fringingreef_pole1-2_qu1_20080412.jpg": JPEG,
        "2008/mcr_lter6_fringingreef_pole1-2_qu1_20080412.jpg.txt": ANNO,
        "2008/mcr_lter6_fringingreef_pole1-2_qu9_20080412.png": PNG,
        "2008/mcr_lter6_fringingreef_pole1-2_qu9_20080412.png.txt": ANNO,
        "2008/mcr_lter6_fringingreef_pole1-2_qu9_20080412.jpg": b"not a jpeg",
        "2008/readme.txt": b"text",
    }
    a._archive(2008).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(a._archive(2008), "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def use_local_zip(a, monkeypatch):
    """Pretend the year zip is already downloaded: _ensure_archive returns the stand-in without any request."""
    monkeypatch.setattr(a, "_ensure_archive", lambda year: a._archive(year))


def test_eml_licence_and_zip_checksums_match_constants():
    eml = (FIX / "knb-lter-mcr.5006.3_eml.xml").read_text(encoding="utf-8")
    assert "Attribution 4.0 International" in eml
    solr = json.loads((FIX / "dataone_solr_5006_3.json").read_text())
    docs = {d["id"].rsplit("/", 1)[-1]: d for d in solr["response"]["docs"]}
    for year, (entity, name, size, md5, sha1) in ml.ZIPS.items():
        assert name in eml and md5 in eml, year
        assert docs[entity]["size"] == size
        assert docs[entity]["checksum"] == sha1


def test_licence_is_cc_by_record_level(tmp_path):
    a = make_adapter(tmp_path)
    lic = a.resolve_licence(a._candidate(2009, EXAMPLE, 1, ml.parse_name(EXAMPLE), True))
    assert (lic.tier, lic.level, lic.name) == ("B", "record", "CC-BY-4.0")
    assert "Moorea Coral Reef LTER" in lic.attribution


def test_example_filename_resolves_to_station_geo(tmp_path):
    a = make_adapter(tmp_path)
    tok = ml.parse_name(EXAMPLE)
    assert (tok["sid"], tok["poles"], tok["quadrat"], tok["date"]) == ("LTER6_out17m", "5-6", 3, "2009-03-31")
    geo = a.resolve_geo(a._candidate(2009, EXAMPLE, 1, tok, True))
    assert geo.geo_precision == "station" and geo.geo_inferred is True
    assert (geo.lat, geo.lon, geo.depth_m, geo.geo_uncertainty_m) == (-17.51751, -149.9223, 17.0, 1500.0)
    assert geo.geo_source.startswith("sites/moorea_lter.csv:LTER6_out17m")


def test_unmatched_name_falls_back_to_region(tmp_path):
    a = make_adapter(tmp_path)
    unmatched = {"sid": None, "site": None, "habitat": None, "poles": None, "quadrat": None, "date": None, "ext": "jpg"}
    geo = a.resolve_geo(a._candidate(2010, "IMG_0001.JPG", 1, unmatched, False))
    assert geo.geo_precision == "region" and geo.geo_uncertainty_m == 20000.0
    assert (geo.lat, geo.lon, geo.depth_m) == (ml.REGION_LAT, ml.REGION_LON, None)


def test_parse_name_pattern():
    assert ml.parse_name("mcr_lter7_out10m_pole1-2_qu1_20080415.jpg") is None
    assert ml.parse_name("mcr_lter1_out10m_pole1-2_qu1_20080415.jpg.txt") is None
    assert ml.parse_name("MCR_LTER1_out10m_pole1-2_qu1_20080415.PNG")["ext"] == "png"


def test_discover_lists_images_round_robin_over_cells(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, years="2008")
    synthetic_2008(a)
    use_local_zip(a, monkeypatch)
    cands = list(a.discover())
    ids = [c.item_id for c in cands]
    assert len(ids) == 5  # 2 x lter1/out10m, lter6/fringingreef jpg + png + bad jpg; readme.txt is not an image
    assert ids[0].startswith("2008/mcr_lter1_") and ids[1].startswith("2008/mcr_lter6_")  # cells alternate
    by_name = {c.raw["member"]: c for c in cands}
    assert by_name["mcr_lter6_fringingreef_pole1-2_qu9_20080412.png"].raw["annotation"] is not None
    assert by_name["mcr_lter1_out10m_pole1-2_qu1_20080415.jpg"].extra["annotation_file"].endswith(
        "annotations/2008/mcr_lter1_out10m_pole1-2_qu1_20080415.jpg.txt"
    )


def test_habitat_option_filters(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, years="2008", habitats="fringingreef")
    synthetic_2008(a)
    use_local_zip(a, monkeypatch)
    assert {c.raw["habitat"] for c in a.discover()} == {"fringingreef"}


def test_fetch_copies_image_and_annotation_and_rejects_bad_magic(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, years="2008")
    synthetic_2008(a)
    use_local_zip(a, monkeypatch)
    by_name = {c.raw["member"]: c for c in a.discover()}
    good = by_name["mcr_lter1_out10m_pole1-2_qu1_20080415.jpg"]
    dest = tmp_path / "out" / "a.jpg"
    nbytes, sha = a.fetch_media(good, a.resolve_media(good), dest)
    assert dest.read_bytes() == JPEG and nbytes == len(JPEG) and len(sha) == 64
    anno = tmp_path / "moorea_lter" / "metadata" / "annotations" / "2008" / "mcr_lter1_out10m_pole1-2_qu1_20080415.jpg.txt"
    assert anno.read_bytes() == ANNO
    bad = by_name["mcr_lter6_fringingreef_pole1-2_qu9_20080412.jpg"]
    with pytest.raises(RuntimeError, match="bad magic"):
        a.fetch_media(bad, a.resolve_media(bad), tmp_path / "out" / "b.jpg")


def test_dry_run_without_zip_lists_nothing_and_makes_no_request(tmp_path):
    a = make_adapter(tmp_path, dry_run=True)
    assert list(a.discover()) == []  # NoNet raises on any request, so no download was attempted


def test_truncated_zip_yields_only_complete_members(tmp_path, monkeypatch):
    from aquasource.adapters.moorea_lter import scan_zip

    a = make_adapter(tmp_path)
    synthetic_2008(a)
    p = a._archive(2008)
    full = len(scan_zip(p))
    p.write_bytes(p.read_bytes()[: p.stat().st_size // 2])
    part = scan_zip(p)
    assert 0 < len(part) < full
