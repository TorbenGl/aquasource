"""Offline tests for the smithsonian_oa adapter (fixtures: tests/fixtures/smithsonian_oa, see SOURCE.md)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aquasource.adapters import smithsonian_oa as so
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog
from aquasource.core.schema import sample_row

FIX = Path(__file__).parent / "fixtures" / "smithsonian_oa"
RECORDS = FIX / "records_nmnhinv_marine.jsonl"
DECAPODA = "ld1-1643412364509-1643412431822-0"
PARANDANIEXIS = "ld1-1643411218332-1643411254826-1"
BARGMANNIA = "ld1-1703589922361-1703589959600-1"


class FakeResponse:
    def __init__(self, lines: list[bytes]):
        self._lines = lines
        self.closed = False

    def iter_lines(self):
        yield from self._lines

    def close(self):
        self.closed = True


class FakeHttp(Http):
    """Serves the fixture records as the shard of nmnhinv/00 and a one-line index. No network."""

    def __init__(self, shard_lines: list[bytes], index_text: str = ""):
        super().__init__(dry_run=True)
        self.shard_lines = shard_lines
        self.index_text = index_text
        self.shard_urls: list[str] = []

    def get_text(self, url, **kwargs):
        assert url.endswith("/index.txt"), url
        return self.index_text

    def get(self, url, **kwargs):
        self.shard_urls.append(url)
        assert kwargs.get("stream") is True
        return FakeResponse(self.shard_lines)

    def request(self, *a, **k):  # pragma: no cover - a leaked request would be a bug
        raise AssertionError(f"unexpected network request: {a[:2]}")


def records() -> list[bytes]:
    return [line.encode() for line in RECORDS.read_text(encoding="utf-8").splitlines() if line.strip()]


def make_adapter(tmp_path, http: FakeHttp, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "smithsonian_oa").ensure()
    opts = {"units": "nmnhinv", "shards": 1, **options}
    ctx = Context(cfg, http, layout, opts, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("smithsonian_oa")(ctx)


def index_for(unit: str = "nmnhinv", n: int = 2) -> str:
    base = f"{so.BUCKET}/{unit}"
    return "\n".join(f"{base}/{i:02d}.txt" for i in range(n)) + "\n"


def by_record(cands):
    return {c.raw["record_id"]: c for c in cands}


def test_registered_and_shard_stream_is_closed(tmp_path):
    http = FakeHttp(records(), index_for())
    adapter = make_adapter(tmp_path, http)
    cands = list(adapter.discover())
    assert http.shard_urls == [f"{so.BUCKET}/nmnhinv/00.txt"]  # shards=1: only the first shard is read
    assert len(cands) == 3


def test_candidates_carry_screen_image_and_flags(tmp_path):
    adapter = make_adapter(tmp_path, FakeHttp(records(), index_for()))
    got = by_record(adapter.discover())
    dec = got[DECAPODA]
    assert dec.media_url.startswith("https://ids.si.edu/ids/download?id=") and dec.media_url.endswith("_screen")
    assert dec.ext == "jpg" and dec.source == "smithsonian_oa"
    # specimen-type records of this fixture carry no in-situ keyword ("backreef" is a locality, not a dive photo)
    assert dec.extra["maybe_not_underwater"] is True
    assert got[PARANDANIEXIS].extra["maybe_not_underwater"] is True
    assert all(c.extra["marine_place"] for c in got.values())
    rec = json.loads(records()[0])
    rec["content"]["freetext"]["notes"] = [{"label": "Notes", "content": "ROV dive, 300 m, in situ photo"}]
    rec["id"] = "in-situ-test"
    adapter = make_adapter(tmp_path, FakeHttp([json.dumps(rec).encode()], index_for()))
    assert next(iter(adapter.discover())).extra["maybe_not_underwater"] is False


def test_licence_is_cc0_record_level(tmp_path):
    adapter = make_adapter(tmp_path, FakeHttp(records(), index_for()))
    for cand in adapter.discover():
        lic = adapter.resolve_licence(cand)
        assert lic.tier == "A"
        assert lic.level == "record"
        assert lic.url == so.CC0_URL
        assert lic.name == "CC0"


def test_geo_is_published_locality_region_precision(tmp_path):
    adapter = make_adapter(tmp_path, FakeHttp(records(), index_for()))
    got = by_record(adapter.discover())
    geo = adapter.resolve_geo(got[DECAPODA])
    assert geo.geo_precision == "region"
    assert geo.geo_inferred is False
    assert geo.geo_uncertainty_m is None
    assert geo.lat is not None and geo.lon is not None
    assert geo.depth_m is not None and geo.depth_m >= 0
    # the coordinate is the one in the record, not an invented one
    raw = got[DECAPODA].raw["point"]
    assert (geo.lat, geo.lon) == raw


def test_samples_row_is_complete(tmp_path):
    adapter = make_adapter(tmp_path, FakeHttp(records(), index_for()))
    cand = next(iter(adapter.discover()))
    row = sample_row(cand, adapter.resolve_licence(cand), adapter.resolve_geo(cand))
    assert row["licence_tier"] == "A" and row["geo_precision"] == "region"
    assert row["lat"] is not None and row["origin_url"].startswith("http")


def test_budget_style_stop_closes_stream(tmp_path):
    http = FakeHttp(records(), index_for())
    adapter = make_adapter(tmp_path, http)
    gen = adapter.discover()
    next(gen)
    gen.close()  # the runner stops the generator at the budget; the shard response must be released


def test_skips_records_without_coordinates_or_marine_place(tmp_path):
    lines = records()
    rec = json.loads(lines[0])
    rec["content"]["indexedStructured"]["geoLocation"] = [{"L1": {"type": "Continent", "content": "Atlantic"}}]
    rec["id"] = "no-coords"
    inland = json.loads(lines[1])
    inland["id"] = "inland"
    inland["content"]["freetext"]["place"] = [{"label": "Place", "content": "Bolivia, Pando"}]
    inland["content"]["indexedStructured"]["geoLocation"] = [{"L1": {"type": "Continent", "content": "South America"}}]
    bad = b"{truncated json"
    adapter = make_adapter(tmp_path, FakeHttp([json.dumps(rec).encode(), json.dumps(inland).encode(), bad, b""], index_for()))
    assert list(adapter.discover()) == []
    adapter = make_adapter(tmp_path, FakeHttp([json.dumps(rec).encode()], index_for()), require_coords=False)
    got = list(adapter.discover())
    assert len(got) == 1 and adapter.resolve_geo(got[0]).geo_precision == "none"


def test_jpeg_check_rejects_html(tmp_path, monkeypatch):
    adapter = make_adapter(tmp_path, FakeHttp(records(), index_for()))
    cand = next(iter(adapter.discover()))
    dest = tmp_path / "x.jpg"

    def fake_download(self, url, dest, **kw):
        Path(dest).write_bytes(b"<html>error</html>")
        return 18, "0" * 64

    monkeypatch.setattr(Http, "download", fake_download)
    with pytest.raises(RuntimeError):
        adapter.fetch_media(cand, adapter.resolve_media(cand), dest)
    assert not dest.exists()


def test_check_options_rejects_bad_values():
    assert so.check_options({"units": "nmnhinv,nmnhfishes", "shards": 2}) == []
    assert so.check_options({"units": "../etc"})
    assert so.check_options({"shards": 0})
