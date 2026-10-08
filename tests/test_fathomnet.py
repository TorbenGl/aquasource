"""Offline tests for the fathomnet adapter, run on the real fixtures in tests/fixtures/fathomnet/.

No test touches the network: the paged ``GET /geoimages`` answer, the image count and the CC-BY query answer are
written into metadata/raw/ (like the other adapter tests) and the Http client raises on any request unless a test
replaces ``get_json`` / ``download``. The 6 light records of api_geoimages_query.json and the 5 full records of
api_images_query.json are real API answers (2026-10-06); the page wrapper (``content``, ``totalItems``) and the image
count of 6 are synthetic. Rows built by hand for ordering / cap tests are marked "synthetic".
"""

import json
from pathlib import Path

import pytest

from aquasource.adapters import fathomnet as fn
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog
from aquasource.runner import run_source

FIX = Path(__file__).parent / "fixtures" / "fathomnet"
LIGHT = json.loads((FIX / "api_geoimages_query.json").read_text())
FULL = json.loads((FIX / "api_images_query.json").read_text())
COUNTS = [json.loads(line) for line in (FIX / "api_counts.ndjson").read_text().splitlines()]

UUID_STATION_1 = "dcbfc174-fcd9-428d-b0a6-d2d4e9bcfba4"  # CC0, 761901231_Cam5, no timestamp
UUID_AVI = "b30b9012-5732-4137-8597-9ff0f5bf059b"
UUID_TS_A = "61a0f397-c6c7-4cf0-843a-a65740db1123"  # CC0, SC2-camera2, timestamp set
UUID_TS_B = "24832f37-b416-4fba-9825-19996198d58d"  # same video, 0.2 s later
UUID_POSCO = "ead1a05d-9b75-491d-b902-57da6bbeaa2c"  # CC-BY-4.0, Korea, depth null
UUID_POSCO_2 = "e2dfa963-d7aa-42e7-a42f-288753edbc38"
UUID_NCND = "59ba03f6-ceeb-4ba6-be6d-ed149921c826"  # CC-BY-NC-ND-4.0 (SOI ROV)
UUID_CROP = "36423e84-a910-4a0f-b616-e643c9255b26"  # CC-BY-4.0 plankton crop, no coordinates

CC0_URL = "https://creativecommons.org/publicdomain/zero/1.0/legalcode"
CCBY_URL = "https://creativecommons.org/licenses/by/4.0/legalcode"
GEO_SRC = fn.GEO_SOURCE


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def page_json(records, total=None):
    return json.dumps({"content": records, "pageNumber": 0, "pageSize": 3000, "totalItems": total or len(records), "totalPages": 1})


