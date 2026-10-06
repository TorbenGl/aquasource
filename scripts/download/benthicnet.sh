#!/usr/bin/env bash
# Download BenthicNet seafloor photos (BenthicNet-1M and BenthicNet-Labelled) into <data_root>/benthicnet/{images,metadata}
#
# Source:   https://doi.org/10.20383/103.01241 (FRDR v2); paper https://doi.org/10.1038/s41597-025-04491-1
# Licence:  set per image set in 00_Documentation/all_licenses_refs.csv (read at record = image-set level).
#           Ingested: U.S. Public Domain (tier A), CC-BY-3.0/4.0 and OGL-Canada (tier B), about 92 % of the bytes.
#           NOT ingested: NC/ND sets (FathomNet, MGDS, USAP-DC, 2 PANGAEA; tier X), the Schmidt Ocean FK* sets
#           (listed CC BY, CC BY-NC-SA 4.0 at origin; tier U) and sets missing from the table (tier U, except
#           pangaea-<id> sets whose own PANGAEA record is CC BY / CC0). The collection licence is "custom".
# Geo:      per-image latitude/longitude (WGS 84, 99.6 % filled). Precision is inferred per site: `image` for most
#           rows; `station` (geo_inferred=true) for RLS photo-quadrats (~1 km) and sites sharing one coordinate;
#           `region` for one-coordinate multi-site datasets. depth_m = -gebco_bathymetry (modelled GEBCO_2022,
#           null when >= 0). geo_source names the CSV and columns.
# Size:     1M: 1,345,096 JPEG photos, 215 GB as 512 px tars (originals vary, 1.6 MB to 12 MB);
#           Labelled: 188,688 photos, 28 GB. BenthicNet-11M has no published list (use squidle_imos,
#           catlin_seaview, pangaea_images). The CSV metadata is a ~25 MB Range request (1M) into metadata/raw/.
#           Measured on the CSVs (2026-10-06): 1M has 1,235,807 of 1,345,096 rows in tier A/B (91.9 %; by geo:
#           image 802,714, station 422,094, region 10,953, none 46); Labelled has 186,614 of 188,688 (98.9 %).
#
# Manual steps before running:
#   none (anonymous HTTPS, no Globus account). Optional: --opt local_dir=<folder> with files you downloaded
#   yourself (finalized_csvs.zip, all_licenses_refs.csv, <dataset>.tar).
#
# Usage:
#   scripts/download/benthicnet.sh --dry-run --budget 100      # metadata only, spread over sources/datasets/sites/time
#   scripts/download/benthicnet.sh --budget 5000               # 5,000 spread photos (originals, 1 request/s per host)
#   scripts/download/benthicnet.sh --opt subset=labelled       # 1m (default) | labelled | both
#   scripts/download/benthicnet.sh --opt media=auto            # 512 px tar when the dataset tar is <= 50 MB, else original
#   scripts/download/benthicnet.sh --opt sources=NGU,SEAM,MUN  # only these CSV `source` values
#   scripts/download/benthicnet.sh --opt exclude_overlap=true  # skip sources other catalog keys cover (SQUIDLE+, Catlin, PANGAEA, NOAA, USGS, NRCan)
#   scripts/download/benthicnet.sh --opt order=csv             # file order instead of the spread order
# More options (datasets, exclude_*, all_tiers, resolve_pangaea, tar_max_mb, local_dir): see the docstring of
# src/aquasource/adapters/benthicnet.py and research/benthicnet.md.
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."
exec uv run aquasource download benthicnet "$@"
