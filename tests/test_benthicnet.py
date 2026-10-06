"""Offline tests for the BenthicNet adapter, run on the real fixtures in tests/fixtures/benthicnet/.

No test touches the network: metadata is pre-seeded in metadata/raw/ (like test_german_bight.py) or served by
small fake Http objects. Rows built by hand (missing coordinates, ordering) are marked as synthetic.
"""

import hashlib
import io
import json
import shutil
import tarfile
import zipfile
from pathlib import Path

import pytest

from aquasource.adapters import benthicnet as bn
from aquasource.adapters.base import Context, get_adapter_class
from aquasource.core.config import load_config
from aquasource.core.http import Http, HttpError
from aquasource.core.layout import DatasetLayout
from aquasource.core.manifest import JsonlLog
from aquasource.core.schema import Candidate
from aquasource.runner import run_source

FIX = Path(__file__).parent / "fixtures" / "benthicnet"
CSV_1M = FIX / "benthicnet_unlabelled_sub_sample.csv"
CSV_LAB = FIX / "benthicnet_labelled_sample.csv"
TABLE = FIX / "all_licenses_refs_excerpt.csv"

GEO_1M = "benthicnet_unlabelled_sub.csv:latitude,longitude (WGS84 dd); depth_m=-gebco_bathymetry (GEBCO_2022 bilinear, modelled)"
GEO_LAB = "benthicnet_labelled.csv:latitude,longitude (WGS84 dd); depth_m=-gebco_bathymetry (GEBCO_2022 bilinear, modelled)"
IMG = "https://www.frdr-dfdr.ca/repo/files/9/published/publication_961/submitted_data/01_Data/images"


class NoNet(Http):
    def request(self, *a, **k):  # pragma: no cover - only runs when a test leaks a request
        raise AssertionError(f"unexpected network request: {a[:2]}")


def make_adapter(tmp_path, *, seed=("table", "1m", "labelled"), http=None, **options):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "benthicnet").ensure()
    if "table" in seed:  # the table is cp1252 with CRLF, copied byte for byte like the provider serves it
        shutil.copyfile(TABLE, layout.raw / "all_licenses_refs.csv")
    if "1m" in seed:
        shutil.copyfile(CSV_1M, layout.raw / "benthicnet_unlabelled_sub.csv")
    if "labelled" in seed:
        shutil.copyfile(CSV_LAB, layout.raw / "benthicnet_labelled.csv")
    opts = {"resolve_pangaea": False, **options}
    ctx = Context(cfg, http or NoNet(dry_run=True), layout, opts, True, JsonlLog(layout.failures_jsonl))
    return get_adapter_class("benthicnet")(ctx)


def by_id(cands):
    return {c.item_id: c for c in cands}


# ------------------------------------------------------------------ 1M: default (tier A/B only)
def test_discover_1m_default_yields_only_ab_rows(tmp_path):
    a = make_adapter(tmp_path)
    cands = list(a.discover())
    # the fixture holds 5 FK* rows (SOI, tier U) and 4 RLS rows (CC-BY-4.0 in the table, tier B)
    assert len(cands) == 4
    got = by_id(cands)
    rid = "RLS_Abrolhos (WA)_2021/912354604/WA167_NEB_5m_N_19042021_Rat Island East ({})"
    assert set(got) == {
        rid.format(1), rid.format(2), rid.format(4),
        "RLS_Abrolhos Islands_2013/912354071/WA154_GER4.5m171113TurtleBay1  (1)",
    }
    c = got[rid.format(1)]
    assert c.source == "benthicnet" and c.media_type == "image" and c.ext == "jpg"
    assert c.media_url == "https://rls.tpac.org.au/pq/912354604/WA167_NEB_5m_N_19042021_Rat%20Island%20East%20(1).JPG/"
    assert c.origin_url == "https://doi.org/10.20383/103.01241"
    assert c.timestamp == "2021-04-19T00:00:00+00:00"
    assert c.extra["url"].startswith("http://rls.tpac.org.au/")
    assert c.extra["url_norm"] == "https://rls.tpac.org.au/pq/912354604/WA167_NEB_5m_N_19042021_Rat%20Island%20East%20(1).JPG"
    assert c.extra["datetime_synthetic"] is True and c.extra["tar"] == "RLS_Abrolhos (WA)_2021.tar"


def test_item_ids_are_stable_and_unique(tmp_path):
    ids1 = [c.item_id for c in make_adapter(tmp_path / "a").discover()]
    ids2 = [c.item_id for c in make_adapter(tmp_path / "b").discover()]
    assert ids1 == ids2 and len(set(ids1)) == len(ids1)
    assert len({c.sample_id for c in make_adapter(tmp_path / "c").discover()}) == 4


