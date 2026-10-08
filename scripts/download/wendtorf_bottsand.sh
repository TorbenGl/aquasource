#!/usr/bin/env bash
# Download wendtorf_bottsand (Zenodo 10.5281/zenodo.16085852) into <data_root>/wendtorf_bottsand/{images,videos,metadata}
#
# Source:   https://doi.org/10.5281/zenodo.16085852 (Carlson, Zenodo 2025)
# Licence:  CC BY 4.0 (record level, https://zenodo.org/api/records/16085852), tier B
# Geo:      image-level EXIF positions in geotagged_continuous.zip (planned; not reachable)
# Size:     4694 geotagged frames (zip), not measured: files are restricted
#
# BLOCKED: the record access_right is "restricted". The files list is empty for anonymous
# requests (HTTP 403). The owner must grant access (Zenodo request-access button) before any download.
# This script prints the reason and exits 1 until a working adapter exists.
set -euo pipefail
cd "$(dirname "$0")/../.."

echo "wendtorf_bottsand is blocked: Zenodo record 16085852 has access_right=restricted (files need login/owner approval)." >&2
echo "See research/wendtorf_bottsand.md (HANDOFF) and https://zenodo.org/records/16085852" >&2
exit 1
