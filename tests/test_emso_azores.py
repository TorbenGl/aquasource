"""Offline tests for the EMSO-Azores SMOOVE adapter.

No network. The tar member listing is cached in metadata/raw/emso_azores/ from a synthetic ustar archive built in
memory (same header layout as the real SEANOE tars, which are range-readable). The real landing page facts are in
tests/fixtures/emso_azores/ (see SOURCE.md). The Http client refuses every request.
"""

import io
import json
import tarfile
from pathlib import Path

import pytest

from aquasource.adapters.base import Context, MediaRef, get_adapter_class
from aquasource.adapters.emso_azores import BLOCK, RECORDS, parse_members
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "emso_azores"
DOI = "101838"
TAR_REL = "data/112940.tar"
NAMES = ["smoove-24-08-17_00-06-37-46.mp4", "smoove-24-08-17_00-16-37-46.mp4", "readme.txt"]


def build_tar() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.USTAR_FORMAT) as tf:
        for name in NAMES:
            payload = (name.encode() * 700)[:1500]
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tf.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


TAR = build_tar()


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def read_block_from(data: bytes):
    def read_block(off: int) -> bytes:
        block = data[off : off + BLOCK]
        return block.ljust(BLOCK, b"\0")

    return read_block


def make_adapter(tmp_path, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "emso_azores").ensure()
    members = parse_members(read_block_from(TAR), len(TAR))
    members = [m for m in members if m["name"].endswith(".mp4")]
    (layout.raw / "emso_azores").mkdir(parents=True, exist_ok=True)
    cache = layout.raw / "emso_azores" / f"{DOI}_0.members.json"
    cache.write_text(json.dumps(members))
    ctx = Context(cfg, NoNet(dry_run=True), layout, options, True, JsonlLog(layout.failures_jsonl))
    adapter = get_adapter_class("emso_azores")(ctx)


    return adapter


def only_2023(monkeypatch):
    import aquasource.adapters.emso_azores as mod

    monkeypatch.setattr(mod, "RECORDS", tuple(r for r in RECORDS if r[0] == 2023))


def candidates(tmp_path, monkeypatch, **options):
    only_2023(monkeypatch)
    return list(make_adapter(tmp_path, **options).discover())


def test_registered(tmp_path):
    a = make_adapter(tmp_path)
    assert a.key == "emso_azores"
    assert a.media_types == ("video",)


def test_tar_headers_give_member_offsets():
    members = parse_members(read_block_from(TAR), len(TAR))
    assert [m["name"] for m in members] == NAMES
    first = members[0]
    assert first["size"] == 1500
    assert TAR[first["offset"] : first["offset"] + 1500] == (NAMES[0].encode() * 700)[:1500]


def test_discover_keeps_videos_only(tmp_path, monkeypatch):
    cands = candidates(tmp_path, monkeypatch)
    assert [c.raw["member"] for c in cands] == NAMES[:2]
    c = cands[0]
    assert c.media_type == "video"
    assert c.media_url == "https://www.seanoe.org/data/00906/101838/data/112940.tar"
    assert c.timestamp == "2024-08-17T00:06:37Z"
    assert c.origin_url == "https://doi.org/10.17882/101838"


def test_per_day_and_date_filters(tmp_path, monkeypatch):
    assert len(candidates(tmp_path, monkeypatch, per_day=1)) == 1
    assert candidates(tmp_path, monkeypatch, to="2024-08-16") == []
    assert len(candidates(tmp_path, monkeypatch, **{"from": "2024-08-17"})) == 2


def test_licence_is_cc_by_record_level(tmp_path, monkeypatch):
    c = candidates(tmp_path, monkeypatch)[0]
    lic = make_adapter(tmp_path).resolve_licence(c)
    assert lic.tier == "B"
    assert lic.level == "record"
    assert lic.url == "https://www.seanoe.org/data/00906/101838/"


def test_geo_is_publication_fixed_site(tmp_path, monkeypatch):
    c = candidates(tmp_path, monkeypatch)[0]
    geo = make_adapter(tmp_path).resolve_geo(c)
    assert geo.geo_precision == "fixed_site"
    assert geo.lat == pytest.approx(37.2889)
    assert geo.lon == pytest.approx(-32.275567)
    assert geo.depth_m == pytest.approx(1695.0)
    assert "SEANOE" in geo.geo_source


def test_media_ref_carries_byte_span(tmp_path, monkeypatch):
    c = candidates(tmp_path, monkeypatch)[0]
    ref = make_adapter(tmp_path).resolve_media(c)
    assert isinstance(ref, MediaRef)
    assert ref.extra == {"offset": c.raw["offset"], "size": 1500}
    assert ref.ext == "mp4"


def test_records_table_matches_research():
    years = [r[0] for r in RECORDS]
    assert years == sorted(years) and len(set(years)) == len(years)
    assert RECORDS[-1][1] == DOI
    assert len(RECORDS) == 10