def test_licence_of_rls_row(tmp_path):
    a = make_adapter(tmp_path)
    c = by_id(a.discover())["RLS_Abrolhos (WA)_2021/912354604/WA167_NEB_5m_N_19042021_Rat Island East (1)"]
    lic_ = a.resolve_licence(c)
    assert lic_.tier == "B" and lic_.level == "record"
    assert lic_.name.startswith("CC-BY-4.0") and "3.0 Australia" in lic_.name
    assert lic_.url == "https://creativecommons.org/licenses/by/4.0/"
    assert "Lowe, S.C., Misiuk, B., Xu, I." in lic_.attribution and "doi.org/10.20383/103.01241" in lic_.attribution
    assert "RLS_Abrolhos (WA)_2021" in lic_.attribution and "6e9c4980-1005-11dd-b28e-00188b4c0af8" in lic_.attribution
    assert "BenthicNet-URLs" not in lic_.attribution


def test_geo_rls_synthetic_offsets_are_station_level(tmp_path):
    a = make_adapter(tmp_path)
    got = by_id(a.discover())
    g = a.resolve_geo(got["RLS_Abrolhos (WA)_2021/912354604/WA167_NEB_5m_N_19042021_Rat Island East (1)"])
    assert (g.lat, g.lon, g.depth_m) == (-28.7199775, 113.79, 1.3)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 1000.0)
    assert g.geo_source == GEO_1M
    # gebco_bathymetry == 0.0 (shoreline) is not a depth
    g2 = a.resolve_geo(got["RLS_Abrolhos Islands_2013/912354071/WA154_GER4.5m171113TurtleBay1  (1)"])
    assert (g2.lat, g2.lon, g2.depth_m) == (-28.4299775, 113.73, None)
    assert (g2.geo_precision, g2.geo_inferred, g2.geo_uncertainty_m) == ("station", True, 1000.0)


# ------------------------------------------------------------ 1M: audit mode with the U-tier FK* rows
def test_all_tiers_fk_rows_are_u_and_geo_logic_holds(tmp_path):
    a = make_adapter(tmp_path, all_tiers=True)
    got = by_id(a.discover())
    assert len(got) == 9
    s353 = [c for i, c in got.items() if i.startswith("FK200429/FK200429_S0353/")]
    assert len(s353) == 3
    for c in s353:
        assert a.resolve_licence(c).tier == "U"  # CC-BY-4.0 in the table, but CC BY-NC-SA 4.0 at origin
        g = a.resolve_geo(c)
        assert (g.lat, g.lon, g.depth_m) == (-14.4974831, 146.31264484, 1919.9)
        assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("station", True, 2000.0)
    c = got["FK200802/FK200802_S0380/FK200802_FK200802_S0380_20200816T052227900002_AUTO_5S_S5K"]
    assert c.media_url == "https://soi-egress.storage.googleapis.com/FK200802/Subastian/FK200802_S0380/Squidle_Framegrabs/FK200802_FK200802_S0380_20200816T052227900002_AUTO_5S_S5K.jpg"
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (-15.36099238, 145.80320994, 578.8)
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("image", False, None)


