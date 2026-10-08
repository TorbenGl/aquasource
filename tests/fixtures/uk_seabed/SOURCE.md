# Fixtures for uk_seabed (saved 2026-10-08, metadata only)

- `ckan_bassurelle_videos_sci1.json`: CKAN package_show subset for `seabed-videos-from-bassurelle-sandbanks-sci1`
  (https://ckan.publishing.service.gov.uk/api/3/action/package_show?id=seabed-videos-from-bassurelle-sandbanks-sci1).
  Licence id `uk-ogl`, bbox extras, resource URL of the zip.
- `zip_entries_bassurelle_subset.json`: central-directory entries of
  http://s3-eu-west-1.amazonaws.com/data.defra.gov.uk/Marine/JNCC2013_03BassSandRawBenthicSamplingvideo.zip
  (read with Range requests: the EOCD at the end, then the 79 KB central directory). First 30 JPEG entries and the
  two text entries of station STN_298 are kept.
- `station_BSSS033_STN_298_1.txt`: one station text file from the same archive (decompressed): file name and
  timestamp per frame, no coordinates.

No image bytes are stored here.
