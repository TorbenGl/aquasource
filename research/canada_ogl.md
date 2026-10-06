# Canada open data: GSC seafloor photographs + DFO Fundy Isles drift-camera imagery (`canada_ogl`)
Status: researched · researched 2026-10-06

## Summary
This key combines two federal Canadian open-data collections, both under the Open Government Licence - Canada 2.0 (tier B):
- **GSC "Seafloor photographs, offshore Canada"** (NRCan). It holds 20,017 full-resolution PNG seabed photos (~153 GB) from 1,804 stations on 78 expeditions, 1965-2015. Coverage runs from the Atlantic shelf and slope to the Arctic and the Pacific. Every photo has its own row with PHOTO_LAT/PHOTO_LONG/WATER_DEPTH. About half are true per-image fixes (USBL or vessel GPS). The rest repeat one station coordinate for every photo at the station.
- **DFO Fundy Isles drift-camera survey** (Bay of Fundy). Per-image WGS84 coordinates are published for all 5,081 Nikon D850 stills (2022-2024). However, only the **2022 subset** of the media is online: 386 stills (~10.2 GB of ZIPs) and 23 MP4 video files (~6.4 GB, ~2.8 h of downward video), in the companion record 8ea6c28a. The 2023-2024 media (4,695 stills, ~28 h of downward and ~28.5 h of forward video) are only "searchable in our imagery library" and would need a request to DFO.

Verdict: a good tier-B source with image and station precision, downloadable over plain HTTPS with Range support, and no human step for the online part. The seed's "needs_human" flag applies only to the optional 2023-2024 Fundy media. A CKAN search found only one more Canadian-portal dataset with downloadable underwater media, N-MARINE (region-level geo only). See Open questions.

## Entry points
- GSC collection record: https://open.canada.ca/data/en/dataset/44cbbdc0-d33d-abe7-b08a-f5872bc0a48a (CKAN API: https://open.canada.ca/data/api/3/action/package_show?id=44cbbdc0-d33d-abe7-b08a-f5872bc0a48a)
- GSC ArcGIS MapServer (station points with a PHOTOS URL list, CSV_FILE, EXCEL_FILE): https://maps-cartes.services.geo.ca/server_serveur/rest/services/NRCan/GSC_Seabed_Photo_Collection/MapServer/0 (French twin: .../NRCan/CGC_Collection_photos_fonds_marins/MapServer). maxRecordCount 1000; 1,804 features.
- GSC media and per-station CSV/XLS (Apache index, Range OK): https://ftp.maps.canada.ca/pub/nrcan_rncan/raster/marine_geoscience/Seabed_Photo_Collection/ (78 expedition folders: `<EXPED>/<EXPED>_<STN4>.csv`, `<STN4>_<CAM>_<PHOTO>_full_res.png`, thumbnails `<STN4>_<CAM>_<PHOTO>.png`)
- GSC FGDB (321 KB): https://ftp.maps.canada.ca/pub/nrcan_rncan/Seas_Mer/SeabedPhotoCollection_CollectionPhotosFondsMarins/GSC_Seabed_Photo_Collection.gdb.zip
- GSC Expedition Database (source system): https://ed.marine-geo.canada.ca/ (the old `ed.gdr.nrcan.gc.ca` PHOTO_GIS_LINK URLs now redirect to a splash page)
- DFO Fundy main record (locations for 2022-2024): https://open.canada.ca/data/en/dataset/f9098f77-b2e1-423d-8950-eeabd7bba85b
  - https://api-proxy.edh-cde.dfo-mpo.gc.ca/catalogue/records/f9098f77-b2e1-423d-8950-eeabd7bba85b/attachments/BayFundy_ImageLocations.csv (560 KB, 5,081 rows, cp1252)
  - .../BayFundy_TransectVideo.csv (73 transects; lists the video file names), .../Data_Dictionary.csv, .../VideoTransect_ImageryLocations.zip (FGDB, 550 KB)
  - MapServer: https://egisp.dfo-mpo.gc.ca/arcgis/rest/services/open_data_donnees_ouvertes/near_seafloor_video_image_two_year_survey_fundy_isles/MapServer (layer 0 images, layer 1 transect lines; no attachments)