# --------------------------------------------------------------------------- Labelled (lon/lat swapped)
def test_labelled_dedup_swapped_columns_and_geo(tmp_path):
    a = make_adapter(tmp_path, subset="labelled")
    cands = list(a.discover())
    assert len(cands) == 7  # 8 label rows, two of them for the same Bastos image
    got = by_id(cands)
    c = got["Bastos/A_001_margem/A_001_margem"]
    assert c.media_url == f"{IMG}/Bastos/A_001_margem/A_001_margem.jpg" and c.ext == "jpg"
    assert c.timestamp == "2018-01-01T00:00:00+00:00"
    g = a.resolve_geo(c)
    assert (g.lat, g.lon, g.depth_m) == (-20.05703136, -39.84970526, 52.0)  # not swapped
    assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m) == ("image", False, None)
    assert g.geo_source == GEO_LAB
    lic_ = a.resolve_licence(c)
    assert lic_.tier == "B" and lic_.name == "CC-BY-4.0" and lic_.level == "record"
    assert "Menandro, P.S." in lic_.attribution and "BenthicNet-URLs" in lic_.attribution

    bof = got["Bay_of_Fundy_2019/BoF_001/20170413_BoF_001_4K_133626_040"]
    assert bof.ext == "tif" and bof.timestamp == "2017-04-13T13:36:26+00:00"
    g = a.resolve_geo(bof)
    assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_inferred) == (44.93015667, -65.59712833, 72.1, "image", False)

    s1 = a.resolve_geo(got["Bedford_2017/Bedford_Station1/Station1_DSC0233"])
    assert (s1.lat, s1.lon, s1.depth_m) == (44.6814333357, -63.6363000002, 35.3)
    assert (s1.geo_precision, s1.geo_inferred, s1.geo_uncertainty_m) == ("station", True, 1000.0)
    assert a.resolve_geo(got["Bedford_2017/Bedford_Station1/Station1_DSC0234"]).geo_precision == "station"
    s10 = a.resolve_geo(got["Bedford_2017/Bedford_Station10/Station10_DSC0325"])
    assert (s10.lat, s10.lon, s10.depth_m) == (44.680999999, -63.6193999981, 21.9)
    assert (s10.geo_precision, s10.geo_inferred, s10.geo_uncertainty_m) == ("station", True, 1000.0)  # dataset mostly shared

    ch = a.resolve_geo(got["Chesterfield/CI_01/CI_01_H00001"])
    assert (ch.lat, ch.lon, ch.depth_m, ch.geo_precision) == (63.28095333, -90.54985167, 49.3, "image")
    assert a.resolve_licence(got["Chesterfield/CI_01/CI_01_H00001"]).tier == "B"


def test_subset_both_does_not_repeat_images(tmp_path):
    a = make_adapter(tmp_path, subset="both")
    ids = [c.item_id for c in a.discover()]
    assert len(ids) == 4 + 7 and len(set(ids)) == len(ids)
    assert [i for i in ids[:4]] == [c.item_id for c in make_adapter(tmp_path / "x").discover()]  # 1M first


# --------------------------------------------------------------------------------- licence tiers
@pytest.fixture
def lic_adapter(tmp_path):
    return make_adapter(tmp_path, seed=("table",))


@pytest.mark.parametrize(
    "dataset,source,tier,name_start",
    [
        ("Hawaii_Archipelago_2019", "NOAA", "A", "U.S. Public Domain"),
        ("Tortugas_2009", "USGS", "A", "U.S. Public Domain"),
        ("nrcan-2001ROPOS", "NRCan", "B", "Open Government Licence - Canada"),
        ("CatlinSeaview_PAC_AUS", "XL Catlin Seaview Survey", "B", "CC-BY-3.0"),
        ("pangaea-73613", "PANGAEA", "B", "CC-BY-3.0"),
        ("NGU_2014", "NGU", "B", "CC-BY-4.0"),
        ("pangaea-865438", "PANGAEA", "X", "CC-BY-NC-3.0"),
        ("Doc Ricketts", "FathomNet", "X", "CC-BY-NC-ND-4.0"),
        ("fathomnet_misc", "FathomNet", "X", "CC-BY-NC-ND-4.0"),  # lower-case tar name, case-insensitive join
        ("FK200429-mgds", "MGDS", "X", "CC-BY-NC-SA-3.0 US"),
        ("LMG1311", "USAP-DC", "X", "CC-BY-NC-4.0"),
        ("FK200802", "SQUIDLE+", "U", "CC-BY-4.0 (BenthicNet table); Schmidt Ocean"),
        ("fk180731", "SQUIDLE+", "U", "not listed"),  # unlisted and an SOI cruise
        ("RLS_Coral Sea_2022", "SQUIDLE+", "U", "not listed"),
        ("wa_peel-harvey_x", "SQUIDLE+", "U", "not listed"),
        ("SomeNewSet", "FathomNet", "X", "not stated"),  # safety net on `source`
    ],
)
def test_licence_tier_per_dataset(lic_adapter, dataset, source, tier, name_start):
    cand = Candidate(
        "benthicnet", f"{dataset}/s/i", "image", "https://example.invalid/i.jpg", "o",
        extra={"dataset": dataset, "bn_source": source, "site": "s", "image": "i", "url": "http://example.invalid/i.jpg"},
    )
    got = lic_adapter.resolve_licence(cand)
    assert got.tier == tier
    assert got.name.startswith(name_start)
    assert got.level in ("record", "collection")


def test_licence_table_is_decoded_as_cp1252(lic_adapter):
    table = lic_adapter._licence_table()
    assert len(table) == 20
    assert "González-Rivero" in table["catlinseaview_pac_aus"]["citation"]
    assert table["fathomnet_misc"]["tier"] == "X" and table["hawaii_archipelago_2019"]["tier"] == "A"


