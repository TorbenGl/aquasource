#!/usr/bin/env bash
# Download NOAA Deep-Sea Coral and Sponge Database images (NOAA-provider records only) into <data_root>/noaa_dsc/{images,metadata}
#
# Source:   NCEI accession 0145037 https://www.ncei.noaa.gov/archive/accession/0145037 (DOI https://doi.org/10.25921/t8c0-yx22)
#           read through the public ERDDAP table https://www.ncei.noaa.gov/erddap/tabledap/deep_sea_corals
#           (one metadata query: DataProvider starts with NOAA and ImageURL set; cached in metadata/raw/).
#           Media: image URLs under https://www.ncei.noaa.gov/waf/dsc-data/images/ (JPEG, 40 KB to 3.3 MB).
# Licence:  tier A for images whose DataProvider is NOAA alone (US government work, no licence stated, ISO accessLevel
#           public; collection level). Tier U for NOAA co-provider records ("NOAA, ... | University of ..."): partner
#           copyright possible, not downloaded by default. Non-NOAA providers are not queried.
# Geo:      image precision from the record's latitude/longitude and DepthInMeters (geo_inferred=false). One candidate per
#           image URL; several records of one image keep the lowest CatalogNumber (extra.geo_conflict flags a clash).
# Size:     about 134 k NOAA-provider image URLs (2026-10-08 distinct check): about 110 k NOAA-only (tier A) and about 24 k
#           co-provider (tier U). JPEGs of 40 KB to 3.3 MB (sample: 2.7-3.3 MB each), roughly 400 GB for the whole set at that size. Use --budget N for a sample.
#
# Manual steps before running:
#   none. Anonymous HTTPS, no token. The ERDDAP query is one large request (several minutes) on the first run.
#   Politeness: about 1 request per second to www.ncei.noaa.gov; the ERDDAP answer is cached, so a re-run reuses it.
#
# Usage:
#   scripts/download/noaa_dsc.sh                         # download (config budget, else everything: very large)
#   scripts/download/noaa_dsc.sh --dry-run               # metadata only (one ERDDAP query), no media
#   scripts/download/noaa_dsc.sh --budget 3              # stop after 3 selected images
#   scripts/download/noaa_dsc.sh --opt timeout_s=1200    # longer timeout for the ERDDAP query
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "noaa_dsc: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download noaa_dsc "$@"
