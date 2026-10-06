# DeepSea MOT (`deepsea_mot`)
Status: researched · researched 2026-10-06

## Summary
DeepSea MOT is MBARI's multi-object-tracking benchmark (Barnard et al. 2025, arXiv:2509.03499), published on Hugging Face as `MBARI-org/DeepSea-MOT`.
- **Contents:** 11 short annotated deep-sea video clips with every frame extracted as JPEG. Ten clips are unique: `MD_CLS` is a byte-identical copy of `MD_CAN`.
  - The four original 1080p MBARI ROV *Ventana* clips: BD, BS, MWD, MWS.
  - Two MBARI 4K clips added 2025-12-08: BS_4K, MWS_4K.
  - Five marine-debris clips added 2026-02-18: three from MBARI (MD_ROP, MD_CAN, MD_CLS) and two from IFREMER (MD_BTL, MD_FLN).
- **Size:** 6,598 frames (5,998 unique) and 11 videos, about 2 minutes of footage, 18.46 GB (15.05 GB unique).
- **Licence:** CC BY-SA 4.0 at record level, so tier **C** (share-alike shard).
- **Geo:** no media file carries any coordinate.
  - Git history and the authors' notebook give the source video file of the four original clips: Ventana dives V4277, V4289, V4432 and V4455, with UTC start times.
  - FathomNet framegrab nav fixes from the same dives place BD and BS at **station** precision (1 km and 2 km).
  - MWD and MWS have no public nav, so they get a **region** anchor at MBARI's published "Midwater One" site (±30 km).
  - The seven newer clips cannot be tied to any dive and get **none**.
- **Verdict:** usable but tiny and highly redundant (about 128 distinct seconds). It is worth a small CC BY-SA shard, mainly the 1080p and 4K ProRes clips.

## Entry points
- Dataset: https://huggingface.co/datasets/MBARI-org/DeepSea-MOT
  - Current revision `61ecbda8acb2749f3771d7192c51341267da2f37` (2026-02-18). Not gated.
- HF API:
  - `https://huggingface.co/api/datasets/MBARI-org/DeepSea-MOT` (card data, siblings)
  - `.../tree/main/<path>` (listing; paginated by `Link: rel="next"`, 1,000 entries per page)
  - `.../commits/main` (12 commits)
- File URL: `https://huggingface.co/datasets/MBARI-org/DeepSea-MOT/resolve/<rev>/data/<SEQ>/<file>`
  - Large files answer 302 → `us.aws.cdn.hf.co/xet-bridge-us/...`; small files answer 307 → `/api/resolve-cache/...`.
- Paper: Barnard, Liu, Walz, Schlining, Stout, Lundsten (2025), "DeepSea MOT: A benchmark dataset for multi-object tracking on deep-sea video", arXiv:2509.03499, doi:10.48550/arXiv.2509.03499. The paper itself is CC BY-SA 4.0. Only v1 (3 Sep 2025) exists, and it describes only the 4 original sequences.
- Code and workflow: https://github.com/mbari-org/benchmark_eval (MIT, a TrackEval fork) and https://docs.mbari.org/benchmark_eval/. The notebook `tracker_output.ipynb` holds the source video file names.
- Intern report (same content): https://www.mbari.org/wp-content/uploads/Elaine_Liu.pdf
- Geo helper sources:
  - FathomNet API `https://database.fathomnet.org/api/geoimages/query` (POST) and `/api/images/{uuid}`
  - Robison et al. 2017, *Oceanography* 30(4):26–37, doi:10.5670/oceanog.2017.421

