# Fixture sources: `ozfish`

All files retrieved 2026-10-06 with User-Agent `aquasource-research/0.1 (+https://github.com/torbengl/aquasource)`.
The Pawsey listing API (`storage.pawsey.org.au/api/...`) needs an anonymous public token from
`POST https://storage.pawsey.org.au/api/login/public` (no credentials), sent as header `X-Auth-Token`.
The direct download URLs `https://data.pawsey.org.au/download/FDFML/<path>` need no token.

| File | Exact URL | Trimming |
|---|---|---|
| `frame_metadata_excerpt.csv` | https://data.pawsey.org.au/download/FDFML/metadata/frame_metadata.csv (6,426,618 bytes, CRLF line endings; same file as Pawsey path `/FDFML/metadata/frame_metadata.csv`) | Only byte ranges were read (`Range: bytes=0-3999`, `1600000-1603999`, `2400000-2403999`, `3200000-3203999`, `6300000-6303999`). Kept: the header plus the complete rows `uid` 1 (prefix A), 20194 (B), 30369 (E), 40496 (G) and 79388 (G, a deployment whose raw video is also published). Dropped rows only; bytes and CRLF endings unchanged. One row = one fish box on one full-HD frame; `file_name` is the frame PNG under `/FDFML/frames/`. |
| `E_AllCumulativeMaxN_excerpt.csv` | https://data.pawsey.org.au/download/FDFML/maxn/E_AllCumulativeMaxN.csv (512,220 bytes, MD5 4d0e67585b8ae67ceb42634aa6a55fe2, LF endings, 7,899 data rows) | Header plus the first 3 data rows. Dropped rows only. One row = one cumulative MaxN event in one raw video (`Filename`, e.g. `E000001_L.MP4` = `/FDFML/videos/E/E000001_L.MP4`). Headers differ per prefix (A/G have extra `Stage` or `Period time (mins)` columns, B has `Genus species` and `MaxN`). |
| `aims_iso19115-3_38c829d4.xml` | https://catalogue.aodn.org.au/geonetwork/srv/api/records/38c829d4-6b6d-44a1-9476-f9b0955ce0b8/formatters/xml (sent with `Accept: application/xml`) | None. Complete ISO 19115-3 record (50,369 bytes, MD5 b29da0987d0e275a91607e938a0b741a). This is the AODN copy of the AIMS record whose point of truth is https://doi.org/10.25845/5e28f062c5097 -> https://apps.aims.gov.au/metadata/view/38c829d4-6b6d-44a1-9476-f9b0955ce0b8 (that host reset our connections and its page is a JavaScript app). Holds the licence (`mco:MD_LegalConstraints`: "Creative Commons Attribution 3.0 Australia License", http://creativecommons.org/licenses/by/3.0/au/), the citation text, the lineage and the only spatial information: `gex:EX_GeographicBoundingBox` west 112.93945312500001, east 137.54882812500003, south -24.126701958681682, north -10.228437266155943. It contains organisational e-mail addresses only (reception@, adc@aims.gov.au). |
| `pawsey_list_folders_FDFML.json` | `GET https://storage.pawsey.org.au/api/m/public/list/folders/FDFML` with `X-Auth-Token: <public token>` | None (978 bytes, MD5 4caa1fbb5f1c0ba2f2804e553040a17a). The top-level folders: crops, frames, labelled, maxn, metadata, videos, videosnippets. File listings (`/api/m/public/list/files/<page>/<path>`) were not kept as fixtures because every item carries the uploader's personal e-mail address. |
| `publication_sites.csv` | derived, see below | Not a provider file. |

## `publication_sites.csv` derivation

Columns: `site_id, site_name, lat, lon, depth_m, uncertainty_m, source`.

OzFish publishes **no per-deployment coordinates**. The dataset paper says so directly
(Marrable et al. 2023, Frontiers in Marine Science 10:1171625, doi:10.3389/fmars.2023.1171625, section 2.2
"Data preparation", read from https://www.frontiersin.org/articles/10.3389/fmars.2023.1171625/pdf):

> "The videos in OzFish have had the metadata removed before publishing, although the data were given prefix
> letters in their filenames to indicate they were taken from different deployments and at different locations."

No source that we found maps a prefix (A, B, E, G) or a deployment number to a survey, site or coordinate. We checked
the GitHub README and its history, the AIMS/AODN ISO record, data.gov.au, Research Data Australia, both
Marrable et al. papers, the open_fish_classifier code repository, the MaxN and lengths CSVs, and the MP4/AVI
container headers. The GoPro HERO4 files carry no GPS and their clock reads 2015-01-01. The B files were re-encoded
by ffmpeg with `creation_time` zeroed.

The only spatial statement is the bounding box in the record-level metadata (`aims_iso19115-3_38c829d4.xml`,
`mdb:identificationInfo/.../gex:EX_GeographicBoundingBox`). The single row is:

- `lat`, `lon` = centre of that box: (-24.126701958681682 + -10.228437266155943) / 2 = -17.17757,
  (112.93945312500001 + 137.54882812500003) / 2 = 125.24414. Research Data Australia shows the same centre point
  (`125.244140625,-17.177569612419`) on https://researchdata.edu.au/ozfish-dataset-machine-video-stations/1442865.
- `uncertainty_m` = largest haversine distance from the centre to a box corner (1,536,593 m to the northern
  corners, R = 6,371,008.8 m), rounded up to 1,540,000.
- `depth_m` is empty: no depth is published for any deployment.
- The centre lies **on land** in the Kimberley. It is a region tag ("tropical northern and north-western Australia"),
  not a sampling position, and it applies to every OzFish sample regardless of prefix.
