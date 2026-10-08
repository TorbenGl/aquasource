## HANDOFF
- status: blocked
- tier + licence: U (not upgraded). Licence still unread (records 401/404).
- geo: none usable; would be fixed_site if node positions are published (not read).
- files: adapter none / script scripts/download/love_observatory.sh (exits 1, prints why) / test none / sites csv none / fixtures tests/fixtures/love_observatory/SOURCE.md
- tests: n/a; sample: not run (no endpoint)
- doubts:
  - NEW (Sonnet retry 2026-10-08): raw data route found. IMR docs https://ftp.nmdc.no/nmdc/IMR/Doc/S3-Node4.pdf and S3-Node7.pdf (open) say raw LoVe data (incl. Develogic underwater camera: sensor 164 node 4, 107 node 7) is on S3 https://s3.hi.no, layout /lovedata/<YEAR>/<Node>/<SensorID>/, but "user credentials are needed", obtained by request to the IMR data help desk (datahjelp at hi.no). Anonymous probe: s3.hi.no/lovedata/ -> 403, bucket list empty. Not open; ftp.nmdc.no/nmdc/IMR/ has no LoVe folder.
  - Licence unknown; a human must ask IMR for credentials plus the licence (NLOD?) for camera images; only then build an S3 adapter (year/node/sensor 164/107, from/to/per_day).
  - Coordinates: not in the PDFs; take node positions from LoVe papers.
- needs_opus: no, a human contact with IMR is needed (credentials + licence); no code can fix it.

## Summary
LoVe (Lofoten-Vesteralen Ocean Observatory, Norway, operated by the Institute of Marine Research with Equinor; cabled seabed node network off Hovden, Vesteralen). It carries cameras, hydrophones and echosounders. The discovery metadata sit at the Norwegian Marine Data Centre (NMDC); data are said to be reached by ftp and OPeNDAP per data type.

## Access (read 2026-10-08, metadata only)
- https://data.arcticobserving.org/metsis/metadata/IMR_LOVE_NODE4 (redirect from saon.met.no): 401
- https://data.arcticobserving.org/metsis/metadata/IMR_LOVE_NODE7: 401
- https://metadata.nmdc.no/metadata/IMR_LOVE_NODE4: 404; https://geonorge.no/geonetworktest/srv/api/records/IMR_LOVE_NODE4: 404
- https://www.gceocean.no/projects/gce/love-ocean-observatory/: no licence, no data URL
- https://www.loveocean.no, https://love.equinor.com: not reachable from this environment
- Node documentation PDF cited in a Geonorge snippet: https://ftp.nmdc.no/nmdc/IMR/Doc/S3-Node4.pdf (not fetched)

## Not done
- No adapter, no sample, no tests, no sites csv. Notion/commit steps follow this status.