## Licence
- Tier: **C** (CC BY-SA 4.0)
- Licence text (quote) + level read (file / record / collection) + URL:
  - **Record level**, from the dataset card YAML at https://huggingface.co/datasets/MBARI-org/DeepSea-MOT/raw/main/README.md: `license: cc-by-sa-4.0`. The HF API `cardData.license` reads `"cc-by-sa-4.0"`, and the tag is `license:cc-by-sa-4.0` (fixture `README.md`).
  - **History:** the first commits (2025-08-29 to 2025-09-03, e.g. `730557577d`, `48a1ff9d5d`) had `license: mit`. Commit `96dea361cc` (2025-09-03, "update license to cc-by-sa-4.0") changed it, and it has been unchanged since. We use the current licence and pin the revision.
  - **File level:** none. The JPEG EXIF holds only an ExifIFD pointer plus an ICC profile ("Copyright 2007 Apple Inc." belongs to the colour profile). The MOV `moov` metadata has no rights field.
  - **Paper:** arXiv abs page, "Rights to this article" → http://creativecommons.org/licenses/by-sa/4.0/. This is consistent.
  - **Code:** the GitHub repo is MIT (inherited from TrackEval). It covers only the code.
  - **Related products under different terms:** MBARI framegrabs on FathomNet are `CC-BY-NC-ND-4.0`. That is a different product, and we use only coordinate facts from it, so it does not contradict this record.
- Attribution / citation text to store with every sample:
  `Barnard K., Liu E., Walz K., Schlining B., Stout N.J., Lundsten L. (2025). DeepSea MOT: A benchmark dataset for multi-object tracking on deep-sea video. arXiv:2509.03499. Data: huggingface.co/datasets/MBARI-org/DeepSea-MOT (rev 61ecbda8). © MBARI (MD_BTL, MD_FLN collected by IFREMER). CC BY-SA 4.0.`
- Embargo / moratorium / special terms:
  - None: not gated, no login.
  - Share-alike: derived shards must stay CC BY-SA.
  - The IFREMER clips (MD_BTL, MD_FLN) are released under MBARI's CC BY-SA statement. No separate IFREMER licence is given (see risks).

## Media
- **Per sequence** (folder `data/<SEQ>/`; from the HF tree, `seqinfo.ini` and Range reads of the `moov` atoms):

| SEQ | Source | Video file | Codec | Resolution / fps | Duration | Frames (JPG) | Size (video + jpg) |
|---|---|---|---|---|---|---|---|
| BD | Ventana V4277 | BD.mov | H.264 | 1920×1080 / 29.97 | 20.0 s | 600 | 27.6 MB + 195 MB |
| BS | Ventana V4289 | BS.mov | H.264 | 1920×1080 / 59.94 | 10.0 s | 600 | 20.3 MB + 193 MB |
| MWD | Ventana V4432 | MWD.mov | ProRes 422 HQ | 1920×1080 / 59.94 | 10.0 s | 600 | 585 MB + 220 MB |
| MWS | Ventana V4455 | MWS.mov | ProRes 422 HQ | 1920×1080 / 59.94 | 10.0 s | 600 | 599 MB + 301 MB |
| BS_4K | MBARI, dive unknown | BS_4K.mov | ProRes 422 HQ | 3840×2160 / 59.94 | 10.0 s | 599 | 2,241 MB + 1,244 MB |
| MWS_4K | MBARI, dive unknown | MWS_4K.mov | ProRes 422 HQ | 3840×2160 / 59.94 | 10.0 s | 599 | 2,343 MB + 535 MB |
| MD_ROP | MBARI, dive unknown | MD_ROP.mov | ProRes 422 HQ (+tmcd) | 3840×2160 / 59.94 | 10.0 s | 600 | 2,184 MB + 733 MB |
| MD_CAN | MBARI, dive unknown | MD_CAN.mov | ProRes 422 HQ | 3840×2160 / 59.94 | 10.0 s | 600 | 2,233 MB + 1,166 MB |
| MD_CLS | **duplicate of MD_CAN** | MD_CLS.mov | same bytes | — | — | 600 | 2,233 MB + 1,166 MB |
| MD_BTL | IFREMER, unknown | MD_BTL.mp4 | H.264 | 1920×1080 / 25 | 24.0 s | 600 | 10.3 MB + 88 MB |
| MD_FLN | IFREMER, unknown | MD_FLN.mp4 | H.264 | 1920×1080 / 25 | 24.0 s | 600 | 8.3 MB + 81 MB |

