#!/usr/bin/env bash
# Download OBSEA seabed station pictures (UPC / EMSO, 2009-2025) into <data_root>/obsea/{images,videos,metadata}
#
# Source:   https://zenodo.org/communities/obsea/records (yearly DOIs 10.5281/zenodo.<id>; ERDDAP https://data.obsea.es/erddap/tabledap/OBSEA_seabed_station_pictures_L0a)
# Licence:  CC BY 4.0 (tier B), read at record level (Zenodo licence field; ERDDAP global licence agrees)
# Geo:      fixed_site from the publication (41.18212 N, 1.75257 E, 20 m; sites/obsea.csv)
# Size:     about 275 GB of zips (about 2 million JPEG, estimate); media fetched per picture from files.obsea.es, not the zips
#
# Manual steps before running:
#   None (open, no token)
#
# Usage:
#   scripts/download/obsea.sh                    # download (config budget, else everything)
#   scripts/download/obsea.sh --dry-run          # metadata only, no media
#   scripts/download/obsea.sh --budget 500       # stop after 500 selected samples
#   scripts/download/obsea.sh --opt from=2013-01-01   # adapter options: from, to, per_day, years, sensors (see research/obsea.md)
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks (remove if none), e.g.:
# : "${ONC_TOKEN:?set ONC_TOKEN first: see the header of this script}"

exec uv run aquasource download obsea "$@"
