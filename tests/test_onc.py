"""Offline tests for the ONC (Oceans 3.0) adapter.

No network: the metadata responses are copied from tests/fixtures/onc/ (SYNTHETIC, see SOURCE.md) into the cache
metadata/raw/onc/ where the adapter reads them, and the HTTP client refuses every request.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aquasource.adapters import onc as mod
from aquasource.adapters.base import Context, MediaRef, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "onc"
LOC, CAT = "SYNLOC", "VIDEOCAM"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, monkeypatch, **options):
    monkeypatch.setenv("ONC_TOKEN", "test-token-not-real")
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "onc").ensure()
    raw = layout.raw / "onc"
    raw.mkdir(parents=True, exist_ok=True)
    (raw / f"deployments_{LOC}_{CAT}.json").write_text((FIX / "deployments_SYNTHETIC.json").read_text())
    # one month window (2024-08) -> one archivefile page
    (raw / f"archivefile_{LOC}_{CAT}_20240801_20240831_all_p0.json").write_text(
        (FIX / "archivefile_SYNTHETIC.json").read_text()
    )
    opts = {"locations": LOC, "categories": CAT, "from": "2024-08-01", "to": "2024-08-31", **options}
    ctx = Context(cfg, NoNet(dry_run=True), layout, opts, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("onc")(ctx)


def test_registered(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, monkeypatch)
    assert a.key == "onc"
    assert a.env_vars == ("ONC_TOKEN",)


def test_file_name_parsing():
    name = "NAXYS_HYD_007_20091231T235919.476Z-spect.png"
    assert mod.device_of(name) == "NAXYS_HYD_007"
    assert mod.file_time(name) == datetime(2009, 12, 31, 23, 59, 19, 476000, tzinfo=timezone.utc)
    assert mod.file_time("readme.txt") is None


def test_missing_token_and_locations(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, monkeypatch)
    monkeypatch.delenv("ONC_TOKEN")
    problems = a.check_ready()
    assert any("ONC_TOKEN" in p for p in problems)
    monkeypatch.setenv("ONC_TOKEN", "x")
    a.options.pop("locations")
    assert any("locations" in p for p in a.check_ready())


def test_discover_geo_licence(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, monkeypatch)
    cands = list(a.discover())
    names = [c.item_id for c in cands]
    assert "readme_without_timestamp.txt" not in names  # no time in name -> skipped, not invented
    assert len(cands) == 4  # the 4 files with a timestamp; VIDEOCAM-SYN-0002 has no deployment
    c = next(c for c in cands if c.item_id.startswith("VIDEOCAM-SYN-0001_20240815T000003"))
    lic = a.resolve_licence(c)
    assert lic.tier == "U"  # owner per device not resolved: never upgraded to B
    geo = a.resolve_geo(c)
    assert geo.geo_precision == "fixed_site"
    # August 2024 falls in the open-ended second deployment (begins 2024-07-01)
    assert (geo.lat, geo.lon, geo.depth_m) == (48.5002, -127.1002, 211.0)
    assert geo.geo_inferred is True and geo.geo_uncertainty_m is None


def test_no_deployment_means_no_geo(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, monkeypatch)
    c = next(c for c in a.discover() if "SYN-0002" in c.item_id)
    geo = a.resolve_geo(c)
    assert geo.geo_precision == "none" and geo.lat is None


def test_per_day_cap(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, monkeypatch, per_day=1)
    ids = [c.item_id for c in a.discover()]
    assert len([i for i in ids if "SYN-0001_20240815" in i]) == 1


def test_months_windows():
    from datetime import date

    w = list(mod.months(date(2024, 1, 15), date(2024, 3, 2)))
    assert w[0] == (date(2024, 1, 15), date(2024, 1, 31))
    assert w[-1] == (date(2024, 3, 1), date(2024, 3, 2))


def test_token_not_in_media_url(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, monkeypatch)
    c = next(a.discover())
    ref = a.resolve_media(c)
    assert "token" not in ref.url and "test-token" not in ref.url
    assert ref.extra["filename"] == c.item_id
