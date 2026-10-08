## HANDOFF
- status: ok (scope: one JNCC archive, Bassurelle Sandbank 2013, 550 station JPEGs; other UK seabed datasets not adapted)
- tier + licence: B, UK Open Government Licence, record level (CKAN license_id uk-ogl, https://ckan.publishing.service.gov.uk/api/3/action/package_show?id=seabed-videos-from-bassurelle-sandbanks-sci1; OGL v3 URL seen on the sibling JNCC record http://data.jncc.gov.uk/waf/18ad227a-dc03-4b64-a91d-004a46881531.xml)
- geo: region, geo_source = CKAN bbox centre (sites/uk_seabed.csv: 50.607 N, 1.038 E, uncertainty 9900 m); no per-image or per-station coordinates in the archive
- files: src/aquasource/adapters/uk_seabed.py / scripts/download/uk_seabed.sh / tests/test_uk_seabed.py / src/aquasource/adapters/sites/uk_seabed.csv / tests/fixtures/uk_seabed/ (3 data files + SOURCE.md)
- tests: pass (9 passed, offline; `uv run pytest tests/test_uk_seabed.py -q`)
- sample: 3 of 3 JPEG downloaded OK (6.5 MB, FFD8FF...FFD9 markers, samples.jsonl written; sample dir removed). Needed `--min-geo-precision region` (the script passes it)
- doubts:
  - Geo is a bounding-box centre (publication-derived, region only). Check whether this is acceptable for pretraining or whether a station table exists to upgrade it.
  - File `JNCC2013_03BassSandRawBenthicSamplingvideo.zip` holds stills, not video. Its sibling `...Videostill_photographs.zip` (2.89 GB, CKAN "stills") shows no end-of-central-directory at its tail (possibly truncated on S3); not adapted.
  - The CKAN record gives only `uk-ogl` (no version); treated as OGL (tier B). The OGL v3 text is seen only on the Haig Fras ISO record.
  - Station text files carry frame timestamps (YYYYMMDDHHMMSS); not parsed yet, so timestamp is null.
  - The script forces `--min-geo-precision region` for this dataset. That is a policy choice for the whole run.
- needs_opus: yes, because region-level geo is a bbox centre (not a station or image position) and the checker has to decide whether that counts as an acceptable publication-derived coordinate.

---

# uk_seabed: UK seabed still photographs (JNCC, OGL)

Seed: "UK seabed imagery (JNCC / Cefas / BGS via MEDIN)", tier B, geo station/image (to verify). Checked on 2026-10-08 (metadata and HEAD/Range only; no image bytes except the 3 sample JPEGs).

## Candidates surveyed
- JNCC offshore survey records on data.gov.uk (CKAN, `ckan.publishing.service.gov.uk`): about 30 packages named `seabed-still-images-...` / `seabed-videos-from-...` (Haig Fras, Fladen, Dogger Bank, Solan Bank, Bassurelle, West Shetland, ...). Most are licence `uk-ogl`, with bbox extras. Most resources are the landing page `http://jncc.defra.gov.uk/opendata` (no direct file). Only two were direct S3 zips: the Bassurelle pair below.
- Bassurelle Sandbank SCI (2013, Cefas/JNCC benthic sampling, English Channel). Direct S3 zip, `Accept-Ranges: bytes`, plain HTTP (no token). Used here.
- Cefas Data Hub, Fladen experimental fishing (DOI 10.14466/CefasDataHub.85, OGL, DataCite rights): derived seabed-imagery analysis (counts), extent only (lat 58-58.25, lon 0-0.5). Not adapted: no per-image positions and the media is not confirmed in the Hub.
- NERC BAS Rothera (DOI 10.5285/2c313c0b-7cf4-4206-8cd1-adc8d0530794, OGL v3): seabed video and stills, 109 GB, Antarctica (not UK shelf). The BAS record says "under embargo until the publication of the associated manuscript" and "Dataset Progress: Planned". Excluded for now (embargo, out of region).
- Non-UK CC BY hits (PANGAEA Borkum, Polarstern OFOS, Zenodo) are out of scope for this dataset key.

## Bassurelle archive (adapted)
- URL: `http://s3-eu-west-1.amazonaws.com/data.defra.gov.uk/Marine/JNCC2013_03BassSandRawBenthicSamplingvideo.zip`, 1,446,466,291 bytes, 585 entries, zip64 not needed.
- Contents: `still_photographs/<BSSS_CEND0313_..._STN_<n>_A1>/`: 550 JPG (about 1-3 MB each), one station text file per folder (`1.txt`: file name tab timestamp YYYYMMDDHHMMSS, no coordinates), `schema.ini`, Thumbs.db, plus a nested 22-byte `still_photographs.zip`.
- Method: central directory read with Range requests (EOCD at the end, then 79 KB), cached at `metadata/raw/uk_seabed/bassurelle_sci_2013_entries.json`. One Range request per frame (local header + compressed bytes), inflated (deflate 8 or stored 0), checked for the JPEG signature and the local name, then written atomically.
- Geo: CKAN extras bbox (N 50.666, S 50.548, W 0.934, E 1.142). Centre 50.607 N, 1.038 E; corner distance about 9.9 km, so precision `region`.
- Licence: `uk-ogl` on the CKAN record (tier B). The attribution text names JNCC and the record.

## Other files
- tests: `tests/test_uk_seabed.py` (discover from the real subset, licence, geo, fetch with a synthetic zip, HEAD error).
- Commands:
  - Sample: `AQUASOURCE_DATA_ROOT=/tmp/aquasource_scratch/sample_uk_seabed uv run aquasource --min-geo-precision region download uk_seabed --budget 3` (the script does the same).
  - Tests: `uv run pytest tests/test_uk_seabed.py -q`.

## Open items (not done)
- Adapt more JNCC archives (find direct S3 zip resources in the CKAN packages; add entries to `ARCHIVES` and rows to `sites/uk_seabed.csv`).
- Parse the station text files for timestamps and check whether JNCC publishes station coordinates (sample tables) for station-level geo.
- Check the Bassurelle stills zip at `...Videostill_photographs.zip` (no EOCD at the tail).
- Cefas Data Hub: check whether the Fladen and Haig Fras media are downloadable there.
