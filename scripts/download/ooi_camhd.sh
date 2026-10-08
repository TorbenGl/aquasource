#!/usr/bin/env bash
# Download OOI CamHD (CAMHDA301, ASHES vent field, Axial Seamount) mp4 files into <data_root>/ooi_camhd/{videos,metadata}
#
# Source:   OOI raw data server https://rawdata.oceanobservatories.org/files/RS03ASHS/PN03B/CAMHDA301/ (anonymous)
# Licence:  tier B (collection level): OOI Data Use Policy v2-00 s4.1, free use incl. derivatives, no named licence
# Geo:      fixed_site (camera position from OOI asset-management deployment table, sites/ooi_camhd.csv)
# Size:     one 1080p mp4 about 852 MB per 3 h file (the .mov about 13 GB is not used); about 8 files per day
#
# Manual steps before running:
#   none (no token).
#
# Usage:
#   scripts/download/ooi_camhd.sh --dry-run                       # listing only, no video
#   scripts/download/ooi_camhd.sh --budget 3                      # first 3 selected videos (oldest first)
#   scripts/download/ooi_camhd.sh --opt from=2016-01-01 --opt to=2016-01-31 --opt per_day=2
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

exec uv run aquasource download ooi_camhd "$@"
