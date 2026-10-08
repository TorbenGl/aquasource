# noaa_dsc fixtures (metadata only, fetched 2026-10-08)

- `erddap_records.csv`: 6 rows of the real ERDDAP answer (header, units row, then records) from
  https://www.ncei.noaa.gov/erddap/tabledap/deep_sea_corals.csv?CatalogNumber,ImageURL,DataProvider,Repository,DatasetID,ScientificName,latitude,longitude,DepthInMeters,ObservationDate,Citation,Locality,Ocean,Country
  with the filters `ImageURL!=""` plus `DatasetID="NOAA_CT-13-07"` (rows 948036, 948037), `DatasetID="NOAA_EX-19-03-L2"`
  (row 1045200), `DatasetID="MBARI"` (row 206126). Row 948037 is a second record of the image 948036.JPG.
  Only complete rows were kept; the CSV is re-encoded by the csv module (quoting unchanged).
- Dataset landing: https://www.ncei.noaa.gov/archive/accession/0145037 ; ISO 19115: https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.nodc:0145037
- Dataset dictionary: https://www.ncei.noaa.gov/waf/dsc-data/metadata/20221213-0_NOAA_NDB_corals_sponges_data_dictionary.csv
- Images checked with HEAD only: https://www.ncei.noaa.gov/waf/dsc-data/images/001045/1045200.jpg (image/jpeg, 44 KB),
  https://www.ncei.noaa.gov/waf/dsc-data/images/000948/948036.JPG (image/jpeg, 290 KB).
