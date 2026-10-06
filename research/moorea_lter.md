# MCR LTER: Coral Reef: Computer Vision: Moorea Labeled Corals (`moorea_lter`)
Status: researched · researched 2026-10-06

## Summary
Moorea Labeled Corals (MLC) is the only Moorea Coral Reef LTER package that publishes raw benthic photo-quadrat images. It is EDI package `knb-lter-mcr.5006.3` (DOI 10.6073/pasta/88dde0e68ab5232a470389f4bedd1892). It holds 2,055 downward-looking 0.5 x 0.5 m photo-quadrats taken in April 2008, 2009 and 2010 at the six MCR LTER sites around Moorea, French Polynesia. There are three habitats per site (fringing reef, outer reef 10 m, outer reef 17 m), and each image comes with a 200-point annotation file. The images ship as three zips totalling 5.64 GB. The record-level licence is CC BY 4.0, so this is **tier B**. Two other sources disagree with it (see Licence), but the record-level licence is the most specific. Geolocation is **station** level for every image: the filename gives site and habitat, and each site-habitat is mapped to a coordinate from the package's own EML site polygons (about 1.1 to 1.65 km radius) or, for the LTER1/LTER2 outer-reef transects, to a BCO-DMO site table (200 to 500 m). Verdict: worth ingesting. The full 2005–2025 photo-quadrat archive (about 14,500 images) is **not** published as images: knb-lter-mcr.4 holds only the percent-cover tables. Since 2026-07-30 EDI's own API needs a free API key, but the DataONE GMN mirror still serves the files anonymously.

## Entry points
- EDI landing page (now behind a Cloudflare Turnstile "Human Verification Check"): https://portal.edirepository.org/nis/mapbrowse?packageid=knb-lter-mcr.5006.3. DOI: https://doi.org/10.6073/pasta/88dde0e68ab5232a470389f4bedd1892 (302 redirect to that page).
- PASTA REST API: base `https://pasta.lternet.edu/package/`. The image zips are `data/eml/knb-lter-mcr/5006/3/<entityId>`. **Every call needs authentication since 2026-07-30.** Anonymous calls return 403 "User 'EDI-… (Public Access)' is not authorized to execute service method 'readDataEntity'". Announcement: https://edirepository.org/news/news-20260727.00
- EDI API key to token exchange: `POST https://auth.edirepository.org/auth/v1/key` with body `{"key": "<access key>"}`, which returns `{"edi-token": "…"}`. Send the token as cookie `edi-token=<token>` (this is how ropensci/EDIutils does it, see `R/utilities.R`). Docs: https://auth.edirepository.org/auth/ui/api-docs/token
- DataONE federation, anonymous and working on 2026-10-06:
  - Metadata via the CN: `https://cn.dataone.org/cn/v2/object/https%3A%2F%2Fpasta.lternet.edu%2Fpackage%2Fmetadata%2Feml%2Fknb-lter-mcr%2F5006%2F3`
  - Search: `https://cn.dataone.org/cn/v2/query/solr/?q=isDocumentedBy:"https://pasta.lternet.edu/package/metadata/eml/knb-lter-mcr/5006/3"&wt=json`
  - Data objects via the LTER member node: `https://gmn.lternet.edu/mn/v2/object/<url-encoded PASTA data URL>`. The response carries the header `DataONE-Proxy: https://pasta.lternet.edu/...`.
- MCR site page: https://mcr.lternet.edu/data/datasets/mcr-lter-coral-reef-computer-vision-moorea-labeled-corals
- Dataset paper: Beijbom, Edmunds, Kline, Mitchell & Kriegman (2012), "Automated Annotation of Coral Reef Survey Images", CVPR 2012. https://vision.ucsd.edu/sites/default/files/docs/automated_coral_annotation.pdf (the UCSD dataset page https://vision.ucsd.edu/datasets/moorea-labeled-corals links to a devkit and samples that now return 404).
- Related packages, all without images:
  - knb-lter-mcr.4 "Long-term Population and Community Dynamics: Corals, ongoing since 2005" (rev 43, DOI 10.6073/pasta/d6a72dac70cf6dcccac8af96feaf9c28): percent cover per photo-quadrat 2005–2025.
  - knb-lter-mcr.5013.3: Moorea part of "Pacific Labeled Corals", the 2008 images again. Different licence, see below.
