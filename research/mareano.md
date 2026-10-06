# MAREANO (Norway) seabed video and stills (`mareano`)
Status: needs_human · researched 2026-10-06

## Summary
MAREANO is Norway's national seabed mapping programme, run by HI/IMR, NGU and Kartverket since 2006. It has filmed 3,908 seabed video lines at 3,787 reference stations, from the Skagerrak/North Sea margin to the Barents Sea, Svalbard and the Arctic Mid-Ocean Ridge (56.5–81.7°N, 3°W–37°E, 2006–2026). Video is recorded with towed video rigs (e.g. Campod) and ROVs, such as Ægir6000 on the 2025–2026 Arctic Mid-Ocean Ridge cruises. Two parts can be used today without registration:
- **340 curated video frame grabs** (2006–2021, ~40–2,730 m deep). Each has its own lat/lon, depth, cruise and video line in the open WFS / OGC-API layer `mareano_stasjoner:bilder_biologi`. The image files themselves are in the HI media archive (hi.imageshop.no), whose terms say **CC BY-SA 4.0**. That makes them **tier C** at geo precision **image**.
- **All station and video-line positions** (NLOD / CC BY 4.0) from the Geonorge layer and the Marbunn database.

The raw video archive (thousands of hours, with navigation) is not public. It is shared on request through IMR's S3 cruise-data store (datahjelp@hi.no). No licence is stated for it (U), so a human has to request access. Verdict: harvest the stills now in the C shard, and send the video request.

## Entry points
- MAREANO images and video page: https://www.mareano.no/bilder-og-video. It links the HI media archive, the NGU photo archive and a YouTube playlist.
- Geolocated frame-grab layer (OGC API Features, GeoServer): https://kart.hi.no/mareano/ogc/features/v1/collections/mareano_stasjoner:bilder_biologi (340 features)
  - WFS 2.0: `https://kart.hi.no/mareano/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=mareano_stasjoner:bilder_biologi&outputFormat=application/json`
  - Geonorge metadata: https://kartkatalog.geonorge.no/metadata/305852ff-5686-4454-ab11-b3ef55a9f5c7 ("Mareanobilder, biologi")
- Video reference stations: https://kart.hi.no/mareano/ogc/features/v1/collections/mareano_stasjoner:videostasjoner_aarlig (3,787 features). Geonorge metadata: https://kartkatalog.geonorge.no/metadata/8bb5b637-51a8-4f0d-905a-378493ae2354. WFS: https://wfs.geonorge.no/skwms1/wfs.mareanovideostasjoner
- Video-line start/end positions per cruise (Marbunn): `https://marbunn-ekstern.hi.no/apps/marbunn/v1/cruises` (46 cruises) and `https://marbunn-ekstern.hi.no/apps/marbunn/v1/showstationsinmap?cruiseno=<cruise>` (GeoJSON LineStrings; `Equipment`="Video", `type`=2)
- HI media archive (image files): https://hi.imageshop.no/1636899/Search?Q=mareano (646 hits). Terms: https://hi.imageshop.no/1636899/StaticText/TermsOfUse
- Raw cruise data, including video files and navigation (on request): https://s3browser.hi.no. Request through datahjelp@hi.no, as described in cruise report https://www.hi.no/en/hi/nettrapporter/toktrapport-en-2026-17, §9.
- Not usable or not relevant:
  - YouTube playlist https://www.youtube.com/playlist?list=PLpvb7g3qiPsuEvYwQ3B7uurBD1vxVpOmP: 48 edited clips, no CC licence seen.
  - NGU photo archive https://foto.ngu.no/fotoweb/archives/5001-NGUs-fotoarkiv/?q=mareano: 27 items, CC BY 4.0, but maps, fieldwork and on-deck photos only.
  - Layer `mareano_stasjoner:bilder_terreng`: 42 bathymetry renderings, not underwater.
  - Layer `mareano_biologi:mareanovideo_fil`: 1 ROV video record whose ownCloud link returns 404.
  - PANGAEA: no MAREANO imagery (search "mareano" returns 2 unrelated datasets).

