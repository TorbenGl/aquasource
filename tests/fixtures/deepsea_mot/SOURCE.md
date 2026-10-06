# Fixture sources: `deepsea_mot`

All files were retrieved on 2026-10-06 with User-Agent
`aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`.
Rows and values are real and unchanged. Where something was removed, it was a whole field or row, never an edited value.

Dataset: DeepSea MOT, Hugging Face dataset `MBARI-org/DeepSea-MOT`, current revision
`61ecbda8acb2749f3771d7192c51341267da2f37` (2026-02-18). Licence: `cc-by-sa-4.0`, read at record level from the dataset card.

| File | Exact URL | What it is / trimming |
|---|---|---|
| `README.md` | https://huggingface.co/datasets/MBARI-org/DeepSea-MOT/raw/main/README.md (revision 61ecbda8) | The dataset card, 4,155 bytes, unmodified. The YAML header holds `license: cc-by-sa-4.0`. It also gives the sequence list, file structure and BibTeX. |
| `hf_tree_data.json` | https://huggingface.co/api/datasets/MBARI-org/DeepSea-MOT/tree/main/data | The HF tree API listing of `data/` (1,192 bytes, unmodified). It has 11 sequence directories (`BD`, `BS`, `BS_4K`, `MD_BTL`, `MD_CAN`, `MD_CLS`, `MD_FLN`, `MD_ROP`, `MWD`, `MWS`, `MWS_4K`) plus `vidseq_names.txt`. The directory name is the key that `resolve_geo` maps to a site. |
| `BD_001_rev2163f4bdd0.xml` | https://huggingface.co/datasets/MBARI-org/DeepSea-MOT/raw/2163f4bdd0/data/BD/xml/BD_001.xml | The Pascal VOC annotation of frame 1 of `BD` **as it was at commit 2163f4bdd0** (2025-08-29, "add TrackEval artifacts"), before commit 4e0b079c39 ("fix XML filename tags") renamed the tags. 18,872 bytes, unmodified. It holds `<filename>Benthic_1_V4277_20200219T211238Z_1.jpg</filename>`, which is the provider's own record that ties sequence `BD` to source video file `V4277_20200219T211238Z` (ROV *Ventana* dive 4277). |
| `fathomnet_geoimages_2020-02-19.json` | `POST https://database.fathomnet.org/api/geoimages/query` with body `{"startTimestamp":"2020-02-19T14:00:00.000Z","endTimestamp":"2020-02-20T06:00:00.000Z","limit":500}` | All 8 FathomNet geo-image records for that UTC window. All are `.../framegrabs/Ventana/images/4277/...`, which is dive V4277. **Trimming:** the `contributorsEmail` key (a personal e-mail address) was dropped from every record. All other keys and values are unchanged, in the original order, and re-serialised compactly with `json.dump`. The record `uuid 207ab015-c8db-4060-b681-2590d8a9b12d` (2020-02-19T21:20:12.646Z, 36.751029 / -122.187046, 764.85 m) is the nav fix used for site `BD`. |
| `fathomnet_geoimages_2020-07-29.json` | Same endpoint, body `{"startTimestamp":"2020-07-29T14:00:00.000Z","endTimestamp":"2020-07-30T06:00:00.000Z","limit":500}` | The only record in that window: Ventana dive 4289, 2020-07-29T19:53:13.382Z, 36.694707 / -122.00259, 399.53 m. The same `contributorsEmail` drop applies. This is the nav fix used for site `BS`. |
| `publication_sites.csv` | Derived (see below) | Built by hand from the provider records above, the benchmark_eval notebook and Robison et al. 2017. It is not a provider file. |

## How the sequences were tied to source dives

1. **HF XML history.** Commit `2163f4bdd0` held the original RectLabel file names. Commit `4e0b079c39` (2025-08-29, "fix XML filename tags") replaced them with `BD_001.jpg` etc. The first frame of each original sequence at 2163f4bdd0 reads:
   - `data/BD/xml/BD_001.xml` → `<filename>Benthic_1_V4277_20200219T211238Z_1.jpg</filename>` (stored as a fixture)
   - `data/BS/xml/BS_001.xml` → `<filename>10s_Benthic_2_V4289_20200729T185027Z_1.jpg</filename>`
   - `data/MWD/xml/MWD_001.xml` → `<filename>Midwater_difficult_V4432_20220914T160635Z_prores_1.jpg</filename>`
   - `data/MWS/xml/MWS_001.xml` → `<filename>Midwater_simple_V4455_20221130T192123Z_prores_1.jpg</filename>`

   URL pattern: `https://huggingface.co/datasets/MBARI-org/DeepSea-MOT/raw/2163f4bdd0/data/<SEQ>/xml/<SEQ>_001.xml`.
2. **Authors' code repository.** In https://github.com/mbari-org/benchmark_eval (HEAD 40aec18, 2026-01-23), file `tracker_output.ipynb`, cell 2 ("Setting Variables"), the lines read verbatim:
   ```
   "simple_mid": "./videos/simple_mid/Midwater_simple_V4455_20221130T192123Z_prores.mov",
   "simple_ben": "./videos/simple_ben/10s_Benthic_2_V4289_20200729T185027Z.mov",
   "difficult_mid": "./videos/difficult_mid/Midwater_difficult_V4432_20220914T160635Z_prores.mov",
   "difficult_ben": "./videos/difficult_ben/Benthic_1_V4277_20200219T211238Z.mov"
   ```
   The paper's Table I names these sequences MWS, BS, MWD and BD.