- **Totals:**
  - 6,598 JPEG frames (5,998 unique) and 11 videos (10 unique, about 128 s), 18.46 GB in total.
  - Annotation sidecars per sequence: `gt.txt` (MOT Challenge `frame, id, x, y, w, h, -1, -1, -1`; for MD_* it sits in `gt/gt.txt`), `labels/*.txt` (YOLO + track id), `xml/*.xml` (Pascal VOC from RectLabel) and `seqinfo.ini`.
  - The original four have 57,376 boxes in 188 tracks (paper Table I).
- **Time range of footage:** 2020-02-19 (V4277), 2020-07-29 (V4289), 2022-09-14 (V4432), 2022-11-30 (V4455). The 4K and MD clips are undated: their MOV creation times are 2025 export dates, and the MD_ROP timecode starts at 00:00:00:00.
- **Frames vs videos:** the JPEGs are every frame of the clip (RectLabel "Convert video to image frames"), so images and videos hold the same content. Consecutive frames at 60 fps are near-identical.
- **Filters needed:**
  - All footage is in-water ROV video, with no aerial or on-deck shots expected.
  - Apply a dark or blue-water frame check: MWD is filmed while "the ROV descended through the midwater depths" (paper), and midwater frames are mostly empty blue with marine snow.
  - Drop `MD_CLS` entirely. Its LFS sha256 `54ac8379…a15a5` equals MD_CAN's, and all 600 images and `gt.txt` are identical. The README promises a different "MD_CLS" sequence.
  - Stray `.DS_Store` files sit in the MD_* folders and must be ignored.
  - `MD_BTL` has 600 JPGs although `seqLength=601`, with 374 label files and 597 XMLs. The frame numbering is 001–601 with one gap.
  - **Overlap with FathomNet** (catalog key `fathomnet`): FathomNet holds MBARI VARS framegrabs from the same dives. FathomNet image `207ab015-c8db-4060-b681-2590d8a9b12d` (Ventana 4277, 2020-02-19T21:20:12Z, Funiculina field) very probably shows the same scene as BD, from inside the BD source file's time window. Store `origin_url = https://huggingface.co/datasets/MBARI-org/DeepSea-MOT/resolve/61ecbda8acb2749f3771d7192c51341267da2f37/data/<SEQ>/<file>` plus `source_video = V4277_20200219T211238Z` etc., and dedup with perceptual hashes against FathomNet Ventana 4277/4289.
  - BS_4K and MWS_4K may or may not come from the same dives as BS and MWS. Their annotated taxa differ (BS_4K: Asteroidea, *Stylasterias forreri*; MWS_4K: *Nanomia bijuga*, *Vitreosalpa gemini*), so they are probably different clips.

## Geolocation
- **Precision levels** (share of the 5,998 unique frames, or of the 10 unique videos):

| Level | Sequences | Frames | Videos | Notes |
|---|---|---|---|---|
| station | BD, BS | 1,200 (20 %) | 2 | ±1 km and ±2 km |
| region | MWD, MWS | 1,200 (20 %) | 2 | ±30 km around Midwater One |
| none | BS_4K, MWS_4K, MD_ROP, MD_CAN, MD_BTL, MD_FLN (and duplicate MD_CLS) | 3,598 (60 %) | 6 | no source dive identified |

  No sample reaches image or segment precision: no per-frame nav is public, and the clip offset inside the source file is unknown.
