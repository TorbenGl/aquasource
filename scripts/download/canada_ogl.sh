#!/usr/bin/env bash
# Download the GSC "Seafloor photographs, offshore Canada" stills into <data_root>/canada_ogl/{images,metadata}
#
# Source:   Geological Survey of Canada (NRCan), record https://open.canada.ca/data/en/dataset/44cbbdc0-d33d-abe7-b08a-f5872bc0a48a
#           Media and per-station CSVs: https://ftp.maps.canada.ca/pub/nrcan_rncan/raster/marine_geoscience/Seabed_Photo_Collection/
# Licence:  tier B. "Open Government Licence - Canada" (record ca-ogl-lgo; ISO 19115 resourceConstraints), record level,
#           https://open.canada.ca/en/open-government-licence-canada. No file-level licence.
# Geo:      image (distinct per-photo PHOTO_LAT/PHOTO_LONG) or station (one position per station), from the station CSV rows;
#           depth from WATER_DEPTH. Uncertainty from HORIZONTAL_POSITIONAL_ACCURACY (see research/canada_ogl.md).
# Size:     20,017 full-resolution PNG (~153 GB, 6-26 MB each) from 1,804 stations on 78 expeditions (1965-2015).
#           The DFO Fundy Isles imagery is NOT in this script (see research/canada_ogl.md, Open questions).
#
# Manual steps before running:
#   none (anonymous HTTPS, no token). The Fundy 2023-2024 media need a request to DFO (human step, not automated).
#
# Usage:
#   scripts/download/canada_ogl.sh                    # download (config budget, else everything the caps allow)
#   scripts/download/canada_ogl.sh --dry-run          # metadata only (folder listings and station CSVs), no images
#   scripts/download/canada_ogl.sh --budget 500       # stop after 500 selected samples
#   scripts/download/canada_ogl.sh --opt per_station=0 --opt max_per_expedition=0   # all photos of the stations taken
#   Options: per_station (default 1; 0 = all), max_per_expedition (default 3; 0 = no limit), seed (default 0)
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "canada_ogl: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download canada_ogl "$@"
