# Fixture sources: `noaa_ncrmp`

All files were retrieved on 2026-10-06 with User-Agent `aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`.
Values are unmodified. Only rows were dropped, as noted below. The CSV sources use CRLF line endings, and the fixtures keep them.

| File | Exact URL | Trimming |
|---|---|---|
| `site_info_climate_hawaii_2024.csv` | https://www.ncei.noaa.gov/data/oceans/archive/arc0247/0317534/1.1/data/0-data/NCRMP_CLIMATE_SITEINFO_HAWAII_2024.csv (4.2 KB, 87 data rows) | Header + the 3 rows `OCC-FFS-001`, `OCC-FFS-003`, `OCC-FFS-002`, in source order. These are the sites of the 3 images in `listing_0317534_excerpt.html`. |
| `site_info_climate_pria_2015.csv` | https://www.ncei.noaa.gov/data/oceans/archive/arc0104/0159155/1.1/data/0-data/Site_Info_PRIAs_2015.csv (1.6 KB, 40 data rows) | Header + rows `BAK-11` (site of image `BAK-11_2015_A_08.JPG`), `KIN-07` and `KIN-62`. The last two are two different sites with identical coordinates in the source. |
| `site_info_climate_nwhi_2019.csv` | https://www.ncei.noaa.gov/data/oceans/archive/arc0188/0240600/1.1/data/0-data/Benthic_Image_Site_Info_NWHI.csv (2.0 KB, 36 data rows) | Header + rows `FFS-4054` / `OCC-FFS-009`, `KUR-4131` / `OCC-KUR-007` and `KUR-4246` / `OCC-KUR-005`. The last two have identical coordinates in the source. The images in this accession are named by `OCC_SITEID`, e.g. `OCC-FFS-009_2019_01.JPG` (folder `NWHI_Climate_PHOTQUADS_2019/`). |
| `listing_0317534_excerpt.html` | https://www.ncei.noaa.gov/data/oceans/archive/arc0247/0317534/1.1/data/0-data/NCRMP_FIXED_IMAGES_HAWAII_2024/ (Apache autoindex, 583 KB, 2,577 image rows) | Kept all header/footer lines and the parent-directory row. Kept only 3 of 2,577 image rows: `OCC-FFS-001_2024_02.JPG`, `OCC-FFS-002_2024_03.JPG`, `OCC-FFS-003_2024_01.JPG`. Rows are byte-identical. |
| `cover_fixed_excerpt.csv` | https://www.ncei.noaa.gov/data/oceans/archive/arc0247/0317416/1.1/data/0-data/NCRMP_BENTHIC_COVER_FIXED_PACIFIC_2012-2025.csv (49 MB). Read with HTTP Range requests: bytes 0-6000 (header), 5495000-5507999 (BAK-11 2015 rows), 40990000-41009999 (OCC-FFS 2024 rows). | Header + 5 complete point rows, the first row in the fetched ranges for each of `BAK-11_2015_A_08.JPG`, `BAK-11_2015_A_03.JPG`, `OCC-FFS-003_2024_01.JPG`, `OCC-FFS-001_2024_02.JPG` and `OCC-FFS-002_2024_03.JPG`. The full file has about 10 point rows per annotated image; depth (`MIN_DEPTH`, `MAX_DEPTH`, in feet) is constant per site visit. |

Licence evidence (record level). NCEI landing page https://www.ncei.noaa.gov/archive/accession/0317534, section "Data License": "This dataset has been dedicated to the public domain under the Creative Commons CC0 1.0 Universal (CC0 1.0) Public Domain Dedication. SPDX License: Creative Commons Zero v1.0 Universal (CC0-1.0)". The older accessions (e.g. 0159155, 0240600) have no licence field. They have `accessLevel: public` and a "Cite as" use constraint (see `research/noaa_ncrmp.md`).

## Expected `resolve_geo` results

All resolved rows have geo_precision = station, geo_inferred = true and geo_uncertainty_m = 50. depth_m = mean(MIN_DEPTH, MAX_DEPTH) × 0.3048, rounded to 0.1 m.

| Image (accession) | Site-info fixture | lat | lon | depth_m | Note |
|---|---|---|---|---|---|
| OCC-FFS-001_2024_02.JPG (0317534) | site_info_climate_hawaii_2024.csv | 23.878545 | -166.290919 | 24.4 | 80.1 ft, DEPTH_SOURCE occ |
| OCC-FFS-002_2024_03.JPG (0317534) | site_info_climate_hawaii_2024.csv | 23.878185 | -166.291118 | 17.7 | 58.1 ft |
| OCC-FFS-003_2024_01.JPG (0317534) | site_info_climate_hawaii_2024.csv | 23.875517 | -166.292174 | 6.4 | 21 ft |
| BAK-11_2015_A_08.JPG (0159155) | site_info_climate_pria_2015.csv | 0.19864 | -176.48489 | 14.5 | MIN 48 / MAX 47 ft (inverted in source), DEPTH_SOURCE site. The cover CSV gives the more precise 0.19864247, -176.48489233 for the same site. |
| OCC-FFS-009_2019_01.JPG (0240600) | site_info_climate_nwhi_2019.csv | 23.63488 | -166.185688 | null | Joined via `OCC_SITEID`, not `SITE`. No cover row in the fixture. |
| OCC-FFS-099_2024_01.JPG (made-up) | site_info_climate_hawaii_2024.csv | null | null | null | geo_precision none: site code not in the CSV. |

No `publication_sites.csv` is provided: the coordinates come from the providers' own site-info tables, not from a publication.
