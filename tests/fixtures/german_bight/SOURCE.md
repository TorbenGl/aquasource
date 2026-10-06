# Fixture sources: `german_bight`

All files were retrieved on 2026-10-06 with the User-Agent `aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`.
Lines were copied byte for byte from the provider response. Rows were dropped; no values were edited and no row was reordered.
The `/* DATA DESCRIPTION ... */` header block of each PANGAEA export is kept complete.

| File | Exact URL | Trimming |
|---|---|---|
| `pangaea_907386_excerpt.tab` | https://doi.pangaea.de/10.1594/PANGAEA.907386?format=textfile | Header block and column line kept. 4 of 87 data rows kept: `Profile Spots_01-1` (row 1, AVI only), `Profile Greifer_AG1_005`, `Profile Greifer_AG1_006`, `Profile Greifer_AG3_024` (HE416 row whose files sit in the HE415 folder). The full, untrimmed export is already in `tests/fixtures/_core/pangaea_907386.tab` (identical bytes, 34,316 B). |
| `pangaea_909999_excerpt.tab` | https://doi.pangaea.de/10.1594/PANGAEA.909999?format=textfile | Header block and column line kept. 4 of 45 data rows kept: `He436_001` (AVI + GoPro), `He436_012-1` (empty `Bathy depth [m]`), `He436_014` (no GoPro MP4), `He436_029` (longitude disagrees with the DSHIP event log by 3.2 km, see below). |
| `pangaea_831731_excerpt.tab` | https://doi.pangaea.de/10.1594/PANGAEA.831731?format=textfile | Header block and column line kept. 3 of 13 data rows kept: `Video01_2011-06-15T15_06_00`, `Video06_2011-06-16T15_20_00`, `Video13_2011-06-17T16_11_50`. |
| `events_HE436_excerpt.tab` | https://www.pangaea.de/ddi/HE436.tab?retr=events/Heincke/HE436.retr&conf=events/CruiseReportText.conf&format=textfile | Column line kept. 5 of 92 event rows kept: `HE436/003-1` (van Veen grab, a non-video event to filter out), `HE436/003-2`, `HE436/014-1`, `HE436/017-2`, `HE436/032-2` (the `Video camera` events whose start-to-end window, widened by 2 min, contains the `Date/Time` of each of the 4 rows in `pangaea_909999_excerpt.tab`; He436_012-1 at 12:54:18 falls 42 s before `HE436/014-1` starts). |
| `pangaea_909999_jsonld.json` | https://doi.pangaea.de/10.1594/PANGAEA.909999?format=metadata_jsonld | Not trimmed (10,004 B). Record-level licence: `"license": "https://creativecommons.org/licenses/by/4.0/"`, `"conditionsOfAccess": "unrestricted"`. |

## Facts the tests can rely on

- Column order differs between datasets: 907386 has `Longitude` before `Latitude`, 909999 has `Latitude` first. Parse by column name, never by position.
- `pangaea_907386_excerpt.tab`, row `Profile Greifer_AG1_005`: its `URL file (LRV)`, `URL movie (MP4)` and `URL file (THM)` cells point to `HE415_Greifer_AG1_006_HD.*`.
  - We read the `mvhd` box of `HE415_Greifer_AG1_006_HD.MP4` with a 119-byte Range request. Its creation_time is 2014-02-21 12:38:36 in the GoPro clock, which runs on CET (UTC+1). That is 11:38 UTC, the `Date/Time` of row `Profile Greifer_AG1_006`.
  - The row `Profile Greifer_AG1_005` has `Date/Time` 11:11 UTC, and its coordinates lie 2,107 m from those of AG1_006.
  - So `resolve_geo` must map GoPro files to a row by the station token in the filename (`AG1_006`), not by the row they appear in.
- `pangaea_909999_excerpt.tab`, row `He436_029`: the table gives `Longitude` 7.10933. The DSHIP event `HE436/032-2` (00:29 to 00:44 UTC) gives 7.15950 to 7.16150. The 10-min master track in PANGAEA.840690 gives 2014-11-18T00:30 at 54.69528 N, 7.15924 E (https://doi.pangaea.de/10.1594/PANGAEA.840690?format=textfile). The table value is therefore a typo, 3,226 m off.
- Distances from table rows to the matched DSHIP event (haversine):

  | Row | To event start | To event end | Event track length |
  |---|---|---|---|
  | He436_001 | 37 m | 67 m | 103 m |
  | He436_012-1 | 8 m | 33 m | not given |
  | He436_014 | 20 m | 81 m | not given |

- `pangaea_831731_excerpt.tab`: the start-to-end midpoint of each transect, the transect length, and the uncertainty used by the recipe (half the length plus 30 m):

  | Row | Midpoint lat | Midpoint lon | Length | Uncertainty |
  |---|---|---|---|---|
  | Video01 | 54.2102501 | 7.8941948 | 155.3 m | 108 m |
  | Video06 | 54.2253556 | 7.8736778 | 108.7 m | 84 m |
  | Video13 | 54.1789196 | 7.9156956 | 153.5 m | 107 m |

No `publication_sites.csv`: every video row carries its own coordinate in the data table, so no location is derived from a publication.
