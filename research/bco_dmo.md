## HANDOFF
- status: blocked
- tier + licence: B at collection level (provisional). Site terms say all datasets are CC BY 4.0: https://bco-dmo.org/terms-use (read via search snippet, live page not re-read). Per-dataset licence NOT read: no dataset page loaded. Per-record rule not yet applicable.
- geo: none verified yet (planned: station/image from per-dataset lat/lon columns; no adapter).
- files: none (no adapter, no sites csv, no script, no fixtures, no test). Note only.
- tests: not run (nothing to test).
- sample: 0 files, not attempted (no data reachable).
- doubts: (1) every dataset page returns "Unable to load this page" (e.g. /dataset/3, /dataset/560, /dataset/773); the homepage shows an alert "whoi servers down" (expiry 2026-10-15). (2) The JSON API https://www.bco-dmo.org/api/... and https://osprey.bco-dmo.org/dataset/... return HTTP 403 from proxy-osprey (Apache), and /erddap returns 403. This may be an access block or a server problem: a checker must confirm with the operator. (3) Licence: CC BY 4.0 is site-wide, so media licences may still differ (embedded third-party photos/video). (4) Media are rare in BCO-DMO (mostly tables); image/video datasets need a per-dataset check. (5) Dataset universe: sitemap https://www.bco-dmo.org/sitemap.xml?type=Dataset&page=1 and page=2 list about 7,700 dataset URLs (osprey.bco-dmo.org/dataset/<id>).
- needs_opus: no. Access is blocked (server down or 403), not a licence contradiction; re-run this lean pass when the site is back.

## Research notes (2026-10-08)
- Entry point: https://www.bco-dmo.org/ (Next.js SPA, search at /search/dataset is client-rendered). Static pages load (terms, how-to); dataset pages do not.
- Dataset list: sitemap ~7,700 entries (2 pages of 5,000 and 2,688).
- Not done: no metadata records saved to tests/fixtures/bco_dmo/ (none could be read; not inventing fixtures). No SOURCE.md.
- Next steps for the next agent: (a) confirm whether BCO-DMO is up (retry /dataset/<id> and /api/ later, or ask the operator whether the 403 is an IP or UA block); (b) find image/video datasets by reading the search or sitemap entries; (c) read each dataset's licence and lat/lon columns; (d) then write adapter, script, test per src/aquasource/adapters/german_bight.py.
- Attribution to store: "PI name (year) title, BCO-DMO, doi/URL, accessed <date>" per https://bco-dmo.org/how-to/access-and-reuse/attribution.
- Politeness: no bulk requests were made; about 20 requests in total at 1/s.
