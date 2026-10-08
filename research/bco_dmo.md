## HANDOFF
- status: blocked
- tier + licence: B (CC BY 4.0). Confirmed per record via DataCite (rightsList = spdx cc-by-4.0) for BCO-DMO DOIs (10.26008/1912/bco-dmo.<id>.<v>); not read at file level.
- geo: DataCite geoLocations give a point (station) or only a place name; no per-image coords.
- files: none (no adapter/fixtures/test/script). Sample: not run (no adapter).
- retry findings (2026-10-08): UA is not the problem. www.bco-dmo.org/dataset/<id> returns HTTP 200 but the body is the Next.js error page "Unable to load this page" (backend down); /api/ and erddap return 403 from proxy-osprey. api.datacite.org works (publisher.name:BCO-DMO, about 70 hits for photo/video/image keywords) but has no contentUrl/media formats (0 hits for jpeg/png/mp4), so no media URLs are discoverable without the dataset pages/ERDDAP.
- doubts: media in BCO-DMO are rare (mostly tables); Zenodo links seen (ISIIS 10.5281/zenodo.7739010) are code only.
- human check: ask BCO-DMO whether the /api and erddap 403 is a deliberate block and when the 'whoi servers down' outage ends (alert expiry 2026-10-15); then re-run, listing candidates via DataCite and file URLs via the dataset page.
- needs_opus: no.

## Research notes (2026-10-08)
- Entry point: https://www.bco-dmo.org/ (Next.js SPA, search at /search/dataset is client-rendered). Static pages load (terms, how-to); dataset pages do not.
- Dataset list: sitemap ~7,700 entries (2 pages of 5,000 and 2,688).
- Not done: no metadata records saved to tests/fixtures/bco_dmo/ (none could be read; not inventing fixtures). No SOURCE.md.
- Next steps for the next agent: (a) confirm whether BCO-DMO is up (retry /dataset/<id> and /api/ later, or ask the operator whether the 403 is an IP or UA block); (b) find image/video datasets by reading the search or sitemap entries; (c) read each dataset's licence and lat/lon columns; (d) then write adapter, script, test per src/aquasource/adapters/german_bight.py.
- Attribution to store: "PI name (year) title, BCO-DMO, doi/URL, accessed <date>" per https://bco-dmo.org/how-to/access-and-reuse/attribution.
- Politeness: no bulk requests were made; about 20 requests in total at 1/s.
