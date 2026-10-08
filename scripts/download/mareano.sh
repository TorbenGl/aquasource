#!/usr/bin/env bash
# Download MAREANO (Norway) geolocated seabed frame grabs into <data_root>/mareano/{images,metadata}
#
# Source:   kart.hi.no OGC API, layer mareano_stasjoner:bilder_biologi (340 frame grabs, 2006-2021, 62-80 N),
#           station check against mareano_stasjoner:videostasjoner_aarlig; images on the HI media archive
#           (hi.imageshop.no, 1,024 px preview JPG). https://www.mareano.no/bilder-og-video
# Licence:  CC BY-SA 4.0, tier C, read at collection level (HI media archive terms). The Geonorge record of the
#           layer says CC BY 4.0: contradiction, kept at C. Tier C is off by default, so this script passes
#           --include-sharealike (samples go to <data_root>/_sharealike/mareano/).
# Geo:      image precision from the layer row's Latitude/Longitude (full precision), depth DYBDE (0 = station
#           BottomDepth); station precision where the point equals the reference station; region / none for QC conflicts.
# Size:     340 JPEG previews, about 0.06 GB (1,024 px, ~176 KB each). The raw video archive is NOT included.
#
# Manual steps before running:
#   none (anonymous HTTPS, no token). The raw video archive (3,908 lines) is on request from datahjelp@hi.no (not implemented).
#
# Usage:
#   scripts/download/mareano.sh                    # all 340 frame grabs (one still per video line first)
#   scripts/download/mareano.sh --dry-run          # metadata only, no media
#   scripts/download/mareano.sh --budget 10        # stop after 10 selected samples
#   scripts/download/mareano.sh --opt seed=3       # other spread order
#   scripts/download/mareano.sh --opt max_per_line=1
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "mareano: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource --include-sharealike download mareano "$@"
