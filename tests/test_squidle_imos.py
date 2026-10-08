"""Offline tests for the squidle_imos adapter, run on the real fixtures in tests/fixtures/squidle_imos/.

No test touches the network: S3 listings, dive CSVs and AODN records are copied into metadata/raw/ (like the other adapter
tests) and the Http client raises on any request. Expected values come from tests/fixtures/squidle_imos/SOURCE.md and
research/squidle_imos.md ("resolve_geo recipe", expected-results table).

Real, unmodified: the five fixture files (IMOS per-dive CSV excerpt, SQUIDLE+ exports of deployments 213 and 16821, the two
``/api/pose`` pages) and the text of the AODN ``MD_LegalConstraints`` (title, licence link, citation and acknowledgement
sentences, credit lines; re-wrapped in a minimal ISO 19115-3 shell). Synthetic (built by hand to hit an edge case): the S3
listings (real campaign names and the real dive key, invented sizes), the extra dive-CSV rows (twin cameras, altitudes, a
missing fix) and the other campaigns of the spread-order test.
"""

import csv
import io
import json
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

from aquasource.adapters import squidle_imos as sq
from aquasource.adapters.base import Context, MediaRef, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog
from aquasource.core.schema import Candidate
from aquasource.runner import run_source

FIX = Path(__file__).parent / "fixtures" / "squidle_imos"
CAMPAIGN = "ScottReef201108"
DIVE = "r20110810_042127_04_scott_long_leg_auv8"
ACK = (
    "Data was sourced from Australia’s Integrated Marine Observing System (IMOS) – IMOS is enabled by the "
    "National Collaborative Research Infrastructure strategy (NCRIS)."
)
CITE_TEXT = 'The citation in a list of references is: "IMOS [year-of-data-download], [Title], [data-access-URL], accessed [date-of-access]."'
ACK_TEXT = (
    "Any users of IMOS data are required to clearly acknowledge the source of the material derived from IMOS in the format: "
    f'"{ACK}" If relevant, also credit other organisations involved in collection of this particular datastream '
    "(as listed in 'credit' in the metadata record)."
)
CREDITS = [
    "Australia’s Integrated Marine Observing System (IMOS) is enabled by the National Collaborative Research Infrastructure "
    "Strategy (NCRIS). It is operated by a consortium of institutions as an unincorporated joint venture, with the University "
    "of Tasmania as Lead Agent.",
    "Australian Centre for Field Robotics (ACFR)",
    "The University of Sydney (USYD)",
]
CC_URL = "http://creativecommons.org/licenses/by/4.0/"
GEO_SRC_CSV = f"IMOS AUV csv_outputs/{CAMPAIGN}/DATA_{CAMPAIGN}_{DIVE}.csv: latitude,longitude (WGS84); depth_m=depth_sensor"
GEO_SRC_SQ = "SQUIDLE+ /api/pose lat,lon (WGS84); depth_m=pose.data.dep|pose.dep (vehicle depth)"
IMG = "https://s3-ap-southeast-2.amazonaws.com/imos-data/IMOS/AUV/auv_viewer_data/images"
FIXTURE_CSV = (FIX / "imos_s3_dive_csv_ScottReef201108_excerpt.csv").read_text(encoding="utf-8")
NAMES = ["PR_20110810_042708_616_LC16", "PR_20110810_042709_618_LC16", "PR_20110810_042710_619_LC16"]
FIXTURE_ROWS = {  # research table, expected results on the fixtures
    NAMES[0]: (-14.10650833, 121.89248264, 57.27),
    NAMES[1]: (-14.10650833, 121.89248056, 57.21),
    NAMES[2]: (-14.10650833, 121.89247847, 57.2),
}


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


class Down(Http):
    def request(self, method, url, **k):
        raise HttpError(url, 503, "down")


