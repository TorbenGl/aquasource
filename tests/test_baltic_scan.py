"""Offline tests for the Mendeley wsd42v8mk5 (baltic_scan) adapter.

No network. The central directory is either the real one saved in tests/fixtures/baltic_scan/ (discover, geo and
licence tests) or a synthetic zip built in memory and served through a fake HTTP client (parsing and fetch tests).
Provenance: tests/fixtures/baltic_scan/SOURCE.md.
"""

import hashlib
import io
import json
import random
import zipfile
from pathlib import Path

import pytest

from aquasource.adapters import baltic_scan as mod
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "baltic_scan"
RAW = mod.RAW_DIR
TOTAL = 3409429991


class _Resp:
    def __init__(self, status=200, headers=None, body=b""):
        self.status_code = status
        self.headers = headers or {}
        self._body = body

    def iter_content(self, n):
        for i in range(0, len(self._body), n):
            yield self._body[i : i + n]

    def close(self):
        pass


class FakeHttp(Http):
    """Serves one in-memory archive behind the public API redirect; any other request fails the test."""

    def __init__(self, blob: bytes | None = None):
        super().__init__(dry_run=False)
        self.blob = blob
        self.total = len(blob) if blob is not None else TOTAL
        self.signed = "https://prod-dcd-datasets-cache-zipfiles.example.invalid/wsd42v8mk5-1.zip?sig=test"

    def request(self, method, url, *, kind="metadata", **kwargs):
        if url == mod.ZIP_API:
            assert kwargs.get("allow_redirects") is False
            return _Resp(302, {"Location": self.signed})
        assert url == self.signed, url
        rng = kwargs.get("headers", {}).get("Range", "")
        a, b = (int(x) for x in rng.split("=", 1)[1].split("-"))
        if self.blob is None:
            raise AssertionError("no archive served in this test")
        if a == 0 and b == 0:
            return _Resp(206, {"Content-Range": f"bytes 0-0/{self.total}"}, self.blob[0:1])
        return _Resp(206, {}, self.blob[a : b + 1])

    def get_range(self, url, start, end, *, kind="metadata"):
        assert url == self.signed, url
        assert self.blob is not None, "no archive served in this test"
        return self.blob[start : end + 1]


