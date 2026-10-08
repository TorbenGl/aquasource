#!/usr/bin/env bash
# Download OOI still-camera frames (CAMDS digital still cameras, CAMDSB/CAMDSC) into <data_root>/ooi_cameras/{images,metadata}
#
# Source:   OOI raw data server https://rawdata.oceanobservatories.org/files/<site>/<platform>/<CAMDS...>/ (anonymous)
# Licence:  tier B (collection level): OOI Data Use Policy v2-00 s4.1, free use incl. derivatives, no named licence
# Geo:      fixed_site (camera position from OOI asset-management deployment tables, sites/ooi_cameras.csv)
# Size:     one JPEG about 10-16 MB; about 300 frames per camera-day in bursts (about 5 GB per day): use per_day / from / to
#
# Manual steps before running:
#   none (no token).
#
# Usage:
#   scripts/download/ooi_cameras.sh --dry-run                       # listing only, no frames
#   scripts/download/ooi_cameras.sh --budget 3                      # first 3 selected frames (oldest first)
#   scripts/download/ooi_cameras.sh --opt from=2025-06-01 --opt to=2025-06-07 --opt per_day=10 --opt cameras=RS01SBPS-PC01A-07-CAMDSC102
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

exec uv run aquasource download ooi_cameras "$@"