def make_adapter(tmp_path, page_data=None, *, ccby=(), count=None, dry_run=True, http=None, **options):
    """``page_data``: {page number: records}; ``ccby``: records of the CC-BY POST answer."""
    pages = {0: LIGHT} if page_data is None else page_data
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "fathomnet").ensure()
    (layout.raw / "geoimages").mkdir(exist_ok=True)
    n = count if count is not None else 3000 * len(pages)
    (layout.raw / "images_count.json").write_text(json.dumps({"count": n, "objectType": "ImageEntity"}))
    for p, recs in pages.items():
        (layout.raw / "geoimages" / f"size3000_page{p:04d}.json").write_text(page_json(recs))
    (layout.raw / "geoimages_query_ccby.json").write_text(json.dumps(list(ccby)))
    ctx = Context(cfg, http or NoNet(dry_run=dry_run), layout, options, dry_run, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("fathomnet")(ctx)


def by_id(cands):
    return {c.item_id: c for c in cands}


def synthetic(uuid, folder, t, station, lic="CC0-1.0", depth=50.0):
    """A hand-made light record of a NOAA frame (synthetic)."""
    hh, rest = divmod(int(t), 3600)
    mm, ss = divmod(rest, 60)
    name = f"{folder}.mp4.{hh:02d}.{mm:02d}.{ss:02d}.{int(round((t % 1) * 1e6)):06d}.jpg"
    return {
        "uuid": uuid, "url": f"{fn.GFISHER_PREFIX}{folder}/{name}", "latitude": station[0], "longitude": station[1],
        "depthMeters": depth, "timestamp": None, "imageLicense": lic, "valid": True,
    }  # fmt: skip


# --------------------------------------------------------------------------------------------- discover
def test_registered_and_metadata():
    cls = get_adapter_class("fathomnet")
    assert cls.key == "fathomnet" and cls.media_types == ("image",) and cls.env_vars == ()
    assert "10.1038/s41598-022-19939-2" in cls.citation and cls.manual_steps


def test_discover_real_fixture_ids_urls_and_filtering(tmp_path):
    a = make_adapter(tmp_path, ccby=LIGHT[4:], min_spacing_s=0)
    cands = list(a.discover())
    # the 6 fixture records are all usable; the two CC-BY ones come from the page AND the POST answer: yielded once
    assert sorted(c.item_id for c in cands) == sorted([UUID_STATION_1, UUID_AVI, UUID_TS_A, UUID_TS_B, UUID_POSCO, UUID_POSCO_2])
    c = by_id(cands)[UUID_STATION_1]
    assert c.source == "fathomnet" and c.media_type == "image" and c.ext == "jpg"
    assert c.media_url == (
        "https://storage.googleapis.com/nmfs_odp_hq/nodd_tools/datasets/gfisher/761901231_Cam5/761901231_Cam5.mp4.00.00.02.400000.jpg"
    )
    assert c.origin_url == f"https://database.fathomnet.org/api/images/{UUID_STATION_1}"
    assert c.timestamp is None and c.extra["video"] == "761901231_Cam5" and c.extra["frame_offset_s"] == pytest.approx(2.4)
    assert by_id(cands)[UUID_TS_A].timestamp == "2021-03-12T15:17:04.200Z"
    # no personal data is kept
    assert all("contributorsEmail" not in json.dumps(x.raw) for x in cands)
    assert by_id(cands)[UUID_POSCO].media_url.endswith("FN251128095328/FN251128095328_DSC_4383.JPG")
    assert by_id(cands)[UUID_POSCO].ext == "jpg"


def test_item_ids_are_stable_across_runs(tmp_path):
    ids1 = [c.item_id for c in make_adapter(tmp_path / "a", min_spacing_s=0).discover()]
    ids2 = [c.item_id for c in make_adapter(tmp_path / "b", min_spacing_s=0).discover()]
    assert ids1 == ids2


def test_nc_nd_and_unknown_licences_and_invalid_records_are_not_yielded(tmp_path):
    ncnd = {**FULL[2]}  # real SOI ROV record, CC-BY-NC-ND-4.0
    assert ncnd["uuid"] == UUID_NCND and ncnd["imageLicense"] == "CC-BY-NC-ND-4.0"
    junk = [
        {**LIGHT[0], "uuid": "u-nc", "imageLicense": "CC-BY-NC-4.0"},
        {**LIGHT[0], "uuid": "u-null", "imageLicense": None},
        {**LIGHT[0], "uuid": "u-jpl", "imageLicense": "JPL-image"},
        {**LIGHT[0], "uuid": "u-invalid", "valid": False},
        {**LIGHT[0], "uuid": "u-nd", "imageLicense": "CC-BY-ND-4.0"},
        {**LIGHT[0], "uuid": "u-sa", "imageLicense": "CC-BY-SA-4.0"},
    ]
    a = make_adapter(tmp_path, {0: [ncnd, *junk, LIGHT[0]]})
    assert [c.item_id for c in a.discover()] == [UUID_STATION_1]
    assert a.skipped["licence tier X"] == 3  # NC-ND, NC, ND
    assert a.skipped["licence tier U"] == 2 and a.skipped["not valid"] == 1 and a.skipped["licence tier C"] == 1
    # tier C only when asked for
    c = make_adapter(tmp_path / "c", {0: junk}, tiers="A,B,C")
    assert [x.item_id for x in c.discover()] == ["u-sa"]


def test_crop_without_coordinates_is_skipped_by_default_and_has_geo_none_when_kept(tmp_path):
    crop = FULL[3]
    assert crop["uuid"] == UUID_CROP and crop["latitude"] is None
    a = make_adapter(tmp_path, {0: [crop, LIGHT[0]]})
    assert [c.item_id for c in a.discover()] == [UUID_STATION_1] and a.skipped["no coordinates"] == 1
    b = make_adapter(tmp_path / "b", {0: [crop, LIGHT[0]]}, geo_only=False)
    cands = by_id(b.discover())
    assert set(cands) == {UUID_CROP, UUID_STATION_1}
    g = b.resolve_geo(cands[UUID_CROP])
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == (None, None, None, "none", False, None)
    assert g.geo_source == "fathomnet API latitude/longitude (null)"
    lic = b.resolve_licence(cands[UUID_CROP])  # still tier B; the runner drops it for the missing position
    assert lic.tier == "B" and lic.name == "CC-BY-4.0"


# --------------------------------------------------------------------------------------------- licence
def test_licence_cc0_noaa_frame(tmp_path):
    a = make_adapter(tmp_path)
    c = by_id(a.discover())[UUID_STATION_1]
    lic = a.resolve_licence(c)
    assert (lic.name, lic.tier, lic.level, lic.url) == ("CC0-1.0", "A", "record", CC0_URL)
    assert lic.attribution.startswith(
        "Image: NOAA NMFS Southeast Fisheries Science Center (Mississippi Laboratories), SEAMAP reef fish video survey, via FathomNet; CC0 1.0."
    )
    assert "Katija, K. et al. (2022) FathomNet" in lic.attribution and "10.1038/s41598-022-19939-2" in lic.attribution
    assert UUID_STATION_1 in lic.attribution and c.media_url in lic.attribution


def test_licence_cc_by_posco_image(tmp_path):
    a = make_adapter(tmp_path, ccby=LIGHT[4:])
    c = by_id(a.discover())[UUID_POSCO]
    lic = a.resolve_licence(c)
    assert (lic.name, lic.tier, lic.level, lic.url) == ("CC-BY-4.0", "B", "record", CCBY_URL)
    assert "POSCO" in lic.attribution and "Katija, K." in lic.attribution and UUID_POSCO in lic.attribution


@pytest.mark.parametrize(
    "spdx,tier",
    [("CC0-1.0", "A"), ("NIST-PD", "A"), ("CC-BY-4.0", "B"), ("OGL-UK-3.0", "B"), ("DL-DE-BY-2.0", "B"), ("CC-BY-SA-4.0", "C"),
     ("CC-BY-NC-4.0", "X"), ("CC-BY-NC-ND-4.0", "X"), ("CC-BY-NC-SA-4.0", "X"), ("CC-BY-ND-4.0", "X"),
     ("JPL-image", "U"), (None, "U"), ("", "U")],
)  # fmt: skip
def test_licence_tier_table(spdx, tier):
    assert fn.licence_tier(spdx) == tier


def test_resolve_licence_never_upgrades_excluded_or_unknown(tmp_path):
    a = make_adapter(tmp_path)
    for spdx, tier in (("CC-BY-NC-ND-4.0", "X"), ("CC-BY-NC-4.0", "X"), ("JPL-image", "U"), (None, "U")):
        cand = fn.Candidate("fathomnet", "x", "image", "https://example.invalid/x.jpg", "o", raw={"imageLicense": spdx, "valid": True})
        assert a.resolve_licence(cand).tier == tier
    withdrawn = fn.Candidate("fathomnet", "x", "image", "https://example.invalid/x.jpg", "o", raw={"imageLicense": "CC0-1.0", "valid": False})
    assert a.resolve_licence(withdrawn).tier == "U"


# --------------------------------------------------------------------------------------------- geo
def test_geo_noaa_station_frame_matches_the_research_example(tmp_path):
    a = make_adapter(tmp_path)
    g = a.resolve_geo(by_id(a.discover())[UUID_STATION_1])
    assert (g.lat, g.lon, g.depth_m) == (29.4648, -87.6247, 63.7)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 200)
    assert g.geo_source == GEO_SRC and "latitude, longitude, depthMeters" in g.geo_source


