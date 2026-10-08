#!/usr/bin/env bash
# Download UK seabed still photographs (JNCC Bassurelle Sandbank survey, OGL) into <data_root>/uk_seabed/{images,metadata}
#
# Source:   https://ckan.publishing.service.gov.uk/dataset/seabed-videos-from-bassurelle-sandbanks-sci1 (data.gov.uk harvest, JNCC)
#           one zip data.defra.gov.uk/Marine/JNCC2013_03BassSandRawBenthicSamplingvideo.zip, 1.45 GB, read by HTTP Range
#           requests (no full download); it holds 550 station JPEGs (the file name says video, the content is stills)
# Licence:  UK Open Government Licence, tier B, read at record level (CKAN license_id uk-ogl; version not stated there)
# Geo:      region, geo_inferred=true: centre of the survey bounding box (src/aquasource/adapters/sites/uk_seabed.csv),
#           geo_uncertainty_m 9900; the archive has no per-image or per-station coordinates
# Size:     550 JPEG frames, about 2.7 MB each
#
# Manual steps before running:
#   none (no token; anonymous HTTP with Range support)
#
# Usage:
#   scripts/download/uk_seabed.sh                  # all frames (budget from config, else everything)
#   scripts/download/uk_seabed.sh --dry-run        # metadata only: central directory of the archive, no frames
#   scripts/download/uk_seabed.sh --budget 100     # stop after 100 selected frames
#   (the script passes --min-geo-precision region: this dataset is region-level only)
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Region-level geo (survey bounding-box centre) is below the default station minimum, so it is passed here.
exec uv run aquasource --min-geo-precision region download uk_seabed "$@"