def test_pangaea_set_missing_from_table_is_read_at_record_level(tmp_path):
    a = make_adapter(tmp_path, seed=("table",), resolve_pangaea=True)
    # licence and citation blocks of https://doi.pangaea.de/10.1594/PANGAEA.615784?format=metainfo_xml
    (a.ctx.layout.raw / "pangaea_615784_metainfo.xml").write_text(
        '<md:MetaData><md:citation id="dataset615784">'
        "<md:author><md:lastName>Schewe</md:lastName><md:firstName>Ingo</md:firstName><md:URI>https://www.awi.de/a</md:URI></md:author>"
        "<md:author><md:lastName>Soltwedel</md:lastName><md:firstName>Thomas</md:firstName><md:URI>https://www.awi.de/b</md:URI></md:author>"
        "<md:year>2007</md:year><md:title>Sea-bed photographs (benthos) from the AWI-Hausgarten area along OFOS profile PS62/161-3</md:title>"
        "<md:URI>https://doi.org/10.1594/PANGAEA.615784</md:URI></md:citation>"
        '<md:license id="license101"><md:label>CC-BY-3.0</md:label><md:name>Creative Commons Attribution 3.0 Unported</md:name>'
        "<md:URI>https://creativecommons.org/licenses/by/3.0/</md:URI></md:license></md:MetaData>",
        encoding="utf-8",
    )
    (a.ctx.layout.raw / "pangaea_907013_metainfo.xml").write_text(
        '<md:MetaData><md:license id="l"><md:label>CC-BY-NC-4.0</md:label><md:URI>https://creativecommons.org/licenses/by-nc/4.0/</md:URI></md:license></md:MetaData>',
        encoding="utf-8",
    )

    def make(ds):
        return Candidate("benthicnet", f"{ds}/s/i", "image", "https://e.invalid/i.jpg", "o",
                         extra={"dataset": ds, "bn_source": "PANGAEA", "site": "s", "image": "i", "url": "http://e.invalid/i.jpg"})

    got = a.resolve_licence(make("pangaea-615784"))
    assert (got.tier, got.level, got.name) == ("B", "record", "CC-BY-3.0")
    assert got.url == "https://creativecommons.org/licenses/by/3.0/"
    assert "Schewe, I., Soltwedel, T. (2007): Sea-bed photographs" in got.attribution
    assert "PANGAEA, https://doi.org/10.1594/PANGAEA.615784" in got.attribution
    assert a.resolve_licence(make("pangaea-907013")).tier == "X"  # a record-level NC licence never gets promoted
    # without the option the set stays U
    b = make_adapter(tmp_path / "off", seed=("table",))
    assert b.resolve_licence(make("pangaea-615784")).tier == "U"


# -------------------------------------------------------------------------- missing coordinates
def test_missing_or_invalid_coordinates_give_geo_none(tmp_path):
    # synthetic rows: real RLS row with empty latitude, with (0, 0), with lat 95, and one valid row
    header = CSV_1M.read_text().splitlines()[0]
    rows = [
        "http://rls.tpac.org.au/pq/1/a.JPG/,SQUIDLE+,RLS_Abrolhos (WA)_2021,1,a,,113.79,2021-04-19 00:00:00,-1.3,24.0",
        "http://rls.tpac.org.au/pq/1/b.JPG/,SQUIDLE+,RLS_Abrolhos (WA)_2021,1,b,0,0,2021-04-19 00:00:20,-1.3,24.0",
        "http://rls.tpac.org.au/pq/1/c.JPG/,SQUIDLE+,RLS_Abrolhos (WA)_2021,1,c,95,113.79,2021-04-19 00:00:40,-1.3,24.0",
        "http://rls.tpac.org.au/pq/1/d.JPG/,SQUIDLE+,RLS_Abrolhos (WA)_2021,1,d,-28.72,113.79,2021-04-19 00:01:00,-1.3,24.0",
    ]
    a = make_adapter(tmp_path, seed=("table",))
    (a.ctx.layout.raw / "benthicnet_unlabelled_sub.csv").write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    cands = list(a.discover())
    assert len(cands) == 4
    geos = {c.extra["image"]: a.resolve_geo(c) for c in cands}
    for k in "abc":
        g = geos[k]
        assert (g.lat, g.lon, g.depth_m, g.geo_precision, g.geo_inferred) == (None, None, None, "none", False)
        assert g.geo_source.startswith("benthicnet_unlabelled_sub.csv:latitude,longitude")
    assert geos["d"].geo_precision == "station" and geos["d"].lat == -28.72
    summary = json.loads((a.ctx.layout.metadata / "index_1m.json").read_text())
    assert summary["geo_precision_rows"] == {"station": 1, "none": 3}


