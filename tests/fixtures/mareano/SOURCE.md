# Fixture sources: `mareano`

All files retrieved 2026-10-06 with User-Agent `aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`.
Values are unmodified. Where a file was trimmed, only whole records (CSV lines / GeoJSON features) were dropped.

| File | Exact URL | Trimming |
|---|---|---|
| `bilder_biologi_wfs_sample.json` | `https://kart.hi.no/mareano/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=mareano_stasjoner:bilder_biologi&outputFormat=application/json&resourceId=bilder_biologi.10,bilder_biologi.1,bilder_biologi.164` | None. This is the full server response for 3 features selected by `resourceId`. |
| `bilder_biologi_ogcapi_sample.csv` | `https://kart.hi.no/mareano/ogc/features/v1/collections/mareano_stasjoner:bilder_biologi/items?f=text%2Fcsv&limit=10000` | The full response has 340 rows (the whole layer). Kept: the header and rows `bilder_biologi.1`, `.10` and `.164` (the same 3 features as the JSON). CRLF line endings are preserved. |
| `videostasjoner_sample.csv` | `https://kart.hi.no/mareano/ogc/features/v1/collections/mareano_stasjoner:videostasjoner_aarlig/items?f=text%2fcsv&filter=RefStation+IN+%285%2c73%2c449%2c734%29&filter-lang=cql-text` | None. This is the full server response to the CQL filter (4 reference stations, matching `REFSTASJ` of the image rows above plus station 449). |
| `marbunn_video_lines_2007105_R73.json` | `https://marbunn-ekstern.hi.no/apps/marbunn/v1/showstationsinmap?cruiseno=2007105` | The full response (44 KB) holds every gear deployment of cruise 2007105. Kept: the 4 features with `"Equipment":"Video"` and `"Reference station":73` (video lines 79, 100, 101, 102). Each kept feature was checked to be a byte-identical substring of the original response, and the FeatureCollection wrapper is the original one. |
| `licence.txt` | Several pages; each section gives its own URL (the Imageshop TermsOfUse, two Geonorge metadata records, the mareano.no biological data page, cruise report 2026007006, the mareano.no footer and the NGU photo archive terms). | Verbatim quotes taken from HTML/JSON. Only whitespace was normalised. |

## Notes for tests

- `bilder_biologi.10` has every field: a time-of-day in `TID`, depth in `DYBDE`, and a legacy `/cache/` URL holding the old archive id `HI-018615`. That id maps to Imageshop asset `HAV-006059`.
- `bilder_biologi.1` has an empty `TID` and a legacy `/embed/` URL. Its `TITTEL_N` is exactly the Imageshop description of asset `HAV-056035`. Its `TOKT` 2006112 differs from `CruiseNo_V` 2006612 of station 5 in `videostasjoner_sample.csv`, which is a known inconsistency.
- `bilder_biologi.164` has `DYBDE` = 0, which means the depth is missing. Use the station `BottomDepth` 270.49 m from `videostasjoner_sample.csv` instead (RefStation 734). Its coordinate equals the station-734 point to within 1 m, so it is probably a station position rather than a per-frame position.
- In both formats the GeoJSON/WFS `geometry` is rounded to 4 decimals. The full-precision coordinates are the `properties.Latitude` and `properties.Longitude` values in the JSON, or the WKT in the `the_geom` column of the CSV. In the CSV, the `Latitude` and `Longitude` columns are rounded to 4 decimals. The JSON `crs` says `EPSG::4326`, but the coordinate order is lon,lat.
- `DATO` holds local midnight (Europe/Oslo) stored as UTC: `2007-03-30T22:00:00Z` is 2007-03-31.
- The Marbunn `Datetime` field (`dd.mm.yyyy HH:MM:SS`) is the video-line start time. Its timezone is not documented.
- No `publication_sites.csv`: positions come from per-image and per-station attributes, not from a publication.
