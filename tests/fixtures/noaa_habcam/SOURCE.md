# Fixture sources: `noaa_habcam`

All files were retrieved on 2026-10-06 with User-Agent `aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`.
Values are unmodified. Some files keep only part of the rows, as noted below; no value was edited.

| File | Exact URL | Trimming |
|---|---|---|
| `viame_items_page.json` | https://viame.kitware.com/api/v1/item?folderId=5e4eed5478ed364cd0f98b40&limit=3&offset=2500&sort=name | None. This is the full response body: one Girder item-listing page (3 items) from the folder `US_NE_2015_NEFSC_HABCAM/Corrected` in the public VIAME "Training Data" collection. The filenames carry the UTC timestamps that `resolve_geo` parses. |
| `metadata_txt_excerpt.csv` | https://viame.kitware.com/api/v1/item/5e4eee2e78ed364cd0fabfa0/download (`metadata.txt`, 9,478,365 bytes, in the same folder) | Kept the header line and 4 of the 104,196 data rows: `"742"` (image `...103817616.70150`, which falls in an R2R-flagged nav hour) and `"2316"`–`"2318"` (the three images in `viame_items_page.json`). The rows are byte-identical and keep their CRLF line endings. This file has no lat/lon column. |
| `HRS1506_bestres_excerpt.geoCSV` | https://www.ncei.noaa.gov/data/oceans/archive/arc0207/0260576/4.6/data/0-data/HRS1506_616376_r2rnav/data/HRS1506_bestres.geoCSV (45,606,849 bytes, read with HTTP Range requests: bytes 0-2047, 4400200-4404800, 6901800-6903100) | Kept the 17-line GeoCSV header (through the `iso_time,...` column line), then 9 unflagged 1-s rows bracketing the three 16:06–16:07Z images, then 4 R2R-flagged rows (prefixed `#`, no speed/course columns) bracketing the 10:38:17Z image. The rows keep the relative order they have in the source file. In the full file the flagged blocks are interleaved and not in time order, so a parser must sort by `iso_time`. |
| `r2rnav_bag-info_HRS1506.txt` | https://www.ncei.noaa.gov/data/oceans/archive/arc0207/0260576/4.6/data/0-data/HRS1506_616376_r2rnav/bag-info.txt | None (full file). This is file-level licence evidence for the navigation: `R2R-License: Creative Commons - Public Domain Mark 1.0`. |
| `cff2017_items_page.json` | https://viame.kitware.com/api/v1/item?folderId=5eb371608d01d968cc1642dd&limit=2&offset=0&sort=name | None. This is the full response body: the first 2 items of `US_NE_2017_CFF_HABCAM/Left` (Coonamessett Farm Foundation HabCam V3). No public navigation exists for this subset, so it exercises the region/none branch of `resolve_geo`. |

## Expected `resolve_geo` results (linear interpolation between the bracketing 1-s fixes)

| Image | lat | lon | geo_precision | nav_flagged |
|---|---|---|---|---|
| 201503.20150517.160624359.187700.png | 37.687949 | -74.641700 | segment | false |
| 201503.20150517.160657817.187900.png | 37.687005 | -74.642168 | segment | false |
| 201503.20150517.160714563.188000.png | 37.686525 | -74.642405 | segment | false |
| 201503.20150517.103817616.70150.png | 37.909550 | -74.449934 | segment | true |
| 201509.20170708.060820993.10389.png (CFF) | null | null | region | n/a |

The values above are rounded to 6 decimals. For every 2015 row: depth_m = null, geo_inferred = true, geo_uncertainty_m = 300. The 300 m reflects that R2R positions are those of the ship's GPS antenna, while HabCam is towed behind the ship (layback), plus some uncertainty in clock synchronisation.

No `publication_sites.csv` is provided. Geolocation comes from archived ship navigation, not from a publication table.