def make_adapter(tmp_path, *, http=None, dry_run=True, **options):
    options.setdefault("accessed", "2026-10-08")
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "squidle_imos").ensure()
    ctx = Context(cfg, http or NoNet(dry_run=dry_run), layout, options, dry_run, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("squidle_imos")(ctx)


def failures(a):
    path = a.ctx.layout.failures_jsonl
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


# ----------------------------------------------------------------------------------------------- seed helpers
def seed(a, name, text):
    path = a.ctx.layout.raw / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def s3_xml(prefixes=(), keys=(), token=None):
    body = "".join(f"<CommonPrefixes><Prefix>{p}</Prefix></CommonPrefixes>" for p in prefixes)
    body += "".join(f"<Contents><Key>{k}</Key><Size>{n}</Size></Contents>" for k, n in keys)
    if token:
        body += f"<NextContinuationToken>{token}</NextContinuationToken>"
    return (
        '<?xml version="1.0" encoding="UTF-8"?><ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<Name>imos-data</Name><IsTruncated>{'true' if token else 'false'}</IsTruncated>{body}</ListBucketResult>"
    )


def seed_campaigns(a, names):
    prefixes = [f"{sq.CSV_PREFIX}{n}/" for n in names] + [f"{sq.CSV_PREFIX}seqld.csv.manifest/"]
    seed(a, "s3/campaigns_1.xml", s3_xml(prefixes))


def seed_dives(a, campaign, dives):
    keys = [(f"{sq.CSV_PREFIX}{campaign}/DATA_{campaign}_{d}.csv", n) for d, n in dives]
    keys.append((f"{sq.CSV_PREFIX}{campaign}/README.txt", 10))
    seed(a, f"s3/dives_{campaign}_1.xml", s3_xml(keys=keys))


def seed_csv(a, campaign, dive, text):
    seed(a, f"csv/{campaign}/{dive}.csv", text)


def dive_csv(campaign, dive, rows, platform="SIRIUS"):
    """A dive CSV in the layout of the real files; ``rows`` = (name, lat, lon, depth_sensor, altitude, time)."""
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["dive_number", "dive_name", "facility_code", "campaign_code", "dive_code", "number_of_images", "abstract", "platform_code", "pattern", " geospatial_lon_min"])
    w.writerow([1, "x", "AUV", campaign, dive, len(rows), "line one\nline two, with a comma", platform, "trajectory", "1.0"])
    w.writerow(["campaign_code", "dive_code", "image_filename", "longitude", "latitude", "image_width", "depth_sensor", "altitude_sensor", "depth", "time"])
    for name, lat, lon, depth, alt, t in rows:
        w.writerow([campaign, dive, name, lon, lat, "1.5", depth, alt, "" if depth == "" or alt == "" else float(depth) + float(alt), t])
    return out.getvalue()


def row(i, *, lat="-30.1", lon="115.2", depth="20.0", alt="2.0", cam="LC16", base=(2015, 3, 4), dt=1):
    """Row ``i`` of a synthetic dive, ``dt`` seconds after row 0, 2015-03-04 01:00:00."""
    s = 3600 + i * dt
    stamp = f"{base[0]}{base[1]:02d}{base[2]:02d}T{s // 3600:02d}{s % 3600 // 60:02d}{s % 60:02d}Z"
    name = f"PR_{base[0]}{base[1]:02d}{base[2]:02d}_{s // 3600:02d}{s % 3600 // 60:02d}{s % 60:02d}_{i % 1000:03d}_{cam}"
    return (name, lat, lon, depth, alt, stamp)


def aodn_xml(*, title="Creative Commons Attribution 4.0 International License", url=CC_URL, extra_text=(), credits=(), with_licence=True):
    """A minimal ISO 19115-3 shell around the real MD_LegalConstraints texts of the IMOS AUV records."""
    texts = [CITE_TEXT, ACK_TEXT, *extra_text]
    other = "".join(f"<mco:otherConstraints><gco:CharacterString>{escape(t)}</gco:CharacterString></mco:otherConstraints>" for t in texts)
    ref = (
        "<mco:reference><cit:CI_Citation><cit:title><gco:CharacterString>" + escape(title) + "</gco:CharacterString></cit:title>"
        "<cit:citedResponsibleParty><cit:CI_Responsibility><cit:party><cit:CI_Organisation><cit:contactInfo><cit:CI_Contact>"
        "<cit:onlineResource><cit:CI_OnlineResource><cit:linkage><gco:CharacterString>http://creativecommons.org/international/"
        "</gco:CharacterString></cit:linkage></cit:CI_OnlineResource></cit:onlineResource><cit:onlineResource><cit:CI_OnlineResource>"
        f"<cit:linkage><gco:CharacterString>{url}</gco:CharacterString></cit:linkage></cit:CI_OnlineResource></cit:onlineResource>"
        "</cit:CI_Contact></cit:contactInfo></cit:CI_Organisation></cit:party></cit:CI_Responsibility></cit:citedResponsibleParty>"
        "</cit:CI_Citation></mco:reference>"
    )
    legal = f"<mri:resourceConstraints><mco:MD_LegalConstraints>{ref}{other}</mco:MD_LegalConstraints></mri:resourceConstraints>"
    credit = "".join(f"<mri:credit><gco:CharacterString>{escape(c)}</gco:CharacterString></mri:credit>" for c in credits)
    return (
        '<?xml version="1.0" encoding="UTF-8"?><mdb:MD_Metadata xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0" '
        'xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0" xmlns:mco="http://standards.iso.org/iso/19115/-3/mco/1.0" '
        'xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0" xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0">'
        f"<mdb:identificationInfo><mri:MD_DataIdentification>{credit}{legal if with_licence else ''}"
        "</mri:MD_DataIdentification></mdb:identificationInfo></mdb:MD_Metadata>"
    )


def seed_records(a, *, sirius=True, nimbus=True, facility=True, **kw):
    if sirius:
        seed(a, f"aodn/{sq.PLATFORM_RECORDS['IMOS AUV Sirius']}.xml", aodn_xml(**kw))
    if nimbus:
        seed(a, f"aodn/{sq.PLATFORM_RECORDS['IMOS AUV Nimbus']}.xml", aodn_xml(**kw))
    if facility:
        seed(a, f"aodn/{sq.FACILITY}.xml", aodn_xml(credits=CREDITS, **kw))