def test_geo_frames_of_one_video_share_the_station_coordinate(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0)
    c = by_id(a.discover())
    ga, gb = a.resolve_geo(c[UUID_TS_A]), a.resolve_geo(c[UUID_TS_B])
    assert (ga.lat, ga.lon, ga.depth_m) == (gb.lat, gb.lon, gb.depth_m) == (28.6365, -89.5522, 79.0)
    assert c[UUID_TS_A].extra["video"] == c[UUID_TS_B].extra["video"] == "SC2-camera2_03-12-21_15-09-59.000"
    assert (c[UUID_TS_B].extra["frame_offset_s"] - c[UUID_TS_A].extra["frame_offset_s"]) == pytest.approx(0.2)
    g = a.resolve_geo(c[UUID_AVI])
    assert (g.lat, g.lon, g.depth_m) == (28.081, -92.0223, 87.4)


def test_geo_posco_cc_by_has_null_depth_and_larger_uncertainty(tmp_path):
    a = make_adapter(tmp_path, ccby=LIGHT[4:])
    g = a.resolve_geo(by_id(a.discover())[UUID_POSCO])
    assert (g.lat, g.lon, g.depth_m) == (37.469, 130.828, None)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 2000)
    assert g.geo_source == fn.GEO_SOURCE_UPLOAD


