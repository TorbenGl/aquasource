#!/usr/bin/env bash
# Download <DATASET NAME> into <data_root>/<key>/{images,videos,metadata}
#
# Source:   <landing page / DOI>
# Licence:  <licence as read> (tier <A|B|C|U>), read at <file|record|collection> level
# Geo:      <precision> from <geo_source>
# Size:     <counts / bytes>
#
# Manual steps before running:
#   <none | e.g. export ONC_TOKEN=... (free account at https://data.oceannetworks.ca)>
#
# Usage:
#   scripts/download/<key>.sh                    # download (config budget, else everything)
#   scripts/download/<key>.sh --dry-run          # metadata only, no media
#   scripts/download/<key>.sh --budget 500       # stop after 500 selected samples
#   scripts/download/<key>.sh --opt name=value   # adapter options (see research/<key>.md)
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks (remove if none), e.g.:
# : "${ONC_TOKEN:?set ONC_TOKEN first: see the header of this script}"

exec uv run aquasource download <key> "$@"
