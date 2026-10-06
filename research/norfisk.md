# NorFisk Dataset (`norfisk`)
Status: researched · researched 2026-10-06

## Summary
NorFisk v1.0 (NTNU Ålesund, published on DataverseNO in 2020) holds 12,514 underwater PNG images of single fish: 9,487 farmed salmonids (salmon and trout inside net pens) and 3,027 wild saithe (outside the pens). The images were cropped automatically from about 49 h of GoPro footage filmed at a Norwegian salmon farm between 2017 and 2020. Everything ships as one 2.64 GB zip, and each image has a one-line bounding-box annotation.
The licence is CC0 1.0 at record level, so the tier is **A**.
No image carries a coordinate, timestamp or depth. The data paper (Crescitelli et al. 2021) gives only "The farm is located near [Å]lesund in Norway". All samples therefore get one publication-derived point at **region** precision: Ålesund, 62.4711 N 6.1552 E, about 30 km uncertainty, `geo_inferred=true`.
Verdict: usable as a small, clean, public-domain shard of North-Atlantic aquaculture imagery. Its geo is coarse, and the images are object-centred crops rather than full frames.

## Entry points
- Dataset DOI: https://doi.org/10.18710/H5G3K5 (landing page https://dataverse.no/dataset.xhtml?persistentId=doi:10.18710/H5G3K5)
- Dataverse API (native JSON): https://dataverse.no/api/datasets/:persistentId/?persistentId=doi:10.18710/H5G3K5
- schema.org export: https://dataverse.no/api/datasets/export?exporter=schema.org&persistentId=doi:10.18710/H5G3K5
- README: https://dataverse.no/api/access/datafile/86886 (`00_ReadMe.txt`, 5,022 B, doi:10.18710/H5G3K5/CPGKKO)
- Data: https://dataverse.no/api/access/datafile/86889 (`NorFisk_v1.0.zip`, 2,641,300,775 B, MD5 `6ec799e74054dec2dadb6f9179e51ea5`, doi:10.18710/H5G3K5/QK355D). It answers 303 with a pre-signed S3 URL on `uit-dataverseno-prod01.s3-oslo.educloud.no`, valid for 21,600 s.
- Data paper (CC BY 4.0): Crescitelli, Gansel & Zhang 2021, *Modeling, Identification and Control* 42(1):1-16, doi:10.4173/mic.2021.1.1. PDF: https://www.mic-journal.no/PDF/2021/MIC-2021-1-1.pdf
- Earlier conference paper (closed access): Crescitelli et al. 2020, ICIEA, doi:10.1109/ICIEA48937.2020.9248107
- Aggregator copy: https://b2find.eudat.eu/dataset/9ac082a3-9a1f-5f92-acf4-61d8f3183985

