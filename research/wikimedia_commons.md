## HANDOFF
- status: ok
- tier + licence: per file, file level. CC0 / Public domain = A; CC BY 3.0/4.0 = B; CC BY-SA = C (not selected by default); NC / ND / fair use / unstated = X or U, never downloaded. Read from `extmetadata.LicenseShortName` + `LicenseUrl` of each File page (https://commons.wikimedia.org/wiki/Commons:Licensing, example https://commons.wikimedia.org/wiki/File:Clownfish_-_Marsa_Alam,_Egypt_-_August_8,_2011.jpg)
- geo: image; geo_source = MediaWiki GeoData `prop=coordinates` of the File page (EXIF GPS or {{Location}} template as stored); geo_inferred false, no uncertainty
- files: src/aquasource/adapters/wikimedia_commons.py / scripts/download/wikimedia_commons.sh / tests/test_wikimedia_commons.py / fixtures tests/fixtures/wikimedia_commons/ (+SOURCE.md); sites csv: none (no fixed sites)
- tests: pass (10/10, `uv run pytest tests/test_wikimedia_commons.py -q`)
- sample: 3 of 3 downloaded OK (2 CC0 Bad Goisern lake photos, 1 CC BY 2.0 Boston Aquarium photo), 0 errors, 26 MB; scratch removed
- doubts:
  - geo precision `image` may be too strong: several files share one coordinate (dive site or {{Location}} template place); check repeated lat/lon in samples.jsonl
  - non-marine files are in the categories (aquarium, lake, cave); flagged `extra.maybe_not_underwater` by a title/description keyword rule only
  - scale is small: Underwater photographs 285 direct files (+11 subcategories, not traversed), Underwater videos 138 (+9 subcats); about 1 file in 8 has coordinates
  - `Restrictions` (trademark, personality rights) is only kept in `extra.restrictions`, not acted on
  - videos (webm/ogv) only tested offline; no video was downloaded in the sample
- needs_opus: no

## Research (2026-10-08, metadata only)
- Access: anonymous MediaWiki API, `https://commons.wikimedia.org/w/api.php`, User-Agent from core/http.py, 1 request/s. No token.
- `list=geosearch` (global coordinate search) returned "cirrussearch-too-busy-error" on the first try and was not used. Discovery is by category instead: `generator=categorymembers` with `prop=coordinates|imageinfo`, 50 files per page, `continue` paging (each page cached under metadata/raw/categories/).
- Categories (direct members, categoryinfo 2026-10-08): Underwater photographs 285 files, Underwater videos 138 files, Coral reefs 1016 (not used by default: mostly above-water reef photos), Scuba diving 97.
- Sizes: photos 0.2-20 MB; videos 2 MB to 3.5 GB. Files above `max_bytes` (default 500 MB) are skipped.
- Fixtures: `api_categorymembers_sample.json` (real answer, 3 file pages: Clownfish CC BY 4.0 B; Bad Goisern CC0 A; Blue Eye webm CC BY-SA 4.0 C). Sources in tests/fixtures/wikimedia_commons/SOURCE.md.

## Adapter options
- `categories` (default `Underwater photographs,Underwater videos`; subcategories are not traversed)
- `tiers` (default `A,B,C`; runner selection still applies)
- `geo_only` (default true), `max_bytes` (default 500000000)

## Next steps (not done)
- Traverse the subcategories (optional `depth` option) if more volume is needed.
- Check the Restrictions field and the `{{Location}}` vs EXIF origin of coordinates per file, if the precision matters for training.
