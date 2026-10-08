## HANDOFF
- status: ok
- tier + licence: B, collection level. OOI Data Use Policy v2-00 s4.1 (1102-00010; read via web.archive.org copy, live site 403; same policy as ooi_camhd): free public use for any legal purpose incl. derivatives, publish, distribute. No NC/ND, no named licence, so B not A. https://oceanobservatories.org/wp-content/uploads/2024/01/1102-00010_Data_Use_Policy_OOI.pdf
- geo: fixed_site, geo_source = sites/ooi_cameras.csv (OOI asset-management deployment tables, latest deployment per camera, lat/lon/deployment_depth), geo_inferred false, uncertainty 10-40 m from deployment spread
- files: src/aquasource/adapters/ooi_cameras.py / scripts/download/ooi_cameras.sh / tests/test_ooi_cameras.py / src/aquasource/adapters/sites/ooi_cameras.csv / tests/fixtures/ooi_cameras/
- tests: pass (7/7, offline)
- sample: 3 JPEG frames (2025-06-01, CAMDSC102, about 17 MB each) downloaded OK + metadata/samples.jsonl; sample dir removed
- doubts:
  - Licence is the same bespoke OOI policy as CamHD; tier B is a judgement call, not a named licence.
  - depth_m = deployment_depth (instrument depth), not water_depth. ooi_camhd uses water_depth. Check the two agree in intent.
  - Positions are the latest deployment of each camera (spread up to 37 m at CE04OSBP); fixed site applied to every frame.
  - Size: a camera-day can be about 300 frames of 10-16 MB (about 5 GB). Use per_day, from/to. Full archive is about 6 cameras x 12 years of day listings (1 req/s metadata).
  - Camera list = 6 CAMDS instruments found by sweeping all RS sites and CE01-CE04; CE06-CE09, CP, GA, GI, GP, GS, AS not finished (sweep stopped for time).
- needs_opus: no

## Notes
- Camera set (CAMDS, JPEG, not CAMHD video): RS01SBPS-PC01A-07-CAMDSC102 (2014-), RS03AXPS-PC03A-07-CAMDSC302, RS01SUM2-MJ01B-05-CAMDSB103, RS03INT1-MJ03C-05-CAMDSB303, CE02SHBP-MJ01C-08-CAMDSB107, CE04OSBP-LV01C-06-CAMDSB106. Video CAMHDA301 (RS03ASHS) is in ooi_camhd.
- Layout: rawdata.oceanobservatories.org/files/<site>/<platform>/<instrument>/<yyyy>/<mm>/<dd>/<INSTR>_<camera IP>_<yyyymmdd>T<hhmmss>_UTC[_n].jpg. Apache listing, anonymous, no token.
- Options: from / to (YYYY-MM-DD), per_day=N, cameras=<refdes,...>.
- Sample check: AQUASOURCE_DATA_ROOT=/tmp/aquasource_scratch/sample_ooi_cameras uv run aquasource download ooi_cameras --budget 3 --opt cameras=RS01SBPS-PC01A-07-CAMDSC102 --opt from=2025-06-01 --opt to=2025-06-30 --opt per_day=3 (about 3.5 min, 4 metadata requests).
- Deploy tables: github oceanobservatories/asset-management deployment/<SITE>_Deploy.csv (CE02SHBP, CE04OSBP, RS01SBPS, RS01SUM2, RS03AXPS, RS03INT1 used).
- Fixtures: tests/fixtures/ooi_cameras/SOURCE.md (listings from 2025-06-01 and the camera's year/month listings; CAMDS deploy excerpt).
- Ruff is not installed in this environment; lint not run.