- **geo_source**, chained per sequence:
  1. **Sequence → source video file.**
     - HF commit `2163f4bdd0` held the original RectLabel names, for example `data/BD/xml/BD_001.xml` `<filename>Benthic_1_V4277_20200219T211238Z_1.jpg</filename>`. Commit `4e0b079c39` "fix XML filename tags" removed them.
     - The same names appear in `mbari-org/benchmark_eval/tracker_output.ipynb` `video_paths`: BD=`Benthic_1_V4277_20200219T211238Z.mov`, BS=`10s_Benthic_2_V4289_20200729T185027Z.mov`, MWD=`Midwater_difficult_V4432_20220914T160635Z_prores.mov`, MWS=`Midwater_simple_V4455_20221130T192123Z_prores.mov`.
     - Reading the name: `V`=*Ventana*, then the dive number, then the UTC start of the source file.
  2. **Dive → coordinate.**
     - **BD:** FathomNet geoimage fields `latitude`, `longitude`, `depthMeters`, `timestamp`.
       - Source: FathomNet image `207ab015-c8db-4060-b681-2590d8a9b12d`, 2020-02-19T21:20:12.646Z, 7.6 min after the file start, 36.751029 / -122.187046, 764.85 m.
       - Uncertainty 1,000 m. The dive's bottom fixes drift about 0.5 km per 40 min, and Ventana files appear to be about 15-minute segments (see SOURCE.md).
     - **BS:** FathomNet `f86584c5-f35d-4bd0-a215-69d8fbb27cae`, 2020-07-29T19:53:13.382Z, 63 min after the file start, 36.694707 / -122.00259, 399.53 m. Uncertainty 2,000 m; the depth is approximate.
     - **MWD and MWS:** there is no public nav.
       - FathomNet has no 2022 Monterey imagery, OBIS has nothing, and MBARI M3 (`m3.shore.mbari.org`) refused the connection.
       - Region anchor from Robison et al. 2017, *Oceanography* 30(4) p.27–28: "Our principal midwater dive site (Midwater One, at 36°42'N, 122°02'W)". Ventana runs day trips from Moss Landing.
       - lat/lon 36.7 / -122.033333, `depth_m` null, uncertainty 30,000 m.
- **CRS:** WGS 84 decimal degrees (FathomNet), and degrees-minutes from the paper converted to decimal.
- **Depth:** `depth_m` comes from FathomNet `depthMeters` for BD and BS, and is null otherwise. The midwater clips span unknown depths, and the paper says only "˜100 m to many kilometers".
- **How a sample maps to its coordinate:** use the sequence folder in the HF path, `data/<SEQ>/...`. `<SEQ>` equals `site_id` in `tests/fixtures/deepsea_mot/publication_sites.csv` (rows BD, BS, MWD, MWS). Every frame and the video of that sequence get the same coordinate (`geo_inferred=true`).

### resolve_geo recipe
Input: one record that carries an HF path, for example an entry of `hf_tree_data.json` (`{"type":"directory","path":"data/BD",...}`), a media path `data/BD/images/BD_001.jpg`, or `data/MWS/MWS.mov`. Also needed: `publication_sites.csv`.
1. Take `path` (or the path part of the origin URL after `/resolve/<rev>/`). Match `^data/(?P<seq>[A-Z0-9_]+)(?:/|$)`.
   - No match, or `seq` not one of the 11 known sequences → step 5.
2. If `seq == "MD_CLS"`, flag it as a duplicate of MD_CAN. The pipeline should skip it; for geo, continue as MD_CAN, which falls to step 5.
3. Look up `site = sites.get(seq)`, where `site_id` equals the sequence code.
   - If it is missing (BS_4K, MWS_4K, MD_ROP, MD_CAN, MD_BTL, MD_FLN), go to step 5.
4. Return:
   - `lat = site.lat`, `lon = site.lon`
   - `depth_m = site.depth_m`: 764.85 for BD, 399.53 for BS, None for MWD and MWS
   - `geo_precision = "station" if site.uncertainty_m <= 5000 else "region"`: BD and BS are station, MWD and MWS are region
   - `geo_source = "publication-derived: " + site.source`, which cites the HF XML revision, the notebook, the FathomNet uuid or the Robison 2017 DOI and page
   - `geo_inferred = True`
   - `geo_uncertainty_m = site.uncertainty_m`: 1000, 2000 or 30000
   - Optional cross-check, if the record is a pre-fix XML (fixture `BD_001_rev2163f4bdd0.xml`): `re.search(r"_V(\d{4})_(\d{8}T\d{6}Z)", filename)` must give the dive in `site.source`, for example `4277` for BD. If it does not match, return none.
