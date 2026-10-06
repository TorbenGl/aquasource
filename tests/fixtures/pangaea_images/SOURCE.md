# Fixture sources: `pangaea_images`

All files were retrieved on 2026-10-06 with User-Agent
`aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`. PANGAEA serves
metadata under CC0 and these data tables under CC BY (see each file's `License:` line).

Trimming rules (the same for every `.tab` file):
- The `/* DATA DESCRIPTION: ... */` header is kept as served, **except** that header lines
  containing an e-mail address were dropped. These are the `Parameter(s):` lines and their
  continuation lines, which carry PI names and e-mails. No other header line was changed.
- The column-header line is kept verbatim. Only the data rows listed below were kept, in
  their original order, byte-identical (TAB-separated, UTF-8, `\n` line ends). All other
  rows were dropped. No value was edited.

| File | Source URL | Kept rows (1-based data-row index in the served table) | What it tests |
|---|---|---|---|
| `989684_msm77_3-5_ofos_rows.tab` | https://doi.pangaea.de/10.1594/PANGAEA.989684?format=textfile | 1, 2, 26, 27, 28 of 762. 7 e-mail header lines dropped. | Per-image `Latitude`/`Longitude` plus `Coord unc [m]`. **Negative** `Depth water [m]` (provider quirk, use abs). Rows 1-2 have empty coordinates and come before the event time, so they fall back to the event and should be filtered as deck or descent frames. |
| `989683_msm77_11-1_ofos_rows.tab` | https://doi.pangaea.de/10.1594/PANGAEA.989683?format=textfile | 1, 240, 241 of 482. 3 e-mail header lines dropped. | No coordinate columns at all. Only the `Event(s):` line gives LATITUDE/LONGITUDE/ELEVATION, so the result is station-level. Media columns are `IMAGE water` and `Metadata` (bare filenames served from `https://download.pangaea.de/dataset/989683/files/`). |
| `879298_so242_auv_rows.tab` | https://doi.pangaea.de/10.1594/PANGAEA.879298?format=textfile | 1, 2, 216 of 1491. 24 e-mail header lines dropped. | AUV, per-image coordinates and positive depth. `URL image` is an absolute `https://hs.pangaea.de/...` link. `Ground vis [#]` is 0 for rows 1-2 (filter) and 1 for row 216. Licence is CC-BY-3.0. |
| `935896_so268_ofos_constant_position_rows.tab` | https://doi.pangaea.de/10.1594/PANGAEA.935896?format=textfile | 1, 2, 3 of 3923. 4 e-mail header lines dropped. | The `Latitude`/`Longitude` columns are present, but all 3923 rows carry the same position. Header `Comment: Positioning failed for this dive. All images should be logged as the same position.` There is no depth column. Expected result: station, depth taken from the event ELEVATION. Media column is `Binary`. |
| `898338_he153_rov_video.panmd.xml` | https://doi.pangaea.de/10.1594/PANGAEA.898338?format=metadata_panmd | Whole document, except the 2 lines `<md:eMail>...</md:eMail>`, which were dropped. The free-text `<md:comment>` line still contains a `mailto:` exactly as served, because editing a value is not allowed. | Single-video dataset (no data matrix). `technicalInfo` `staticURL` points to the MPEG. The `<md:event>` has latitude/longitude/elevation for both start and end (`*2` elements). The comment reads "Positions and depths from the ship's automatic data recording system". Expected result: station, midpoint of start and end. |

Expected `resolve_geo()` outputs (see `research/pangaea_images.md`, "resolve_geo recipe"):

| Fixture row | lat | lon | depth_m | geo_precision | geo_inferred | geo_uncertainty_m |
|---|---|---|---|---|---|---|
| 989684 row `2018-09-17T03:48:00` | 78.616649 | 5.001493 | 2361.4 | image | false | 1.59 |
| 989684 row `2018-09-17T02:43:27` (empty coords) | 78.61677 | 5.00115 | 2313.0 | station | true | 4000 (also flag `pre_event_no_position` → filter) |
| 989683 any row | 79.13221 | 6.26172 | 1290.0 | station | true | 4000 |
| 879298 row `2015-08-04T03:53:04` | -7.1247861 | -88.4512639 | 4140.9 | image | false | 50 |
| 935896 any row | 11.930071 | -117.021376 | 4093.9 | station | true | 4000 |
| 898338 (video) | 78.2599 | 9.399692 | 416.5 | station | true | ~1137 (half of 1273 m transect + 500 m) |

No publication-derived coordinates were needed: every station-level coordinate above comes from the
PANGAEA event metadata of the dataset itself. For that reason there is no `publication_sites.csv`.

Related file that was read but not stored as a fixture (fixture limit): the ROV ship track for the video,
https://hs.pangaea.de/Images/Benthos/HE/HE153/HE153_1274/HE153_1274_track.txt (2817 bytes, CR line ends,
1-minute fixes, columns `Latitude Longitude Time (UTC) Depth (m) Distance (m)`).
