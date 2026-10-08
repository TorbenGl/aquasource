"""Offline tests for the wikimedia_commons adapter on the 3 real file pages in tests/fixtures/wikimedia_commons/.

No network: the category page is served by a stub ``get_text`` (the cache layer calls it); the Http client raises on any
other request. Fixture: real api.php answer (generator=categorymembers, prop=coordinates|imageinfo) trimmed to 3 pages.
"""

import json
from pathlib import Path

from aquasource.adapters import wikimedia_commons as wc
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog

FIX = Path(__file__).parent / "fixtures" / "wikimedia_commons"
SAMPLE = json.loads((FIX / "api_categorymembers_sample.json").read_text())
BY_TITLE = {p["title"]: p for p in SAMPLE["query"]["pages"].values()}

CLOWNFISH = "File:Clownfish - Marsa Alam, Egypt - August 8, 2011.jpg"  # CC BY 4.0, coordinate
BAD_GOISERN = "File:4822 Bad Goisern am Hallstättersee, Grund Hallstätter See 01 2022-07-25.jpg"  # CC0, coordinate
BLUE_EYE = "File:Blue Eye, Theth.webm"  # CC BY-SA 4.0, video, coordinate


class StubHttp(Http):
    """Serves the fixture for the first page of each category; later pages are empty."""

    def __init__(self):
        super().__init__(dry_run=True)
        self.calls = []

    def get_text(self, url, **kwargs):
        params = kwargs.get("params", {})
        self.calls.append(params.get("gcmtitle"))
        if "gcmcontinue" in params:
            return json.dumps({"batchcomplete": ""})
        return json.dumps(SAMPLE)

    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "wikimedia_commons").ensure()
    ctx = Context(cfg, StubHttp(), layout, options, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("wikimedia_commons")(ctx)


def candidates(tmp_path, **options):
    return list(make_adapter(tmp_path, **options).discover())


def by_title(cands):
    return {c.item_id: c for c in cands}


def test_registered(tmp_path):
    assert get_adapter_class("wikimedia_commons").key == "wikimedia_commons"


def test_discover_yields_geotagged_files_of_all_three_tiers_once(tmp_path):
    cands = candidates(tmp_path, categories="Underwater photographs,Underwater videos")
    # both categories return the same 3 fixture pages: the title dedup keeps one candidate per file
    assert sorted(c.item_id for c in cands) == sorted([CLOWNFISH, BAD_GOISERN, BLUE_EYE])
    types = {c.item_id: c.media_type for c in cands}
    assert types[BLUE_EYE] == "video" and types[CLOWNFISH] == "image"
    assert all(c.media_url.startswith("https://upload.wikimedia.org/") for c in cands)


def test_licence_is_read_per_file(tmp_path):
    ad = make_adapter(tmp_path)
    cands = by_title(list(ad.discover()))
    clown = ad.resolve_licence(cands[CLOWNFISH])
    assert clown.tier == "B" and clown.level == "file"
    assert clown.url == "https://creativecommons.org/licenses/by/4.0"
    assert "Clownfish" in clown.attribution and "Wikimedia Commons" in clown.attribution
    cc0 = ad.resolve_licence(cands[BAD_GOISERN])
    assert cc0.tier == "A" and cc0.name == "CC0"
    sa = ad.resolve_licence(cands[BLUE_EYE])
    assert sa.tier == "C"  # share-alike: kept by discover, not selected by default (runner tier rules)


def test_geo_is_geodata_coordinate_at_image_precision(tmp_path):
    ad = make_adapter(tmp_path)
    clown = by_title(list(ad.discover()))[CLOWNFISH]
    geo = ad.resolve_geo(clown)
    assert geo.lat == 24.916117
    assert geo.lon == 34.972583
    assert geo.geo_precision == "image" and geo.geo_inferred is False
    assert geo.depth_m is None and geo.geo_uncertainty_m is None
    assert geo.geo_source == wc.GEO_SOURCE


def test_maybe_not_underwater_marks_lake_photo_not_fish(tmp_path):
    cands = by_title(candidates(tmp_path))
    assert cands[BAD_GOISERN].extra["maybe_not_underwater"] is True  # lake photo, no marine keyword
    assert cands[CLOWNFISH].extra["maybe_not_underwater"] is False  # "Clownfish" in the title


def test_tiers_option_drops_share_alike(tmp_path):
    ad = make_adapter(tmp_path, tiers="A,B")
    cands = list(ad.discover())
    assert BLUE_EYE not in {c.item_id for c in cands}
    assert ad.skipped.get("tier C not in tiers option") == 1


def test_max_bytes_skips_large_originals(tmp_path):
    ad = make_adapter(tmp_path, max_bytes=1000)
    assert list(ad.discover()) == []
    assert ad.skipped.get("larger than max_bytes", 0) >= 1


def test_licence_contradiction_is_held_as_unknown():
    ext = {"LicenseShortName": {"value": "CC BY 4.0"}, "License": {"value": "cc-by-sa-4.0"}}
    tier, name, url, conflict = wc.file_licence(ext)
    assert tier == "U" and conflict is True and name == "CC BY 4.0"


def test_non_commercial_and_unknown_licences_are_not_selectable():
    assert wc.file_licence({"LicenseShortName": {"value": "CC BY-NC 4.0"}})[0] == "X"
    assert wc.file_licence({"LicenseShortName": {"value": "Copyrighted free use"}})[0] == "U"
    assert wc.file_licence({})[0] == "U"


def test_coordinates_absent_are_skipped_unless_geo_only_false(tmp_path):
    page = json.loads(json.dumps(BY_TITLE[CLOWNFISH]))
    page.pop("coordinates")
    ad = make_adapter(tmp_path)
    assert ad._candidate("Underwater photographs", page, set(), {"A", "B", "C"}, 10**9, True) is None
    cand = make_adapter(tmp_path, geo_only=False)._candidate(
        "Underwater photographs", page, set(), {"A", "B", "C"}, 10**9, False
    )
    assert cand is not None and cand.raw["geo"] is None
    assert make_adapter(tmp_path).resolve_geo(cand).geo_precision == "none"
