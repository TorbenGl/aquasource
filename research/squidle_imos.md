# SQUIDLE+ (IMOS AUV and other campaigns) (`squidle_imos`)
Status: researched · researched 2026-10-07

## Summary
SQUIDLE+ (https://squidle.org) is a marine-image management and annotation platform run by the IMOS Understanding of Marine Imagery (UMI) sub-facility. It does not host images itself. It indexes 1,208 campaigns, 27,461 deployments and **11.39 M media** from 36 platforms, each served from the custodian's own storage. The core of this key is the **IMOS AUV Facility imagery**: AUV Sirius, AUV Nimbus and ACFR AUV Holt. That is 69 campaigns, 906 deployments and **7.60 M downward-looking stereo-left JPEGs** from 2007-09 to 2023-10 around Australia, all served anonymously from the public AWS bucket `imos-data`. The total is about 8-9 TB at full resolution for one camera per pair (estimate, corrected in verification from 7.0 TB).

Licence: SQUIDLE+ stores **no licence field** at any level. The IMOS AUV imagery is **tier B (CC BY 4.0)**, read from the AODN metadata records, whose facility record covers the whole `IMOS/AUV/` prefix. Every IMOS image carries its own AUV navigation fix: `latitude`/`longitude` in the IMOS per-dive CSV, or `pose.lat`/`pose.lon` in SQUIDLE+. That is **geo_precision = image**.

Verdict: **ingest the IMOS AUV part (tier B, image-level geo)**. The other 3.8 M SQUIDLE+ media are not covered here:
- Schmidt Ocean ROV (1.26 M) is NC-SA, so Excluded.
- CSIRO, RLS and AADC/IMAS imagery belong to their own catalog keys.
- The rest are tier U, because SQUIDLE+ publishes no licence for them.

## Entry points
- SQUIDLE+ web: https://squidle.org. API schema as JSON: https://squidle.org/api/help (41 collections). Human-readable help: https://squidle.org/api/help?template=api_help_page.html.
- SQUIDLE+ API base: `https://squidle.org/api/`. The relevant collections are `campaign`, `deployment`, `media`, `pose`, `platform`, `media_type`, `campaign_file` and `deployment_file`.
- Anonymous per-deployment export: `https://squidle.org/api/deployment/<id>/export?template=dataframe.csv&f={"operations":[{"module":"pandas","method":"json_normalize"}]}&include_columns=[...]`. It answers 202 with a background task; poll `/task/<task_id>` (send `Accept: application/json`, otherwise an HTML page comes back), then download from `/task/<task_id>/result`.
- IMOS AUV data on AWS S3 (public, anonymous listing):
  - Bucket: `https://imos-data.s3-ap-southeast-2.amazonaws.com/?list-type=2&prefix=IMOS/AUV/`, also reachable as `s3://imos-data/IMOS/AUV/` with `--no-sign-request`.
  - Per-dive navigation CSV: `IMOS/AUV/auv_viewer_data/csv_outputs/<campaign>/DATA_<campaign>_<dive>.csv`.
  - Images: `IMOS/AUV/auv_viewer_data/images/<campaign>/<dive>/full_res/<image>.jpg` and `.../thumbnails/<image>.jpg`.
  - Original products: `IMOS/AUV/<campaign>/<dive>/i<YYYYMMDD_hhmmss>_gtif/*.tif`, plus `i*_subsample20/`, `track_files/`, `hydro_netcdf/`, `mesh/` and `mosaic/`. Campaign-level files: `IMOS/AUV/<campaign>/all_reports/` and `README_AUV_Data_Products.txt`.
  - AODN browse page: http://data.aodn.org.au/?prefix=IMOS/AUV/.
- AODN metadata records (ISO 19115-3; XML at `https://catalogue-imos.aodn.org.au/geonetwork/srv/api/records/<uuid>/formatters/xml`):
  - `af5d0ff9-bb9c-4b7c-a63c-854a630b6984`: IMOS - Autonomous Underwater Vehicles Facility. Its data link is `http://data.aodn.org.au/?prefix=IMOS/AUV/`.
  - `fe81b24e-adee-4c77-a8e1-e8a77cfd3dff`: AUV Sirius. It has 19 child campaign records (2007-2012), for example `89fb5a5c-abe7-4aa3-bace-f758340cf49e` (GBR200709).
  - `8dfa2b64-4eed-491c-ba5e-645ea9409d4d`: AUV Nimbus. It has no child records.
  - `0c9bdfd6-2760-4bde-8230-241132790701`: IMOS - UMI Sub-Facility - Squidle+ Imagery and Tracks by Deployment (the map layer).
- Platform paper: Friedman A., Monk J., Pizarro O., et al. (2026), "Squidle+: a collaborative platform to manage, discover and annotate marine imagery", *Front. Mar. Sci.* 12:1677103, https://doi.org/10.3389/fmars.2025.1677103.

## Licence
- Tier: **B** for IMOS AUV imagery. This covers platforms `IMOS AUV Sirius` (id 1), `IMOS AUV Nimbus` (id 5) and `ACFR AUV Holt` (id 7), for the 69 campaigns present under `s3://imos-data/IMOS/AUV/`. The rest of SQUIDLE+ is tiered per platform, because SQUIDLE+ itself has no licence field:
  - `SOI ROV Subastian` (1.26 M media) → **Excluded**. SOI publishes CC BY-NC-SA 4.0 (see the `benthicnet` note and the `schmidt_ocean` key).
  - `CSIRO MNF DTC Towed Camera` (0.81 M) and `CSIRO O&A MRITC` (0.13 M) → handled by the `csiro_mnf` key; **U** here.
  - `RLS Diver Photos` (0.36 M) → handled by the `reef_life_survey` key; **U** here.
  - `IMAS Collated Antarctic Imagery` (85 k) → overlaps the `aadc` key; **U** here.
  - Every other platform (SOTON/UTOK OPLab AUV 240 k, ACFR AUV Seekers 197 k, IMAS ROV Boxfish 128 k, NSW towed cameras and ROV, UoA, TNC, BOSS dropcams, BRUVs and so on) → **U**. No licence is published in SQUIDLE+, and none was found at origin in this pass.
  - Three campaigns flown with IMOS platforms but **not** in the IMOS bucket, served only from `https://data.acfr.usyd.edu.au/marine/...`, are **U**: `Hawaii201801` (159,109 media), `TasFracture202106` (115,334) and `PortPhillipBay202301` (162,568). They have no AODN record and no S3 copy.
- Licence text (quote) + level read (file / record / collection) + URL:
  - **Record level, AODN.** This is the most specific level that exists: dive-level UUIDs from the CSVs, for example `104e0ddb-ebe0-4dfb-99af-24a5535a281d`, return 404 from the catalogue. The facility record `af5d0ff9-...`, the Sirius record `fe81b24e-...`, the Nimbus record `8dfa2b64-...` and the campaign record `89fb5a5c-...` all carry the same `MD_LegalConstraints`: "Creative Commons Attribution 4.0 International License … http://creativecommons.org/licenses/by/4.0/ … The citation in a list of references is: "IMOS [year-of-data-download], [Title], [data-access-URL], accessed [date-of-access]." Any users of IMOS data are required to clearly acknowledge the source of the material derived from IMOS in the format: "Data was sourced from Australia's Integrated Marine Observing System (IMOS) – IMOS is enabled by the National Collaborative Research Infrastructure strategy (NCRIS)." If relevant, also credit other organisations involved in collection of this particular datastream (as listed in 'credit' in the metadata record)." The records also say: "Data, products and services from IMOS are provided "as is" without any warranty as to fitness for a particular purpose." Read at https://catalogue-imos.aodn.org.au/geonetwork/srv/api/records/af5d0ff9-bb9c-4b7c-a63c-854a630b6984/formatters/xml, and the same URL pattern for the other UUIDs.
  - Coverage: Sirius has child campaign records only for 2007-2012 campaigns. Nimbus has none, and Holt has no platform record at all. For the later campaigns the most specific record is the platform record (Sirius/Nimbus) or the facility record. The facility record links `http://data.aodn.org.au/?prefix=IMOS/AUV/`, which includes `GeographeBay201505` (Holt) and all Nimbus campaigns. No record contradicts CC BY 4.0.
  - **File level, older wording.** The README in each campaign folder, for example `https://imos-data.s3-ap-southeast-2.amazonaws.com/IMOS/AUV/Batemans201211/README_AUV_Data_Products.txt`, says: "Distribution Statement: "AUV data may be reused, provided that related metadata explaining the data has been reviewed by the user, and the data is appropriately acknowledged."" Its acknowledgement reads: "Data was sourced from the Integrated Marine Observing System (IMOS). An initiative of the Australian Government being conducted as part of the National Collaborative Research Infrastructure Strategy". This is compatible with CC BY 4.0 (attribution only) and is not a contradiction.
  - **SQUIDLE+ platform level.** The `reference` field of platforms 1 and 5 (https://squidle.org/api/platform/1) says: "Sirius data was sourced from Australia's Integrated Marine Observing System (IMOS) – IMOS is enabled by the National Collaborative Research Infrastructure Strategy (NCRIS)." It is an acknowledgement, not a licence. Campaign, deployment and media objects have **no licence column** (checked in the `/api/help` schema). None of the 1,208 campaign descriptions mentions a licence. The wiki "User Agreement" (https://squidle.org/wiki_page/documents/user_agreement) reads only "PAGE UNDER CONSTRUCTION…" (last edited 2024-06-18).
  - **Caution.** AODN record `0c9bdfd6-...` (Squidle+ Imagery and Tracks by Deployment) is CC BY 4.0. It describes the SQUIDLE+ deployment map layer, not third-party imagery. Do not read it as licensing SOI, RLS or other non-IMOS images. The 2026 paper says datasets are shared under "granular permissions" and "Data Usage Agreements (DUA)" decided by custodians.
- Attribution / citation text to store with every sample (IMOS part):
  - "Data was sourced from Australia's Integrated Marine Observing System (IMOS) – IMOS is enabled by the National Collaborative Research Infrastructure strategy (NCRIS)."
  - Citation: "IMOS <year-of-download>, IMOS - Autonomous Underwater Vehicles - AUV <Sirius|Nimbus> (campaign <campaign>), https://imos-data.s3-ap-southeast-2.amazonaws.com/IMOS/AUV/<campaign>/, accessed <date>." Use the campaign record title when one exists, for example "IMOS - Autonomous Underwater Vehicles - SIRIUS, CAMPAIGN: Great Barrier Reef, SEPTEMBER 2007".
  - Credit: "Australian Centre for Field Robotics (ACFR), The University of Sydney".
  - Store as well: `licence = CC-BY-4.0`, `licence_url = http://creativecommons.org/licenses/by/4.0/`, `aodn_record = <uuid>`, and the origin S3 URL.
  - If SQUIDLE+ metadata was used, optionally also cite Friedman et al. 2026 (doi 10.3389/fmars.2025.1677103).
- Embargo / moratorium / special terms:
  - No embargo exists. The facility record says: "This IMOS Facility finished in June 2023, with data still available through the AODN Portal".
  - The 2026 paper describes a planned "discoverable but private" mode. Private datasets do not appear in anonymous API results, and none were used here.

## Media
- Types, counts, formats, resolution, total size, time range:
  - **IMOS AUV, in scope.** These are still images only: downward-looking stereo pairs at about 2 m altitude, captured at about 1 Hz (the abstracts say "stereo pairs images were captured every around each 40cm at an average altitude of 2.2m").
    - SQUIDLE+ holds **one camera per stereo pair**: `*_LC16` in older campaigns, `*_FC16` from about 2020. **Correction (verification):** from about 2020 the S3 `auv_viewer_data` tree and the per-dive CSVs hold **both** cameras of a pair, `*_FC16` and `*_AC16`, with identical lat/lon (Apollo202309, WA202103 dive NG61, Tasmania2020-2023, Sydney202111, Wollongong202201, SEQueensland202211, Forster202006, EMR202001, DiscoveryBay202112, WA202205, WA202303, WA_SW_202103: 15 campaigns checked from the first CSV of each). CSV `number_of_images` is then twice the SQUIDLE+ `media_count` (Apollo dive NG02 d17: 20,548 against 10,279). Keep `_FC16` (the camera SQUIDLE+ indexes) and drop `_AC16` as a near-duplicate. Older campaigns have `_LC16` only. The GeoTIFF folders also hold the second camera (`*_RM16`).
    - Counts from SQUIDLE+ `deployment.media_count`, summed on 2026-10-07: Sirius 5,659,895; Nimbus 1,888,593; Holt 47,077. Total **7,595,565** images in 69 campaigns and 906 deployments.
    - Time range is 2007-09-28 (GBR200709) to 2023-10-11 (Apollo202309). Media by start year: 2007 113 k; 2008 200 k; 2009 392 k; 2010 515 k; 2011 639 k; 2012 1,092 k; 2013 622 k; 2014 322 k; 2015 509 k; 2016 311 k; 2017 366 k; 2018 191 k; 2019 71 k; 2020 502 k; 2021 1,029 k; 2022 373 k; 2023 347 k.
    - Formats and sizes:
      - full_res JPEG, 1360×1024 up to about 2019. Medians are 90-500 kB per campaign; for example, Batemans201211 is about 192 kB.
      - 4112×3008 JPEG from about 2020 on (WA202103 checked). Medians are 1.0-8.2 MB.
      - Thumbnails are 453×341. Sizes range from about 1 kB (near-black surface frame, Batemans201211) to about 70-125 kB (2021-2023 campaigns: WA202103 69 kB, Apollo202309 125 kB), not "a few kB" throughout.
      - GeoTIFF originals are about 30-300 kB each (2012).
    - Estimated full_res total is **about 8-9 TB** for LC16/FC16 only (verification revision of the original 7.0 TB). Basis: 5.34 M images before 2020 at about 0.25 MB (GBR201509 0.24 MB, Tasmania201808 0.27 MB) is about 1.3 TB, and 2.25 M images from 2020 on at 1.7-4.7 MB (medians from the first 500 FC16 of each: WA202103 1.66, Forster202006 1.78, WA202303 2.26, Tasmania202104 2.77, Apollo202309 3.03, Tasmania202302 3.31, SEQueensland202211 3.57, Wollongong202201 3.96, Sydney202111 4.60 MB) is about 7 TB. Uncertainty +-30 %. The `_AC16` twins would add roughly the same again, so do not mirror the bucket.
    - The S3 bucket also has three campaigns that are not in SQUIDLE+ or `auv_viewer_data` (GeoTIFF products only): `Ningaloo200705`, `Whyalla200806` and `SEQueensland201010Eng`.
  - **Whole SQUIDLE+**: 11,389,627 media. The other big platforms are:
    - SOI ROV Subastian 1.26 M (Excluded)
    - CSIRO MNF DTC 0.81 M
    - RLS 0.36 M
    - SOTON/UTOK OPLab AUV 0.24 M
    - ACFR AUV Seekers 0.20 M
    - CSIRO MRITC 0.13 M
    - IMAS ROV Boxfish 0.13 M
    - IMAS Antarctic 85 k
    - all others under 40 k each (see the per-platform table in Open questions)
  - SQUIDLE+ also lists `media_type = wms` items: one ortho-mosaic WMS layer per AUV deployment, served from `geoserver.imas.utas.edu.au`. These are not photos.
- Filters needed:
  - Keep only `media_type.name == "image"` and `is_valid == true`. In the `/api/pose` JSON a mosaic shows up as `media.key == deployment.key`, with `path_best_thm` pointing to `squidle.org/api/media/<id>/thumbnail`.
  - **Water-column, descent and ascent frames.** Deployments report `alt_min = 0.0` and dives begin near the surface; the first frame of Batemans201211 dive 05 is only 8,468 bytes, a near-black JPEG. Keep frames with `0.5 <= altitude <= 6 m` (nominal is 2 m), and drop frames whose JPEG is below about 15 % of the deployment's median size, or whose mean luminance is below a threshold.
  - **Bogus depths.** Some Nimbus poses have `dep` ≈ -1000.6, and Sirius goes down to -1.1. Null them (see the recipe).
  - **Near-duplicates.** Consecutive frames overlap by roughly 50 % or more (0.4 m spacing against a 1.3-2 m footprint, from `image_width` in the CSV). Subsample by time or distance (see Sampling).
  - **Overlaps with other sources.** Deduplicate on `(campaign, dive, image_filename)` and on the normalised S3 URL.
    - `benthicnet` holds 512 px copies of SQUIDLE+ sets, including IMOS AUV.
    - BENTHOZ-2015 ("Australian sea-floor survey data, with images and expert annotations", Bewley et al. 2015) is a subset of the IMOS AUV images.
    - The ACFR server `data.acfr.usyd.edu.au/marine/<campaign>/<dive>/full_res/<key>.jpg` holds the same keys with **different bytes**: Tasmania202302 is 3,125,836 B on ACFR against 4,874,116 B on S3. Always fetch the S3 copy.
    - Keys `reef_life_survey`, `schmidt_ocean`, `csiro_mnf` and `aadc` cover other SQUIDLE+ platforms.
  - There are no aerial or on-deck frames on the AUVs. Surface frames do occur at the start and end of a dive (handled by the altitude filter).

## Geolocation
- Region and extent: Australian waters only for the IMOS part, from Tasmania (about -43.6) to the Great Barrier Reef and Scott Reef (about -12), longitude about 112 to 154 E. The AODN facility record bounding box is W 112.00, E 160.00, S -45.00, N -12.00. Depth (vehicle) about 2-100 m, mostly 10-90 m (Scott Reef 57 m, Batemans 18 m, Apollo 50-86 m).
- Precision levels and share:
  - IMOS AUV: **100 % image**. Every image row or pose has its own navigated position (USBL-aided DVL/INS navigation, post-processed by ACFR).
  - Whole SQUIDLE+, by platform class: about 95.7 % image (AUV, ROV and towed cameras: 10.90 M) and about 4.3 % station (0.49 M):
    - BRUVs: one pose per deployment.
    - BOSS dropcams: four views share one pose.
    - Diver photo-quadrats.
    - RLS: synthetic per-photo offsets of 2.25e-5° around a site coordinate rounded to 0.01°.
- geo_source, CRS, depth field, uncertainty:
  - **IMOS S3 route.**
    - Coordinates: the `DATA_<campaign>_<dive>.csv` columns `latitude`, `longitude` (WGS 84 dd).
    - Depth: `depth_sensor` is vehicle (camera) depth in metres. `altitude_sensor` is height above the seabed. `depth` is seafloor depth (= depth_sensor + altitude_sensor). `time` is formatted `YYYYMMDDThhmmssZ`.
    - Footprint corners: `up_left_lon/lat`, `up_right_*`, `low_right_*` and `low_left_*`.
    - Layout: the file starts with a 2-line dive header, then the column header on line 3, then data rows. The header spelling varies; the 2021 files contain `geospatial_lat_min, geospatial_lon_min` with spaces, so trim names.
  - **SQUIDLE+ route.** Use `/api/pose` objects, or export columns `pose.lat`, `pose.lon`, `pose.dep`, `pose.alt`, `pose.timestamp`, `pose.data.*` (WGS 84, `pose.geom` SRID 4326). **The meaning of `pose.dep` depends on when the deployment was imported**:
    - Older imports (2017-2018, platform `data.datafile_operations` maps `"dep": "depth_sensor"`): `pose.dep` = vehicle depth, and `pose.data` has **no** `dep`. Examples: deployment 22, where `dep` 18.094441 equals `depth_sensor`; and deployment 213, 57.266194.
    - Newer imports (datasource 2/4 maps `"depth": "pose.dep"` and `"depth_sensor": "pose.data.dep"`): `pose.dep` = **seafloor** depth and `pose.data.dep` = vehicle depth. Example: deployment 11646, where `dep` 47.473168 equals CSV `depth` and `data.dep` 45.753168 equals `depth_sensor`.
    - So: vehicle depth = `pose.data.dep` if present, else `pose.dep`.
  - The pipeline's `depth_m` = **vehicle/camera depth**. Seafloor depth can be kept as an extra field (vehicle + alt).
  - Uncertainty: no per-image navigation error is published, so `geo_uncertainty_m = null` for image precision. For station-type platforms see the recipe.
- How a sample maps to its coordinate:
  - IMOS S3: the CSV row with `image_filename == <key>` gives the image `.../full_res/<image_filename>.jpg`. Campaign and dive come from the CSV columns `campaign_code` and `dive_code`, and match the folder names.
  - SQUIDLE+: `pose.media.id` / `media.key` gives `path_best`. Still images have exactly one pose.

### resolve_geo recipe
Input: one record, either an IMOS CSV row (`src="imos_csv"`) or a SQUIDLE+ pose or export row (`src="squidle"`). Context: `platform_name`, `media_type` (if known), `deployment_key`, and per deployment `n_img` (image count) and `n_xy` (count of distinct (lat, lon) among images).

1. Skip non-images. If `media_type` is known and is not `"image"`, or (for `/api/pose` JSON) `media.key == deployment.key`, or `"/api/media/" in media.path_best_thm`, then the record is **not a sample**: return `None` (WMS mosaic). Also skip when `is_valid` is false.
2. Coordinates. For `imos_csv`: `lat = float(row["latitude"])`, `lon = float(row["longitude"])`. For `squidle`: `lat = pose["lat"]` / `row["pose.lat"]`, and `lon` likewise. If either is missing or NaN, `abs(lat) > 90` or `abs(lon) > 180`, or (lat, lon) == (0, 0), return `Geo.none(geo_source=<string from step 4>)`.
3. Depth (vehicle/camera). For `imos_csv`: `v = row["depth_sensor"]`. For `squidle`: `v = pose["data"]["dep"]` (or export `pose.data.dep`) if present and non-empty, else `pose["dep"]` (or `pose.dep`). Then `depth_m = round(float(v), 2)` if `0 <= v <= 11000`, else `None`. Negative values such as -1000.6 or -1.1 are invalid.
4. `geo_source`:
   - `imos_csv`: `"IMOS AUV csv_outputs/<campaign>/DATA_<campaign>_<dive>.csv: latitude,longitude (WGS84); depth_m=depth_sensor"`
   - `squidle`: `"SQUIDLE+ /api/pose lat,lon (WGS84); depth_m=pose.data.dep|pose.dep (vehicle depth)"`
5. Precision:
   - a. Platforms `IMOS AUV Sirius`, `IMOS AUV Nimbus`, `ACFR AUV Holt`, and any other AUV, ROV or towed platform: `geo_precision="image"`, `geo_inferred=False`, `geo_uncertainty_m=None`.
   - b. If `platform_name` contains `RLS`: `station`, inferred=True, uncertainty=1000.
   - c. Otherwise, if `platform_name` matches `/BRUV|Dropcam|Drop Camera|DIVER|Diver/`, **or** `n_img > 1 and n_xy == 1`: `station`, inferred=True. Uncertainty is 100 for BRUV and dropcam (vessel GPS at the drop) and 500 for diver photos.
   - d. Otherwise use `image` as in (a).
6. Never return `segment`: positions are already per frame. Never interpolate.

Expected results on the fixtures:

| fixture / record | lat, lon | depth_m | precision | inferred | unc. |
|---|---|---|---|---|---|
| `imos_s3_dive_csv_ScottReef201108_excerpt.csv` row `PR_20110810_042708_616_LC16` | -14.10650833, 121.89248264 | 57.27 | image | false | null |
| same, `PR_20110810_042709_618_LC16` | -14.10650833, 121.89248056 | 57.21 | image | false | null |
| same, `PR_20110810_042710_619_LC16` | -14.10650833, 121.89247847 | 57.2 | image | false | null |
| `squidle_deployment_export_213_excerpt.csv`, the same three images (`pose.dep` 57.26619399999999 / 57.212695 / 57.195496, no `pose.data.dep` column) | identical to the three rows above | 57.27 / 57.21 / 57.2 | image | false | null |
| `squidle_api_pose_deployment22_page1.json` item 1 (`PR_20121128_200011_588_LC16`, old import) | -35.82695625, 150.2332375 | 18.09 | image | false | null |
| same, item 2 (`media.key` == deployment key, WMS mosaic) | not a sample (None) | | | | |
| same, item 3 (`PR_20121128_200012_589_LC16`) | -35.82695764, 150.23323611 | 18.04 | image | false | null |
| `squidle_api_pose_deployment11646_page1.json` item 1 (new import; `dep` 47.473168 is the seafloor, `data.dep` 45.753168) | -28.847136499999998, 114.04728 | 45.75 | image | false | null |
| same, item 2 (WMS mosaic) | not a sample (None) | | | | |
| same, item 3 | -28.8471381, 114.0472806 | 45.7 | image | false | null |
| `squidle_deployment_export_16821_boss_dropcam.csv` (4 rows, UWA BOSS, one pose) | -34.16379179, 120.9335453 | 77.0 | station | true | 100 |

The BOSS rows are tier U by licence and are included only to test the station branch.

## Access & download recipe
- Enumeration, auth and rate limits:
  - **IMOS images (recommended route, no SQUIDLE+ calls needed).**
    1. `GET https://imos-data.s3-ap-southeast-2.amazonaws.com/?list-type=2&delimiter=/&prefix=IMOS/AUV/auv_viewer_data/csv_outputs/` lists the campaigns. For each campaign, list `.../csv_outputs/<campaign>/` (ListObjectsV2, 1,000 keys per page, continue with `continuation-token`) to get one `DATA_*.csv` per dive. Each is 0.06-4 MB, about 330 B per image row; the CSVs hold about 7.6 M rows for LC16/FC16 plus the `_AC16` twin rows of the 2020+ campaigns (about 2 M more, estimated from the `number_of_images` ratio), roughly 3.3 GB in all.
    2. Parse each CSV with `skiprows=2` (2-line dive header). Strip whitespace from the dive-header names (Apollo202309 has `" geospatial_lon_min"`). Treat each row as one image **except** rows whose `image_filename` ends `_AC16`, which are the second camera of a pair (same lat/lon, drop them; keep `_FC16`).
    3. The image URL is `https://s3-ap-southeast-2.amazonaws.com/imos-data/IMOS/AUV/auv_viewer_data/images/<campaign_code>/<dive_code>/full_res/<image_filename>.jpg`. The thumbnail is the same with `thumbnails`.
    4. No auth is needed and the bucket is anonymous. Stay at 4-8 parallel GETs and back off on 503 SlowDown.
  - **SQUIDLE+ API** (useful for counts, mosaics and non-IMOS platforms). No token is needed for GET on `campaign`, `deployment`, `media` and `pose`, nor for `/api/deployment/<id>/export`. `/api/media/export` returns **401 "You are not logged in!"** without an API token (`X-Auth-Token` header).
    - Pagination: `results_per_page` up to at least 2,000 (`/api/pose`: 2,000 rows in 13 s) and `page=N`. Filters are `q={"filters":[{"name":..,"op":..,"val":..}],"order_by":[..]}`. Relations use `has`/`any`, for example `{"name":"media","op":"has","val":{"name":"deployment_id","op":"eq","val":22}}` or `{"name":"media_type","op":"has","val":{"name":"name","op":"eq","val":"image"}}`. `datasource_id` and `platform_id` filters work on `/api/deployment`. `include_columns` is ignored on list endpoints, but honoured by the export endpoints.
    - Export: `/api/deployment/<id>/export?template=dataframe.csv&disposition=inline&f={"operations":[{"module":"pandas","method":"json_normalize"}]}&include_columns=["id","key","path_best","timestamp_start","pose.timestamp","pose.lat","pose.lon","pose.dep","pose.alt","pose.data","media_type.name","is_valid","deployment.key","deployment.campaign.key"]` returns `202 {task_id}`. Then poll `/task/<id>` until `"result_available": true` and GET `/task/<id>/result`. Without `f`, the task fails with `'list object' has no attribute 'to_csv'`. Deployment metadata comes back in the `X-Content-Metadata` header. An 8,196-media deployment took about 56 s server-side; results expire shortly after completion.
    - No rate limit is documented (behind Cloudflare). Use 1 request per second and at most one export task at a time.
- How to fetch one media file:
  - Plain HTTPS GET of the S3 URL. Example: `https://s3-ap-southeast-2.amazonaws.com/imos-data/IMOS/AUV/auv_viewer_data/images/Batemans201211/r20121128_195806_Burrewarra_BU_DG3_05_dense/full_res/PR_20121128_210659_511_LC16.jpg` (192,007 B, 1360×1024).
  - S3 sends `Accept-Ranges: bytes`, so Range requests and resume work (206 verified). `Last-Modified` is available for change detection.
  - Do not use the `data.acfr.usyd.edu.au` copies of S3 campaigns (different bytes, not the AODN-licensed copy).
- Sampling strategy for a budget of N samples:
  1. Stratify by campaign: 69 campaigns over 2007-2023 in GBR, Coral Sea, Ningaloo, Scott Reef, WA, SA, Tasmania, Victoria, NSW and Qld. Give each campaign `ceil(N/69)`, capped by availability, and let large campaigns share the remainder in proportion to the square root of their size.
  2. Within a campaign, spread over dives (round-robin).
  3. Within a dive, take frames at least 30 s apart, which is at least about 15 m along track and has no footprint overlap. Apply the altitude window `0.5-6 m` and drop dark frames.
  4. Use `thumbnails/` (453×341, about 1-125 kB) for a cheap low-resolution pass. Use `full_res` for training: about 0.2 MB per image before 2019 and about 2-8 MB after 2020.
  5. Write `<data_root>/squidle_imos/images/<campaign>/<dive>/<image>.jpg` and `<data_root>/squidle_imos/metadata/<campaign>/DATA_<campaign>_<dive>.csv`. Store the provenance row (campaign, dive, image_filename, S3 URL, AODN record UUID, licence) per sample.

## Manual steps (human)
- None for the IMOS AUV part.
- Optional: a free SQUIDLE+ account and API token would enable `/api/media/export`, but that endpoint is not needed.
- Optional: email IMOS/ACFR to confirm the licence for `Hawaii201801`, `TasFracture202106` and `PortPhillipBay202301` (ACFR-hosted only).

## Fixtures
- `tests/fixtures/squidle_imos/imos_s3_dive_csv_ScottReef201108_excerpt.csv`: IMOS AUV per-dive CSV (`DATA_ScottReef201108_r20110810_042127_04_scott_long_leg_auv8.csv`). Lines 1-6 kept: the 2-line dive header, the column header and the first 3 image rows.
- `tests/fixtures/squidle_imos/squidle_deployment_export_213_excerpt.csv`: SQUIDLE+ anonymous deployment export (json_normalize CSV) for the same dive. Header plus the first 3 rows, which are the same three images as the IMOS CSV (cross-route test).
- `tests/fixtures/squidle_imos/squidle_api_pose_deployment22_page1.json`: `/api/pose` page (3 items, untrimmed) for an old-import Sirius dive. It includes the WMS-mosaic pose; `dep` = vehicle depth.
- `tests/fixtures/squidle_imos/squidle_api_pose_deployment11646_page1.json`: `/api/pose` page (3 items, untrimmed) for a 2021-import Sirius dive. `dep` = seafloor depth and `data.dep` = vehicle depth; includes a WMS-mosaic pose.
- `tests/fixtures/squidle_imos/squidle_deployment_export_16821_boss_dropcam.csv`: SQUIDLE+ export for a UWA BOSS drop-camera deployment (4 views, one pose). This is the station-branch test; its licence is tier U.
- `tests/fixtures/squidle_imos/SOURCE.md`: URLs, retrieval date and trimming for each file (**missing in the original delivery, written during verification**).

## Short download instruction
List `s3://imos-data/IMOS/AUV/auv_viewer_data/csv_outputs/<campaign>/` anonymously over HTTPS (ListObjectsV2) and read each `DATA_<campaign>_<dive>.csv` (skip 2 header lines). Each row is one image (drop `_AC16` twin rows) with `latitude`, `longitude`, `depth_sensor`, `altitude_sensor`, `time`. Download `https://s3-ap-southeast-2.amazonaws.com/imos-data/IMOS/AUV/auv_viewer_data/images/<campaign>/<dive>/full_res/<image_filename>.jpg`, keeping frames ≥30 s apart with altitude 0.5-6 m. Licence CC BY 4.0 (AODN record af5d0ff9-…); store the IMOS acknowledgement. SQUIDLE+ (`/api/pose`, `/api/deployment/<id>/export`) is optional, for counts and non-IMOS platforms (licence U unless verified per custodian).

## Open questions / risks
- **Non-IMOS licences.** SQUIDLE+ has no licence field and an empty User Agreement. All non-IMOS platforms stay U or Excluded until each custodian's own record is read (IMAS, UWA, NSW DPI/DCCEEW, SOTON, UoA, TNC, DBCA, DEW, Curtin and others).
- **ACFR-only IMOS-platform campaigns** (`Hawaii201801`, `TasFracture202106`, `PortPhillipBay202301`, 0.44 M media) have no AODN record and no S3 copy, so they are U. 11 deployments of `Tasmania202302` and other recent campaigns point to ACFR in SQUIDLE+, but the same keys exist on S3: rewrite those URLs to S3.
- **`pose.dep` semantics** differ by import (vehicle depth in older imports, seafloor depth in the 2021 Sirius import). The recipe handles this with `pose.data.dep`. Verification spot-check on a Nimbus deployment (id 15663, Apollo202309): `pose.dep` 50.04 is vehicle depth (CSV `depth_sensor` about 49.99, CSV `depth` about 52.2) and `pose.data` has no `dep`, so the "else `pose.dep`" branch is right for it. Prefer the S3 CSV `depth_sensor`, which is unambiguous.
- **Navigation accuracy** is not published per image (USBL/DVL; probably a few metres). Uncertainty is left null.
- **Size** (about 8-9 TB for LC16/FC16 only) is extrapolated from the first 500 files of one dive per campaign; the true total may differ by ±30 %. The bucket as a whole is larger because of the `_AC16` twins and the GeoTIFF products.
- **Counts drift.** SQUIDLE+ is live, and `campaign.media_count` summed to 11,367,458 against the deployment sum of 11,389,627 on the same day.
- Per-platform SQUIDLE+ media counts (2026-10-07, deployment sums):

| platform | media |
|---|---|
| IMOS AUV Sirius | 5,934,338 |
| IMOS AUV Nimbus | 2,051,161 |
| SOI ROV Subastian | 1,256,434 |
| CSIRO MNF DTC Towed Camera | 809,763 |
| RLS Diver Photos | 362,930 |
| SOTON/UTOK OPLab AUV | 240,430 |
| ACFR AUV Seekers | 197,232 |
| CSIRO O&A MRITC Towed Stereo Camera | 130,876 |
| IMAS ROV Boxfish | 127,663 |
| IMAS Collated Antarctic Imagery | 84,971 |
| ACFR AUV Holt | 47,077 |
| NSW ENV Towed Camera | 39,463 |
| 24 other platforms | 107,299 |

## Verification (2026-10-06)
Checked on 2026-10-08 (the run date; the heading keeps the date requested by the workflow) with metadata-only requests (image HEADs and a few Range GETs of CSVs; no media downloaded).

Checked and confirmed:
- **Licence (record level, provider's own catalogue).** Re-fetched https://catalogue-imos.aodn.org.au/geonetwork/srv/api/records/af5d0ff9-bb9c-4b7c-a63c-854a630b6984/formatters/xml: `MD_LegalConstraints` title "Creative Commons Attribution 4.0 International License", link http://creativecommons.org/licenses/by/4.0/, with the IMOS acknowledgement and citation wording quoted above. No NC / ND / SA / research-only wording anywhere in the record. The Nimbus (`8dfa2b64-...`), campaign (`89fb5a5c-...`) and Squidle+ layer (`0c9bdfd6-...`) records carry the same CC BY 4.0 link. The campaign README at https://imos-data.s3-ap-southeast-2.amazonaws.com/IMOS/AUV/Batemans201211/README_AUV_Data_Products.txt still says "AUV data may be reused, provided that related metadata ... has been reviewed ... and the data is appropriately acknowledged": compatible, no contradiction. Tier **B** stands for the 69 campaigns in the bucket. The facility record is the most specific licence for Nimbus and Holt campaigns, so the licence level is **record** (collection-level coverage for the later campaigns).
- **Attribution text** matches the record (the record uses a typographic apostrophe in "Australia's"; the lower-case "strategy" in the record versus "Strategy" on the platform page is cosmetic).
- **SQUIDLE+ has no licence field.** https://squidle.org/api/platform/1 carries only `reference` = "Sirius data was sourced from Australia's Integrated Marine Observing System (IMOS) ...", an acknowledgement.
- **Geo columns.** The live CSV https://imos-data.s3-ap-southeast-2.amazonaws.com/IMOS/AUV/auv_viewer_data/csv_outputs/ScottReef201108/DATA_ScottReef201108_r20110810_042127_04_scott_long_leg_auv8.csv (Range GET of 4 kB) has the columns `longitude`, `latitude` (in that order), `depth_sensor`, `altitude_sensor`, `depth`, `time` with the fixture values (-14.10650833, 121.89248264, 57.266194). Coordinates are not swapped and signs are right; the sample points are in water: Scott Reef -14.1065/121.8925, Batemans -35.827/150.233, WA202103 -28.847/114.047, Apollo202309 -38.915/143.514 (Bass Strait), Port Phillip Bay -38.2/145.0. `geo_precision = image`, `geo_inferred = false`, `geo_uncertainty_m = null` are right per the definitions (per-image navigation fix, no interpolation).
- **Fixtures are real provider records.** `/api/deployment?q=` for id 22 returns pose lat -35.82695625, lon 150.2332375, dep 18.094441 (fixture item 1). `/api/pose` for deployment 11646 returns the same first and third poses as the fixture (-28.8471365 etc. and `dep` 47.473168 / `data.dep` 45.753168). The deployment-213 export, re-run live (`/api/deployment/213/export`, task then `/task/<id>/result`), reproduces the three fixture rows exactly. Deployment 16821 is "UWA BOSS Dropcam", 4 media, pose -34.16379179 / 120.9335453 / dep 77.0 (in water, off the south coast of WA). The thumbnail URL in the 11646 fixture returns 200.
- **Counts.** Summing `/api/deployment` `media_count` for platforms 1, 5, 7 over the 69 bucket campaigns gives 5,659,895 (Sirius), 1,888,593 (Nimbus), 47,077 (Holt) = 7,595,565 in 906 deployments, and the by-year split in the note matches. The three ACFR-only campaigns are outside the bucket (Hawaii201801 159,109; TasFracture202106 115,334; PortPhillipBay202301 162,568). The S3 `csv_outputs/` listing returns exactly 69 campaign prefixes (plus a stray `seqld.csv.manifest`).
- **Access.** The anonymous S3 ListObjectsV2 call and the anonymous `/api/deployment`, `/api/pose` and export endpoints respond as described. Image HEADs return 200 with `Content-Length` (Apollo202309 FC16 6,525,922 B).
- **Observatories.** Not a fixed-site observatory; the full campaign history 2007-09 to 2023-10 (17 start years) is covered.

Corrected:
- **Two cameras per pair from about 2020.** The note said the CSV and S3 hold one camera per pair. For 15 of the 69 campaigns (Apollo202309, DiscoveryBay202112, EMR202001, Forster202006, SEQueensland202211, Sydney202111, Tasmania202001/202104/202208/202302, WA202103, WA202205, WA202303, WA_SW_202103, Wollongong202201) the CSV lists `_FC16` and `_AC16` rows with identical coordinates, and the `_AC16` image exists on S3 (HEAD 200, 7,034,952 B). SQUIDLE+ indexes only `_FC16`. The download recipe now drops `_AC16`. Without this, a sampler would double-count near-identical stereo twins.
- **Size.** About 8-9 TB (LC16/FC16 only), not 7.0 TB, from measured 500-file samples in 14 campaigns (full_res medians 0.24-0.27 MB before 2020, 1.7-4.7 MB after 2020).
- **Thumbnail size** is up to about 125 kB, not "a few kB".
- **Status polling** of an export task needs `Accept: application/json`.
- **`pose.dep` for Nimbus** (open question): checked on deployment 15663 (Apollo202309): `pose.dep` is vehicle depth, `pose.data.dep` absent; the recipe's fallback handles it.
- **SOURCE.md was missing** from the fixture directory; written now from the URLs above.
- Added the region, extent and depth range to the Geolocation section.

Not changed: tier B, `geo_precision` image, the resolve_geo recipe, the non-IMOS platform tiers (U or Excluded). Not re-verified: licences of non-IMOS custodians, and the Hawaii201801, TasFracture202106 and PortPhillipBay202301 campaigns (still U).
