"""Offline tests for the gbif_marine_media adapter on the 3 real records in tests/fixtures/gbif_marine_media/.

No network: the GBIF page is served by a stub ``get_json``; the Http client raises on any other request.
"""

import json
from pathlib import Path

from aquasource.adapters import gbif_marine_media as gm
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "gbif_marine_media"
SAMPLE = json.loads((FIX / "search_sample.json").read_text())
BY_KEY = {str(r["key"]): r for r in SAMPLE["results"]}


class StubHttp(Http):
    def __init__(self, pages):
        super().__init__(dry_run=True)
        self.pages = pages
        self.calls = []

    def get_json(self, url, **kwargs):
        self.calls.append(kwargs.get("params", {}).get("offset"))
        return self.pages.get(kwargs.get("params", {}).get("offset"), {"results": [], "endOfRecords": True})

    def request(self, *a, **k):  # pragma: no cover
        raise AssertionError(f"unexpected request {a[:2]}")


def make_adapter(tmp_path, pages, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "gbif_marine_media").ensure()
    ctx = Context(cfg, StubHttp(pages), layout, options, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("gbif_marine_media")(ctx)


def candidates(tmp_path, pages=None, **options):
    pages = {0: SAMPLE} if pages is None else pages
    return list(make_adapter(tmp_path, pages, **options).discover())


def test_registered(tmp_path):
    assert get_adapter_class("gbif_marine_media").key == "gbif_marine_media"


def test_discover_keeps_only_image_media_with_geo_and_records_licence_level(tmp_path):
    cands = candidates(tmp_path)
    urls = {c.media_url for c in cands}
    # one candidate per media URL: 6454357462 has 3 CC BY images, 6148296146 one, 6406420337 one (NC)
    assert len(cands) == 5
    assert "https://www.artsobservasjoner.no/MediaLibrary/2026/1/0fb674b7-abfd-4360-8884-f3c1d41163aa_image.jpg" in urls
    assert all(c.media_type == "image" for c in cands)
    assert all(c.origin_url.startswith("https://www.gbif.org/occurrence/") for c in cands)


def test_licence_is_read_at_file_level_and_never_upgraded(tmp_path):
    cands = {c.extra["occurrence_key"]: c for c in candidates(tmp_path)}
    ad = make_adapter(tmp_path, {0: SAMPLE})
    cc_by = ad.resolve_licence(cands["6454357462"])
    assert cc_by.tier == "B" and cc_by.level == "file"
    assert cc_by.url == "http://creativecommons.org/licenses/by/4.0/"
    assert "GBIF occurrence 6454357462" in cc_by.attribution
    nc = [c for c in candidates(tmp_path) if c.extra["occurrence_key"] == "6406420337"][0]
    lic = ad.resolve_licence(nc)
    assert lic.tier == "X"  # media says CC BY-NC although the occurrence says CC0
    assert nc.extra["licence_conflict"] is True
    assert nc.extra["record_licence"] == "http://creativecommons.org/publicdomain/zero/1.0/legalcode"


def test_geo_from_occurrence_fields(tmp_path):
    ad = make_adapter(tmp_path, {0: SAMPLE})
    cand = [c for c in candidates(tmp_path) if c.extra["occurrence_key"] == "6454357462"][0]
    geo = ad.resolve_geo(cand)
    assert (geo.lat, geo.lon) == (59.607369, 5.452343)
    assert geo.geo_precision == "image" and geo.geo_inferred is False
    assert geo.geo_uncertainty_m == 5.0 and geo.depth_m == 2.0
    assert geo.geo_source == gm.GEO_SOURCE


def test_noisy_terrestrial_bird_is_kept_and_marked(tmp_path):
    bird = [c for c in candidates(tmp_path) if c.extra["occurrence_key"] == "6148296146"][0]
    assert bird.extra["maybe_not_underwater"] is True
    assert bird.extra["scientific_name"] == "Cygnus cygnus (Linnaeus, 1758)"
    sea_squirt = [c for c in candidates(tmp_path) if c.extra["occurrence_key"] == "6454357462"][0]
    assert sea_squirt.extra["maybe_not_underwater"] is True  # habitat / waterBody are not stated in this record


def test_invalid_coordinates_give_geo_none(tmp_path):
    ad = make_adapter(tmp_path, {0: SAMPLE})
    cand = [c for c in candidates(tmp_path) if c.extra["occurrence_key"] == "6454357462"][0]
    cand.raw["occurrence"] = dict(cand.raw["occurrence"], decimalLatitude=0, decimalLongitude=0)
    geo = ad.resolve_geo(cand)
    assert geo.geo_precision == "none" and geo.lat is None


def test_paging_stops_at_end_and_duplicates_are_skipped(tmp_path):
    pages = {0: dict(SAMPLE, endOfRecords=False), 300: SAMPLE}  # same records twice: media URLs must not be yielded twice
    ad = make_adapter(tmp_path, pages, max_offset=600)
    cands = list(ad.discover())
    assert len(cands) == 5
    assert ad.http.calls == [0, 300]
