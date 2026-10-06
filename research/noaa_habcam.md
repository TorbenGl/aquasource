# NOAA HabCam (NEFSC) (`noaa_habcam`)
Status: researched · researched 2026-10-06

## Summary
HabCam is NOAA NEFSC's towed stereo seabed camera. It is flown 1–3 m above the bottom at about 6 kn during the annual sea scallop survey on the US Northeast shelf (Mid-Atlantic Bight, Georges Bank). It has produced millions of image pairs per year since about 2012 (7.9 M pairs / 45 TB in 2015 alone). The full NEFSC archive is not public. Its InPort record lists "Formal request in writing" as the access procedure and "No Archiving Intended". The only public bulk copy is in Kitware's VIAME Web public "Training Data" collection:
- 119,461 colour-corrected stereo PNGs (650.9 GB) from NOAA's own 2015 survey (HabCam V4 on R/V Hugh R. Sharp, cruise S1 15-01, HabCam cruise code 201503). Tier A: US government work, and NOAA's catalogue record for HabCam carries CC0 1.0.
- 8,047 left-camera PNGs from Coonamessett Farm Foundation (CFF) HabCam V3 surveys in 2017–2019. Tier U: private producer, no licence stated anywhere.

The public files have no lat/lon. The 2015 images can still be geolocated at segment level. Each filename carries a UTC timestamp, which is matched against the ship's 1-s GPS track: R/V Hugh R. Sharp cruises HRS1506/HRS1507/HRS1508, archived as CC0 R2R navigation at NCEI. NEFSC's own `lat`/`lon` are also the ship's GPS fix, so this yields the same coordinate NEFSC holds, within about 300 m of the towed vehicle. The CFF subset gets region-level geo at best.

Verdict: ingest the 2015 NEFSC subset (tier A, segment). Keep the CFF folders out of the default shards (tier U, no navigation).

## Entry points
- NOAA InPort record (collection metadata; describes the non-public PostgreSQL + PNG archive): https://www.fisheries.noaa.gov/inport/item/27598 (XML: https://www.fisheries.noaa.gov/inport/item/27598/inport-xml; ISO: https://data.noaa.gov/waf/NOAA/nmfs/nefsc/iso/xml/27598.xml)
- data.gov catalogue entry (licence field): https://catalog.data.gov/dataset/habitat-mapping-camera-habcam
- HabCam group site linked from InPort: https://habcam.whoi.edu/. It was unreachable on 2026-10-06 (proxy 502 / DNS failure). A Wayback snapshot exists (20230331) but could not be fetched from here.
- VIAME Web public "Training Data" collection (Girder 5 REST API, no auth): https://viame.kitware.com/#/collection/5e4c256ca0fc86aa03120c34. API base: `https://viame.kitware.com/api/v1/`
  - `US_NE_2015_NEFSC_HABCAM` folder 5e4c2586a0fc86aa03120c4a → dataset `Corrected` folder **5e4eed5478ed364cd0f98b40** (119,467 items = 119,461 PNG + 6 metadata files; subfolder `auxiliary` 6060d4f87be29b6cb5c54228)
  - `US_NE_2017_CFF_HABCAM` 5eb3713a8d01d968cc1633d8 → `Left` 5eb371608d01d968cc1642dd (1,921 PNG), `Raws` 5eb371558d01d968cc1633da
  - `US_NE_2018_CFF_HABCAM` 5eb372688d01d968cc1651e0 → `Left` 5eb372788d01d968cc165ced (1,413 PNG), `Raws` 5eb3726f8d01d968cc1651e2
  - `US_NE_2019_CFF_HABCAM` 5eb374f38d01d968cc1667f8 → `Left` 5eb375298d01d968cc168607 (3,846 PNG), `Raws` 5eb375128d01d968cc1667fa
  - `US_NE_2019_CFF_HABCAM_PART2` 5eb375f78d01d968cc16a414 → `Left` 5eb376888d01d968cc16aadd (867 PNG), `Raws` 5eb376838d01d968cc16a416
  - `Unsorted/ChallengeData` 5e4c2584a0fc86aa03120c38: tarballs of the 2018 CVPR AAMVEM NOAA fish-detection challenge (874 GB), including 52,339 HabCam 2015 frames (overlap, see Media)