def seed_scott(a, *, spacing=True):
    """ScottReef201108: the real fixture CSV, one dive, the CC BY records."""
    seed_campaigns(a, [CAMPAIGN])
    seed_dives(a, CAMPAIGN, [(DIVE, 1000)])
    seed_csv(a, CAMPAIGN, DIVE, FIXTURE_CSV)
    seed_records(a)


def cands(a):
    return list(a.discover())


def by_name(cs):
    return {c.item_id.rsplit("/", 1)[1]: c for c in cs}


# --------------------------------------------------------------------------------------------- pure helpers
def test_parse_listing_prefixes_keys_and_continuation_token():
    prefixes, keys, token = sq.parse_listing(s3_xml(["a/", "b/"], [("a/k.csv", 5)], token="TOK"))
    assert prefixes == ["a/", "b/"] and keys == [("a/k.csv", 5)] and token == "TOK"
    assert sq.parse_listing(s3_xml(["a/"]))[2] is None


def test_xml_with_entities_is_refused():
    with pytest.raises(ValueError):
        sq.parse_listing('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e "boom">]><ListBucketResult>&e;</ListBucketResult>')
    with pytest.raises(ValueError):
        sq.parse_aodn_record('<!DOCTYPE x [<!ENTITY e "boom">]><x/>')


@pytest.mark.parametrize(
    "name,ok",
    [("GBR200709", True), ("WA_SW_202103", True), ("TasVic201602SS", True), ("Wilsonsprom201603SS", True), ("seqld.csv.manifest", False), ("auvReporting.csv", False)],
)
def test_campaign_names(name, ok):
    assert sq.is_campaign(name) is ok


def test_dive_date_and_stamps():
    assert sq.dive_date(DIVE) == "2011-08-10" and sq.dive_date("nodate") is None
    assert sq.iso_z(sq.parse_stamp("20110810T042708Z")) == "2011-08-10T04:27:08Z"
    assert sq.name_stamp("PR_20150526_024829_369_FC16") - sq.name_stamp("PR_20150526_024829_000_FC16") == pytest.approx(0.369)
    assert sq.name_stamp("whatever.jpg") is None and sq.camera_of("PR_20150526_024829_369_FC16") == "FC16"


def test_pick_order_is_a_permutation_with_the_centre_first_and_spread_order_ends_first():
    assert sq.pick_order(3) == (1, 0, 2)
    for n in (0, 1, 2, 7, 50):
        assert sorted(sq.pick_order(n)) == list(range(n)) and sorted(sq.spread_order(n)) == list(range(n))
    assert sq.spread_order(5)[:2] == [0, 4]


def test_parse_dive_csv_fixture_header_rows_and_multiline_abstract():
    d = sq.parse_dive_csv(FIXTURE_CSV)
    assert d.header["platform_code"] == "SIRIUS" and d.header["campaign_code"] == CAMPAIGN and len(d.rows) == 3
    assert d.rows[0]["image_filename"] == NAMES[0] and d.rows[0]["depth_sensor"] == "57.266194"
    text = dive_csv("X201501", "r20150304_010000_a", [row(0)])
    d = sq.parse_dive_csv(text)
    assert d.header["abstract"] == "line one\nline two, with a comma" and "geospatial_lon_min" in d.header and len(d.rows) == 1


def test_parse_dive_csv_without_column_header_is_an_error():
    with pytest.raises(ValueError):
        sq.parse_dive_csv("a,b\n1,2\n")


def test_thin_keeps_frames_at_least_min_spacing_apart():
    frames = [sq.Frame(f"f{i}", float(t), {}) for i, t in enumerate([0, 10, 29, 30, 31, 61, 100])]
    assert [f.name for f in sq.thin(frames, 30)] == ["f0", "f3", "f5", "f6"]
    assert len(sq.thin(frames, 0)) == 7


# ---------------------------------------------------------------------------------------------- discover
def test_discover_real_fixture_item_ids_media_url_and_type(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0)
    seed_scott(a)
    cs = cands(a)
    assert sorted(c.item_id for c in cs) == [f"{CAMPAIGN}/{DIVE}/{n}" for n in NAMES]
    c = by_name(cs)[NAMES[0]]
    assert c.source == "squidle_imos" and c.media_type == "image" and c.ext == "jpg"
    assert c.media_url == f"{IMG}/{CAMPAIGN}/{DIVE}/full_res/{NAMES[0]}.jpg"
    assert c.origin_url == f"https://s3-ap-southeast-2.amazonaws.com/imos-data/{sq.CSV_PREFIX}{CAMPAIGN}/DATA_{CAMPAIGN}_{DIVE}.csv"
    assert c.timestamp == "2011-08-10T04:27:08Z"
    assert c.extra["platform"] == "IMOS AUV Sirius" and c.extra["camera"] == "LC16"
    assert c.extra["altitude_m"] == 2.158 and c.extra["seafloor_depth_m"] == 59.42
    assert c.extra["thumbnail_url"] == f"{IMG}/{CAMPAIGN}/{DIVE}/thumbnails/{NAMES[0]}.jpg"
    assert c.extra["aodn_record"] == "fe81b24e-adee-4c77-a8e1-e8a77cfd3dff"
    assert [c.item_id.rsplit("/", 1)[1] for c in cs][0] == NAMES[1]  # centre frame first (pick_order)
    assert failures(a) == []


