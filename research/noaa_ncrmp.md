# NOAA NCRMP benthic photo-quadrats, US Pacific (PIFSC ESD) (`noaa_ncrmp`)
Status: researched · researched 2026-10-06

## Summary
These are the diver photo-quadrat images of NOAA's National Coral Reef Monitoring Program (NCRMP) in the US Pacific, taken by the PIFSC Ecosystem Sciences Division (ESD). Divers photograph the reef straight down from a 1 m monopod at 1 m intervals, about 30 images per site, at 0–30 m depth. Coverage is Hawaiʻi (main and Northwestern islands), the Mariana Archipelago (Guam, CNMI), American Samoa and the Pacific Remote Island Areas (Wake, Johnston, Howland, Baker, Jarvis, Kingman, Palmyra).

NCEI archives them in **39 accessions covering 2013–2025**. There are two families:
- 18 "climate station" (fixed/permanent site) accessions, about 20.1 k images.
- 21 stratified-random-site (StRS) accessions, about 0.18 M images.

In total that is **about 0.20 M JPEGs and about 1.45 TB** (exact counts per accession are in the table below; three late values are marked).

Licence is **tier A**:
- The 2023–2025 accessions carry an explicit CC0 1.0 dedication.
- The older accessions state no licence. They are NOAA works with "data-access-constraints: None" and a citation request only.

Geolocation is **station level** for essentially all images. Each accession ships a site-info CSV (`SITE`, `DATE_`, `LATITUDE`, `LONGITUDE`, WGS 84), taken with a handheld GPS by the boat over the divers' buoy. It joins on the site code that starts every filename `SITE_YEAR[_REP]_PHOTO.JPG`. Depth is not in the image accessions. It can be joined per image from NCEI's benthic-cover CSVs (`MIN_DEPTH`/`MAX_DEPTH`, in feet).

Verdict: ingest. This is a large, clean, CC0/US-government, consistently geolocated coral-reef image set. Plain HTTPS from Apache directory listings, with Range support.

## Entry points
- InPort collection records (each lists its accessions):
  - Climate stations / permanent sites: https://www.fisheries.noaa.gov/inport/item/71813 (XML: https://www.fisheries.noaa.gov/inport/item/71813/inport-xml)
  - Stratified random sites: https://www.fisheries.noaa.gov/inport/item/71814 (XML: …/71814/inport-xml)
  - Site-info data dictionary entity: https://www.fisheries.noaa.gov/inport/item/71816
  - The superseded records 25380, 36143–36145, 25247 and 36152–36154 now return 403.
- NCEI accession landing pages: `https://www.ncei.noaa.gov/archive/accession/<acc>`. This redirects to `https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.nodc:<acc>`, and the ISO XML is at the same URL with `&view=xml`.
- NCEI HTTPS file tree: `https://www.ncei.noaa.gov/data/oceans/archive/<arc>/<acc>/<ver>/data/0-data/`. The same tree is on FTP at `ftp://ftp-oceans.ncei.noaa.gov/nodc/archive/<arc>/<acc>/`.
- Depth / extra per-image metadata (benthic cover from CoralNet annotation, one row per annotated point):
  - Fixed sites: NCEI 0317416, https://www.ncei.noaa.gov/data/oceans/archive/arc0247/0317416/1.1/data/0-data/NCRMP_BENTHIC_COVER_FIXED_PACIFIC_2012-2025.csv (49 MB) plus `ESD_NCRMP_BENTHIC_COVER_FIXED_DataDictionary_2026.csv`.
  - StRS: NCEI 0317464 v2.2, https://www.ncei.noaa.gov/data/oceans/archive/arc0247/0317464/2.2/data/0-data/. Files: `NCRMP_BENTHIC_COVER_STRS_HAWAII_2015-2024.csv` (156 MB), `…_MARI_2017-2025.csv` (110 MB), `…_PRIA_2012-2025.csv` (106 MB), `…_SAMOA_2010-2025.csv` (124 MB), and `ESD_NCRMP_BENTHIC_COVER_DataDictionary_2026.csv`.
- Survey SOP, for the photo protocol and the GPS procedure: NOAA Tech Memo NMFS-PIFSC-71 (2018). URL: https://www.ncei.noaa.gov/data/oceans/archive/arc0101/0157633/13.13/data/0-data/Pacific/Biological/Protocols/PIFSC_NTM-PIFSC-71_2018_SOP_Benthic.pdf (NCEI 0157633 is the NCRMP documentation accession).

All image accessions (counts and sizes come from the NCEI directory listings on 2026-10-06; sizes are the sum of the listed, rounded file sizes):

