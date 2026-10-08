# Fixtures: smithsonian_oa

`records_nmnhinv_marine.jsonl`: three real EDAN records (one JSON object per line, unmodified) copied from the
Smithsonian Open Access metadata shard `metadata/edan/nmnhinv/00.txt` (NMNH Invertebrate Zoology), read 2026-10-08.

- Shard URL: https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan/nmnhinv/00.txt
  (unit index: https://smithsonian-open-access.s3-us-west-2.amazonaws.com/metadata/edan/nmnhinv/index.txt)
- Line 1 `ld1-1643412364509-1643412431822-0`: Decapoda, Moorea (South Pacific), coords + Depth (m); CC0 screen image.
- Line 2 `ld1-1643411218332-1643411254826-1`: Parandaniexis sp., South Sandwich Islands; CC0; no underwater keyword.
- Line 3 `ld1-1703589922361-1703589959600-1`: Bargmannia sp., Aleutians / Gulf of Alaska area; CC0.
- Licence field: `descriptiveNonRepeating.online_media.media[].usage.access` = `CC0` (record level).
- Metadata licence: https://github.com/Smithsonian/OpenAccess/blob/master/LICENSE (CC0 1.0 Universal).
- Public API (api.si.edu) needs an api.data.gov key (`API_KEY_MISSING` without it); not used.
- Images are not fixtures: no media was downloaded for research.
