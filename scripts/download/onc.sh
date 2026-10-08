#!/usr/bin/env bash
# Download Ocean Networks Canada (Oceans 3.0) fixed camera video / stills into <data_root>/onc/{videos,images,metadata}
#
# Source:   Ocean Networks Canada, https://data.oceannetworks.ca (Oceans 3.0 API, archive files)
#           API guide https://oceannetworkscanada.github.io/Oceans3.0-API/API_Guide.html
# Licence:  tier U for every sample (not resolved per device). ONC-owned data are CC BY 4.0, partner-owned data may be
#           CC BY-NC or more restrictive (ONC Data Policy https://www.oceannetworks.ca/data/data-policy/, collection level).
#           Check the owner of each device before using a sample as tier B. Nothing is upgraded.
# Geo:      fixed_site, inferred: the deployment position (fields lat, lon, depth of /deployments) of the device for the file
#           time. No uncertainty published. Mobile categories (ROV, AUV) are not used by default.
# Size:     not measured: video files are archive files of the device (size unknown until the download starts).
#
# Manual steps before running:
#   export ONC_TOKEN=...   (free account, token at https://data.oceannetworks.ca/Profile). Without it every call fails.
#   Pick locations with --opt locations=<ONC location codes> (the API lists them, see the API guide: getLocations).
#
# Usage:
#   ONC_TOKEN=... scripts/download/onc.sh --opt locations=<CODE> --opt from=2024-08-01 --opt to=2024-08-31 --dry-run
#   ONC_TOKEN=... scripts/download/onc.sh --opt locations=<CODE> --opt from=2024-08-01 --opt to=2024-08-31 --budget 50
#   scripts/download/onc.sh --opt locations=<CODE> --opt from=2006-01-01 --opt per_day=1   # full history, one per day
#   Options: locations (required), categories (VIDEOCAM,CAMERA), from, to, extension (mp4 | jpg), per_day
#            (see the module docstring of src/aquasource/adapters/onc.py).
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks
command -v uv >/dev/null 2>&1 || { echo "onc: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }
: "${ONC_TOKEN:?onc: set ONC_TOKEN first (free account, https://data.oceannetworks.ca/Profile); see the header of this script}"

exec uv run aquasource download onc "$@"
