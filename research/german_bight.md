# German Bight seafloor drift videos (HE415/HE416, HE436, Helgoland 2011) (`german_bight`)
Status: verified · researched 2026-10-06 · verified 2026-10-06

## Summary
This key covers three PANGAEA data tables of seafloor video from the German Bight (SE North Sea), all recorded by AWI's Wadden Sea Station Sylt:
- **PANGAEA.907386**: R/V Heincke cruises HE415/HE416, Feb–Mar 2014. 87 rows: 87 Kongsberg AVI and 55 GoPro MP4.
- **PANGAEA.909999**: HE436, Nov 2014. 45 rows: 45 AVI and 44 GoPro MP4.
- **PANGAEA.831731**: 13 MPEG-2 transects off Helgoland, Jun 2011.

That is 244 video files: 145 station videos plus 99 simultaneous GoPro HD clips. The total is about 180 GB, of which about 170 GB is GoPro 1080p.

Every record is CC BY (4.0 for the Heincke tables, 3.0 for Helgoland), read at record level, so the tier is **B**.

Each table row gives one ship-GPS position per video, which is **station** precision (`geo_inferred=true`).
- Heincke: the ship drifts about 30–240 m during a 4–16 min drift. We use a 200 m uncertainty.
- Helgoland: start and end positions are given, so we use their midpoint, with an uncertainty of 62–139 m.

Verdict: **ingest**. Everything is anonymous HTTPS with Range support. About 40 % of the files sit on tape; the first request returns HTTP 503 and recalls the file automatically, and it was online after about 7 minutes.

Two data errors must be handled:
- One GoPro clip is linked to the wrong row.
- 5 of 132 Heincke rows have a longitude typo of 0.5–4.3 km.

Six sibling cruise tables in the same format (HE400, HE474, HE478, HE501, HE502, HE505; 274 more stations, 2013–2018) should be added to this key.

## Entry points
- Datasets (landing pages):
  - https://doi.pangaea.de/10.1594/PANGAEA.907386 (HE415/HE416)
  - https://doi.pangaea.de/10.1594/PANGAEA.909999 (HE436)
  - https://doi.pangaea.de/10.1594/PANGAEA.831731 (Helgoland 2011). This is a child of the collection https://doi.pangaea.de/10.1594/PANGAEA.831732, which has no textfile export.
- Tab-separated export (header block `/* … */`, then a TSV table): `https://doi.pangaea.de/10.1594/PANGAEA.<id>?format=textfile`
- Licence metadata (JSON-LD): `https://doi.pangaea.de/10.1594/PANGAEA.<id>?format=metadata_jsonld`
- Media hosts:
  - Heincke: `https://hs.pangaea.de/platforms/towed_systems/video/exdata/{HE415|HE436}/<file>`. HE416 rows also live in the `HE415/` folder with an `HE415_` prefix.
  - Helgoland: `https://hs.pangaea.de/Movies/mielck_etal_2014/<file>.mpg`
  - Directory listing is forbidden (403).
- Ship station logs (DSHIP event lists, which hold the "Video camera" events with start and end time and position): `https://www.pangaea.de/ddi/<CRUISE>.tab?retr=events/Heincke/<CRUISE>.retr&conf=events/CruiseReportText.conf&format=textfile`. This works for HE415, HE416 and HE436.
- Navigation:
  - HE436 station list and 10-min track: https://doi.pangaea.de/10.1594/PANGAEA.840690
  - HE436 1 Hz master track: https://hs.pangaea.de/nav/mastertrack/he/HE436_mastertrack.zip (9.3 MB; not downloaded)
  - HE400 master track: https://doi.pangaea.de/10.1594/PANGAEA.843704
  - No master track was found on PANGAEA for HE415 or HE416.
- Helgoland RoxAnn 1 Hz single-beam data (depth enrichment only): https://doi.pangaea.de/10.1594/PANGAEA.831686
- Papers:
  - Michaelis et al. 2019, Continental Shelf Research 175:30–41, doi:10.1016/j.csr.2019.01.011. Open-access PDF read from https://www.vliz.be/imisdocs/publications/ocrd/323837.pdf.
  - Michaelis et al. 2019, Journal of Sea Research 144:78–84, doi:10.1016/j.seares.2018.11.009 (no open PDF found).
  - Mielck et al. 2014, Estuarine, Coastal and Shelf Science 143:1–11, doi:10.1016/j.ecss.2014.03.016. PDF read from https://epic.awi.de/id/eprint/35383/1/Mielck_et_al_2014-Predicting_spatial_kelp_abundance_in_shallow_waters.pdf.
