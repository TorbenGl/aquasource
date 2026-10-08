## HANDOFF
- status: ok
- tier + licence: B, CC BY 4.0 (record level: table header "License: Creative Commons Attribution 4.0 International (CC-BY-4.0) (URI: https://creativecommons.org/licenses/by/4.0/)" at https://doi.pangaea.de/10.1594/PANGAEA.980001?format=textfile; same in metadata_jsonld)
- geo: fixed_site, geo_source "PANGAEA.980001 Coverage LATITUDE/LONGITUDE" (54.340625 N, 10.174105 E, observatory position for all sequences; geo_inferred true; depth null)
- files: adapter src/aquasource/adapters/hodor.py / script scripts/download/hodor.sh / test tests/test_hodor.py / fixtures tests/fixtures/hodor/ / sites csv: none (coordinates parsed from the PANGAEA Coverage line)
- tests: pass (uv run pytest tests/test_hodor.py -q, 6 tests)
- sample: 3 files downloaded OK (cam1 seq 0-2, mp4 ftyp, 2.6-11 MB each, samples.jsonl 3 rows); scratch dir removed
- doubts:
  - Full archive: PANGAEA.980001 holds only the 86-day subset (5850 sequences, 2021-08-22 to 2021-11-16); the README mentions about 430 h of sequences. The longer archive is not on PANGAEA and was not found.
  - Geo is one publication point applied to every sequence; no uncertainty is stated (geo_uncertainty_m null).
  - Depth is null. Abiotic CTD/ADCP data (PANGAEA.973019) may give depth per sequence (not checked).
  - Timestamps: Date/time start is stored as UTC ("Z"); verified only for SeqID 0 against sequenceStartUnix.
  - GitHub repo TAWilts/HODOR has no licence (API license null). Only the PANGAEA CC BY 4.0 licence was used.
- needs_opus: no

## Summary
HODOR (Hydroacoustic and Optical Dataset for Oceanic Research), PANGAEA.980001 "camera data". Stereo camera videos from the Kiel Fjord underwater fish observatory (UFO), Baltic Sea, collected 2021-08-22 to 2021-11-16. The dataset holds 5850 activity-selected sequences; each row lists cam1 and cam2 MP4 files (served without login from `download.pangaea.de/dataset/980001/files/`) plus per-sequence timestamp TXT files. Sequences were selected for fish activity, so they are not noise-filtered for "no fish" frames. Verdict: go, CC BY 4.0 (tier B), fixed-site geo. Default adapter option is cam1 only; cam2 is available with `cams=cam1,cam2`.

## Entry points
- Dataset: https://doi.org/10.1594/PANGAEA.980001 (bundled in PANGAEA.980000)
- Data table: https://doi.pangaea.de/10.1594/PANGAEA.980001?format=textfile (5850 rows, 14 columns: SeqID, sequence start/end in Unix and ISO, `Binary (cam1FilePath)` and friends)
- Media: https://download.pangaea.de/dataset/980001/files/cam1_NNNN.mp4 (HEAD 200, video/mp4, no login). Bulk ZIP/TAR need PANGAEA registration and are not used.
- Companion: sonar is PANGAEA.980002; abiotic data PANGAEA.973019; code and README https://github.com/TAWilts/HODOR (hodor-python package).

## Licence
- CC BY 4.0, read at record level from the table header and the JSON-LD `license` (https://creativecommons.org/licenses/by/4.0/). Attribution = PANGAEA citation (stored per sample in `attribution`).
- No file-level licence. The GitHub repo has no licence file; it is code, not the data.

## Geolocation
- Coverage and Event lines give LATITUDE 54.340625, LONGITUDE 10.174105 (WGS84), with the observatory as the event (METHOD/DEVICE: underwater fish observatory). Every sequence carries this position, so `geo_precision` is `fixed_site`, `geo_inferred` is true, and `depth_m` is null.
- Coordinates come from the dataset publication, not hardcoded. The adapter parses them from the cached table metadata.

## Access and size
- Metadata: one table, about 1 MB, one request. Media: about 2.6 MB to 12 MB per cam1 MP4. Both cameras together are about 144 GB including TXT files, so cam1 alone is about 72 GB. Use `--budget` for samples.
- Throttling: 1 request/s per host (doi.pangaea.de, download.pangaea.de).

## Adapter options
- `cams=cam1` (default), `cams=cam1,cam2`
- `from=YYYY-MM-DD`, `to=YYYY-MM-DD` (inclusive, on sequence start day)
- `per_day=N` (at most N sequences per day)

## Verification
- Sample run: 3 videos downloaded and recorded in samples.jsonl with tier B, fixed_site, lat/lon set, depth null. Scratch sample removed.
- Timestamp check: `sequenceStartUnix` 1629609208 equals 2021-08-22T05:13:28 UTC, the stored value.
- Fixture: first three data rows and the header of the PANGAEA table, see tests/fixtures/hodor/SOURCE.md.
