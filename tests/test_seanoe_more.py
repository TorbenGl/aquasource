"""Offline tests for the SEANOE 10.17882/101899 adapter.

No network. The zip central directory is either the real subset saved in tests/fixtures/seanoe_more/ (discover and
geo tests) or a synthetic zip built in memory and served through a fake Range reader (entry reading and fetch tests).
The fixtures and their provenance are in tests/fixtures/seanoe_more/SOURCE.md.
"""

import hashlib
import io
import json
import random
import zipfile
from pathlib import Path

import pytest

from aquasource.adapters import seanoe_more as mod
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "seanoe_more"
ARC = mod.ARCHIVE_DIR


class FakeHttp(Http):
    """Serves one in-memory archive for Range reads and HEAD; any other request fails the test."""

    def __init__(self, blob: bytes | None = None):
        super().__init__(dry_run=False)
        self.blob = blob
        self.ranges: list[tuple[int, int]] = []

    def get_range(self, url, start, end, *, kind="metadata"):
        assert url == mod.ZIP_URL, url
        assert self.blob is not None, "no archive served in this test"
        self.ranges.append((start, end))
        return self.blob[start : end + 1]

    def head(self, url, **kwargs):
        class Resp:
            status_code = 200
            headers = {"Content-Length": str(len(self.blob or b""))}

        return Resp()

    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")



def frame_bytes(seed: int, n: int = 3000) -> bytes:
    rnd = random.Random(seed)
    return b"\xff\xd8\xff\xe0" + bytes(rnd.randrange(256) for _ in range(n))


SYN_FRAMES = {
    f"{ARC}CAM-TEMPO-MINI-2_20140704233556.jpg": (frame_bytes(1), zipfile.ZIP_DEFLATED),
    f"{ARC}CAM-TEMPO-MINI-2_20140705020018.jpg": (frame_bytes(2), zipfile.ZIP_STORED),
    f"{ARC}MOMAR_20141017055611.jpg": (frame_bytes(3), zipfile.ZIP_DEFLATED),
    f"{ARC}notes_20140101000000.jpg": (frame_bytes(4), zipfile.ZIP_DEFLATED),  # unknown camera prefix
    "dataset_seanoe_101899/cleaned-dataset.csv": (b";name_img\n0;MOMAR_20141017055611.jpg\n", zipfile.ZIP_DEFLATED),
}


def build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, (data, method) in SYN_FRAMES.items():
            zf.writestr(zipfile.ZipInfo(name, date_time=(2024, 1, 1, 0, 0, 0)), data, compress_type=method)
    return buf.getvalue()


ZIP = build_zip()


