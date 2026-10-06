from pathlib import Path

import pytest

from aquasource.core.geo import NavFix, NavTrack, check_coordinate, parse_dms, parse_time, precision_at_least, to_float
from aquasource.core.licence import classify, combine, most_specific
from aquasource.core.manifest import JsonlLog, Manifest
from aquasource.core.schema import Candidate, Geo, Licence, make_sample_id, sample_row
from aquasource.core.sites import Site
from aquasource.providers.pangaea import coverage, parse_textfile

FIX = Path(__file__).parent / "fixtures" / "_core"


@pytest.mark.parametrize(
    "text,tier",
    [
        ("CC0 1.0 Universal", "A"),
        ("Public Domain", "A"),
        ("https://creativecommons.org/publicdomain/zero/1.0/", "A"),
        ("U.S. Government Work", "A"),
        ("Creative Commons Attribution 4.0 International (CC-BY-4.0)", "B"),
        ("cc-by-4.0", "B"),
        ("CC BY 3.0 AU", "B"),
        ("https://creativecommons.org/licenses/by/4.0/", "B"),
        ("Open Government Licence - Canada", "B"),
        ("Open Government Licence v3.0", "B"),
        ("Datenlizenz Deutschland – Namensnennung – Version 2.0", "B"),
        ("dl-de/by-2-0", "B"),
        ("Norwegian Licence for Open Government Data (NLOD) 2.0", "B"),
        ("Licence Ouverte / Open Licence 2.0 (Etalab)", "B"),
        ("CC BY-SA 4.0", "C"),
        ("Creative Commons Attribution-ShareAlike 4.0", "C"),
        ("CC BY-NC 4.0", "X"),
        ("CC BY-NC-SA 4.0", "X"),
        ("Creative Commons Attribution-NonCommercial-NoDerivatives", "X"),
        ("cc-by-nd-4.0", "X"),
        ("For research use only", "X"),
        ("All rights reserved", "X"),
        ("", "U"),
        ("not specified", "U"),
        ("Custom licence, see documentation", "U"),
    ],
)
def test_licence_classify(text, tier):
    assert classify(text) == tier


def test_licence_combine_and_levels():
    assert combine("B", "B") == "B"
    assert combine("B", "A") == "U"  # contradiction
    assert combine("B", "X") == "X"
    assert combine("U", "B") == "B"
    assert most_specific(("file", None), ("record", "CC BY 4.0"), ("collection", "CC0")) == ("record", "CC BY 4.0")
    assert most_specific(("file", ""), ("record", None)) == ("unknown", "")


@pytest.mark.parametrize(
    "lat,lon,ok",
    [(54.1, 7.2, True), (None, None, True), (0.0, 0.0, False), (91.0, 0.0, False), (0.0, 181.0, False), (float("nan"), 3.0, False), (10.0, None, False), (0.0, 12.5, True)],
)
def test_check_coordinate(lat, lon, ok):
    assert (check_coordinate(lat, lon) is None) == ok


def test_precision_order():
    assert precision_at_least("image", "station")
    assert precision_at_least("fixed_site", "station")
    assert precision_at_least("station", "fixed_site")
    assert not precision_at_least("region", "station")
    assert not precision_at_least("none", "region")


def test_geo_validation():
    with pytest.raises(ValueError):
        Geo(1.0, 2.0, None, "none", "", False)
    with pytest.raises(ValueError):
        Geo(None, None, None, "image", "x", False)
    with pytest.raises(ValueError):
        Geo(1.0, 2.0, None, "bogus", "x", False)


