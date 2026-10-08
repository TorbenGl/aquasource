"""Offline tests for the seatizen adapter, run on the real fixtures in tests/fixtures/seatizen/.

No test touches the network. ``zenodo_record_13170795.json`` (session record, cc-by-4.0, open) and
``zenodo_13170795_METADATA.zip`` (its METADATA.zip, 141 EXIF rows with GPS) are real Zenodo answers (2026-10-08);
``session_doi_head.csv`` holds the first 5 rows of the real session index. The DCIM.zip of that session is 522 MB, so the
range-request path is tested on a synthetic zip (same member names as the real metadata, random bytes, marked synthetic).
"""

import hashlib
import io
import json
import random
import zipfile
from pathlib import Path

import pytest

from aquasource.adapters import seatizen as sz
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "seatizen"
RECORD = json.loads((FIX / "zenodo_record_13170795.json").read_text())
METADATA_ZIP = (FIX / "zenodo_13170795_METADATA.zip").read_bytes()
METADATA_URL = "https://zenodo.org/api/records/13170795/files/METADATA.zip/content"
SESSION_NAME = "20150611_REU-St-Gilles_scuba"
FIRST_FILE = "20150611_REU-St-Gilles_scuba_G0043959.JPG"


class FakeHttp(Http):
    """Serves ``files`` {url: bytes} with Range support; any other request fails the test."""

    def __init__(self, files=None, dry_run=False):
        super().__init__(dry_run=dry_run)
        self.files = files or {}

    def request(self, method, url, **kwargs):  # pragma: no cover - only when a test leaks a request
        raise AssertionError(f"unexpected network request: {method} {url}")

    def get(self, url, **kwargs):
        if url not in self.files:
            raise AssertionError(f"unexpected GET {url}")
        resp = type("R", (), {"content": self.files[url], "status_code": 200})()
        return resp

    def get_range(self, url, start, end, *, kind="metadata"):
        return self.files[url][start : end + 1]


def metadata_csv(blob=METADATA_ZIP) -> str:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        return zf.read("metadata.csv").decode()


def write_cache(layout, session_csv, record):
    (layout.raw / "session_doi.csv").write_text(session_csv, encoding="utf-8")
    (layout.raw / "records").mkdir(parents=True, exist_ok=True)
    (layout.raw / "records" / "11408925.json").write_text(json.dumps(record))


def make_adapter(tmp_path, *, session_csv=None, record=None, http=None, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "seatizen").ensure()
    csv_text = session_csv or f"session_name,session_doi,place,date,raw_data,processed_data\n{SESSION_NAME},https://doi.org/10.5281/zenodo.11408925,ST-GILLES,2015-06-11,1,0\n"
    write_cache(layout, csv_text, record or RECORD)
    http = http or FakeHttp()
    http.files.setdefault(METADATA_URL, METADATA_ZIP)  # METADATA.zip is read by range requests unless cached
    ctx = Context(cfg, http, layout, options, options.pop("dry_run", False), JsonlLog(layout.failures_jsonl))
    return get_adapter_class("seatizen")(ctx), layout


def synthetic_dcim(names):
    """A zip with the real member names, stored and deflated members, random JPEG-looking bytes (synthetic)."""
    rng = random.Random(1)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i, name in enumerate(names):
            body = b"\xff\xd8\xff\xe0" + bytes(rng.getrandbits(8) for _ in range(3000))
            zf.writestr(name, body, compress_type=zipfile.ZIP_DEFLATED if i % 2 else zipfile.ZIP_STORED)
    return buf.getvalue()


# ------------------------------------------------------------------------------------------- pure helpers
@pytest.mark.parametrize(
    "spdx, access, tier",
    [("cc-by-4.0", "open", "B"), ("cc-zero", "open", "A"), ("cc-by-sa-4.0", "open", "C"),
     ("cc-by-nc-4.0", "open", "X"), ("cc-by-nd-4.0", "open", "X"), ("cc-by-4.0", "restricted", "U"), ("", "open", "U")],
)
def test_licence_tiers(spdx, access, tier):
    assert sz.licence_tier(spdx, access) == tier


def test_fixture_licence_is_record_level_cc_by():
    assert RECORD["metadata"]["license"]["id"] == "cc-by-4.0"
    assert RECORD["metadata"]["access_right"] == "open"
    assert sz.licence_tier("cc-by-4.0", "open") == "B"


@pytest.mark.parametrize(
    "name, platform",
    [("20150611_REU-St-Gilles_scuba", "scuba"), ("20210311_MDG-Toliara_UVC-01_02", "uvc"),
     ("20230906_REU-BOUCAN_ASV-1_02", "asv"), ("20240405_REU-HERMITAGE_UAV-01_01", "aerial"),
     ("20180407_MUS-Le-Morne-with-Aerial_KITE-01_01", "aerial"), ("weird", "unknown")],
)
def test_platform_from_session_name(name, platform):
    assert sz.platform_of(name) == platform


