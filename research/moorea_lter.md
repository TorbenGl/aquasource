## HANDOFF
- status: blocked (adapter, script and offline tests done; no bulk download possible)
- tier + licence: B, CC BY 4.0, read at record level: EML intellectualRights of knb-lter-mcr.5006.3 rev 3, https://cn.dataone.org/cn/v2/object/https%3A%2F%2Fpasta.lternet.edu%2Fpackage%2Fmetadata%2Feml%2Fknb-lter-mcr%2F5006%2F3
- geo: station (100 %), geo_source = `sites/moorea_lter.csv` row from filename tokens (EML site polygon centroids; BCO-DMO 918265 for LTER1/2 10 m), geo_inferred, uncertainty 200-1650 m
- files: adapters/moorea_lter.py, scripts/download/moorea_lter.sh, tests/test_moorea_lter.py, adapters/sites/moorea_lter.csv, fixtures/moorea_lter/
- tests: pass (9/9 offline, `uv run pytest tests/test_moorea_lter.py -q`)
- sample: 0 files downloaded, error: 2010 zip (963 MB) stream reset at about 19 MB, 2 tries, Range ignored; sample dir removed
- doubts:
  - discover() downloads each year zip (no per-image listing exists, GMN ignores Range): conflicts with the metadata-only rule in base.py; needs a shared-code decision
  - access: needs EDI API key (route A) or a copy from MCR; bulk zip path is blocked anonymously today
  - licence: MCR policy page and 5013.3 say "no redistribution"; record CC BY kept (tier B)
  - 2010 zip: PNG files and damaged images reported; only magic bytes checked, no full decode
  - publication-derived geo: polygon centroids (up to 1.65 km), fringing depths from 2005-06 rows
- needs_opus: yes, because access is blocked (zip stream) and discover() needs media bytes to build the zip index (base.py conflict)

# MCR LTER: Coral Reef: Computer Vision: Moorea Labeled Corals (`moorea_lter`)
Status: blocked (download) · lean pass 2026-10-08; research 2026-10-06

## Summary
Moorea Labeled Corals (MLC) is the only Moorea Coral Reef LTER package that publishes raw benthic photo-quadrat images. It is EDI package `knb-lter-mcr.5006.3` (DOI 10.6073/pasta/88dde0e68ab5232a470389f4bedd1892). It holds 2,055 downward-looking 0.5 x 0.5 m photo-quadrats taken in April 2008, 2009 and 2010 at the six MCR LTER sites around Moorea, French Polynesia. There are three habitats per site (fringing reef, outer reef 10 m, outer reef 17 m), and each image comes with a 200-point annotation file. The images ship as three zips totalling 5.64 GB. The record-level licence is CC BY 4.0, so this is **tier B**. Two other sources disagree with it (see Licence), but the record-level licence is the most specific. Geolocation is **station** level for every image: the filename gives site and habitat, and each site-habitat is mapped to a coordinate from the package's own EML site polygons (about 1.1 to 1.65 km radius) or, for the LTER1/LTER2 outer-reef transects, to a BCO-DMO site table (200 to 500 m). Verdict: worth ingesting. The full 2005–2025 photo-quadrat archive (about 14,500 images) is **not** published as images: knb-lter-mcr.4 holds only the percent-cover tables. Since 2026-07-30 EDI's own API needs a free API key, but the DataONE GMN mirror served the files anonymously on 2026-10-06; on 2026-10-08 bulk zip transfers were cut off (see Access).

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
- **Overlaps:** knb-lter-mcr.5013.3 (same 2008 images, excluded licence, do not ingest); CoralNet and GitHub mirrors (not used); Dryad "Pacific Labeled Corals" has no Moorea. Dedup key = filename stem + MD5.
- **Repeated quadrats:** the same permanent quadrat is photographed each year; group by quadrat id for train/val splits.

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

### resolve_geo (implemented)
- Regex on the lower-cased filename: `mcr_lter{1-6}_{fringingreef|out10m|out17m}_pole{a}-{b}_qu{q}_{yyyymmdd}.(jpg|png)[.txt]`; key `LTER{n}_{habitat}` into sites/moorea_lter.csv.
- Fallback when no match: bbox centre -17.535, -149.835, precision `region`, uncertainty 20000 m. Never `none`.
- Expected for the example file: lat -17.51751, lon -149.9223, depth 17, uncertainty 1500, date 2009-03-31 (tested).

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
- **Lean run 2026-10-08 (blocked):** a zip GET from gmn.lternet.edu got 200 but the stream was reset after about 19-20 MB (two tries, `IncompleteRead`), Range was ignored again, and the rate was about 160 kB/s. Bulk download is not possible anonymously right now.
- **Rate limits:** none documented; the adapter uses 1 s per request to gmn.lternet.edu, zips one after another.
- **Fetching one image:** no per-image endpoint exists; you must fetch a whole year zip. Unpack as follows:
  - images to `<data_root>/moorea_lter/images/<year>/`
  - `*.txt` annotations to `<data_root>/moorea_lter/metadata/annotations/<year>/`
  - the EML to `metadata/knb-lter-mcr.5006.3.xml`
  - `publication_sites.csv` to `metadata/`
  - `videos/` stays empty.
- **Sampling (adapter):** 18 site x habitat cells per year, round-robin; years in order 2008, 2009, 2010 (`years=` option).

## Manual steps (human)
- Needed: a free EDI API key (https://auth.edirepository.org), stored as `EDI_API_KEY` (route A). Or ask MCR LTER information management for a copy of the zips (contact form at https://mcr.lternet.edu).
- Optional: ask MCR whether the 2005-2025 photo-quadrat archive (about 14,500 images, source of knb-lter-mcr.4) can be released under CC BY 4.0.

## Fixtures (tests/fixtures/moorea_lter/)
- `knb-lter-mcr.5006.3_eml.xml` (licence, polygons, MD5s); `dataone_solr_5006_3.json` (sizes, SHA-1s);
- `mcr_lter6_out17m_pole5-6_qu3_20090331.jpg.txt` (example annotation, unmodified; the geo test record);
- `bcodmo_918265_site_locations.csv`, `knb-lter-mcr.4.43_long_excerpt.csv` (depth source), `publication_sites.csv` (18 rows, copied to adapters/sites/moorea_lter.csv); `SOURCE.md` (URLs).

## Open questions / risks
- **Full archive missing:** about 14,500 photo-quadrats (2005-2025, knb-lter-mcr.4) are not published as images; MLC covers 2008-2010 only.
- **Licence wording:** the MCR policy page and knb-lter-mcr.5013.3 still carry "no redistribution" text. We follow the record-level CC BY 4.0 of 5006.3; a strict reader may downgrade to U until MCR confirms.
- **Access:** see the 2026-10-08 blocked test above. Keep route A (API key) ready.
- **2010 files:** third party reports PNG files and 53 damaged or missing images. Check after a successful download; resolution 2000 x 2000 (EML) vs 6.24 MP (CVPR table).
- **Station coordinates:** LTER3-6 and all fringing-reef transects use polygon centroids (up to 1.65 km off). Fringing depths come from 2005-06 rows.
- **EXIF:** not checked (no images downloaded). Probably no GPS; upgrade to `image` only if tags exist.
