"""Offline tests for the csiro_mnf adapter, run on the real fixtures in tests/fixtures/csiro_mnf/.

No test touches the network. The DAP collection record, the first 3 real listing records and the first 40 lines of
the real DTC_IN2023_V05_005_STILLS.CSV are in the fixtures. The listing is written as metadata/raw/listing.json and
the CSV as metadata/raw/stills/IN2023_V05_005.csv, so cached_text() never requests them. Still-image listing records
for the rows that have coordinates (DTC_DSP_..._00004 to _00011) are synthetic: the real listing is ~250 MB and only
its first 3 records were kept.
"""

import json
from pathlib import Path

import pytest

from aquasource.adapters import csiro_mnf as cm
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "csiro_mnf"
HEAD = json.loads((FIX / "listing_head.json").read_text())
COLLECTION = json.loads((FIX / "dap_collection_74006.json").read_text())
STILLS_CSV = (FIX / "DTC_IN2023_V05_005_STILLS_head.csv").read_text(encoding="utf-8")
DEP = "IN2023_V05_005"
DIR = f"IN2023_V05/data/DTC/{DEP}"
STILLS_REC = next(r for r in HEAD["file"] if r["filename"].endswith("_STILLS.CSV"))


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def compact(recs):
    """The DAP listing is compact JSON; the adapter regex relies on that layout."""
    return json.dumps({"id": "data:74006", "file": recs}, separators=(",", ":"))


def synthetic_still(fid, key):
    """Synthetic listing record for a still (only the name and link shape matter to the adapter)."""
    return {
        "id": fid,
        "filename": f"{DIR}/{key}",
        "lastUpdated": "2026-06-12T09:57:09.431+10:00",
        "fileSize": 5_000_000 + fid % 1000,
        "link": {
            "relationship": "self",
            "mediaType": "image/jpeg",
            "href": f"https://data.csiro.au/dap/ws/v2/collections/74006/data/{fid}",
            "fileUpload": False,
            "fileId": 0,
        },
    }


def make_adapter(tmp_path, *, extra_records=(), stills_csv=STILLS_CSV, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "csiro_mnf").ensure()
    (layout.raw / "stills").mkdir(parents=True, exist_ok=True)
    (layout.raw / "listing.json").write_text(compact(list(HEAD["file"]) + list(extra_records)), encoding="utf-8")
    (layout.raw / "stills" / f"{DEP}.csv").write_text(stills_csv, encoding="utf-8")
    ctx = Context(cfg, NoNet(dry_run=True), layout, options, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("csiro_mnf")(ctx)


def still_records():
    """Synthetic image records for the fixture rows that have coordinates (Key names taken from the CSV)."""
    import csv
    import io

    keys = [r["Key"] for r in csv.DictReader(io.StringIO(STILLS_CSV)) if r["Latitude"] and r["Longitude"]]
    return [synthetic_still(900_000 + i, k) for i, k in enumerate(keys)]


def test_fixture_listing_regex_matches_real_records():
    rows = cm.FILE_RE.findall(compact(HEAD["file"]))
    assert len(rows) == 3
    assert rows[0][1] == f"{DIR}/data/DTC_IN2023_V05_005.CSV"
    assert int(rows[0][2]) == 378089
    assert rows[1][3] == "text/csv"
    assert rows[2][4].startswith("https://data.csiro.au/dap/ws/v2/collections/74006/data/")


def test_collection_record_is_public_cc_by():
    assert COLLECTION["licence"] == "Creative Commons Attribution 4.0 International Licence"
    assert COLLECTION["dataRestricted"] == "FALSE"
    assert COLLECTION["imageCount"] == 346715


def test_licence_is_tier_b_record_level(tmp_path):
    ad = make_adapter(tmp_path, extra_records=still_records())
    cand = next(iter(ad.discover()))
    lic = ad.resolve_licence(cand)
    assert lic.tier == "B"
    assert lic.level == "record"
    assert lic.url == "https://creativecommons.org/licenses/by/4.0/"
    assert "CSIRO Marine National Facility" in lic.attribution
    assert "10.25919/gddy-hn24" in lic.attribution


def test_discover_yields_only_rows_with_coordinates(tmp_path):
    ad = make_adapter(tmp_path, extra_records=still_records())
    cands = list(ad.discover())
    # Rows of the fixture CSV without Latitude/Longitude (00002, 00003, ...) are dropped; the rest are kept.
    import csv
    import io

    with_pos = [r for r in csv.DictReader(io.StringIO(STILLS_CSV)) if r["Latitude"] and r["Longitude"]]
    assert len(cands) == len(with_pos) == 37
    keys = {c.raw["row"]["Key"] for c in cands}
    assert "DTC_DSP_IN2023_V05_005_20230630T092202Z_00005.JPG" in keys
    assert not any(k.endswith("00002.JPG") or k.endswith("00003.JPG") for k in keys)
    c = cands[0]
    assert c.media_type == "image"
    assert c.ext == "jpg"
    assert c.item_id.startswith("74006:")
    assert c.media_url.startswith("https://data.csiro.au/dap/ws/v2/collections/74006/data/")
    assert c.extra["deployment"] == DEP


def test_geo_is_image_precision_from_stills_csv(tmp_path):
    ad = make_adapter(tmp_path, extra_records=still_records())
    cand = next(c for c in ad.discover() if c.raw["row"]["Key"].endswith("00004.JPG"))
    geo = ad.resolve_geo(cand)
    assert geo.geo_precision == "image"
    assert geo.geo_inferred is False
    assert geo.geo_source == cm.GEO_SOURCE
    assert geo.lat == pytest.approx(-40.57596016973025)
    assert geo.lon == pytest.approx(148.73222740744825)
    assert geo.depth_m == pytest.approx(62.458)
    assert -43.5 < geo.lat < -36.0 and 147.0 < geo.lon < 151.0


def test_row_without_coordinates_gets_geo_none_when_passed_directly(tmp_path):
    ad = make_adapter(tmp_path)
    fake = cm.Candidate(
        source="csiro_mnf",
        item_id="74006:0",
        media_type="image",
        media_url="https://example.invalid/x",
        origin_url=cm.LANDING,
        raw={"row": {"Key": "x.JPG", "Latitude": "", "Longitude": "", "Depth": ""}},
    )
    geo = ad.resolve_geo(fake)
    assert geo.geo_precision == "none"
    assert geo.lat is None and geo.lon is None


def test_deployment_filter_skips_other_deployments(tmp_path):
    ad = make_adapter(tmp_path, extra_records=still_records(), deployments=["IN2023_V05_999"])
    assert list(ad.discover()) == []


def test_max_rows_caps_the_selection(tmp_path):
    ad = make_adapter(tmp_path, extra_records=still_records(), max_rows=2)
    assert len(list(ad.discover())) == 2


def test_resolve_media_uses_dap_link_and_expected_size(tmp_path):
    ad = make_adapter(tmp_path, extra_records=still_records())
    cand = next(iter(ad.discover()))
    ref = ad.resolve_media(cand)
    assert ref.url == cand.media_url
    assert ref.ext == "jpg"
    assert ref.expected_bytes == cand.raw["bytes"]
