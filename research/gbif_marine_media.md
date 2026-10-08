## HANDOFF
- status: ok
- tier + licence: A/B per media file: `media[].license` (file level), occurrence `license` only if the media states none (record level). Read at https://api.gbif.org/v1/occurrence/search (fields media, license); licence URLs as stated by the publisher (e.g. http://creativecommons.org/licenses/by/4.0/). X (NC/ND/"All rights reserved") is not downloaded.
- geo: precision `image` (seed) + geo_source "GBIF occurrence decimalLatitude/decimalLongitude (+ coordinateUncertaintyInMeters, depth)"; coordinates are published, geo_inferred false.
- files: adapter src/aquasource/adapters/gbif_marine_media.py / script scripts/download/gbif_marine_media.sh / test tests/test_gbif_marine_media.py / fixtures tests/fixtures/gbif_marine_media/ / sites csv: not needed (no publication-derived coordinates)
- tests: pass (7 tests, offline, 3 real records)
- sample: 3 files downloaded OK, 0 errors (budget 3, 6 s, 1 metadata request); scratch dir removed afterwards
- doubts:
  - geo_precision `image` is the seed's value, but the coordinate belongs to the occurrence (the observation place), not to the photo: check whether `station` fits better.
  - No underwater filter in the API (`habitat` and `waterBody` are not search parameters). Pool = StillImage + coordinates + depth 0-200 m; most hits are birds and plants: all kept, `extra.maybe_not_underwater` true unless habitat=marine or waterBody set.
  - File and record licence disagree: a CC0 occurrence with CC BY-NC media (fixture 6406420337). File level applied, `extra.licence_conflict` set.
  - Offset paging stops at 100,000 (GBIF cap) of about 717 k records: more needs partitioning (year, datasetKey or depth bands).
  - CC0 media were rare in the sample (0 of 600 occurrences); the publishers' own terms (iNaturalist, Artsobservasjoner, museums) are not checked.
- needs_opus: yes, licence contradictions between occurrence and media level are common (the rule "most specific level" was applied as written, but a checker should confirm it for pretraining).

## Notes (lean pass 2026-10-08)
- Access: anonymous GBIF API, no token. Metadata requests ~1 request/s (`host_intervals`). Media fetched from each publisher's host (plain HTTPS).
- Counts (API, 2026-10-08): 83 M occurrences with CC BY_4_0 record licence; 717,511 StillImage occurrences with coordinates and depth 0-200 m. `mediaLicense` is ignored by the API (CC0 and CC BY counts identical), so the licence is filtered client side.
- Sample of 600 occurrences (depth 0-200, StillImage): 916 X media, 156 CC BY media (B), 15 unknown; media licences most often by-nc-nd, by-nc-sa, "All rights reserved".
- Fixtures: `search_sample.json` (3 real records) and `SOURCE.md`.
- Adapter options: `depth` (default `0,200`), `max_offset` (default 100000).
- Not done: pixel filters for underwater or above-water shots; dedup against other sources (the item id is the media URL); partitioned enumeration beyond 100k.
