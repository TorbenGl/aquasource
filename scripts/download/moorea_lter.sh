#!/usr/bin/env bash
# Download Moorea Labeled Corals (MCR LTER photo-quadrats 2008-2010) into <data_root>/moorea_lter/{images,metadata,archives}
#
# Source:   EDI knb-lter-mcr.5006.3 rev 3, https://doi.org/10.6073/pasta/88dde0e68ab5232a470389f4bedd1892
#           (research/moorea_lter.md; fetched via the anonymous DataONE member node gmn.lternet.edu)
# Licence:  CC BY 4.0, tier B, read at record level (EML intellectualRights, https://cn.dataone.org/cn/v2/object/...)
# Geo:      station precision, geo_inferred=true, from the filename (site, habitat) and sites/moorea_lter.csv
#           (EML site polygon centroids; BCO-DMO 918265 for LTER1/2 10 m); uncertainty 200 m to 1650 m
# Size:     2,055 images in 3 zips: 2008 2.04 GB, 2009 2.63 GB, 2010 0.96 GB (5.6 GB). Each zip is downloaded whole
#           once (no per-image endpoint; the member node ignores HTTP Range) and kept in <data_root>/moorea_lter/archives/
#
# Manual steps before running:
#   none for access, but the anonymous member node is currently BLOCKED for bulk zips (2026-10-08 test: stream reset
#   after ~20 MB, no HTTP Range, ~160 kB/s). Plan: free EDI API key (https://auth.edirepository.org, route A in
#   research/moorea_lter.md) or ask MCR LTER information management for a copy. The adapter retries on rerun.
#
# Usage:
#   scripts/download/moorea_lter.sh                    # all images, 2008 then 2009 then 2010 (needs ~5.6 GB disk)
#   scripts/download/moorea_lter.sh --dry-run          # no zip downloads: lists nothing until a zip is present
#   scripts/download/moorea_lter.sh --budget 3 --opt head_mb=12   # 3 images from the first 12 MB of the 2008 zip (cut-off streams are salvaged)
#   scripts/download/moorea_lter.sh --opt years=2010   # only the 963 MB 2010 zip (contains some PNG files)
#   scripts/download/moorea_lter.sh --opt habitats=out17m
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

exec uv run aquasource download moorea_lter "$@"
