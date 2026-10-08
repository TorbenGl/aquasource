## HANDOFF
- status: ok
- tier + licence: A, CC0 1.0 at record level: media `usage.access == "CC0"` in each EDAN record of the public bucket (https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan/nmnhinv/00.txt); metadata CC0 per https://github.com/Smithsonian/OpenAccess/blob/master/LICENSE. si.edu terms pages were not readable (bot wall).
- geo: region (record `indexedStructured.geoLocation[].points.point` lat/lon = published collection locality of the specimen, not camera position); depth from freetext `Depth (m)`. Script passes `--min-geo-precision region` (same as uk_seabed).
- files: adapter `src/aquasource/adapters/smithsonian_oa.py` / script `scripts/download/smithsonian_oa.sh` / test `tests/test_smithsonian_oa.py` / fixtures `tests/fixtures/smithsonian_oa/` (+SOURCE.md) / sites csv: none (no fixed sites)
- tests: pass (9 offline tests, `uv run pytest tests/test_smithsonian_oa.py -q`)
- sample: 3 of 3 JPEG downloaded OK (10-100 kB each, FFD8FF magic, samples.jsonl written, sample dir removed; run took 4 s, 2 metadata requests)
- doubts:
  - Most records are specimen photographs, not in-situ. `extra.maybe_not_underwater` is a keyword heuristic (underwater, in situ, ROV, diver, reef, camera, dive...); checker should look at a sample of flagged rows.
  - Coordinates are specimen collection localities (can be a whole-ocean or country point): region precision is used, uncertainty not set.
  - Media is the ids.si.edu `_screen` derivative (resolution not checked; not the TIFF originals).
  - Marine filter (default `marine_only=true`) drops terrestrial CC0 records; set `--opt marine_only=false` to keep them as noise.
  - Full run: 37 units x 256 shards of 5-20 MB (~95 GB metadata, estimate), streamed not cached; the default units are nmnhinv and nmnhfishes only.
- needs_opus: no (licence is explicit per record and CC0; geo is the record's own published coordinate, not inferred)

# Smithsonian Open Access: research note (2026-10-08)

## Access
- Public metadata: AWS bucket `smithsonian-open-access` (registry: https://registry.opendata.aws/smithsonian-open-access/). Unit index `metadata/edan/index.txt` lists 37 units; each unit has `index.txt` with 256 shards `NN.txt` (line-delimited EDAN JSON). No key.
- api.si.edu returns `API_KEY_MISSING` without an api.data.gov key; not used. The si.edu/openaccess and terms pages return a bot-verification page to scripts.
- Images: `https://ids.si.edu/ids/download?id=<NMNH-...>_screen` (Screen Image, JPEG, anonymous, 200 OK). High-resolution TIFF/JPEG are listed but not used (up to 14204x10652 px).
- Size: shards 5-20 MB; about 11 million records overall (OpenAccess README). Media: about 10-100 kB per screen JPEG measured on 3 files.

## Licence
- Record level: `descriptiveNonRepeating.online_media.media[].usage.access` = "CC0" (only this value is downloaded).
- Metadata: CC0 1.0 (GitHub Smithsonian/OpenAccess, LICENSE). Attribution kept per sample (Smithsonian Institution, unit, record link, CC0).

## Geo and content
- Coordinates: `indexedStructured.geoLocation[].points.point` latitude/longitude (decimal strings), present in about half of the records; depth in `physicalDescription` `Depth (m)`.
- In-situ share is unknown; in a 10.8 MB partial copy of nmnhinv/00 (4,718 lines), 154 CC0 media records have a screen image and 40 have a marine place with coordinates; the keyword flag marks 17 of the 40 as underwater-related (mostly "reef" and "camera" words).
- Units used by default: nmnhinv (Invertebrate Zoology, many ARMS / deep-sea collections), nmnhfishes. Others (nmnhmammals, nmnhherps, nmnhbirds, nmnhpaleo) can be added with `--opt units=`.

## Sample (2026-10-08)
- `aquasource --min-geo-precision region download smithsonian_oa --budget 3`: 3 candidates, 3 selected, 3 downloaded (first three marine CC0 records of nmnhinv/00: Atlantic off the US, South Sandwich area, Moorea; tier A). The fixture records are not the sample.
- Without `--min-geo-precision region` the run selected 0 (region is below the default `station` minimum), so the script passes it.

## Fixtures
- `tests/fixtures/smithsonian_oa/records_nmnhinv_marine.jsonl`: three real records copied from `metadata/edan/nmnhinv/00.txt`; see SOURCE.md.