def test_region_precision_when_a_multi_site_dataset_has_one_coordinate(tmp_path):
    # synthetic rows: two sites of one dataset sharing one coordinate
    header = CSV_1M.read_text().splitlines()[0]
    rows = [
        "http://e.invalid/1.jpg,NGU,NGU_2014,siteA,1,60.5,5.5,2014-01-01 00:00:00,-100.0,1",
        "http://e.invalid/2.jpg,NGU,NGU_2014,siteB,2,60.5,5.5,2014-01-02 00:00:00,-100.0,1",
    ]
    a = make_adapter(tmp_path, seed=("table",))
    (a.ctx.layout.raw / "benthicnet_unlabelled_sub.csv").write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    for c in a.discover():
        g = a.resolve_geo(c)
        assert (g.geo_precision, g.geo_inferred, g.geo_uncertainty_m, g.depth_m) == ("region", True, None, 100.0)


# ------------------------------------------------------------------------------------- ordering
def _synthetic_rows():
    rows = []

    def add(dataset, source, site, n, lat0):
        for k in range(n):
            rows.append(f"http://e.invalid/{dataset}/{site}/{k}.jpg,{source},{dataset},{site},{k},{lat0 + k * 0.001},5.0,2020-01-{k + 1:02d} 00:00:00,-50.0,1")

    add("Bay_of_Fundy_2019", "SEAM", "s1", 8, 44.0)
    add("Bay_of_Fundy_2019", "SEAM", "s2", 2, 45.0)
    add("Bastos", "LaboGeo (Marine Geosciences Lab/UFES)", "b1", 4, -20.0)
    add("Hawaii_Archipelago_2019", "NOAA", "h1", 6, 20.0)
    return rows


def test_spread_order_interleaves_groups_datasets_sites_and_time(tmp_path):
    header = CSV_1M.read_text().splitlines()[0]
    a = make_adapter(tmp_path, seed=("table",))
    (a.ctx.layout.raw / "benthicnet_unlabelled_sub.csv").write_text("\n".join([header, *_synthetic_rows()]) + "\n", encoding="utf-8")
    cands = list(a.discover())
    assert len(cands) == 20
    # the first picks come from three different source groups, largest share (sqrt of images) first
    assert [c.extra["dataset"] for c in cands[:3]] == ["Bay_of_Fundy_2019", "Hawaii_Archipelago_2019", "Bastos"]
    # round robin over the sites of a dataset
    bof = [c for c in cands if c.extra["dataset"] == "Bay_of_Fundy_2019"]
    assert {bof[0].extra["site"], bof[1].extra["site"]} == {"s1", "s2"}
    # evenly spaced in time inside a site: earliest, middle, then the quarters
    s1_days = [c.timestamp[8:10] for c in cands if c.extra["site"] == "s1"]
    assert s1_days[:4] == ["01", "05", "03", "07"]
    # deterministic
    b = make_adapter(tmp_path / "again", seed=("table",))
    (b.ctx.layout.raw / "benthicnet_unlabelled_sub.csv").write_text("\n".join([header, *_synthetic_rows()]) + "\n", encoding="utf-8")
    assert [c.item_id for c in b.discover()] == [c.item_id for c in cands]


def test_order_csv_keeps_file_order(tmp_path):
    header = CSV_1M.read_text().splitlines()[0]
    a = make_adapter(tmp_path, seed=("table",), order="csv")
    (a.ctx.layout.raw / "benthicnet_unlabelled_sub.csv").write_text("\n".join([header, *_synthetic_rows()]) + "\n", encoding="utf-8")
    ids = [c.item_id for c in a.discover()]
    assert ids[:3] == [f"Bay_of_Fundy_2019/s1/{k}" for k in range(3)]


def test_filters_and_always_dropped_sets(tmp_path):
    header = CSV_1M.read_text().splitlines()[0]
    rows = _synthetic_rows() + ["http://e.invalid/c.jpg,NRCan,nrcan-71014,s,c,60.0,-60.0,1990-01-01 00:00:00,-50.0,1"]
    seed = "\n".join([header, *rows]) + "\n"

    def run(path, **opts):
        a = make_adapter(path, seed=("table",), **opts)
        (a.ctx.layout.raw / "benthicnet_unlabelled_sub.csv").write_text(seed, encoding="utf-8")
        return list(a.discover())

    assert len(run(tmp_path / "all")) == 20  # nrcan-71014 (collages) is never yielded
    assert {c.extra["dataset"] for c in run(tmp_path / "s", sources="SEAM")} == {"Bay_of_Fundy_2019"}
    assert {c.extra["dataset"] for c in run(tmp_path / "x", exclude_datasets=["bastos"])} == {"Bay_of_Fundy_2019", "Hawaii_Archipelago_2019"}
    assert {c.extra["bn_source"] for c in run(tmp_path / "o", exclude_overlap=True)} == {"SEAM", "LaboGeo (Marine Geosciences Lab/UFES)"}


