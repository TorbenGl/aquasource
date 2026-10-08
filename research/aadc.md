## HANDOFF
- status: blocked
- tier + licence: B, CC BY 4.0 at record level (`use_constraints` "CCBY Attribution License"; API https://data.aad.gov.au/metadata/api/records/VMS_Benthic_Photography). Site footer also says CC BY 4.0 (https://data.aad.gov.au/aadc/about/condition_of_use.cfm redirects to /docs/conditions-of-use)
- geo: region at best (record `spatial_coverage` is a bounding box only, no per-image or per-station coordinates in metadata); geo_source would be the record bbox, not yet implemented
- files: research/aadc.md, tests/fixtures/aadc/ (3 detail JSON + SOURCE.md). No adapter, script or test written (blocked on media access)
- tests: not run (no adapter)
- sample: 0 files, not attempted (no working download route)
- doubts:
  - Media download: `eds/<n>/download` links return the SPA HTML shell (1211 bytes) to HEAD and GET; no direct file found
  - Most underwater records are marked "not yet publicly available" (e.g. ASAC_2201_Casey_photoquadrats1/2, AAS_4633); only open ones count
  - Per-image coordinates: unknown, probably inside the data packages (5 to 86 GB); check before any geo claim
  - Discovery works (JSON API, 59 hits for full_text=underwater); candidates: VMS_Benthic_Photography (stills), underwater_video_V40304 (avi), CEAMARC_200708_V3_MARINE_VIDEO_SAMPLES (request point)
- needs_opus: yes, access: the download route for `eds` links is unknown (need a form or an API token?), and geo for region-only records is a policy call

## Summary
Australian Antarctic Data Centre (AADC, https://data.aad.gov.au). Underwater stills and video exist (benthic photos, marine
video, photoquadrats) but are either restricted or not reachable by a plain HTTP download. Metadata is good: CC BY 4.0
on the record, and a JSON API.

## Access (metadata only, 2026-10-08)
- Search: `GET https://data.aad.gov.au/metadata/api/records/?full_text=<text>&size=100` with `Accept: application/json`
  (the page's own JS calls this; the `text=` parameter is ignored). Total on full catalogue: 3428.
- Detail: `GET https://data.aad.gov.au/metadata/api/records/<entry_id>` returns `{success, data}` with licence, distribution,
  access constraints, spatial and temporal coverage, related URLs.
- Citation/DOI per record (`dataset_doi`, e.g. doi:10.4225/15/59acda196ccfb for VMS_Benthic_Photography).
- The `eds/<n>/download` links from `related_url` ("Download the dataset") do not serve a file to a plain request.

## Candidate records (full_text=underwater)
| entry_id | content | licence (record) | distribution | access text |
|---|---|---|---|---|
| VMS_Benthic_Photography | seafloor stills, Mertz shelf, 2011 | CC BY 4.0 | 5 GB, Images, HTTP, free | publicly available |
| underwater_video_V40304 | Aurora Australis voyage 4 video, 2003-04 | CC BY 4.0 | 7.75 GB, avi | copies available from the URL |
| CEAMARC_200708_V3_MARINE_VIDEO_SAMPLES | video samples, 2007-08 | CC BY 4.0 | 86 GB mpeg ("Request point"), 68 kB Excel | request for video files |
| ASAC_2201_Casey_photoquadrats1 / 2 | photoquadrats, Casey 1997 | CC BY 4.0 | none | not yet publicly available |
| AAS_4633_BEAUT_..._Photoquadrats | benthic photoquadrats Casey/Davis 1997-2022 | CC BY 4.0 | 3 MB Excel | not yet publicly available |

## Geo
- Record `spatial_coverage` gives a bounding box (VMS: lat -67 to -42, lon 140 to 150, depth 0 to 4500 m). That is a
  region, not a station or image position. Per-image coordinates are not in the metadata.
- The AADC publishes no per-station table for these records (checked in the detail JSON and the citation page).
- Options if access is solved: region precision from the bbox centre with `geo_uncertainty_m` from the half-diagonal, or
  per-image coordinates from the data package if it has them (must be read first). No coordinates invented.

## Licence
- Record level: `use_constraints` "This data set conforms to the CCBY Attribution License (http://creativecommons.org/licenses/by/4.0/)".
- Site footer (AADC): CC BY 4.0 Unported.
- No NC/ND/research-only term seen in the records read. Tier B, read at record level.

## Blocked
1. Media download: the `eds/<n>/download` routes return the AADC front-end HTML, not a file. Unknown whether a form, a
   login, a request step or an API token is needed. Not guessed.
2. Most underwater records are restricted ("not yet publicly available").

## Next step (for a person or Opus)
- Find the real download route for one open record (VMS_Benthic_Photography, 5 GB) and check whether the download is a
  zip/tar of images, and whether it holds coordinates.
- Then write `src/aquasource/adapters/aadc.py` (discovery through the JSON API, licence from `use_constraints`, geo from
  the bbox or data package), `scripts/download/aadc.sh` (from _template.sh) and `tests/test_aadc.py` on the fixtures.

## Not done
- No adapter, script, test or sites CSV.
- No sample download (no route to media).
