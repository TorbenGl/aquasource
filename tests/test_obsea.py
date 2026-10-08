"""Offline tests for the OBSEA adapter, run on the real records in tests/fixtures/obsea/.

No test touches the network. The Zenodo record (one monthly zip, 2013-01) and its index.csv (first 10 rows) are
copied into metadata/raw/ where the adapter caches them. The Http client refuses every request. Expected values come
from tests/fixtures/obsea/SOURCE.md and research/obsea.md.
"""

import io
import json
import shutil
import zipfile
from pathlib import Path

from aquasource.adapters.base import Context, get_adapter_class
from aquasource.adapters.obsea import RangeReader, iso_utc, read_index_csv
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog
from aquasource.core.schema import Candidate

FIX = Path(__file__).parent / "fixtures" / "obsea"
RECORD_ID = "22802714"
ZIP = "OBSEA_seabed_station_pictures_L0a_20130101_20130201.zip"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "obsea").ensure()
    raw = layout.raw
    (raw / "obsea").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIX / "zenodo_search_p1.json", raw / "zenodo_search_p1.json")
    shutil.copyfile(FIX / "zenodo_22802714.json", raw / f"zenodo_{RECORD_ID}.json")
    shutil.copyfile(FIX / "index_2013_01_first10.csv", raw / "obsea" / f"{ZIP}.index.csv")
    ctx = Context(cfg, NoNet(dry_run=True), layout, options, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("obsea")(ctx)


def candidates(tmp_path, **options):
    return list(make_adapter(tmp_path, **options).discover())


def test_registered(tmp_path):
    a = make_adapter(tmp_path)
    assert a.key == "obsea"
    assert a.media_types == ("image",)


def test_discover_yields_index_rows(tmp_path):
    cands = candidates(tmp_path)
    assert len(cands) == 10
    first = cands[0]
    assert isinstance(first, Candidate)
    assert first.media_url == "https://files.obsea.es/pictures/Sony_SNC-RZ25N/2013/01/09/20130109-181742-Sony_SNC-RZ25N.jpeg"
    assert first.timestamp == "2013-01-09T18:17:42Z"
    assert first.ext == "jpg"
    assert first.extra["sensor_id"] == "Sony_SNC-RZ25N"
    assert first.extra["field_of_view"] == "OBSEA_concrete_biotop"
    assert first.extra["zenodo_record"] == RECORD_ID
    assert first.extra["zip"] == ZIP
    assert first.extra["zip_member"] == "2013/01/09/20130109-181742-Sony_SNC-RZ25N.jpeg"
    assert len({c.sample_id for c in cands}) == 10


def test_licence_is_cc_by_record_level(tmp_path):
    a = make_adapter(tmp_path)
    cand = next(iter(a.discover()))
    lic = a.resolve_licence(cand)
    assert lic.tier == "B"
    assert lic.name == "CC-BY-4.0"
    assert lic.level == "record"
    assert lic.url == f"https://zenodo.org/records/{RECORD_ID}"
    assert "10.5281/zenodo.22802714" in lic.attribution


def test_geo_is_fixed_site_from_publication(tmp_path):
    a = make_adapter(tmp_path)
    cand = next(iter(a.discover()))
    geo = a.resolve_geo(cand)
    assert geo.geo_precision == "fixed_site"
    assert geo.lat == 41.18212
    assert geo.lon == 1.75257
    assert geo.depth_m == 20.0
    assert geo.geo_inferred is True
    assert geo.geo_uncertainty_m is None
    assert "zenodo.22802714" in geo.geo_source or "22802714" in geo.geo_source


def test_per_day_and_from_to(tmp_path):
    # all 10 rows are on 2013-01-09
    assert len(candidates(tmp_path, per_day=3)) == 3
    assert len(candidates(tmp_path, to="2013-01-08")) == 0
    assert len(candidates(tmp_path, **{"from": "2013-01-09", "to": "2013-01-09"})) == 10
    assert len(candidates(tmp_path, years="2014")) == 0
    assert len(candidates(tmp_path, sensors="Sony_SNC-RZ25N")) == 10
    assert len(candidates(tmp_path, sensors="nope")) == 0


def test_iso_utc():
    assert iso_utc("2013-01-09 18:17:42+00:00") == "2013-01-09T18:17:42Z"
    assert iso_utc("2013-01-09T18:17:42Z") == "2013-01-09T18:17:42Z"
    assert iso_utc("not a time") is None


def test_index_read_from_zip_by_range(tmp_path):
    """The zip path used for uncached months: read index.csv through a Range reader (fake HTTP here)."""
    index = (FIX / "index_2013_01_first10.csv").read_bytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("2013/01/09/", b"")
        zf.writestr("index.csv", index)
        zf.writestr("2013/01/09/20130109-181742-Sony_SNC-RZ25N.jpeg", b"\xff\xd8\xff not really a jpeg")
    data = buf.getvalue()

    class FakeHttp:
        calls = 0

        def get_range(self, url, start, end, kind="metadata"):
            FakeHttp.calls += 1
            return data[start : end + 1]

    reader = RangeReader(FakeHttp(), "https://zenodo.example/zip", len(data))
    assert read_index_csv(reader) == index.decode("utf-8")
    assert FakeHttp.calls >= 1
