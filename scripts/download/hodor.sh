#!/usr/bin/env bash
# Download HODOR camera videos into <data_root>/hodor/{images,videos,metadata}
#
# Source:   PANGAEA.980001 (HODOR camera data), https://doi.org/10.1594/PANGAEA.980001
#           (bundled publication PANGAEA.980000; Wilts et al. 2025, IEEE Data Descriptions)
# Licence:  Creative Commons Attribution 4.0 (CC-BY-4.0), read at record level from the table header
#           "License:" line, tier B.
# Geo:      fixed_site: observatory position from the Coverage line (LATITUDE 54.340625, LONGITUDE 10.174105),
#           geo_inferred true. No depth in the table (depth_m null).
# Size:     5850 activity-selected sequences, 2021-08-22 to 2021-11-16, two synchronised stereo cameras
#           (~144 GB for cam1 + cam2 with timestamp files). Default is cam1 only.
#
# Manual steps before running:
#   none. Single video files are served without login (the bulk ZIP/TAR needs PANGAEA registration; not used).
#
# Usage:
#   scripts/download/hodor.sh                          # download (config budget, else everything)
#   scripts/download/hodor.sh --dry-run                # metadata only, no media
#   scripts/download/hodor.sh --budget 500             # stop after 500 selected samples
#   scripts/download/hodor.sh --opt cams=cam1,cam2     # both stereo cameras
#   scripts/download/hodor.sh --opt from=2021-09-01 --opt to=2021-09-30 --opt per_day=20
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

exec uv run aquasource download hodor "$@"