def test_helpers():
    assert bn.spread_perm(8) == (0, 4, 2, 6, 1, 5, 3, 7)
    assert bn.spread_perm(3) == (0, 2, 1) and bn.spread_perm(1) == (0,) and bn.spread_perm(0) == ()
    share = bn.allocate_weights({"Catlin": 1_000_000, "NGU": 10_000, "PANGAEA": 100}, capped=["catlin"])
    assert share["Catlin"] == pytest.approx(0.15) and sum(share.values()) == pytest.approx(1.0)
    assert share["NGU"] > share["PANGAEA"] > 0
    assert bn.norm_url("http://rls.tpac.org.au/pq/1/a.JPG/") == "https://rls.tpac.org.au/pq/1/a.JPG"
    assert bn.sanitize(" Fundy: Bay/2019? ") == "Fundy Bay-2019"
    assert bn.sanitize("Café.") == "Caf"
    assert bn.url_ext("http://x/y/z.TIF") == "tif" and bn.url_ext("http://x/y/z.JPG/") == "jpg" and bn.url_ext("http://x/y") == "jpg"


# ----------------------------------------------------------------------------- readiness / estimate
def test_check_ready(tmp_path):
    assert make_adapter(tmp_path).check_ready() == []
    problems = make_adapter(tmp_path / "x", subset="11m").check_ready()
    assert len(problems) == 1 and "no published image list" in problems[0]
    assert make_adapter(tmp_path / "y", media="zip").check_ready()


def test_estimate_uses_the_cached_size_listing(tmp_path):
    a = make_adapter(tmp_path)
    (a.ctx.layout.raw / "frdr_tar_sizes_unlabelled.json").write_text(
        json.dumps({"contents": [
            {"name": "Bastos.tar", "size": 45465600},
            {"name": "FathomNet_misc.tar", "size": 1000},  # both case variants exist on FRDR and must both be counted
            {"name": "fathomnet_misc.tar", "size": 2000},
            {"name": "x.txt", "size": 5},
        ]}), encoding="utf-8"
    )
    est = a.estimate()
    assert est["images_1m"] == 1_345_096 and est["tars_1m"] == 3 and est["tar_gb_1m"] == 0.05
    assert a._tar_lookup("unlabelled", "FathomNet_misc.tar") == ("FathomNet_misc.tar", 1000)
    assert a._tar_lookup("unlabelled", "fathomnet_misc.tar") == ("fathomnet_misc.tar", 2000)
    assert a._tar_lookup("unlabelled", "BASTOS.tar") == ("Bastos.tar", 45465600) and a._tar_lookup("unlabelled", "nope.tar") is None


# --------------------------------------------------------------------- zip member over Range requests
class _Resp:
    def __init__(self, data, status=206, headers=None):
        self.data, self.status_code, self.headers = data, status, headers or {}

    def iter_content(self, n):
        for i in range(0, len(self.data), 7):  # tiny odd chunks to exercise the streaming path
            yield self.data[i : i + 7]

    def close(self):
        pass


class FakeZipHttp(Http):
    """Serves one zip over HEAD / Range like the FRDR Globus endpoint (no suffix ranges)."""

    def __init__(self, blob):
        super().__init__(dry_run=True)
        self.blob, self.ranges = blob, []

    def head(self, url, **kw):
        return _Resp(b"", 200, {"Content-Length": str(len(self.blob))})

    def get_range(self, url, start, end, *, kind="metadata"):
        self.ranges.append((start, end))
        return self.blob[start : end + 1]

    def request(self, method, url, *, kind="metadata", **kw):
        a, b = kw["headers"]["Range"].removeprefix("bytes=").split("-")
        self.ranges.append((int(a), int(b)))
        return _Resp(self.blob[int(a) : int(b) + 1])


def _zip_blob():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("finalized_csvs/labelled_counts.csv", "label,count\nsand,1\n" * 50)
        z.writestr("finalized_csvs/benthicnet_labelled.csv", CSV_LAB.read_bytes())
        z.writestr("finalized_csvs/benthicnet_unlabelled_sub.csv", CSV_1M.read_bytes())
    return buf.getvalue()


