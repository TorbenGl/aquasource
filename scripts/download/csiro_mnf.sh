#!/usr/bin/env bash
# Download CSIRO MNF RV Investigator voyage IN2023_V05 Deep Towed Camera stills into <data_root>/csiro_mnf/{images,metadata}
#
# Source:   DAP image collection csiro:74006, DOI 10.25919/gddy-hn24 (https://data.csiro.au/collection/csiro:74006)
#           RDA record 3970151 (https://researchdata.edu.au/rv-investigator-voyage-imagery-data/3970151)
# Licence:  Creative Commons Attribution 4.0 International, tier B, read at record level (DAP licence 1121,
#           https://data.csiro.au/dap/ws/v2/licences/1121). The DAP "rights" field reads "All Rights (including copyright)
#           CSIRO 2026."; the attribution stored with every sample is the DOI citation plus the MNF acknowledgement.
# Geo:      image precision, geo_source "STILLS.CSV Latitude/Longitude/Depth" (per still, geo_inferred=false)
# Size:     346,715 stills (3.78 TB collection incl. video). The one-shot file listing is about 1.36 GB of JSON and is cached
#           in metadata/raw/listing.json. Still JPEGs are 13-16 MB each (sampled).
#
# Manual steps before running:
#   none: anonymous access (dataRestricted=FALSE). Presigned S3 links expire after 2 days, so they are never stored.
#
# Usage:
#   scripts/download/csiro_mnf.sh                    # all deployments with coordinates (huge: plan a budget)
#   scripts/download/csiro_mnf.sh --dry-run          # metadata only (listing + STILLS.CSV per deployment), no media
#   scripts/download/csiro_mnf.sh --budget 500       # stop after 500 selected stills (spread over deployments)
#   scripts/download/csiro_mnf.sh --opt 'deployments=["IN2023_V05_005"]'   # one deployment
#   scripts/download/csiro_mnf.sh --opt max_rows=100                       # cap stills per deployment
#   Options: deployments (list), max_rows (per deployment). See the module docstring of
#            src/aquasource/adapters/csiro_mnf.py.
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "csiro_mnf: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download csiro_mnf "$@"