- Coordinates for LTER1/LTER2: BCO-DMO dataset 918265, https://www.bco-dmo.org/dataset/918265 (DOI 10.26008/1912/bco-dmo.918265.1), supplemental `site_locations.csv`.

## Licence
- **Tier: B** (CC BY 4.0, read at record level).
- **Licence text (record level).** `dataset/intellectualRights` of the EML for knb-lter-mcr.5006.3. Read at https://cn.dataone.org/cn/v2/object/https%3A%2F%2Fpasta.lternet.edu%2Fpackage%2Fmetadata%2Feml%2Fknb-lter-mcr%2F5006%2F3 (same document as https://portal.edirepository.org/nis/mapbrowse?packageid=knb-lter-mcr.5006.3):
  > "This data package is released under the Creative Commons license Attribution 4.0 International (CC BY 4.0 , see https://creativecommons.org/licenses/by/4.0/). This license states that consumers ("Data Users" herein) may distribute, adapt, reuse, remix, and build upon this work, as long as they give appropriate credit, provide a link to the license, and indicate if changes were made. If redistributed, a Data User may not apply additional restrictions or technological measures that prevent access. The Data User has an ethical obligation to cite the data source appropriately …"

  No file-level licence exists: the zips and annotation files carry no licence of their own.
- **Contradicting sources** (kept for audit; neither overrides the record licence above):
  1. Collection level: the MCR Data Use Policy at https://mcr.lternet.edu/data/data-use-policy starts with "Data collected at MCR LTER are released under the Creative Commons license Attribution 4.0 International (CC BY 4.0 …)". Further down it still contains the old sentence "Users are prohibited from selling or redistributing any data provided by MCR LTER without explicit prior permission." The page contradicts itself, and the record-level CC BY 4.0 is more specific.
  2. A different record, knb-lter-mcr.5013.3 (2015), re-packages the same 2008 images. It carries the pre-CC-BY MCR policy: "5. Users are prohibited from selling or redistributing any data provided by MCR LTER without explicit prior permission." and "1. The user agrees to provide valid name and contact information prior to downloading online data." **Treat 5013.3 as Excluded and do not download it.** MLC 5006.3 rev 3 (2019) was re-released under CC BY 4.0.
- **Attribution text to store with every sample:**
  "Moorea Coral Reef LTER and P. Edmunds. 2019. MCR LTER: Coral Reef: Computer Vision: Moorea Labeled Corals ver 3. Environmental Data Initiative. https://doi.org/10.6073/pasta/88dde0e68ab5232a470389f4bedd1892. Licence: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Images cropped/resized by aquasource." The year is the publication date of revision 3 (2019-05-10); the EML pubDate is 2012-05-21.
  Also cite: Beijbom O., Edmunds P.J., Kline D.I., Mitchell B.G., Kriegman D. (2012) Automated Annotation of Coral Reef Survey Images. IEEE CVPR 2012.
  MCR also asks for this acknowledgement in publications: "This manuscript uses data collected by the U.S. National Science Foundation's (US NSF) Moorea Coral Reef Long Term Ecological research (MCR LTER) site under Grant No. OCE 1637396 (and earlier awards)…".
- **Embargo / moratorium / special terms:** none. The data were public in 2012. The courtesy requests (notify the creators, send manuscripts) are not licence conditions. The EML lists research permits from the French Polynesian Government; these do not restrict reuse.

