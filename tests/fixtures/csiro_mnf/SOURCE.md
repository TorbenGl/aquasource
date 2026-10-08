# csiro_mnf fixtures (fetched 2026-10-08, metadata only)

- `dap_collection_74006.json`: subset of the DAP v2 collection record
  https://data.csiro.au/dap/ws/v2/collections/csiro:74006 (landing page https://data.csiro.au/collection/csiro:74006,
  DOI https://doi.org/10.25919/gddy-hn24). Keys trimmed; description and relatedLinks omitted.
- `listing_head.json`: first 3 records of the complete file listing
  https://data.csiro.au/dap/ws/v2/collections/74006/data (about 1.36 GB; `max`/`pageSize` are ignored by the server).
  `presignedLink` values expire after 2 days.
- `DTC_IN2023_V05_005_STILLS_head.csv`: first 40 lines of `IN2023_V05/data/DTC/IN2023_V05_005/data/DTC_IN2023_V05_005_STILLS.CSV`
  (DAP file id 99348533, https://data.csiro.au/dap/ws/v2/collections/74006/data/99348533).
- Other reads (not stored): RDA record https://researchdata.edu.au/rv-investigator-voyage-imagery-data/3970151,
  GeoNetwork ISO 19115-3 https://marlin.csiro.au/geonetwork/srv/api/records/ce9b09e2-30b1-42f5-9b6f-10be8bbedff5/formatters/xml,
  licence 1121 https://data.csiro.au/dap/ws/v2/licences/1121. The DOI 10.25919/8c9t-x889 (publications.csiro.au) answers
  HTTP 403 from Cloudflare here and is not needed.
