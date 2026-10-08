#!/usr/bin/env bash
# Download NOAA Ocean Exploration ROV video segments (low-res MP4) into <data_root>/noaa_oe/{videos,metadata}
#
# Source:   NOAA NCEI video portal https://www.ncei.noaa.gov/access/ocean-exploration/video/ ; its search is the OneStop
#           granule index of data.noaa.gov (POST https://data.noaa.gov/onestop/api/search/search/granule, project
#           NOAAOceanExploration, about 112 k granules). One granule = one ~5 min segment of one camera of one dive.
#           Media: https://www.ncei.noaa.gov/data/oceans/oer/video/<cruise>/Video/<dive folder>/Compressed/*_Low.mp4
# Licence:  tier A (US government work, NOAA / NCEI; no licence stated on the records; ISO accessLevel public). Read at
#           collection level. A record containing "copyright" / "all rights reserved" is tier U (not downloaded).
#           Attribution: cruise citation (landing page under Documentation), segment id, portal URL.
# Geo:      segment precision, geo_inferred=true: centre of the segment's spatialBounding polygon (OneStop granule);
#           geo_uncertainty_m = half the box diagonal. Granules without a polygon: geo none (kept in the log, not sampled).
#           depth_m from "between A m and B m" in the description (empty for the 0.0 m placeholder).
# Size:     whole project: about 112 k granules, mostly 360P low-res MP4 of about 1.5 Mbit/s (about 56 MB per 5-minute
#           segment); the full history is many TB. Use --budget N for a sample.
#
# Manual steps before running:
#   none. Anonymous HTTPS, no token. The index and the media are public.
#   Politeness: about 1 request per second to data.noaa.gov and www.ncei.noaa.gov; the index pages are cached under
#   metadata/raw/search/, so a re-run reuses them.
#
# Usage:
#   scripts/download/noaa_oe.sh                          # download (config budget, else everything: very large)
#   scripts/download/noaa_oe.sh --dry-run                # metadata only (index pages), no media
#   scripts/download/noaa_oe.sh --budget 3               # stop after 3 selected segments
#   scripts/download/noaa_oe.sh --opt from=2025-05-01 --opt to=2025-05-31   # one month
#   scripts/download/noaa_oe.sh --opt pages=5            # visit at most 5 index pages (500 granules)
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "noaa_oe: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download noaa_oe "$@"