## Licence
- Tier: **A** (CC0 1.0)
- Licence text (quote) + level read (file / record / collection) + URL:
  - **Record level.** Read from the DataverseNO landing page, "Dataset Terms" tab: "License/Data Use Agreement — Our Community Norms as well as good scientific practices expect that proper credit is given via citation. Please use the data citation shown on the dataset page. CC0 1.0" (https://dataverse.no/dataset.xhtml?persistentId=doi:10.18710/H5G3K5).
  - The native API returns `"license": {"name": "CC0 1.0", "uri": "http://creativecommons.org/publicdomain/zero/1.0", "rightsIdentifier": "CC0-1.0"}`. The schema.org export returns `"license": "http://creativecommons.org/publicdomain/zero/1.0"` (fixture `dataverse_schemaorg.json`). Both licence fields are unchanged across versions 1.0 (2020-12-07) and 1.1 (2023-09-28).
  - Neither file carries its own licence. The README says only "// Licenses/Restrictions: See Terms tab." The PNGs have no metadata chunks: we read 8 KB of the headers and found only IHDR followed by IDAT. No source contradicts CC0.
- Attribution / citation text to store with every sample:
  - Repository citation, as generated: `Maximiliano, Crescitelli Alberto, 2020, "NorFisk Dataset", https://doi.org/10.18710/H5G3K5, DataverseNO, V1`. Dataverse swaps the author's given and family names; the correct name is Alberto Maximiliano Crescitelli.
  - String to store: `Crescitelli, A. M. (2020). NorFisk Dataset (v1.1). DataverseNO. https://doi.org/10.18710/H5G3K5. CC0 1.0. Paper: Crescitelli, Gansel & Zhang (2021) MIC 42(1):1-16, doi:10.4173/mic.2021.1.1`
- Embargo / moratorium / special terms: none. Both files have `restricted: false`, and an anonymous API download works without a guestbook. `fileAccessRequest: true` is only the Dataverse request-access switch and has no effect on unrestricted files. Citation is requested as a community norm, not as a legal condition.

## Media
- **Types and counts:** 12,514 still images (PNG, 8-bit RGB) and 12,514 annotation `.txt` files.
  - `saithe/img/saithe.000001.png` … `saithe.003027.png` (3,027 files, 931.6 MB)
  - `salmonid/img/salmonid.000001.png` … `salmonid.009487.png` (9,487 files, 1,704.1 MB)
  - Per-image size runs from 11 KB to 6.8 MB, median 134 KB.
  - No videos are published. The 346 source videos (58 h 56 min raw, 49 h 25 min after cleaning) were not released.
- **Resolution:** each image is a crop (ROI) around one detected fish, cut from frames normalised to 1920×1080. Sizes vary because of random ROI scaling, and the ROI keeps the bounding box's aspect ratio. Width and height come from all 12,514 annotation rows, read through Range requests:
  - saithe: width 125–3190 px (median 511), height 94–2156 px (median 381)
  - salmonid: width 101–1916 px (median 353), height 77–1295 px (median 266)
  - Each annotation file holds exactly one row, which means one fish per image.
- **Time range:** Dataverse `dateOfCollection` gives 2017-01-01 to 2020-08-01; the paper says "between 2017 to 2020". No per-image timestamp exists. The zip mtimes (2020-04 to 2020-11) are processing dates, not capture dates.
- **Cameras and depth:** GoPro Hero 4, 5 and 8, at "depths ranges between 1 and 50 meters" (README). Frames were sampled at 1 fps.
- **Filters needed:**
  - No aerial or on-deck frames are expected: every image is a crop around a detected fish. The surface photo of the cage in the paper's Fig. 7 is not in the dataset.
  - Drop very small crops if the pretraining resolution requires it. 1,242 salmonid and 153 saithe crops are under 224 px wide.
  - Near-duplicates are very likely, because crops were taken at 1 fps from long videos of the same pens. Deduplicate with perceptual hashing.
  - Labels were produced semi-automatically (YOLOv3 loop), so a few crops may show non-fish objects. This does not matter for self-supervised pretraining.
  - The "salmonid" class mixes Atlantic salmon and trout.
  - Many backgrounds are net-pen mesh. Keep this in mind when balancing the data against natural-habitat sources.
- **Overlaps:** no copies were found on Kaggle, Roboflow or Hugging Face. B2FIND indexes the same DOI. Later NTNU work (Banno et al. 2022, doi:10.3354/aei00432) used new 2020 footage, and none of its images are published. For dedup, record the origin as `https://doi.org/10.18710/H5G3K5#<zip member path>`.

## Geolocation
- **Precision levels:** 100 % `region`. No sample has image, segment, station or fixed-site precision.
- **geo_source:**
  - The publication: Crescitelli, Gansel & Zhang 2021, doi:10.4173/mic.2021.1.1, Section 3.2 "Data collection", p. 9. It reads: "The video footage has been taken in a fish farm at different times on different days between 2017 to 2020. … The farm is located near lesund in Norway (see figure 7)". The printed PDF has lost the "Å"; we read it as Ålesund.
  - The place was geocoded with OSM Nominatim. Node 31264149 "Ålesund, Møre og Romsdal" sits at lat 62.4711412, lon 6.1551755 (WGS 84).
  - The paper gives no coordinates, farm name, site table or map grid.
- **CRS:** WGS 84 decimal degrees.
- **Depth:** no per-sample field, so `depth_m` is null. Only a 1–50 m range is given (README / paper).
- **Uncertainty:** 30,000 m, covering farms in the Ålesund, Giske, Sula, Hareid and Haram archipelago. Two caveats:
  - The Dataverse description and README say "several fish farms in Norway", while both papers say "a fish farm". See Open questions.
  - A literal reading, "Lesund" (a hamlet in Aure, 63.33 N 8.47 E, about 130 km away), is not covered by this radius. We judge it unlikely.
- **How a sample maps to its coordinate:** it cannot be mapped per sample. Filenames (`<class>.<6-digit index>.png`), class folders and annotation columns carry no site, video or time. Every NorFisk v1.0 sample maps to the single site `norfisk_alesund_farm` in `tests/fixtures/norfisk/publication_sites.csv`.

### resolve_geo recipe
Input: one fixture record, which is an annotation row such as `salmonid.000001.png,salmonid,129,191,602,359,730,549` (or its zip member path), plus `publication_sites.csv`.
1. Parse the row as CSV with columns `file_name,class,xmin,ymin,xmax,ymax,width,height`. Check that `file_name` matches `^(saithe|salmonid)\.\d{6}\.png$` and that `class` is in {saithe, salmonid}.
   - If the record is not a NorFisk v1.0 member (for example from a future v2 that may include other farms), return the "none" result from step 4.
2. Look up the site. All v1.0 samples use `site_id = "norfisk_alesund_farm"`. Read its row from `publication_sites.csv`: lat 62.4711412, lon 6.1551755, depth_m empty, uncertainty_m 30000.
3. Return:
   - `lat = 62.4711412`, `lon = 6.1551755`
   - `depth_m = None` (the source gives only "1–50 m"; never fill in a midpoint)
   - `geo_precision = "region"` (the uncertainty is over 5 km)
   - `geo_source = "publication: Crescitelli et al. 2021 MIC doi:10.4173/mic.2021.1.1 Sec. 3.2 p.9 'farm is located near [Å]lesund'; geocoded Ålesund via OSM Nominatim node 31264149"`
   - `geo_inferred = True`
   - `geo_uncertainty_m = 30000`
4. Missing data: if `publication_sites.csv` or the site row is missing, or step 1 fails, return `lat=None, lon=None, depth_m=None, geo_precision="none", geo_source="none", geo_inferred=False, geo_uncertainty_m=None`.
5. Do not use the bounding-box columns or the image dimensions for geolocation.

## Access & download recipe
- **Enumeration:**
  - There are two files. List them with `GET https://dataverse.no/api/datasets/:persistentId/?persistentId=doi:10.18710/H5G3K5` → `data.latestVersion.files[]`, which gives ids 86886 (README) and 86889 (zip).
  - No auth is needed. No pagination exists.
  - No rate limit is documented. Stay at 1 request/s or less.
- **Full fetch (recommended at only 2.64 GB):**
  - Run `curl -L -C - -A "$UA" -o NorFisk_v1.0.zip https://dataverse.no/api/access/datafile/86889`.
  - The 303 goes to a pre-signed S3 URL that returns `accept-ranges: bytes`, so resuming works. If a resume comes more than 6 h after the first request, call the API URL again to get a fresh signature.
  - Verify the MD5 `6ec799e74054dec2dadb6f9179e51ea5`.
  - Unzip `*/img/*.png` → `<data_root>/norfisk/images/<class>/`. Put `*/annotations/*.txt` and `00_ReadMe.txt` → `<data_root>/norfisk/metadata/`. `videos/` stays empty.
- **Selective fetch (no full download):** the zip is plain (not zip64) and every member is STORED, with no compression.
  1. Range-GET the last 64 KB. Find the EOCD: 25,034 entries, central directory 2,629,252 B at offset 2,638,671,501.
  2. Range-GET the central directory to get each member's local-header offset and size.
  3. For each chosen image, Range-GET `offset … offset + 30 + name_len + extra_len + size`, then strip the 30-byte local header, the name and the extra field.
  - The annotation blocks are contiguous: saithe at bytes 142–430,961 and salmonid at 932,306,983–933,725,384. Two requests return all 12,514 rows.
  - This was tested for headers only; no images were downloaded.
- **Sampling for a budget of N:**
  - There is no site or time metadata to stratify on. Split N between the classes; for example, take saithe at up to 50 % to boost the wild-fish and outside-pen diversity.
  - Within each class, pick indices evenly spaced over 1…max. Sequential indices probably come from the same video and second.
  - Prefer crops of 224 px or more.
  - Apply perceptual-hash dedup before counting toward N.

## Manual steps (human)
- None.
- Optional: open Banno et al. 2022 (doi:10.3354/aei00432, CC BY 4.0) in a browser and check its Methods for a named NTNU research site near Ålesund. The publisher's bot check blocked automated access. Even with a site name, tying the 2017–2020 NorFisk footage to that site would remain an assumption.

## Fixtures
- `tests/fixtures/norfisk/dataverse_schemaorg.json`: schema.org export of the dataset, unmodified (licence, file URLs and sizes).
- `tests/fixtures/norfisk/dataverse_dataset_trimmed.json`: native Dataverse dataset JSON with the `datasetContact` (e-mail) field dropped (licence, dateOfCollection, file ids and MD5s).
- `tests/fixtures/norfisk/00_ReadMe_excerpt.txt`: provider README with the one e-mail line dropped (format, depths, cameras).
- `tests/fixtures/norfisk/saithe.000001.txt`: real annotation file, exact zip member bytes.
- `tests/fixtures/norfisk/salmonid.000001.txt`: real annotation file, exact zip member bytes.
- `tests/fixtures/norfisk/publication_sites.csv`: one publication-derived site (Ålesund, 30 km).
- `tests/fixtures/norfisk/SOURCE.md`: URLs, retrieval date, trimming, paper quote and gazetteer result.

## Short download instruction
NorFisk (CC0, tier A): `curl -L -C - -o NorFisk_v1.0.zip https://dataverse.no/api/access/datafile/86889` (2.64 GB, MD5 6ec799e74054dec2dadb6f9179e51ea5, Range/resume OK).
Unzip `saithe|salmonid/img/*.png` → images/ and `*/annotations/*.txt` + README (datafile/86886) → metadata/.
12,514 PNG fish crops; no videos; no per-image geo or time.
Geo: every sample gets lat 62.4711, lon 6.1552, region, ±30 km, geo_inferred=true (paper doi:10.4173/mic.2021.1.1 §3.2 "near Ålesund").
Dedup near-identical crops (1 fps frames) and drop crops under 224 px if needed.

## Open questions / risks
- **Spelling of the place:** the PDF literally prints "near lesund". We read it as Ålesund (the word is lower-case, the authors are at NTNU Ålesund, and the README names "NTNU i Ålesund"). Nominatim also knows a hamlet "Lesund" in Aure (63.3309, 8.4669), about 130 km away. If that reading were correct, every coordinate would fall outside the 30 km radius.
- **One farm or several:** the Dataverse description and README say "several fish farms in Norway", while the MIC 2021 and ICIEA 2020 papers say "a fish farm". The paper also says the test images came from "videos taken in different places and times". Some footage may therefore come from other farms; this is a contradiction in the sources. The licence is unaffected; the geo uncertainty may be underestimated.
- **Farm identity:** the farm is unknown. An NTNU press release (2021) on later work mentions "an aquaculture site where NTNU has a research license". We did not identify the site. We stopped a search of the Fiskeridirektoratet register, which showed only NTNU's Trondheim licences, and we did not use it.
- **No per-image metadata:** there is no video id, timestamp or depth. Temporal or spatial stratification is impossible, and near-duplicates are likely.
- **Crops, not full frames:** the images are object-centred crops with varying scale. They suit object-centric pretraining; scene-level diversity is limited.
- **No v2:** the paper and README promise a v2 with more than 150 h of 2020 wild-fish footage. A DataverseNO search on 2026-10-06 found only doi:10.18710/H5G3K5 (v1.0 / v1.1, same files). Re-check later.
- **Metadata errors:** the README calls the archive `NorFisk_v1.0.tar`, but the file is a `.zip`. Dataverse has the author's given and family names swapped.