def test_zip_member_is_read_with_range_requests(tmp_path):
    blob = _zip_blob()
    http = FakeZipHttp(blob)
    a = make_adapter(tmp_path, seed=("table",), http=http)
    cands = list(a.discover())
    assert len(cands) == 4
    assert (a.ctx.layout.raw / "benthicnet_unlabelled_sub.csv").read_bytes() == CSV_1M.read_bytes()
    assert http.ranges[0] == (max(0, len(blob) - 65536), len(blob) - 1)  # explicit offsets, no suffix range
    member_bytes = sum(b - a_ + 1 for a_, b in http.ranges[1:])
    assert member_bytes < len(blob)  # only the wanted member (plus its local header) was requested

    lab = make_adapter(tmp_path / "lab", seed=("table",), http=FakeZipHttp(blob), subset="labelled")
    got = by_id(lab.discover())
    assert len(got) == 7
    derived = lab.ctx.layout.raw / "benthicnet_labelled_images.csv"
    # canonical column order, values taken by header name (the Labelled member has longitude before latitude)
    assert derived.read_text().splitlines()[0] == "url,source,dataset,site,image,latitude,longitude,datetime,gebco_bathymetry"
    assert ",-20.05703136,-39.84970526," in derived.read_text()
    assert len(derived.read_text().splitlines()) == 8
    g = lab.resolve_geo(got["Bastos/A_002_margem/A_002_margem"])
    assert (g.lat, g.lon, g.depth_m, g.geo_precision) == (-20.04130325, -39.86042929, 51.0, "image")


def test_zip_member_crc_failure_is_an_error(tmp_path):
    blob = bytearray(_zip_blob())
    # corrupt the stored CRC of the 1M member in the central directory (the last occurrence of its name)
    j = bytes(blob).rfind(b"finalized_csvs/benthicnet_unlabelled_sub.csv")
    blob[j - 46 + 16] ^= 0xFF
    a = make_adapter(tmp_path, seed=("table",), http=FakeZipHttp(bytes(blob)))
    with pytest.raises(RuntimeError, match="CRC"):
        list(a.discover())
    assert not (a.ctx.layout.raw / "benthicnet_unlabelled_sub.csv").exists()


def test_local_dir_with_a_downloaded_zip_needs_no_network(tmp_path):
    local = tmp_path / "from_human"
    local.mkdir()
    (local / "finalized_csvs.zip").write_bytes(_zip_blob())
    shutil.copyfile(TABLE, local / "all_licenses_refs.csv")
    a = make_adapter(tmp_path / "run", seed=(), local_dir=str(local))
    assert len(list(a.discover())) == 4
    assert (a.ctx.layout.raw / "all_licenses_refs.csv").read_bytes() == TABLE.read_bytes()
    b = make_adapter(tmp_path / "run2", seed=(), local_dir=str(local), subset="labelled")
    assert len(list(b.discover())) == 7


# ------------------------------------------------------------------------------------------- media
def test_media_original_route_and_content_sniff(tmp_path):
    a = make_adapter(tmp_path)
    c = next(iter(a.discover()))
    ref = a.resolve_media(c)
    assert ref.url == c.media_url and ref.ext == "jpg" and c.extra["image_route"] == "original"

    calls = []

    def fake_download(url, dest, **kw):
        calls.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"<html>login</html>" if url.startswith("https") else b"\xff\xd8\xff\xe0jpegdata")
        return dest.stat().st_size, "sha"

    a.http.download = fake_download
    dest = tmp_path / "out" / "x.jpg"
    # https answers with an HTML page: refused and removed; the listed http URL is not retried after a sniff failure
    with pytest.raises(HttpError, match="not an image"):
        a.fetch_media(c, ref, dest)
    assert not dest.exists() and calls == [c.media_url]

    def https_fails(url, dest, **kw):
        if url.startswith("https"):
            calls.append(url)
            raise HttpError(url, None, "tls")
        return fake_download(url, dest)  # the listed http:// URL

    a.http.download = https_fails
    calls.clear()
    n, _sha = a.fetch_media(c, ref, dest)
    assert n > 0 and calls == [c.media_url, c.extra["url"]] and dest.exists()