5. None: `lat=None, lon=None, depth_m=None, geo_precision="none", geo_source="none", geo_inferred=False, geo_uncertainty_m=None`.
6. Never interpolate per frame. The clip's offset inside the source file is unknown, so segment precision is impossible.
   - If MBARI later publishes the clip start timecodes and per-dive nav, BD, BS, MWD and MWS could be upgraded to `segment` by interpolating nav at `file_start + clip_offset + frame/fps`.

## Access & download recipe
- **Enumeration:**
  - `GET https://huggingface.co/api/datasets/MBARI-org/DeepSea-MOT/tree/<rev>/data` lists the 11 sequence dirs.
  - Per sequence, `GET .../tree/<rev>/data/<SEQ>` gives the video, `gt.txt`, `seqinfo.ini` and subdirs. `GET .../tree/<rev>/data/<SEQ>/images` gives 599–600 entries in one page.
  - Alternatively, `?recursive=true` returns 19,665 entries over 20 pages via the `Link` header.
  - The tree entries carry `size`, plus `lfs.oid` (sha256) for videos and images.
  - No auth is needed. Anonymous HF limits apply, so stay at 1 request/s or less and back off on 429.
- **Fetch one file:** `curl -L -A "$UA" -o BD_001.jpg https://huggingface.co/datasets/MBARI-org/DeepSea-MOT/resolve/61ecbda8acb2749f3771d7192c51341267da2f37/data/BD/images/BD_001.jpg`.
  - The resolve URL returns `accept-ranges: bytes`, `x-linked-size` and `x-linked-etag` (the sha256), then redirects to the CDN.
  - Range requests work (206 verified), so `curl -C -` resumes.
  - Alternatives: `huggingface-cli download MBARI-org/DeepSea-MOT --repo-type dataset --revision 61ecbda8… --include "data/BD/*"`, or `hf_hub_download`.
  - Layout:
    - `<data_root>/deepsea_mot/videos/<SEQ>.<mov|mp4>`
    - `<data_root>/deepsea_mot/images/<SEQ>/<SEQ>_NNN.jpg`
    - `<data_root>/deepsea_mot/metadata/<SEQ>/{gt.txt,seqinfo.ini}` plus `README.md`
- **Sampling for a budget of N:** there are only about 128 distinct seconds of footage, so diversity saturates fast.
  - Skip `MD_CLS`.
  - Spread N round-robin over the 10 unique sequences, geolocated first (BD, BS, MWD, MWS) when the run requires geo.
  - Within a sequence, take frames at 1 fps or slower: every 60th frame at 59.94 fps, every 30th for BD, every 25th for MD_BTL and MD_FLN. That gives at most 10–24 frames per sequence, about 130 frames in all. Beyond that, add only perceptual-hash-distinct frames.
  - Videos: all 10 unique files are 10.25 GB. The 1080p subset (BD, BS, MWD, MWS, MD_BTL, MD_FLN) is 1.25 GB.

## Manual steps (human)
- None.
- Optional, to improve geo: ask the curators (HF discussion on `MBARI-org/DeepSea-MOT`, or the MBARI Video Lab) for three things:
  - the dive IDs and timecodes of BS_4K, MWS_4K, MD_ROP, MD_CAN and MD_CLS, and IFREMER's dive or site for MD_BTL and MD_FLN;
  - ROV nav for Ventana V4432 and V4455;
  - whether MD_CLS was uploaded by mistake.