- Sibling video tables in the same format (not in the seed): PANGAEA.907382 (HE400), 910009 (HE474), 910939 (HE478), 907338 (HE501), 907337 (HE502), 907340 (HE505). See Open questions.

## Licence
- Tier: **B** (CC BY 4.0 for 907386 and 909999; CC BY 3.0 for 831731).
- Licence text (quote) + level read (file / record / collection) + URL:
  - **Record level**, read from the tab export header:
    - PANGAEA.907386: "License: Creative Commons Attribution 4.0 International (CC-BY-4.0) (URI: https://creativecommons.org/licenses/by/4.0/)" (https://doi.pangaea.de/10.1594/PANGAEA.907386?format=textfile)
    - PANGAEA.909999: the same text (https://doi.pangaea.de/10.1594/PANGAEA.909999?format=textfile)
    - PANGAEA.831731: "License: Creative Commons Attribution 3.0 Unported (CC-BY-3.0) (URI: https://creativecommons.org/licenses/by/3.0/)" (https://doi.pangaea.de/10.1594/PANGAEA.831731?format=textfile). The parent collection 831732 also says `https://creativecommons.org/licenses/by/3.0/`.
  - The JSON-LD of each record agrees: `"license": "https://creativecommons.org/licenses/by/4.0/"` (or `/by/3.0/` for 831731), `"conditionsOfAccess": "unrestricted"`, `"isAccessibleForFree": true` (fixture `pangaea_909999_jsonld.json`).
  - **File level:** there is no file-level licence. The video files are served with `content-disposition: attachment` only. The GoPro `udta` box holds only firmware, lens and camera IDs (`HD3.11.01.00`, `H3B+…`), and the AVI headers have no INFO chunk. No source contradicts the record licence.
  - Not to be confused: the CSR 2019 *article* is CC BY-NC-ND 4.0 ("This is an open access article under the CC BY-NC-ND license"). That applies to the paper's text and figures, not to the PANGAEA data. Do not ingest figures from it.
- Attribution / citation text to store with every sample (the `Citation:` line of the matching record, plus the licence):
  - 907386: `Papenmeier, Svenja; Hass, H Christian (2019): Video observation during R/V Heincke cruise HE415 and HE416 in the German Bight with link to raw data files [dataset]. Alfred Wegener Institute - Wadden Sea Station Sylt, PANGAEA, https://doi.org/10.1594/PANGAEA.907386. CC BY 4.0`
  - 909999: `Papenmeier, Svenja; Hass, H Christian (2019): Video observation during R/V Heincke cruise HE436 in the German Bight with link to raw data files [dataset]. Alfred Wegener Institute - Wadden Sea Station Sylt, PANGAEA, https://doi.org/10.1594/PANGAEA.909999. CC BY 4.0`
  - 831731: `Mielck, Finn; Bartsch, Inka; Hass, H Christian; Wölfl, Anne-Cathrin; Bürk, Dietmar; Betzler, Christian (2014): Links to sea-bottom video files along 13 transects off Helgoland [dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.831731. CC BY 3.0`
- Embargo / moratorium / special terms: none. No `Moratorium` line appears in any header, and access is "unrestricted". About 40 % of the files are on tape, which is an access delay, not a restriction (see Access).

## Media
- **Types and counts:**

  | Dataset | Rows | Kongsberg/MPEG station videos | GoPro HERO3+ Black MP4 | Other |
  |---|---|---|---|---|
  | 907386 (HE415 19–21 Feb 2014, HE416 28 Feb–5 Mar 2014) | 87 (abstract: "85 stations"; Spots_01 is split into 3 parts) | 87 `.avi` | 55 `.MP4` | 55 `.LRV` (GoPro low-res proxy), 55 `.THM` (GoPro ~5 KB thumbnail) |
  | 909999 (HE436 17–18 Nov 2014) | 45 (44 stations; 012 is split into 012-1 and 012-2) | 45 `.avi` | 44 `.MP4` (He436_014 has none) | none |
  | 831731 (Helgoland 15–17 Jun 2011) | 13 | 13 `.mpg` | none | none |
  | **Total** | 145 | 145 | 99 | 55 LRV, 55 THM |

- **Formats and resolution** (read from file headers with Range requests of at most 16 KB, or 313 KB for one GoPro `moov`):
  - **Kongsberg AVI:** RIFF AVI, H.264, 640×480, 29.97 fps, no audio stream.
    - `He415_Spots_01-1.avi`: 61,756 frames = 34.3 min, 175,314,120 B.
    - `HE415_Greifer_AG3_030.avi`: 6,749 frames = 3.75 min, 17.9 MB.
    - The bitrate is about 5 MB per minute.
  - **GoPro MP4:** HERO3+ Black (`CAME H3B+`), H.264 1920×1080 plus AAC audio, with `moov` at the start of the file.
    - `HE415_Greifer_AG1_007_HD.MP4`: 350 s, 1,316,183,905 B.
    - `HE436_GOPRO_001.MP4`: 471 s, 1,709,542,405 B.
    - The GoPro clock runs on CET (UTC+1). See Geolocation.
  - **Helgoland MPG:** MPEG-2 program stream, 704×576, 25 fps, 4:3 (PAL), 110–469 MB per file.
- **Sizes:**
  - 34 AVIs measured by HEAD: 5–175 MB, median 22 MB, mean 32 MB. That projects to about 4.3 GB for all 132 AVIs, roughly 14 h of footage.
  - 5 MP4s measured by HEAD: 1.32–2.17 GB, mean 1.72 GB. That projects to about 170 GB for 99 files, roughly 11 h, recorded at the same times as the AVIs.
  - MPG total: exactly 3,100,876 kB (3.18 GB), from the `File size [kByte]` column. Durations total 80.5 min (2.8–12.7 min each).
  - LRV: 32–53 MB each, about 2.3 GB in all.
  - Overall: about 180 GB, or about 7.5 GB if the GoPro MP4s are skipped.
- **Time range:** 2011-06-15 to 2014-11-18 for the seeded tables. The sibling tables add 2013-05 (HE400), 2016-10 (HE474), 2017-03 (HE478), 2017-11 (HE501), 2017-12 (HE502) and 2018-03 (HE505).
  - This is not a fixed-site observatory, so there is no archive to enumerate beyond these cruises.
- **Recording setup:**
  - Heincke (CSR 2019 §2.2): "The camera systems were equipped with two ahead-oriented cameras, artificial light sources and a laser scale reference. Recordings were taken from the drifting ship (max. speed: 1 knot) while the camera system was kept as close to the seafloor as possible."
  - Helgoland (Mielck 2014 §2.3.1): a Kongsberg OE14-106/107 camera, "recorded at low vessel speed of approximately 0.5 knots".
  - Scenes: sand, gravel, cobbles and boulders with epifauna (Metridium, Flustra, Alcyonium), and kelp (Laminaria hyperborea) off Helgoland. Water depth is 24–47 m for the seeded Heincke tables (`Bathy depth [m]` 24.4–47.0) and 2–18 m for Helgoland.
- **Filters needed:**
  - **On-deck, surface and descent frames at the start and end of clips.** The GoPro starts before deployment: `HE436_GOPRO_001.MP4` begins at 03:02:06 UTC, while the DSHIP "Video camera" event starts at 03:03 UTC and the table time is 03:05:51 UTC. Trim the first and last 60 s, then drop frames with no seafloor (low texture or blue water column) and above-water frames.
  - **Sediment clouds** when the frame touches down; **turbid, low-visibility** German Bight water; **dark frames** (many stations were filmed at night under artificial light). Use a blur/variance filter and a near-black filter.
  - **Laser dots** are visible scale references. Keep them, but note that they are present.
  - **Duplicates and overlaps:**
    - AVI and GoPro MP4 of the same station are two simultaneous views; give them the same `station_id` so they go to the same split.
    - `.LRV` is a low-res copy of the MP4 and `.THM` is a thumbnail. Skip both.
    - `Spots_01-1/-2/-3` and `He436_012-1/-2` are parts of one station.
    - Possible overlap with the `pangaea_images` key, if its discovery also picks up video tables. Deduplicate by media URL or DOI.
    - BenthicNet's PANGAEA harvester takes image URL columns only, so it does not include these videos.
  - **Not underwater:** the sister PANGAEA tables "CILAS raw data and grab sample photos" (for example 899248 and 899288) hold on-deck sediment photos. Do not ingest them under this key.

## Geolocation
- **Precision levels:** 100 % `station`.
  - Heincke 907386 and 909999: one ship-GPS position per video file. 2 of the 132 rows have no depth.
  - Helgoland 831731: start and end positions per transect, reduced to their midpoint.
  - Nothing qualifies as `segment`: no per-frame navigation with gaps of 10 s or less is linked to the videos (see "Better than station?" below).
- **geo_source fields** (CRS WGS 84 decimal degrees, PANGAEA GEOCODE parameters; times are UTC):
  - **907386:** columns `Longitude`, `Latitude`, `Date/Time` (HH:MM:00), `Bathy depth [m]` (positive down, 25.2–47.0 m, none missing), plus `Content` (station label, for example `Profile Greifer_AG1_005`) and `Event` (`HE415-track` / `HE416-track`).
    - Longitude comes before Latitude in this table, so parse by column name.
  - **909999:** `Latitude`, `Longitude`, `Date/Time` (to the second), `Bathy depth [m]` (24.4–46.3 m; empty for He436_012-1 and 012-2). There is no station label; the station number is in the filename (`He436_NNN[-k].avi`, `HE436_GOPRO_NNN[-k].MP4`).
  - **831731:** `Latitude`/`Longitude` (start), `Latitude 2`/`Longitude 2` (end), `Date/Time` / `Date/time end`, the same positions in UTM zone 32U (`UTM east [m] (start)`, …), `File size [kByte]` and `File name`. There is **no depth column**.
- **What the position means** (Heincke):
  - CSR 2019 §2.2: "Positioning information during the recordings was received from the ship GPS". The camera hangs below the drifting ship, so there is a layback of up to about the water depth.
  - We matched all 132 Heincke rows to the DSHIP "Video camera" events: 87/87 for HE415/416 and 44/45 for HE436.
    - The table position lies a median of 21 m (907386) and 15 m (909999) from the event start position.
    - Event start-to-end drift: median 46 m (max 182 m) and 64 m (max 237 m).
    - Event duration: median 5 min and 8 min (max 37 min).
  - **Uncertainty is therefore 200 m.** That covers the drift, the layback and the GPS error.
- **Known coordinate errors:** 5 rows disagree with the DSHIP event log by more than 300 m, all in longitude only, at the same time and latitude. The distances below are to the event *start*; the recipe's `min(start, end)` gives 651, 4,221, 464, 503 and 3,226 m.

  | Row | Disagreement |
  |---|---|
  | `Spots_03` | 651 m |
  | `Greifer_AG1_010` | 4,253 m |
  | `Greifer_AG1_011` | 483 m |
  | `Greifer_AG1_017` | 535 m |
  | `He436_029` | 3,226 m |

  - For He436_029 the HE436 10-min track (PANGAEA.840690) gives 2014-11-18T00:30 at 54.69528 N 7.15924 E. That matches the event log (7.15950), so the table's 7.10933 is a typo.
  - Do not silently replace the coordinate: keep the table value and inflate the uncertainty (recipe step 6).
- **GoPro row mis-assignment in 907386:** row `Profile Greifer_AG1_005` links `HE415_Greifer_AG1_006_HD.{MP4,LRV,THM}`, and row AG1_006 has no GoPro links.
  - The MP4 `mvhd` creation_time is 2014-02-21 12:38:36 in CET, which is 11:38 UTC. That equals the `Date/Time` of row AG1_006 (11:38), not that of AG1_005 (11:11). The two coordinates are 2.1 km apart.
  - Map every file to a row by the station token in its filename. This is the only mismatch among the 252 file links of 907386 (87 AVI + 55 each of MP4, LRV, THM).
- **Helgoland:**
  - Transects are 63–218 m long, at about 0.25 m/s in 2–18 m of water, with DGPS on the vessel (Mielck 2014 §2.2).
  - We use the midpoint of start and end, with uncertainty = half the length + 30 m, which gives 62–139 m.
  - Optional depth enrichment: PANGAEA.831686 (RoxAnn, 1 Hz DGPS with `Bathy depth [m]`) has 47–857 points within 50 m of each midpoint, with medians of 4.0–17.4 m. If used, mark it in `geo_source` as a nearby-sounding depth (not tide-corrected). Its timestamps (Feb 2011 and 2011-06-16 00:47–04:58) do not overlap any video, so it cannot be used as navigation.
- **Better than station? No, not worth it now.**
  - HE436 and HE400 have 1 Hz ship master tracks. However:
    - The Kongsberg AVIs carry no timestamps, and the 907386 times are rounded to the minute.
    - The camera's layback from the ship is unknown.
    - The whole drift is usually 50–100 m.
  - HE415 and HE416 have no master track on PANGAEA; HE416 has only a 160-point thermosalinograph track, PANGAEA.859780.
  - The GoPro `mvhd` creation_time (CET, about ±1 s) would allow a ship-position interpolation (`segment`, ship position rather than camera position) for HE436 GoPro clips if it is ever needed.

### resolve_geo recipe
Input: one data row (a dict of column name to string) from a PANGAEA `?format=textfile` export, the dataset id, and the media URL being resolved. Optionally, the matching DSHIP event rows.
1. **Pick the row for the media file.** For 907386, take the station token from the filename: `re.sub(r'^(He|HE)415_|(_HD)?\.\w+$', '', basename)` gives for example `Greifer_AG1_006`. Use the row whose `Content` minus `Profile ` equals that token, not the row the URL was listed in. For 909999 and 831731, the listing row is correct.
2. **Coordinates.** For datasets other than 831731: `lat = float(row['Latitude'])`, `lon = float(row['Longitude'])`, matched by exact column name.
   - For 831731: if `Latitude 2` and `Longitude 2` are both present, set `lat = (Latitude + Latitude 2)/2` and `lon = (Longitude + Longitude 2)/2`, and let `L` = the haversine distance between the two points. Otherwise use the start point and set `L = 440` (twice the longest observed transect).
   - If lat or lon is missing or unparseable, return `lat=None, lon=None, depth_m=<step 3>, geo_precision="none", geo_source="PANGAEA.<id>: no Latitude/Longitude in row", geo_inferred=False, geo_uncertainty_m=None`.
   - Reject values outside 53–56.5 N and 3–9 E with the same "none" result. That is a German Bight / Dogger Bank sanity box that also covers the sibling tables.
3. **Depth.** Set `depth_m = float(row['Bathy depth [m]'])` if the cell is non-empty; it is already positive down. If it is empty (He436_012-1/-2) or the column is absent (831731), set `depth_m = None`. Never use the PANGAEA `Elevation` coverage line.
4. **Precision.** Set `geo_precision = "station"` and `geo_inferred = True`, since one position applies to every frame of the video.
5. **Uncertainty and source:**
   - Heincke: `geo_uncertainty_m = 200`, `geo_source = "PANGAEA.<id> data table columns Latitude/Longitude (ship GPS at drift-video station, WGS 84); depth: Bathy depth [m]"`.
   - 831731: `geo_uncertainty_m = round(L/2 + 30)`, `geo_source = "PANGAEA.831731 midpoint of Latitude/Longitude (start) and Latitude 2/Longitude 2 (end) of the video transect, WGS 84"`.
6. **Optional QC (Heincke, when event lists are cached).**
   - Find the `Method/Device == "Video camera"` event with `Date/Time - 5 min <= row Date/Time <= Date/Time end + 5 min`. (A ±2 min window, as first written, matches only 74 of 87 rows of 907386 and misses the typo row `Spots_03`, whose minute-rounded time is 4 min before its event; ±5 min matches 87/87 and 44/45 with no ambiguous match.)
   - Let `d` = min(haversine to the event start, haversine to the event end).
   - If `d > 300`, set `geo_uncertainty_m = round(d + 200, -1)`, append `"; QC: table position differs by <d> m from DSHIP event <label>"` to `geo_source`, and keep the table coordinate.
   - If no event matches, keep step 5.
7. **Worked fixture results** (`tests/fixtures/german_bight/`):

   | Row | lat, lon | depth_m | uncertainty | Notes |
   |---|---|---|---|---|
   | 907386 `Spots_01-1` | 54.86993, 6.71440 | 45.0 | 200 | |
   | 907386 MP4 `HE415_Greifer_AG1_006_HD.MP4` | 54.98333, 6.66713 | 41.0 | 200 | uses row AG1_006, not AG1_005 |
   | 909999 `He436_001` | 54.79000, 6.00733 | 41.6 | 200 | QC: d = 37 m |
   | 909999 `He436_012-1` | 54.90007, 6.64600 | None | 200 | |
   | 909999 `He436_029` | 54.69607, 7.10933 | 33.2 | 3430 | after QC with `HE436/032-2`, d = 3,226 m |
   | 831731 `Video01` | 54.2102501, 7.8941948 | None | 108 | |

   All rows return `geo_precision="station"` and `geo_inferred=True`.

## Access & download recipe
- **Enumeration:**
  - `GET https://doi.pangaea.de/10.1594/PANGAEA.<id>?format=textfile` for 907386, 909999 and 831731 (and optionally 907382, 910009, 910939, 907338, 907337, 907340). Each returns one TSV of 7–34 KB, with no pagination.
  - Split at the line `*/`. The next line is the header. Every cell that starts with `https://hs.pangaea.de/` is a media link.
    - Video columns: `URL movie (avi)`, `URL movie (MP4)`, `URL movie (mpeg-format)`; in the siblings also `URL movie`, `URL file (avi)`, `URL file (MP4)`, `URL movie (part N)` and `URL file (asf file)`.
    - Skip `URL file (LRV)` and `URL file (THM)`.
  - Licence: from the header `License:` line, cross-checked against `?format=metadata_jsonld`.
  - No auth. Keep to 1 request/s or less per host; `doi.pangaea.de`, `www.pangaea.de` and `hs.pangaea.de` are separate hosts.
- **Fetching one file:**
  - `GET` the hs.pangaea.de URL. An online file answers `200` with `accept-ranges: bytes`, `etag`, `last-modified`, `content-length` and `content-disposition: attachment`.
  - Resume with `Range: bytes=<n>-`; `206` was verified.
  - Store `etag` and `content-length` in the manifest and check the size after download.
- **Tape staging:**
  - About 40 % of the files are offline: 33 of 82 probed answered `HTTP 503`, with `content-type: text/html`, `retry-after: 7` (2 on 2026-10-07), `refresh: 5` and a page reading "The requested file He415_Spots_06.avi is loading from tape... Download will start automatically after a minute".
  - Any request, including HEAD, triggers the recall; no login or ticket is needed.
  - Measured: `He415_Spots_06.avi` (91 MB) was first requested at about 14:35 UTC, still answered 503 at 14:41:20, and answered 200 at 14:42:50. So it took 7–8 min.
  - Never save a 503 HTML body as media; check `content-type` starts with `video/`.
  - Recommended pattern: HEAD a batch of 10–20 URLs at 1 request/s, wait 10 min, then GET them, and requeue any that still return 503 after 15–30 min.
  - The project `Http` client retries a 503 only a few times with `Retry-After` 7 s, so tape files will land in `metadata/failures.jsonl`. Rerun the script later; by then they are online.
- **Sampling for a budget of N videos:**
  1. Use the Kongsberg AVI / MPEG files first: they are 32 MB on average, and one per station.
  2. Round-robin across datasets and cruises (HE415, HE416, HE436, Helgoland, plus the siblings). Within a cruise, round-robin across areas: `Content` prefixes `Spots`, `AG1`, `AG3`, `AG4`, or a 0.1° lat/lon grid for HE436, so that Sylt Outer Reef, Borkum Reef Ground and the Helgoland kelp all appear.
  3. Prefer one part per station (`-1`).
  4. Add GoPro MP4s (1.3–2.2 GB, 1080p) only after every station has its AVI, and only where the budget is in bytes rather than in clips.
  5. For frames, take 1 frame per 2–5 s after trimming the first and last 60 s. Each frame inherits the video's station geo.

## Manual steps (human)
- None. Tape recall is automatic on the first request; it only needs waiting and a rerun.

## Fixtures
- `tests/fixtures/german_bight/pangaea_907386_excerpt.tab`: PANGAEA.907386 export with the full header and 4 rows (Spots_01-1; AG1_005 holding the AG1_006 GoPro links; AG1_006; an HE416 row in the HE415 folder).
- `tests/fixtures/german_bight/pangaea_909999_excerpt.tab`: PANGAEA.909999 export with the full header and 4 rows (001 normal, 012-1 with empty depth, 014 with no MP4, 029 with the longitude typo).
- `tests/fixtures/german_bight/pangaea_831731_excerpt.tab`: PANGAEA.831731 export with the full header and 3 transects that have start and end positions.
- `tests/fixtures/german_bight/events_HE436_excerpt.tab`: the DSHIP event list for HE436, with 1 grab event and the 4 video events that match the 909999 rows.
- `tests/fixtures/german_bight/pangaea_909999_jsonld.json`: the untrimmed JSON-LD record with `license` and `conditionsOfAccess`.
- `tests/fixtures/german_bight/SOURCE.md`: URLs, retrieval date, trimming, and the expected distances.
- The full 907386 export also exists, unchanged, at `tests/fixtures/_core/pangaea_907386.tab`.

## Short download instruction
1. `scripts/download/german_bight.sh --dry-run` reads the 3 PANGAEA tab exports (CC BY 4.0/3.0, tier B; station geo from `Latitude`/`Longitude`).
2. `scripts/download/german_bight.sh --budget N` fetches station videos from hs.pangaea.de (anonymous, Range OK, 1 req/s). AVIs are about 32 MB each; GoPro MP4s are 1.3–2.2 GB each.
3. About 40 % of files are on tape: the first request returns 503 and starts the recall. Rerun after 10–15 min to fetch the files listed in `metadata/failures.jsonl`.
4. Trim the first and last 60 s of each clip (deck and descent). Group AVI and MP4 by station; skip `.LRV` and `.THM`.

## Open questions / risks
- **Adapter vs findings** (`src/aquasource/adapters/german_bight.py`, not changed by this research):
  - It takes one file per row, preferring `URL movie (MP4)`. That downloads about 170 GB of GoPro and skips the 132 Kongsberg AVIs. Consider emitting both files per row with a shared station id, or preferring the AVI.
  - It assigns the GoPro `HE415_Greifer_AG1_006_HD.MP4` to row AG1_005, which is 2.1 km off. Map by filename token instead.
  - It returns `geo_uncertainty_m=None`. Use 200 m for Heincke and `L/2+30` for Helgoland.
  - For 831731 it uses the start point rather than the midpoint.
- **Coordinate typos:** 5 of 132 Heincke rows have longitude errors of 0.5–4.3 km against the DSHIP log. For He436_029 the master track proves the table wrong; the four HE415 cases cannot be checked against an independent track. The QC step inflates uncertainty. A report to PANGAEA (info@pangaea.de, by a human) could get the tables corrected.
- **Sibling tables:** PANGAEA.907382 (HE400, 2013, 114 MPG), 910009 (HE474, 2016, Dogger Bank, 25 AVI + 25 MP4), 910939 (HE478, 2017, 43 AVI + 42 MP4), 907338 (HE501, 2017, 63 MP4 + 63 AVI), 907337 (HE502, 3 stations, MP4 + ASF) and 907340 (HE505, 2018, 25 MP4 + 26 ASF) are all CC BY 4.0, by the same authors and in the same format.
  - Recommend adding them to `dataset_ids`. Their column names differ (`URL file (avi)`, `URL movie` = MP4 in HE501, `.asf`), so the media-column list needs extending.
  - Their media files were not probed: there were no HEAD requests, to avoid triggering tape recalls.
- **Sizes are projections:** 49 of 82 probed files answered 200 with a size. The remaining files were not probed, to avoid mass tape recalls; totals extrapolate from the mean size per type.
- **Duration and quality are unknown per file:** how much of each clip is usable seafloor (versus deck, descent or sediment clouds) is unmeasured. Michaelis et al. note that the videos were quality-controlled before analysis but publish only the analysed subset counts (CSR 2019 Table 1).
- **Time base:**
  - The 907386 `Date/Time` values are rounded to the minute and sit within about ±5 min of the DSHIP event start. The 909999 values fall 0.7–2.9 min after the event start.
  - The GoPro clocks run on CET (+1 h). Any future `segment` work must correct for this.
- **Tape behaviour may change:** the 503 page and its timings were observed once, for a 91 MB file. Recall of 2 GB MP4s may take longer, so keep retries patient (≥ 30 min) and polite.
- **Requests made in this research:** our HEAD probes triggered recalls of about 33 files. That is harmless, but further probing should stay small.
- **Unpublished HE415 video deployments (found in verification):** the HE415 DSHIP list has 114 `Video camera` events, but 907386 holds only the 32 from 19 and 21 Feb 2014. The 82 events of 13–14 Feb (a transect along about 8.06 E, 53.96–54.47 N) and 24 Feb 2014 (around Helgoland) have no video on PANGAEA. A PANGAEA search for "Video observation during R/V Heincke" returns exactly 8 tables (the 2 seeded Heincke ones plus the 6 siblings), so those videos are not published elsewhere under that title. Only a request to the PIs could recover them.
- **HE505 sibling timestamps are not acquisition times (found in verification):** in PANGAEA.907340 all 26 `Date/Time` values fall in 13 minutes (2018-03-14T18:10:49 to 18:23:44) although the stations are up to 30 km apart. Use its coordinates but not its times. HE505 used a "C-Technics Camera" plus GoPro, not the Kongsberg camera.
- **Helgoland paper vs data:** Mielck et al. 2014 §2.3.1 describes "8 concurrent video transect[s]" of about 1,200 m and 60 min in total; PANGAEA.831731 lists 13 transects totalling about 1,564 m and 80.5 min. Use the data table.
- **Download script header** (`scripts/download/german_bight.sh`, not changed here): it says "CC BY 4.0 per PANGAEA record" (831731 is CC BY 3.0) and "one AVI is ~175 MB" (that is the largest AVI; the median is about 22 MB).

## Verification (2026-10-06)
Independent re-check against primary sources (requests made 2026-10-07 UTC with the project User-Agent; metadata only, plus three header Range reads of at most 4 KB and two HEADs).

**Checked and confirmed**
- Licence, record level, tier **B**:
  - `?format=textfile` headers of https://doi.pangaea.de/10.1594/PANGAEA.907386 and https://doi.pangaea.de/10.1594/PANGAEA.909999: "License: Creative Commons Attribution 4.0 International (CC-BY-4.0) (URI: https://creativecommons.org/licenses/by/4.0/)".
  - https://doi.pangaea.de/10.1594/PANGAEA.831731?format=textfile: "License: Creative Commons Attribution 3.0 Unported (CC-BY-3.0) (URI: https://creativecommons.org/licenses/by/3.0/)".
  - `?format=metadata_jsonld` of 907386, 909999, 831731 and the parent 831732: `license` by/4.0, by/4.0, by/3.0, by/3.0; `conditionsOfAccess` "unrestricted". The HTML landing page of 907386 shows the same licence. No NC, ND or moratorium term anywhere.
  - The CC BY-NC-ND notice is in the CSR article PDF (https://www.vliz.be/imisdocs/publications/ocrd/323837.pdf), not in the data records.
  - The three citation strings in the note match the `Citation:` lines verbatim.
- Columns and counts, from the live exports:
  - 907386: `Event, Content, Longitude, Latitude, Date/Time, Bathy depth [m], URL movie (avi), URL file (LRV), URL movie (MP4), URL file (THM)`; 87 rows, 87 AVI, 55 MP4, 55 LRV, 55 THM, all in the `HE415/` folder; depth 25.2–47.0 m, none missing.
  - 909999: `Latitude, Longitude, Date/Time, Bathy depth [m], URL movie (avi), URL movie (MP4)`; 45 rows, 45 AVI, 44 MP4; depth 24.4–46.3 m, empty for He436_012-1 and 012-2.
  - 831731: start/end `Latitude`/`Longitude`, `Latitude 2`/`Longitude 2`, UTM, `File size [kByte]` (sum 3,100,876), 13 MPG; no depth column.
  - Total 244 videos (145 station + 99 GoPro).
- GoPro mis-assignment: row `Profile Greifer_AG1_005` links `HE415_Greifer_AG1_006_HD.*`; a 1 KB Range read of that MP4 gives `mvhd` creation 2014-02-21 12:38:36 (file 1,457,159,957 B). `HE436_GOPRO_001.MP4` gives 2014-11-17 04:02:06 and 471 s (1,709,542,405 B), consistent with a CET camera clock (03:02 UTC, DSHIP event 03:03 UTC).
- He436_029 typo: https://doi.pangaea.de/10.1594/PANGAEA.840690?format=textfile has `2014-11-18T00:30 54.69528 7.15924`; the DSHIP event HE436/032-2 has 7.15950; the table has 7.10933 (3,226 m off).
- DSHIP lists (https://www.pangaea.de/ddi/HE415.tab?..., HE416, HE436): with a ±5 min window, 87/87 and 44/45 rows match (He436_020 has no event), median table-to-event-start distance 21 m and 15 m, drift median 46/64 m, max 182/237 m. The farthest ship position from the table point is ≤ 200 m for 125 of 126 rows (median 48 m), so the 200 m station uncertainty is honest.
- Helgoland positions are in water: every transect midpoint has 47–857 RoxAnn soundings (PANGAEA.831686, 2.8 MB export) within 50 m, median depth 4.0–17.4 m. All coordinates are N/E with positive signs, as expected for the North Sea.
- Fixtures: every line of the three `*_excerpt.tab` files and of `events_HE436_excerpt.tab` occurs verbatim and in order in the live responses; `pangaea_909999_jsonld.json` and `tests/fixtures/_core/pangaea_907386.tab` are byte-identical to the live files. The SOURCE.md URLs are correct.
- Access: `HEAD He415_Spots_01-1.avi` gave 200, `video/x-msvideo`, 175,314,120 B, `accept-ranges: bytes`; its header has `vidsH264`, 640×480, 29.97 fps and 61,756 frames (34.3 min). `HEAD Video06_2011-06-16T15_20_00.mpg` gave 503 `text/html` with `retry-after: 2` (tape). The HE436 master track zip is 9,783,698 B.
- Siblings: the 6 tables exist, are CC BY 4.0, and hold 114 + 25 + 43 + 63 + 3 + 26 = 274 rows; the PANGAEA search above finds no other Heincke video table.
- Precision `station` with `geo_inferred=true` is right: one ship position per video; no per-frame navigation linked to the files. Not an observatory, so no archive enumeration is needed.

**Corrected**
- Helgoland uncertainty range: 62–139 m (the summary said 84–140 m and the Geolocation section 61–139 m).
- 907386 has 252 file links, not 284.
- Heincke depth: 24–47 m for the seeded tables, not 18–47 m.
- QC recipe step 6: the time window must be ±5 min, not ±2 min (±2 min misses 13 of 87 rows, including the typo row Spots_03). The per-row distances in the typo table are to the event start; the recipe's `min(start, end)` values are 651, 4,221, 464, 503 and 3,226 m.
- Added risks: 82 unpublished HE415 video deployments, HE505 timestamps, the Helgoland paper vs data count, the download script header.

No fixture file needed changing.