def test_exif_time_and_session_doi():
    assert sz.exif_time_iso("2015:06:11 04:26:11Z") == "2015-06-11T04:26:11Z"
    assert sz.exif_time_iso("") is None
    assert sz.session_doi_id("https://doi.org/10.5281/zenodo.11408925") == "11408925"


def test_index_csv_parsing(tmp_path):
    adapter, layout = make_adapter(tmp_path, session_csv=(FIX / "session_doi_head.csv").read_text())
    sessions = adapter._sessions()
    assert len(sessions) == 5
    assert sessions[0] == {"session_name": "20150611_REU-St-Gilles_scuba", "record_id": "11408925",
                           "place": "ST-GILLES", "date": "2015-06-11"}


# ------------------------------------------------------------------------------------------- metadata
def test_fixture_metadata_rows_are_real_exif_gps():
    import csv
    rows = list(csv.DictReader(io.StringIO(metadata_csv())))
    assert len(rows) == 141
    assert rows[0]["FileName"] == FIRST_FILE
    assert all(r["GPSMapDatum"] == "WGS-84" for r in rows)
    assert all(sz.valid_coordinate(float(r["GPSLatitude"]), float(r["GPSLongitude"])) for r in rows)


def test_discover_yields_georeferenced_images(tmp_path):
    adapter, _ = make_adapter(tmp_path, order="table")
    cands = list(adapter.discover())
    assert len(cands) == 141
    c = cands[0]
    assert c.item_id == f"13170795/{FIRST_FILE}"  # record id from the Zenodo answer, not the DOI in the index
    assert c.extra["platform"] == "scuba" and "maybe_not_underwater" not in c.extra
    assert c.origin_url == "https://zenodo.org/records/13170795"
    geo = adapter.resolve_geo(c)
    assert (geo.geo_precision, geo.geo_inferred, geo.depth_m, geo.geo_uncertainty_m) == ("image", False, None, None)
    assert geo.lat == pytest.approx(-21.0519751799925) and geo.lon == pytest.approx(55.2228493199944)
    lic = adapter.resolve_licence(c)
    assert (lic.tier, lic.level, lic.name) == ("B", "record", "cc-by-4.0")
    assert "Seatizen Atlas session" in lic.attribution and "10.1038/s41597-024-04267-z" in lic.attribution


def test_aerial_session_is_kept_and_marked(tmp_path):
    csv_text = ("session_name,session_doi,place,date,raw_data,processed_data\n"
                "20240405_REU-HERMITAGE_UAV-01_01,https://doi.org/10.5281/zenodo.11408925,HERMITAGE,2024-04-05,1,0\n")
    adapter, _ = make_adapter(tmp_path, session_csv=csv_text, max_per_session=3)
    cands = list(adapter.discover())
    assert len(cands) == 3
    assert all(c.extra["maybe_not_underwater"] is True and c.extra["platform"] == "aerial" for c in cands)


def test_nc_session_is_not_yielded(tmp_path):
    record = json.loads(json.dumps(RECORD))
    record["metadata"]["license"] = {"id": "cc-by-nc-4.0"}
    adapter, _ = make_adapter(tmp_path, record=record)
    assert list(adapter.discover()) == []
    assert adapter.skipped and any("cc-by-nc-4.0" in k for k in adapter.skipped)


def test_geo_gate_drops_rows_without_gps_unless_asked(tmp_path):
    import csv
    rows = list(csv.DictReader(io.StringIO(metadata_csv())))
    rows[0]["GPSLatitude"] = ""
    rows[1]["GPSLatitude"] = "0"
    rows[1]["GPSLongitude"] = "0"
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    adapter, layout = make_adapter(tmp_path, order="table")
    (layout.raw / "zip").mkdir(exist_ok=True)
    (layout.raw / "zip" / "13170795_metadata.csv").write_text(out.getvalue())
    assert len(list(adapter.discover())) == 139
    adapter2, layout2 = make_adapter(tmp_path / "b", geo_only=False, order="table")
    (layout2.raw / "zip").mkdir(exist_ok=True)
    (layout2.raw / "zip" / "13170795_metadata.csv").write_text(out.getvalue())
    cands = list(adapter2.discover())
    assert len(cands) == 141
    assert adapter2.resolve_geo(cands[0]).geo_precision == "none"


# ------------------------------------------------------------------------------------------- media
def test_range_read_of_one_member_matches_crc(tmp_path):
    import csv
    names = [r["FileName"] for r in csv.DictReader(io.StringIO(metadata_csv()))]
    dcim = synthetic_dcim(names)
    record = json.loads(json.dumps(RECORD))
    for f in record["files"]:
        if f["key"] == "DCIM.zip":
            f["size"] = len(dcim)
            f["links"]["self"] = "https://zenodo.test/DCIM.zip"
    http = FakeHttp({"https://zenodo.test/DCIM.zip": dcim})
    adapter, layout = make_adapter(tmp_path, record=record, http=http, max_per_session=2, order="table")
    cands = list(adapter.discover())
    assert len(cands) == 2
    dest_dir = tmp_path / "out"
    for c in cands:
        ref = adapter.resolve_media(c)
        dest = dest_dir / f"{c.item_id.replace('/', '_')}.jpg"
        nbytes, sha = adapter.fetch_media(c, ref, dest)
        expected = zipfile.ZipFile(io.BytesIO(dcim)).read(c.extra["member"])
        assert dest.read_bytes() == expected
        assert nbytes == len(expected) and sha == hashlib.sha256(expected).hexdigest()
    assert (layout.raw / "zipindex" / "13170795_DCIM.json").exists()


