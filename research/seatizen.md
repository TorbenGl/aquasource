## HANDOFF
- status: ok
- tier + licence: B. Per session deposit, Zenodo record `license.id` = cc-by-4.0, access open (e.g. https://zenodo.org/api/records/13170795). Index deposit https://zenodo.org/records/18211765 is cc-by-4.0 at collection level only and is not used for samples. CC-BY-NC/ND, restricted or unknown sessions are not yielded.
- geo: precision image; geo_source = session METADATA.zip > metadata.csv GPSLatitude/GPSLongitude (camera EXIF, WGS-84). ASV sessions: PPK-corrected per frame, geo_uncertainty_m = sqrt(GPSsde^2+GPSsdn^2). No depth. No publication-derived coordinates, no sites csv.
- files: src/aquasource/adapters/seatizen.py; scripts/download/seatizen.sh; tests/test_seatizen.py; tests/fixtures/seatizen/ (SOURCE.md); no sites csv.
- tests: pass (26/26, `uv run pytest tests/test_seatizen.py -q`).
- sample: 3 JPEGs + metadata/samples.jsonl OK (re-run 2026-10-08, --budget 3, 47 s); earlier run logged 3 skipped (ambiguous basenames in zip). Census 589/589 cc-by-4.0 open.
- doubts:
  - Underwater GPS: EXIF fixes of scuba (GoPro HERO3+) and SURF/ASV frames may be surface or last-fix positions; check the fix against the track (GPS.zip) before trusting `image` precision.
  - ASV (294 of 589 sessions, the bulk) use PROCESSED_DATA_FRAMES.zip; the ASV path is tested offline only, not in the sample. Check that GPSsde/GPSsdn are metres (values ~0.004 suggest so).
  - Platform: aerial (UAV, KITE) images are kept and marked extra.maybe_not_underwater=true; unknown platforms (SURF, PADDLE) are not flagged. Decide whether to keep aerial images in the pretraining set.
  - Coverage: sessions with neither DCIM.zip nor PROCESSED_DATA_FRAMES.zip (about 15) and sessions whose images are not uniquely named in the zip are skipped and logged in failures.jsonl.
  - Redundancy: video-derived frames (ASV, scuba) are dense; use max_per_session before a full run.
- needs_opus: no (licence is clear per record, geo is EXIF, no publication-derived coordinates).

## Source and access
- Index: https://zenodo.org/records/18211765 ("Seatizen Atlas", Contini et al. 2025, Sci. Data, https://doi.org/10.1038/s41597-024-04267-z). `session_doi.csv` lists 589 session deposits (place, date).
- Each session is its own Zenodo record (DOI zenodo.<id>; older ids redirect to newer records; the adapter stores the resolved id). Files: METADATA.zip (EXIF metadata.csv, can be large, up to 1.2 GB with thumbnails), DCIM.zip (GoPro scuba and UAV/KITE stills, 0.3-16 GB), PROCESSED_DATA_FRAMES.zip (ASV frames, 1080p JPEG), GPS.zip, SENSORS.zip, PROCESSED_DATA_BATHY.zip, PROCESSED_DATA_IA.zip, previews.
- Anonymous, no token. Zenodo answers HTTP Range requests (206), which the adapter uses for zip members.
- The Nature article returned a 303 to a gateway page for this environment; the licence and geo were taken from Zenodo.

## Licence
- Census of session records (all 589 sessions via `GET /api/records/<id>`, 1 req/s): all 589/589 are cc-by-4.0, access open (no NC/ND/other); per-session licence still read at runtime.
- Index deposit: cc-by-4.0. Sessions: read per record; tier from classify() (cc-by-4.0 -> B, cc-zero -> A, NC/ND -> X).

## Geo
- metadata.csv columns: FileName, GPSLatitude, GPSLongitude, GPSMapDatum (WGS-84 in all rows checked), GPSDateTime, CreateDate, Make, Model; ASV adds GPSfix, GPSsde, GPSsdn, SubSecDateTimeOriginal.
- GPSAltitude is not used as depth (ASV: "Below Sea Level", small values; scuba: positive altitudes).
- Rows with empty or 0,0 coordinates are dropped unless geo_only=false (then precision none).

## Structure / census of session types (589 sessions)
- Session platforms (589): ASV 294, UAV 85, KITE 69, UVC 68, SCUBA 46, AUV 14, PADDLE 8, SURF 3, BOAT 1, HIKE 1 (UAV/KITE/PADDLE/SURF/HIKE images are mostly aerial/surface, flagged maybe_not_underwater).

## Adapter behaviour
- discover: session index -> session record (licence, access, files) -> METADATA.zip/metadata.csv (range read) -> rows. Sessions visited in seeded shuffle (order=spread) so budget samples spread across sessions.
- resolve_media: central directory of DCIM.zip or PROCESSED_DATA_FRAMES.zip read via range requests (cached in metadata/raw/zipindex/). Member matched by FileName (exact, else unique basename tail after the session prefix).
- fetch_media: one local header and one compressed member by range requests; zlib inflate; CRC32 and size checked; JPEG magic checked.
- Options: tiers (A,B), order (spread|table), seed, max_per_session (0 = all), geo_only (true), platforms.

## Sample run (budget 3, AQUASOURCE_DATA_ROOT=/tmp/aquasource_scratch/sample_seatizen, removed afterwards)
- 3 JPEG files downloaded OK from session 20181209_MUS-Ilot-Sancho_SURF-01_01 (Mauritius), geo image precision, licence B; 3 failures (duplicate basenames in the zip).
- Session METADATA.zip of that session is 1.2 GB: only metadata.csv was read (28 MB compressed).

## Not done
- GPS.zip / SENSORS.zip interpolation (sessions without EXIF GPS are skipped).
- Pixel filters (above-water, black, deck frames).
- Full run and dedup of frames (video-derived; use max_per_session).