def test_nav_interpolation():
    track = NavTrack([NavFix(0.0, 10.0, 20.0, 100.0), NavFix(10.0, 10.1, 20.2, 110.0), NavFix(40.0, 11.0, 21.0, 120.0)])
    hit = track.locate(5.0)
    assert hit is not None
    assert hit.lat == pytest.approx(10.05)
    assert hit.lon == pytest.approx(20.1)
    assert hit.depth_m == pytest.approx(105.0)
    assert hit.offset_s == pytest.approx(5.0)
    assert track.locate(25.0) is None  # gap 30 s > 10 s
    assert track.locate(-1.0) is None  # before the track
    exact = track.locate(40.0)
    assert exact is not None and exact.offset_s == 0.0
    geo, off = track.geo_at(2.0, "nav.csv lat/lon")
    assert geo.geo_precision == "segment" and geo.geo_inferred and off == pytest.approx(2.0)
    geo, off = track.geo_at(30.0, "nav.csv lat/lon")
    assert geo.geo_precision == "none" and off is None


def test_nav_antimeridian():
    track = NavTrack([NavFix(0.0, 0.5, 179.9), NavFix(2.0, 0.5, -179.9)])
    hit = track.locate(1.0)
    assert hit is not None and abs(abs(hit.lon) - 180.0) < 1e-6


def test_parsers():
    assert to_float("12,5") == 12.5
    assert to_float("") is None
    assert to_float("nan") is None
    assert parse_time("2014-02-19T10:18:00") == parse_time("2014-02-19T10:18:00Z")
    assert parse_dms("54°52.196'N") == pytest.approx(54.869933, abs=1e-5)
    assert parse_dms("6 43 12 W") == pytest.approx(-6.72, abs=1e-6)


def test_site_precision():
    s = Site("a", "A", 54.0, 7.0, 20.0, 2000.0, "doi:x Table 1")
    assert s.geo().geo_precision == "station" and s.geo().geo_inferred
    far = Site("b", "B", 54.0, 7.0, None, 20000.0, "doi:x text")
    assert far.geo().geo_precision == "region"


def test_manifest_idempotent(tmp_path):
    cand = Candidate("src", "item-1", "image", "https://x/a.jpg", "https://x/a")
    lic = Licence("CC BY 4.0", "B", "record", None, "Someone (2020)")
    geo = Geo(1.0, 2.0, None, "image", "lat/lon", False)
    f = tmp_path / "data.bin"
    f.write_bytes(b"12345")
    with Manifest(tmp_path / "s.sqlite") as m:
        row = sample_row(cand, lic, geo, local_path=str(f), nbytes=5, sha256="x", status="downloaded")
        m.upsert(row)
        m.upsert(row)
        assert m.count() == 1
        assert m.is_complete(cand.sample_id)
        n = m.export(tmp_path / "samples.jsonl")
        assert n == 1
    f.write_bytes(b"1")  # truncated file -> not complete any more
    with Manifest(tmp_path / "s.sqlite") as m:
        assert not m.is_complete(cand.sample_id)
    assert cand.sample_id == make_sample_id("src", "item-1")


def test_jsonl_log_dedup(tmp_path):
    log = JsonlLog(tmp_path / "f.jsonl")
    log.write({"a": 1})
    log.write({"a": 1})
    log2 = JsonlLog(tmp_path / "f.jsonl")
    log2.write({"a": 1})
    assert (tmp_path / "f.jsonl").read_text().count("\n") == 1


def test_pangaea_textfile_parse():
    t = parse_textfile((FIX / "pangaea_907386.tab").read_text(encoding="utf-8"))
    assert t.dataset_id == "907386"
    assert t.licence_name == "Creative Commons Attribution 4.0 International (CC-BY-4.0)"
    assert t.licence_url == "https://creativecommons.org/licenses/by/4.0/"
    assert classify(t.licence_name) == "B"
    assert t.column("Latitude") == "Latitude"
    assert t.column("URL movie") == "URL movie (avi)"
    assert len(t.rows) > 50
    first = t.rows[0]
    assert first["Event"] == "HE415-track"
    assert float(first["Latitude"]) == pytest.approx(54.86993)
    cov = coverage(t)
    assert cov["SOUTH-BOUND LATITUDE"] == pytest.approx(54.4305)
