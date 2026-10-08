#!/usr/bin/env bash
# Download baltic_scan (SE Baltic reef ROV and SCUBA video, Mendeley Data) into <data_root>/baltic_scan/{images,videos,metadata}
#
# Source:   https://data.mendeley.com/datasets/wsd42v8mk5/1  (DOI 10.17632/wsd42v8mk5.1)
# Licence:  CC BY 4.0 (tier B), read at record level (Mendeley data_licence field)
# Geo:      station precision from the record description (DE01, SM02, SM07, SM08), geo_source in sites/baltic_scan.csv
# Size:     one archive, about 3.4 GB: 7 AVI videos (254-493 MB each) and 8 JPEG 2D video mosaics
#
# Manual steps before running:
#   none (no token; the archive is read by Range requests, about 3 KB of metadata first)
#
# Usage:
#   scripts/download/baltic_scan.sh                    # download (config budget, else everything)
#   scripts/download/baltic_scan.sh --dry-run          # metadata only, no media
#   scripts/download/baltic_scan.sh --budget 500       # stop after 500 selected samples
#   scripts/download/baltic_scan.sh --opt kinds=video  # adapter options (see research/baltic_scan.md)
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

exec uv run aquasource download baltic_scan "$@"
