#!/usr/bin/env bash
# Download German Bight seafloor drift videos into <data_root>/german_bight/{videos,metadata}
#
# Source:   PANGAEA data tables with links to video files on hs.pangaea.de (AWI Wadden Sea Station Sylt):
#             PANGAEA.907386  R/V Heincke HE415/HE416, Feb-Mar 2014   (87 Kongsberg AVI + 55 GoPro MP4)
#             PANGAEA.909999  R/V Heincke HE436, Nov 2014             (45 AVI + 44 GoPro MP4)
#             PANGAEA.831731  Helgoland transects, Jun 2011           (13 MPEG-2)
#           plus six sibling cruise tables of the same authors and format (siblings=true, default):
#             907382 HE400 (114 MPG), 910009 HE474, 910939 HE478 (Dogger Bank), 907338 HE501,
#             907337 HE502 (3 stations, ASF + MP4 parts), 907340 HE505 (ASF + MP4)
# Licence:  CC BY 4.0 (CC BY 3.0 for PANGAEA.831731), tier B, read at record level from the table header
#           "License:" line and cross-checked with the record JSON-LD. The attribution stored with every
#           sample is the record's "Citation:" line plus the licence. Not the CC BY-NC-ND of the CSR 2019 paper.
# Geo:      station precision, geo_inferred=true: one ship-GPS position per video (columns Latitude/Longitude,
#           depth "Bathy depth [m]"), applied to every frame. geo_uncertainty_m is 200 m for the Heincke tables
#           (inflated to distance + 200 m where the position disagrees with the DSHIP event log by > 300 m: 5 known
#           longitude typos in the seed tables, 2 in HE400) and half the transect length + 30 m for Helgoland.
#           GoPro clips are mapped to their table row by file name (PANGAEA.907386 lists one clip in the wrong row).
# Size:     default media=station: 145 seed videos (AVI median 22 MB, mean 32 MB; Helgoland MPG 110-469 MB) and 419
#           with the siblings, about 16 GB projected (see the "provider total" line of --dry-run). GoPro MP4
#           (--opt media=gopro|all) are 1.3-2.2 GB each: 99 seed clips = ~170 GB, 260 clips = ~450 GB with the
#           siblings. Plan for the station videos only unless the budget is in bytes.
#
# Manual steps before running:
#   none for the default media=station. A GoPro harvest (media=gopro|all, ~450 GB) is beyond sampled use: PANGAEA ToU
#   section 5.5 lets PANGAEA throttle bulk downloads, so ask first (https://www.pangaea.de/contact/).
#   About 40 % of the files sit on tape: the first request answers HTTP 503 and recalls the file, it is online
#   after ~7-15 min. The adapter waits (up to 30 min per file) and HEADs the next files so that recalls overlap;
#   whatever still fails is listed in <data_root>/german_bight/metadata/failures.jsonl: just rerun the script later.
#
# Usage:
#   scripts/download/german_bight.sh                    # all station videos (AVI/MPG/ASF), spread over cruises and areas
#   scripts/download/german_bight.sh --dry-run          # metadata only (tables, JSON-LD, DSHIP events), no media
#   scripts/download/german_bight.sh --budget 30        # stop after 30 selected videos (spread over all cruises)
#   scripts/download/german_bight.sh --opt media=all    # station videos first, then the GoPro 1080p MP4 (huge)
#   scripts/download/german_bight.sh --opt siblings=false                 # only the three seed tables
#   scripts/download/german_bight.sh --opt 'cruises=["HE436","Helgoland2011"]'
#   scripts/download/german_bight.sh --opt qc_reject_m=1000               # drop rows that disagree with the ship log
#   Options: dataset_ids, siblings, cruises, media (station|gopro|all), order (spread|table), qc, qc_reject_m,
#            licence_check, stage_batch, stage_timeout_s, stage_poll_s (see the module docstring of
#            src/aquasource/adapters/german_bight.py).
#   Afterwards: aquasource frames german_bight --every 5   # still frames; it does not trim yet: drop the first/last 60 s
#               of each clip (deck, descent; hints in extra.trim_start_s / trim_end_s) and dark/turbid frames downstream
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "german_bight: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download german_bight "$@"
