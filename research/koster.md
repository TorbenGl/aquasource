## HANDOFF
- status: blocked
- tier + licence: U (not upgraded). SND ROV series snd1069-* shows only a URL https://creativecommons.org/licenses/by/4.0/ (no licence name) and creativeWorkStatus WITHDRAWN, while accessRights say openAccess (https://researchdata.se/en/catalogue/dataset/snd1069-5). KSO observatory archive: no licence found anywhere.
- geo: none confirmed. Candidate station (publication coordinate only) would be fixed_site/station; not usable until the deposit is confirmed.
- files: adapter none / script scripts/download/koster.sh (exits 1, prints why) / test none / sites csv none / fixtures tests/fixtures/koster/ (snd1069-5.html, SOURCE.md)
- tests: n/a (no adapter; nothing to test offline)
- sample: 0 files, not run (blocked before any media endpoint was found)
- doubts:
  - The observatory footage (3000+ h, Zooniverse KSO) has no found open deposit; project page says "out of data at the moment", restructuring
  - SND snd1069-5 and snd1069-4: CC BY URL vs WITHDRAWN status conflict; check on snd.se whether the record is live
  - researchdata.se snd1069-3 notice says the data are no longer available there (possible move to snd.se, unverified)
  - SND ROV dives (1999-2007) are campaign footage, not the observatory archive; file count and size unknown
  - BDJ 10.3897/BDJ.9.e60548 'Usage licence' text not retrieved (page body missing in fetch)
- retry 2026-10-08 (Sonnet): Zenodo (only BDJ figures/PDF + model 13589902 + Nilsson 2025 PDF, all CC BY, no media), GitHub org ocean-data-factory-sweden (kso, kso-utils: code only, sample footage on Google Drive, no licence), GBIF 51d0bd32 (CC BY 4.0, occurrences only, no media), snd.se snd1069-5 still WITHDRAWN with 'no longer available'; no newer version found. Still blocked.
- human must check: ask Tjarno Marine Lab (Lundalv/Univ. Gothenburg) or Wildlife.ai (Anton) for the Koster ROV 1997-2023 video archive and its licence; or ask SND whether snd1069 was re-published.
- needs_opus: no (needs human), was: licence contradiction (CC BY URL vs WITHDRAWN) and no reachable KSO licence or deposit; needs a human to contact Tjarnö Marine Lab / Sven Lovén Centre (Lundälv) or the KSO team (Obst, Anton) for permission.

## Summary
Koster Seafloor Observatory (Kosterhavet National Park, Skagerrak, Sweden, about 58.9 N 11.0 E) publishes snapshots of
observatory video via Zooniverse (project victorav/the-koster-seafloor-observatory). Project status: "out of data at the
moment", re-structuring, footage to return "in a few months". Obst/Anton BDJ 2021 (10.3897/BDJ.9.e60548) describes the
software pipeline. Related open data that does NOT contain the media: EurOBIS / GBIF "Koster historical biodiversity
assessment" (CC BY 4.0, species occurrences from ROV video of 70 transects, 7-105 m; "original videos archived at Tjärnö").
No GitHub repo "ocean-data-factory-sweden/koster" was found.

## Access (read 2026-10-08, metadata only)
- SND (Swedish National Data Service, Tomas Lundälv, Sven Lovén Centre, Univ. Gothenburg): snd1069-1..5 ROV image and movie
  dives 1999-2007 around the Koster islands (snd1069-5 KH60 2007-11-15; snd1069-4 KH54 2007-10-04; snd1069-3 KH52; snd1069-2
  Pockmark Bratten; snd1069-1 Hamnero). No file list, size or download route in the record.
- The Zooniverse "Collect" tab is the only public route to observatory frames; no download link or licence stated.
- Not checked: Zenodo, GBIF media, SND download API (no file endpoint found, so no sample could be run).

## Geo
Only publication-level centroids exist (SND snd1069-5 centroid 58.89997 N, 10.90247 E; snd1069-4 58.64804 N, 11.01668 E).
Not used: they are campaign centroids, not observatory positions. Nothing added to sites/ yet.

## Not done
- No adapter, no sample, no tests (no media endpoint, licence unresolved). Notion/commit steps follow this status.
