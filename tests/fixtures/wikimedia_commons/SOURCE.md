# Fixtures: wikimedia_commons (fetched 2026-10-08, metadata only, no media downloaded)

- API: https://commons.wikimedia.org/w/api.php?action=query&generator=categorymembers&gcmtitle=Category:Underwater_photographs&gcmtype=file&gcmlimit=50&prop=coordinates|imageinfo&iiprop=url|extmetadata|size|mime|user|timestamp
- Docs: https://www.mediawiki.org/wiki/API:Categorymembers , https://www.mediawiki.org/wiki/Extension:GeoData (prop=coordinates)
- Licence reference: https://commons.wikimedia.org/wiki/Commons:Licensing
- `api_categorymembers_sample.json`: real answer, trimmed to 3 file pages (pageid kept):
  - "File:Clownfish - Marsa Alam, Egypt - August 8, 2011.jpg" (CC BY 4.0, https://creativecommons.org/licenses/by/4.0 , coordinate 24.916117 N). Accepted, tier B, file level.
  - "File:4822 Bad Goisern am Hallstättersee, Grund Hallstätter See 01 2022-07-25.jpg" (CC0, coordinate 47.609875 N). Tier A, but the category is a lake photo: `maybe_not_underwater` true.
  - "File:Blue Eye, Theth.webm" (CC BY-SA 4.0, coordinate 42.364405 N). Tier C: not downloaded by default (tiers A,B).
