# Fixture sources: `moorea_lter`

All files retrieved 2026-10-06 with User-Agent `aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`.
Note: since 2026-07-30 EDI (pasta.lternet.edu, portal.edirepository.org) requires authentication for
every REST call (anonymous calls return HTTP 403 "Public Access ... not authorized"). The files below were
therefore read through the DataONE federation (cn.dataone.org / gmn.lternet.edu, the LTER member node run
by EDI), which serves byte-identical copies of the PASTA objects anonymously.

| File | Exact URL | Trimming |
|---|---|---|
| `knb-lter-mcr.5006.3_eml.xml` | https://cn.dataone.org/cn/v2/object/https%3A%2F%2Fpasta.lternet.edu%2Fpackage%2Fmetadata%2Feml%2Fknb-lter-mcr%2F5006%2F3 | None. Complete EML 2.1.1 record of "MCR LTER: Coral Reef: Computer Vision: Moorea Labeled Corals" rev 3 (57,833 bytes). Contains `intellectualRights` (CC BY 4.0), the six `LTER N polygon` gRings used in `publication_sites.csv`, and the four entities (3 image zips + 1 example annotation). |
| `mcr_lter6_out17m_pole5-6_qu3_20090331.jpg.txt` | https://gmn.lternet.edu/mn/v2/object/https:%2F%2Fpasta.lternet.edu%2Fpackage%2Fdata%2Feml%2Fknb-lter-mcr%2F5006%2F3%2F26d10e4bc0512211a42f488597bea558 (DataONE-Proxy header: https://pasta.lternet.edu/package/data/eml/knb-lter-mcr/5006/3/26d10e4bc0512211a42f488597bea558) | None. Entity "Image_annotation" (3,067 bytes). MD5 `8373c8d16419ec80d7614d3869e7843e` = the MD5 in the EML `physical/authentication`, so the bytes are unmodified. The file name comes from the HTTP `Content-Disposition` header and the EML `objectName`. It is the per-image annotation file (`# Row; Col; Label`, 200 points) that sits next to every image in the year zips; the file name is the record that `resolve_geo()` parses. |
| `dataone_solr_5006_3.json` | https://cn.dataone.org/cn/v2/query/solr/?q=isDocumentedBy:%22https://pasta.lternet.edu/package/metadata/eml/knb-lter-mcr/5006/3%22&fl=id,formatId,size,checksum,checksumAlgorithm,fileName,dateUploaded,isDocumentedBy,resourceMap&rows=20&wt=json | None. Complete response, numFound = 5: the 3 image zips with byte sizes and SHA-1, the example annotation and the PASTA quality report. |
| `bcodmo_918265_site_locations.csv` | https://datadocs.bco-dmo.org/dataset/918265/file/p9VrEDmCOQ107o/site_locations.csv (linked from https://www.bco-dmo.org/dataset/918265, DOI 10.26008/1912/bco-dmo.918265.1, licence CC-BY-4.0) | None (215 bytes). Fore-reef 10 m site coordinates for LTER0, LTER1 and LTER2 from Edmunds et al. 2024 (doi:10.1007/s00442-024-05517-y). The LTER0 row (-17.388) lies about 9 km offshore, outside every EML polygon, so it looks like a typo. It is not used (MLC has no LTER0 images). |
| `knb-lter-mcr.4.43_long_excerpt.csv` | https://gmn.lternet.edu/mn/v2/object/https:%2F%2Fpasta.lternet.edu%2Fpackage%2Fdata%2Feml%2Fknb-lter-mcr%2F4%2F43%2F14be40162808dfdf6e235534b1b1937b (entity "Percent Cover - Long Table", `knb-lter-mcr.4_1_20260106.csv`, 41,174,843 bytes) | Only the first ~600 KB were streamed (the server ignores Range, so the stream was cut client-side). Kept: the header plus the first row of each of the 18 site x habitat transects in 2005 (dropped rows only; no value edited). Source of `depth_m` (column `Depth`) per transect. |
| `publication_sites.csv` | derived, see below | Not a provider file. |

## `publication_sites.csv` derivation

Columns: `site_id, site_name, lat, lon, depth_m, uncertainty_m, source`. `site_id` = `LTER{n}_{habitat}`,
where habitat is the token used in MLC image filenames (`fringingreef`, `out10m`, `out17m`).

1. **Polygon rows** (all fringing-reef rows, plus outer 10 m / 17 m at LTER 3 to 6). Source: the gRing polygons in
   `knb-lter-mcr.5006.3_eml.xml`, `dataset/coverage/geographicCoverage`, quoted descriptions:
   "LTER 1 polygon including LTER 0 on north shore", "LTER 2 polygon on north shore",
   "LTER 3 polygon on southeast shore", "LTER 4 polygon on southeast shore",
   "LTER 5 polygon on southwest shore", "LTER 6 polygon on southwest shore" (gRing = `lon,lat` pairs, WGS 84).
   lat/lon = planar (shoelace) centroid of the gRing. uncertainty_m = largest haversine distance from the centroid
   to any polygon vertex, rounded up to 50 m (1092->1100, 1122->1150, 1223->1250, 1180->1200, 1641->1650, 1495->1500).
   Every transect of that site lies inside the polygon, so the radius covers it. The EML gives no
   per-habitat point.
2. **LTER1/LTER2 outer reef rows**: `bcodmo_918265_site_locations.csv` rows
   `Moorea,LTER1,-17.475,-149.837,17 28.5 S,149 50.2 W` and `Moorea,LTER2,-17.472,-149.808,17 28.3 S,149 48.5 W`.
   The BCO-DMO page says: "Coral cover was measured annually ... at 10-m depth along a 50 m, permanently marked
   transect at LTER 1 and LTER 2". Both points fall inside the matching EML polygon (checked).
   Uncertainty: 200 m for out10m (3-decimal rounding of ~110 m plus the 50 m transect). For out17m the same point is
   used with 500 m, because the 17 m transect lies seaward of the 10 m one at an unpublished distance (our estimate).
3. **depth_m**: from column `Depth` of the knb-lter-mcr.4.43 long table (see the excerpt). Forereef = 10 or 17;
   Fringing: LTER_1 = 6, LTER_2 = 4, LTER_3 = 7, LTER_4 = 6, LTER_5 = 3, LTER_6 = 4. Checked for 2005 and 2006 only.
   The transects are permanent (fixed since 2005), so we assume the same depths for 2008 to 2010.
   For comparison, knb-lter-mcr.5013.3 methods say "fringing reef at 2-5 m depth".
