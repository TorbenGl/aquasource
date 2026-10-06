# Fixture sources: `benthicnet`

All files were retrieved on 2026-10-06 with User-Agent
`aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`.
The rows are real and their values are unchanged. Rows were only dropped, never edited.

FRDR serves files over anonymous HTTPS.
`https://www.frdr-dfdr.ca/repo/files/<path>` answers with a 302 redirect to the Globus HTTPS
collection `https://g-1f414e.cd4fe.0ec8.data.globus.org/<path>`. Both URLs are given below.

| File | Exact URL | What it is / trimming |
|---|---|---|
| `benthicnet_unlabelled_sub_sample.csv` | `https://www.frdr-dfdr.ca/repo/files/9/published/publication_1236/submitted_data/01_BenthicNet/csvs/finalized_csvs.zip` (redirects to `https://g-1f414e.cd4fe.0ec8.data.globus.org/9/published/publication_1236/submitted_data/01_BenthicNet/csvs/finalized_csvs.zip`), zip member `finalized_csvs/benthicnet_unlabelled_sub.csv` | This is the BenthicNet-1M metadata CSV (348,603,319 bytes uncompressed). The whole 110 MB zip was **not** downloaded. A single `Range: bytes=56786150-56917221` request fetched the member's local header plus the first 128 KiB of its deflate stream, and that was raw-inflated (`zlib`, wbits=-15). Kept: line 1 (the header) and lines 2-4 (`FK200429_S0353`, all frames share one coordinate). Also kept: lines 21-22 (`FK200802_S0380`, the coordinate changes per frame), lines 23-25 (RLS `RLS_Abrolhos (WA)_2021`, with synthetic per-photo offsets around a 2-decimal site coordinate) and line 343 (RLS `RLS_Abrolhos Islands_2013`, `gebco_bathymetry` = 0.0). Encoding is UTF-8 with LF line endings. |
| `benthicnet_labelled_sample.csv` | Same zip, member `finalized_csvs/benthicnet_labelled.csv` | This is the BenthicNet-Labelled CSV, with one row per label (1,310,700,941 bytes uncompressed). A `Range: bytes=77-131148` request fetched the first 128 KiB of the member, which was raw-inflated. Kept: line 1 (the header) and lines 2-3 (two label rows of the same image, `Bastos/A_001_margem`). Also kept: line 4 (`Bastos/A_002_margem`), line 486 (`Bay_of_Fundy_2019/BoF_001`), line 6439 (`Chesterfield/CI_01`), lines 6360-6361 (`Bedford_2017/Bedford_Station1`, two images with an identical station coordinate) and line 6362 (`Bedford_Station10`). Note that the column order is **longitude, latitude** here, which is the reverse of the 1M CSV. |
| `all_licenses_refs_excerpt.csv` | `https://www.frdr-dfdr.ca/repo/files/9/published/publication_1236/submitted_data/00_Documentation/all_licenses_refs.csv` (337,573 bytes, 2,004 data rows, downloaded whole) | This is the per-dataset licence table. Kept: the header plus 19 rows. These are the datasets that appear in the two CSV samples, and examples of each licence class: U.S. Public Domain (NOAA, USGS), OGL-Canada (NRCan), CC-BY-3.0 (PANGAEA, Catlin), CC-BY-NC-3.0 (PANGAEA), CC-BY-NC-ND-4.0 (FathomNet), CC-BY-NC-SA-3.0 US (MGDS `FK200429-mgds`) and CC-BY-NC-4.0 (USAP-DC `LMG1311`). The bytes are copied raw. The file is **cp1252/latin-1**, not UTF-8 (for example `González`), with LF line endings. |
| `frdr_file_sizes_root.json` | `https://www.frdr-dfdr.ca/cache/9/publication_1236/file_sizes/file_sizes.json` | This is the FRDR file-size cache for the root of the v2 publication (1,645 bytes, unmodified). Subfolders are served at `https://www.frdr-dfdr.ca/cache/9/publication_1236/file_sizes/file_sizes-<sha256(relative folder path)>.json`. For example, `sha256("01_BenthicNet/images/unlabelled/individual_dataset_tars")` lists all 2,024 per-dataset tars with their byte sizes. |
| `README_licence_excerpt.txt` | `https://www.frdr-dfdr.ca/repo/files/9/published/publication_1236/submitted_data/README.txt` (11,635 bytes) | This is a verbatim excerpt, the bytes from `1. Licenses/restrictions placed on the data:` up to just before `2. Links to publications ...` (README lines 40-48), with trailing whitespace trimmed at the end. |

Other files that were read but are not stored as fixtures (each was small or Range-limited):

- The FRDR landing pages `https://www.frdr-dfdr.ca/repo/dataset/a1e4ff21-8f5e-40d6-97cb-2c6e95c12c18?mode=full` (v2, DOI 10.20383/103.01241), `.../24c6c813-d0ff-4461-8174-3f960f1edc0d?mode=full` (v1, DOI 10.20383/103.0614) and `.../e59f9418-d13b-4a21-84ba-97fd0a48db6f?mode=full` (BenthicNet-URLs, DOI 10.20383/103.0966).
- `.../publication_1236/submitted_data/README_version_history_20250403.txt`, `CITATION.txt` and `frdr-dfdr-checksums.txt` (the list of 2,428 files).
- `.../00_Documentation/licenses/LICENSE_Public_Domain.txt`, which is CC0 1.0 text, and `LICENSE_Open_Government_Canada.txt`.
- The zip central directory of `finalized_csvs.zip`, read with a tail Range of 64 KiB. It holds 17 entries and no 11M-level CSV. The same was done for `03_Superseded_Files/csvs/finalized_csvs.zip`.
- `https://www.frdr-dfdr.ca/repo/files/9/published/publication_961/submitted_data/00_Documentation/benthicnet-urls_licenses_refs.csv` (63 datasets), `.../00_Documentation/README.txt`, `.../LICENSE.txt` (CC BY 4.0 text) and the first 64 KiB of `.../01_Data/benthicnet-urls.csv` (columns `source,dataset,site,image,url`).
- The first 1-2 KiB of `.../individual_dataset_tars/Bastos.tar` and `FK200429.tar`, which confirmed the member path `<dataset>/<site>/<image>.jpg` (each member has a PAX header).
- The paper, arXiv 2405.05241v3 (HTML), and the Scientific Data version, https://doi.org/10.1038/s41597-025-04491-1.
- MGDS `https://doi.org/10.26022/IEDA/329944`, whose licence reads "Attribution-NonCommercial-ShareAlike 4.0 International [CC BY-NC-SA 4.0]".
- USAP-DC `https://www.usap-dc.org/view/dataset/601311`, whose licence reads "Creative Commons Attribution-NonCommercial v4.0 Generic [CC BY-NC 4.0]".

No publication-derived coordinates are used, because every image row carries its own `latitude`/`longitude`. That is why there is no `publication_sites.csv`.
