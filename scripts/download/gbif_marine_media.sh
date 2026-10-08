#!/usr/bin/env bash
# Download GBIF occurrence still photos (CC0 / CC BY per media file) into <data_root>/gbif_marine_media/{images,metadata}
#
# Source:   GBIF occurrence search, https://api.gbif.org/v1/occurrence/search (GBIF.org, read 2026-10-08).
#           Files stay on the publishers' hosts (iNaturalist, Artsobservasjoner, museums, ...).
# Licence:  tier A / B, read per media file (field media[].license; occurrence license only when the media states none).
#           NC / ND / "All rights reserved" / unknown are not downloaded. Research note: research/gbif_marine_media.md.
# Geo:      image precision (seed), fields decimalLatitude, decimalLongitude (WGS 84), coordinateUncertaintyInMeters, depth.
#           Occurrence-level position, geo_inferred false.
# Size:     about 717 k still-image occurrences with coordinates and depth 0-200 m (the API total, 2026-10-08); the API
#           returns at most 100,000 per query (offset cap). Not measured: media bytes per file.
#
# Manual steps before running:
#   none (anonymous API, no token). Keep the per-image attribution (creator, licence, GBIF occurrence) with the samples.
#
# Usage:
#   scripts/download/gbif_marine_media.sh                    # download (config budget, else everything the caps allow)
#   scripts/download/gbif_marine_media.sh --dry-run          # metadata only, no media
#   scripts/download/gbif_marine_media.sh --budget 500       # stop after 500 selected samples
#   scripts/download/gbif_marine_media.sh --opt depth=5,200  # GBIF depth range in metres (default 0,200)
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "gbif_marine_media: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download gbif_marine_media "$@"