def test_discover_is_idempotent_and_item_ids_are_stable(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0)
    seed_scott(a)
    first = [c.item_id for c in cands(a)]
    assert first == [c.item_id for c in cands(make_adapter(tmp_path, min_spacing_s=0))]


def test_default_thinning_keeps_one_frame_of_the_one_second_fixture(tmp_path):
    a = make_adapter(tmp_path)  # min_spacing_s 30
    seed_scott(a)
    cs = cands(a)
    assert [c.item_id for c in cs] == [f"{CAMPAIGN}/{DIVE}/{NAMES[0]}"]


def test_thumbnail_option_changes_only_the_media_url(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0, image="thumbnail")
    seed_scott(a)
    c = by_name(cands(a))[NAMES[1]]
    assert c.media_url == f"{IMG}/{CAMPAIGN}/{DIVE}/thumbnails/{NAMES[1]}.jpg" and c.item_id.endswith(NAMES[1])


def test_stereo_twin_altitude_window_and_missing_fix_are_filtered(tmp_path):
    camp, dive = "Apollo202309", "r20150304_010000_a"
    rows = [
        row(0, cam="AC16"), row(0, cam="FC16"),  # twin cameras: AC16 dropped
        row(40, cam="FC16", alt="0.0"), row(80, cam="FC16", alt="8.5"), row(120, cam="FC16", alt=""),  # water column / too high / unknown
        row(160, cam="FC16", lat="", lon=""),  # no navigation fix
        row(200, cam="FC16", alt="0.5"), row(240, cam="FC16", alt="6.0"),  # window edges are inside
    ]
    a = make_adapter(tmp_path)
    seed_campaigns(a, [camp]), seed_dives(a, camp, [(dive, 500)]), seed_csv(a, camp, dive, dive_csv(camp, dive, rows)), seed_records(a)
    names = sorted(c.item_id.rsplit("/", 1)[1] for c in cands(a))
    assert names == sorted([rows[1][0], rows[6][0], rows[7][0]])
    assert a.skipped == {"altitude": 3, "no_fix": 1}
    a2 = make_adapter(tmp_path / "keep", twins="keep", altitude_min=0, altitude_max=100)
    seed_campaigns(a2, [camp]), seed_dives(a2, camp, [(dive, 500)]), seed_csv(a2, camp, dive, dive_csv(camp, dive, rows)), seed_records(a2)
    assert any(c.item_id.endswith("_AC16") for c in cands(a2))


def test_thinning_spacing_option_and_frames_per_dive(tmp_path):
    camp, dive = "WA201503", "r20150304_010000_a"
    rows = [row(i, dt=10) for i in range(10)]  # one frame every 10 s
    for opts, n in (({}, 4), ({"min_spacing_s": 0}, 10), ({"min_spacing_s": 50}, 2), ({"frames_per_dive": 3}, 3)):
        a = make_adapter(tmp_path / str(len(opts)) / str(n), **opts)
        seed_campaigns(a, [camp]), seed_dives(a, camp, [(dive, 500)]), seed_csv(a, camp, dive, dive_csv(camp, dive, rows)), seed_records(a)
        assert len(cands(a)) == n, opts


def test_frames_of_one_second_use_the_millisecond_time_of_the_file_name(tmp_path):
    camp, dive = "GeographeBay201505", "r20150526_024446_wa-gb-auv-01"
    names = ["PR_20150526_024829_369_FC16", "PR_20150526_024829_870_FC16", "PR_20150526_024830_370_FC16"]
    rows = [(n, "-33.5731341", "115.1917994", "21.8", "3.3", "20150526T024829Z") for n in names]
    a = make_adapter(tmp_path, min_spacing_s=0.4)
    seed_campaigns(a, [camp]), seed_dives(a, camp, [(dive, 500)]), seed_csv(a, camp, dive, dive_csv(camp, dive, rows)), seed_records(a)
    assert len(cands(a)) == 3  # 0.5 s apart: all kept although the time column is the same second
    b = make_adapter(tmp_path / "b", min_spacing_s=0.9)
    seed_campaigns(b, [camp]), seed_dives(b, camp, [(dive, 500)]), seed_csv(b, camp, dive, dive_csv(camp, dive, rows)), seed_records(b)
    assert sorted(c.item_id.rsplit("/", 1)[1] for c in cands(b)) == [names[0], names[2]]


