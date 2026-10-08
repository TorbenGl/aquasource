# Fixtures: gbif_marine_media (fetched 2026-10-08, metadata only, no media downloaded)

- API: https://api.gbif.org/v1/occurrence/search?mediaType=StillImage&hasCoordinate=true&hasGeospatialIssue=false&depth=0,200&limit=300
- Docs: https://techdocs.gbif.org/en/openapi/v1/occurrence
- `search_sample.json`: 3 real occurrence records, verbatim (occurrence key in the record):
  - 6454357462: Didemnum vexillum (sea squirt), Norway, media CC BY 4.0 (`http://creativecommons.org/licenses/by/4.0/`), depth 2 m, uncertainty 5 m. Accepted (tier B, file level).
  - 6148296146: Cygnus cygnus (bird), Norway, media CC BY 4.0, depth 2 m. Accepted, `maybe_not_underwater` true.
  - 6406420337: Cinctura tortugana (shell museum specimen), occurrence licence CC0 but media licence CC BY-NC 4.0. Excluded (tier X, file level beats record level).
- Access check: `mediaLicense` is ignored by the API (CC0 and CC BY counts identical); `depth=5,200` and `waterBody=` work.