3. **Reading the name.** In `V4277_20200219T211238Z`, `V` = ROV *Ventana*, `4277` = dive number, and `20200219T211238Z` = UTC start of the source video file. FathomNet uses the same convention (`framegrabs/Ventana/images/4277/20200219T212012Z--…png`, whose `timestamp` field is `2020-02-19T21:20:12.646Z`). FathomNet holds Ventana 4277 framegrabs only on 2020-02-19 and Ventana 4289 only on 2020-07-29, which confirms the dates.
4. **No source identifier for the other 7 sequences.** `BS_4K`, `MWS_4K`, `MD_ROP`, `MD_CAN`, `MD_CLS` (MBARI) and `MD_BTL`, `MD_FLN` (IFREMER) had clean names from their first commit. We checked:
   - their QuickTime `moov` atoms, read with Range requests (export dates in 2025 and timecode 00:00:00:00 only; MD_ROP metadata says `title=clips`, `author=Megan Bassett`)
   - their `.DS_Store` files (empty)
   - the docs at https://docs.mbari.org/benchmark_eval/

   None of these identifies a dive. These sequences get no site row.

## publication_sites.csv: derivation

- **BD → Ventana V4277.**
  - The source file starts 2020-02-19T21:12:38Z.
  - FathomNet record `207ab015-c8db-4060-b681-2590d8a9b12d` (GET https://database.fathomnet.org/api/images/207ab015-c8db-4060-b681-2590d8a9b12d) has timestamp 2020-02-19T21:20:12.646Z, `latitude` 36.751029, `longitude` -122.187046, `depthMeters` 764.8499755859375 and `pressureDbar` 770.9. Its tags are `platform=Ventana` and `source=MBARI/VARS`. Its 21 bounding boxes are all `Funiculina`, the same sea pens that dominate BD (`Funiculina_Balticina complex`, 42 boxes in BD_001).
  - Two other framegrabs of the same dive are named `<elapsed ms>--<video uuid>`: 157290 ms → a file starting at 16:57:37Z, and 814680 ms → a file starting at 20:27:38Z. With 21:12:38Z these starts sit on a 15-minute grid, so the source file probably covers about 21:12:38–21:27:38Z. That grid is our inference, not a documented fact. The fix at 21:20:12Z falls inside that window.
  - The bottom fixes of the dive drift north by about 0.5 km per 40 min (19:21 → 20:41 → 21:20Z: 36.740671 → 36.746444 → 36.751029).
  - Uncertainty is set to **1,000 m**. That covers any clip position within the file, even if the file is longer than 15 min, plus USBL error.
  - `depth_m` = 764.85, from `depthMeters` rounded to cm.
- **BS → Ventana V4289.**
  - The source file starts 2020-07-29T18:50:27Z.
  - The only public fix is FathomNet `f86584c5-f35d-4bd0-a215-69d8fbb27cae`: 2020-07-29T19:53:13.382Z, 36.694707 / -122.00259, `depthMeters` 399.5299987792969 (it shows one *Pasiphaea*). It is 63 min after the file start.
  - Uncertainty is set to **2,000 m**, since a benthic ROV moves at most about 1 km/h on transects. The depth of 399.53 m is approximate: the ROV may have been at a different depth an hour earlier.
- **MWD → Ventana V4432 (2022-09-14) and MWS → Ventana V4455 (2022-11-30).**
  - No public navigation was found:
    - FathomNet has no geo-images at all between 2022-01-01 and 2022-07-01, and none in the Monterey box (35.5–37.5 N, 121.5–123.5 W) between 2022-06-01 and 2023-03-01.
    - OBIS has no records deeper than 50 m in the Monterey box on either date.
    - The MBARI M3 / VARS API (`m3.shore.mbari.org`) refused the connection from here, and WebFetch got HTTP 503.
  - The rows use a published **region anchor** instead. Robison, B.H., Reisenbichler, K.R., Sherlock, R.E. (2017), "The coevolution of midwater research and ROV technology at MBARI", *Oceanography* 30(4):26–37, doi:10.5670/oceanog.2017.421 (PDF https://tos.org/oceanography/assets/docs/30-4_robison.pdf), pages 27–28, section "LOCATION":
    > "MBARI's proximity to Monterey Submarine Canyon allowed us to adopt a unique operational mode for Ventana—day trips. Rachel Carson and Ventana typically leave the dock each morning at 0700 hrs and arrive at our reference dive site at about 0830. … Our principal midwater dive site (Midwater One, at 36°42'N, 122°02'W) is located over the axis of the Monterey Submarine Canyon where the water column depth is approximately 1,600 m."
  - 36°42'N 122°02'W = 36.7, -122.033333.
  - Uncertainty is set to **30,000 m**. Midwater One is only MBARI's usual midwater site; the paper does not say these two dives were there. The radius covers Ventana day-trip sites in Monterey Bay: the V4277 site is 14.8 km from Midwater One and the V4289 site is 2.8 km from it.
  - `depth_m` is left empty because MWD is filmed during descent.
  - Both MWD (file start 09:06 PDT) and MWS (11:21 PST) fall in the day-trip window described above.