def test_campaigns_listing_ignores_non_campaign_prefixes_and_the_campaigns_option(tmp_path):
    a = make_adapter(tmp_path)
    seed_campaigns(a, ["WA201004", "GBR200709", "Tasmania202302"])
    assert a.campaigns() == ["GBR200709", "WA201004", "Tasmania202302"]  # by year-month, seqld.csv.manifest is not a campaign
    b = make_adapter(tmp_path, campaigns="GBR200709,Tasmania202302,Nope200001")
    assert b.campaigns() == ["GBR200709", "Tasmania202302"]
    assert b.estimate()["campaigns_in_bucket"] == 2 and b.estimate()["images_squidle_research"] == 7_595_565


def test_dive_listing_filters_by_the_date_in_the_dive_code(tmp_path):
    a = make_adapter(tmp_path, **{"from": "2015-03-05", "to": "2015-03-31"})
    seed_dives(a, "WA201503", [("r20150304_010000_a", 1), ("r20150310_010000_b", 1), ("r20150402_010000_c", 1), ("undated", 1)])
    assert [d.dive for d in a.dives("WA201503")] == ["r20150310_010000_b", "undated"]


def test_paged_listings_follow_the_continuation_token(tmp_path):
    a = make_adapter(tmp_path)
    key = lambda d: f"{sq.CSV_PREFIX}WA201503/DATA_WA201503_{d}.csv"
    seed(a, "s3/dives_WA201503_1.xml", s3_xml(keys=[(key("r20150304_010000_a"), 1)], token="T1"))
    seed(a, "s3/dives_WA201503_2.xml", s3_xml(keys=[(key("r20150305_010000_b"), 2)]))
    assert [d.dive for d in a.dives("WA201503")] == ["r20150304_010000_a", "r20150305_010000_b"]


def test_spread_order_covers_every_campaign_first_then_weights_by_size(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0)
    names = ["A200901", "B201201", "C201501"]
    seed_campaigns(a, names)
    for n, size in zip(names, (100_000, 100_000, 3_300)):  # C is a small campaign
        dive = "r20150304_010000_a"
        seed_dives(a, n, [(dive, size)])
        seed_csv(a, n, dive, dive_csv(n, dive, [row(i, dt=60) for i in range(20)]))
    seed_records(a)
    got = [c.extra["campaign"] for c in cands(a)]
    assert got[:3] == ["A200901", "C201501", "B201201"]  # oldest, newest, middle
    assert sorted(got) == sorted([n for n in names for _ in range(20)])
    assert got[3:23].count("C201501") < got[3:23].count("A200901")  # the small campaign comes later in the weighted round robin
    t = make_adapter(tmp_path, min_spacing_s=0, order="table")
    assert [c.extra["campaign"] for c in cands(t)][:21] == ["A200901"] * 20 + ["B201201"]


def test_a_dive_csv_that_cannot_be_read_is_logged_and_skipped(tmp_path):
    a = make_adapter(tmp_path, http=Down(dry_run=True), min_spacing_s=0)
    seed_campaigns(a, [CAMPAIGN]), seed_dives(a, CAMPAIGN, [(DIVE, 1000)])
    assert cands(a) == []
    assert failures(a)[0]["stage"] == "dive_csv" and failures(a)[0]["item_id"] == f"{CAMPAIGN}/{DIVE}"


def test_unknown_route_and_order_are_refused(tmp_path):
    with pytest.raises(ValueError):
        cands(make_adapter(tmp_path, route="ftp"))
    a = make_adapter(tmp_path, order="random")
    seed_campaigns(a, [CAMPAIGN])
    with pytest.raises(ValueError):
        cands(a)
    with pytest.raises(ValueError):
        cands(make_adapter(tmp_path, route="squidle"))  # needs deployments=


# ----------------------------------------------------------------------------------------------- licence
def test_licence_sirius_is_tier_b_at_record_level_with_the_providers_acknowledgement_and_citation(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0)
    seed_scott(a)
    lic = a.resolve_licence(by_name(cands(a))[NAMES[0]])
    assert (lic.name, lic.tier, lic.level, lic.url) == ("CC-BY-4.0", "B", "record", CC_URL)
    assert lic.attribution.startswith(ACK)
    assert (
        f"IMOS 2026, IMOS - Autonomous Underwater Vehicles - AUV Sirius (campaign {CAMPAIGN}), "
        f"https://imos-data.s3-ap-southeast-2.amazonaws.com/IMOS/AUV/{CAMPAIGN}/, accessed 2026-10-08."
    ) in lic.attribution
    assert "Australian Centre for Field Robotics (ACFR); The University of Sydney (USYD)" in lic.attribution
    assert "Integrated Marine Observing System (IMOS) is enabled" not in lic.attribution.split("Credit:")[1]
    assert failures(a) == []


