## HANDOFF
- status: blocked
- tier + licence: B, CC BY 4.0 at record level (https://zenodo.org/api/records/16085852, field `license.id`=cc-by-4.0). No file-level licence (no files reachable).
- geo: image precision; intended geo_source = EXIF GPS of the 4694 frames in geotagged_continuous.zip (authors wrote positions to EXIF). Not verified: no file accessible.
- files: adapter none (no media list to discover); script scripts/download/wendtorf_bottsand.sh (prints blocker, exit 1); test tests/test_wendtorf_bottsand.py; fixtures tests/fixtures/wendtorf_bottsand/ (SOURCE.md); sites csv none.
- tests: pass (2 offline tests on the Zenodo metadata fixtures).
- sample: 0 files; `aquasource download wendtorf_bottsand --budget 3` fails with KeyError "no adapter" (no adapter written, nothing to download anonymously).
- doubts:
  - access_right=restricted: files need owner approval (Zenodo request access). Anonymous /files returns 403. Do not bypass.
  - Once accessible: verify EXIF GPS is present in the JPEGs in geotagged_continuous.zip and that it matches Humminbird/Ardu logs.
  - Frames are GoPro Hero9 video frames at 1 s from a USV: flag surface/air frames with extra.maybe_not_underwater=true.
  - Single survey (27 Aug 2024, Bottsand Strand, approx 54.43N 10.29E) in shallow Baltic water: check region weighting.
  - Drone orthomosaics and sonar are out of scope for images; only the GoPro frames are media.
- retry 2026-10-08 (Sonnet): searched Zenodo (query Wendtorf Bottsand; concept record 16085851 has no other open version) and no PANGAEA/other copy found. Still blocked.
- human action: ask the record owner (Carlson, Zenodo 16085852) to open the files or share geotagged_continuous.zip with a licence statement; then write the adapter.
- needs_opus: no. Not solvable by a stronger model; needs the owner to grant access.

# Wendtorf / Bottsand GoPro frames (`wendtorf_bottsand`)
Status: blocked · researched 2026-10-08

## Summary
Zenodo record 16085852 (Carlson, 2025): drone orthomosaic, side-scan sonar, and "geotagged_continuous.zip" with 4694 underwater GoPro Hero9 frames (1 s interval, positions written to EXIF). The record is public and CC BY 4.0, but its files are restricted. Anonymous access to the file list returns 403. The only usable media is the GoPro frames, so the dataset is blocked until access is granted.

## Entry points
- Record API (metadata): https://zenodo.org/api/records/16085852
- Files API (anonymous): https://zenodo.org/api/records/16085852/files, HTTP 403 "Permission denied"
- Landing page: https://zenodo.org/records/16085852 (DOI 10.5281/zenodo.16085852)
- Versions: single version (https://zenodo.org/api/records/16085852/versions)

## Licence
- Record level: `license.id` = `cc-by-4.0` (API and landing page), read 2026-10-08. Tier **B**.
- File level: none readable.
- Access: `access_right` = `restricted`; landing page: "The record is publicly accessible, but files are restricted. Log in to check if you have access."
- Access is a separate blocker. The licence is not in doubt.

## Geo
- Intended: `geo_precision=image`, `geo_source` = EXIF GPS in the frames of geotagged_continuous.zip. `geo_inferred=false` if EXIF is present.
- Not verified: no image is accessible. The description says positions were aligned from navigation data (Wendtorf_Ardu_Log.csv, restricted too).
- Site: Bottsand Strand, near Wendtorf, 54.43N 10.29E, from the description. Only used as a sanity check, not as coordinates.

## Next steps (owner or human)
1. Request access on the Zenodo record (owner approval), or a contact to get the frames.
2. Then write adapter `wendtorf_bottsand.py` (zip member discovery, EXIF GPS read, 1 request/s), replace the script with the standard template, and add the sample test.

## Fixtures
tests/fixtures/wendtorf_bottsand/: zenodo_16085852_record.json, zenodo_16085852_files_anon.json, SOURCE.md.