| Type | Year | Region | NCEI acc. | Path `<arc>/<acc>/<ver>` | Images | GB | Survey dates | Site-info CSV |
|---|---|---|---|---|---|---|---|---|
| climate | 2013 | Hawaiʻi (MHI+NWHI) | 0159172 | arc0106/0159172/1.1 | 2,205 | 6.9 | 2013-07-12…10-30 | Site_Info_HAWAII_2013.csv |
| climate | 2014 | Marianas | 0157759 | arc0104/0157759/1.1 | 1,373 | 5.0 | 2014-03-25…05-05 | `Site Info MARIAN 2014.csv` |
| climate | 2014 | PRIA (Wake) | 0159139 | arc0104/0159139/1.1 | 216 | 0.7 | 2014-03-16…03-19 | Site_Info_PRIAs_2014.csv |
| climate | 2015 | American Samoa | 0159170 | arc0104/0159170/1.1 | 1,439 | 4.7 | 2015-02-15…03-26 | `Site Info SAMOA 2015.csv` |
| climate | 2015 | PRIA | 0159155 | arc0104/0159155/1.1 | 1,216 | 3.7 | 2015-01-26…04-27 | Site_Info_PRIAs_2015.csv |
| climate | 2016 | Hawaiʻi | 0164296 | arc0111/0164296/1.1 | 656 | 2.6 | 2016-07-17…09-21 | Site_Info_HAWAII_2016.csv |
| climate | 2017 | Marianas | 0202138 | arc0145/0202138/1.1 | 947 | 3.9 | 2017-05-03…06-21 | SiteInfo_Marianas_2017.csv |
| climate | 2017 | PRIA (Wake) | 0202139 | arc0145/0202139/1.1 | 57 | 0.2 | 2017-04-19…04-20 | SiteInfo_Wake_2017.csv |
| climate | 2018 | American Samoa | 0187561 | arc0135/0187561/1.1 | 894 | 10.2 | 2018-06-19…07-16 | Site_Info_SAMOA_2018.csv |
| climate | 2018 | PRIA | 0187562 | arc0135/0187562/1.1 | 704 | 7.8 | 2018-06-08…08-10 | Site_Info_PRIAs_2018.csv |
| climate | 2019 | Hawaiʻi | 0240600 | arc0188/0240600/1.1 | 1,893 | 21.9 | 2019-04-26…09-04 | Benthic_Image_Site_Info_MHI.csv, …_NWHI.csv |
| climate | 2022 | Marianas | 0279443 | arc0219/0279443/1.1 | 1,891 | 22.0 | 2022-04-12…08-06 | NCRMP_CLIMATE_SITEINFO_MARIAN_2022.csv |
| climate | 2023 | American Samoa | 0289892 | arc0223/0289892/1.1 | 1,137 | 13.7 | 2023-06-30…08-08 | NCRMP_CLIMATE_SITEINFO_SAMOA_2023.csv |
| climate | 2023 | PRIA | 0289907 | arc0226/0289907/1.1 | 449 | 4.8 | 2023-03-15…03-19 | NCRMP_CLIMATE_SITEINFO_PRIA_2023.csv |
| climate | 2024 | Hawaiʻi | 0317534 | arc0247/0317534/1.1 | 2,577 | 30.7 | 2024-05-29…08-27 | NCRMP_CLIMATE_SITEINFO_HAWAII_2024.csv |
| climate | 2025 | PRIA (Wake) | 0317752 | arc0247/0317752/1.1 | 300 | 3.4 | 2025-04-03…04-08 | NCRMP_CLIMATE_SITEINFO_PRIA_2025.csv |
| climate | 2025 | Marianas | 0317786 | arc0247/0317786/1.1 | 2,114 | 25.4 | 2025-05-09…06-28 | NCRMP_CLIMATE_SITEINFO_MARIAN_2025.csv |
| StRS | 2013 | Hawaiʻi | 0159144 | arc0104/0159144/1.1 | 12,628 | 39.4 | 2013-05-01…10-31 | Site_Info_HAWAII_2013.csv |
| StRS | 2014 | Marianas | 0159142 | arc0104/0159142/1.1 | 13,326 | 40.5 | 2014-03-25…05-07 | Site_Info_MARIAN_2014.csv |
| StRS | 2014 | PRIA (Wake) | 0159157 | arc0104/0159157/1.1 | 599 | 1.3 | 2014-03-16…03-20 | Site_Info_PRIAs_2014.csv |
| StRS | 2015 | American Samoa | 0159168 | arc0103/0159168/**2.2** | 17,387 | 74.1 | 2015-02-15…03-26 | Site_Info_SAMOA_2015.csv |
| StRS | 2015 | PRIA | 0159153 | arc0104/0159153/1.1 | 13,271 | 55.9 | 2015-01-26…04-28 | Site_Info_PRIAs_2015.csv |
| StRS | 2015 | MHI (Reef Fish cruise HA1503) | 0268773 | arc0208/0268773/1.1 | 10,259 | 38.7 | 2015-06-15…07-02 | MHI_RFS_PQ_siteinfo_2015.csv |
| StRS | 2015 | NWHI (PMNM RAMP HA1505) | 0276273 | arc0211/0276273/1.1 | 4,159 | 16.3 | 2015-07-30…08-21 | NWHI_PMNM_PQ_siteinfo_2015.csv |
| StRS | 2016 | Hawaiʻi | 0164293 | arc0111/0164293/1.1 | 19,667 | 93.2 | 2016-07-13…09-27 | Site_Info_HAWAII_2016.csv |
| StRS | 2016 | PRIA (Jarvis) | 0176287 | arc0125/0176287/1.1 | 1,482 | 6.7 | 2016-05-16…05-22 | Site_Info_PRIAs_2016.csv |
| StRS | 2017 | Marianas | 0176286 | arc0190/0176286/1.1 | (listing in progress) | | 2017-05-03…06-21 | Site_Info_MARIAN_2017.csv |
| StRS | 2017 | PRIA | 0176288 | arc0190/0176288/1.1 | (listing in progress) | | 2017-04-02…04-23 | Site_Info_PRIAs_2017.csv |
| StRS | 2018 | American Samoa | 0187563 | arc0180/0187563/1.1 | 7,008 | 76.4 | 2018-06-19…07-18 | Site_Info_SAMOA_2018.csv |
| StRS | 2018 | PRIA | 0187564 | arc0180/0187564/1.1 | 7,964 | 74.8 | 2018-06-08…08-11 | Site_Info_PRIAs_2018.csv |
| StRS | 2019 | MHI | 0211063 | arc0157/0211063/1.1 | 14,445 | 122.4 | 2019-04-21…10-31 | Site_Info_HAWAII_2019.csv |
| StRS | 2022 | Marianas | 0279441 | arc0219/0279441/1.1 | 13,450 | 155.9 | 2022-04-12…08-10 | NCRMP_STRS_SITEINFO_MARIAN_2022.csv |
| StRS | 2023 | PRIA | 0289904 | arc0223/0289904/1.1 | 1,721 | 19.9 | 2023-03-15…05-07 | NCRMP_STRS_SITEINFO_PRIAS_2023.csv |
| StRS | 2023 | American Samoa | 0289905 | arc0223/0289905/1.1 | 9,139 | 100.1 | 2023-03-30…08-09 | NCRMP_STRS_SITEINFO_SAMOA_2023.csv |
| StRS | 2024 | Hawaiʻi | 0317535 | arc0247/0317535/1.1 | 13,165 | 151.9 | 2024-05-13…08-27 | NCRMP_STRS_SITEINFO_HAWAII_2024.csv |
| StRS | 2025 | PRIA (Wake) | 0317753 | arc0247/0317753/1.1 | 1,051 | 12.0 | 2025-04-03…04-08 | NCRMP_STRS_SITEINFO_PRIA_2025.csv |
| StRS | 2025 | Marianas | 0317785 | arc0248/0317785/1.1 | 11,796 | 148.5 | 2025-04-23…06-27 | NCRMP_STRS_SITEINFO_MARIAN_2025.csv |
| StRS | 2019 | MHI bleaching event (InPort 59193) | 0270550 | (listing in progress) | | | 2019-10-08…11-14 | |

Notes on the table:
- InPort 71813 lists the PRIA 2023 climate accession only as "accession#". It is **0289907**.
- InPort 71814 gives "ESD_NCRMP_BENTHIC_IMAGES_STRS_2024_HAWAII" the link 0217940. That is wrong: 0217940 is the 2019 Hawaiʻi StRS *cover* table (`MV_BIA_CNET_ANALYSIS_DATA_HAWAII_2019.csv`, 33 MB). The 2024 Hawaiʻi StRS images are **0317535**.
- InPort 71814 also lists 0157633, which is the documentation accession (PDF SOPs), not images.

## Licence
- Tier: **A** (US federal government work; CC0 1.0 on the 2023–2025 accessions; no contradicting source).
- Licence text (quote) + level read (file / record / collection) + URL:
  - Record level, newer accessions. NCEI landing page for 0317534 (https://www.ncei.noaa.gov/archive/accession/0317534), "Data License": "This dataset has been dedicated to the public domain under the Creative Commons CC0 1.0 Universal (CC0 1.0) Public Domain Dedication. SPDX License: Creative Commons Zero v1.0 Universal (CC0-1.0)". The same text appears on 0317535, 0317752, 0317753, 0317785 and 0317786.
  - Record level, older accessions (2013–2023, for example https://www.ncei.noaa.gov/archive/accession/0159172 and …/0279441). There is no "Data License" field. The ISO XML has:
    - `useLimitation` "accessLevel: public"
    - `MD_LegalConstraints/otherConstraints` "Cite as: …" (citation only)
    - the NOAA/NCEI no-warranty "Use liability" text.
  - Collection level, InPort 71813 and 71814 (https://www.fisheries.noaa.gov/inport/item/71813/inport-xml):
    - `data-access-constraints` "None".
    - `data-use-constraints` "Please cite PIFSC Ecosystem Sciences Division (ESD) when using the data."
    - 71814 has `data-license-type` "Custom". The custom text is the "ESD Data Sharing Recommendations, version 9.0", which are explicitly "recommendations … for your consideration": acknowledgement expected, error reporting and data sharing requested. These are not restrictions.
  - Provenance: originator "Pacific Islands Fisheries Science Center" (NOAA), funded by the NOAA Coral Reef Conservation Program. Data from NOAA employees are US-government works (17 U.S.C. §105).
  - Nothing NC, ND or research-only appears anywhere, so tier A.
- Attribution / citation text to store with every sample:
  - "Ecosystem Sciences Division, Pacific Islands Fisheries Science Center (<year published>). National Coral Reef Monitoring Program: Benthic Images Collected from <Climate Stations|Stratified Random Sites (StRS)> across <region> (NCEI Accession <acc>). NOAA National Centers for Environmental Information. https://www.ncei.noaa.gov/archive/accession/<acc>"
  - Plus the ESD acknowledgement: "This work makes use of data products provided by the Ecosystem Sciences Division (ESD), Pacific Islands Fisheries Science Center (PIFSC), NOAA, with funding support from the NOAA Coral Reef Conservation Program (CRCP)."
  - The exact "Cite as" text of each accession is on its landing page. Store `ncei_accession` and the landing URL per sample.
- Embargo / moratorium / special terms:
  - None.
  - Not every collector is federal. ESD divers include cooperative-institute (University of Hawaiʻi CIMAR/JIMAR) staff. The 2015 NWHI set 0276273 was "conducted by PMNM" (Papahānaumokuākea Marine National Monument, co-managed with the State of Hawaiʻi). NOAA nonetheless publishes all of them as public, and CC0 on the recent ones. Flag this for the verifier, but it does not change the tier.

## Media
- Types, counts, formats, resolution, total size, time range (full history for observatories)
  - Still images only: JPEG `.JPG`, plus a few lowercase `.jpg` in older sets. No video.
  - Totals: climate about **20.1 k images / 167 GB** (18 accessions). StRS about **0.18 M images / 1.25 TB** (21 accessions, of which three are still being listed). Grand total about 0.20 M images, about 1.45 TB.
  - Time range: survey years 2013–2019 and 2022–2025. There are no surveys in 2020–2021 (COVID).
  - The 2010–2012 RAMP images exist at PIFSC: the cover tables contain `IMAGE_NAME`s such as `JOH-07_2012_A_27.JPG` and `TUT-21_2012_A_28.JPG`. They are **not** in any NCEI image accession found (see Open questions).
  - Cameras, from EXIF read with 64 KB Range requests:
    - Canon PowerShot S100 / S110: 4000×3000, about 3 MB (2013–2015).
    - Canon G9 X / G9 X Mark II: 5472×3648, 10–12 MB (2018–2022).
    - Canon G7 X Mark II: 5472×3648, Lightroom-processed, 11–16 MB (2024).
  - About 30 frames per site visit: two transects × 15 frames at 1 m intervals. Each frame covers about 1 m² of reef, shot straight down from a 1 m monopod (SOP NMFS-PIFSC-71 p. 42). The ~1 m measuring stick ("tape and wand") is often visible.
  - Filename patterns (case varies):
    - `SITE_YYYY_R_NN.JPG` (2013–2018, and StRS through 2025; R = transect letter A/B, occasionally C/D). Examples: `HAW-395_2013_A_01.JPG`, `BAK-11_2015_A_08.JPG`.
    - `SITE_YYYY_NN.JPG` (climate 2019+). Examples: `OCC-FFS-001_2024_02.JPG`, `HAW-41_2019_01.JPG`.
    - Site codes are `ISL-nnn[n]` (StRS and older climate) or `OCC-ISL-nnn` (climate 2019+).
  - Folder layout:
    - Mostly flat: one image folder per accession, for example `0-data/NCRMP_FIXED_IMAGES_HAWAII_2024/`.
    - 0240600 has two folders, `MHI_CLIMATE_PHOTOQUADS_2019/MHI_CLIMATE_PHOTOQUADS_2019/` and `NWHI_Climate_PHOTQUADS_2019/`.
    - 0176286, 0176287 and 0176288 keep the raw cruise tree: `Cruise/CruiseData/<cruise>/Optical/<ISL>/REA/{BENTHIC,FISH}/<SITE>/PHOTO_QUADS/[A|B/]<file>`, which needs recursive listing.
- Filters needed (aerial, on-deck, black frames, overlaps with other sources)
  - No aerial or above-water imagery: all frames are diver photo-quadrats.
  - The SOP says "The first photo taken at each REA site is a photo of the slate with the dive site ID" and that transect starts are marked by photographing one or two fingers. ESD QC states images were "quality controlled to remove non-photoquadrat/poor quality images", so these should be gone. Still drop frames with `PHOTO` = 00 or > 30 as a cheap guard, and run a slate/hand detector if needed.
  - Apply the EXIF `Orientation` tag. Value 6 occurs (2015, 2018) and some 2024 files are stored portrait (3648×5472).
  - Ignore EXIF `DateTimeOriginal`. It is wrong on some cameras: `1980:01:01` in 2022, and 2013-05-10 for a site surveyed on 2013-09-05. EXIF has a GPS IFD with no coordinates.
  - Overlaps:
    - (a) The 2019 bleaching-event StRS images (0270550, 2019-10/11) and the 2019 StRS set (0211063, ends 2019-10-31) may share files. Dedup on filename + byte size.
    - (b) The same photos were annotated in CoralNet. Any public CoralNet copies are duplicates.
    - (c) NCRMP SfM imagery (InPort 63091/63095) is a different image stream at the same sites, not a duplicate.
    - Dedup key: `<SITE>_<YEAR>[_R]_<NN>` plus size. Origin URL: the NCEI HTTPS file URL.

## Geolocation
- Precision level(s) and approximate share of samples at each
  - **station** for about 100 % of images. Spot checks of 0317534 (87/87 sites), 0159155 (40/40) and the 0240600 MHI part (27/27) found every image site code in the accession's site-info CSV.
  - **none** only if a code is missing from the CSV and from the cover tables. None observed so far.
- geo_source (exact field names / table), CRS, depth field, uncertainty
  - Coordinates: `LATITUDE`, `LONGITUDE` of the per-accession site-info CSV. The data dictionary (InPort 71816, `SITEINFO_DATADICTIONARY_2024.csv`) says: "Latitude of the survey site where photoquads were collected (WGS84, decimal degrees)."
  - Join key column: `SITE`, except `OCC_SITEID` in `NCRMP_CLIMATE_SITEINFO_MARIAN_2022.csv`. The 2019 NWHI file has **both** `SITE` (old code) and `OCC_SITEID`, and the images there use `OCC_SITEID`. Index every ID column.
  - Date column: `DATE_` (or `DATE` in 2018). Formats vary: `05-SEP-13`, `15-Aug-16`, `"10-Aug-24"`, `7/10/2018`, `8/28/2019 0:00`, `29-APR-22 11.42.31`. Quoting also varies, and files are CRLF.
  - How coordinates were taken (SOP NMFS-PIFSC-71 p. 43): "Geographic coordinates for the position taken by the coxswain with the GPS directly over the dive site, once the divers have descended and set the surface buoy." InPort 71813: "Handheld GPS units were used to mark site locations."
  - Uncertainty: about **50 m**. This covers handheld GPS error (about 5–10 m), buoy offset and the two 18 m transects around the buoy.
  - Two different sites sometimes share identical coordinates, probably copy errors: `KIN-07`/`KIN-62` in 0159155, and `KUR-4131`/`KUR-4246` in 0240600 (both in the fixtures). Keep them, but do not treat the coordinates as unique site identifiers.
  - Depth: not in the image accessions.
    - Join on `IMAGE_NAME` (or the same `<SITE>_<YEAR>` site visit) in the cover CSVs, columns `MIN_DEPTH`, `MAX_DEPTH` (**feet**), `DEPTH_SOURCE` (`site` = in-situ benthic survey, `fish` = fish point-count area, `sfm`, `occ` = reference depth of the fixed site).
    - depth_m = mean(MIN_DEPTH, MAX_DEPTH) × 0.3048. Values can be inverted, for example MIN 48 / MAX 47 for BAK-11 2015.
    - Coverage: fixed sites 2012–2025; StRS Hawaiʻi 2015–2024, Marianas 2017–2025, PRIA 2012–2025, Samoa 2010–2025. So StRS Hawaiʻi 2013 and Marianas 2014 get `depth_m = null`.
    - The data dictionary adds: "Typically Mid sites without depths are at 15m". Do not use that as a value.
- How a sample maps to its coordinate
  - Image filename → site code (the text before `_YYYY_`) → the row with the same code in **the site-info CSV of the same accession**. Codes are reused across years with different coordinates, and permanent sites were renamed (e.g. `JOH-07` → `OCC-JOH-004`), so never join across accessions.
  - The cover CSV also carries `SITE` (new OCC code), `LATITUDE`, `LONGITUDE` and `IMAGE_NAME` (old filename). It is the fallback coordinate source and the depth source.

### resolve_geo recipe
Input: one image record `{acc, url, name}` from an accession listing (e.g. `tests/fixtures/noaa_ncrmp/listing_0317534_excerpt.html`). Also the parsed site-info rows of the same accession (e.g. `site_info_climate_hawaii_2024.csv`) and, optionally, a cover lookup built from the cover CSVs (e.g. `cover_fixed_excerpt.csv`).
1. `m = re.match(r'^(?P<site>.+?)_(?P<year>\d{4})_(?:(?P<rep>[A-Za-z])_)?(?P<photo>\d{1,3})\.jpe?g$', name, re.I)`. If there is no match, return `lat=lon=depth_m=None, geo_precision="none", geo_source="filename not parseable", geo_inferred=False, geo_uncertainty_m=None`.
2. Load the accession's site-info CSV(s) with `csv.DictReader`. Use `utf-8-sig`, strip quotes and whitespace, and accept CRLF.
   - Build `idx[code.upper()] = row` for every value in the columns `SITE` and `OCC_SITEID` that are present.
   - 0240600 has two CSVs (MHI, NWHI); merge them.
3. `row = idx.get(m['site'].upper())`. If `row` exists and `LATITUDE`/`LONGITUDE` parse as floats with |lat| ≤ 90 and |lon| ≤ 180:
   - `lat, lon = round(float(LATITUDE), 6), round(float(LONGITUDE), 6)`
   - `geo_precision = "station"`
   - `geo_source = "NCEI <acc> <csv filename> LATITUDE/LONGITUDE (handheld GPS over dive buoy), joined on SITE|OCC_SITEID = <code>"`
   - `geo_inferred = True` (one coordinate per site visit, applied to all ~30 frames)
   - `geo_uncertainty_m = 50`
   - Also keep `survey_date` parsed from `DATE_`/`DATE`. Try `%d-%b-%y`, `%m/%d/%Y`, `%m/%d/%Y %H:%M` and `%d-%b-%y %H.%M.%S`, case-insensitively.
4. Otherwise, use the cover fallback. If `cover[name.upper()]` exists, take its `LATITUDE`/`LONGITUDE` and set `geo_source = "NCEI 0317416/0317464 cover CSV LATITUDE/LONGITUDE via IMAGE_NAME"`; the other values are as in step 3. Otherwise return `lat=lon=None, geo_precision="none", geo_source="site code <code> not in site-info CSV of <acc>", geo_inferred=False, geo_uncertainty_m=None`.
5. Depth:
   - Look up `cover[name.upper()]`. If it is missing, take any cover row whose `IMAGE_NAME` starts with `<site>_<year>_`, because depth is per site visit.
   - Take the numeric `MIN_DEPTH` and `MAX_DEPTH` (feet), ignoring empty or `NA`. `depth_m = round(mean(values) × 0.3048, 1)`. If neither is numeric, `depth_m = None`.
   - Keep `depth_source = DEPTH_SOURCE`.
6. Expected fixture results, all with geo_precision station, geo_inferred true and uncertainty 50:
   - `OCC-FFS-001_2024_02.JPG` → 23.878545, −166.290919, depth 24.4 m (80.1 ft).
   - `OCC-FFS-002_2024_03.JPG` → 23.878185, −166.291118, 17.7 m.
   - `OCC-FFS-003_2024_01.JPG` → 23.875517, −166.292174, 6.4 m.
   - `BAK-11_2015_A_08.JPG` (with `site_info_climate_pria_2015.csv`) → 0.19864, −176.48489, 14.5 m (47.5 ft).
   - `OCC-FFS-009_2019_01.JPG` (with `site_info_climate_nwhi_2019.csv`, matched via `OCC_SITEID`) → 23.63488, −166.185688, depth None (no cover row in the fixture).
   - `OCC-FFS-099_2024_01.JPG` (made-up code) → geo_precision `none`.

## Access & download recipe
- Enumeration (endpoints / listings / pagination), auth, rate limits
  - No auth. Plain Apache `mod_autoindex` HTML listings, with no pagination.
  - Use the accession table above as the authoritative list. To discover new accessions:
    - re-read the InPort XMLs 71813 and 71814 (`distribution/download-url`), and
    - query `https://www.ncei.noaa.gov/metadata/geoportal/opensearch?q=title:(benthic%20AND%20images)&f=json&size=500` and keep NCRMP titles.
  - For each accession:
    - `GET https://www.ncei.noaa.gov/data/oceans/archive/<arc>/<acc>/` and pick the highest `<ver>/` (0159168 is at 2.2).
    - List `<ver>/data/0-data/` recursively. Parse rows with `<a href="NAME">…</a></td><td align="right">DATE  </td><td align="right">SIZE</td>`.
    - Keep `*.jpg|*.JPG` and the site-info CSVs (files containing `Site`/`SITE` and ending `.csv`, excluding `*DataDictionary*`). Also save `DataDictionary` CSVs and ISO XML to metadata.
  - Listings of big folders (13–20 k files, 2–3 MB HTML) can take more than 2 minutes. Use a 15-minute timeout.
  - The server occasionally drops TLS (`SSL_ERROR_SYSCALL`), so retry with backoff.
  - No published rate limit. Use at most 1 request per second for listings and 2 parallel downloads.
- How to fetch one media file; range / resume support
  - `GET https://www.ncei.noaa.gov/data/oceans/archive/<arc>/<acc>/<ver>/data/0-data/<folder>/<name>`, URL-encoding spaces (e.g. `Climate%20Images%20MARIAN%202014`).
  - Range requests are supported: `206 Partial Content`, `Content-Range: bytes 0-65535/14076918` for `OCC-FFS-001_2024_01.JPG`. Use `curl -C -` to resume and verify against `Content-Length`.
  - Listing sizes are rounded (`13M`), so use HEAD for exact sizes.
  - Store as `<data_root>/noaa_ncrmp/images/<acc>/<name>`. Put the site-info CSVs, data dictionaries and the 5 cover CSVs (about 545 MB, or a reduced `IMAGE_NAME → depth, lat, lon` table built from them) in `<data_root>/noaa_ncrmp/metadata/`.
  - NCEI also offers whole-accession tarballs at `https://www.ncei.noaa.gov/archive/accession/download/<acc-without-leading-zero>`. Not used; per-file is better for sampling.
- Sampling strategy for a budget of N samples (diversity across sites and time)
  - The unit is the site visit (accession × site code; about 6,500 visits of about 30 frames). Frames in a visit are adjacent 1 m² quadrats along the same 15 m line, so they are highly correlated.
  - Allocate N across the 5 regions (MHI, NWHI, Marianas, Samoa, PRIA) roughly equally. Within a region, split across survey years, and keep climate vs StRS at about 1:3 (climate visits are repeat visits to the same few hundred fixed sites).
  - Then sample site visits uniformly at random, and take k = 2–3 frames per visit with spaced photo numbers (e.g. 03, 10, 13 from different transects).
  - For N < 6,500, take one frame per visit, so every sample has a distinct station.
  - Everything can be selected from listings plus site-info CSVs before downloading any pixels.

## Manual steps (human)
None are required. Optional:
- Ask PIFSC ESD (InPort data steward listed in 71813) whether the 2010–2012 RAMP photo-quadrats, which appear in the cover tables, can be archived or shared.
- Ask for an explicit licence statement for the pre-2023 accessions, if the project wants more than the US-government-work reasoning.

## Fixtures
- tests/fixtures/noaa_ncrmp/site_info_climate_hawaii_2024.csv: header + 3 rows (`OCC-FFS-001/002/003`) of `NCRMP_CLIMATE_SITEINFO_HAWAII_2024.csv` (NCEI 0317534). Current format, quoted, `dd-Mon-yy`, CRLF.
- tests/fixtures/noaa_ncrmp/site_info_climate_pria_2015.csv: header + 3 rows of `Site_Info_PRIAs_2015.csv` (NCEI 0159155). Legacy format `dd-MON-yy`, and two sites with identical coordinates (KIN-07/KIN-62).
- tests/fixtures/noaa_ncrmp/site_info_climate_nwhi_2019.csv: header + 3 rows of `Benthic_Image_Site_Info_NWHI.csv` (NCEI 0240600). Has the `SITE` + `OCC_SITEID` columns (images use `OCC_SITEID`), `M/D/YYYY H:MM` dates, and a duplicate-coordinate pair.
- tests/fixtures/noaa_ncrmp/listing_0317534_excerpt.html: NCEI Apache directory listing of `NCRMP_FIXED_IMAGES_HAWAII_2024/`, trimmed to 3 image rows.
- tests/fixtures/noaa_ncrmp/cover_fixed_excerpt.csv: header + 5 point rows of `NCRMP_BENTHIC_COVER_FIXED_PACIFIC_2012-2025.csv` (NCEI 0317416), one per fixture image. This is the depth source (`MIN_DEPTH`/`MAX_DEPTH` in feet).
- tests/fixtures/noaa_ncrmp/SOURCE.md: URLs, retrieval date, trimming and expected `resolve_geo` outputs.

## Short download instruction
1. For each NCEI accession in the table (InPort 71813 climate + 71814 StRS, 2013–2025), list `https://www.ncei.noaa.gov/data/oceans/archive/<arc>/<acc>/<ver>/data/0-data/` recursively.
2. Download the `*.JPG` (about 0.20 M, about 1.45 TB, HTTPS with Range support) plus the site-info CSV(s). No auth, CC0 / US government.
3. Geo: filename `SITE_YEAR[_R]_NN.JPG` → `SITE` (or `OCC_SITEID`) row in the same accession's site-info CSV → `LATITUDE`/`LONGITUDE` (station, ±50 m).
4. Depth: join `IMAGE_NAME` in the NCEI 0317416/0317464 cover CSVs, then mean(`MIN_DEPTH`, `MAX_DEPTH`) ft × 0.3048.
5. Sample 1–3 frames per site visit, balanced across regions and years.

## Open questions / risks
- Three accessions were still being listed when this note was written: 0176286, 0176288 (2017 StRS, nested cruise tree) and 0270550 (2019 bleaching StRS). Their counts need to be filled in, and 0270550 needs checking for filename overlap with 0211063.
- The 2010–2012 photo-quadrats (RAMP era, InPort says "since 2010") are not in any NCEI image accession found. The cover CSVs reference them (e.g. `JOH-07_2012_A_27.JPG`, `TUT-21_2012_A_28.JPG`), so they exist at PIFSC.
- No climate images were archived for Hawaiʻi 2016 beyond 656 frames, nor for Samoa/Marianas in some years. Gaps follow the survey rotation; this is not an error.
- Licence on pre-2023 accessions is implicit (US-government work, no licence field). Some collectors were cooperative-institute or state partners (e.g. PMNM 2015 NWHI, 0276273). NCEI marks all as public and the recent ones CC0, so tier A is reasonable. A verifier may want explicit confirmation.
- Coordinates are boat GPS over the buoy, not per-frame positions. Two sites sometimes share identical coordinates (copy errors). Old and new site codes differ (`FFS-12` vs `OCC-FFS-0xx`), so never join across accessions or years.
- The cover CSVs are large (49–156 MB each) and point-level. Build a reduced depth table once. Depth is missing for StRS Hawaiʻi 2013 and Marianas 2014, and for unannotated images.
- Atlantic/Caribbean NCRMP (Florida, Puerto Rico, USVI, Flower Garden Banks): **no comparable public photo-quadrat image sets found**. The Atlantic benthic protocol (NCRMP Benthic Assessment Protocols 2018, in NCEI 0157633 `Atlantic/…/NCRMP_Protocol_Benthic_BenthicAssessment_2018.pdf`) is in-situ line-point-intercept plus coral demographics. It takes only "at least five photographs per station" (datasheet + 4 cardinal views), and the NCEI Atlantic benthic collections (e.g. NCRMP-Benthic-PR) are tabular. Atlantic imagery that does exist is separate: AOML NCRMP climate photomosaics (NCEI 0178832, 0178633, 0286804) and Flower Garden Banks NMS long-term monitoring photos (non-NCRMP). Both are listed as new candidates.
- NCEI's directory host occasionally resets TLS. Listings of 15–20 k files are slow, so build retries into the downloader.
