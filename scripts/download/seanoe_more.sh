#!/usr/bin/env bash
# Download SEANOE 10.17882/101899 (citizen-labelled deep-sea observatory images) into <data_root>/seanoe_more/{images,metadata}
#
# Source:   https://www.seanoe.org/data/00907/101899/  (DOI 10.17882/101899, Lebeaud, Tosello, Borremans, Matabos, 2024)
#           one archive data/115473.zip, 798.7 MB, 3,979 JPEG frames read by HTTP Range requests (no full download)
# Licence:  CC BY 4.0, tier B, read at record level (SEANOE landing page licence badge and DataCite rights list)
# Geo:      fixed_site, geo_inferred=true: each frame takes the coordinate of its camera (file name prefix
#           CAM-TEMPO-MINI-2 = TEMPO Juan de Fuca 48.503038 N, -125.554305; MOMAR = Azores 37.2933 N, -32.2733),
#           from the two DataCite geoLocationBoxes (src/aquasource/adapters/sites/seanoe_more.csv).
# Size:     3,979 frames, about 0.78 GB of JPEG (3,403 TEMPO, 576 MOMAR); about 200 KB per frame.
#
# Manual steps before running:
#   none (no token; anonymous HTTPS with Range support)
#
# Usage:
#   scripts/download/seanoe_more.sh                      # all frames (budget from config, else everything)
#   scripts/download/seanoe_more.sh --dry-run            # metadata only: central directory of the archive, no frames
#   scripts/download/seanoe_more.sh --budget 500         # stop after 500 selected frames
#   scripts/download/seanoe_more.sh --opt cameras=MOMAR  # only the Azores camera
#   scripts/download/seanoe_more.sh --opt per_day=5      # at most 5 frames per calendar day
#   Options: cameras, per_day (see the module docstring of src/aquasource/adapters/seanoe_more.py).
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "seanoe_more: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download seanoe_more "$@"
