## HANDOFF
- status: ok (scope: one record, 10.17882/101899; other SEANOE image/video records not yet adapted)
- tier + licence: B, CC BY 4.0, record level (https://www.seanoe.org/data/00907/101899/ licence badge; DataCite rights https://api.datacite.org/dois/10.17882/101899)
- geo: fixed_site, inferred; geo_source = DataCite geoLocationBox per observatory (src/aquasource/adapters/sites/seanoe_more.csv), camera from file-name prefix
- files: src/aquasource/adapters/seanoe_more.py / scripts/download/seanoe_more.sh / tests/test_seanoe_more.py / src/aquasource/adapters/sites/seanoe_more.csv (+ tests/fixtures/seanoe_more/)
- tests: pass (10 passed, offline); checked by Sonnet 2026-10-08: licence CC BY 4.0 confirmed (DataCite), geo code OK, sample 3 JPEG + samples.jsonl OK
- sample: 3 of 3 JPEG downloaded OK (budget 3, ~6.7 s, 4 metadata requests; header + end markers FFD8/FFD9 checked; sample dir removed)
- doubts:
  - Juan de Fuca point (48.503038 N, -125.554305) is the second DataCite box; the record names no site in words (README only says "TEMPO for Juan de Fuca"). Check against the paper / TEMPO deployment list.
  - Frame timestamps are taken as UTC from the file name (README gives no time zone).
  - MOMAR (Azores) point 37.2933, -32.2733 is about 0.5 km from the SMOOVE camera (37.2889, -32.2756); both are publication-derived, no uncertainty published.
  - Citizen labels (cleaned/expert CSV in the archive) are not loaded; some frames may be dark or show no animal (kept, not flagged).
  - Single 799 MB archive is read by Range requests: about 3 requests once for the central directory, then 1 request per frame (at 1 req/s, a full run takes about 1.1 h of request time).
- needs_opus: yes, publication-derived geo for the TEMPO camera is assigned by elimination of the two DataCite boxes and not verified against a second source.

---

# seanoe_more: SEANOE underwater images beyond SMOOVE

Scope note: `seanoe_more` was seeded as "SEANOE imagery beyond SMOOVE". SMOOVE (10.17882/101838 and siblings) is already the `emso_azores` adapter, so it is excluded here. This pass adapts one record and lists the others.

## Access and method
- Search: no SEANOE REST search. Metadata via DataCite (`https://api.datacite.org/dois?client-id=euvi.seanoe&query=...`, client id `euvi.seanoe`; 2120 SEANOE DOIs). The SEANOE OAI-PMH endpoint has moved to DataCite (`https://oai.datacite.org/oai/?verb=ListRecords&metadataPrefix=datacite&set=EUVI.SEANOE`).
- Landing pages: `https://www.seanoe.org/data/<group>/<id>/` list files with direct links `.../data/<fileid>.<ext>`.
- Media: HTTP Range supported on the SEANOE file host (verified for 115473.zip, 206 responses).

## Record used: 10.17882/101899
"Deep-sea observatories images labeled by citizen for object detection algorithms" (Lebeaud, Tosello, Borremans, Matabos; 2024).
- Archive `https://www.seanoe.org/data/00907/101899/data/115473.zip`, 798,707,675 bytes, 3,987 entries: 3,979 JPEG under `dataset_seanoe_101899/images/Images/`, two CSV label sets (raw/cleaned/expert annotations), README.md, two YOLOv8 `.pt` models.
- Frame names: `CAM-TEMPO-MINI-2_<YYYYMMDDHHMMSS>.jpg` (3,403; README: TEMPO, Juan de Fuca) and `MOMAR_<YYYYMMDDHHMMSS>.jpg` (576; README: MOMAR, Azores). Frames are 150-220 KB each.
- Geo: DataCite geoLocationBox x2 (point boxes): (48.503038, -125.554305) and (37.2933, -32.2733). The Azores point matches the observatory; the other is assigned to TEMPO by elimination.
- Licence: CC BY 4.0 on the landing page (badge `https://creativecommons.org/licenses/by/4.0/`) and in DataCite rights. No file-level licence in the archive README.

## Method (adapter)
- discover: reads the zip central directory with Range requests (`zipfile` over an HTTP reader, 3 requests), cached in `metadata/raw/seanoe_more/101899_entries.json`. One candidate per JPEG under the Images folder. CSVs and models are not media.
- fetch_media: one Range request per frame (local header + data, 1 KB header room), inflates deflate (method 8) or copies stored (0), checks the local name and size, writes atomically, sha256.
- Options: `cameras=CAM-TEMPO-MINI-2,MOMAR`, `per_day=N`.

## Other SEANOE image/video records found (not adapted)
Same licence family unless noted. Sizes from the landing pages.
- 10.17882/113745 GEOFLAMME ROV Victor 6000 videos (Mayotte), CC BY, one zip 70 GB (stated), coordinates ambiguous (hemisphere letters mixed).
- 10.17882/109763 HOLOTVSPM2025 underwater videos (Saint-Pierre-et-Miquelon), CC BY, one zip 35 GB; coordinates have sign errors on the page.
- 10.17882/103869 MoMARSAT2023 black smoker HD video, CC BY, one mp4 6 GB; coordinates contradictory on the page (37.17 N and S).
- 10.17882/87389 TEMPO screenshots (Lucky Strike), CC BY, 720 MB RAR (no range extraction tool here) plus 1 GB RAR of transformed images; coordinates contradictory.
- 10.17882/76019 FAROFA underwater video observations (Brazil), CC BY, CSV annotations only (242 MB); no media.
- 10.17882/84672 TEMPO annotations (Lucky Strike), CC BY, annotations on screenshots; the screenshots are in 87389.
- Excluded for NC/ND: 10.17882/79218, 96475, 95808, 99108 (NC-SA), 96266 (NC), 97987 (NC-ND), most plankton imaging sets (NC). 105884 and 105883 (3D models, CC BY) have no per-image positions.

## Next steps (not done)
- Adapt the next CC BY record if it has range-readable archives, starting with 113745 or 109763 (large; needs a budget).
- Check the TEMPO camera coordinate against the TEMPO / Juan de Fuca deployment list (see needs_opus).

## Commands
- Sample: `AQUASOURCE_DATA_ROOT=/tmp/aquasource_scratch/sample_seanoe_more uv run aquasource download seanoe_more --budget 3`
- Tests: `uv run pytest tests/test_seanoe_more.py -q`