@pytest.mark.parametrize("lat,lon", [(None, 10.0), (10.0, None), (0.0, 0.0), (91.0, 10.0), (10.0, 181.0)])
def test_geo_unusable_coordinates_give_none_and_keep_depth(tmp_path, lat, lon):
    a = make_adapter(tmp_path)
    rec = {**LIGHT[0], "latitude": lat, "longitude": lon}
    cand = a._candidate(rec, "v", None)
    g = a.resolve_geo(cand)
    assert (g.lat, g.lon, g.geo_precision, g.geo_inferred) == (None, None, "none", False) and g.depth_m == 63.7


# --------------------------------------------------------------------------------------------- order and caps
def test_spread_order_covers_stations_before_repeating_one(tmp_path):
    stations = [(25.0, -90.0), (26.0, -91.0), (27.0, -92.0)]  # synthetic
    recs = []
    for i, st in enumerate(stations):
        for v in range(2):
            for f in range(30):
                recs.append(synthetic(f"s{i}v{v}f{f:02d}", f"vid{i}{v}", 20.0 * f, st))
    a = make_adapter(tmp_path, {0: recs}, frames_per_video=0, min_spacing_s=0)
    first6 = [c for c in a.discover()][:6]
    assert len({(c.raw["latitude"], c.raw["longitude"]) for c in first6[:3]}) == 3  # first round: three stations
    assert len({c.extra["video"] for c in first6}) == 6  # second round: other video of each station
    assert len({c.extra["video"] for c in first6[:3]}) == 3