## Media
- **Types:** still images only. No video: the 2020 GoPro transect videos mentioned in knb-lter-mcr.4 are not published, and 2020 is not in MLC.
- **Counts** (EML entity descriptions): 671 images from 2008, 695 from 2009 and 689 from 2010, so 2,055 in total. Each image has a `<image>.txt` annotation file next to it (`# Row; Col; Label`, 200 random points, labels such as CCA, Turf, Macro, Sand, Acrop, Pavon, Monti, Pocill, Porit, Off).
- **Archives:**

  | Year | File | Bytes | EML MD5 | DataONE SHA-1 | PASTA entity |
  |---|---|---|---|---|---|
  | 2008 | MCR_LTER_ComputerVision_LabeledCorals_2008_20120521.zip | 2,044,220,065 | 743d62088ac2be456b8d50c02725bcc3 | 4af4b83f3f964b3d7f234178130bc196e599ca18 | 28c6c36ed93e699e0550361ee871bdc9 |
  | 2009 | MCR_LTER_ComputerVision_LabeledCorals_2009_20120523.zip | 2,628,754,087 | 4b265a33d32ebd6a7efc68c477d65e97 | 9ccadaa2c5293542a861f6ea661c8c02ec7c799c | 1b90487f445a82fe072c43871dfcd1ef |
  | 2010 | MCR_LTER_ComputerVision_LabeledCorals_2010_20120521.zip | 962,738,166 | d708520d6822d9701bf02e64f8817b39 | 86e79281b658113de8358df895864811bd99aa31 | 41afbdac7aac223ff92dea751ea39530 |

  Total: 5,635,712,318 bytes (about 5.64 GB).
- **Format and resolution:**
  - The EML methods say: "Quantitative high resolution digital images, each aproximately 2.5 to 3.2 Mb in JPEG format, with aproximately 2000 x 2000 pixels or 4 megapixels". The example annotation has points up to row 1913 and column 1937, which fits.
  - Camera: Nikon D70 with dual Nikonos SB-105 strobes (knb-lter-mcr.5013.3 methods, for 2008).
  - Third-party README (data-mermaid/mermaid-segmentation) reports that the 2010 folder contains `.png` files and that 53 of the 2010 images are damaged or missing. Verify after download. 2010 also averages only 1.4 MB per file versus about 3 MB for 2008.
  - Zip layout (same README): `2008/`, `2009/`, `2010/`, each holding `<name>.jpg|png` and `<name>.jpg|png.txt`.
- **Time range:** single April surveys in 2008, 2009 and 2010 (dates appear in the filenames, e.g. 20080415, 20090331, 20100410).
  - Parent series: knb-lter-mcr.4.43 lists 14,542 photo-quadrats over 2005–2025, about 690 per year (6 sites x 3 habitats x 40 quadrats), with one survey each April (August in 2020, May in 2021). These images are **not** in any public package. They live in MCR's CoralNet sources and the photographers' archive, so a human request to MCR would be needed (see Open questions).
- **Filters:**
  - No aerial, above-water or on-deck frames: every image is a nadir photo of the reef.
  - The 0.5 x 0.5 m photo-quadrat frame shows along the image edges and a white transect line crosses the middle (Beijbom 2012, Fig. 1). Optionally crop the frame border.
  - Run a decode check and drop the corrupt 2010 files.
  - Optional blur and darkness check: the images are strobe-lit, so very few should fail.
- **Overlaps / dedup** (key = filename stem `mcr_lter{n}_{habitat}_pole{a}-{b}_qu{q}_{yyyymmdd}`, plus MD5):
  - knb-lter-mcr.5013.3: the same 671 images from 2008. Excluded licence, do not ingest.
  - CoralNet: MCR-related sources, e.g. public source 8689 "Depth Transects" (UCSB, 2020/2023/2025, LTER0/1/2/Pile). The core LTER sources appear not to be public.
  - Third-party mirrors and converted copies on GitHub (jxwleong/coral-sleuth uses PNG conversions; data-mermaid/mermaid-segmentation).
  - Dryad "Pacific Labeled Corals" (doi:10.5061/dryad.m5pr3) does **not** contain Moorea; it covers Heron Reef, the Line Islands and Nanwan Bay only.
  - Record `origin_url` = the PASTA entity URL + the path inside the zip.
