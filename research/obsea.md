## HANDOFF
- status: ok
- tier + licence: B, CC BY 4.0, read at record level (Zenodo record licence `cc-by-4.0` per year, e.g. https://zenodo.org/records/22802714; ERDDAP global `license` attribute CC-BY-4.0 agrees: https://data.obsea.es/erddap/info/OBSEA_seabed_station_pictures_L0a/index.json)
- geo: fixed_site, geo_source = publication coordinate (Zenodo description "latitude 41.18212 N, longitude 1.75257 E, depth 20.0 m", same in ERDDAP geospatial attributes), kept in adapters/sites/obsea.csv, inferred, no uncertainty published; index.csv has no per-picture coordinate
- files: src/aquasource/adapters/obsea.py / scripts/download/obsea.sh / tests/test_obsea.py / src/aquasource/adapters/sites/obsea.csv / tests/fixtures/obsea/ (SOURCE.md)
- tests: pass (7/7, `uv run pytest tests/test_obsea.py -q`)
- sample: 3 JPEG files downloaded OK, 0 errors (budget 3, about 28 kB each, magic FFD8FF, sample_id rows with fixed_site geo and tier B; dir removed); run took 145 s, 21 metadata requests (mostly the zip index reads, now cached)
- doubts:
  - Discovery order is table order: the sample is 2009-06-01 pictures only (oldest zip first); pictures were not looked at (dark / night frames, turbid frames, lab or sample photos such as `seaslag_samples`, `dolphin_carcass_20240530` are kept unflagged, as the rules say)
  - Geo is publication-derived for every camera: check that the PopUp_Cam_SN001 and other sensors really sit at the station (their rows carry the same coordinate)
  - Licence read from the Zenodo record field, not from the Zenodo landing page text; the per-year records all say cc-by-4.0
  - Full history is about 275 GB of zips (about 2 million JPEG, estimate from zip sizes); the adapter reads only the zip index, media comes from files.obsea.es one picture at a time; check the host load before a large run
  - Monthly zips are read with HTTP Range requests (central directory + index.csv); if a future zip has no top-level index.csv it is logged in failures.jsonl
- needs_opus: no
- checked: tests 7/7; sample OK; no network use in tests; checked by Sonnet 2026-10-08 (licence cc-by-4.0 confirmed on Zenodo record, geo ok, re-run took 589 s because Zenodo returned 504s)

## Summary
OBSEA (Observatorio Submarino de Vilanova i la Geltru, UPC / EMSO, 4 km offshore, NW Mediterranean, 20 m) runs a seabed
station with several cameras (IPC608UW, DCS-7010L, Sony SNC-RZ25N, AXIS P1346, PopUp camera) since 2009. Pictures are
open: one Zenodo community "obsea" record per year, 2009 to 2025, cc-by-4.0.

## Access (metadata only, read 2026-10-08)
- Discovery: `GET https://zenodo.org/api/records?q=title:"Underwater photography at OBSEA seabed station during"` (page
  size max 25 without a token), then each record `GET /api/records/<id>`. 19 year records (2009 to 2025, DOIs 10.5281/zenodo.22802048 ... 22817114).
- Each record has monthly zips `OBSEA_seabed_station_pictures_L0a_<yyyymmdd>_<yyyymmdd>.zip`. Each zip holds
  `index.csv` (timestamp, URL, sensor_id, platform_id, foi, files) and a NetCDF manifest (EMSO). The adapter reads only
  the zip central directory and index.csv (Range requests, zenodo supports them), cached in metadata/raw/obsea/.
- Media: `https://files.obsea.es/pictures/<sensor>/<yyyy>/<mm>/<dd>/<yyyymmdd-hhmmss>-<sensor>.jpeg` (nginx, Range supported,
  200 image/jpeg, no token). Listing of /pictures/ is open.
- ERDDAP (`data.obsea.es/erddap/tabledap/OBSEA_seabed_station_pictures_L0a`) has the same timestamps per sensor but no
  picture URL column: not used for discovery.

## Size (Zenodo file sizes)
2009 0.7 GB, 2010 0.8, 2011 1.1, 2012 1.3, 2013 0.5, 2014 1.1, 2015 14.8, 2016 14.7, 2017 14.4, 2018 3.1, 2019 4.6,
2020 4.6, 2021 2.8, 2022 2.2, 2023 22.8, 2024 87.5, 2025 99.9 GB (zips, total about 275 GB). Per-zip index sizes: about
3,200 rows for the 2013-01 zip (one camera), not measured for 2015 and later (several cameras).

## Geo
The index has no coordinate. The publication gives one position for the station; the adapter applies it to all rows
(`fixed_site`, the same rule as hodor). The site table is `src/aquasource/adapters/sites/obsea.csv`.

## Options (--opt)
- `from`, `to`: UTC day range (YYYY-MM-DD, inclusive).
- `per_day`: at most N pictures per UTC day (default all).
- `years`: only some Zenodo record years, e.g. `years=2013,2014`.
- `sensors`: only some sensor_id values.
- `refresh_metadata`: core option, re-read the cached index.csv files.

## Not done
- No pixel checks (dark / night frames, turbid frames, the PopUp camera, lab photos). Nothing is flagged in extra yet.
- No per-camera coordinates (none published); the PopUp camera may sit elsewhere on the seabed structure.
- The 2013 fixture is a 10-row cut of the real index; the full index has 3,181 rows.
