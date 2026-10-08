## HANDOFF
- status: ok
- tier + licence: A. US government work (NOAA/NCEI), no licence stated on the records; ISO accessLevel "public" and "available to the public for a wide variety of uses" (ISO of accession 0310923, the EX2507 mapping set; NCEI record for the video collection not read). https://www.ncei.noaa.gov/access/ocean-exploration/video/
- geo: segment, geo_source = OneStop granule attributes.spatialBounding (Polygon centre), geo_inferred true, uncertainty = half box diagonal (about 35 m on the one sampled box). Granules without a polygon get geo none.
- files: src/aquasource/adapters/noaa_oe.py / scripts/download/noaa_oe.sh / tests/test_noaa_oe.py / no sites csv (no publication coordinates used)
- tests: pass (12/12, `uv run --with pytest pytest tests/test_noaa_oe.py -q`; plain `uv run pytest` fails here, pytest is not in the default env)
- sample: 3 files downloaded OK, 0 errors (budget 3, 204 MB, sha256 recorded; run took 871 s, the 900 s timeout cut nothing)
- doubts:
  - Licence is read at collection level only: check the ISO / landing record of the video collection for an explicit statement (not the mapping accession 0310923 I used).
  - spatialBounding exists on only some granules (1 of 3 in the fixture); it is a box around the segment, not a published point.
  - Depth is empty for every segment (description says "between 0.0 m and 0.0 m"); ROV dive nav / event logs on the cruise page may hold depth (not used).
  - LAUNCH / RECOVERY / PTROBO / SBROBO / CPHD clips are flagged extra.maybe_not_underwater; not checked by pixels.
  - Budget picks newest granules first: the sample is 3 recovery clips, all flagged maybe_not_underwater.
- needs_opus: no
- checked by Sonnet 2026-10-08 (tests 12/12, licence page reachable, geo/licence code ok; re-run sample cut at 590 s with 2 mp4 because host is slow, dry-run ok)

## Summary
NOAA Ocean Exploration (OER) ROV and camera video from the Okeanos Explorer dives since 2013. The public portal
https://www.ncei.noaa.gov/access/ocean-exploration/video/ searches the OneStop granule index of data.noaa.gov (project
`NOAAOceanExploration`, about 112,060 granules on 2026-10-08, 1,121 pages of 100). A granule is one video segment of about
5 minutes of one camera of one dive, id `fileIdentifier` (e.g. `EX2503_DIVE16_20250501T025000Z_ROVHD`).

## Access (metadata only, verified 2026-10-08)
- Index: `POST https://data.noaa.gov/onestop/api/search/search/granule`, JSON body `{queries, filters, sort, page:{max,offset}}`.
  Filters used: facet `projects` = `["NOAAOceanExploration"]`, facet `dataFormats` (the portal's three names), optional
  `datetime` {after, before}. Answer: `meta.total`, `data[].attributes` (fileIdentifier, title, description, beginDate,
  links, spatialBounding, gcmdLocations, citeAsStatements).
- Media: low-res MP4, `https://www.ncei.noaa.gov/data/oceans/oer/video/<CRUISE>/Video/<CRUISE>_DIVE<NN>_<date>/Compressed/<CRUISE>_VID_<time>Z_<CAMERA>_Low.mp4`
  (360P H.264, about 1.5 Mbit/s, about 56 MB per 5 min). Apache directory listings, Range supported.
- Not used: high-res ProRes .mov (oerkey page), `Imagery/` JPG frames, `Still_Cam_Imagery/`, `Products/HighlightVideo`.
- Cruise landing pages (cite, dive tracks, nav data): `https://www.ncei.noaa.gov/waf/okeanos-rov-cruises/<cruise>/`
  (e.g. ex2503: "Submersible Navigation/Sensor Data (ASCII)", "ROV Dive Event Logs", "Low-Resolution Video Clips (Zip - 14 GB)"
  on an FTP server, DOI 10.25923/zmec-b493).
- Size: whole project many TB; one 5-min low-res segment about 56 MB. No token, no account.

## Licence
- Read at collection level. No per-granule licence field; the OneStop record says "Cite this video data segment by using the
  citation from the cruise" (`citeAsStatements`). The cruise ISO for the mapping accession 0310923 (EX2507) says
  `accessLevel: public`, "This dataset is available to the public for a wide variety of uses including scientific research
  and analysis", and gives a NCEI "Cite as". No NC / ND / research-only term anywhere (checked: OneStop text search
  "copyright" returns 0 granules).