## Licence
- Tier: **C** for the 340 geolocated frame grabs and other MAREANO underwater stills in the HI media archive. This is the conservative choice; see the discrepancy below. **U** for the raw video archive, because no licence is stated. **Excluded**: archive items under "Illustrasjonar og teikningar" and "Kart" (CC BY-NC-ND 4.0), and the YouTube clips.
- Licence text (quote) + level read (file / record / collection) + URL:
  - Image files, collection level (file level gives only a credit line). HI Imageshop terms, https://hi.imageshop.no/1636899/StaticText/TermsOfUse: "Bileta i dette arkivet er til fri deling og gjenbruk med CC-BY-SA 4.0 lisens dersom ikkje anna er oppgitt. … Bileta under Illustrasjonar og teikningar og Kart er lisensierte med CC BY-NC-ND 4.0 lisens." Translation: images in this archive may be freely shared and reused under CC BY-SA 4.0 unless stated otherwise; illustrations/drawings and maps are CC BY-NC-ND 4.0. Asset pages (e.g. https://hi.imageshop.no/1636899/Detail/Index/8626077) show only "Kreditering: MAREANO / Havforskningsinstituttet".
  - Image-link layer, record level. Geonorge record 305852ff…: `"AccessConstraints": "Åpne data"`, `"OtherConstraintsLinkText": "Creative Commons BY 4.0 (CC BY 4.0)"`. The abstract reads: "Punktdatasett med lenker til bilder … Bildene er et lite utvalg stillbilder fra video".
  - Station positions, record level. Geonorge record 8bb5b637…: "Norsk lisens for offentlige data (NLOD)", "Ingen begrensninger på bruk er oppgitt."
  - Biological datasets, collection level. https://www.mareano.no/kart-og-data/biologisk-data_test: "Datasettene kan fritt brukes under disse lisensvilkårene: CC BY 4.0 og NLOD - fritt bruk mot at kilden oppgis."
  - Discrepancy: the layer record says CC BY 4.0 and the file host says CC BY-SA 4.0. The two are compatible in direction: complying with BY-SA also satisfies BY. So the images go into the share-alike shard (C) until IMR confirms CC BY 4.0, which would make them tier B. The mareano.no footer "Alle rettigheter reservert" covers the website only.
  - Raw video. Cruise report 2026007006 §9 says only that "Video files (with metadata/navigation data) … are shared upon request" and gives no licence, so U.
  - All quotes are in `tests/fixtures/mareano/licence.txt`.
- Attribution / citation text to store with every sample: "Photo: MAREANO / Havforskningsinstituttet (Institute of Marine Research, Norway), www.mareano.no — CC BY-SA 4.0". Use the per-asset `Kreditering` string from Imageshop verbatim; some read "Havforskningsinstituttet/MAREANO" or name a photographer. Add "Positions: MAREANO, Havforskningsinstituttet (NLOD / CC BY 4.0)".
- Embargo / moratorium / special terms: no embargo on the stills. Raw cruise data is "tilgjengelig omkring en uke etter toktslutt" (available about a week after the cruise ends) according to mareano.no, or "within one month" according to cruise report 2026007006. Access needs an S3 user from datahjelp@hi.no.

## Media
- **Geolocated frame grabs (`bilder_biologi`)**:
  - 340 stills from 32 cruise numbers, 2006–2021. By year: 2021: 69, 2011: 56, 2008/2009: 44 each, 2010: 42, others fewer.
  - 62.1–80.3°N, 1.2–36.8°E, depth up to 2,731 m. Benthic fauna, corals, sponges, fish and trawl marks, all underwater.
  - Imageshop originals are TIF or JPG, about 1,430×794 to 1,920×1,080 (e.g. HAV-006059: TIF 1920×1080, 12 MB; JPG 792 KB).
  - The no-session preview is a 1,024×576 JPG (~176 KB).
  - Total: about 0.06 GB as previews, ~0.3 GB as full-size JPG, ~3 GB as TIF.
  - 243 rows have legacy `/embed/` URLs. Exactly 243 Imageshop assets are tagged `xxxArtsbilderMAREANOxxx`, so these are probably the same set; exact description matches were confirmed for samples.
  - 97 rows have legacy `/cache/…/HI-0xxxxx…` URLs.