- **Repeated quadrats:** the same permanent quadrat is photographed in each of the three years. Treat each quadrat across 2008–2010 as a near-duplicate group when splitting train/val.

## Geolocation
- **Precision:** 100 % `station`. No per-image coordinates exist: the EML, the annotation files and (as far as known) EXIF carry no GPS. EXIF is unverified because no images were downloaded.
  - About 22 % of images: LTER1/LTER2 outer reef at 10 m and 17 m (458 of 2,082 quadrats in 2008–2010 according to knb-lter-mcr.4). Uncertainty 200 m (10 m) or 500 m (17 m).
  - About 78 %: all fringing-reef images plus outer reef at LTER3–6. Polygon centroid with 1,100–1,650 m uncertainty.
- **geo_source:**
  - (a) `knb-lter-mcr.5006.3` EML `dataset/coverage/geographicCoverage/boundingCoordinates/gRing`, one polygon per site ("LTER 1 polygon including LTER 0 on north shore", …, "LTER 6 polygon on southwest shore"). gRing pairs are `lon,lat`, WGS 84. We use the polygon centroid; the uncertainty is the largest distance from the centroid to a vertex.
  - (b) BCO-DMO 918265 `site_locations.csv` columns `lat_dd`, `lon_dd` for LTER1 (-17.475, -149.837) and LTER2 (-17.472, -149.808). These are the 10 m fore-reef transects, Edmunds et al. 2024 (doi:10.1007/s00442-024-05517-y). Both points fall inside the matching EML polygon. The table's LTER0 row (-17.388) lies about 9 km offshore and is apparently a typo; it is not needed.
  - Pre-computed: `tests/fixtures/moorea_lter/publication_sites.csv` (18 rows).
- **CRS:** WGS 84 decimal degrees.
- **Depth:** from knb-lter-mcr.4.43 long table, column `Depth`. Outer 10 m = 10, outer 17 m = 17. Fringing reef: LTER1 6, LTER2 4, LTER3 7, LTER4 6, LTER5 3, LTER6 4 m. These were read from the 2005–2006 rows; the transects are permanent, so the same values are assumed for 2008–2010.
- **Image to coordinate mapping:** by filename. For `mcr_lter6_out17m_pole5-6_qu3_20090331.jpg`:
  - site = `lter6`
  - habitat = `out17m` (one of `fringingreef`, `out10m`, `out17m`)
  - transect section = poles 5–6
  - quadrat = 3 within that section
  - date = 2009-03-31

  The year folder in the zip must match the filename date. The annotation file uses the same stem with `.txt` appended.

### resolve_geo recipe
Input: one fixture record, i.e. an image or annotation file name such as `mcr_lter6_out17m_pole5-6_qu3_20090331.jpg.txt`. Lookup table: `publication_sites.csv`.
1. `base = basename(name).lower()`
2. Match against `^mcr_lter(?P<site>[1-6])_(?P<hab>fringingreef|out10m|out17m)_pole(?P<pa>\d+)-(?P<pb>\d+)_qu(?P<q>\d+)_(?P<date>\d{8})\.(?:jpe?g|png)(?:\.txt)?$`
3. If there is a match, set `sid = f"LTER{site}_{hab}"` and `row = sites[sid]`, then return:
   - `lat = float(row.lat)`, `lon = float(row.lon)`, `depth_m = float(row.depth_m)`
   - `geo_precision = "station"`
   - `geo_source = f"publication_sites.csv:{sid} (from filename tokens lter{site}/{hab}); " + row.source`
   - `geo_inferred = True`
   - `geo_uncertainty_m = float(row.uncertainty_m)`
   - Optionally `date = YYYY-MM-DD` from `date`.
4. If there is no match, or `sid` is missing from the table (e.g. a mirror renamed the file), fall back to the dataset bounding box:
   - `lat = -17.535`, `lon = -149.835`
   - `depth_m = None`
   - `geo_precision = "region"`
   - `geo_source = "knb-lter-mcr.5006.3 EML geographicCoverage 'Moorea, French Polynesia' bbox W-150.00 E-149.67 N-17.45 S-17.62 (centre)"`
   - `geo_inferred = True`
   - `geo_uncertainty_m = 20000`
