#!/usr/bin/env bash
# Download Seatizen Atlas session images (EXIF GPS) into <data_root>/seatizen/{images,metadata}
#
# Source:   Seatizen Atlas index deposit, https://zenodo.org/records/18211765 (Zenodo community seatizen-data; 589 session
#           deposits listed in session_doi.csv). Contini, M. et al. (2025) Seatizen Atlas: a collaborative dataset of
#           underwater and aerial marine imagery. Scientific Data, https://doi.org/10.1038/s41597-024-04267-z
# Licence:  read per session deposit (record level, field license.id of https://zenodo.org/api/records/<id>); all sessions
#           sampled so far are cc-by-4.0 (tier B). CC BY-NC / ND / restricted sessions are not downloaded (never upgraded).
#           The index record itself is cc-by-4.0 at collection level and is not used for the samples.
# Geo:      image precision, geo_inferred false: GPSLatitude / GPSLongitude of the session METADATA.zip > metadata.csv
#           (camera EXIF GPS, WGS 84). No uncertainty published; no depth. Images without GPS are dropped (geo_only=false keeps them).
#           Open question: underwater GPS fixes (see research/seatizen.md doubts).
# Size:     DCIM.zip per session 0.3-16 GB; each image is about 2.5-4.5 MB. Only the selected members are read, with HTTP
#           range requests (no whole-zip download). Each session metadata archive is about 13 kB-2 MB.
#
# Manual steps before running:
#   none (anonymous Zenodo API and file downloads, no token)
#
# Usage:
#   scripts/download/seatizen.sh                    # download (config budget, else everything the caps allow)
#   scripts/download/seatizen.sh --dry-run          # metadata only (session records and METADATA.zip archives), no images
#   scripts/download/seatizen.sh --budget 500       # stop after 500 selected samples
#   scripts/download/seatizen.sh --opt max_per_session=50 --opt seed=1
#   Options: tiers (A,B), order (spread|table), seed, max_per_session (0 = all), geo_only (true), platforms (scuba,uvc,asv,aerial)
#            (see the module docstring of src/aquasource/adapters/seatizen.py). Aerial (UAV / KITE) images are kept and
#            marked extra.maybe_not_underwater=true.
#   Re-runs read metadata/raw/; --opt refresh_metadata=true re-reads Zenodo. The index is live: record the access date.
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "seatizen: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download seatizen "$@"