def test_frames_per_video_and_spacing_caps(tmp_path):
    recs = [synthetic(f"a{i:02d}", "vidA", i * 0.2, (25.0, -90.0)) for i in range(100)]  # 5 fps for 20 s (synthetic)
    default = list(make_adapter(tmp_path / "d", {0: recs}).discover())
    offs = sorted(c.extra["frame_offset_s"] for c in default)
    assert len(offs) == 2 and offs[1] - offs[0] >= 10  # 20 s of video, 10 s apart
    every = list(make_adapter(tmp_path / "e", {0: recs}, min_spacing_s=0).discover())
    assert len(every) == fn.DEFAULT_FRAMES_PER_VIDEO
    allf = list(make_adapter(tmp_path / "f", {0: recs}, min_spacing_s=0, frames_per_video=0).discover())
    assert len(allf) == 100
    cap = list(make_adapter(tmp_path / "g", {0: recs}, min_spacing_s=0, frames_per_video=0, max_per_station=7).discover())
    assert len(cap) == 7


def test_pages_are_visited_in_a_seeded_order_and_pages_option_limits_them(tmp_path):
    pages = {p: [synthetic(f"p{p}-{i}", f"vid{p}{i}", 0.0, (25.0 + p, -90.0)) for i in range(2)] for p in range(4)}  # synthetic
    a = make_adapter(tmp_path, pages, count=4 * 3000 - 5, pages=1)
    first = [c.item_id for c in a.discover()]
    assert len(first) == 2 and first[0][:2] == first[1][:2]  # one page only
    assert fn.page_order(4, 0) == fn.page_order(4, 0) and sorted(fn.page_order(4, 3)) == [0, 1, 2, 3]
    assert fn.page_order(161, 0) != fn.page_order(161, 1)
    assert f"p{fn.page_order(4, 0)[0]}-" in first[0]
    everything = [c.item_id for c in make_adapter(tmp_path / "all", pages, count=4 * 3000 - 5).discover()]
    assert len(everything) == 8
    table = [c.item_id for c in make_adapter(tmp_path / "t", pages, order="table", count=4 * 3000 - 5).discover()]
    assert [i[:2] for i in table[::2]] == ["p0", "p1", "p2", "p3"]


def test_empty_page_is_skipped_not_fatal(tmp_path):
    a = make_adapter(tmp_path, {0: [], 1: [LIGHT[0]]}, count=4000)
    assert [c.item_id for c in a.discover()] == [UUID_STATION_1]


def test_frame_offset_and_video_helpers():
    u = LIGHT[1]["url"]
    assert fn.video_of(u) == "SC2-camera3_03-14-21_19-57-25.000"
    assert fn.frame_offset_s(u) == pytest.approx(18 * 60 + 10)
    assert fn.frame_offset_s(LIGHT[4]["url"]) is None
    assert fn.light_record({"uuid": "x", "contributorsEmail": "a@b", "boundingBoxes": []}) == {"uuid": "x"}


def test_check_ready_flags_bad_options(tmp_path):
    assert make_adapter(tmp_path / "ok").check_ready() == []
    bad = make_adapter(tmp_path / "bad", order="random", tiers="A,Q", frames_per_video="many").check_ready()
    assert len(bad) == 3


# --------------------------------------------------------------------------------------------- estimate
def test_estimate_reports_provider_totals(tmp_path):
    a = make_adapter(tmp_path, count=481126)
    raw = a.ctx.layout.raw
    for name, lines in (("cc0_images", COUNTS[1]), ("ccby_images", COUNTS[2]), ("ccby_georeferenced", COUNTS[6])):
        (raw / f"count_{name}.json").write_text(json.dumps(lines))
    est = a.estimate()
    assert (est["images_total"], est["cc0_images"], est["ccby_images"], est["ccby_georeferenced"]) == (481126, 231631, 7948, 16)
    assert est["pages"] == 161 and est["cc0_gb_estimate"] == 116


