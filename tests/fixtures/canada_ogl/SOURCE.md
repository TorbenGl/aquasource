# Fixtures for `canada_ogl`

All files retrieved 2026-10-06 with User-Agent `aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`.
Rows are byte-identical to the provider's lines (original encoding, CRLF line endings and BOM kept); trimming = rows dropped only.

| File | Exact source URL | Trimming |
|---|---|---|
| `fundy_image_locations_sample.csv` | https://api-proxy.edh-cde.dfo-mpo.gc.ca/catalogue/records/f9098f77-b2e1-423d-8950-eeabd7bba85b/attachments/BayFundy_ImageLocations.csv | Header + 6 of 5,081 data rows: data rows 1-3 (CON002, 2022, negative depth), row 387 (first CON029 row, 2023, positive depth), row 3451 (CON098, 2024, empty Latitude/Longitude and depth `0`), and the last row (CON121, empty distance/time-lapse). Encoding is cp1252 (the header contains `Bathymétrie` as byte 0xE9). |
| `fundy2022_video_segments_sample.csv` | https://api-proxy.edh-cde.dfo-mpo.gc.ca/catalogue/records/8ea6c28a-3d6c-47ef-8cf7-56790ee0c7f5/attachments/Start_End_Video_Transect_D_vexillum_BayFundy_2022.csv | Header + first 3 of 496 data rows (20-s video segments of CON_002, with start and end coordinates). UTF-8 with BOM, as served. |
| `gsc_station_query.json` | https://maps-cartes.services.geo.ca/server_serveur/rest/services/NRCan/GSC_Seabed_Photo_Collection/MapServer/0/query?where=1%3D1&outFields=*&resultRecordCount=3&orderByFields=OBJECTID&returnGeometry=true&outSR=4326&f=json | None. The query asked for 3 features (OBJECTID 1-3), and the file is the complete response. |
| `gsc_photos_95006_7392_sample.csv` | https://ftp.maps.canada.ca/pub/nrcan_rncan/raster/marine_geoscience/Seabed_Photo_Collection/95006/95006_7392.csv | Header + first 3 of 21 rows. Station-level case: every photo has the same PHOTO_LAT/PHOTO_LONG, and HORIZONTAL_POSITIONAL_ACCURACY says "no correction ... greater than plus/minus 20 percent of water depth". |
| `gsc_photos_2010020_0026_sample.csv` | https://ftp.maps.canada.ca/pub/nrcan_rncan/raster/marine_geoscience/Seabed_Photo_Collection/2010020/2010020_0026.csv | Header + first 3 of 86 rows. Image-level case: the positions differ per photo, with "Ultra-Short Baseline (USBL) positioning on camera used; position accurate to within 5 percent of water depth". |
| `licence.txt` | https://open.canada.ca/en/open-government-licence-canada | Plain text taken from the HTML page (markup and site navigation removed). Covers the licence body from the title to the "Versioning" paragraph (OGL-Canada version 2.0). |

## Publication-derived information (no coordinates taken from it)

No coordinates come from a publication: all of them are per-sample values in the provider tables above. A publication supplies only the **uncertainty** for the 2022 Fundy positions:

- Teed LL, Goodwin C, Lawton P, Lacoursière-Roussel A, Dinning KM (2024) *BioInvasions Records* 13(3): 713-738, https://doi.org/10.3391/bir.2024.13.3.12 (CC BY 4.0), Methods, p. 722:
  "For the September 2022 survey, an underwater acoustic positioning system was not available, and so geographic positions were recorded from a Hemisphere R330 GNSS receiver with an A45 antenna at the surface. From prior use of similar near-seafloor camera systems within the EBSA on the CCGS Viola M. Davidson, it can be expected that spatial offsets from the survey vessel could range up to 40 m astern to 5-10 m port or starboard, depending on depth and tidal factors (Lawton pers. obs.)."
  From this, `geo_uncertainty_m = 50` for Fundy stills and video segments. Accordingly, `publication_sites.csv` is not needed and was not created.