def make_adapter(tmp_path, http=None, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "seanoe_more").ensure()
    ctx = Context(cfg, http or FakeHttp(), layout, options, False, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("seanoe_more")(ctx)


def use_fixture_entries(adapter):
    """Cache the real central-directory subset so discover runs without the archive."""
    subset = json.loads((FIX / "zip_entries_101899_subset.json").read_text(encoding="utf-8"))
    adapter.ctx.save_raw(mod.ENTRIES_CACHE, json.dumps(subset))
    return adapter


def test_registered(tmp_path):
    a = make_adapter(tmp_path)
    assert a.key == "seanoe_more"
    assert a.media_types == ("image",)


def test_frame_name_parsing():
    assert mod.frame_stamp("CAM-TEMPO-MINI-2_20140704233556.jpg") == ("CAM-TEMPO-MINI-2", "2014-07-04T23:35:56Z")
    assert mod.frame_stamp("MOMAR_20141017055611.jpg") == ("MOMAR", "2014-10-17T05:56:11Z")
    assert mod.frame_stamp("readme.jpg") is None


def test_discover_fixture_keeps_frames_only(tmp_path):
    a = use_fixture_entries(make_adapter(tmp_path))
    cands = list(a.discover())
    assert len(cands) == 9  # 6 TEMPO + 3 MOMAR frames; CSV and README are not media
    assert all(c.media_type == "image" and c.ext == "jpg" for c in cands)
    assert all(c.media_url == mod.ZIP_URL for c in cands)
    c = cands[0]
    assert c.raw["member"].startswith(ARC)
    assert c.timestamp == "2014-07-04T23:35:56Z"
    assert c.origin_url == "https://doi.org/10.17882/101899"


def test_camera_filter_and_per_day(tmp_path):
    a = use_fixture_entries(make_adapter(tmp_path, cameras="MOMAR"))
    assert [c.extra["camera_prefix"] for c in a.discover()] == ["MOMAR"] * 3
    b = use_fixture_entries(make_adapter(tmp_path, per_day=1))
    days = [c.timestamp[:10] for c in b.discover()]
    assert len(days) == len(set(days)) and len(days) >= 1


def test_licence_is_cc_by_record_level(tmp_path):
    a = use_fixture_entries(make_adapter(tmp_path))
    c = next(a.discover())
    lic = a.resolve_licence(c)
    assert lic.tier == "B"
    assert lic.level == "record"
    assert lic.url == "https://creativecommons.org/licenses/by/4.0/"
    assert "10.17882/101899" in lic.attribution


def test_geo_is_fixed_site_per_camera(tmp_path):
    a = use_fixture_entries(make_adapter(tmp_path))
    cands = list(a.discover())
    tempo = next(c for c in cands if c.extra["camera_prefix"] == "CAM-TEMPO-MINI-2")
    momar = next(c for c in cands if c.extra["camera_prefix"] == "MOMAR")
    g_t, g_m = a.resolve_geo(tempo), a.resolve_geo(momar)
    assert g_t.geo_precision == g_m.geo_precision == "fixed_site"
    assert g_t.geo_inferred is True
    assert (g_t.lat, g_t.lon) == pytest.approx((48.503038, -125.554305))
    assert (g_m.lat, g_m.lon) == pytest.approx((37.2933, -32.2733))
    assert g_m.depth_m is None and g_m.geo_uncertainty_m is None
    assert "10.17882/101899" in g_t.geo_source


def test_entries_are_read_with_range_requests(tmp_path):
    http = FakeHttp(ZIP)
    a = make_adapter(tmp_path, http=http)
    entries = a.entries()
    assert sorted(e["name"] for e in entries) == sorted(SYN_FRAMES)
    assert sum(e - s + 1 for s, e in http.ranges) < len(ZIP)  # the whole archive is not transferred
    assert (a.ctx.layout.raw / mod.ENTRIES_CACHE).exists()  # cached for the next run


def test_fetch_inflates_deflated_and_stored_frames(tmp_path):
    http = FakeHttp(ZIP)
    a = make_adapter(tmp_path, http=http)
    cands = [c for c in a.discover() if c.raw["camera"] == "CAM-TEMPO-MINI-2"]
    assert len(cands) == 2  # 20140704... (deflated) and 20140705... (stored)
    for cand in cands:
        ref = a.resolve_media(cand)
        dest = tmp_path / f"{cand.sample_id}.jpg"
        size, sha = a.fetch_media(cand, ref, dest)
        original = SYN_FRAMES[cand.raw["member"]][0]
        assert dest.read_bytes() == original
        assert size == len(original)
        assert sha == hashlib.sha256(original).hexdigest()
        assert not dest.with_name(dest.name + ".part").exists()


def test_fetch_rejects_wrong_local_name(tmp_path):
    http = FakeHttp(ZIP)
    a = make_adapter(tmp_path, http=http)
    cand = next(c for c in a.discover() if c.raw["camera"] == "MOMAR")
    cand.raw["member"] = cand.raw["member"] + "x"
    with pytest.raises(ValueError):
        a.fetch_media(cand, a.resolve_media(cand), tmp_path / "x.jpg")


def test_inflate_size_mismatch_is_an_error():
    raw = zlib_raw(b"abc")
    assert mod.inflate_member(raw, 8, 3) == b"abc"
    with pytest.raises(ValueError):
        mod.inflate_member(raw, 8, 4)
    with pytest.raises(ValueError):
        mod.inflate_member(b"abc", 12, 3)


def zlib_raw(data: bytes) -> bytes:
    import zlib

    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(data) + c.flush()