def test_licence_holt_campaign_is_read_from_the_facility_record_at_collection_level(tmp_path):
    camp, dive = "GeographeBay201505", "r20150526_024446_wa-gb-auv-01"
    a = make_adapter(tmp_path)
    seed_campaigns(a, [camp]), seed_dives(a, camp, [(dive, 500)])
    seed_csv(a, camp, dive, dive_csv(camp, dive, [row(0)], platform="SIRIUS"))  # the dive header says SIRIUS
    seed_records(a)
    c = cands(a)[0]
    assert c.extra["platform"] == "ACFR AUV Holt" and c.extra["aodn_record"] == sq.FACILITY
    lic = a.resolve_licence(c)
    assert (lic.tier, lic.level, lic.name) == ("B", "collection", "CC-BY-4.0")
    assert "AUV Holt (campaign GeographeBay201505)" in lic.attribution


def test_licence_nimbus_uses_its_own_record(tmp_path):
    camp, dive = "Apollo202309", "r20230926_232818_NG21_d0"
    a = make_adapter(tmp_path)
    seed_campaigns(a, [camp]), seed_dives(a, camp, [(dive, 500)])
    seed_csv(a, camp, dive, dive_csv(camp, dive, [row(0, cam="FC16")], platform="NIMBUS"))
    seed_records(a)
    c = cands(a)[0]
    assert c.extra["platform"] == "IMOS AUV Nimbus" and c.extra["aodn_record"] == sq.PLATFORM_RECORDS["IMOS AUV Nimbus"]
    assert a.resolve_licence(c).level == "record"


def test_licence_falls_back_to_the_facility_when_the_platform_record_is_unreadable(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0, http=Down(dry_run=True))
    seed_scott(a)
    (a.ctx.layout.raw / f"aodn/{sq.PLATFORM_RECORDS['IMOS AUV Sirius']}.xml").unlink()
    lic = a.resolve_licence(cands(a)[0])
    assert (lic.tier, lic.level) == ("B", "collection")
    assert failures(a)[0]["stage"] == "licence_record"


def test_licence_not_read_at_any_level_is_unknown_never_upgraded(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0, http=Down(dry_run=True))
    seed_scott(a)
    for f in (a.ctx.layout.raw / "aodn").iterdir():
        f.unlink()
    lic = a.resolve_licence(cands(a)[0])
    assert (lic.tier, lic.level, lic.name) == ("U", "unknown", "not stated")


def test_a_record_without_legal_constraints_is_unknown(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0)
    seed_scott(a)
    seed_records(a, with_licence=False)
    assert a.resolve_licence(cands(a)[0]).tier == "U"


@pytest.mark.parametrize(
    "kw,tier",
    [
        ({"title": "Creative Commons Attribution-NonCommercial 4.0 International License", "url": "http://creativecommons.org/licenses/by-nc/4.0/"}, "X"),
        ({"extra_text": ["Data are for research use only."]}, "X"),
        ({"extra_text": ["No redistribution of these images."]}, "X"),
        ({"title": "Creative Commons Attribution-ShareAlike 4.0 International License", "url": "http://creativecommons.org/licenses/by-sa/4.0/"}, "C"),
        ({"title": "Some bespoke IMOS terms", "url": "http://example.org/terms"}, "U"),
    ],
)
def test_other_terms_in_the_record_are_never_upgraded_to_b(tmp_path, kw, tier):
    a = make_adapter(tmp_path, min_spacing_s=0)
    seed_scott(a)
    seed_records(a, **kw)
    assert a.resolve_licence(cands(a)[0]).tier == tier


def test_real_record_text_is_not_misread_as_excluded():
    rec = sq.parse_aodn_record(aodn_xml(credits=CREDITS))
    name, url, tier = sq.SquidleImos._licence_of(rec)
    assert (name, url, tier) == ("CC-BY-4.0", CC_URL, "B") and rec["ack"] == ACK and len(rec["credits"]) == 3


# ------------------------------------------------------------------------------------------------- geo
@pytest.mark.parametrize("name", NAMES)
def test_resolve_geo_imos_csv_fixture_rows(tmp_path, name):
    a = make_adapter(tmp_path, min_spacing_s=0)
    seed_scott(a)
    lat, lon, depth = FIXTURE_ROWS[name]
    g = a.resolve_geo(by_name(cands(a))[name])
    assert (g.lat, g.lon, g.depth_m) == (lat, lon, depth)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("image", False, None)
    assert g.geo_source == GEO_SRC_CSV


def test_resolve_geo_without_coordinates_is_none_with_the_source_that_was_checked():
    rec = {"src": "imos_csv", "campaign_code": CAMPAIGN, "dive_code": DIVE, "latitude": "", "longitude": "121.9", "depth_sensor": "20", "platform_name": "IMOS AUV Sirius"}
    g = sq.geo_for_record(rec)
    assert g.geo_precision == "none" and g.lat is None and g.lon is None and g.geo_source == GEO_SRC_CSV
    for lat, lon in (("NaN", "10"), ("91", "10"), ("-30", "181"), ("0", "0"), ("-30", "")):
        g = sq.geo_for_record({**rec, "latitude": lat, "longitude": lon})
        assert g.geo_precision == "none", (lat, lon)


