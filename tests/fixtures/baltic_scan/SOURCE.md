# Fixtures for baltic_scan (Mendeley Data 10.17632/wsd42v8mk5.1)

- `mendeley_record_wsd42v8mk5_1.json`: public API record, `https://data.mendeley.com/public-api/datasets/wsd42v8mk5?version=1`
  (licence text in `data_licence`, station coordinates in `description`, publish date 2022-06-21). Fetched 2026-10-08.
- `zip_entries_wsd42v8mk5_1.json`: central directory of the single archive (19 entries, 3,409,429,991 bytes), read with
  Range requests from `https://data.mendeley.com/public-api/zip/wsd42v8mk5/download/1` (302 to a signed S3 URL).
  Only the central directory was read (about 3 KB); no member bytes are stored here.
- Landing page: `https://data.mendeley.com/datasets/wsd42v8mk5/1`