- **Other HI-archive MAREANO assets**: 646 hits for "mareano", including 96 tagged "Campod". This includes on-deck, lab, people and illustrations, so only underwater-tagged assets should be taken. Many descriptions carry a `R<station>VL<line>` code (e.g. "R449VL470 still a-00-11-28"), which gives a station position.
- **Raw video archive (on request)**:
  - 3,908 video lines in Marbunn by year: 2006: 77, 2007: 137, 2008: 165, 2009: 134, 2010: 189, 2011: 202, 2012: 204, 2013: 221, 2014: 171, 2015: 135, 2016: 96, 2017: 170, 2018: 90, 2019: 196, 2020: 244, 2021: 526, 2022: 311, 2023: 198, 2024: 223, 2025: 183, 2026: 36.
  - Straight-line length per line: median 440 m, p90 730 m, max 2.6 km. Standard lines are 700 m, or 3×200 m transects in the deep sea.
  - Estimated ~2,000–4,000 h. Formats: SD/HD tape or MPEG-2 in early years, HD later, plus 4K stills on the ROV cruises (e.g. `20260416103430_4K.jpeg`). Size is unknown, likely 5–20+ TB (unverified).
- Filters needed:
  - Imageshop: keep only assets matched to `bilder_biologi`, or assets with keywords `Undervannsbilde`, `Campod` or `xxxArtsbilderMAREANOxxx`. Drop the categories "Illustrasjonar og teikningar" and "Kart", which are NC-ND, and drop on-deck, lab and people photos.
  - Raw video: drop descent and ascent (water column), off-bottom segments and frames with heavy laser or text overlay.
  - Overlaps and dedup: MAREANO video observations (no media) are also in EMODnet Biology / OBIS. The IMR CoralFISH Campod videos on PANGAEA (doi:10.1594/PANGAEA.760079) are not MAREANO but use the same rig and region; dedup by cruise number. Dedup keys to record: Imageshop `Kode` (HAV-xxxxxx), layer `FID`, legacy `BILDEURL`.
  - No overlap seen with BenthicNet or FathomNet (not checked exhaustively).

## Geolocation
- Precision levels and approximate share of samples:
These shares come from applying the recipe below to all 340 frame grabs.
  - Frame grabs, **image**: 326 of 340 (96%).
  - Frame grabs, **station**: 4 rows whose coordinate equals the station point (e.g. `bilder_biologi.164`).
  - Frame grabs, **region**: 9 rows whose coordinate is 4–45 km from their own reference station. These are QC conflicts.
  - Frame grabs, **none**: 1 row, `bilder_biologi.316` (REFSTASJ 2620, but coordinates near Svalbard, 1,600 km away).
  - Other Imageshop stills with an `R…VL…` code: **station**.
  - Raw video with navigation files: **segment** once obtained. Without navigation, station (Marbunn line midpoint).
- `geo_source`:
  - Frame grabs: `kart.hi.no mareano_stasjoner:bilder_biologi` properties `Latitude` and `Longitude` (WGS 84 decimal degrees, full precision in JSON). The same point is in `X_UTM33`/`Y_UTM33` (UTM zone 33N; checked to agree within 0.2 m) and in WKT `the_geom` in the CSV output.
  - The GeoJSON/WFS geometry is rounded to 4 decimals (~4–11 m), and the CSV `Latitude`/`Longitude` columns are rounded too. Use JSON properties or the CSV WKT instead.
  - Depth: `DYBDE` (m, positive down; 0 means missing, 2 rows).
  - Date and time: `DATO` is local midnight stored as UTC (`2007-03-30T22:00:00Z` means 2007-03-31). `TID` holds time of day (empty in 128 rows). Video timecode is embedded in `BILDEFIL` (e.g. `R734VL762_still_a-00-42-10.jpg`).
  - Stations: `videostasjoner_aarlig` columns `Latitude`, `Longitude` and `BottomDepth`, keyed by `RefStation`. The station point lies on the video line; the farthest line endpoint is at median 265 m and p95 494 m.
  - Video lines: Marbunn LineString `[start, end]`, `Datetime` (line start, `dd.mm.yyyy HH:MM:SS`, timezone undocumented) and `Notes` (tape id).
