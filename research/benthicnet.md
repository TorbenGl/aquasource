# BenthicNet (1M / 11M / Labelled) (`benthicnet`)
Status: verified · researched 2026-10-06 · independently verified 2026-10-06 (see the Verification section at the end)

## Summary
BenthicNet (Lowe, Misiuk, Xu et al., *Scientific Data* 12, 230, 2025) is a global compilation of seafloor photos from 1965 to 2021, hosted on the Canadian FRDR. It has three parts:
- **BenthicNet-11M**: 11,408,887 images. This is a description only. BenthicNet does not host these images or publish a list of them; they stay at their origin repositories.
- **BenthicNet-1M**: 1,345,096 images, spatially rarefied from the 11M. FRDR hosts them as 512 px JPEG tars (215 GB) with a per-image CSV.
- **BenthicNet-Labelled**: 188,688 images with 3.1 M CATAMI labels (28 GB of tars).

A separate record, BenthicNet-URLs, hosts about 0.4 M full-resolution originals (782 GB) of images that had no public URL elsewhere. These include all of the individual contributions (NGU, DFO, MUN, SEAM, Hakai and others) and the XL Catlin Seaview images.

Every image row carries `latitude`/`longitude` (WGS 84, 99.63 % filled in 1M, 100 % in Labelled) and a GEBCO-derived depth. Precision is not flagged. By estimate, about two thirds of rows are true per-image positions, and the rest are station-level coordinates: RLS site coordinates, drop-camera stations, and site means imputed by the compilers.

The licence is set per image set in `00_Documentation/all_licenses_refs.csv`. By bytes of 1M:
- about 88 % is tier B (CC BY 3.0/4.0, OGL-Canada);
- about 4 % is tier A (U.S. Public Domain);
- about 4.4 % is Excluded (FathomNet NC-ND including the lower-case `fathomnet_misc` tar, MGDS NC-SA, USAP-DC NC, 2 PANGAEA NC);
- about 3.2 % is U. This covers the Schmidt Ocean `FK*` sets, which BenthicNet lists as CC BY but whose origin licence is CC BY-NC-SA, and datasets missing from the table.

Verdict: **ingest the A/B part, filtering per dataset.** Everything is reachable over anonymous HTTPS with Range support, so no Globus account is needed, which corrects the seed notes. Much of the content overlaps other catalog keys (SQUIDLE+, PANGAEA, Catlin, NOAA, NRCan, RLS, AADC), so deduplicate by `url`.

## Entry points
- Paper: https://doi.org/10.1038/s41597-025-04491-1. Preprint: https://arxiv.org/abs/2405.05241 (v3 read).
- FRDR BenthicNet **v2 (current)**: https://doi.org/10.20383/103.01241, which resolves to https://www.frdr-dfdr.ca/repo/dataset/a1e4ff21-8f5e-40d6-97cb-2c6e95c12c18. Globus endpoint `59ff4285-b842-47e7-bce9-56cf50ad34ab`, path `/9/published/publication_1236/submitted_data/`.
- FRDR BenthicNet v1 (superseded, same images): https://doi.org/10.20383/103.0614, path `/9/published/publication_609/`.
- FRDR BenthicNet-URLs (full-resolution originals): https://doi.org/10.20383/103.0966, which resolves to https://www.frdr-dfdr.ca/repo/dataset/e59f9418-d13b-4a21-84ba-97fd0a48db6f, path `/9/published/publication_961/submitted_data/`.
- Anonymous HTTPS file access: `https://www.frdr-dfdr.ca/repo/files/9/published/publication_1236/submitted_data/<relpath>`. This returns a 302 to `https://g-1f414e.cd4fe.0ec8.data.globus.org/9/published/publication_1236/submitted_data/<relpath>`, which serves `Accept-Ranges: bytes` and `Access-Control-Allow-Origin: *`.
- Listing API (FRDR size cache, JSON): `https://www.frdr-dfdr.ca/cache/9/publication_<id>/file_sizes/file_sizes.json` for the root, and `.../file_sizes-<sha256(relative/folder/path)>.json` for each subfolder.
- Key files in v2:
  - `01_BenthicNet/csvs/finalized_csvs.zip` (110,341,064 B). Members: `benthicnet_unlabelled_sub.csv` (1M, 348.6 MB unzipped), `benthicnet_labelled.csv` (1.31 GB unzipped, one row per label), `labelled_counts.csv`, `benthicnet_taxonomies.csv` and `trainable/*`.
  - `00_Documentation/all_licenses_refs.csv` (per-dataset licence and citation) and `00_Documentation/licenses/*.txt`.
  - `01_BenthicNet/images/unlabelled/full_unlabelled_512px.tar` (215,328,665,600 B) and `.../unlabelled/individual_dataset_tars/<dataset>.tar` (2,024 tars, 216.3 GB).
  - `01_BenthicNet/images/labelled/full_labelled_512px.tar` (28,418,600,960 B) and `.../labelled/individual_dataset_tars/<dataset>.tar` (385 tars, 28.6 GB).
  - `02_Pre-Trained_Models/` (2.26 GB of SSL checkpoints).
