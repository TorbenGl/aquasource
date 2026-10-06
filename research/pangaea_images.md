# PANGAEA image datasets (seed DOIs + discovery) (`pangaea_images`)
Status: researched · researched 2026-10-06

## Summary
PANGAEA (AWI/MARUM, Germany) publishes seafloor imagery as DOI'd "dataset publication series". Each child dataset is one camera deployment (OFOS/OFOBS towed camera, AUV, ROV or diver transect), and its tab-separated table has one row per image: `Date/Time`, usually `Latitude`/`Longitude`/`Depth water [m]`, and a media URL or filename. The 7 seeds (Arctic, Antarctic, Pacific abyss) are all CC BY (six CC-BY-4.0, one CC-BY-3.0) → **tier B**. They hold ~447 k open images (~430 GB) plus one 3.45 GB ROV video, and ~17 k more (SO295, 994607) are under moratorium until 2027-04-22. About 99 % of the open seed images have **per-image coordinates** (USBL/AUV navigation, WGS 84); the rest fall back to the PANGAEA event position (station). A discovery query on PANGAEA's Elasticsearch index finds 1,121 open CC-BY/CC0 underwater image/video datasets: roughly 300 k more images with per-image coordinates (other cruises, Great Barrier Reef diver transects) and ~300 k at station or fixed-site level (MOSAiC under-ice ROV, OBSEA). Verdict: go, provided the pipeline throttles hard, handles tape staging, filters descent/deck frames and dedupes derived versions.

## Entry points
- Portal / landing pages: https://www.pangaea.de/ · `https://doi.pangaea.de/10.1594/PANGAEA.<id>` (DOI `10.1594/PANGAEA.<id>`)
- Seed DOIs (verified): 10.1594/PANGAEA.989682, .898338, .994607, .935856, .882349, .911904, .936205
- Per-dataset formats (append `?format=`): `textfile` (TSV data table, the main source), `metadata_panmd` (PANGAEA XML: columns, events, licence, `technicalInfo` with `collectionChilds`, `moratoriumUntil`, `staticURL`), `metadata_jsonld` (schema.org/Croissant: `license`, `conditionsOfAccess`), `citation_text`, `linkset_json`, `zip` (zip of the child **tables only** for a series, e.g. 57 KB for 989682)
- Media hosts: `https://hs.pangaea.de/...` (absolute URLs in `URL image` / `URL raw` / `URL movie` columns and in `staticURL`), `https://download.pangaea.de/dataset/<child_id>/files/<filename>` (bare filenames in `IMAGE`, `IMAGE water`, `Binary`, `VIDEO`, `Metadata` columns), `https://store.pangaea.de/...` (thumbnails, `URL thumb`)
- Search: Elasticsearch `https://ws.pangaea.de/es/pangaea/panmd/_search` (GET `q=` or POST query DSL. Fields used: `techKeyword`, `parentIdDataSet`, `sp-loginOption`, `nDataPoints`, `xml` (full pan_md), `meanPosition`, `agg-method`). Simple search: `https://www.pangaea.de/advanced/search.php?q=...&count=..&offset=..` (used by pangaeapy `PanQuery`)
- OAI-PMH: `https://ws.pangaea.de/oai/provider?verb=GetRecord&metadataPrefix=pan_md&identifier=oai:pangaea.de:doi:10.1594/PANGAEA.<id>`
- Python client: `pangaeapy` 1.1.3 (PyPI, 2026-09-16), https://github.com/pangaea-data-publisher/pangaeapy
- Terms of use: https://www.pangaea.de/about/terms.php · Geocode definitions: https://wiki.pangaea.de/wiki/Geocode

