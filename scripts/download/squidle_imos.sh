#!/usr/bin/env bash
# Download SQUIDLE+ / IMOS AUV Facility seafloor imagery (AUV Sirius, Nimbus, Holt) into <data_root>/squidle_imos/{images,metadata}
#
# Source:   IMOS Autonomous Underwater Vehicles Facility (ACFR, The University of Sydney), indexed by SQUIDLE+ (https://squidle.org).
#           Files come from the public anonymous AWS bucket imos-data (ap-southeast-2):
#             per-dive navigation CSV  IMOS/AUV/auv_viewer_data/csv_outputs/<campaign>/DATA_<campaign>_<dive>.csv
#             images                   IMOS/AUV/auv_viewer_data/images/<campaign>/<dive>/{full_res,thumbnails}/<image>.jpg
#           69 campaigns, 906 dives, 7.60 M downward-looking still images (one camera of each stereo pair), 2007-09 to 2023-10,
#           around Australia (GBR, Coral Sea, Ningaloo, Scott Reef, WA, SA, Tasmania, Victoria, NSW, Qld). JPEG only, no video.
#           Other SQUIDLE+ platforms (SOI ROV = excluded NC-SA, CSIRO, RLS, IMAS, BOSS dropcams ...) are not in the bucket,
#           have no licence in SQUIDLE+ (tier U) and are not downloaded here.
# Licence:  tier B, CC BY 4.0, read at record level from the AODN catalogue (ISO 19115-3 MD_LegalConstraints, "Creative Commons
#           Attribution 4.0 International License", http://creativecommons.org/licenses/by/4.0/): Sirius fe81b24e-adee-4c77-a8e1-e8a77cfd3dff
#           and Nimbus 8dfa2b64-4eed-491c-ba5e-645ea9409d4d (record level); ACFR AUV Holt (GeographeBay201505) has no platform record
#           and uses the facility record af5d0ff9-bb9c-4b7c-a63c-854a630b6984 (collection level, it links the whole IMOS/AUV/ prefix).
#           SQUIDLE+ itself has no licence field (only an acknowledgement). NC / ND / research-only text in a record makes it tier X,
#           an unreadable record tier U. Attribution stored per sample: the IMOS acknowledgement quoted in the record ("Data was
#           sourced from Australia's Integrated Marine Observing System (IMOS) ..."), the citation form it asks for ("IMOS <year>,
#           IMOS - Autonomous Underwater Vehicles - AUV <platform> (campaign <c>), <URL>, accessed <date>") and its credit lines.
# Geo:      image precision, geo_inferred=false, no uncertainty: every image row of the dive CSV has its own post-processed AUV
#           navigation fix (latitude, longitude, WGS 84). depth_m = depth_sensor (vehicle / camera depth; values outside 0-11000 are
#           dropped); seafloor depth is in extra.seafloor_depth_m. Rows without a usable fix are skipped.
# Size:     whole archive about 8-9 TB at full resolution (+-30 %): 0.2-0.3 MB per image before 2020, 1.7-8 MB (4112x3008) from 2020 on.
#           The default keeps frames >= 30 s apart with altitude 0.5-6 m (about 1/30 of the frames) and drops the second stereo
#           camera (*_AC16): use --budget N for less. The order is spread over campaigns, dives and time (one frame of every
#           campaign first). metadata/raw/ keeps the dive CSVs that were read (3.6 MB each on average): about 100 MB per 30 samples
#           because every campaign needs one CSV, 3.3 GB if every dive is read.
#
# Manual steps before running:
#   none. Anonymous HTTPS, no token. Optional: a free SQUIDLE+ account and API token (X-Auth-Token) enables /api/media/export, which
#   is not needed. Optional: ask IMOS / ACFR for the licence of Hawaii201801, TasFracture202106 and PortPhillipBay202301 (served only
#   from data.acfr.usyd.edu.au, no AODN record, no S3 copy: not read here).
#   Politeness: 0.25 s between requests to the S3 hosts, 1 s to squidle.org and the AODN catalogue; one download at a time.
#
# Usage:
#   scripts/download/squidle_imos.sh                    # everything that passes the filters (very large: use --budget)
#   scripts/download/squidle_imos.sh --dry-run          # metadata only (S3 listings, dive CSVs, AODN records), no images
#   scripts/download/squidle_imos.sh --budget 500       # stop after 500 selected images, spread over campaigns / dives / time
#   scripts/download/squidle_imos.sh --opt campaigns=GBR200709,Apollo202309 --opt frames_per_dive=5
#   scripts/download/squidle_imos.sh --opt from=2015-01-01 --opt to=2019-12-31 --opt image=thumbnail    # 453x341 low-res pass
#   scripts/download/squidle_imos.sh --opt min_spacing_s=0 --opt twins=keep                              # every frame, both cameras
#   scripts/download/squidle_imos.sh --opt route=squidle --opt deployments=213,22                        # poses from SQUIDLE+ exports
#   Options: campaigns, from, to, min_spacing_s, altitude_min, altitude_max, frames_per_dive, twins (drop|keep), image
#            (full_res|thumbnail), order (spread|table), route (s3|squidle), deployments, accessed (see the module docstring of
#            src/aquasource/adapters/squidle_imos.py).
#   Re-runs read metadata/raw/ (s3/, csv/, aodn/, squidle/); --opt refresh_metadata=true re-reads the providers.
#   Not done: dark-frame filter (JPEG size / luminance), dedup against benthicnet / BENTHOZ-2015 (same campaign/dive/image_filename
#             key in extra.dedup_key), the data.acfr.usyd.edu.au copies (different bytes, never used).
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "squidle_imos: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download squidle_imos "$@"
