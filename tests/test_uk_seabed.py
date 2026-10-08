"""Offline tests for the UK seabed (JNCC Bassurelle still photographs, OGL) adapter.

No network. Discover uses the real central-directory subset saved in tests/fixtures/uk_seabed/ (cached as the
adapter's entries file). Fetch tests build a small synthetic zip in memory and serve it through a fake Range reader.
Provenance of the fixtures: tests/fixtures/uk_seabed/SOURCE.md.
"""

import hashlib
import io
import json
import random
import zipfile
from pathlib import Path

import pytest

from aquasource.adapters import uk_seabed as mod
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "uk_seabed"
ARCHIVE = mod.ARCHIVES[0]
URL = ARCHIVE["url"]


class FakeHttp(Http):
    """Serves one in-memory archive for Range reads and HEAD; any other request fails the test."""

    def __init__(self, blob: bytes | None = None):
        super().__init__(dry_run=False)
        self.blob = blob
        self.ranges: list[tuple[int, int]] = []

    def get_range(self, url, start, end, *, kind="metadata"):
        assert url == URL, url
        assert self.blob is not None, "no archive served in this test"
        self.ranges.append((start, end))
        return self.blob[start : end + 1]

    def head(self, url, **kwargs):
        class Resp:
            status_code = 200
            headers = {"Content-Length": str(len(self.blob or b""))}

        assert url == URL, url
        return Resp()

    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def jpeg_bytes(seed: int, n: int = 3000) -> bytes:
    rnd = random.Random(seed)
    return b"\xff\xd8\xff\xe0" + bytes(rnd.randrange(256) for _ in range(n))


SYN = {
    "still_photographs/BSSS_CEND0313_BSSS033_STN_298_A1/BSSS_CEND0313_BSSS033_STN_298_A1_001.JPG": (
        jpeg_bytes(1),
        zipfile.ZIP_DEFLATED,
    ),
    "still_photographs/BSSS_CEND0313_BSSS033_STN_298_A1/BSSS_CEND0313_BSSS033_STN_298_A1_002.JPG": (
        jpeg_bytes(2),
        zipfile.ZIP_STORED,
    ),
    "still_photographs/BSSS_CEND0313_BSSS033_STN_298_A1/1.txt": (b"x\tYYYY\n", zipfile.ZIP_DEFLATED),
    "still_photographs/BSSS_CEND0313_BSSS033_STN_298_A1/Thumbs.db": (b"\x00\x01", zipfile.ZIP_DEFLATED),
    "still_photographs/notes/broken_name.jpg": (jpeg_bytes(3), zipfile.ZIP_DEFLATED),  # no STN_ folder
}


def build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, (data, method) in SYN.items():
            zf.writestr(zipfile.ZipInfo(name, date_time=(2013, 3, 29, 0, 0, 0)), data, compress_type=method)
    return buf.getvalue()


ZIP = build_zip()


def make_adapter(tmp_path, http=None, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "uk_seabed").ensure()
    ctx = Context(cfg, http or FakeHttp(), layout, options, False, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("uk_seabed")(ctx)


def use_fixture_entries(adapter):
    """Cache the real central-directory subset so discover runs without the archive."""
    subset = json.loads((FIX / "zip_entries_bassurelle_subset.json").read_text(encoding="utf-8"))
    adapter.ctx.save_raw(f"uk_seabed/{ARCHIVE['id']}_entries.json", json.dumps(subset))
    return adapter


def test_registered(tmp_path):
    a = make_adapter(tmp_path)
    assert a.key == "uk_seabed"
    assert a.media_types == ("image",)


def test_discover_fixture_keeps_station_jpegs_only(tmp_path):
    a = use_fixture_entries(make_adapter(tmp_path))
    cands = list(a.discover())
    assert len(cands) == 30  # the first 30 JPEG entries of the real archive subset; txt/ini are not media
    assert all(c.media_type == "image" and c.ext == "jpg" for c in cands)
    assert all(c.media_url == URL for c in cands)
    c = cands[0]
    assert c.extra["station"] == "STN_343"
    assert c.raw["member"].endswith("BSSS_CEND0313_ADDGT01_STN_343_A1_001.JPG")
    assert c.timestamp is None
    assert c.origin_url.startswith("https://ckan.publishing.service.gov.uk/dataset/")


def test_fixture_entries_are_real_zip_members(tmp_path):
    entries = json.loads((FIX / "zip_entries_bassurelle_subset.json").read_text(encoding="utf-8"))
    assert entries[0]["header_offset"] == 59
    assert all(e["method"] in (0, 8) for e in entries)
    assert any(e["name"].endswith("1.txt") for e in entries)


def test_licence_is_ogl_record_level(tmp_path):
    a = use_fixture_entries(make_adapter(tmp_path))
    c = next(a.discover())
    lic = a.resolve_licence(c)
    assert lic.tier == "B"
    assert lic.level == "record"
    assert "Open Government Licence" in lic.attribution


def test_geo_is_region_centre_of_survey_bbox(tmp_path):
    a = use_fixture_entries(make_adapter(tmp_path))
    g = a.resolve_geo(next(a.discover()))
    assert g.geo_precision == "region"
    assert g.geo_inferred is True
    assert (g.lat, g.lon) == pytest.approx((50.607, 1.038))
    assert g.geo_uncertainty_m == pytest.approx(9900)
    assert g.depth_m is None
    assert "bbox" in g.geo_source
    # The centre lies inside the CKAN bounding box.
    assert 50.548 <= g.lat <= 50.666 and 0.934 <= g.lon <= 1.142


def test_entries_are_read_with_range_requests(tmp_path):
    http = FakeHttp(ZIP)
    a = make_adapter(tmp_path, http=http)
    entries = a.entries(ARCHIVE)
    assert sorted(e["name"] for e in entries) == sorted(SYN)
    assert sum(e - s + 1 for s, e in http.ranges) < len(ZIP)  # the whole archive is not transferred
    assert (a.ctx.layout.raw / f"uk_seabed/{ARCHIVE['id']}_entries.json").exists()


def test_fetch_inflates_deflated_and_stored_jpegs(tmp_path):
    http = FakeHttp(ZIP)
    a = make_adapter(tmp_path, http=http)
    cands = list(a.discover())
    assert len(cands) == 2  # the synthetic zip has two station JPEGs; the 'broken_name' one has no STN folder
    for cand in cands:
        ref = a.resolve_media(cand)
        dest = tmp_path / f"{cand.sample_id}.jpg"
        size, sha = a.fetch_media(cand, ref, dest)
        original = SYN[cand.raw["member"]][0]
        assert dest.read_bytes() == original
        assert size == len(original)
        assert sha == hashlib.sha256(original).hexdigest()
        assert not dest.with_name(dest.name + ".part").exists()


def test_fetch_rejects_wrong_local_name(tmp_path):
    http = FakeHttp(ZIP)
    a = make_adapter(tmp_path, http=http)
    cand = next(a.discover())
    cand.raw["member"] = cand.raw["member"] + "x"
    with pytest.raises(ValueError):
        a.fetch_media(cand, a.resolve_media(cand), tmp_path / "x.jpg")


def test_head_failure_is_reported(tmp_path):
    class NoLength(FakeHttp):
        def head(self, url, **kwargs):
            class Resp:
                status_code = 404
                headers = {}

            return Resp()

    a = make_adapter(tmp_path, http=NoLength(ZIP))
    with pytest.raises(HttpError):
        a.archive_size(URL)
