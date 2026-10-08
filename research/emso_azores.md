## HANDOFF
- status: ok
- tier + licence: B, CC BY 4.0, read at record level (JSON-LD `license` and licence icon on https://www.seanoe.org/data/00906/101838/; same on the other SMOOVE records)
- geo: fixed_site, geo_source = publication Position 37 deg 17.334 N, 32 deg 16.534 W (= 37.2889, -32.275567), depth 1695 m (src/aquasource/adapters/sites/emso_azores.csv); inferred, no uncertainty published
- files: adapter src/aquasource/adapters/emso_azores.py / script scripts/download/emso_azores.sh / test tests/test_emso_azores.py / sites csv src/aquasource/adapters/sites/emso_azores.csv
- tests: pass (uv run pytest tests/test_emso_azores.py -q)
- sample: 1 file downloaded OK (SMOOVE-23-07-26_09-59-24-00.mkv, 1219167490 B, EBML magic ok, 1 samples.jsonl row); ~0.46 MB/s, 44 min; 3-file budget not run (time)
- doubts:
  - seed said "CC BY 4.0 (verify)": verified. "FP7/H2020 FIXO3, iAtlantic" on the page is funding, not licence.
  - Members are .mkv (about 1.2 GB per 10-min video), not mp4. Timestamp parsed from name YY-MM-DD_HH-MM-SS (assumed UTC); trailing -00 unexplained.
  - Resume-after-interrupt fix in fetch_media was added after the sample; sample used the restart path. Recheck with a kill/resume.
  - Dataset 2024-2025 (SEANOE 01073/114442, 52 videos, DOI not resolved) is NOT in the adapter: landing page showed no tar/licence; check if it is public.
  - Period 2014-2015 has no record; not a gap in the adapter.
  - Tar range reads: 10 records x 1-2 tars, ~250 GB total; member header walk is about 1 request per video on first discover (cached). Full run is very long at this throughput.
- needs_opus: no

## Details
- Source: SEANOE, EMSO-Azores SMOOVE video (camera on TEMPO module, Lucky Strike vent field, 1695 m), 10-minute 1080p videos.
- Records (DOI -> period -> tars): 48592 2013-14 (48926.tar); 48594 2015-16 (48928.tar); 51551 2016-17 (52158.tar); 83937 2017-18 (88867, 88868); 83946 2018-19 (88871, 88872); 83947 2019-20 (88873, 88874); 83948 2020-21 (88875, 88876); 101828 2021-22 (112943, 112944); 101834 2022-23 (112941, 112942); 101838 2023-24 (112940, 56 GB).
- Access: open, no token. Tars are plain ustar with HTTP Range support (Content-Length known). Adapter reads headers with Range, fetches each video by one Range request.
- Politeness: metadata only during research; 1 request/s to www.seanoe.org. SEANOE blocked the IP for about 40 min after repeated requests; the sample run had no failures.
- Fixtures: tests/fixtures/emso_azores/SOURCE.md and smoove_records.json.
