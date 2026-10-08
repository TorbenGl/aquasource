# Fixture sources (noaa_oe), read 2026-10-08, metadata only

- `onestop_granules.json`: POST https://data.noaa.gov/onestop/api/search/search/granule with filters
  facet projects=["NOAAOceanExploration"], facet dataFormats (MP4 low-res, MP4 high-res, JPEG), page max 3 offset 0, sort beginDate desc.
  Contains 3 granules of EX2503 DIVE16 (fileIdentifier EX2503_DIVE16_20250501T025000Z_ROVHD, ..T024938Z_ROVAUX1_RECOVERY, ..T024928Z_CRROBO_RECOVERY).
- `licence.txt`: ISO 19115 record gov.noaa.nodc:0310923 (https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.nodc:0310923&view=xml),
  access constraints, and the citeAsStatements of the granules.
- Portal: https://www.ncei.noaa.gov/access/ocean-exploration/video/ ; cruise page https://www.ncei.noaa.gov/waf/okeanos-rov-cruises/ex2503/
- Media (not fixtures, not downloaded for the fixtures): https://www.ncei.noaa.gov/data/oceans/oer/video/EX2503/Video/EX2503_DIVE16_20250430/Compressed/