@pytest.mark.parametrize("value,depth", [("57.266194", 57.27), ("0", 0.0), ("11000", 11000.0), ("-1000.6", None), ("-1.1", None), ("12000", None), ("", None), ("NaN", None)])
def test_vehicle_depth_outside_zero_to_11000_is_dropped(value, depth):
    rec = {"src": "imos_csv", "campaign_code": CAMPAIGN, "dive_code": DIVE, "latitude": "-14.1", "longitude": "121.9", "depth_sensor": value, "platform_name": "IMOS AUV Nimbus"}
    g = sq.geo_for_record(rec)
    assert g.depth_m == depth and g.geo_precision == "image" and g.lat == -14.1


def test_a_row_without_a_fix_that_reaches_resolve_geo_gets_geo_none(tmp_path):
    a = make_adapter(tmp_path)
    c = Candidate("squidle_imos", "x/y/z", "image", "https://example.org/z.jpg", "https://example.org/", raw={"src": "imos_csv", "latitude": "", "longitude": "", "platform_name": "IMOS AUV Sirius"})
    assert a.resolve_geo(c).geo_precision == "none"


def test_cross_route_export_of_deployment_213_gives_the_same_positions_and_ids(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0)
    seed_records(a)
    cs = a.candidates_from_export((FIX / "squidle_deployment_export_213_excerpt.csv").read_text(), "IMOS AUV Sirius", 213)
    assert sorted(c.item_id for c in cs) == [f"{CAMPAIGN}/{DIVE}/{n}" for n in NAMES]  # same ids as the S3 route (dedupe)
    for c in cs:
        lat, lon, depth = FIXTURE_ROWS[c.item_id.rsplit("/", 1)[1]]
        g = a.resolve_geo(c)
        assert (g.lat, g.lon, g.depth_m) == (lat, lon, depth)
        assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m, g.geo_source) == ("image", False, None, GEO_SRC_SQ)
        assert c.media_url == f"{IMG}/{CAMPAIGN}/{DIVE}/full_res/{c.item_id.rsplit('/', 1)[1]}.jpg"
        assert a.resolve_licence(c).tier == "B"


def load_pose(name):
    return json.loads((FIX / name).read_text())


def test_pose_page_old_import_vehicle_depth_and_the_mosaic_is_not_a_sample(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0)
    page = load_pose("squidle_api_pose_deployment22_page1.json")
    assert sq.geo_for_record({"src": "squidle", "lat": 1, "lon": 1, "media_key": "k", "deployment_key": "k", "platform_name": "IMOS AUV Sirius"}) is None
    cs = sq.candidates_from_pose_json(a, page)
    assert len(cs) == 2 and len(page["objects"]) == 3  # item 2 is the WMS ortho-mosaic
    dive = "r20121128_195806_Burrewarra_BU_DG3_05_dense"
    assert [c.item_id for c in cs] == [f"Batemans201211/{dive}/PR_20121128_200011_588_LC16", f"Batemans201211/{dive}/PR_20121128_200012_589_LC16"]
    g1, g2 = (a.resolve_geo(c) for c in cs)
    assert (g1.lat, g1.lon, g1.depth_m) == (-35.82695625, 150.2332375, 18.09)
    assert (g2.lat, g2.lon, g2.depth_m) == (-35.82695764, 150.23323611, 18.04)
    assert (g1.geo_precision, g1.geo_inferred, g1.geo_uncertainty_m, g1.geo_source) == ("image", False, None, GEO_SRC_SQ)


def test_pose_page_new_import_uses_data_dep_as_vehicle_depth(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0)
    seed_records(a)
    page = load_pose("squidle_api_pose_deployment11646_page1.json")
    cs = sq.candidates_from_pose_json(a, page)
    assert len(cs) == 2
    g1, g3 = (a.resolve_geo(c) for c in cs)
    assert (g1.lat, g1.lon, g1.depth_m) == (-28.847136499999998, 114.04728, 45.75)  # pose.dep 47.473168 is the seafloor
    assert (g3.lat, g3.lon, g3.depth_m) == (-28.8471381, 114.0472806, 45.7)
    assert page["objects"][0]["dep"] == 47.473168 and cs[0].item_id.startswith("WA202103/r20210315_230947_SS13_coralpatches_40m_out/")
    assert a.resolve_licence(cs[0]).tier == "B"


def test_bruv_dropcam_fixture_is_station_precision_inferred_and_tier_u(tmp_path):
    a = make_adapter(tmp_path)
    cs = a.candidates_from_export((FIX / "squidle_deployment_export_16821_boss_dropcam.csv").read_text(), "UWA BOSS Dropcam", 16821)
    assert len(cs) == 4 and cs[0].item_id.startswith("squidle/202211_Investigator/INV_DC_001/INV_DC_001_")
    for c in cs:
        g = a.resolve_geo(c)
        assert (g.lat, g.lon, g.depth_m) == (-34.16379179, 120.9335453, 77.0)
        assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m, g.geo_source) == ("station", True, 100.0, GEO_SRC_SQ)
        lic = a.resolve_licence(c)
        assert (lic.tier, lic.level) == ("U", "unknown") and "UWA BOSS Dropcam" in lic.attribution
    assert {c.item_id for c in cs} == {f"squidle/202211_Investigator/INV_DC_001/INV_DC_001_{v}" for v in ("east", "north", "south", "west")}


