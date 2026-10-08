## HANDOFF
- status: ok
- tier + licence: B, CC BY 4.0, record level (Mendeley public API `data_licence`, https://data.mendeley.com/public-api/datasets/wsd42v8mk5?version=1; landing https://data.mendeley.com/datasets/wsd42v8mk5/1)
- geo: station (4 stations, publication coordinates); geo_source = description text in sites/baltic_scan.csv; geo_inferred true
- files: src/aquasource/adapters/baltic_scan.py / scripts/download/baltic_scan.sh / tests/test_baltic_scan.py / src/aquasource/adapters/sites/baltic_scan.csv (+ tests/fixtures/baltic_scan/)
- tests: pass (11 passed, offline)
- sample: 3 of 3 JPEG mosaics downloaded OK (budget 3; SOI/EOI markers, sha256 in samples.jsonl); 1 AVI video (SM08_1.avi, 254 MB) OK, size equals the central directory, RIFF/AVI header; sample dir removed
- doubts:
  - Station coordinates are publication-derived (one point per station, not per frame); DE01 is the ROV station, SM02/SM07/SM08 are SCUBA transects, so all frames of a transect share one point.
  - Frames and Mosaics folders are RAR archives (annotation masks). Not read; not in the candidate set.
  - Timestamps are not published; timestamp is null for all items.
  - Videos are 254 to 493 MB each, deflated AVI at 50 fps: large, use `kinds=` or a budget.
  - Signed S3 URL is resolved per fetch from the public API (302); if Mendeley changes the redirect, `signed_url()` must change.
- needs_opus: no

---

# baltic_scan: SE Baltic reef ROV and SCUBA video (Mendeley wsd42v8mk5)

Scope: the seed asked for open Baltic and Nordic underwater imagery with positions. Only one candidate was adapted in this pass: Mendeley Data 10.17632/wsd42v8mk5.1 (Klaipeda University, 2022). The other leads from the search were not checked in detail (see below).

## Record
- Title: "A fully-annotated imagery dataset of sublittoral benthic species in South Eastern Baltic Sea reefs". Published 2022-06-21, version 1.
- Data: 2 ROV videos (DE01_1, DE01_2, offshore, Full HD), 5 SCUBA GoPro transects (SM02_1, SM02_2, SM07_1, SM07_2, SM08_1; SM08 was split, SM08_2 is the second mosaic).
- Archive: one zip, 3,409,429,991 bytes, 19 entries. Raw data (15 entries): 7 AVI (254 to 493 MB, deflated) and 8 JPEG 2D video mosaics (0.19 to 7.9 MB). Frames/ and Mosaics/ folders: 4 RAR files (annotation sets), not read.
- Licence: CC BY 4.0 (`data_licence` field of the public API record). No file-level licence.
- Geo: the description gives "Geographical information (Y, X in WGS coordinate system)": DE01 (55.39904, 20.62784), SM02 (55.90750, 21.04090), SM07 (55.92220, 21.03720), SM08 (55.92360, 21.04100). No depth, no timestamps.

## Access and method
- Metadata: `https://data.mendeley.com/public-api/datasets/wsd42v8mk5?version=1` (the file-list endpoints return an empty list for this record).
- Media: `https://data.mendeley.com/public-api/zip/wsd42v8mk5/download/1` answers 302 to a signed S3 URL (valid for a short time). The adapter resolves it per run and per fetch.
- Central directory: read with two Range requests (tail, then the directory, 3.2 KB). Cached in metadata/raw/baltic_scan/wsd42v8mk5_entries.json.
- Each member is read with one Range request for the local header, then streamed (1 MB chunks), inflated, checked against the size and sha256.
- The HEAD request on the signed URL returns 403; size comes from Content-Range on a 1-byte GET.

## Commands
- Sample: `AQUASOURCE_DATA_ROOT=/tmp/aquasource_scratch/sample_baltic_scan uv run aquasource download baltic_scan --budget 3`
- Video only: add `--opt kinds=video`
- Tests: `uv run pytest tests/test_baltic_scan.py -q`

## Other leads (not adapted)
- IOW Warnemuende "geo-referenced database of underwater images" (http://uwfotos.io-warnemuende.de, linked from https://www.iow.de/media-center-others.html): licence and download terms not stated on the page. Not checked further.
- EMODnet record for coastal bank habitats, Latvia-Lithuania border, underwater video observation (2016): licence ODC-ODbL, which is not in the tier list (would be U). Not adapted.
- Not in the Baltic: PANGAEA Helgoland sea-bottom video (North Sea); OBSEA (Mediterranean).
- Seed countries (Finland VELMU, Sweden, Denmark, Poland, Estonia, Latvia, Lithuania) were not searched in this pass.
