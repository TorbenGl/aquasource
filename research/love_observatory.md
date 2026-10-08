## HANDOFF
- status: blocked
- tier + licence: U (not upgraded). Licence not read: the IMR node metadata records (data.arcticobserving.org/metsis/metadata/IMR_LOVE_NODE4, _NODE7) return HTTP 401, metadata.nmdc.no and geonorge.no return 404. Search snippets show "Access constraint: Open" and an empty Use constraint.
- geo: none usable. Only "west of Hovden, Vesteralen" (gceocean.no project page) and approximate node positions in a 2020 IMR slide. No published node coordinates read. Would be fixed_site if confirmed.
- files: adapter none / script scripts/download/love_observatory.sh (exits 1, prints why) / test none / sites csv none / fixtures tests/fixtures/love_observatory/SOURCE.md (no record saved)
- tests: n/a (no adapter; nothing to test offline)
- sample: 0 files, not run (no readable record, no media endpoint)
- doubts:
  - Licence: no NLOD or other licence text read anywhere; check the Use constraint field of the IMR_LOVE_NODE* records on NMDC/data.norge.no
  - Camera imagery: whether still images or video are public at all (sources say "images, sound" but no file route)
  - Access: records need login (401); check whether NMDC offers anonymous ftp (ftp.nmdc.no/nmdc/IMR/) for image folders
  - Coordinates: only approximate; do not add to sites/ without a published position
  - Observatory was down for over a year; check current data availability and the new loveocean.no portal
- needs_opus: yes, access not solvable from here (401/404 on every record endpoint, loveocean.no unreachable). A human or IMR/NMDC contact is needed first; Opus will not fix a 401.

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