- 2015 cruise report ("Cruise Results, UNOLS R/V Hugh R. Sharp Cruise No. S1 15-01 (Parts I–III), Sea Scallop Survey", NEFSC 2016): https://repository.library.noaa.gov/view/noaa/22504 (PDF: https://repository.library.noaa.gov/view/noaa/22504/noaa_22504_DS1.pdf)
- Ship navigation (R2R `r2rnav` products, archived at NCEI):
  - HRS1506 (2015-05-16 → 05-25, Part I, Mid-Atlantic Bight): NCEI 0260576, https://www.ncei.noaa.gov/archive/accession/0260576. File: https://www.ncei.noaa.gov/data/oceans/archive/arc0207/0260576/4.6/data/0-data/HRS1506_616376_r2rnav/data/HRS1506_bestres.geoCSV (45.6 MB). R2R cruise DOI 10.7284/906846.
  - HRS1507 (2015-05-27 → 06-10, Part II): NCEI 0206224. File: https://www.ncei.noaa.gov/data/oceans/archive/arc0148/0206224/4.6/data/0-data/HRS1507_608881_r2rnav/data/HRS1507_bestres.geoCSV (67.3 MB).
  - HRS1508 (2015-06-11 → 06-23, Part III, Georges Bank): NCEI 0206225. File: https://www.ncei.noaa.gov/data/oceans/archive/arc0148/0206225/3.4/data/0-data/HRS1508_608882_r2rnav/data/HRS1508_bestres.geoCSV (50.5 MB).
  - Each folder also holds a `_1min.geoCSV` (0.3–0.5 MB) and a `_control.geoCSV`.
- 2018 AAMVEM data-challenge page (describes `habcam_seq0`, 10,465 images 2720×1024): https://sites.google.com/view/aamvem/data-challenge. Its download host, challenge.kitware.com, is dead (CONNECT 502).

## Licence
- Tier:
  - **A** for the 2015 NEFSC subset, the bulk of the public data.
  - **U** for the CFF 2017–2019 subsets.
  - The navigation used for geo is CC0 / Public Domain Mark.
