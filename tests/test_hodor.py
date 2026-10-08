"""Offline tests for the HODOR adapter, run on the real rows in tests/fixtures/hodor/.

No test touches the network: the PANGAEA data table is copied into metadata/raw/ (as the adapter caches it)
and the Http client refuses any request. Expected values come from tests/fixtures/hodor/SOURCE.md and
research/hodor.md.
"""

import shutil
from datetime import datetime, timezone
from pathlib import Path

from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "hodor"
TABLE = FIX / "980001_camera_rows.tab"
DL = "https://download.pangaea.de/dataset/980001/files/"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "hodor").ensure()
    shutil.copyfile(TABLE, layout.raw / "pangaea_980001.tab")
    ctx = Context(cfg, NoNet(dry_run=True), layout, options, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("hodor")(ctx)


def test_registered_and_licence_tier_b(tmp_path):
    a = make_adapter(tmp_path)
    cand = next(iter(a.discover()))
    lic = a.resolve_licence(cand)
    assert lic.tier == "B"
    assert lic.level == "record"
    assert lic.url == "https://creativecommons.org/licenses/by/4.0/"
    assert lic.name == "Creative Commons Attribution 4.0 International (CC-BY-4.0)"


def test_geo_is_observatory_fixed_site(tmp_path):
    a = make_adapter(tmp_path)
    cand = next(iter(a.discover()))
    geo = a.resolve_geo(cand)
    assert (geo.lat, geo.lon) == (54.340625, 10.174105)
    assert geo.geo_precision == "fixed_site"
    assert geo.geo_inferred is True
    assert geo.depth_m is None
    assert "Coverage" in geo.geo_source


def test_default_one_camera_per_sequence(tmp_path):
    a = make_adapter(tmp_path)
    cands = list(a.discover())
    assert [c.item_id for c in cands] == [f"PANGAEA.980001/{s}/cam1" for s in (0, 1, 2)]
    assert cands[0].media_url == DL + "cam1_0000.mp4"
    assert cands[0].media_type == "video"
    assert cands[0].ext == "mp4"
    assert cands[0].extra["stereo_partner_url"] == DL + "cam2_0000.mp4"
    assert cands[0].extra["timestamps_url"] == DL + "cam1_0000.txt"
    assert cands[0].extra["duration_s"] == 74.0


def test_timestamps_are_utc(tmp_path):
    a = make_adapter(tmp_path)
    cand = next(iter(a.discover()))
    unix = 1629609208  # sequenceStartUnix of SeqID 0 in the table
    assert cand.timestamp == "2021-08-22T05:13:28.033Z"
    assert datetime.fromtimestamp(unix, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") == cand.timestamp[:19]


def test_both_cameras_and_date_filters(tmp_path):
    assert len(list(make_adapter(tmp_path, cams="cam1,cam2").discover())) == 6
    assert len(list(make_adapter(tmp_path, cams=["cam2"]).discover())) == 3
    assert list(make_adapter(tmp_path, to="2021-08-21").discover()) == []
    assert len(list(make_adapter(tmp_path, per_day=1).discover())) == 1  # all rows share one day
    assert len(list(make_adapter(tmp_path, **{"from": "2021-08-22"}).discover())) == 3


def test_estimate_and_bad_camera_option(tmp_path):
    a = make_adapter(tmp_path, cams="cam1,cam2")
    assert a.estimate() == {"sequences": 3, "videos": 6}
    try:
        make_adapter(tmp_path, cams="cam9")
    except ValueError as exc:
        assert "cam9" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for unknown camera")
