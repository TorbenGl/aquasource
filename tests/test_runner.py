import json
from pathlib import Path

from aquasource.adapters.base import Adapter, register
from aquasource.core.config import load_config
from aquasource.core.licence import make_licence
from aquasource.core.schema import Candidate, Geo
from aquasource.report import build_reports, write_dry_run_report
from aquasource.runner import run_source

ITEMS = [
    # item_id, licence, lat, lon, precision
    ("ok-1", "CC BY 4.0", 54.1, 7.2, "image"),
    ("ok-2", "CC0", -33.9, 151.3, "station"),
    ("zero", "CC BY 4.0", 0.0, 0.0, "image"),  # rejected by sanity check
    ("nogeo", "CC BY 4.0", None, None, "none"),  # dropped: require_geo
    ("nc", "CC BY-NC 4.0", 10.0, 10.0, "image"),  # excluded
    ("sa", "CC BY-SA 4.0", 56.9, 9.9, "fixed_site"),  # tier C, off by default
    ("unk", "", 20.0, -150.0, "image"),  # tier U, held
    ("region", "CC BY 4.0", 40.0, 3.0, "region"),  # below min precision
]

FETCHED: list[str] = []


@register
class FakeAdapter(Adapter):
    key = "fake_test_source"
    name = "Fake"

    def discover(self):
        for item_id, lic, lat, lon, prec in ITEMS:
            yield Candidate(self.key, item_id, "image", f"https://example.invalid/{item_id}.jpg", f"https://example.invalid/{item_id}", raw={"lic": lic, "lat": lat, "lon": lon, "prec": prec})

    def resolve_licence(self, cand):
        return make_licence(cand.raw["lic"], level="record", url=None, attribution="Fake et al.")

    def resolve_geo(self, cand):
        r = cand.raw
        if r["prec"] == "none":
            return Geo.none("lat/lon empty")
        return Geo(r["lat"], r["lon"], 5.0, r["prec"], "raw lat/lon", r["prec"] != "image")

    def fetch_media(self, cand, ref, dest: Path):
        FETCHED.append(cand.item_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"jpegbytes")
        return 9, "sha"


def _cfg(tmp_path, **kw):
    return load_config(None, data_root=tmp_path, **kw)


def test_dry_run_downloads_nothing(tmp_path):
    FETCHED.clear()
    cfg = _cfg(tmp_path)
    s = run_source(cfg, "fake_test_source", "dry-run")
    assert FETCHED == []
    assert s.candidates == len(ITEMS)
    assert s.selected == 2
    assert s.by_precision["none"] == 2  # nogeo + rejected (0,0)
    assert s.dropped["licence excluded (NC/ND/research-only)"] == 1
    assert s.bbox == [7.2, -33.9, 151.3, 54.1]
    failures = (tmp_path / "fake_test_source" / "metadata" / "failures.jsonl").read_text()
    assert "exactly (0, 0)" in failures
    md = write_dry_run_report(tmp_path / "_reports", [s.to_dict()])
    assert "fake_test_source" in md.read_text()


def test_download_is_idempotent_and_filters(tmp_path):
    FETCHED.clear()
    cfg = _cfg(tmp_path)
    s1 = run_source(cfg, "fake_test_source", "download")
    assert sorted(FETCHED) == ["ok-1", "ok-2"]
    assert s1.downloaded == 2
    s2 = run_source(cfg, "fake_test_source", "download")
    assert sorted(FETCHED) == ["ok-1", "ok-2"]  # nothing fetched again
    assert s2.already_done == 2 and s2.downloaded == 0
    rows = [json.loads(l) for l in (tmp_path / "fake_test_source" / "metadata" / "samples.jsonl").read_text().splitlines()]
    assert len(rows) == 2
    for r in rows:
        assert r["licence_tier"] in ("A", "B")
        assert r["attribution"]
        assert r["geo_precision"] != "none"
        for k in ("lat", "lon", "depth_m", "geo_precision", "geo_source", "geo_inferred"):
            assert k in r
        assert (tmp_path / r["local_path"]).exists()
    # failures.jsonl does not grow on re-run
    lines = (tmp_path / "fake_test_source" / "metadata" / "failures.jsonl").read_text().splitlines()
    assert len(lines) == len(set(lines)) == 1


def test_sharealike_and_relaxed_geo(tmp_path):
    FETCHED.clear()
    cfg = _cfg(tmp_path, include_sharealike=True, require_geo=False, min_geo_precision="region")
    s = run_source(cfg, "fake_test_source", "download")
    assert sorted(FETCHED) == ["nogeo", "ok-1", "ok-2", "region", "sa", "zero"]
    sa_rows = (tmp_path / "_sharealike" / "fake_test_source" / "metadata" / "samples.jsonl").read_text().splitlines()
    assert len(sa_rows) == 1 and json.loads(sa_rows[0])["licence_tier"] == "C"
    out = build_reports(tmp_path)
    gj = json.loads(out["geojson"].read_text())
    assert len(gj["features"]) == 4  # ok-1, ok-2, region, sa (no coords for nogeo / zero)
    assert "Geo report" in out["geo_report"].read_text()
    assert s.error is None


def test_budget(tmp_path):
    FETCHED.clear()
    cfg = _cfg(tmp_path)
    s = run_source(cfg, "fake_test_source", "download", budget=1)
    assert s.selected == 1 and len(FETCHED) == 1