- Uncertainty:
  - Rig positions come from a hydro-acoustic transponder (HPR/HiPAP USBL on Campod).
  - Image points lie a median 16 m (p90 ~65 m) from the start–end line of a video line at the same reference station, so 50 m is used for image precision.
  - Station level: 500 m.
- How a sample maps to its coordinate:
  - Layer row → its own lat/lon.
  - Imageshop asset → match to a layer row (legacy `HI-0xxxxx` id, or `Skildring` == `TITTEL_N`). Otherwise parse `R(\d+)\s*VL[-_ ]?(\d+)` from `Skildring` and use `RefStation` = group 1.
  - Raw video file → named by video line (`R<ref>VL<line>…`) with an ROV/Campod position file next to it.

### resolve_geo recipe
Input: one `bilder_biologi` record (GeoJSON feature `properties`, or CSV row), plus a lookup `stations[RefStation]` built from `videostasjoner_aarlig`.
1. `lat, lon` = `float(props["Latitude"]), float(props["Longitude"])` from JSON. From CSV, parse `the_geom` `POINT (lon lat)` instead. Never use the rounded CSV `Latitude`/`Longitude` columns or the JSON `geometry`, except as a last resort with uncertainty +10 m.
2. If lat/lon are missing or outside 55–82°N / −5–40°E, try the inverse of `X_UTM33`/`Y_UTM33` (EPSG:25833). If that fails, go to step 7.
3. `depth_m` = `float(DYBDE)` if it is present and > 0. Otherwise use `stations[REFSTASJ].BottomDepth` (station-level depth, and append `; depth from videostasjoner_aarlig.BottomDepth` to `geo_source`). Otherwise `None`.
4. If `st = stations.get(REFSTASJ)` exists, compute the distance `d` in metres from (lat, lon) to (st.Latitude, st.Longitude).
   - `d < 2` m → the coordinate is the station point: `geo_precision="station"`, `geo_inferred=True`, `geo_uncertainty_m=500`.
   - `2 ≤ d ≤ 2000` (or no station found) → `geo_precision="image"`, `geo_inferred=False`, `geo_uncertainty_m=50`.
   - `2000 < d ≤ 50000` → QC conflict: keep lat/lon, `geo_precision="region"`, `geo_inferred=False`, `geo_uncertainty_m=round(d)`.
   - `d > 50000` → `geo_precision="none"`, lat/lon/depth `None`, `geo_uncertainty_m=None`.
5. `geo_source = "kart.hi.no WFS mareano_stasjoner:bilder_biologi properties.Latitude/Longitude (=X_UTM33/Y_UTM33), DYBDE"`.
6. Return the 7 fields. Expected results for the fixtures:
   - `bilder_biologi.10` → 70.26431547, 22.481867621, 257, image, False, 50.
   - `bilder_biologi.1` → 71.291374, 22.538244, 422, image, False, 50 (d ≈ 365 m to station 5).
   - `bilder_biologi.164` → 67.7882125, 10.22658, 270.49 (station depth because `DYBDE`=0), station, True, 500.