def make_adapter(tmp_path, http=None, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "baltic_scan").ensure()
    ctx = Context(cfg, http or FakeHttp(), layout, options, False, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("baltic_scan")(ctx)


def use_fixture_entries(adapter):
    """Cache the real central directory (19 entries) so discover runs without the archive."""
    entries = json.loads((FIX / "zip_entries_wsd42v8mk5_1.json").read_text(encoding="utf-8"))
    adapter.ctx.save_raw(mod.ENTRIES_CACHE, json.dumps(entries))
    return adapter


def payload(seed: int, n: int = 4000) -> bytes:
    rnd = random.Random(seed)
    return bytes(rnd.randrange(256) for _ in range(n))


SYN = {
    f"{RAW}DE01_1.jpg": (payload(1), zipfile.ZIP_DEFLATED),
    f"{RAW}SM08_1.avi": (payload(2), zipfile.ZIP_STORED),
    f"{RAW}XX99_1.jpg": (payload(3), zipfile.ZIP_DEFLATED),  # unknown station prefix
    f"{RAW.rsplit('Raw data', 1)[0]}Frames/Biological features/Baltic_bio.rar": (payload(4), zipfile.ZIP_STORED),
}


def build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, (data, method) in SYN.items():
            zf.writestr(zipfile.ZipInfo(name, date_time=(2022, 6, 1, 0, 0, 0)), data, compress_type=method)
    return buf.getvalue()


ZIP = build_zip()


def test_registered(tmp_path):
    a = make_adapter(tmp_path)
    assert a.key == "baltic_scan"
    assert set(a.media_types) == {"image", "video"}


def test_fixture_directory_is_complete():
    entries = json.loads((FIX / "zip_entries_wsd42v8mk5_1.json").read_text(encoding="utf-8"))
    raw = [e for e in entries if e["name"].startswith(RAW)]
    assert len(entries) == 19 and len(raw) == 15
    assert sum(e["name"].endswith(".jpg") for e in raw) == 8
    assert sum(e["name"].endswith(".avi") for e in raw) == 7


def test_discover_fixture_keeps_raw_mosaics_and_videos(tmp_path):
    a = use_fixture_entries(make_adapter(tmp_path))
    cands = list(a.discover())
    assert len(cands) == 15  # 8 JPEG mosaics + 7 AVI; RAR annotation sets are not read
    assert sum(c.media_type == "image" for c in cands) == 8
    assert sum(c.media_type == "video" for c in cands) == 7
    assert all(c.media_url == mod.ZIP_API for c in cands)
    assert all(c.origin_url == mod.LANDING for c in cands)
    assert all(c.timestamp is None for c in cands)


def test_kinds_option(tmp_path):
    v = list(use_fixture_entries(make_adapter(tmp_path, kinds="video")).discover())
    assert len(v) == 7 and all(c.ext == "avi" for c in v)
    i = list(use_fixture_entries(make_adapter(tmp_path, kinds="image")).discover())
    assert len(i) == 8 and all(c.ext == "jpg" for c in i)


def test_geo_is_station_from_publication(tmp_path):
    a = use_fixture_entries(make_adapter(tmp_path))
    by_station = {}
    for c in a.discover():
        by_station.setdefault(c.extra["station"], a.resolve_geo(c))
    assert by_station["DE01"].lat == pytest.approx(55.39904)
    assert by_station["DE01"].lon == pytest.approx(20.62784)
    assert by_station["SM08"].lat == pytest.approx(55.92360)
    assert by_station["SM08"].lon == pytest.approx(21.04100)
    g = by_station["SM02"]
    assert g.geo_precision == "station"
    assert g.depth_m is None and g.geo_uncertainty_m is None
    assert g.geo_inferred is True
    assert "wsd42v8mk5" in g.geo_source


def test_licence_is_cc_by_record_level(tmp_path):
    a = use_fixture_entries(make_adapter(tmp_path))
    c = next(a.discover())
    lic = a.resolve_licence(c)
    assert lic.tier == "B"
    assert lic.level == "record"


def test_unknown_prefix_is_reported_not_dropped(tmp_path):
    entries = json.loads((FIX / "zip_entries_wsd42v8mk5_1.json").read_text(encoding="utf-8"))
    entries.append({"name": f"{RAW}XX99_1.jpg", "file_size": 10, "compress_size": 10, "method": 0, "header_offset": 0})
    a = make_adapter(tmp_path)
    a.ctx.save_raw(mod.ENTRIES_CACHE, json.dumps(entries))
    cands = list(a.discover())
    assert not any("XX99" in c.item_id for c in cands)
    fails = (tmp_path / "baltic_scan").rglob("*")
    assert any(p.name.endswith(".jsonl") and "XX99" in p.read_text() for p in fails if p.is_file())


def test_parse_central_directory_from_synthetic_zip():
    tail = ZIP[-65536:] if len(ZIP) > 65536 else ZIP
    base = len(ZIP) - len(tail)
    entries = mod.parse_central_directory(tail, lambda a, b: ZIP[a : b + 1])
    names = {e["name"] for e in entries}
    assert names == set(SYN)
    for e in entries:
        assert e["file_size"] == len(SYN[e["name"]][0])
    assert base >= 0


def test_fetch_deflated_and_stored_members_match_sha(tmp_path):
    http = FakeHttp(ZIP)
    a = make_adapter(tmp_path, http=http)
    a.ctx.save_raw(mod.ENTRIES_CACHE, json.dumps(mod.parse_central_directory(ZIP, lambda x, y: ZIP[x : y + 1])))
    for c in a.discover():
        if c.raw["member"] not in (f"{RAW}DE01_1.jpg", f"{RAW}SM08_1.avi"):
            continue
        dest = tmp_path / "out" / c.sample_id / f"x.{c.ext}"
        ref = a.resolve_media(c)
        n, sha = a.fetch_media(c, ref, dest)
        want = SYN[c.raw["member"]][0]
        assert n == len(want)
        assert sha == hashlib.sha256(want).hexdigest()
        assert dest.read_bytes() == want
        assert not dest.with_name(dest.name + ".part").exists()


def test_fetch_rejects_wrong_local_name(tmp_path):
    http = FakeHttp(ZIP)
    a = make_adapter(tmp_path, http=http)
    a.ctx.save_raw(mod.ENTRIES_CACHE, json.dumps(mod.parse_central_directory(ZIP, lambda x, y: ZIP[x : y + 1])))
    c = next(c for c in a.discover() if c.raw["member"].endswith("DE01_1.jpg"))
    c.raw["member"] = f"{RAW}SM02_1.jpg"
    with pytest.raises(ValueError):
        a.fetch_media(c, a.resolve_media(c), tmp_path / "bad.jpg")


def test_redirect_missing_raises(tmp_path):
    class NoRedirect(FakeHttp):
        def request(self, method, url, **kwargs):
            return _Resp(200, {})

    a = make_adapter(tmp_path, http=NoRedirect())
    with pytest.raises(HttpError):
        a.signed_url()