## Fixtures
- `tests/fixtures/deepsea_mot/README.md`: HF dataset card, unmodified (licence `cc-by-sa-4.0`, structure, citation).
- `tests/fixtures/deepsea_mot/hf_tree_data.json`: HF tree API listing of `data/` (11 sequence dirs), unmodified.
- `tests/fixtures/deepsea_mot/BD_001_rev2163f4bdd0.xml`: Pascal VOC XML of BD frame 1 at commit 2163f4bdd0. It holds the original `<filename>Benthic_1_V4277_20200219T211238Z_1.jpg</filename>` that links BD to dive V4277.
- `tests/fixtures/deepsea_mot/fathomnet_geoimages_2020-02-19.json`: 8 FathomNet geo-image records of Ventana dive 4277, with the `contributorsEmail` key dropped. It includes the BD nav fix (uuid 207ab015…).
- `tests/fixtures/deepsea_mot/fathomnet_geoimages_2020-07-29.json`: the single FathomNet record of Ventana dive 4289 (the BS nav fix), with `contributorsEmail` dropped.
- `tests/fixtures/deepsea_mot/publication_sites.csv`: 4 derived sites (BD and BS station; MWD and MWS region).
- `tests/fixtures/deepsea_mot/SOURCE.md`: URLs, retrieval date, trimming, quotes and the derivation.

## Short download instruction
DeepSea MOT (CC BY-SA 4.0, tier C, share-alike shard): `huggingface-cli download MBARI-org/DeepSea-MOT --repo-type dataset --revision 61ecbda8acb2749f3771d7192c51341267da2f37` (18.5 GB; Range/resume OK). Or fetch per file via `.../resolve/<rev>/data/<SEQ>/...`.
Skip `data/MD_CLS` (byte-identical to MD_CAN). Videos → videos/, `images/*.jpg` → images/<SEQ>/, `gt.txt`/`seqinfo.ini`/README → metadata/.
Sample 1 frame per second or slower; the whole dataset is about 128 s of footage.
Geo from `publication_sites.csv` by folder: BD (Ventana V4277) 36.7510,-122.1870, 765 m, station ±1 km; BS (V4289) 36.6947,-122.0026, 400 m, ±2 km; MWD and MWS region ±30 km (Midwater One); all others none.

## Open questions / risks
- **Midwater anchor is an assumption.** MWD and MWS use "Midwater One", which is MBARI's usual Ventana midwater site. The actual positions of dives V4432 and V4455 are unpublished, hence region at ±30 km. M3/VARS nav would fix this, but `m3.shore.mbari.org` is not reachable from here.
- **15-minute file grid is inferred.** It rests on two FathomNet `<elapsed ms>--<uuid>` framegrab names of V4277. If Ventana files are longer, the BD fix could be further from the clip; the 1 km radius allows for this. The BS fix is 63 min after the file start, so we gave ±2 km and treat the depth as approximate.
- **FathomNet as a geo source:** we use only the coordinate, depth and time facts from the FathomNet API. Its images are CC BY-NC-ND 4.0 and are not used. Facts are generally not copyrightable, but note the provenance.
- **IFREMER rights chain:** MD_BTL and MD_FLN are IFREMER footage under MBARI's dataset-wide CC BY-SA 4.0. No IFREMER licence or credit line is given, and their origin (vehicle, site, date) is undocumented. The README calls one of them `MD_BOT`, but the folder is `MD_BTL`.
- **Licence changed once:** MIT until 2025-09-03, then CC BY-SA 4.0. Pin revision `61ecbda8…` and store it with every sample.
- **Duplicate upload:** MD_CLS is a byte-identical copy of MD_CAN (video, 600 images, gt). The intended MD_CLS clip may appear in a later revision, so re-check the tree hash on refresh.
- **Ventana or Doc Ricketts:** the card says the videos come from *Doc Ricketts* and *Ventana*, but all four identified sources are Ventana. Any Doc Ricketts footage would be in the unidentified 4K or MD clips. Doc Ricketts also dives far outside Monterey Bay (Oregon, Gulf of California, Hawai'i), so no regional fallback is safe for those clips.
- **Minor metadata inconsistencies:** the paper says 59.94 fps and 29.97 fps for BD, while `seqinfo.ini` says 60 and 30. The Elaine Liu report is dated "Summer 2026", which is probably a typo for 2025.
- **Small and redundant:** about 2 minutes of footage, so low pretraining value per GB. The 4K ProRes files are large: about 2.2 GB for 10 s each.