7. Fallback for an Imageshop-only still: regex `R(\d+)\s*VL[-_ ]?(\d+)` on `Skildring`, then `stations[ref]`. Return the station lat/lon and `BottomDepth`, `geo_precision="station"`, `geo_inferred=True`, `geo_uncertainty_m=500`, `geo_source="videostasjoner_aarlig Latitude/Longitude via R<ref> code in Imageshop Skildring"`. If there is no code, return `none` with everything `None`. Do not geocode the free-text area names ("Tromsøflaket"); they span tens of km.
8. Raw video frame, once S3 access is granted:
   - If a navigation file exists and its two nearest fixes are ≤ 10 s from the frame time, interpolate: `segment`, `geo_inferred=True`, uncertainty 50.
   - Otherwise use the Marbunn line for (Cruise, `Station number` = VL): midpoint, `station`, `geo_inferred=True`, uncertainty = half the line length + 50 m.
   - Otherwise use `stations[ref]`: `station`, 500 m.

## Access & download recipe
- Enumeration:
  - `GET https://kart.hi.no/mareano/ogc/features/v1/collections/mareano_stasjoner:bilder_biologi/items?f=application%2Fgeo%2Bjson&limit=1000` returns all 340 rows in one page (`numberMatched`=340).
  - `GET …/videostasjoner_aarlig/items?f=text%2Fcsv&limit=5000` returns 3,787 rows (~0.6 MB). It supports `filter=<CQL>&filter-lang=cql-text`.
  - Marbunn: `cruises`, then `showstationsinmap?cruiseno=<n>` for each of 46 cruises (15–313 KB each).
  - No auth needed; kart.hi.no and hi.imageshop.no have no robots.txt (404). Keep to ≤1 request/s per host.
- Fetching one image (no login):
  1. `GET https://hi.imageshop.no/1636899/Search?Q=<query>`. The query is the `HI-0xxxxx` id from `BILDEURL` if it has one, else `TITTEL_N`. Results are HTML; parse each `div.thumb-holder[data-documentid]` with `Skildring:`, `Kode:` (HAV-…), `Kreditering:`, `Filtypar:` and the `data-previewurl`.
  2. Accept a match only if `Skildring` == `TITTEL_N`, or if the HI-id query returns a single hit. In a probe, 9 of 10 sampled rows matched exactly.
  3. Download the `data-previewurl` / detail-page `<img>` right away. It is a presigned S3 URL (`s3.eu-west-1.amazonaws.com/s.imgi.no/server/base/738/<uuid>-v-34.jpg`, `X-Amz-Expires=604740`) for a 1,024 px JPG. It supports HTTP Range (206 seen), so resume works.
  4. Full-resolution JPG/TIF needs the session-based POST flow `/1636899/Download/DownloadAllDetail` (documentid + subdocumentid). This was not tested; alternatively ask mediearkiv@hi.no for an Imageshop API token.
  5. Save to `<data_root>/mareano/images/<HAV-id>.jpg`, with the layer row, Imageshop fields, licence and credit in `<data_root>/mareano/metadata/<HAV-id>.json`. Planned script: `scripts/download/mareano.sh`.
  6. Note: the legacy `BILDEURL` links (mediebank.hi.no/fotoweb/…) return 404. Keep them only as origin ids.
- Raw video, after access is granted: S3 folders `\\ces.hi.no\cruise_data\<year>\S<cruise>_P<vessel>_<id>` via https://s3browser.hi.no. File naming per the cruise reports: video and ROV position files carry the `R<ref>VL<line>` portion names. Enumerate per cruise with an S3 list call; check whether ranged GET works on the HI S3 endpoint.
- Sampling for a budget of N:
  - Stills: take all 340 (the QC-conflict rows only if they keep coordinates). Prefer ≤ 2 per video line. 52 lines have more than one still, and stills on the same line are near-duplicates seconds apart.
  - Video: stratify across the 3,908 lines by year (2006–2026), region (Barents/Norwegian Sea/North Sea/Svalbard/AMOR) and depth bin. Take `k = ceil(N / n_lines)` frames per line, evenly spaced over the on-bottom part (altitude ~1–3 m from the navigation/altimeter log) and at least 10 s apart.