- DFO Fundy 2022 companion record (media): https://open.canada.ca/data/en/dataset/8ea6c28a-3d6c-47ef-8cf7-56790ee0c7f5
  - base: https://api-proxy.edh-cde.dfo-mpo.gc.ca/catalogue/records/8ea6c28a-3d6c-47ef-8cf7-56790ee0c7f5/attachments/
  - `Photos_CON002-20220921T124142_20220921T130732.zip` (2.14 GB), `Photos_CON003-...zip` (1.80 GB), `Photos_CON004-...` (1.26 GB), `Photos_CON005-...` (1.26 GB), `Photos_CON006-...` (1.53 GB), `Photos_CON007-...` (1.03 GB), `Photos_CON008-...` (1.20 GB)
  - `Video_CON002_003.zip` (2.08 GB), `Video_CON004_005.zip` (1.49 GB), `Video_CON006.zip` (1.00 GB), `Video_CON007_008.zip` (1.82 GB)
  - `Start_End_Video_Transect_D_vexillum_BayFundy_2022.csv` (496 20-s segments with start/end lat/lon), `PercentageCover_Image_D_vexillum_BayFundy_2022.csv` (386 stills with lat/lon/depth)
- Paper for the 2022 survey: Teed et al. 2024, https://doi.org/10.3391/bir.2024.13.3.12 (CC BY 4.0)
- CKAN search API used for discovery: https://open.canada.ca/data/api/3/action/package_search

