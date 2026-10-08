## HANDOFF
- status: blocked
- tier + licence: U (not resolved per device). ONC Data Policy: ONC-owned data CC BY 4.0; partner-owned data "may be" CC BY-NC or more restrictive. Read at collection level: https://www.oceannetworks.ca/data/data-policy/ (2026-10-08)
- geo: fixed_site, inferred, no uncertainty; lat/lon/depth of the /deployments record whose begin..end covers the file time (fields from client source, not checked live)
- files: src/aquasource/adapters/onc.py / scripts/download/onc.sh / tests/test_onc.py / tests/fixtures/onc/ (synthetic, SOURCE.md) / no sites csv (coords come from the API)
- tests: pass (8 offline, `uv run pytest tests/test_onc.py -q`)
- sample: 0 files, not run: ONC_TOKEN not set ("not ready: environment variable ONC_TOKEN is not set")
- doubts: (max 5)
  - Response shapes (archivefile `files`/`next.parameters`, deployments `deviceCode`/`begin`/`end`/`lat`/`lon`/`depth`) come from the ONC client 2.6.0 source, not from a live call; check on the first token run
  - tests/fixtures/onc has SYNTHETIC records (no token here); replace with real redacted responses
  - tier U: the runner must allow U for pretraining, otherwise nothing is downloaded
  - owner per device is not in the metadata we read; a partner device must not become B
  - the token travels as a query parameter; core/http.py logs only the URL, so it stays out of the log, but check the failures file
- needs_opus: yes, access: no ONC_TOKEN here (free account, human step); owner per device unresolved, so tier stays U

# ONC (Ocean Networks Canada, Oceans 3.0) research note

Date: 2026-10-08. Scope: fixed camera video and stills with a deployment position. Metadata only.

## Access
- API: https://data.oceannetworks.ca/api (guide: https://oceannetworkscanada.github.io/Oceans3.0-API/API_Guide.html). Every call needs `token` (or appToken); without it HTTP 401 errorCode 128.
- Token: free account, https://data.oceannetworks.ca/Profile. Env `ONC_TOKEN` (adapter env_vars).
- Endpoints used: `/deployments` (locationCode, deviceCategoryCode), `/archivefile/location` (locationCode, deviceCategoryCode, dateFrom, dateTo, fileExtension; paged via `next.parameters`), `/archivefile/download?filename=` (media).
- Rate: 1 request/s to data.oceannetworks.ca (host_intervals). No documented quota.

## Licence
- Data policy (read 2026-10-08): ONC-owned data CC BY 4.0; partner-owned data may be CC BY-NC or more restrictive; mixed reuse inherits the most restrictive licence. The seed says the same.
- Per file or device owner: not found in the metadata the client exposes. So every sample is tier U with `licence_level` collection and `extra.licence_note`. Not upgraded to B.
- Tier B would need a per-device owner check (ONC) or a verified ONC-owned device list.

## Geo
- Fixed cameras (VIDEOCAM, CAMERA): precision fixed_site, inferred, uncertainty null. Coordinates come from the deployment record for the file time, never from a guess.
- No deployment match -> geo none (sample kept, extra untouched). ROV/AUV categories are not fixed: not in the defaults.
- No publication-derived coordinates are used, so no site CSV.

## Filenames and time
- `<DEVICE>_<yyyymmddTHHMMSS.fffZ>.<ext>` (example from the API guide: `NAXYS_HYD_007_20091231T235919.476Z-spect.png`). Files without a timestamp are skipped.

## Size and history
- Not measured (no token). Archive history since about 2006 per the seed. Discovery requests one listing per calendar month of the window, cached under metadata/raw/onc/.

## Open
- Location codes: list with the API (`getLocations`) once a token exists; the adapter has no default location.
- First live run: `ONC_TOKEN=... scripts/download/onc.sh --opt locations=<CODE> --opt from=... --opt to=... --dry-run`, then copy one redacted deployments and archivefile response into tests/fixtures/onc/.
- Sample run (budget 3) still to do.
