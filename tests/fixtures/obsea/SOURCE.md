# OBSEA fixtures (metadata only, fetched 2026-10-08)

- `zenodo_22802714.json`: Zenodo API record https://zenodo.org/api/records/22802714 (DOI 10.5281/zenodo.22802714,
  "Underwater photography at OBSEA seabed station during 2013", licence cc-by-4.0). Trimmed: only the zip
  `OBSEA_seabed_station_pictures_L0a_20130101_20130201.zip` is kept in `files`.
- `zenodo_search_p1.json`: one hit in the shape of https://zenodo.org/api/records?q=title:"Underwater photography at OBSEA seabed station during"
  (trimmed to the 2013 record).
- `index_2013_01_first10.csv`: header and first 10 rows of `index.csv` inside that zip (read with HTTP Range requests,
  the zip itself was not downloaded). Full file: 3,181 rows, 2013-01-09 to 2013-01-31.
- Image host check (HEAD only): https://files.obsea.es/pictures/Sony_SNC-RZ25N/2013/01/09/20130109-181742-Sony_SNC-RZ25N.jpeg
  answers 200, image/jpeg, 51,143 bytes.
- ERDDAP: https://data.obsea.es/erddap/info/OBSEA_seabed_station_pictures_L0a/index.json (global licence CC-BY-4.0,
  lat 41.18212, lon 1.75257, depth 20 m).
