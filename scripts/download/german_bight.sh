#!/usr/bin/env bash
# Download German Bight seafloor drift videos into <data_root>/german_bight/{videos,metadata}
#
# Source:   PANGAEA.907386 (HE415/HE416), PANGAEA.909999 (HE436), PANGAEA.831731 (Helgoland 2011)
# Licence:  CC BY 4.0 per PANGAEA record (tier B), read at record level
# Geo:      station: the station Latitude/Longitude next to each movie URL, applied to the whole video
# Size:     ~145 station videos; one AVI is ~175 MB
#
# Manual steps before running:
#   none (some PANGAEA files may sit on tape; a failed download is listed in metadata/failures.jsonl, retry later)
#
# Usage:
#   scripts/download/german_bight.sh                   # all videos
#   scripts/download/german_bight.sh --dry-run         # metadata only, no media
#   scripts/download/german_bight.sh --budget 10       # first 10 videos
#   scripts/download/german_bight.sh --opt 'dataset_ids=["907386"]'
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."
exec uv run aquasource download german_bight "$@"