# --------------------------------------------------------------------------------------------- runner
def test_runner_dry_run_end_to_end(tmp_path):
    a = make_adapter(tmp_path, {0: [*LIGHT, FULL[2], FULL[3]]}, ccby=LIGHT[4:], count=6)
    raw = a.ctx.layout.raw
    for name, lines in (("cc0_images", COUNTS[1]), ("ccby_images", COUNTS[2]), ("ccby_georeferenced", COUNTS[6])):
        (raw / f"count_{name}.json").write_text(json.dumps(lines))
    cfg = load_config(None, data_root=tmp_path)
    s = run_source(cfg, "fathomnet", "dry-run", options={"min_spacing_s": 0})
    assert s.error is None and s.candidates == 6 and s.selected == 6
    assert dict(s.selected_by_tier) == {"A": 4, "B": 2} and dict(s.selected_by_precision) == {"station": 6}
    assert dict(s.media_types) == {"image": 6}
    assert s.estimate["cc0_images"] == 231631


# --------------------------------------------------------------------------------------------- media
class FakeHttp(NoNet):
    def __init__(self, record, payload):
        super().__init__(dry_run=False)
        self.record, self.payload, self.urls = record, payload, []

    def get_json(self, url, **kw):
        self.urls.append(url)
        return self.record

    def download(self, url, dest, **kw):
        import hashlib

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.payload)
        return len(self.payload), hashlib.sha256(self.payload).hexdigest()


def live(tmp_path, record, payload, **options):
    http = FakeHttp(record, payload)
    a = make_adapter(tmp_path, {0: [FULL[0]]}, dry_run=False, http=http, **options)
    cand = by_id(a.discover())[FULL[0]["uuid"]]
    return a, cand, http, tmp_path / "out" / "x.jpg"


def test_resolve_media_reads_sha256_and_fetch_verifies_it(tmp_path):
    payload = b"\xff\xd8\xff\xe0 fake jpeg"
    import hashlib

    rec = {**FULL[0], "sha256": hashlib.sha256(payload).hexdigest()}
    a, cand, http, dest = live(tmp_path, rec, payload)
    ref = a.resolve_media(cand)
    assert http.urls == [f"https://database.fathomnet.org/api/images/{FULL[0]['uuid']}"]
    assert ref.url == cand.media_url and ref.ext == "jpg" and ref.extra["sha256"] == rec["sha256"]
    n, sha = a.fetch_media(cand, ref, dest)
    assert n == len(payload) and sha == rec["sha256"] and dest.read_bytes() == payload


def test_fetch_media_sha_mismatch_and_bad_magic_delete_the_file(tmp_path):
    a, cand, _, dest = live(tmp_path, FULL[0], b"\xff\xd8\xff not the registered bytes")
    ref = a.resolve_media(cand)
    assert ref.extra["sha256"] == "a34295aa2f9dda4f8888d2b53b6c48f44a5ea5de39832ab5cb329726497d1091"
    with pytest.raises(HttpError, match="sha256"):
        a.fetch_media(cand, ref, dest)
    assert not dest.exists()
    b, cand_b, _, dest_b = live(tmp_path / "b", FULL[0], b"<html>error page</html>", verify_sha256=False)
    with pytest.raises(HttpError, match="magic"):
        b.fetch_media(cand_b, b.resolve_media(cand_b), dest_b)
    assert not dest_b.exists()


def test_resolve_media_refuses_withdrawn_or_relicensed_images(tmp_path):
    a, cand, _, _ = live(tmp_path / "a", {**FULL[0], "valid": False}, b"x")
    with pytest.raises(RuntimeError, match="no longer valid"):
        a.resolve_media(cand)
    b, cand_b, _, _ = live(tmp_path / "b", {**FULL[0], "imageLicense": "CC-BY-NC-ND-4.0"}, b"x")
    with pytest.raises(RuntimeError, match="licence"):
        b.resolve_media(cand_b)


def test_dry_run_discover_and_geo_never_send_a_request(tmp_path):
    a = make_adapter(tmp_path, ccby=LIGHT[4:])  # NoNet raises on any request
    for c in a.discover():
        a.resolve_licence(c)
        a.resolve_geo(c)
