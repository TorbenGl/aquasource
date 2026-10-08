# AADC fixtures (metadata only, read 2026-10-08)

Records from the AADC JSON API (no media downloaded):

- `GET https://data.aad.gov.au/metadata/api/records/?full_text=underwater&size=100` (search, 59 hits, used to pick candidates; not saved)
- `GET https://data.aad.gov.au/metadata/api/records/<entry_id>` (detail, saved here):
  - `detail_VMS_Benthic_Photography.json`: stills, Mertz shelf, CC BY 4.0, distribution "5 GB Images", bbox only
  - `detail_underwater_video_V40304.json`: Aurora Australis voyage 4 video, CC BY 4.0, "7.75 GB avi", bbox only
  - `detail_ASAC_2201_Casey_photoquadrats1.json`: photoquadrats, CC BY 4.0 in the text, "not yet publicly available" (restricted)
- Licence page footer (AADC site): "The scientific data on this site is licensed under a Creative Commons Attribution 4.0 Unported License."
- Download links `https://data.aad.gov.au/eds/<n>/download` return the SPA HTML shell (1211 bytes) to HEAD and GET requests: no direct file was seen.
