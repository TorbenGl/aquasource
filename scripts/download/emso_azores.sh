#!/usr/bin/env bash
# Download SMOOVE video, EMSO-Azores Lucky Strike TEMPO module, into <data_root>/emso_azores/{images,videos,metadata}
#
# Source:   SEANOE, DOIs 10.17882/48592 ... 10.17882/101838 (research/emso_azores.md)
# Licence:  CC BY 4.0 (tier B), read at record level (SEANOE landing page)
# Geo:      fixed_site from the publication (37.2889 N, -32.275567 E, 1695 m; sites/emso_azores.csv)
# Size:     about 250 GB of tar archives (10 datasets, 1-2 tars each); videos fetched by byte range, not the tars
#
# Manual steps before running:
#   None (open, no token)
#
# Usage:
#   scripts/download/emso_azores.sh                    # download (config budget, else everything)
#   scripts/download/emso_azores.sh --dry-run          # metadata only, no media
#   scripts/download/emso_azores.sh --budget 500       # stop after 500 selected samples
#   scripts/download/emso_azores.sh --opt from=2023-01-01   # adapter options: from, to, per_day, years (see research/emso_azores.md)
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks (remove if none), e.g.:
# : "${ONC_TOKEN:?set ONC_TOKEN first: see the header of this script}"

exec uv run aquasource download emso_azores "$@"