- Key files in BenthicNet-URLs: `01_Data/benthicnet-urls.csv` (90.7 MB, columns `source,dataset,site,image,url`), `01_Data/images/<dataset>/<site>/<file>` (63 datasets, 781.5 GB) and `00_Documentation/benthicnet-urls_licenses_refs.csv`.
- Code: https://github.com/DalhousieAI/BenthicNet (`benthicnet/io.py` defines the output path `<dataset>/<site>/<image>.jpg`), https://github.com/DalhousieAI/squidle-downloader and https://github.com/DalhousieAI/pangaea-downloader.

## Licence
- Tier: **B overall, but the pipeline must tier each dataset.** Map the `License` column of `all_licenses_refs.csv` as follows:
  - `U.S. Public Domain` (the file `LICENSE_Public_Domain.txt` contains CC0 1.0) → **A**.
  - `CC-BY-4.0`, `CC-BY-3.0` and `Open Government Licence - Canada` → **B**.
  - `CC-BY-NC-ND-4.0` (8 FathomNet sets), `CC-BY-NC-SA-3.0 US` (6 MGDS), `CC-BY-NC-4.0` (5 USAP-DC), `CC-BY-NC-3.0` and `CC-BY-NC-SA-3.0` (1 PANGAEA each) → **Excluded**.
  - Override to **U**: the 9 SQUIDLE+ Schmidt Ocean datasets (`FK181210, FK190106, FK190726, FK200126, FK200308, FK200429, FK200802, FK200930, fk180731`). BenthicNet lists them as CC-BY-4.0, but SOI and MGDS publish this imagery as CC BY-NC-SA 4.0. Also **U**: any dataset whose tar or CSV name has no row in the table, even after a **case-insensitive** match. These are 19 unlabelled tars (`RLS_Coral Sea_2022`, `RLS_Kangaroo Island_2021`, 10× `pangaea-*`, 6× `wa_peel-harvey_*` and `nrcan-71014`) and 14 labelled tars, all `pangaea-*`.
  - Join case-insensitively. Both `FathomNet_misc.tar` and `fathomnet_misc.tar` exist; the lower-case one matches the licence row `FathomNet_misc` (CC-BY-NC-ND-4.0), so it is **Excluded**, not U. As a safety net, also exclude any row whose `source` is `FathomNet`, `MGDS` or `USAP-DC`.
  - The unlisted `pangaea-*` sets can be resolved at record level from the PANGAEA metadata: `https://doi.pangaea.de/10.1594/PANGAEA.615784?format=metainfo_xml` gives `creativecommons.org/licenses/by/3.0/`, and `PANGAEA.907013` gives `creativecommons.org/licenses/by/4.0/`. Promote a set to B only after reading its own record.
  - Measured shares, using the bytes of the per-dataset 512 px tars as a proxy for image count:
    - 1M: A 4.0 % (23 sets), B 88.4 % (1,951), Excluded 4.4 % (22), U 3.2 % (28). (The first draft had Excluded 3.8 % / U 3.8 % because `fathomnet_misc` was counted as unlisted.)
    - Labelled: A 6.5 % (6), B 89.5 % (363), U 4.0 % (16: `FK200308`, `fk180731` and 14 `pangaea-*`).
  - Origin cross-checks of the two biggest B sources: XL Catlin Seaview is CC BY 3.0 at origin (UQ eSpace, DOI 10.14264/uql.2019.930, licence `http://creativecommons.org/licenses/by/3.0/deed.en_US` as listed on https://researchdata.edu.au/seaview-survey-photo-classification-dataset/3369315). RLS photo-quadrats are "Creative Commons Attribution 3.0 Australia License" at origin (IMAS record `6e9c4980-1005-11dd-b28e-00188b4c0af8`, https://metadata.imas.utas.edu.au/geonetwork/srv/api/records/6e9c4980-1005-11dd-b28e-00188b4c0af8), not CC BY 4.0 as BenthicNet lists. Both are tier B, but the attribution for RLS rows should cite the RLS record.
- Licence text (quote) + level read (file / record / collection) + URL:
  - Collection level (FRDR v2 record `dc.rights`, https://www.frdr-dfdr.ca/repo/dataset/a1e4ff21-8f5e-40d6-97cb-2c6e95c12c18?mode=full): "This dataset is made available under a custom license, as follows. The model data are available under the Creative Commons Attribution 4.0 (CC-BY-4.0) License. Image data within this collection are made available under a variety of terms. The specific license assigned to each image set is listed in the document "00_Documentation/all_licenses_refs.csv" and the full terms and conditions of each license are available in "00_Documentation/licenses"."
  - README.txt (v2): "Image data within this collection are usable under Creative Commons* licenses. … The metadata and models are provided in this repository are available for reuse without restriction under the Creative Commons Attribution 4.0 License (CC-BY-4.0)".
  - Paper (*Data Records*): "Most images are available for use without restriction under CC-BY-4.0, except where the original licenses of individual datasets indicate limitations to derivative or commercial uses. The individual licenses for all datasets comprising BenthicNet are retained".
  - **Record level (per image set, the most specific level BenthicNet offers)**: `https://www.frdr-dfdr.ca/repo/files/9/published/publication_1236/submitted_data/00_Documentation/all_licenses_refs.csv`, with columns `Source,Dataset,License,Citation` and 2,004 rows. Counts: CC-BY-3.0 1,043; CC-BY-4.0 841; OGL-Canada 76; U.S. Public Domain 23; CC-BY-NC-ND-4.0 8; CC-BY-NC-SA-3.0 US 6; CC-BY-NC-4.0 5; CC-BY-NC-3.0 1; CC-BY-NC-SA-3.0 1.
  - Contradictions found:
    - BenthicNet-URLs record `dc.rights` says "Creative Commons Attribution 4.0 International (CC BY 4.0)" for the whole record. Its own `00_Documentation/benthicnet-urls_licenses_refs.csv` gives NC licences for `AT18-12`, `FK200429-mgds`, `LISMARC*` (MGDS) and `King_George_Bransfield_2018`, `LMG1311`, `LMG1703`, `NBP1402`, `NBP1502` (USAP-DC). The per-dataset licence wins, so these are Excluded. The origin pages agree: USAP-DC https://www.usap-dc.org/view/dataset/601311 says "Creative Commons Attribution-NonCommercial v4.0 Generic [CC BY-NC 4.0]"; MGDS https://www.marine-geo.org/doi/10.26022/IEDA/329944 says "Attribution-NonCommercial-ShareAlike 4.0 International [CC BY-NC-SA 4.0]".
    - The SQUIDLE+ copies of SOI cruises are listed as CC-BY-4.0 by BenthicNet, but SOI states it "has now applied the Creative Commons Attribution-Noncommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) License" (https://schmidtocean.org/newsletter04-data-in-open/). These sets are **U**; do not ingest.
    - All 691 SQUIDLE+ sets are blanket-listed as CC-BY-4.0 with an empty citation. Cross-check them against the per-campaign licences found for `squidle_imos` before relying on them.
- Attribution / citation text to store with every sample:
  - BenthicNet: "Lowe, S.C., Misiuk, B., Xu, I., et al. (2025). BenthicNet: A global compilation of seafloor images for deep learning applications. Scientific Data 12, 230. https://doi.org/10.1038/s41597-025-04491-1; Misiuk, B., Lowe, S., Xu, I. (2024). BenthicNet. Federated Research Data Repository. https://doi.org/10.20383/103.01241".
  - Per dataset, add the `Citation` column of `all_licenses_refs.csv` (the file is cp1252-encoded), plus `License`, `Source`, `dataset` and the origin `url`.
  - For images served from BenthicNet-URLs, also add "Misiuk, B., Lowe, S., Xu, I. (2024). BenthicNet-URLs. FRDR. https://doi.org/10.20383/103.0966".
- Embargo / moratorium / special terms:
  - There is no embargo.
  - The umbrella is a "custom license". The pipeline must carry the per-dataset licence on each sample.
  - The ND/SA sets must not be resized or redistributed; drop them.
  - `03_Superseded_Files/` holds old CSVs; do not use them.

## Media
- Types, counts, formats, resolution, total size, time range:
  - Still images only. Video sources (NGU, Hakai, DFO, DFO IOS, the SEAM drift video) were already converted to frames, mostly 1 frame per 10 s.
  - **1M**: 1,345,096 JPEGs, shortest side about 512 px (±10 %), about 160 kB each. Total 215.3 GB as one tar, or 216.3 GB across 2,024 per-dataset tars (median 18 MB, 90th percentile 215 MB, largest `CatlinSeaview_PAC_AUS.tar` 15.3 GB; 1,476 tars are under 50 MB).
  - **Labelled**: 188,688 images in 28.4 GB (one tar) or 385 per-dataset tars totalling 28.6 GB. Some of these also appear in 1M.
  - **Originals**: reachable at each row's `url`. Formats and resolutions vary: for example 4K `.tif` (Bay_of_Fundy_2019, about 12 MB each), `.png` (Chesterfield), RLS JPEGs of about 1.6 MB, and SOI framegrabs of about 160 kB.
  - **BenthicNet-URLs**: 781.5 GB of originals. By file-count estimate this is about 0.39 M files across 63 datasets: all individual contributions, NGU, NEFSC HabCam 2015, the USGS Tortugas/Crocker/FRRP sets, MGDS, USAP-DC, AADC VMS_2011 and Catlin (about 550 GB).
  - **11M**: no distributed list exists. `finalized_csvs.zip` (v2) and the superseded zip both lack an 11M CSV, and the README's mention of `benthicnet_unlabelled.csv` is wrong. Reaching the 11M means going back to the origin sources, mainly SQUIDLE+ (9.17 M), Catlin (1.08 M) and PANGAEA (0.76 M).
  - Time range is 1965-11-25 to 2021-12-22 (`dc.coverage.temporal`). Datetimes were partly imputed and should be treated as "accurate to the year". Formats are mixed: `YYYY-MM-DD HH:MM:SS[.ffffff]`, `…+00:00`, and date-only.
  - Byte shares of 1M by source: Catlin 24.9 %, RLS (via SQUIDLE+) 23.8 %, other SQUIDLE+ 22.4 %, PANGAEA 14.6 %, NOAA 3.6 %, FathomNet 3.2 %, NGU 2.0 %, NRCan 1.4 %, everything else under 1 % each.
- Filters needed:
  - Black and water-column frames: SQUIDLE+ ROV "AUTO_5S" framegrabs cover descent and ascent, and AUV start and end frames.
  - On-deck and surface frames: the compilers removed these manually only for MGDS and USAP-DC, and screened NOAA/USGS/PANGAEA by keywords. SQUIDLE+ and FathomNet were not screened.
  - `nrcan-71014`: collages of 2-6 photos. The paper says this set was excluded, but its tar is present, so drop it.
  - NRCan pre-1978 photos are greyscale film scans. Keep them, but tag them.
  - PANGAEA experimental growth plates, and quadrat-frame photos (UFES images were cropped to remove the quadrat frame).
  - RLS photo-quadrats: check whether the first photo of a transect is a dive-slate or ID shot.
  - **Overlaps**, deduplicated by normalised `url` (http→https, strip trailing `/`) and by perceptual hash:
    - BenthicNet internally: `FK200429` (SQUIDLE+) vs `FK200429-mgds`, and Labelled vs 1M.
    - Other catalog keys: `squidle_imos` (all SQUIDLE+ incl. IMOS AUV, NESP, Reef Builder), `reef_life_survey` (RLS_*), `schmidt_ocean` (FK*), `pangaea_images`, `fathomnet`, `catlin_seaview`, `noaa_ncrmp` (e.g. `Hawaii_Archipelago_2019`), `noaa_habcam` (`NOAA_HabCam_2015`), `usgs_cmgp` (sATRIS Tortugas), `canada_ogl` (NRCan GSC photos, DFO), `aadc`.
    - Store `url`, `source`, `dataset`, `site` and `image` for every sample.

## Geolocation
- Precision levels, as estimates. Precision is not stored and must be inferred from the data:
  - **image** is about 65-70 % of 1M: per-image `latitude/longitude` from AUV/ROV/tow navigation, diver GPS or per-frame video navigation. This covers most SQUIDLE+ non-RLS sets, Catlin, NGU, SEAM BoF, MUN, LaboGeo and much of PANGAEA.
  - **station** is about 25-30 %:
    - RLS photo-quadrats: SQUIDLE+ gives each photo a synthetic position. The site coordinate is rounded to 0.01° and each photo gets a small synthetic offset of about 2.5 m per photo (2.25e-5°, mostly in latitude). Times are synthetic, counting up from 00:00:00 in 20 s steps (e.g. `RLS_Abrolhos (WA)_2021`) or 1 s steps (e.g. `RLS_Abrolhos Islands_2008` sites named `<id>_WA53_2008-03-24`).
    - NRCan GSC: 1,804 camera stations.
    - Drop-camera stations (for example `Bedford_2017`).
    - ROV dives with a single dive coordinate (for example `FK200429_S0353`, 19 frames over 19 h at one point).
    - NOAA, USGS and USAP-DC sites whose coordinates the compilers imputed as "the mean centre of the study site bounding box".
  - **region** is under 1 %: one coordinate for a whole multi-site dataset.
  - **none** is 0.37 % of 1M (paper Table 3: latitude/longitude coverage 99.63 %).
- geo_source:
  - `benthicnet_unlabelled_sub.csv` columns `latitude`, `longitude`; or `benthicnet_labelled.csv` columns `longitude`, `latitude`. **The column order is swapped in the labelled CSV**, so always parse by header name.
  - CRS: WGS 84, decimal degrees. The paper says "All geographic coordinates were converted to decimal degrees using the WGS 84 datum".
  - Depth comes from `gebco_bathymetry`, which is "Depth interpolated from GEBCO2022" (bilinear) and stored as negative elevation in metres. It is **modelled, not sensor depth**. It is 0.0 or positive at many shallow coastal RLS sites (for example `RLS_Abrolhos Islands_2013`): 1,613 of the first 7,669 rows of the 1M CSV (21 %, almost all RLS) have `gebco_bathymetry >= 0`. Those values must become null. No measured depth column exists.
  - `emu` is the nearest Ecological Marine Unit and is not needed.
  - Uncertainty: per-image navigation error is not reported, so the image level is null. RLS is about 1 km. Shared-coordinate stations are 1-5 km. Region-level rows are unknown.
- How a sample maps to its coordinate:
  - One CSV row equals one image. The labelled CSV has one row per label, so deduplicate it by `url`.
  - The 512 px file is the tar member `<sanitize(dataset)>/<sanitize(site)>/<image>.jpg` inside `<dataset>.tar`. `sanitize` drops non-ASCII characters, strips spaces and dots at the ends, replaces `/` with `-` and removes `:*?"<>|` (see `benthicnet/io.py`).
  - The original is at the row's `url`.
  - `benthicnet-urls.csv` has no coordinates. Join it to the main CSVs on `url` (or on `dataset`,`site`,`image`).

### resolve_geo recipe
Context, precomputed once per CSV:
- `site[(dataset,site)]` holds `n`, the number of unique `url`s, and `coords`, the set of non-null (lat, lon).
- `ds[dataset]` holds `sites`, the set of sites; `coords`, the set of coordinates; `multi`, the number of sites with n>1; and `shared`, the number of sites with n>1 and exactly one coordinate.

1. `lat = float(row["latitude"])` and `lon = float(row["longitude"])`, always looked up by column name. If either is empty or NaN, out of range, or exactly (0, 0), return `{lat:None, lon:None, depth_m:None, geo_precision:"none", geo_source:<below>, geo_inferred:False, geo_uncertainty_m:None}`.
2. `g = float(row["gebco_bathymetry"])` (or NaN). Then `depth_m = round(-g, 1)` if `g < 0`, otherwise `None`.
3. Set `geo_source = "<csv name>:latitude,longitude (WGS84 dd); depth_m=-gebco_bathymetry (GEBCO_2022 bilinear, modelled)"`.
4. Classify:
   - a. If `dataset` starts with `"RLS_"`, use `station`, inferred=True, uncertainty=1000.
   - b. Otherwise, if `len(ds.sites) >= 2` and `len(ds.coords) == 1`, use `region`, inferred=True, uncertainty=None.
   - c. Otherwise, use `station` with inferred=True when either of these holds: the site has `n > 1` and `len(site.coords) == 1`; or the site has `n == 1`, `ds.multi > 0` and `ds.shared/ds.multi >= 0.5`. Set the uncertainty by `source`: 5000 for NOAA, USGS or USAP-DC (bounding-box-centre imputation); 2000 if `source == "MGDS"` or the dataset starts with `fk`/`FK` (dive-level ROV coordinate); 1000 otherwise.
   - d. Otherwise use `image`, inferred=False, uncertainty=None.
5. Never return `segment`. No navigation file is supplied.

Expected results on the fixtures:

| fixture row(s) | lat, lon | depth_m | precision | inferred | unc. |
|---|---|---|---|---|---|
| `FK200429/FK200429_S0353` (3 rows) | -14.4974831, 146.31264484 | 1919.9 | station | true | 2000 |
| `FK200802/FK200802_S0380` row 1 | -15.36099238, 145.80320994 | 578.8 | image | false | null |
| `RLS_Abrolhos (WA)_2021/912354604` row 1 | -28.7199775, 113.79 | 1.3 | station | true | 1000 |
| `RLS_Abrolhos Islands_2013/912354071` | -28.4299775, 113.73 | null (gebco 0.0) | station | true | 1000 |
| labelled `Bastos/A_001_margem` (2 label rows → 1 image) | -20.05703136, -39.84970526 | 52.0 | image | false | null |
| labelled `Bay_of_Fundy_2019/BoF_001` | 44.93015667, -65.59712833 | 72.1 | image | false | null |
| labelled `Bedford_2017/Bedford_Station1` (2 images) | 44.6814333357, -63.6363000002 | 35.3 | station | true | 1000 |
| labelled `Bedford_2017/Bedford_Station10` (1 image, dataset mostly shared) | 44.680999999, -63.6193999981 | 21.9 | station | true | 1000 |

The FK* rows are tier U by licence. They are kept in the fixtures only to test the geo logic.

## Access & download recipe
- Enumeration, auth and rate limits:
  - No authentication is needed.
  - List folders through the FRDR size cache: `GET https://www.frdr-dfdr.ca/cache/9/publication_1236/file_sizes/file_sizes-<sha256("01_BenthicNet/images/unlabelled/individual_dataset_tars")>.json`. This returns 2,024 entries `{name, path, size}`. The labelled folder is the same with `labelled` in the path.
  - Enumerate images by downloading `finalized_csvs.zip` (110 MB) and reading `benthicnet_unlabelled_sub.csv` and `benthicnet_labelled.csv`. Alternatively, Range-read just one member: parse the central directory from the last 64 KB, then fetch only that member's bytes, for example `benthicnet_unlabelled_sub.csv` at local header offset 56,786,150, compressed size 25,326,098.
  - Join the result with `all_licenses_refs.csv` on `dataset`, case-insensitively.
  - FRDR documents no rate limit. Stay at 1 request per second for small files and 2-4 parallel streams for tars, and back off on 429/503.
  - For multi-TB pulls, Globus Transfer (endpoint `59ff4285-b842-47e7-bce9-56cf50ad34ab`) is optional.
- How to fetch one media file:
  - (a) **512 px**: download `<dataset>.tar` from `https://www.frdr-dfdr.ca/repo/files/9/published/publication_1236/submitted_data/01_BenthicNet/images/unlabelled/individual_dataset_tars/<urlencoded dataset>.tar`. Follow the 302 with `curl -L`; resume works with `-C -` or Range. Then extract `<dataset>/<site>/<image>.jpg`. Each member is a PAX header, a ustar header (2×512 B) and the data. A tar has no index, so random access needs a sequential header walk.
  - (b) **Original**: `GET row.url` (seen to return 200 at `soi-egress.storage.googleapis.com`, `rls.tpac.org.au/pq/...JPG/`, and `www.frdr-dfdr.ca/repo/files/9/published/publication_961/...`, which redirects to Globus HTTPS with Range support). Many URLs are plain `http://`; try `https` first. Some origin links may have rotted.
- Sampling strategy for a budget of N samples:
  1. Keep rows with tier A or B, and deduplicate by `url` across 1M and Labelled and against the other catalog keys.
  2. Allocate N across `source` in proportion to sqrt(images), capping Catlin, RLS and SQUIDLE+ at 15 % each. Then spread each source's share round-robin over `dataset`, and then over `site`, at most ceil(N_dataset / n_sites) per site.
  3. Within a site, sort by `datetime` and take evenly spaced rows.
  4. Prefer `geo_precision=image` when the budget is tight. Favour sets unique to BenthicNet (NGU, DFO, MUN, SEAM, Hakai, 4D Oceans, EAC, HAL, UFES, NEFSC) when the overlapping keys are ingested separately.
  5. Fetch with route (a) when a dataset's tar is under 50 MB or at least 30 % of its rows are wanted. Otherwise use (b), at about 1 request per second per host, and downscale locally.
  6. Store files under `<data_root>/benthicnet/images/<dataset>/<site>/<image>.jpg` and metadata under `<data_root>/benthicnet/metadata/` (the CSV extract plus the licence table).

## Manual steps (human)
- None. Anonymous HTTPS works for every file, so neither a Globus account nor Globus Connect Personal is required. Globus is optional for bulk transfers of hundreds of GB.

## Fixtures
- `tests/fixtures/benthicnet/benthicnet_unlabelled_sub_sample.csv`: header plus 9 real rows of the 1M CSV (FK200429 shared-coordinate dive, FK200802 per-frame, RLS synthetic offsets, RLS with gebco 0.0).
- `tests/fixtures/benthicnet/benthicnet_labelled_sample.csv`: header plus 8 real label rows (Bastos with 2 labels for one image, Bay_of_Fundy_2019, Chesterfield, Bedford_2017 station rows). Longitude comes before latitude.
- `tests/fixtures/benthicnet/all_licenses_refs_excerpt.csv`: 20 real rows of the per-dataset licence table, cp1252-encoded with CRLF line endings, covering every licence class. The last row (`FathomNet_misc`) tests the case-insensitive join against `fathomnet_misc.tar`.
- `tests/fixtures/benthicnet/frdr_file_sizes_root.json`: the FRDR size-cache response for the root of the v2 publication.
- `tests/fixtures/benthicnet/README_licence_excerpt.txt`: the licence paragraph of the v2 README, verbatim.
- `tests/fixtures/benthicnet/SOURCE.md`: URLs, Range offsets, retrieval date and trimming.

## Short download instruction
1. Fetch `https://www.frdr-dfdr.ca/repo/files/9/published/publication_1236/submitted_data/01_BenthicNet/csvs/finalized_csvs.zip` and `.../00_Documentation/all_licenses_refs.csv` (cp1252), using `curl -L` with anonymous HTTPS.
2. Join `benthicnet_unlabelled_sub.csv` and `benthicnet_labelled.csv` to the licence table on `dataset` (case-insensitive). Keep Public Domain, CC-BY and OGL-Canada; drop NC/ND, `source` FathomNet/MGDS/USAP-DC, `FK*`/`fk*` (SOI) and unlisted datasets.
3. Get images from `.../01_BenthicNet/images/{unlabelled,labelled}/individual_dataset_tars/<dataset>.tar` (512 px; members `<dataset>/<site>/<image>.jpg`; Range and resume work), or the original at the row's `url`.
4. Geo: `latitude`/`longitude` per row (WGS 84). `depth_m = -gebco_bathymetry` (modelled). RLS and shared-coordinate sites are `station`.

## Open questions / risks
- BenthicNet-11M has no published image list. Only the 1M and Labelled CSVs exist, despite the README referring to `benthicnet_unlabelled.csv`. The rest of the 11M must come from the origin keys (`squidle_imos`, `catlin_seaview`, `pangaea_images`, …).
- The SQUIDLE+ blanket "CC-BY-4.0" is unreliable. It is proven wrong for the SOI sets, which are CC BY-NC-SA 4.0 at origin. Other SQUIDLE+ campaigns (NESP, Reef Builder/TNC, university AUVs) need a per-campaign check, shared with `squidle_imos`.
- 33 dataset tars (19 unlabelled, 14 labelled) have no licence row, even case-insensitively, and are U until resolved. The PANGAEA ones can be checked through the PANGAEA metainfo API (two checked: CC BY 3.0 and CC BY 4.0), and `RLS_*` through the IMAS RLS record (CC BY 3.0 AU).
- The BenthicNet-URLs record-level CC BY 4.0 conflicts with its own per-dataset NC entries. The per-dataset licence is applied.
- The MGDS licence version differs: the table says CC-BY-NC-SA-3.0 US, the origin says 4.0. Both are NC, so the outcome is the same.
- Geo precision is not flagged, so the recipe relies on heuristics. The shares above are estimates from tar bytes and a 7.7k-row head sample. Run a full pass over the 1M CSV to measure them.
- The imputed site means and bounding-box centres for NOAA, USGS and USAP-DC may exceed 5 km, so `station` at 5000 m may be optimistic there. Check the bounding box against the origin metadata.
- Partial imputation is invisible to the recipe. The paper says "Missing datetime and coordinate information was imputed everywhere where reasonably possible — for example, by assigning the geographic mean centre of the image acquisition site where coordinates were missing for some images at a given site." Rows imputed this way inside an otherwise per-image site keep `geo_precision=image`. A full pass could flag them: several rows of one site sharing exactly the site-mean coordinate while the rest differ.
- GEBCO depth is modelled and unreliable in the nearshore. For example, at RLS Rat Island GEBCO gives 1.3 m while the filename says 5 m. Consider parsing the RLS depth from the filename (`_5m_`, `4.5m`) as a separate field.
- Datetimes are partly imputed (to the year) and their formats are mixed.
- Origin URLs (http://, SOI bucket, rls.tpac.org.au) may break. The FRDR Globus hostname `g-1f414e.cd4fe.0ec8.data.globus.org` may change, so always start from `www.frdr-dfdr.ca/repo/files/...`.
- `nrcan-71014` (collages) is present despite the paper excluding it. Possible water-column, black or on-deck frames remain in the SQUIDLE+ and FathomNet sets.

## Verification (2026-10-06)
Independent check of the claims above against primary sources (metadata only; no images or tars downloaded).

Checked:
- FRDR v2 record, full metadata: https://www.frdr-dfdr.ca/repo/dataset/a1e4ff21-8f5e-40d6-97cb-2c6e95c12c18?mode=full. The `dc.rights` quote is verbatim; `dc.coverage.temporal` is 1965-11-25/2021-12-22; Globus endpoint `59ff4285-b842-47e7-bce9-56cf50ad34ab`, path `/9/published/publication_1236/`.
- Per-dataset licence table, downloaded whole (337,573 B): https://www.frdr-dfdr.ca/repo/files/9/published/publication_1236/submitted_data/00_Documentation/all_licenses_refs.csv. 2,004 rows with columns `Source,Dataset,License,Citation`. Licence counts match exactly (CC-BY-3.0 1,043; CC-BY-4.0 841; OGL-Canada 76; U.S. Public Domain 23; CC-BY-NC-ND-4.0 8; CC-BY-NC-SA-3.0 US 6; CC-BY-NC-4.0 5; CC-BY-NC-SA-3.0 1; CC-BY-NC-3.0 1). All 691 SQUIDLE+ rows say CC-BY-4.0.
- `00_Documentation/licenses/LICENSE_Public_Domain.txt` is the CC0 1.0 legal code, so U.S. Public Domain maps to tier A.
- README.txt (v2, 11,635 B): the licence excerpt fixture is a verbatim substring. Its section 3 does name `benthicnet_unlabelled.csv`, which is not in the zip.
- BenthicNet-URLs record: https://www.frdr-dfdr.ca/repo/dataset/e59f9418-d13b-4a21-84ba-97fd0a48db6f?mode=full gives `dc.rights` "Creative Commons Attribution 4.0 International (CC BY 4.0)". Its own `00_Documentation/benthicnet-urls_licenses_refs.csv` (63 rows) lists 6 MGDS sets as CC-BY-NC-SA-3.0 US and 5 USAP-DC sets as CC-BY-NC-4.0. The contradiction is real; the per-dataset NC licence wins (Excluded). Size cache for `01_Data/images`: 63 folders, 781.5 GB.
- SOI: https://schmidtocean.org/newsletter04-data-in-open/ says "SOI has now applied the Creative Commons Attribution-Noncommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) License". The FK* sets stay U and are not ingested.
- Catlin origin: https://researchdata.edu.au/seaview-survey-photo-classification-dataset/3369315 (DOI 10.14264/uql.2019.930) gives `http://creativecommons.org/licenses/by/3.0/deed.en_US`, which matches BenthicNet's CC-BY-3.0.
- RLS origin: IMAS record https://metadata.imas.utas.edu.au/geonetwork/srv/api/records/6e9c4980-1005-11dd-b28e-00188b4c0af8 ("Reef Life Survey (RLS): Habitat Quadrats") gives "Creative Commons Attribution 3.0 Australia License" and links the image API `http://rls.tpac.org.au/`. That is tier B, but it differs from BenthicNet's CC-BY-4.0.
- Paper: arXiv 2405.05241v3 (HTML) and Crossref https://api.crossref.org/works/10.1038/s41597-025-04491-1. Counts 11,408,887 / 1,345,096 / 188,688 and 3,091,158 CATAMI labels are confirmed, as is the Table 3 lat/lon coverage of 99.63 % (Table 4: 100 %). "All geographic coordinates were converted to decimal degrees using the WGS 84 datum" is quoted correctly. Depths range from "<1 m to over 5,500 m". The paper also says expedition 71014 collages "were excluded". Crossref gives volume 12, article 230, published 2025-02-07.
- `finalized_csvs.zip`: HEAD gives 302 to Globus HTTPS, then 200 with `Accept-Ranges: bytes` and 110,341,064 B. The central directory, read with an explicit Range of the last 64 KiB, has 17 entries and no 11M CSV. `benthicnet_unlabelled_sub.csv` is at local header offset 56,786,150 with csz 25,326,098 and usz 348,603,319; `benthicnet_labelled.csv` is at 77 with usz 1,310,700,941. Suffix ranges (`bytes=-N`) return 416, so use explicit offsets.
- Columns: the 1M header is `url,source,dataset,site,image,latitude,longitude,datetime,gebco_bathymetry,emu`. The Labelled header has `longitude,latitude` in swapped order. Both confirmed by Range-inflating 128 KiB of each member.
- Fixtures: every row of both CSV samples is byte-identical to the stated line numbers of the live members. All 19 licence-excerpt rows match the live table. `frdr_file_sizes_root.json` is byte-identical to a fresh fetch of https://www.frdr-dfdr.ca/cache/9/publication_1236/file_sizes/file_sizes.json.
- Enumeration: the size cache `file_sizes-<sha256("01_BenthicNet/images/unlabelled/individual_dataset_tars")>.json` returns 2,024 tars totalling 216.26 GB (median 17.9 MB; 1,476 are under 50 MB; the largest is `CatlinSeaview_PAC_AUS.tar` at 15.27 GB). The labelled folder has 385 tars totalling 28.60 GB. `full_unlabelled_512px.tar` is 215,328,665,600 B. HEAD on `.../labelled/individual_dataset_tars/Bastos.tar` gives 302, then 200 with `Accept-Ranges: bytes` and 45,465,600 B, which matches the cache. HEAD on an RLS origin `url` over https (`rls.tpac.org.au/pq/912354604/...`) gives 200 `image/jpeg`.
- Geo spot checks: the fixture coordinates are in water with correct signs. FK200429 (Coral Sea, GEBCO -1,920 m), FK200802 (-578 m), Bastos (off Espírito Santo, -52 m), Bay of Fundy (-72 m), Bedford Basin (-35 m) and Chesterfield Inlet (-49 m) all check out. `FK200429_S0353` has 19 frames from 03:25 to 22:32 UTC at one coordinate, so `station` is correct. RLS rows confirm one 0.01° site coordinate plus synthetic 2.25e-5° steps.

Corrected:
- `fathomnet_misc.tar` is not unlisted. It is a lower-case variant of the `FathomNet_misc` row (CC-BY-NC-ND-4.0), so it is **Excluded**. The licence join must be case-insensitive. The 1M shares become A 4.0 % / B 88.4 % / Excluded 4.4 % / U 3.2 % (previously 3.8 % / 3.8 %). Unlisted tars: 19 unlabelled + 14 labelled = 33 (previously 34).
- RLS synthetic times use 20 s **or 1 s** steps, not only 20 s.
- `gebco_bathymetry >= 0` is common, not occasional: 21 % of the first 7,669 1M rows, almost all RLS. Expect many RLS rows with `depth_m = null`.
- The licence excerpt fixture has CRLF line endings, not LF (SOURCE.md is fixed). One real row (`FathomNet_misc`) was appended for the case-insensitive join test.
- Citation completed: *Scientific Data* 12, 230 (2025).
- Added: RLS origin licence is CC BY 3.0 AU (still B), Catlin origin CC BY 3.0 is confirmed, the unlisted PANGAEA sets are resolvable through the PANGAEA metainfo API (615784 is CC BY 3.0, 907013 is CC BY 4.0), and partial site-mean imputation risk is documented.

Confirmed unchanged: overall tier **B** with per-dataset filtering (A for U.S. Public Domain sets); geo precision image (majority) / station / region / none; anonymous HTTPS access with no human step; sizes and counts.
