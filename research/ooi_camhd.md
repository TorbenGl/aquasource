## HANDOFF
- status: ok (retry 2026-10-08)
- tier + licence: B, collection level. OOI Data Use Policy v2-00 s4.1 (read from a web.archive.org copy of the PDF; live site 403): data public, free, user may use for any legal purpose incl. derivative works/publish/distribute. No NC/ND, but no named licence (not CC), so B (not A).
- geo: fixed_site, geo_inferred false; lat 45.93364, lon -130.01364, depth 1543 m, uncertainty 30 m (assumed) from OOI asset-management deployment table (github oceanobservatories/asset-management deployment/RS03ASHS_Deploy.csv, RS03ASHS-PN03B-06-CAMHDA301). Replaces the Wikipedia position (which was ~1.5 km off).
- files: src/aquasource/adapters/ooi_camhd.py / scripts/download/ooi_camhd.sh / tests/test_ooi_camhd.py / src/aquasource/adapters/sites/ooi_camhd.csv / tests/fixtures/ooi_camhd/
- tests: pass (5/5, offline)
- sample: 1 file (2015-07-09, 43 KB stub) + metadata/samples.jsonl OK. Fixed bug: listing sizes are rounded, so strict size check removed (expected_bytes=None).
- doubts:
  - Licence is a bespoke permissive policy, not a named licence; no attribution clause was seen (policy T&Cs separate doc not read). Tier B is a judgement call.
  - Position varies a few metres per deployment; one fixed site row used.
  - Size: normal .mp4 is about 852 MB (download here ~0.25 MB/s); about 8 files/day; use from/to/per_day. Early 2015 days may hold tiny stub files. Months before 2015-07 give 404 (logged in failures.jsonl, harmless).
  - Full archive listing about 3,900 day folders at 1 req/s (about 1 h of metadata).
- needs_opus: no

## Notes
- Layout: rawdata.oceanobservatories.org/files/RS03ASHS/PN03B/CAMHDA301/<yyyy>/<mm>/<dd>/CAMHDA301-<UTC>.{mov,mp4}, 2015 to now.
- Options: from / to (YYYY-MM-DD), per_day=N.
- Ruff is not installed in this environment; lint not run.