def test_missing_member_and_bad_crc_are_errors(tmp_path):
    dcim = synthetic_dcim([FIRST_FILE])
    record = json.loads(json.dumps(RECORD))
    for f in record["files"]:
        if f["key"] == "DCIM.zip":
            f["size"] = len(dcim)
            f["links"]["self"] = "https://zenodo.test/DCIM.zip"
    http = FakeHttp({"https://zenodo.test/DCIM.zip": dcim})
    adapter, _ = make_adapter(tmp_path, record=record, http=http, max_per_session=1, order="table")
    (cand,) = list(adapter.discover())
    ref = adapter.resolve_media(cand)
    ref.extra["entry"]["crc"] ^= 1
    with pytest.raises(HttpError):
        adapter.fetch_media(cand, ref, tmp_path / "x.jpg")
    assert not (tmp_path / "x.jpg").exists()
    cand.extra["member"] = "nope.JPG"
    with pytest.raises(HttpError):
        adapter.resolve_media(cand)


def test_metadata_csv_is_read_by_range_requests(tmp_path):
    http = FakeHttp({METADATA_URL: METADATA_ZIP})
    adapter, layout = make_adapter(tmp_path, http=http)
    assert len(list(adapter.discover())) == 141
    assert (layout.raw / "zip" / "13170795_metadata.csv").read_text().startswith("ApertureValue,")
    assert (layout.raw / "zipindex" / "13170795_METADATA.json").exists()


def test_discover_makes_no_media_requests(tmp_path):
    adapter, _ = make_adapter(tmp_path, dry_run=True)
    assert len(list(adapter.discover())) == 141


def test_asv_frame_archive_and_ppk_uncertainty(tmp_path):
    """ASV sessions: PROCESSED_DATA_FRAMES.zip instead of DCIM.zip; GPSsde / GPSsdn give the horizontal sigma."""
    import csv
    rows = list(csv.DictReader(io.StringIO(metadata_csv())))
    fields = list(rows[0].keys()) + ["GPSsde", "GPSsdn"]
    for r in rows:
        r["GPSsde"], r["GPSsdn"] = "0.003", "0.004"
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)
    frames = synthetic_dcim([r["FileName"] for r in rows[:3]])
    record = json.loads(json.dumps(RECORD))
    for f in record["files"]:
        if f["key"] == "DCIM.zip":
            f["key"] = "PROCESSED_DATA_FRAMES.zip"
            f["size"] = len(frames)
            f["links"]["self"] = "https://zenodo.test/FRAMES.zip"
    http = FakeHttp({"https://zenodo.test/FRAMES.zip": frames})
    adapter, layout = make_adapter(tmp_path, record=record, http=http, max_per_session=2, order="table")
    (layout.raw / "zip").mkdir(exist_ok=True)
    (layout.raw / "zip" / "13170795_metadata.csv").write_text(out.getvalue())
    cands = list(adapter.discover())
    assert len(cands) == 2 and cands[0].extra["zip_key"] == "PROCESSED_DATA_FRAMES.zip"
    geo = adapter.resolve_geo(cands[0])
    assert geo.geo_uncertainty_m == pytest.approx(0.005)
    assert "maybe_not_underwater" not in cands[0].extra
    ref = adapter.resolve_media(cands[0])
    dest = tmp_path / "frame.jpg"
    adapter.fetch_media(cands[0], ref, dest)
    assert dest.read_bytes() == zipfile.ZipFile(io.BytesIO(frames)).read(cands[0].extra["member"])
    assert (layout.raw / "zipindex" / "13170795_PROCESSED_DATA_FRAMES.json").exists()


def test_find_member_exact_prefixed_and_ambiguous():
    entries = {"100GOPRO/G0030642.JPG": {"name": "100GOPRO/G0030642.JPG"}, "x.jpeg": {"name": "x.jpeg"},
               "a/dup.JPG": {"name": "a/dup.JPG"}, "b/dup.JPG": {"name": "b/dup.JPG"}}
    assert sz.find_member("x.jpeg", entries)["name"] == "x.jpeg"
    assert sz.find_member("20181209_MUS-Ilot-Sancho_SURF-01_01_G0030642.JPG", entries)["name"] == "100GOPRO/G0030642.JPG"
    assert sz.find_member("20181209_sess_dup.JPG", entries) is None
    assert sz.find_member("missing.JPG", entries) is None