- NOAA federal works are US government works (17 U.S.C. 105): public domain, tier A (same reading as noaa_ncrmp.md).
  The NOAA disclaimer page (noaa.gov/disclaimer.html) answers 403 to this client and was not read.
- Adapter rule: a granule text with "copyright", "all rights reserved" or the copyright sign becomes tier U (not yielded).

## Geolocation
- Granule `attributes.spatialBounding`: GeoJSON Polygon (5 corners, WGS 84), present on some granules only. Fixture record
  `EX2503_DIVE16_20250501T024928Z_CRROBO_RECOVERY`: lon -172.53944 .. -172.53876, lat 23.449327 .. 23.449437 (Paul Seamount, NW Hawaii).
  Two other fixture granules of the same dive (ROVHD 02:50:00, ROVAUX1 02:49:38) have no polygon -> geo none.
- Lat / lon = centre of the box, precision `segment`, `geo_inferred` true, `geo_uncertainty_m` = half the diagonal.
- Depth: the description reads "... at Paul Seamount between 0.0 m and 0.0 m" for every fixture granule: a placeholder, so
  `depth_m` stays empty; a non-zero "between A m and B m" is averaged.
- Not used: `gcmdLocations` (names only, e.g. "Paul Seamount"): no coordinates are invented from names.
- Dive-level nav (ship and ROV navigation ASCII files on the cruise pages) could give a finer track per segment; not done here.

## Fixtures (tests/fixtures/noaa_oe/)
- `onestop_granules.json`: real OneStop answer (page offset 0, max 3, filters as above, 2026-10-08). 3 granules of EX2503 DIVE16.
- `licence.txt`: quoted ISO access constraints (EX2507 0310923) and the granule citeAsStatements.
- SOURCE.md with URLs.

## Adapter (src/aquasource/adapters/noaa_oe.py)
- Paging with `page.offset` / `page.max` (100), sort `beginDate` desc; each index answer cached under metadata/raw/search/.
- Candidates: granules with a `.mp4` link (prefers `_Low.mp4`). Item id = `fileIdentifier`. Granules without MP4 are counted as
  skipped (`no mp4 link`).
- Options: `from`, `to` (ISO dates, datetime filter on the index), `pages` (max index pages), `page_max` (<= 100).
- `extra`: cruise, dive, locations, instruments, description, maybe_not_underwater (LAUNCH / RECOVERY / PTROBO / SBROBO / CPHD /
  Still_Cam in the id), portal_key (oerkey link).
- `estimate()` = one index request (total granules).

## Sample (2026-10-08, `--budget 3`, scratch dir removed afterwards)
- 3 of 11 candidates selected, all 3 downloaded: 65.1, 71.7, 67.1 MB MP4 (EX2503 DIVE16, CRROBO_RECOVERY segments).
- geo: segment, lat about 23.449, lon about -172.540 .. -172.539, uncertainty 24-35 m, depth empty. 8 candidates without a
  polygon were dropped (no geolocation).
- All 3 selected are flagged maybe_not_underwater (recovery clips): newest-first order, so a small budget samples the
  recovery segments of the last dive; use from/to or pages to spread the sample.
- Download rate of the NCEI host about 0.3 MB/s on this machine: about 4 min per segment.

## Open questions / next steps
- Find the explicit licence statement of the OER video collection (NCEI record of the video portal or the cruise DOI) and
  confirm tier A at record level.
- Decide whether to use the cruise nav files for per-segment depth and a finer position.
- Pixel-level filters (deck, surface, black frames) are not done: `maybe_not_underwater` is only a name marker.