- Licence text (quote) + level read (file / record / collection) + URL:
  - File level, VIAME items: no licence or terms on any item or folder (`meta` is empty). Read via `https://viame.kitware.com/api/v1/item?folderId=…` and `/folder/{id}`.
  - Collection level, VIAME "Training Data" (https://viame.kitware.com/api/v1/collection/5e4c256ca0fc86aa03120c34): "This folder is reserved for public annotations which have been vetted by more than one user (and moved here by server admins) and can be used in training new models or combined with user-provided data." This is a usage statement, not a licence. VIAME Web's public settings only link a privacy notice (https://www.kitware.com/privacy).
  - Record level, NOAA HabCam dataset (data.gov DCAT entry harvested from NOAA, https://catalog.data.gov/dataset/habitat-mapping-camera-habcam): `license https://creativecommons.org/publicdomain/zero/1.0/`, `accessLevel non-public`, `rights otherRestrictions, unclassified`.
  - Record level, NOAA ISO XML (https://data.noaa.gov/waf/NOAA/nmfs/nefsc/iso/xml/27598.xml): no licence element. It gives `useConstraints otherRestrictions` with "Cite As: Northeast Fisheries Science Center, [Date of Access]: Habitat Mapping Camera (HABCAM) [Data Date Range], https://www.fisheries.noaa.gov/inport/item/27598." and the NOAA no-warranty disclaimer.
  - Provenance of the 2015 images: the cruise report (https://repository.library.noaa.gov/view/noaa/22504) says "NOAA HabCam V4 was deployed concurrently throughout the scallop strata … The total production of paired images was approximately 45 terabytes (TB) for raw tiff paired images. This translates into 7,906,000 image pairs". The camera is NOAA-owned and was run on a NOAA survey, so the images are a US-government work (17 U.S.C. §105), consistent with the CC0 on the NOAA record. The "non-public"/otherRestrictions fields describe access to NEFSC's internal database, not a reuse restriction, and no source contradicts CC0. Hence tier A.
  - CFF subsets (folders `US_NE_201[7-9]_CFF_HABCAM*`; the server path reveals `/data/public/Benthic/US_NE_2017_CFARM_HABCAM/`): Coonamessett Farm Foundation is a private non-profit. No licence is stated by Kitware, NOAA or CFF. Hence tier U.
  - Navigation (geo source), file level: `R2R-License: Creative Commons - Public Domain Mark 1.0` (https://www.ncei.noaa.gov/data/oceans/archive/arc0207/0260576/4.6/data/0-data/HRS1506_616376_r2rnav/bag-info.txt; same line in the HRS1507 bag). Record level: NCEI landing page 0260576, "This dataset has been dedicated to the public domain under the Creative Commons CC0 1.0 Universal (CC0 1.0) Public Domain Dedication."
- Attribution / citation text to store with every sample:
  - 2015 images: "Image: NOAA Northeast Fisheries Science Center, HabCam V4, 2015 Sea Scallop Survey (R/V Hugh R. Sharp cruise S1 15-01; HabCam cruise 201503); obtained from the VIAME Web public training data (Kitware, https://viame.kitware.com). Cite: Northeast Fisheries Science Center, [Date of Access]: Habitat Mapping Camera (HABCAM) [2015-05-17/2015-06-21], https://www.fisheries.noaa.gov/inport/item/27598."
  - Position: "Ship navigation: Rolling Deck to Repository (R2R) Program, cruise <HRS1506|HRS1507|HRS1508> (R/V Hugh R. Sharp), NOAA NCEI Accession <0260576|0206224|0206225>."
  - CFF images, if ever used: "Coonamessett Farm Foundation HabCam V3, <year>, via VIAME Web public training data".
- Embargo / moratorium / special terms: none stated. NOAA asks for the citation above. The InPort access procedure for the non-public archive is: "1. Formal request in writing usually to the data owner/contact or Center Director; … 3. If data is confidential then owner will determine if the data may be released".

## Media
- Types, counts, formats, resolution, total size, time range (full history for observatories)
  - Images only, no video.
  - **2015 NEFSC (`Corrected`)**:
    - 119,461 PNG, RGB 8-bit, **2720×1024 = left|right stereo pair side by side**. Each camera is 1360×1024 and the annotations refer to the left half.
    - 650.9 GB, about 5.45 MB median per file.
    - Filenames look like `201503.20150517.160624359.187700.png` (`<cruise>.<YYYYMMDD>.<HHMMSSmmm UTC>.<frame>.png`). Frames are roughly every 50th camera frame, about 8 s / 25 m apart along track.
    - Time range from 2015-05-17 07:34Z to 2015-06-21 01:25Z, spread over 25 image-days across 3 cruise legs.
    - Metadata in the same folder:
      - `metadata.txt`, 104,196 rows, columns `Imagename, Altitude, Mm_Pix, NumScallops, MeanSH, FOV, CDOM, Chl, Turbidity`, with **no lat/lon/depth**.
      - Annotations: `annotations.json` (COCO, 16 classes), its train/validation/test splits, `annotations.habcam_csv` and `auxiliary/annotations.csv` (VIAME CSV).
  - **CFF 2017/2018/2019/2019-part2 (`Left`)**:
    - 1,921 + 1,413 + 3,846 + 867 = 8,047 PNG, 1360×1024 RGB, about 2.8 MB each, about 22.6 GB in total.
    - Time ranges: 2017-07-08→07-21, 2018-07-15→07-20, 2019-06-28→07-29.
    - Filenames have the same pattern (cruise codes `201509` for 2017 and 2018, `201901` for 2019).
    - The `Raws` folders list 8,047 matching TIFs, but the one tested returns `file-does-not-exist`, so treat `Raws` as broken.
  - The full NEFSC archive (2012–present, millions of pairs per year) is not publicly available.
- Filters needed (aerial, on-deck, black frames, overlaps with other sources)
  - Crop the left 1360 px of the 2015 stereo PNGs, or keep both halves as two views of the same footprint. Do not train on the side-by-side pair.
  - Blank/black frames: a few PNGs are about 10 KB (for example `201503.20150517.073414892.4174.png`, 9,983 B). Drop files under 500 KB. This is about 0.1 %: 3 per 1,000 in the first listing page, 0 in two later pages.
  - Turbid frames: COCO class `dust cloud` and similar.
  - No aerial or on-deck frames are expected; the camera fires only near the bottom, and `Altitude` in metadata.txt is 0.81–2.99 m. Frames without a metadata.txt row (about 15 k) can still be geolocated from the filename.
  - The CDOM/Chl/Turbidity columns often hold placeholder-like values (650, 695, 460, 1), so do not trust them.
  - Overlaps:
    - VIAME `Unsorted/ChallengeData` tarballs contain 52,339 HabCam frames with identical names (`habcam/201503.2015…png`, from `fpaths_to_ids.json`, item 5e4c2584a0fc86aa03120c47). All are from the same 2015 cruise, so this is the same source, possibly raw rather than colour-corrected.
    - data.kitware.com folder 5dfcf845af2e2eed35a54210 (`HabCam2019_dataset1_samples`) holds 4 CFF 2019 frames plus 3-D products.
    - Dedup key: the filename stem (`<cruise>.<date>.<time>.<frame>`). Origin URL: `https://viame.kitware.com/api/v1/item/{_id}/download`.

## Geolocation
- Precision level(s) and approximate share of samples at each
  - **segment** for the 2015 NEFSC subset: about 94 % of public images (119.5 k).
  - **region** (no coordinates) for the CFF subsets: about 6 % (8.0 k).
  - No image carries its own coordinate in any public file.
- geo_source (exact field names / table), CRS, depth field, uncertainty
  - Columns `iso_time`, `ship_latitude`, `ship_longitude` of the R2R `r2rnav` "Best Resolution" GeoCSV `<cruise>_bestres.geoCSV`. It is 1-s ship GPS from a Furuno GP-37. Header: `#ellipsoid: WGS-84 (EPSG:4326)`, times in UTC (`Z`).
  - These are interpolated at the UTC timestamp in the image filename.
  - The filename time base is not documented. It was checked statistically against ship speed: with times read as UTC, 98.9 % of Part II images (HRS1507) fall at a ship speed of 2–4 m/s (HabCam tow speed). Read as EDT (+4 h) the share is 86.4 %, and 98.8 % vs 96.9 % for Part III. UTC is clearly the best fit.
  - NEFSC's own (non-public) `Image_Metadata.lat/lon` is described in InPort as "latitude from ship's GPS where image was recorded", so the result matches what NEFSC holds.
  - depth_m: **null**. Public files carry only `Altitude` (height above the seabed, 0.8–3 m). `bottom_depth` and `vehicle_depth` exist only in NEFSC's non-public database. Survey depths are 29–118 m per the cruise report.
  - geo_uncertainty_m = **300**. This covers layback of the towed vehicle behind the GPS antenna (about 1–3× water depth) plus unknown clock offset. Interpolation error with 1-s fixes is about 3 m.
  - R2R quirk: in all three cruises, fixes from about 01:01Z to 12:01Z each day are written as commented lines (`#2015-05-17T10:38:17Z,…`) without the speed/course columns. They sit in blocks that are not in time order. Their positions are continuous with the unflagged fixes (for example #10:19:38Z → #11:02:38Z → 12:01:40Z implies about 3 m/s). They are needed because about half of the images fall in those hours. The `_1min.geoCSV` omits them entirely, so do not use it for geo.
- How a sample maps to its coordinate
  - The Girder item `name` gives a UTC timestamp, which selects the cruise leg by date window and then the two bracketing 1-s fixes in that leg's bestres file.
  - Cruise windows (UTC):
    - HRS1506: 2015-05-16T11:52Z – 2015-05-26T00:00Z (Mid-Atlantic Bight; bbox −75.16…−71.46 E, 37.25…41.07 N)
    - HRS1507: 2015-05-27T00:00Z – 2015-06-11T00:00Z (Mid-Atlantic → Georges Bank; bbox −75.16…−67.00, 38.79…42.15)
    - HRS1508: 2015-06-11T00:00Z – 2015-06-24T00:00Z (Georges Bank; bbox −70.67…−66.35, 40.42…41.75)
  - Images by day: 05-17…05-25 (57.0 k in metadata.txt) → HRS1506; 05-27…06-09 (17.6 k) → HRS1507; 06-12…06-21 (29.6 k) → HRS1508.

### resolve_geo recipe
Input: one Girder item record (`name`, `folderId`, `_id`, `size`), as in `tests/fixtures/noaa_habcam/viame_items_page.json`, and optionally its `metadata.txt` row.
1. Match `name` against `^(\d{6})\.(\d{8})\.(\d{9})\.(\d+)\.(png|tif)$`. If it does not match, return `lat=lon=depth_m=None, geo_precision="none", geo_source="none", geo_inferred=False, geo_uncertainty_m=None`.
2. Build `t = datetime.strptime(date+hhmmss, "%Y%m%d%H%M%S").replace(tzinfo=UTC) + milliseconds(mmm)`.
3. If `folderId` is one of the CFF dataset folders (`5eb371608d01d968cc1642dd`, `5eb372788d01d968cc165ced`, `5eb375298d01d968cc168607`, `5eb376888d01d968cc16aadd`), or the name's cruise code is not `201503`, return:
   - `lat=lon=None, depth_m=None, geo_precision="region"`
   - `geo_source="VIAME folder US_NE_<year>_CFF_HABCAM (US Northeast shelf scallop grounds); no public per-image navigation"`
   - `geo_inferred=True, geo_uncertainty_m=None`
   - Optionally store `region_bbox=[-75.25,37.0,-66.0,42.1]` from InPort 27598 in the sample metadata, not as lat/lon.
4. Otherwise (2015 NEFSC), pick the cruise whose window from the table above contains `t`. If none does, return the "none" result from step 1 with `geo_source="no R2R nav window for timestamp"`.
5. Load and cache that cruise's `_bestres.geoCSV`. For every line:
   - Skip it if it is the `iso_time,` column line, or if it starts with `#` followed by a letter (`#dataset`, `#title`, …).
   - If it starts with `#` followed by a digit, strip the `#` and set `flagged=True`.
   - Split on `,`, parse `iso_time` (`%Y-%m-%dT%H:%M:%SZ`, UTC), `ship_longitude` and `ship_latitude`. Skip `NAN`.
   - Keep one fix per second, preferring unflagged. Sort by time.
6. Find fixes `a` (time ≤ t) and `b` (time > t). If either is missing, or `b.t − a.t > 10 s`, or the implied speed between a and b exceeds 8 m/s, return `lat=lon=None, geo_precision="none", geo_source="R2R nav gap"`, `geo_inferred=False`, `geo_uncertainty_m=None`.
7. Set `f = (t − a.t)/(b.t − a.t)`, `lat = a.lat + f·(b.lat − a.lat)`, `lon = a.lon + f·(b.lon − a.lon)`, and round to 6 dp.
8. Return:
   - `lat, lon`, `depth_m=None`, `geo_precision="segment"`
   - `geo_source="R2R r2rnav <cruise>_bestres.geoCSV ship_latitude/ship_longitude interpolated at filename UTC time (NCEI <accession>)"`
   - `geo_inferred=True`, `geo_uncertainty_m=300`
   - Also store `nav_flagged = a.flagged or b.flagged`, plus `altitude_m` from the metadata.txt `Altitude` column if the row exists, so that `Altitude` is never misread as depth.
9. The fixture's expected outputs are listed in `tests/fixtures/noaa_habcam/SOURCE.md`. For example, `201503.20150517.160624359.187700.png` → 37.687949, −74.641700, and the flagged-hour image `…103817616.70150` → 37.909550, −74.449934.

## Access & download recipe
- Enumeration (endpoints / listings / pagination), auth, rate limits
  - No auth is needed (Girder `public: true`).
  - Folder sizes: `GET https://viame.kitware.com/api/v1/folder/{id}/details` returns `{"nFolders":1,"nItems":119467}` for the 2015 folder.
  - Listing: `GET /api/v1/item?folderId={id}&limit=1000&offset={k}&sort=name`, which returns JSON items with `_id, name, size, folderId`. That is 120 pages for 2015 and 2–4 per CFF folder. Keep `*.png` and skip the 6 metadata items (`metadata.txt`, `annotations*.json`, `annotations.habcam_csv`).
  - Subfolders: `GET /api/v1/folder?parentType=folder&parentId={id}`.
  - No documented rate limit. Use about 1 listing request per second and at most 2 parallel file downloads.
  - Navigation: three static files at NCEI (URLs in Entry points). Directory listings are Apache-style and HTTP Range is supported (`Accept-Ranges: bytes`).
- How to fetch one media file; range / resume support
  - `GET https://viame.kitware.com/api/v1/item/{item_id}/download` streams the file (attachment).
  - For resume, use `GET /api/v1/item/{item_id}/files` → `[{"_id": file_id, "size": …}]`, then `GET /api/v1/file/{file_id}/download` with a `Range:` header. This was verified to return 206 with `content-range: bytes 0-1023/5894341`.
  - A Range on `/item/{id}/download` was not honoured once (the whole 9.5 MB body came back), so always use the `/file/` endpoint for partial requests.
  - Verify by size from the listing.
  - Store files as `<data_root>/noaa_habcam/images/<subset>/<name>`. Put the left-crop and the raw pair side by side, or crop at load time.
  - Put `metadata.txt`, the annotation files and the three `*_bestres.geoCSV` files (163 MB in total) under `<data_root>/noaa_habcam/metadata/`.
- Sampling strategy for a budget of N samples (diversity across sites and time)
  - Use only the 2015 folder unless the CFF licence is resolved.
  - Split N across the three legs as roughly 40 % HRS1506 (Mid-Atlantic), 25 % HRS1507 and 35 % HRS1508 (Georges Bank). This is between equal shares and proportional to the image counts of 57 k/17.6 k/29.6 k (+15 k frames without metadata rows).
  - Within a leg, sample evenly per image-day, then per UTC hour.
  - Enforce at least 60 s (about 200 m) between selected frames. Consecutive frames are about 8 s apart and visually near-duplicate.
  - Drop files under 500 KB and frames annotated as `dust cloud`.
  - Optionally stratify by `NumScallops > 0` vs `0` so that the scallop beds do not dominate.
  - The listing pages give sizes and names, so the whole selection can be made before downloading any pixels.

## Manual steps (human)
None are required for the public 2015 subset. Optional:
- To get more years, or NEFSC's own per-image `lat/lon/bottom_depth/vehicle_depth`, submit a formal NEFSC data request (InPort 27598 data access procedure; data steward listed there, NEFSC Population Dynamics Branch).
- To use the CFF 2017–2019 subsets, ask Coonamessett Farm Foundation or Kitware (viame-web@kitware.com) for a licence statement and any navigation logs.

## Fixtures
- tests/fixtures/noaa_habcam/viame_items_page.json: Girder item-listing page (3 items) of the 2015 NEFSC folder, exactly as served.
- tests/fixtures/noaa_habcam/metadata_txt_excerpt.csv: header + 4 rows of the 2015 `metadata.txt` (CRLF kept). It shows that there is no lat/lon and that `Altitude` is height above the bottom.
- tests/fixtures/noaa_habcam/HRS1506_bestres_excerpt.geoCSV: R2R 1-s navigation header plus 9 unflagged rows around the three fixture images and 4 `#`-flagged rows around a 10:38Z image, from byte ranges of the NCEI file.
- tests/fixtures/noaa_habcam/r2rnav_bag-info_HRS1506.txt: R2R bag-info containing `R2R-License: Creative Commons - Public Domain Mark 1.0` (licence evidence for the geo source).
- tests/fixtures/noaa_habcam/cff2017_items_page.json: 2-item listing of the CFF 2017 `Left` folder, for the region/tier-U branch.
- tests/fixtures/noaa_habcam/SOURCE.md: URLs, retrieval date, trimming and expected `resolve_geo` outputs.

## Short download instruction
1. List the 2015 NEFSC PNGs: `GET https://viame.kitware.com/api/v1/item?folderId=5e4eed5478ed364cd0f98b40&limit=1000&offset=k&sort=name` (119,461 PNG, 651 GB, no auth).
2. Download the sampled items via `/api/v1/item/{_id}/download`. Drop files under 500 KB and keep the left 1360 px of each 2720×1024 stereo pair.
3. Fetch the R2R 1-s nav `HRS1506/1507/1508_bestres.geoCSV` from NCEI accessions 0260576, 0206224 and 0206225. Parse the `#`-flagged rows too, then sort.
4. Geo: interpolate `ship_latitude/ship_longitude` at the filename's UTC time (segment, ±300 m, depth null). Skip the CFF 2017–19 folders (licence U, no nav).

## Open questions / risks
- The filename time base (UTC) is inferred statistically, not documented. A sub-minute clock offset between the HabCam and ship GPS cannot be ruled out; it would be about 3 m per second of offset.
- R2R flags about 11 h per day (≈01–12Z) of fixes in all three cruises, for an undocumented reason (the R2R service and its processing-description PDF returned 503). The positions look continuous, and this note uses them with `nav_flagged=true`. Check against R2R documentation when the service is reachable.
- No layback correction is applied. The ship antenna vs vehicle offset is probably 50–300 m in 30–110 m water, along the reciprocal of the course made good.
- The tier-A call for the 2015 subset rests on NOAA provenance plus the CC0 in the data.gov/NOAA catalogue record. The VIAME copy itself states no licence, and NOAA's record lists `accessLevel non-public`. If the project wants certainty, a one-line confirmation from NEFSC would settle it.
- CFF 2017–2019 (8 k images): licence unknown and no public navigation. Their `Raws` TIFs appear missing on the server.
- habcam.whoi.edu (tracklines, area boundaries, per-cruise data) was unreachable from here. Its trackline downloads might hold timestamped tracks for other cruises; check via the Wayback snapshot `web.archive.org/web/20230331120710/https://habcam.whoi.edu/data-and-visualization/`.
- The VIAME public collection is a community/Kitware-hosted copy with no SLA. Mirror what is needed. The 2018 challenge host (challenge.kitware.com) is already dead.
- The full NEFSC HabCam archive (2012–present, "No Archiving Intended" at NCEI) is far larger than the public subset, but it is only available by request.
