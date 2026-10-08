## HANDOFF
- status: ok
- tier + licence: B, "Creative Commons Attribution 4.0 International Licence", record level. Read at https://data.csiro.au/dap/ws/v2/collections/csiro:74006 (licence field) and https://data.csiro.au/dap/ws/v2/licences/1121; the same CC BY 4.0 appears in the RDA record https://researchdata.edu.au/rv-investigator-voyage-imagery-data/3970151 and the ISO 19115-3 record.
- geo: image precision; geo_source "STILLS.CSV Latitude/Longitude/Depth" (per still, Key = still file name); geo_inferred=false.
- files: src/aquasource/adapters/csiro_mnf.py / scripts/download/csiro_mnf.sh / tests/test_csiro_mnf.py / no sites csv (positions are per image) / fixtures in tests/fixtures/csiro_mnf/ (SOURCE.md)
- tests: pass (9/9, offline; uv run pytest tests/test_csiro_mnf.py -q)
- sample: 3 of 3 stills downloaded OK (13-16 MB each, 43.9 MB total); samples.jsonl rows carry lat/lon, depth_m, geo_precision=image, tier B. Sample dir removed.
- doubts:
  - The DAP `rights` field says "All Rights (including copyright) CSIRO 2026." while the licence field, RDA and ISO record say CC BY 4.0. Tier B is kept; check the attribution text and the licence field.
  - The listing is cached as metadata/raw/listing.json, about 1.36 GB, and is read whole into memory. Parsing should be streamed before a full run.
  - Only stills are harvested. Videos (oblique forward view) and the 1 s video navigation CSV are not used. Stills without Latitude/Longitude in STILLS.CSV are dropped.
  - Depth is the STILLS.CSV Depth column (positive m); Alt is altitude above the seabed and is not stored.
  - DAP JSON reports accessViewable=false for the collection. Downloads worked anonymously in the sample, so this flag was not used as a gate.
- checked by Sonnet 2026-10-08: licence URL re-read (DAP licence 1121 = CC BY 4.0); `rights` is CSIRO's copyright-holder statement, compatible with CC BY; tier B confirmed. Tests 9/9, sample 3 stills + samples.jsonl OK. resolve_geo/licence reviewed, no errors.
- needs_opus: no (was yes), because the `rights` field ("All Rights (including copyright)") contradicts the explicit CC BY 4.0 licence. The explicit licence was applied (tier B), but a licence-owner check is needed before a full harvest.

---

# csiro_mnf: CSIRO MNF RV Investigator voyage IN2023_V05 stills

Last run: 2026-10-08 (lean pass, Haiku).

## Source
- DAP image collection csiro:74006 "Image Collection - RV Investigator Voyage IN2023_V05 - SEA-MES ... Voyage 1", DOI 10.25919/gddy-hn24, published 2026-06-15, v1.
- Voyage 28 Jun to 30 Jul 2023, SE Australia (36 to 43 S, 147 to 150 E), MNF Deep Towed Camera (DTC).
- Access: anonymous (dataRestricted FALSE). Listing: GET https://data.csiro.au/dap/ws/v2/collections/74006/data (about 1.36 GB, one response; `max` and `pageSize` are ignored). Per file: https://data.csiro.au/dap/ws/v2/collections/74006/data/<id>, which redirects to a presigned S3 link valid for 2 days (never stored).
- Size: 346,715 images, 346,977 files, 3.78 TB (video included). Stills are 13-16 MB each.

## Licence
- Collection: CC BY 4.0 (DAP licence 1121). Tier B, record level.
- DAP `rights`: "All Rights (including copyright) CSIRO 2026." (conflicts; see HANDOFF doubts).
- Attribution stored with each sample: DOI citation, CC BY 4.0 URL, MNF acknowledgement "We acknowledge the use of the CSIRO Marine National Facility (https://ror.org/01mae9353) in undertaking this research."

## Geo
- Per still, from the deployment's `DTC_<dep>_STILLS.CSV` (columns Date, Key, Alt, Latitude, Longitude, Depth, ...). Key is the still file name. Latitude/Longitude/Depth are used: geo_precision=image, geo_source="STILLS.CSV Latitude/Longitude/Depth", geo_inferred=false.
- Rows without Latitude/Longitude are not yielded. Alt (altitude) is not used as depth.
- The collection lineage says GIS location and depth were also written to still EXIF; the CSV is the source used (no media was read for geo).

## Adapter (src/aquasource/adapters/csiro_mnf.py)
- discover(): one listing fetch (cached in metadata/raw/listing.json), regex over file records; per deployment, the STILLS.CSV is cached in metadata/raw/stills/<dep>.csv; one candidate per coordinate row whose Key matches an image record. Options: deployments (list), max_rows (per deployment).
- Media: /data/<id> link (redirect followed by Http.download). Videos not harvested.

## Tests and sample
- tests/test_csiro_mnf.py: 9 offline tests on tests/fixtures/csiro_mnf/ (real listing head, real collection record subset, real STILLS.CSV head; synthetic still records for keys with coordinates).
- Sample: `AQUASOURCE_DATA_ROOT=/tmp/aquasource_scratch/sample_csiro_mnf uv run aquasource download csiro_mnf --budget 3`: 3 files, 549 s (mostly the listing), no errors.

## Open items for a full run
- Stream the 1.36 GB listing instead of caching it as text.
- Decide whether to add the 1 s video navigation and the videos.
- Confirm the rights statement with CSIRO (data-requests-hf@csiro.au) if the tier matters.