## Manual steps (human)
1. Email datahjelp@hi.no with subject "S3 aksess til toktdata" / "S3 access to cruise data" (CC kjell.bakkeplass@hi.no or paal.buhl.mortensen@hi.no, as named in cruise report 2026007006).
   - Ask for read access to the MAREANO cruise folders (2006–2026 video files plus navigation/position files) on https://s3browser.hi.no.
   - Ask explicitly which licence applies to the raw video and frames, hoping for CC BY 4.0 / NLOD like the published MAREANO data, and whether redistribution of extracted frames is allowed.
   - Ask about total volume and preferred transfer rate.
2. Optional: email mediearkiv@hi.no to confirm whether the MAREANO frame grabs are CC BY 4.0 (as on Geonorge) or CC BY-SA 4.0 (Imageshop default). CC BY 4.0 would move them to tier B. Also ask for an Imageshop API token or a bulk export of the "MAREANO" assets.

## Fixtures
- `tests/fixtures/mareano/bilder_biologi_wfs_sample.json`: WFS 2.0 GeoJSON response with 3 frame-grab features (`bilder_biologi.1`, `.10`, `.164`), untrimmed.
- `tests/fixtures/mareano/bilder_biologi_ogcapi_sample.csv`: OGC API CSV for the same 3 rows (header plus 3 of 340 rows). Shows the WKT full-precision vs rounded-column behaviour.
- `tests/fixtures/mareano/videostasjoner_sample.csv`: reference stations 5, 73, 449 and 734 (CQL-filtered server response, untrimmed). Covers the depth fallback and the station-point check.
- `tests/fixtures/mareano/marbunn_video_lines_2007105_R73.json`: Marbunn GeoJSON with the 4 video lines of reference station 73 (cruise 2007105), trimmed to whole features.
- `tests/fixtures/mareano/licence.txt`: verbatim licence and access quotes with URLs.
- `tests/fixtures/mareano/SOURCE.md`: exact URLs, retrieval date and trimming for each file.

## Short download instruction
1. GET kart.hi.no OGC API `mareano_stasjoner:bilder_biologi` (GeoJSON, 340 rows), which gives per-image lat/lon/depth (`Latitude`, `Longitude`, `DYBDE`), plus `videostasjoner_aarlig` for station QC.
2. For each row, search `hi.imageshop.no/1636899/Search?Q=<HI-id|TITTEL_N>`, keep the exact match, and download its presigned 1,024 px preview JPG to `images/<HAV-id>.jpg` (≤1 req/s).
3. Licence: CC BY-SA 4.0 (HI media archive), so these go to the C shard. Credit: "MAREANO / Havforskningsinstituttet".
4. The full video archive (3,908 lines, 2006–2026, with navigation) is only via IMR S3 on request (datahjelp@hi.no), and its licence still has to be confirmed.

## Open questions / risks
- The licence for the image files differs between sources: CC BY 4.0 in the Geonorge record vs CC BY-SA 4.0 in the Imageshop terms. Treated as C; ask IMR to confirm.
- The raw video licence and the external S3 access policy are unknown. Volume and hours are estimates; check them against the S3 listing.
- The Imageshop full-resolution download needs a session/POST flow (untested). Presigned preview URLs expire in about 7 days, so download right after parsing.
- About 3% of `bilder_biologi` rows have metadata conflicts: coordinates 4–45 km from their REFSTASJ station, one 1,600 km off, and title place names or depths that disagree (e.g. `bilder_biologi.45` "Spitsbergenbanken" at 68.47°N 14.71°E). `TOKT` sometimes differs from the station cruise (2006112 vs 2006612; one `3013112` typo).
- The Marbunn `Datetime` timezone and the meaning of `Station number` for some recent cruises (value 1) are undocumented.
- How many of the 646 Imageshop "mareano" assets are underwater frame grabs with `R…VL…` codes beyond the 340 layer images was not counted. Imageshop pagination is session-based.
- IMR is experimenting with video links in map layers (`mareanovideo_fil`, `mareanovideo_test`). A public video layer may appear later.
