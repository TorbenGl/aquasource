#!/usr/bin/env bash
# Download NOAA HabCam (NEFSC) 2015 Sea Scallop Survey stereo images into <data_root>/noaa_habcam/{images,metadata}
#
# Source:   NOAA InPort item 27598, https://www.fisheries.noaa.gov/inport/item/27598 (HabCam, Northeast Fisheries Science Center)
#           Images: VIAME Web public "Training Data" (Kitware), https://viame.kitware.com, folder US_NE_2015_NEFSC_HABCAM/Corrected
#           (119,461 PNG). Navigation: R2R r2rnav "Best Resolution" GeoCSV, NCEI accessions 0260576, 0206224, 0206225.
# Licence:  tier A (CC0 1.0), read at record level: data.gov DCAT entry https://catalog.data.gov/dataset/habitat-mapping-camera-habcam
#           (license = CC0). Contradiction to review: the NOAA ISO record says useConstraints otherRestrictions and non-public access.
#           Navigation: CC0 / Public Domain Mark 1.0 (R2R-License in bag-info.txt). CFF 2017-2019 subsets (tier U) are not downloaded.
# Geo:      segment precision, geo_inferred true: 1-s ship GPS (R2R) interpolated at the UTC time of the filename, uncertainty 300 m.
#           No depth (metadata.txt Altitude is height above the seabed, stored in extra.altitude_m).
# Size:     about 5.45 MB per stereo PNG (2720x1024), 650.9 GB for all 119,461 frames. metadata.txt 9.5 MB, navigation 163 MB.
#
# Manual steps before running:
#   none (public API, no token, no account)
#
# Usage:
#   scripts/download/noaa_habcam.sh                    # download (config budget, else everything)
#   scripts/download/noaa_habcam.sh --dry-run          # metadata only (about 120 listing pages, cached), no images
#   scripts/download/noaa_habcam.sh --budget 500       # stop after 500 selected samples
#   scripts/download/noaa_habcam.sh --opt from=2015-06-01 --opt to=2015-06-21
#   scripts/download/noaa_habcam.sh --opt order=table  # name order instead of the spread order
#   Options: order (spread|table), min_spacing_s (60), from, to (YYYY-MM-DD), altitude (true|false)
#            (see the module docstring of src/aquasource/adapters/noaa_habcam.py).
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

command -v uv >/dev/null 2>&1 || { echo "noaa_habcam: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download noaa_habcam "$@"