## Licence
- Tier: **B** for all 7 seeds (CC-BY-4.0 ×6, CC-BY-3.0 ×1). Assign the tier **per child DOI** from the licence block: `license21` CC-BY-4.0 / `license101` CC-BY-3.0 → B. `license29` CC0 → A. `license22`/`license102` CC-BY-SA → C. `license23`/`103` ND and `license24`-`26`/`104`-`106` NC → Excluded. `license108` "UNKNOWN" / `license107` BSRN / missing → U. (IDs are the `techKeyword` values in the ES index, checked against each record's `<md:license>` label.) Mixed series exist. Example: series 702107 has 37 CC-BY-3.0 children and 1 CC-BY-NC-3.0 video child, so never inherit the licence from the parent.
- Licence text (quote) + level read (file / record / collection) + URL:
  - Record level (each child data table header, and `<md:license>` in pan_md): "License: Creative Commons Attribution 4.0 International (CC-BY-4.0) (URI: https://creativecommons.org/licenses/by/4.0/)". Read at https://doi.pangaea.de/10.1594/PANGAEA.989683?format=textfile, and the same text in 911902, 936138, 935854, 989684, 935896 and in the pan_md of 898338 and 994576.
  - Record level, 882349 children: "License: Creative Commons Attribution 3.0 Unported (CC-BY-3.0) (URI: https://creativecommons.org/licenses/by/3.0/)". Read at https://doi.pangaea.de/10.1594/PANGAEA.879298?format=textfile.
  - Collection level (platform ToU, consistent with the records): "By submitting research content and metadata to the PANGAEA platform the content will be published under the Creative Commons license CC0 for metadata and CC-BY for data. Exceptions have to be negotiated on an individual basis with PANGAEA. Once a license has been issued, it cannot be changed retroactively." (https://www.pangaea.de/about/terms.php, §6.2)
  - No file-level licence exists. Image EXIF `Copyright:` is empty in the MSM77 sidecar files that were checked.
- Attribution / citation text to store with every sample: the child's `?format=citation_text` string plus licence URI. Example (911902): "Purser, Autun; Hehemann, Laura; Dreutter, Simon; Dorschel, Boris; Nordhausen, Axel (2020): Seabed photographs taken along OFOBS profile PS118_6-9 during RV POLARSTERN cruise PS118 [dataset]. Alfred Wegener Institute, Helmholtz Centre for Polar and Marine Research, Bremerhaven, PANGAEA, https://doi.org/10.1594/PANGAEA.911902, In: Purser, A et al. (2020): OFOBS Seafloor images from the Antarctic Peninsula and Powell Basin, collected during RV POLARSTERN cruise PS118 [dataset publication series]. ... https://doi.org/10.1594/PANGAEA.911904". Store `doi`, `parent_doi`, `citation`, `licence_uri`, `media_url` per sample.
- Embargo / moratorium / special terms:
  - Moratorium: pan_md `technicalInfo` `loginOption = "access rights needed"` (ES `sp-loginOption: 3`) plus `moratoriumUntil`. JSON-LD `conditionsOfAccess: "access rights needed"`, `isAccessibleForFree: false`. `?format=textfile` returns **HTTP 401** with `WWW-Authenticate: Bearer realm="https://www.pangaea.de/user/login.php"`. Seed **994607** (SO295, 14 children) is under moratorium until **2027-04-22**. ToU: "The user can request a moratorium of a maximum of two years until the publication of the research contents - after this time research contents will be automatically published by PANGAEA." Metadata stays open ("Metadata is always freely accessible").
  - Bulk-access clause (ToU §API): "PANGAEA is entitled at its own discretion to technically limit the retrieval and download of research contents ... Requests significantly beyond the average number of access attempts per time unit by other users of PANGAEA or mass download of metadata and associated data e.g. for the purpose of content duplication ... Such exceeding inquiries will automatically lead to error messages and/or a forced disconnection from the service unless prior authorization from PANGAEA is requested". A full-archive harvest therefore needs prior authorisation (see Manual steps).
  - `allfiles.zip` / `allfiles.tar` per child need a PANGAEA account (HTTP 401, Bearer token). Single files need no login.

## Media
- Seed DOIs (all counts verified from the tables or the ES `nDataPoints`):

| DOI | Title (short) | Licence | Children | Images / media | Media column → host | Coordinates | Depth | Access |
|---|---|---|---|---|---|---|---|---|
| 989682 | OFOS seafloor images, Fram Strait (HAUSGARTEN), MSM77, Sep 2018 | CC-BY-4.0 | 3 (989683, 989684, 989732) | 2,114 JPG (482+762+870; TIMER 1,343 / HOTKEY 771), ~5 MB each, Canon EOS 5D Mk III (5760×3840), plus 1 EXIF/Posidonia `.txt` sidecar per image | `IMAGE water` + `Metadata` filenames → download.pangaea.de (tape) | 989684/989732: `Latitude`,`Longitude`,`Coord unc [m]`. 989683: **none** (event only) | `Depth water [m]` **negative sign** | open |
| 898338 | ROV SPRINT sea-bed video HE153/1274-3, W Svalbard shelf, 2001-09-07 | CC-BY-4.0 | child of series 898362 (24 MPEGs + 1 `URL movie` table, 62.7 GB total) | 1 MPEG-2, 3,454,525,444 B, ~75 min | `staticURL` https://hs.pangaea.de/Movies/HE/HE153/HE153_1274-3.mpeg (tape) | event start/end (ship's data system). 1-min track file https://hs.pangaea.de/Images/Benthos/HE/HE153/HE153_1274/HE153_1274_track.txt | event elevation 402-431 m | open |
| 994607 | iFDOs of seafloor images, polymetallic nodules, SO295, Nov-Dec 2022 | CC-BY-4.0 | 14 (994576-994593) | ~16,991 (est.) | `IMAGE water` | `Latitude`,`Longitude`,`Depth water [m]`,`Coord unc [m]` (from pan_md) | yes | **moratorium until 2027-04-22** (401) |
| 935856 | OFOS seafloor images, CCZ nodule field (MiningImpact), SO268/1+2, Mar-May 2019 | CC-BY-4.0 | 12 | 41,088 JPG, ~3.5 MB | `Binary` filenames → download.pangaea.de | `Longitude`,`Latitude` (note the order). Child 935896 has **constant** position ("Positioning failed for this dive") | `Depth water [m]` (missing in 935896) | open |
| 882349 | AUV ABYSS seafloor images + context, SO239 & SO242/1 (CCZ, Peru Basin), Mar-Aug 2015 | **CC-BY-3.0** | 21 | ~380 k JPG (1 img/s), ~373 KB, 3072×2304 (undistorted from fisheye to 90° FOV) | `URL image` absolute → hs.pangaea.de | `Latitude`,`Longitude` | `Depth water [m]` + `Distance [m]` (altitude), `Ground vis [#]`, `Img brightness` | open |
| 911904 | OFOBS images, Antarctic Peninsula & Powell Basin, PS118, Mar-Apr 2019 | CC-BY-4.0 | 11 | ~12.6 k JPG, ~5.1 MB, 5760×3840 (+ `.txt` via `URL file`) | `URL image`, `URL file` → hs.pangaea.de | `Latitude`,`Longitude` | `Depth water [m]` | open |
| 936205 | OFOBS images, Weddell Sea (Filchner), PS124, Feb-Mar 2021 | CC-BY-4.0 | 16 | ~11.7 k JPG ("~11,700" per abstract), ~5-6.5 MB | `IMAGE` filenames → download.pangaea.de | `Latitude`,`Longitude` | `Depth water [m]` | open |

  - Totals (open seeds): ~447 k images, ~430 GB (AUV ~140 GB, SO268 ~145 GB, PS118 ~65 GB, PS124 ~70 GB, MSM77 ~10 GB), plus 3.45 GB of video (62.7 GB for the full HE153 series). Time range 2001 → 2021 (2022 when SO295 opens).
  - Formats: JPEG (OFOS/OFOBS/AUV), TIFF ~24 MB (`URL raw` in 1997-2004 legacy OFOS), MPEG-2 (ROV videos), MP4/MOV in newer `VIDEO`/`VIDEO water` columns.
- Filters needed:
  - **Descent / ascent / on-deck frames**: towed systems start shooting before touchdown. Examples: 935854 starts at `Depth water` 1985.6 m with a seafloor depth of ~4,070 m. 936138 has `SW_RELEASER_...` frames at 136 m. In 989684, rows 1-25 have no position and come before the event time, so they are probably deck or descent frames. Rule: drop rows where depth < 0.9 × median depth of the child, drop rows without position that come before the event `DATE/TIME`, and drop filenames starting with `SW_`.
  - **AUV**: use `Ground vis [#]` = 1 only. 216 of 1,491 rows in 879298 are 0. Also check `Distance [m]` (altitude, target 7.5 m) ≤ ~12 m and `Img brightness`.
  - **Black/blank frames**: run a luminance threshold. These are dark-boundary images even after undistortion (882349 abstract).
  - **Duplicates / derived versions** (dedupe by origin URL and by `(cruise, event, timestamp)`):
    - 957274 "Analysis-ready optical underwater images ... SO268/1 and SO268/2" (Mbani & Greinert 2023) = processed copies of seed 935856.
    - 912471 (HAUSGARTEN litter) and 849291/897047 re-reference OFOS images published elsewhere.
    - GBR "Benthic and substrate cover" series (892623, 891736) and "Georeferenced photographs" series (877578, 891505) point at the same photos.
    - 882349 has an "Other version: Gallery of sea-bed photographs" (pangaea.de/helpers/Benthos.php) and annotations at https://annotate.geomar.de/volumes/259.
    - PS118 is also described in ESSD (https://doi.org/10.5194/essd-13-609-2021, same files).
  - Not underwater: ES hits for image parameters also include sky imagers, Parasound echograms, side-scan/multibeam "Binary" files, aerial DEM photos, ship webcams (PS122 Panomax), and core/microscope photos. Restrict to underwater platforms (see the discovery query) and exclude titles matching `side scan|bathymetr|multibeam|Parasound|quicklook|Sky Imager|aerial`.

## Geolocation
- Precision levels (open seed images): **image ≈ 99 %** (~443 k: 882349, 911904, 936205, 935856 except 935896, 989684, 989732). **station ≈ 1 %** (~4.4 k: 935896 constant position 3,923; 989683 482; the 25 position-less rows of 989684). The video 898338 is **station**. 994607 will be image-level once open.
- geo_source / CRS:
  - Per image: data-table columns `Latitude`, `Longitude` (PANGAEA GEOCODE 1600/1601). Wiki quote: "LATITUDE and LONGITUDE are given in decimal degree (positive for North, negative for South, WGS84). They are specified in each Event and can additionally expand the data tables and georeference individual samples more precisely." (https://wiki.pangaea.de/wiki/Geocode). Column order varies (`Longitude` comes first in 935856), so always map by header name.
  - Per station: header line `Event(s):` (`LATITUDE`/`LONGITUDE`/`ELEVATION`, or `LATITUDE START`/`END` etc.), equal to pan_md `<md:event>` `latitude`/`longitude`/`elevation` and `latitude2`/`longitude2`/`elevation2`. Multi-event tables carry an `Event` column; match on its label.
  - Depth: `Depth water [m]` (GEOCODE 1619, positive down by definition: "the water depth in which the measurement or sample was collected"). The MSM77 children serve it **negative** (e.g. -2361.4), so use `abs()`. Event `ELEVATION` is "Height/bottom depth relative to sea level ... negative below mean sea level", so depth = -ELEVATION.
  - Uncertainty: `Coord unc [m]` where present (MSM77, SO295: 1.6-5.5 m). Otherwise defaults: OFOS/OFOBS with USBL (Posidonia) 20 m. AUV 50 m. Ship-GPS positions (legacy 1997-2004 OFOS with `Course`/`Speed` GPS columns, and HE153 "Positions ... from the ship's automatic data recording system") use max(200, min(2000, 0.5 × depth)) m, a heuristic for layback. Station from a single event point: 4000 m (OFOS profiles are ~2-4 km long; for 935896 the logged position is 2.1 km from the event point). Station from a start/end event: half the start-end distance + 500 m.
- How a sample maps to its coordinate: one table row = one image. The media filename (or URL) and the coordinates sit in the same row. The child DOI is found from `collectionChilds` of the series (pan_md) or from ES `parentIdDataSet`. The download URL is the absolute `URL image`/`URL raw` value, or `https://download.pangaea.de/dataset/<child_id>/files/<filename>` for filename-type columns (`IMAGE`, `IMAGE water`, `Binary`, `VIDEO`, `Metadata`). For a video dataset (no table), the pan_md `staticURL` maps to the dataset's event. MSM77 `.txt` sidecars contain `Posidonia Latitude/Longitude` fields, but they were **empty** in the files checked (989683), so they add nothing.

### resolve_geo recipe
Input: one parsed table row `row` (dict keyed by the exact column header), plus dataset context `ds` parsed once per child. `ds` holds: `doi`; `events` (list of {label, lat, lon, lat2, lon2, elev, elev2, datetime}) parsed from the `Event(s):` header line (`LATITUDE: x * LONGITUDE: y * ... ELEVATION: -z m`, or the `START`/`END` variants) or from pan_md `<md:event>`; `comment` (header `Comment:` line); `platform` (event `METHOD/DEVICE`); `n_unique_pos` (number of distinct non-empty (Latitude, Longitude) pairs over all rows). For video datasets `row = {}`.
1. `num(x)`: strip; `""` → None; strip a leading PANGAEA QC flag character (`?*/#<>`); `float()`; on error return None.
2. `ev` = the event whose label equals `row.get("Event")`, else `ds.events[0]` if there is exactly one, else None.
3. `lat, lon = num(row.get("Latitude")), num(row.get("Longitude"))`. Treat the pair as invalid unless both are set, -90 ≤ lat ≤ 90, -180 ≤ lon ≤ 180, and not (0, 0).
4. `depth_m`: `d = num(row.get("Depth water [m]"))`. If d is set → `abs(d)`. Else if `ev` has elevation(s) → `-mean(elev, elev2)` when that value is > 0. Else None.
5. If the pair is valid **and** `ds.n_unique_pos > 1` **and** `"positioning failed"` is not in `ds.comment.lower()`: return `lat, lon, depth_m`, `geo_precision="image"`, `geo_inferred=False`, `geo_source="PANGAEA <doi> data table: Latitude/Longitude (WGS84)` (+ `/Depth water [m]` when used)`"`. For `geo_uncertainty_m` use `num(row["Coord unc [m]"])` if present, else 50 if the platform matches /autonomous underwater vehicle|AUV/, else 20 if it matches /OFOS|OFOBS|Ocean Floor Observation|ROV|remote/, else null.
6. If the pair is valid but constant per dataset (`n_unique_pos == 1`) or the comment says positioning failed: return that lat/lon and `depth_m`, `geo_precision="station"`, `geo_inferred=True`, `geo_source="PANGAEA <doi> data table Latitude/Longitude, constant for whole deployment (Comment: positioning failed)"`, `geo_uncertainty_m=4000`.
7. Else, if `ev` has lat/lon:
   - If lat2/lon2 are present: `lat, lon` = midpoint of start and end, and `unc = haversine(start, end)/2 + 500`.
   - Else: `lat, lon = ev.lat, ev.lon` and `unc = 4000`.
   - Return `geo_precision="station"`, `geo_inferred=True`, `geo_source="PANGAEA <doi> Event(s) <label> LATITUDE/LONGITUDE[ START/END] (event metadata)"`, `geo_uncertainty_m=round(unc)`.
   - Also set the flag `pre_event_no_position=True` when the row `Date/Time` < `ev.datetime`. The pipeline should drop such rows by default (deck/descent).
8. Else: return `lat=lon=depth_m=None`, `geo_precision="none"`, `geo_inferred=False`, `geo_source=None`, `geo_uncertainty_m=None`.

Expected values for the fixtures are listed in `tests/fixtures/pangaea_images/SOURCE.md`. Examples: 989684 `03:48:00` → (78.616649, 5.001493, 2361.4, image, false, 1.59). 989683 → (79.13221, 6.26172, 1290.0, station, true, 4000). 935896 → (11.930071, -117.021376, 4093.9, station, true, 4000). 898338 video → (78.2599, 9.399692, 416.5, station, true, ~1137).

## Access & download recipe
- Enumeration:
  1. Series → children: `GET https://doi.pangaea.de/10.1594/PANGAEA.<series>?format=metadata_panmd` and read `<md:entry key="collectionChilds" value="D989683,D989684,..."/>`. Alternatively `GET https://ws.pangaea.de/es/pangaea/panmd/_search?q=parentIdDataSet:<series>&size=500&_source_includes=URI,nDataPoints,sp-loginOption`.
  2. Per child: skip if `loginOption != unrestricted` (or ES `sp-loginOption != 1`) or if `moratoriumUntil` is in the future. Read the licence from pan_md `<md:license><md:label>`. Then `GET ...?format=textfile` (TSV; strip the `/* ... */` header; use the header for `Event(s):`, `Comment:`, `License:`, `Citation:`). Tables are 50 KB-10 MB. Do a HEAD first and skip anything over ~20 MB.
  3. Discovery of more datasets (answers seed question 3). POST to ES with `query_string`: `(techKeyword:param54243 OR techKeyword:param150836 OR techKeyword:param514706 OR techKeyword:param146419 OR techKeyword:param15651 OR techKeyword:param510678 OR techKeyword:param514838 OR techKeyword:param83431) AND (techKeyword:license21 OR techKeyword:license101 OR techKeyword:license29) AND sp-loginOption:1 AND (techKeyword:method11386 OR techKeyword:method11971 OR techKeyword:method10738 OR techKeyword:method11520 OR agg-method:"Remote operated vehicle" OR agg-method:"Remotely operated sensor platform BEAST" OR agg-method:"Sampling by diver" OR agg-method:"Underwater fish observatory")`. Use `"sort":[{"sf-idDataSet":"asc"}]` with `search_after` pagination: from+size is capped at 10,000, and aggregations on `techKeyword` are rejected. This returned **1,121** datasets on 2026-10-06.
     - Parameter IDs: 54243 URL image, 150836 Image, 514706 Image under water, 146419 Binary Object, 15651 URL raw, 510678 Video, 514838 Video under water, 83431 URL movie.
     - Method IDs: 11386 OFOS, 11971 OFOBS, 10738 AUV, 11520 ROV.
     - `geocode1600` in `techKeyword` does **not** prove per-image coordinates, because it is also set from the event. Check the pan_md `matrixColumn` for `Latitude` with `source="geocode"`.
     - Then group by `parentIdDataSet` and drop non-imagery titles (side scan, bathymetry, Parasound, quicklook).
     - Platform-filtered open datasets with per-row coordinates: 389 datasets, ~652 k rows. Without coordinates: 256 datasets, ~36 k rows. There are also 211 standalone (no-parent) OFOS/ROV/AUV media datasets from 1972-2024 (~98 k rows).
  4. Best extra DOIs (not seeds; open, CC BY, underwater; counts are ≈ rows = `nDataPoints` / number of non-geocode columns):

| DOI 10.1594/PANGAEA. | What | Licence | Children | ≈ images | Geo |
|---|---|---|---|---|---|
| 894801 | Heron Reef (GBR) georeferenced benthic photoquadrats, annually 2002-2017 (diver) | CC-BY-4.0 | 33 | ~117 k (rows, may include duplicates) | image (photo GPS) |
| 958183 | MOSAiC under-ice upward-looking ROV (BEAST) stills, 2019-2020 | CC-BY-4.0 | 88 | ~235 k | station (only floe-relative X/Y per image; event lat/lon) |
| 946149 | OBSEA cabled observatory (Vilanova i la Geltrú, 41.18191 N 1.75234 E) fish photos 2013-2014 | CC-BY-4.0 | 1 | ~63 k rows (tag rows; fewer unique images) | fixed_site |
| 846147 | Moreton Bay Eastern Banks photo-transects 2004-2015 (diver) | CC-BY-3.0 | 10 | ~31 k | image |
| 877578 | GBR Cairns-Cooktown photoquadrats, 160 transects / 23 reefs, Jan-May 2017 | CC-BY-3.0 | 26 | ~28 k (same photos as 892623) | image |
| 890634 | DISCOL Peru Basin OFOS, SO242/2, 2015 | CC-BY-3.0 | 20 | ~17.9 k | image |
| 872719 | Antarctic Peninsula OFOS, PS81 (ANT-XXIX/3), 2013 | CC-BY-3.0 | 31 | ~14.5 k | image (no depth column) |
| 871550 | Central Arctic OFOS, PS101 (ARK-XXX/3), 2016 | CC-BY-3.0 | 15 | ~9.8 k | image |
| 971424 | Central Arctic OFOBS, PS138, 2023 | CC-BY-4.0 | 16 | ~9.5 k | image |
| 928815 | Svalbard / Fram Strait OFOBS, MSM95, 2020 | CC-BY-4.0 | 13-15 | ~9-10 k | image |
| 891505 | GBR Far North photoquadrats, 63 transects / 12 reefs, Dec 2017 | CC-BY-3.0 | 13 | ~8.5 k (same photos as 891736) | image |
| 943364 | Aurora seamount, high Arctic OFOBS, HACON / Kronprins Haakon, 2019 | CC-BY-4.0 | 10 | ~7.0 k | image |
| 971365 | Fram Strait OFOBS, PS136, 2023 | CC-BY-4.0 | 9 | ~5.0 k | image |
| 932827 | Filchner Trough icefish nests OFOBS, PS124, 2021 | CC-BY-4.0 | 4 | ~4.6 k | image |
| 894734 | Atacama Trench margins OFOBS, SO261, 2018 | CC-BY-4.0 | 7 | ~4.4 k | image (depth partly) |
| 971422 | Gakkel Ridge OFOBS, PS137, 2023 | CC-BY-4.0 | 4 | ~3.4 k | image |
| 862097 | Weddell Sea OFOS, PS96, 2015-16 | CC-BY-3.0 | 13 | ~2.7 k | image |
| 921370 | Karasik Seamount HROV images, PS101, 2016 | CC-BY-4.0 | 1 | ~2.7 k | image |
| 961936 | ARTofMELT 2023 under-ice ROV videos (Fram Strait sea ice) | CC-BY-4.0 | 18 | videos | station (floe-relative `Dist rel X/Y` only, as for MOSAiC) |
| e.g. 615785 (+~45 similar) | Legacy HAUSGARTEN / Greenland Sea OFOS photos 1997-2004 (ARK-XIII/2 … ARK-XX/1), TIFF ~24 MB + thumbnails | CC-BY-3.0 | standalone | ~700-800 each, ~35 k total | image (ship GPS; large layback uncertainty) |
| 957274 | SO268 "analysis-ready" (processed) images | CC-BY-4.0 | 12 | ~35 k | image. **Overlaps seed 935856** |
| Moratorium (later) | 995890 PS153 (until 2028-06-03, ~12 k), 987471 PS143/1 (2027-08-10, ~9.5 k), 988212 PS143/2 (2027-09-03, ~5.1 k), 987706 PS146 (2027-09-03, ~3.4 k) | CC-BY-4.0 | | ~30 k | image |

- Auth / rate limits: no auth for unrestricted single files and metadata. A PANGAEA account Bearer token is needed for `allfiles.zip/.tar` and for moratorium data (only if the PI grants access). Keep ≤ 1 request/s per host and ≤ 2 parallel transfers. Honour `Retry-After` on 429/503. pangaeapy itself uses 5 concurrent downloads and retries on 429 and 503. Stay well below that given the ToU bulk clause.
- How to fetch one media file:
  - `GET <URL image>`, or `GET https://download.pangaea.de/dataset/<child_id>/files/<filename>` (filename exactly as in the column, case-sensitive, e.g. `.JPG`).
  - Both hosts send `Accept-Ranges: bytes` (Range → 206 verified on hs.pangaea.de), `Content-Length` and `Last-Modified` (plus `ETag` on download.pangaea.de), so resume with `curl -C -` works.
- **Tape staging** (answers seed question 4). Files on both hs.pangaea.de and download.pangaea.de can sit on tape.
  - A request for a file on tape returns **HTTP 503**, `Content-Type: text/html`, `Retry-After: 2` (then `7`), `Refresh: 5`, and an HTML page "The requested file … is loading from tape... Download will start automatically after a minute". A **HEAD request alone triggers the recall**. Observed: 503 at t=0, 20 s and 41 s, then 200 at t≈62 s for a 9.5 KB file.
  - Detection rule: status 503 **and** `Content-Type` is not the expected media type → staging. Never save the body.
  - Strategy: send HEAD for a batch of ≤ 50 sampled files (this triggers recall), then poll each file with HEAD every max(Retry-After, 15) s, and GET once it returns 200 with `image/*` or `video/*`. Give up after ~10 min per file.
  - Do not HEAD files you will not download. Each HEAD recalls the file, including multi-GB videos.
  - pangaeapy waits 30·(attempt+1) s for up to 4 attempts.
- pangaeapy (answers seed question 2): `PanDataSet(id).data` loads `?format=textfile` (Accept `text/tab-separated-values`) into a DataFrame whose column names are the **short names** (`URL image`, `IMAGE water`, `Binary`, `IMAGE`, `URL file`, `Metadata`, `Latitude`, `Longitude`, `Depth water`).
  - Caveat: with `addEventColumns=True` (the default), pangaeapy **fills missing Latitude/Longitude/Elevation with the event coordinate**. `ds.params['Latitude'].source == 'event'` shows when that happened, and resolve_geo must treat that case as station.
  - `ds.download(indices=[...])` fetches columns matching `^(binary|netcdf|image|video|text|url|csv)` from `https://download.pangaea.de/dataset/<id>/files/<name>` or the absolute URL. With no indices and no URL column, it tries `allfiles.zip`, which needs an `auth_token`.
  - It does not handle moratorium data without a token. It sends the UA `pangaeapy/<ver>`; set our own UA via raw requests instead.
- Sampling strategy for N samples:
  1. Build the candidate list: seeds plus the discovery query, keeping only open, CC BY/CC0 children with an underwater platform and an image column.
  2. Compute per-child image counts and the region (meanPosition) and year.
  3. Allocate N across parent series ∝ sqrt(images), with a cap of max(50, N/20) per series and a floor of 1 per series, so the 380 k-image AUV series does not dominate.
  4. Within a child, apply the filters (depth ≥ 0.9 × median depth, `Ground vis = 1`, no `SW_` files, not before the event time). Then take evenly spaced rows by time, mixing TIMER and HOTKEY.
  5. Prefer hs.pangaea.de URLs, which are mostly disk-cached. Stage download.pangaea.de files in batches.
  6. Spread across regions (Arctic HAUSGARTEN, Antarctic, CCZ/Peru Basin abyss, GBR shallow reef) and years (1997-2023).
  7. Videos: download at most 1-2 per series (each 2-3.5 GB), sample frames at ≥ 30 s spacing, and tag them station-level.
  8. Store under `<data_root>/pangaea_images/{images,videos,metadata}`. Metadata holds the child TSV, pan_md XML and citation per child DOI.

## Manual steps (human)
- Before a full-archive harvest (more than a few thousand files per day, or more than ~100 GB), email PANGAEA (contact via https://www.pangaea.de/contact/) for "prior authorization" as required by the ToU bulk-download clause. Sampled runs of a few thousand files at ≤ 1 req/s should be fine without it.
- Optional: create a PANGAEA account and store its Bearer token only if per-child `allfiles.tar` downloads are wanted. Single-file downloads need no account.
- Moratorium datasets (994607 until 2027-04-22, PS143/PS146 2027, PS153 2028): wait and re-check `moratoriumUntil`. No action is needed beyond scheduling a re-check.

## Fixtures
- tests/fixtures/pangaea_images/989684_msm77_3-5_ofos_rows.tab: MSM77 OFOS child table (header + 5 rows). Two rows have no position and come before the event; three rows have `Latitude`/`Longitude`/`Coord unc [m]` and a negative `Depth water [m]`.
- tests/fixtures/pangaea_images/989683_msm77_11-1_ofos_rows.tab: MSM77 OFOS child with **no** coordinate columns. Only the `Event(s):` header gives a station position (3 rows).
- tests/fixtures/pangaea_images/879298_so242_auv_rows.tab: AUV ABYSS child, CC-BY-3.0. Per-image coordinates and depth, `URL image` on hs.pangaea.de, `Ground vis` 0/1 (3 rows).
- tests/fixtures/pangaea_images/935896_so268_ofos_constant_position_rows.tab: SO268 OFOS child where every row repeats one position, with the comment "Positioning failed for this dive". There is no depth column, and the `Binary` filename column is used (3 rows).
- tests/fixtures/pangaea_images/898338_he153_rov_video.panmd.xml: pan_md of the seed ROV video (event start/end, `staticURL`, licence). `<md:eMail>` lines were dropped.
- tests/fixtures/pangaea_images/SOURCE.md: URLs, retrieval date, trimming, and expected resolve_geo outputs.

## Short download instruction
1. List children of each series via `?format=metadata_panmd` (`collectionChilds`); keep `loginOption=unrestricted` and CC-BY/CC0 licences; find more with the ES query in this note.
2. Per child, GET `https://doi.pangaea.de/10.1594/PANGAEA.<id>?format=textfile`; one row = one image (`Latitude`/`Longitude`/`Depth water [m]`, else the `Event(s):` position).
3. Media: absolute `URL image`/`URL raw`, else `https://download.pangaea.de/dataset/<id>/files/<filename>`; ≤ 1 req/s, Range/resume OK.
4. HTTP 503 + text/html + Retry-After = tape recall: HEAD a batch, poll until 200, then GET. Never save HTML bodies.
5. Drop descent/deck rows and `Ground vis=0`; store the DOI citation and licence with every sample; ask PANGAEA before full-archive bulk download.

## Open questions / risks
- The ToU bulk-download clause could throttle or disconnect a full harvest (~1 M+ images across PANGAEA). Prior authorisation is advisable. Rate limits are not published; only Retry-After was observed.
- Tape recall latency at scale is unknown: ~60 s for one small file. Batches of large OFOBS JPGs and multi-GB videos may take much longer. Unintended HEADs trigger recalls; this research HEADed 24 HE153 MPEGs (21 returned 503 and were recalled).
- SO295 (994607): the abstract says per-image iFDOs exist ("The actual images can be accessed through the image-handles provided in each iFDO"), but every child returns 401 until 2027-04-22. The iFDO location and its field mapping (`image-latitude`, `image-longitude`, `image-altitude-meters`, negative below sea level) are unverified.
- Uncertainty defaults (USBL 20 m, AUV 50 m, ship-GPS layback heuristic, 4 km station) are estimates. Only MSM77/SO295 publish a per-image `Coord unc [m]`.
- The ~380 k count for 882349 and the other row counts are `nDataPoints` / data-column estimates, not row counts of every table. Tables above ~5 MB (e.g. 882182, 41 k rows) were not downloaded.
- Depth sign is inconsistent between series (MSM77 negative). Some series have no depth column (872719, 935896). Legacy OFOS positions are ship GPS, not camera positions.
- The MOSAiC BEAST images (958183) carry only floe-relative X/Y. The floe drifted during surveys, so a station uncertainty of ~1-2 km should be checked against drift speed.
- Overlap with other aquasource sources: the GEOMAR BIIGLE volumes, FathomNet or other image hubs may re-host PANGAEA images. Dedupe on hs.pangaea.de / download.pangaea.de origin URLs and DOIs.