5. Never return `none` for this dataset: every file is from Moorea.
6. Expected result for the fixture `mcr_lter6_out17m_pole5-6_qu3_20090331.jpg.txt`:
   - lat -17.51751, lon -149.9223, depth_m 17
   - geo_precision `station`, geo_inferred True, geo_uncertainty_m 1500
   - date 2009-03-31
7. Expected result for a hypothetical `mcr_lter1_out10m_…`: lat -17.475, lon -149.837, depth 10, uncertainty 200.

## Access & download recipe
- **Enumeration:** fixed and small: 3 zips plus the EML. Get the list from the EML `otherEntity/physical/distribution/online/url`, or from the DataONE solr query in the fixtures (`numFound` = 5). No pagination.
  - EDI search and list endpoints (`/package/search/eml`, `/package/eml/knb-lter-mcr`) now return 403 without a token.
- **Auth:**
  - Route A, preferred and policy-aligned: an EDI API key. `TOKEN=$(curl -s -X POST https://auth.edirepository.org/auth/v1/key -d "{\"key\":\"$EDI_API_KEY\"}" | jq -r '."edi-token"')`, then `curl -A "$UA" -b "edi-token=$TOKEN" -o <file> https://pasta.lternet.edu/package/data/eml/knb-lter-mcr/5006/3/<entityId>`.
  - Route B, anonymous, verified 2026-10-06 with HEAD plus a small-file GET: `curl -A "$UA" -o <file> "https://gmn.lternet.edu/mn/v2/object/https:%2F%2Fpasta.lternet.edu%2Fpackage%2Fdata%2Feml%2Fknb-lter-mcr%2F5006%2F3%2F<entityId>"`.
- **Range / resume:**
  - GMN ignores `Range` (it answers 200 with the full length) and sends no `Accept-Ranges`. So there is no resume and no partial read of the zip central directory; failed downloads restart.
  - Whether authenticated PASTA supports Range is untested.
  - Verify each zip with the EML MD5 and the DataONE SHA-1 from the table above.
- **Rate limits:** none documented. The 2026 lock-down targets DoS and scraping, so download the three zips one after another, never in parallel, with backoff on 429/503.
- **Fetching one image:** no per-image endpoint exists; you must fetch a whole year zip. Unpack as follows:
  - images to `<data_root>/moorea_lter/images/<year>/`
  - `*.txt` annotations to `<data_root>/moorea_lter/metadata/annotations/<year>/`
  - the EML to `metadata/knb-lter-mcr.5006.3.xml`
  - `publication_sites.csv` to `metadata/`
  - `videos/` stays empty.
- **Sampling for a budget of N:**
  - Strata: 3 years x 6 sites x 3 habitats = 54 cells of about 38 images each. Take `ceil(N/54)` per cell, round-robin.
  - Within a cell, pick distinct `(pole, qu)` positions, and rotate positions across years so the same permanent quadrat is not taken three times unless N > about 700.
  - With N < about 600 and limited bandwidth, the 2008 zip alone (2.04 GB, 671 images, all 18 transects) gives full spatial diversity but no temporal diversity.
  - For N >= 2,000, take everything minus the corrupt 2010 files.

