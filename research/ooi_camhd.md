## HANDOFF
- status: blocked
- tier + licence: U, licence not confirmed. OOI Data Use Policy (https://oceanobservatories.org/wp-content/uploads/2024/01/1102-00010_Data_Use_Policy_OOI.pdf) and data policy page (https://oceanobservatories.org/data-policy/) returned HTTP 403 to all fetches (curl, WebFetch); no licence string read. Search snippets only: OOI data "freely available"; CC BY 4.0 applies to OOI articles, not datasets.
- geo: region (fixed camera at ASHES vent field; geo_source = src/aquasource/adapters/sites/ooi_camhd.csv, 45.9266 N 129.9795 W from Wikipedia ASHES article, depth 1552 m from OOI site listing)
- files: src/aquasource/adapters/ooi_camhd.py / scripts/download/ooi_camhd.sh / tests/test_ooi_camhd.py / src/aquasource/adapters/sites/ooi_camhd.csv / tests/fixtures/ooi_camhd/
- tests: pass (5/5, offline)
- sample: 0 files downloaded (dry-run and budget 3 over 2016-01-01..02 yield 16 candidates, all dropped as "tier U not selected"; no media fetched by design)
- doubts:
  - Licence: read the OOI Data Use Policy by hand before any tier change; do not set tiers to include U without that.
  - Geo: the vent field position is from Wikipedia, not a publication; the camera's own OOI metadata position (instrument page on the OOI Data Explorer) was not reachable. Replace with it if available.
  - Depth 1552 m comes from a search snippet of the OOI site page, not a fetched page.
  - Size: each .mp4 is about 852 MB (over the 500 MB sample rule); about 8 files per day, about 7 GB/day for .mp4 alone.
  - Full archive listing is about 3,900 day folders at 1 req/s (about 1 h of metadata); use from/to.
- needs_opus: yes, licence unresolved (the policy is unreadable here) and the geo coordinate is not from a publication.

## Notes
- Layout: rawdata.oceanobservatories.org/files/RS03ASHS/PN03B/CAMHDA301/<yyyy>/<mm>/<dd>/CAMHDA301-<UTC>.{mov,mp4}, 2015 to now.
- Options: from / to (YYYY-MM-DD), per_day=N.
- Ruff is not installed in this environment; lint not run.