## Licence
- Tier: **B** (OGL-Canada 2.0)
- Licence text (quote) + level read (file / record / collection) + URL:
  - Level: **record**. No file-level licence exists: no licence file sits in the FTP folders, and the ZIP/PNG files carry no licence metadata. Record level is consistent in three places: the CKAN `license_id: "ca-ogl-lgo"` (`license_title: "Open Government Licence - Canada"`, `license_url: https://open.canada.ca/en/open-government-licence-canada`) on 44cbbdc0, f9098f77 and 8ea6c28a, and the ISO 19115 `resourceConstraints` of each record (CSW GetRecordById at https://csw.open.canada.ca/geonetwork/srv/csw), which read "Open Government Licence - Canada (http://open.canada.ca/en/open-government-licence-canada)". The GSC ISO record also states "No constraint".
  - Licence text (https://open.canada.ca/en/open-government-licence-canada, version 2.0): "The Information Provider grants you a worldwide, royalty-free, perpetual, non-exclusive licence to use the Information, including for commercial purposes, subject to the terms below. You are free to: Copy, modify, publish, translate, adapt, distribute or otherwise use the Information in any medium, mode or format for any lawful purpose. You must, where you do any of the above: Acknowledge the source of the Information by including any attribution statement specified by the Information Provider(s) and, where possible, provide a link to this licence. If the Information Provider does not provide a specific attribution statement ... you must use the following attribution statement: Contains information licensed under the Open Government Licence – Canada." Exemptions: personal information, third-party rights, official symbols, and other IP rights such as patents and trade-marks.
- Attribution / citation text to store with every sample:
  - GSC: "Contains information licensed under the Open Government Licence – Canada. Source: Geological Survey of Canada (Natural Resources Canada), Seafloor photographs, offshore Canada (2020), https://open.canada.ca/data/en/dataset/44cbbdc0-d33d-abe7-b08a-f5872bc0a48a" (no specific attribution statement is given, so the OGL default sentence is required).
  - DFO Fundy (the statement given in the record): "Lawton P, Teed L. Near-seafloor drift transect video and high-resolution digital still imagery from a three-year survey in the Fundy Isles region of the lower, western Bay of Fundy. Published November 2025. Coastal Ecosystems Science Division, Fisheries and Oceans Canada, St. Andrews, N.B." For 2022 media, also add the record's own statement: "Teed LL, Goodwin C, Lawton P, Lacoursière-Roussel A, Dinning KM (2024) Multiple perspectives on the emergence of the invasive colonial tunicate Didemnum vexillum Kott, 2002 in the western Bay of Fundy, Atlantic Canada. BioInvasions Records 13(3): 713–738, https://doi.org/10.3391/bir.2024.13.3.12". In both cases add "Contains information licensed under the Open Government Licence – Canada" and the licence URL.
- Embargo / moratorium / special terms: none. The OGL non-endorsement clause applies (do not imply DFO/NRCan endorsement). Personal information is not licensed, and none is expected in seabed photos.

## Media
- **GSC Seabed Photo Collection** (complete listing crawled 2026-10-06)
  - 20,017 `*_full_res.png` files totalling ~152.7 GB, plus 20,260 thumbnails (~1.45 GB). There are 1,804 per-station CSVs and 1,804 XLS files, across 78 expedition folders.
  - Expedition years 1965-2015, parsed from the expedition codes; the record's temporal extent is 1964-12-31 to 2019-12-30. By decade: 1960s 2,394 photos/3.1 GB · 1970s 2,393/4.7 GB · 1980s 1,523/7.0 GB · 1990s 2,077/11.4 GB · 2000s 9,157/62.4 GB · 2010s 2,473/64.1 GB.
  - Content: older material is scanned film (CAMERA_TYPE Benthos/BIO/GSCA 35mm/Other; FILM_TYPE Print, Slide, Ektachrome), e.g. 1888×1279 or 1224×1848 RGBA PNG at 6-7 MB. Newer material is digital (Tritech Scorpio, "Digital Benthic", "4K Camera System"), e.g. 3072×2048 and 5184×3456 PNG at up to ~26 MB. A few frames are digital-video grabs (FILM_TYPE "Digital Video").
  - Bounding box: lat 38.92-74.78, lon -134.19 to -27.79. Depths range from a few m (estuaries) to >2,600 m. `WATER_DEPTH` can be "Unknown".
- **DFO Fundy Isles**
  - Full survey (2022-2024): 73 drift transects, 5,081 stills (~127 GB), downward video ~31 h/~603 GB and forward video ~28.5 h/~279 GB (2023-24 only) according to the transect table, depths 15-188 m below chart datum.
  - Online (2022, CON002-CON008, 2022-09-21/22): 386 Nikon D850 JPEGs (8256×5504, ~26-30 MB each). EXIF holds UTC time and no GPS. Inside each `Photos_CON00x*.zip` the stills are split into nested ZIPs (`<n>_CON00x-<start>_<end>_<A-D>.zip`) plus some loose JPEGs.
  - Online video: 23 MP4 files (SubC 1Cam Alpha 6, downward-facing, recorded "1080 progressive/60 frames per s" per Teed et al. 2024), named like `CON006-20220922_T145006_1Cam_.mp4`, each ~10 min, 1.5-520 MB. Total ~6.4 GB zipped. The transect table gives ~2.8 h of downward video for 2022 (fields `Downward_video_HMMSS` are H:MM:SS packed as integers, e.g. 2617 = 26 min 17 s).
  - Note: the transect table lists ~44 GB of 2022 downward video, while the published MP4s total ~6.4 GB, so the online files are re-encoded or a subset.
- Filters needed:
  - GSC film scans may include film borders, data-chamber imprints, handwritten labels or scanner artefacts. Some frames show the ROV manipulator, the trigger weight or a compass (PHOTO_CONTENTS_DESCRIPTION_OTH e.g. "Other - Manipulating arms"), and PHOTO_COMMENTS flags some frames as "dark". Run a black/overexposure filter and a border/label crop check.
  - Fundy video: the camera descends and ascends outside the on-bottom window. Clip to `Start_time_UTC`/`End_time_UTC` (BayFundy_TransectVideo.csv), or keep only frames inside a row of the 2022 segment table. Turbid or too-high segments were removed from that table. Altitude > 1.7 m means FOV is blank. 10-cm red laser dots are visible.
  - Overlaps: the 2022 stills are the same files in f9098f77 (locations) and 8ea6c28a (media and percent cover), so dedup on `Image_file_name`. The GSC photos are the same images as in the NRCan Expedition Database. No overlap is known with other aquasource sources. Record the origin URL per file, i.e. the FullResolutionImageURL or the ZIP URL plus the member path.

## Geolocation
- Precision levels and approximate share of the ~20.4k online samples:
  - GSC **image** ≈ 47% (~9.4k photos with distinct per-photo positions; USBL or vessel GPS, mostly 1998+).
  - GSC **station** ≈ 53% (~10.6k photos where every photo at a station has the same PHOTO_LAT/PHOTO_LONG; all pre-1998 and some later). These shares are photo-weighted estimates from one station CSV per expedition (78 sampled).
  - Fundy stills: **image** (all 386 online 2022 stills have coordinates; 7 of 5,081 overall have empty Latitude/Longitude, all on CON098 in 2024).
  - Fundy video frames: **segment** (20-s segments with start/end coordinates; the nearest fix is ≤ 10 s from any frame).
- geo_source, CRS, depth field, uncertainty:
  - GSC: per-station CSV columns `PHOTO_LAT`, `PHOTO_LONG` (decimal degrees, record CRS EPSG:4326), `WATER_DEPTH` (m, positive; "Unknown" means missing), `HORIZONTAL_POSITIONAL_ACCURACY`. The latter takes three values in the sample, by row:
    - "no correction made for antenna offset or wire angle; positional uncertainty of greater than plus/minus 20 percent of water depth" (~80%)
    - "Ultra-Short Baseline (USBL) positioning on camera used; position accurate to within 5 percent of water depth" (~14%)
    - "antenna offset corrected  no correction for wire angle; position accurate to plus/minus 20 percent of water depth" (~6%)
    The map layer has `LATITUDE`/`LONGITUDE` rounded to 3 decimals (station position); use it only as a fallback.
  - Fundy stills: `BayFundy_ImageLocations.csv` columns `Latitude`, `Longitude` ("decimal degrees (WGS84)" per the data dictionary) and `Bathymetry_m_Bathymétrie_m` ("below chart datum", taken from 1-10 m multibeam). Sign convention: 2022 values are negative, 2023-24 values positive, and `0` means missing, so use the absolute value and treat 0 as null. `Altitude_m` is camera height above the seabed.
  - Uncertainty: Teed et al. 2024 report that 2022 positions came from surface GNSS, with "spatial offsets from the survey vessel [that] could range up to 40 m astern to 5–10 m port or starboard". Use 50 m. The 2023-24 positioning method is not documented; assume 50 m.
  - Fundy video: `Start_End_Video_Transect_D_vexillum_BayFundy_2022.csv` columns `Start_latitude`, `Start_longitude`, `End_latitude`, `End_longitude`, `Start_depth_m`, `End_depth_m` (negative, BCD), `Start_segment_time_UTC_HHMMSS`, `Video_file_name`, `Distance_covered_m`.
- How a sample maps to its coordinate:
  - GSC: the PNG name `<STN4>_<CAM>_<PHOTO>_full_res.png` in folder `<EXPED>` maps to the CSV row (EXPED_CD, STATION_NUM, CAMERA_NUM, PHOTO_NUM), or directly via the `FullResolutionImageURL` column. That column uses http://, so rewrite it to https://.
  - Fundy still: the JPEG member name equals `Image_file_name_Image_fichier_nom` (e.g. `CON002-20220921T124142.jpg`).
  - Fundy video frame: the absolute UTC time is the file start time from the MP4 name plus the frame offset. Then look up the matching segment row. Names differ between the CSV (`CON_00220220921_T124140_1Cam_.mp4`) and the ZIP (`CON002-20220921_T124140_1Cam_.mp4`), so normalise both with the regex `CON_?(\d{3})-?(\d{8})_?T(\d{6})` to the key (transect, date, time).

### resolve_geo recipe
```
num(x): float(x) or None for '', 'NA', 'Unknown'

A) GSC photo row r (per-station CSV), with n_distinct = number of distinct (PHOTO_LAT, PHOTO_LONG) over all rows of that station CSV
 1. lat, lon = num(r.PHOTO_LAT), num(r.PHOTO_LONG)
    if None: fall back to the map-layer feature (EXPED_CD, STATION_NUM) LATITUDE/LONGITUDE -> precision 'station',
    geo_source 'GSC MapServer layer 0 LATITUDE/LONGITUDE', inferred True, uncertainty max(step 3, 1000);
    if that is missing too -> all None, precision 'none'.
 2. depth_m = num(r.WATER_DEPTH)   (positive metres; None if 'Unknown')
 3. acc = r.HORIZONTAL_POSITIONAL_ACCURACY
      'USBL' in acc                       -> frac 0.05, floor 10
      'antenna offset corrected' in acc   -> frac 0.20, floor 50
      otherwise ('no correction ...')     -> frac 0.20, floor 100
    year = int(m[1]) if (m = re.match(r'^(19[6-9]\d|20[0-2]\d)(\d{3}|[A-Z])', EXPED_CD)) else 1900 + int(EXPED_CD[:2])
    if year < 1990: floor = max(floor, 1000)     # pre-GPS ship navigation (Loran-C/Decca/Transit); estimate
    unc = max(frac * depth_m, floor) if depth_m else max(floor, 1000)
 4. if n_distinct > 1: precision 'image', inferred False
    else:              precision 'station', inferred True, unc = max(unc, 500)  # drift between casts
 5. geo_source = 'GSC <EXPED>_<STN>.csv PHOTO_LAT/PHOTO_LONG; WATER_DEPTH; ' + acc
    return lat, lon, depth_m, precision, geo_source, inferred, round(unc)

B) Fundy still row r (BayFundy_ImageLocations.csv, cp1252; or PercentageCover_..._2022.csv for 2022)
 1. lat, lon = num(r.Latitude), num(r.Longitude)
 2. d = num(r['Bathymetry_m_Bathymétrie_m'] or r['Depth_m']); depth_m = abs(d) if d not in (None, 0) else None
 3. if lat or lon is None -> (None, None, depth_m, 'none', 'BayFundy_ImageLocations.csv Latitude/Longitude empty', False, None)
 4. return lat, lon, depth_m, 'image',
    'DFO f9098f77 BayFundy_ImageLocations.csv Latitude/Longitude (WGS84, surface GNSS) + Bathymetry_m', False, 50

C) Fundy 2022 video frame (mp4 name, offset_s)
 1. key = regex CON_?(\d{3})-?(\d{8})_?T(\d{6}) on the mp4 name; t = datetime(date, time, UTC) + offset_s
 2. seg = row of Start_End_Video_Transect_D_vexillum_BayFundy_2022.csv with the same key
    (from Video_file_name) and Start_segment_time <= t < Start_segment_time + 20 s
 3. if seg: f = (t - seg_start)/20
       lat = Start_latitude + f*(End_latitude - Start_latitude); lon likewise
       depth_m = abs(Start_depth_m + f*(End_depth_m - Start_depth_m))
       return lat, lon, depth_m, 'segment', '8ea6c28a Start_End_Video_Transect... Start/End_latitude/longitude, linear interp',
              True, round(50 + Distance_covered_m/2)
 4. else if a still of the same transect has |t_still - t| <= 10 s: use its lat/lon/depth -> 'segment', inferred True, 50 + 1.0 m/s * |dt|
 5. else (frame outside the published usable segments, likely descent/turbid): mark the frame for exclusion; if kept,
    use the centroid of that transect's still coordinates -> 'station', inferred True,
    uncertainty = max distance from the centroid to any still of the transect (<= ~2.6 km)
```

## Access & download recipe
- Enumeration:
  - GSC: GET the Apache index at `.../Seabed_Photo_Collection/` (78 folders), then each folder index. This lists the CSVs and `*_full_res.png` files with sizes. Alternatively query MapServer layer 0 (`/query?where=1=1&outFields=*&resultOffset=0|1000&resultRecordCount=1000&f=json`, 2 pages) for EXPED_CD, STATION_NUM and CSV_FILE.
    - Bug: for `82FOGO-ISLE` the CSV_FILE URL is a 404, because the real file is `82FOGO_ISLE/82FOGO_ISLE_0024.csv`. Prefer the folder listing.
    - The layer's PHOTOS field lists only ~14.5k of the photos (it skips some, e.g. every third photo at 2003029/87). The per-station CSVs and the folders are complete.
    - Fetch all 1,804 CSVs (~30 min at 1 req/s) to build the manifest.
  - Fundy: the CKAN `package_show` resource URLs (above); CSVs are small.
  - Auth: none.
  - Rate limits: none documented. Stay at ≤ 1 req/s per host (ftp.maps.canada.ca, api-proxy.edh-cde.dfo-mpo.gc.ca, maps-cartes.services.geo.ca).
- Fetch one media file:
  - GSC: `GET https://ftp.maps.canada.ca/pub/nrcan_rncan/raster/marine_geoscience/Seabed_Photo_Collection/<EXPED>/<STN4>_<CAM>_<N>_full_res.png`. Apache serves `Accept-Ranges: bytes`, so `curl -C -` resume works and HEAD works.
  - Fundy: `GET .../attachments/<zip>`. Ranges are supported (206 with Content-Range). HEAD returns 404 on this proxy, so use `Range: bytes=0-0` to read the size. Members are deflated, so either download the whole ZIP (1.0-2.1 GB each, 16.6 GB total for 2022) with `curl -C -`, or use a remote-zip reader to pull single members. Still images sit inside nested ZIPs (350-500 MB each), which must be fetched whole.
  - Store under `<data_root>/canada_ogl/images` (GSC PNG, Fundy JPG), `<data_root>/canada_ogl/videos` (Fundy MP4), and `<data_root>/canada_ogl/metadata` (CSV, JSON, licence).
- Sampling for N samples:
  - Stratify GSC by expedition × decade. Take at most k = ceil(N_gsc / 1,804) photos per station, preferring stations with per-photo positions (USBL/GPS) and spreading over Atlantic, Arctic and Pacific (lon < -100 = Pacific).
  - Fundy: take all 386 stills (one 16.6 GB pull covers stills and video). Sample video frames at the midpoint of each usable 20-s segment (≤ 496 frames), or 1 frame per 5 s inside segments for more.
  - Suggested split for small N: ~90% GSC, ~10% Fundy.

## Manual steps (human)
- None for the online part (GSC full collection + Fundy 2022 media).
- Optional: the 2023-2024 Fundy media (CON029-CON121: 4,695 stills, ~28 h downward + ~28.5 h forward video) have published per-image coordinates but no download links. Request them from DFO.CESDDataRequest-DSECDemandededonnes.MPO@dfo-mpo.gc.ca, the record's contact address, citing record f9098f77-b2e1-423d-8950-eeabd7bba85b. This must be done by a human; the pipeline must not send email.

## Fixtures
- tests/fixtures/canada_ogl/fundy_image_locations_sample.csv: header + 6 real rows of BayFundy_ImageLocations.csv (cp1252, CRLF). Covers 2022 negative depth, 2023/2024 positive depth, a CON098 row with empty lat/lon and depth 0, and the last row.
- tests/fixtures/canada_ogl/fundy2022_video_segments_sample.csv: header + 3 rows of the 2022 20-s video segment table (UTF-8 BOM).
- tests/fixtures/canada_ogl/gsc_station_query.json: ArcGIS MapServer layer 0 query response with 3 station features (outSR=4326; PHOTOS/CSV_FILE URLs).
- tests/fixtures/canada_ogl/gsc_photos_95006_7392_sample.csv: GSC per-station CSV, header + 3 rows (station-level, "no correction" accuracy, film print).
- tests/fixtures/canada_ogl/gsc_photos_2010020_0026_sample.csv: GSC per-station CSV, header + 3 rows (image-level, USBL).
- tests/fixtures/canada_ogl/licence.txt: OGL-Canada 2.0 text.
- tests/fixtures/canada_ogl/SOURCE.md: URLs, retrieval date and trimming for each file, plus the Teed et al. 2024 quote used for the Fundy uncertainty.

## Short download instruction
GSC: crawl https://ftp.maps.canada.ca/pub/nrcan_rncan/raster/marine_geoscience/Seabed_Photo_Collection/ (78 folders). Each `<EXPED>_<STN>.csv` gives PHOTO_LAT/LONG, WATER_DEPTH, accuracy and FullResolutionImageURL. GET the `*_full_res.png` files (20,017 files, ~153 GB, Range OK, 1 req/s).
DFO Fundy 2022: GET the 7 `Photos_CON00x*.zip` and 4 `Video_*.zip` from https://api-proxy.edh-cde.dfo-mpo.gc.ca/catalogue/records/8ea6c28a-3d6c-47ef-8cf7-56790ee0c7f5/attachments/ (16.6 GB; HEAD unsupported, Range OK).
Join stills by filename to BayFundy_ImageLocations.csv (record f9098f77); place video frames with Start_End_Video_Transect_D_vexillum_BayFundy_2022.csv.
Licence OGL-Canada 2.0 (tier B); store the attribution per sample.

## Open questions / risks
- The share of GSC station-level vs image-level photos (~53/47%) is extrapolated from one station per expedition. The download script should compute it exactly from all 1,804 CSVs.
- Pre-1990 GSC positions: the navigation system and datum (NAD27 vs WGS84) are not stated. The 1,000 m uncertainty floor is an estimate and the record does not give it. The positional accuracy field says only "greater than ±20% of water depth".
- `82FOGO_ISLE` stations plot near 42.4 N, -67.1 W (Georges Bank), not at Fogo Island. "FOGO ISLE" may be a ship name. Coordinates look plausible but are unverified.
- GSC: 20,260 thumbnails vs 20,017 full-res files, so ~240 photos may lack a full-res file. Use the CSV `FullResolutionImageURL` and skip on 404.
- GSC film scans: whether labels, borders or data blocks are burned into the PNGs was not inspected, because no images were downloaded. Check during the first pull.
- Fundy: the published 2022 MP4s (~6.4 GB) are much smaller than the 43.7 GB of 2022 downward video in the transect table. They may be re-encoded, and resolution/fps were not verified because `moov` is at the end of each file. Forward-facing video for 2022 is "NA".
- Fundy 2023-2024 positioning method (vessel GNSS vs acoustic) is undocumented. The sister St. Anns Bank survey says APOS USBL was acquired only in 2024.
- The segment-precision rule says "gap ≤ 10 s". Fundy navigation fixes are 20 s apart, but every frame is ≤ 10 s from a fix and the camera drifts at ~0.3 m/s. This was judged acceptable, but a reviewer may prefer 'station'.
- OGL exemption: "third party rights the Information Provider is not authorized to license". Some GSC cruises used partner platforms (e.g. 2001ROPOS), and no third-party credit is shown. Low risk.
- The DFO api-proxy URLs set session cookies. Downloads work without them, but the proxy might change. Keep the CKAN record IDs as the stable reference.
