#!/usr/bin/env bash
# Download FathomNet (MBARI) CC0 and CC BY images into <data_root>/fathomnet/{images,metadata}
#
# Source:   FathomNet, https://database.fathomnet.org/fathomnet/ (anonymous read API https://database.fathomnet.org/api).
#           Katija, K. et al. (2022) FathomNet: A global image database for enabling artificial intelligence in the ocean.
#           Sci. Rep. 12, 15914. https://doi.org/10.1038/s41598-022-19939-2
#           481,126 image records (2026-10-08); the database stores URLs, the files stay on the contributors' hosts.
# Licence:  tier A (CC0-1.0) and tier B (CC-BY-4.0), read at record level from the field imageLicense of every image.
#           Everything with NC or ND (CC-BY-NC-ND-4.0 240,912 images, CC-BY-NC-4.0 635: MBARI, Schmidt Ocean Institute,
#           NOAA Ocean Exploration, Ocean Networks Canada, ...), null, JPL-image or unknown is NOT downloaded (never upgraded).
#           Usable: 231,631 CC0 frames = NOAA NMFS SEFSC (Mississippi Laboratories) SEAMAP reef-fish drop-camera video frames,
#           Gulf of Mexico, public GCS bucket gs://nmfs_odp_hq/nodd_tools/datasets/gfisher/ (NOAA InPort item 30062:
#           "There are not restrictions or legal prerequisites for accessing this data."), and 16 georeferenced CC-BY-4.0
#           POSCO macroalgae photos off Korea (the other 7,932 CC-BY images are 224 px plankton crops without coordinates).
#           Terms of Use https://www.fathomnet.org/terms, Data Use Policy https://www.fathomnet.org/datause. Attribution stored
#           per sample: the paper citation, image uuid, url and SPDX id, plus the NOAA NMFS / SEAMAP acknowledgement.
# Geo:      station precision, geo_inferred true: fields latitude, longitude, depthMeters of the image record (WGS 84). The
#           coordinate is ONE deployment position per video folder, copied to all frames and camera views (95 distinct
#           positions); uncertainty 200 m (assumption, none published; 2000 m for the 16 POSCO images). Depth 19.7-151.1 m
#           (camera or bottom depth is not stated), null for POSCO. Timestamps exist for about half of the CC0 frames (2021).
# Size:     about 0.35-0.64 MB per 1920x1080/1200 JPEG, about 115 GB if all 231,631 CC0 frames were taken (5 fps frames of
#           ~526 videos, extremely redundant). The default keeps at most 5 frames per video, at least 10 s apart (about
#           2.6 k frames, ~1.3 GB); use --budget N for less. Enumeration reads 161 pages of 1.2 MB under metadata/raw/geoimages/
#           (a budget of 30 reads one page). The order spreads over pages (random uuid), stations and videos.
#
# Manual steps before running:
#   none (no token, no account). Optional: the Terms of Use say an account is needed to use the Database although the read
#   API is open; consider registering and/or asking fathomnet@mbari.org to confirm bulk use of the CC0 / CC BY images for
#   model pretraining. Put the FathomNet acknowledgement and the "benevolent use" (UN SDGs) condition in the dataset card.
#
# Usage:
#   scripts/download/fathomnet.sh                    # download (config budget, else everything the caps allow)
#   scripts/download/fathomnet.sh --dry-run          # metadata only (one 1.2 MB page, counts, one POST), no images
#   scripts/download/fathomnet.sh --budget 500       # stop after 500 selected samples
#   scripts/download/fathomnet.sh --opt frames_per_video=0 --opt min_spacing_s=0    # every frame (huge, redundant)
#   scripts/download/fathomnet.sh --opt max_per_station=300 --opt seed=1
#   Options: tiers (A,B[,C]), order (spread|table), seed, page_size, pages, frames_per_video, min_spacing_s, max_per_station,
#            include_ccby, geo_only, verify_sha256 (see the module docstring of src/aquasource/adapters/fathomnet.py).
#   Re-runs read metadata/raw/; --opt refresh_metadata=true re-reads the API. The database is live: record the access date.
#   Not done: pixel filters (deck / surface / black frames), the 140 source .mp4 videos of the bucket, dedup against other
#             SEFSC keys (extra.video and the record sha256 are the keys).
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "fathomnet: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download fathomnet "$@"
