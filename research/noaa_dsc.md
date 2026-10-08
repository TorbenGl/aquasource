## HANDOFF
- status: ok (NOAA-only images tier A downloadable; co-provider images tier U, not downloaded by default)
- checked by Sonnet 2026-10-08: tests (11) and 3-image sample pass; geo/licence code reviewed, no changes; tier A (NOAA-only) / U (co-provider) confirmed.
- tier + licence: A for images whose DataProvider is NOAA alone (about 110 k images); U for NOAA co-provider images (about 24 k). Licence read at collection level: ISO accessLevel public, no licence stated, https://www.ncei.noaa.gov/archive/accession/0145037 ; ERDDAP licence text https://www.ncei.noaa.gov/erddap/info/deep_sea_corals/index.json
- geo: precision image; geo_source "ERDDAP deep_sea_corals latitude,longitude,DepthInMeters (record CatalogNumber)"
- files: src/aquasource/adapters/noaa_dsc.py / scripts/download/noaa_dsc.sh / tests/test_noaa_dsc.py / sites csv: none (per-record coordinates)
- tests: pass (11 offline, `uv run --extra dev pytest tests/test_noaa_dsc.py -q`; plain `uv run pytest` fails because pytest is not in the default env)
- sample: 3 of 3 images downloaded OK (3.3 MB, 2.9 MB, 2.7 MB JPEG, tier A, geo image, 95 s incl. one ERDDAP query); scratch removed
- doubts:
  - Tier A for NOAA-only images is a US-government-work reading of records with no stated licence (same as noaa_oe); the seed also says "NOAA public domain". The ERDDAP text says "may be used and redistributed for free" with a no-warranty disclaimer.
  - Co-provider images (NOAA | University of Hawaii, UConn, ...) are tier U: partner copyright possible; excluded by default.
  - geo precision "image" comes from the record's own latitude/longitude; for survey or transect records it may be a station position. Check a few records.
  - Several records share one image URL: first CatalogNumber's coordinates are used; extra.geo_conflict flags disagreements.
  - Seed host deepseacoraldata.noaa.gov is the portal front end; the data endpoint is the NCEI ERDDAP (seed corrected). The ISO citation shows version 20250903-0 while the abstract says 20260416-1.
- needs_opus: no (the tier-A reading follows the noaa_oe precedent; a checker should confirm the doubt above, not an Opus pass)

---

# NOAA National Deep-Sea Coral and Sponge Database (noaa_dsc)

Checked 2026-10-08. Metadata only during research; the sample run downloaded 3 images.

## Source and access
- Dataset: NCEI accession 0145037, "Observations of Deep-Sea Coral and Sponge Occurrences ... 1842-Present", DOI https://doi.org/10.25921/t8c0-yx22 (ISO citation version 20250903-0; abstract says 20260416-1 with 1,484,516 records). Landing https://www.ncei.noaa.gov/archive/accession/0145037 ; ISO https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.nodc:0145037
- Data: ERDDAP table https://www.ncei.noaa.gov/erddap/tabledap/deep_sea_corals (info: .../info/deep_sea_corals/index.json, 109 variables). Portal front end https://deepseacoraldata.noaa.gov/data (links the ERDDAP and a CSV dump).
- Anonymous HTTPS, no token. The ERDDAP query for NOAA image records is one request of several minutes (cached in metadata/raw/erddap_noaa_images.csv).
- Images: ImageURL on https://www.ncei.noaa.gov/waf/dsc-data/images/<nnnnnn>/<CatalogNumber>.jpg|JPG (mostly), a few on data.nodc.noaa.gov, dsg.mbari.org, ftp.library.noaa.gov, Yale. JPEG only (magic FF D8 FF checked).

## Licence (read at collection level)
- ISO "Use Limitations": accessLevel public; "Distribution liability" and "Use liability" disclaimers; no licence name, no CC/PD statement.
- ERDDAP global attribute `license`: data "may be used and redistributed for free but is not intended for legal use", no-warranty text. No per-record licence field exists (no licence column among the 109 variables).
- NOAA federal work with no licence stated: tier A for NOAA-only providers (noaa_oe precedent). Co-provider records (DataProvider "NOAA, ... | <partner>"): tier U.
- Non-NOAA providers (MBARI about 7.9 k images, Harbor Branch, Nova Southeastern, Hawaii, Smithsonian, Penn State, ...): not queried; their licences were not checked.

## Geolocation
- Per record: latitude, longitude (degrees, WGS84 per the ERDDAP units), DepthInMeters (m, positive; -999 = missing), ObservationDate. ShallowFlag marks depths under 50 m.
- Adapter: precision image, geo_inferred false, geo_source as in the HANDOFF. Records whose latitude or longitude is missing are dropped. No site table: coordinates are the dataset's own record values.

## Size (distinct check 2026-10-08, ERDDAP DataProvider/ImageURL/DatasetID combos)
- NOAA-prefixed image records: about 134 k distinct image URLs (about 110 k NOAA-only tier A; about 24 k co-provider tier U). Non-NOAA image records: about 31 k (not queried).
- About 3 MB per JPEG in the sample (range 40 KB to 3.3 MB). At that average, all 134 k images are about 400 GB (tier A about 330 GB); use --budget.

## Sample (3 images, tier A)
- 285928.JPG, 285929.JPG, 285930.JPG (NOAA, Greater Farallones National Marine Sanctuary, dataset NOAA_FM-12-10, 37.881 N, 123.334 W, depths 86-96 m); samples.jsonl rows carry lat, lon, depth_m, licence_tier A, geo_precision image.

## Implementation notes
- Adapter yields one candidate per ImageURL (record CatalogNumbers in extra.catalog_numbers, extra.dataset_ids, extra.scientific_names capped at 20). Tier is decided from the first record's DataProvider; the runner's tier filter selects A (and B if configured) only.
- Attribution: the DSCRTP citation with the DOI, the record CatalogNumber(s) and the provider.
- Offline tests use tests/fixtures/noaa_dsc/erddap_records.csv (provenance in SOURCE.md).

## Changes needed in shared code (not made)
- None found. Base Adapter has no `_skip`; the adapter keeps its own counter, as noaa_oe does.