## Manual steps (human)
- Optional, recommended: create a free EDI profile (sign in with Google, Microsoft, GitHub or ORCID at https://auth.edirepository.org) and generate an API access key. Store it as the secret `EDI_API_KEY` so the script uses the official PASTA route (A). Route B works anonymously today, so this does not block anything.
- Optional, high value: ask MCR LTER information management whether the full 2005–2025 photo-quadrat image archive (about 14,500 images, the source of knb-lter-mcr.4) can be released under the same CC BY 4.0 terms. While asking, confirm that the leftover "prohibited from … redistributing" sentence on the Data Use Policy page does not apply to CC BY packages. Use the contact form at https://mcr.lternet.edu; no email address is recorded here.

## Fixtures
- `tests/fixtures/moorea_lter/knb-lter-mcr.5006.3_eml.xml`: complete EML of the package (licence, site polygons, entity list, MD5s).
- `tests/fixtures/moorea_lter/mcr_lter6_out17m_pole5-6_qu3_20090331.jpg.txt`: the provider's example per-image annotation file, unmodified (MD5 matches the EML). Its filename is the record for `resolve_geo()`.
- `tests/fixtures/moorea_lter/dataone_solr_5006_3.json`: complete DataONE solr response listing the 5 objects of the package with sizes and SHA-1.
- `tests/fixtures/moorea_lter/bcodmo_918265_site_locations.csv`: BCO-DMO site table (LTER0/1/2, 10 m fore reef).
- `tests/fixtures/moorea_lter/knb-lter-mcr.4.43_long_excerpt.csv`: header plus one real row per transect (18) from the knb-lter-mcr.4 long table, the source of `Depth`.
- `tests/fixtures/moorea_lter/publication_sites.csv`: derived lookup table with 18 site-habitat rows (lat, lon, depth_m, uncertainty_m, source).
- `tests/fixtures/moorea_lter/SOURCE.md`: URLs, retrieval date, trimming and derivation notes.

## Short download instruction
Moorea Labeled Corals (EDI knb-lter-mcr.5006.3, CC BY 4.0): 3 zips (2008/2009/2010), 2,055 photo-quadrats, 5.6 GB.
Get each zip from https://gmn.lternet.edu/mn/v2/object/https:%2F%2Fpasta.lternet.edu%2Fpackage%2Fdata%2Feml%2Fknb-lter-mcr%2F5006%2F3%2F{28c6c36ed93e699e0550361ee871bdc9,1b90487f445a82fe072c43871dfcd1ef,41afbdac7aac223ff92dea751ea39530}
(or from PASTA with an EDI API key sent as cookie edi-token). Check the MD5s from the EML, then unzip to images/<year>/ and metadata/annotations/.
Geo: parse `mcr_lter{n}_{fringingreef|out10m|out17m}_…` and look it up in publication_sites.csv (station, 0.2–1.65 km).

## Open questions / risks
- **Full archive missing:** about 14,500 photo-quadrats from 2005–2025 (knb-lter-mcr.4) exist but are not published as images. MLC covers only 2008–2010, about 14 % of the series. Getting the rest needs MCR's cooperation.
- **Licence wording:** the MCR collection-level policy page still carries a "no redistribution without permission" sentence next to its CC BY 4.0 statement, and knb-lter-mcr.5013.3 (the same 2008 images) carries the old restrictive policy. We follow the record-level CC BY 4.0 of 5006.3. A reviewer who reads the rules strictly could downgrade this to U until MCR confirms.
- **Access:** EDI has required authentication since 2026-07-30, and the portal adds a Turnstile challenge. The anonymous DataONE GMN mirror works now but may be locked down later; keep route A (API key) ready.
- **2010 files:** a third party reports PNG files in the 2010 zip and 53 damaged or missing images. Verify the counts and formats after download. Also confirm the resolution: about 2000 x 2000 (EML) versus "6.24 MP" (CVPR / PLC table).
- **Station coordinates:** for LTER3–6 and for every fringing-reef transect we only have the site polygon centroid (up to 1.65 km off). Exact transect GPS points are not published. The 17 m transect positions at LTER1/2 are assumed to lie within 500 m of the published 10 m point.
- **Fringing depths:** taken from 2005–2006 rows of knb-lter-mcr.4. knb-lter-mcr.5013.3 says the fringing reef is "2-5 m", while knb-lter-mcr.4 gives 3–7 m by site.
- **EXIF:** not checked (no images downloaded). If GPS tags turn out to exist, which is unlikely for a 2008 D70 in a housing, upgrade to `image` precision.