def _tar_bytes(members):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_media_tar_route_extracts_the_member_and_reuses_the_tar(tmp_path):
    a = make_adapter(tmp_path, subset="labelled", media="tar")
    (a.ctx.layout.raw / "frdr_tar_sizes_labelled.json").write_text(
        json.dumps({"contents": [{"name": "Bastos.tar", "size": 45465600}]}), encoding="utf-8"
    )
    got = by_id(a.discover())
    c = got["Bastos/A_001_margem/A_001_margem"]
    ref = a.resolve_media(c)
    assert ref.url == f"{bn.FILES}/01_BenthicNet/images/labelled/individual_dataset_tars/Bastos.tar"
    assert ref.ext == "jpg" and ref.expected_bytes == 45465600
    assert ref.extra["member"] == "Bastos/A_001_margem/A_001_margem.jpg" and c.extra["image_route"] == "tar"

    img1, img2 = b"\xff\xd8\xff\xe0one", b"\xff\xd8\xff\xe0two-two"
    tar = _tar_bytes({"Bastos/A_001_margem/A_001_margem.jpg": img1, "Bastos/A_002_margem/A_002_margem.jpg": img2})
    downloads = []

    def fake_download(url, dest, **kw):
        downloads.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(tar)
        return len(tar), "sha"

    a.http.download = fake_download
    dest = tmp_path / "out" / "a.jpg"
    n, sha = a.fetch_media(c, ref, dest)
    assert dest.read_bytes() == img1 and n == len(img1) and sha == hashlib.sha256(img1).hexdigest()
    ref2 = a.resolve_media(got["Bastos/A_002_margem/A_002_margem"])
    dest2 = tmp_path / "out" / "b.jpg"
    a.fetch_media(got["Bastos/A_002_margem/A_002_margem"], ref2, dest2)
    assert dest2.read_bytes() == img2 and len(downloads) == 1  # the tar is downloaded once
    assert any((tmp_path / "benthicnet" / "tars" / "labelled").iterdir())

    missing = got["Bedford_2017/Bedford_Station1/Station1_DSC0233"]
    ref3 = a.resolve_media(missing)  # no Bedford tar in the size listing: the URL is still built from the name
    assert ref3.url.endswith("/Bedford_2017.tar") and ref3.expected_bytes is None


def test_media_auto_route_uses_tar_only_for_small_tars(tmp_path):
    a = make_adapter(tmp_path, subset="labelled", media="auto")
    (a.ctx.layout.raw / "frdr_tar_sizes_labelled.json").write_text(
        json.dumps({"contents": [{"name": "Bastos.tar", "size": 45465600}]}), encoding="utf-8"
    )
    got = by_id(a.discover())
    assert a.resolve_media(got["Bastos/A_001_margem/A_001_margem"]).extra["route"] == "tar"
    assert a.resolve_media(got["Bay_of_Fundy_2019/BoF_001/20170413_BoF_001_4K_133626_040"]).extra["route"] == "original"
    small = make_adapter(tmp_path / "s", subset="labelled", media="auto", tar_max_mb=10)
    (small.ctx.layout.raw / "frdr_tar_sizes_labelled.json").write_text(
        json.dumps({"contents": [{"name": "Bastos.tar", "size": 45465600}]}), encoding="utf-8"
    )
    assert small.resolve_media(by_id(small.discover())["Bastos/A_001_margem/A_001_margem"]).extra["route"] == "original"


# ----------------------------------------------------------------------------- through the runner
def test_runner_dry_run_on_the_fixture(tmp_path):
    cfg = load_config(None, data_root=tmp_path)
    layout = DatasetLayout(tmp_path, "benthicnet").ensure()
    shutil.copyfile(TABLE, layout.raw / "all_licenses_refs.csv")
    shutil.copyfile(CSV_1M, layout.raw / "benthicnet_unlabelled_sub.csv")
    (layout.raw / "frdr_tar_sizes_unlabelled.json").write_text(json.dumps({"contents": []}), encoding="utf-8")
    s = run_source(cfg, "benthicnet", "dry-run", options={"subset": "1m", "resolve_pangaea": False})
    assert s.error is None and s.not_ready == []
    assert (s.candidates, s.selected) == (4, 4)
    assert s.selected_by_tier == {"B": 4} and s.selected_by_precision == {"station": 4}
    assert s.bbox == [113.73, -28.7199775, 113.79, -28.4299775]
    # the same fixture with all_tiers: the runner itself drops the five FK* rows (tier U) and nothing is downloaded
    s2 = run_source(cfg, "benthicnet", "dry-run", options={"subset": "1m", "resolve_pangaea": False, "all_tiers": True})
    assert (s2.candidates, s2.selected) == (9, 4) and s2.dropped == {"tier U not selected": 5}
    s3 = run_source(cfg, "benthicnet", "dry-run", options={"subset": "11m"})
    assert s3.error and "no published image list" in s3.error and s3.candidates == 0
