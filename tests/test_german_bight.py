from pathlib import Path

from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "_core" / "pangaea_907386.tab"


def make_adapter(tmp_path):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "german_bight").ensure()
    # Pre-seed the metadata cache with the real PANGAEA export so no network is needed.
    (layout.raw / "pangaea_907386.tab").write_text(FIX.read_text(encoding="utf-8"), encoding="utf-8")
    ctx = Context(cfg, Http(dry_run=True), layout, {"dataset_ids": ["907386"]}, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("german_bight")(ctx)


def test_discover_and_resolve(tmp_path):
    a = make_adapter(tmp_path)
    cands = list(a.discover())
    assert len(cands) > 50
    c = cands[0]
    assert c.media_type == "video"
    assert c.media_url.endswith(".avi")
    assert c.origin_url == "https://doi.pangaea.de/10.1594/PANGAEA.907386"
    lic = a.resolve_licence(c)
    assert lic.tier == "B" and lic.level == "record"
    assert "Papenmeier" in lic.attribution
    geo = a.resolve_geo(c)
    assert geo.geo_precision == "station"
    assert geo.geo_inferred is True
    assert abs(geo.lat - 54.86993) < 1e-6 and abs(geo.lon - 6.7144) < 1e-6
    assert geo.depth_m == 45.0
    assert "Latitude/Longitude" in geo.geo_source
    assert len({x.item_id for x in cands}) == len(cands)