@pytest.mark.parametrize(
    "platform,n_img,n_xy,precision,inferred,unc",
    [
        ("IMOS AUV Sirius", 1000, 1, "image", False, None),  # a named AUV is never reclassified
        ("IMOS AUV Nimbus", 5, 5, "image", False, None),
        ("ACFR AUV Holt", 5, 5, "image", False, None),
        ("SOI ROV Subastian", 9, 9, "image", False, None),
        ("CSIRO MNF DTC Towed Camera", 9, 9, "image", False, None),
        ("RLS Diver Photos", 9, 9, "station", True, 1000.0),
        ("BRUV", 1, 1, "station", True, 100.0),
        ("NSW Diver", 3, 3, "station", True, 500.0),
        ("Some Camera", 12, 1, "station", True, 500.0),  # many images on one coordinate
        ("Some Camera", 12, 12, "image", False, None),
    ],
)
def test_station_branches_of_the_recipe(platform, n_img, n_xy, precision, inferred, unc):
    g = sq.geo_for_record({"src": "squidle", "lat": -30.0, "lon": 115.0, "dep": 10.0, "platform_name": platform, "n_img": n_img, "n_xy": n_xy})
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == (precision, inferred, unc)


def test_non_images_and_invalid_records_are_not_samples():
    base = {"src": "squidle", "lat": -30.0, "lon": 115.0, "platform_name": "IMOS AUV Sirius", "media_key": "a", "deployment_key": "b"}
    assert sq.geo_for_record({**base, "media_type": "wms"}) is None
    assert sq.geo_for_record({**base, "is_valid": False}) is None
    assert sq.geo_for_record({**base, "path_best_thm": "https://squidle.org/api/media/1/thumbnail?size=400"}) is None
    assert sq.geo_for_record(base).geo_precision == "image"
    with pytest.raises(ValueError):
        sq.geo_for_record({"src": "other"})


# ------------------------------------------------------------------------------------------------ media
def test_resolve_media_and_fetch_media_checks_the_jpeg_magic(tmp_path, monkeypatch):
    a = make_adapter(tmp_path, min_spacing_s=0, dry_run=False)
    seed_scott(a)
    c = cands(a)[0]
    ref = a.resolve_media(c)
    assert (ref.url, ref.ext) == (c.media_url, "jpg")
    dest = tmp_path / "out" / "a.jpg"

    def fake(url, d, **k):
        d.parent.mkdir(parents=True, exist_ok=True)
        d.write_bytes(fake.payload)
        return len(fake.payload), "sha"

    monkeypatch.setattr(a.http, "download", fake)
    fake.payload = b"\xff\xd8\xff\xe0" + b"0" * 10
    assert a.fetch_media(c, ref, dest) == (14, "sha") and dest.exists()
    fake.payload = b"<?xml version='1.0'?><Error>SlowDown</Error>"
    with pytest.raises(HttpError):
        a.fetch_media(c, ref, dest)
    assert not dest.exists()


def test_dry_run_http_refuses_media_so_discover_never_downloads(tmp_path):
    a = make_adapter(tmp_path, min_spacing_s=0, http=Http(dry_run=True))
    seed_scott(a)
    cs = cands(a)  # all metadata is cached: no request at all
    with pytest.raises(Exception):
        a.fetch_media(cs[0], a.resolve_media(cs[0]), tmp_path / "x.jpg")


# ------------------------------------------------------------------------------------------- adapter meta
def test_adapter_metadata_and_readiness(tmp_path):
    cls = get_adapter_class("squidle_imos")
    assert cls.key == "squidle_imos" and cls.media_types == ("image",) and cls.env_vars == ()
    assert cls.homepage == "https://squidle.org" and "CC BY 4.0" in cls.citation and cls.manual_steps
    assert set(cls.host_intervals) == set(sq.S3_HOSTS)
    assert make_adapter(tmp_path).check_ready() == []


# ----------------------------------------------------------------------------------------------- runner
def test_runner_dry_run_end_to_end(tmp_path, monkeypatch):
    seed_scott(make_adapter(tmp_path, min_spacing_s=0))
    monkeypatch.setattr(Http, "request", lambda self, *a, **k: (_ for _ in ()).throw(AssertionError(f"unexpected network request: {a[:2]}")))
    cfg = load_config(None, data_root=tmp_path)
    s = run_source(cfg, "squidle_imos", "dry-run", options={"min_spacing_s": 0})
    assert s.error is None and s.candidates == 3 and s.selected == 3
    assert dict(s.selected_by_tier) == {"B": 3} and dict(s.selected_by_precision) == {"image": 3}
    assert dict(s.media_types) == {"image": 3} and s.estimate["campaigns_in_bucket"] == 1
    assert s.bbox == [121.89247847, -14.10650833, 121.89248264, -14.10650833]
