#!/usr/bin/env bash
# Download the USGS CMGP Video and Photograph Portal seafloor STILLS into <data_root>/usgs_cmgp/{images,metadata}
#
# Source:   Coastal and Marine Geology Program (CMGP) Video and Photograph Portal, USGS data release
#           https://doi.org/10.5066/F7JH3J7N (Golden, Ackerman and Dailey 2015), served by Axiom Data Science at
#           https://video.ioos.us/ ; release page https://www.usgs.gov/data/coastal-and-marine-geology-video-and-photograph-portal
#           Index: GeoServer WFS https://data.axds.co/gs/{wfs,usgs_imagery/wfs,usgs_pacific/wfs} (no auth).
#           Photos: https://servomatic9000.axiomalaska.com/photo-server/usgs/<album>/<id>/photo? (legacy Axiom host).
# Licence:  tier A. "This work is marked with CC0 1.0 Universal" (release page) and FGDC <useconst>: "USGS-authored or produced
#           data and information are in the public domain from the U.S. Government and are freely redistributable with proper
#           metadata and source attribution" (https://data.usgs.gov/datacatalog/metadata/USGS.fa1a6827-fbde-442a-80f6-b607892854a5.xml).
#           Read at record level; no per-file licence. Only the 6 USGS-authored layers with photos are used; the non-USGS layers
#           of the portal (CSU Monterey Bay CUIA) and ~70 above-water aerial layers are never read.
# Geo:      image precision, geo_inferred false: WFS properties.lat/lon of the photo's row (vessel GPS fix matched to the photo,
#           5-6 decimals), uncertainty 10 m (provider: vessel offset "typically +/- 10 meters"). No depth field (depth_m null).
# Size:     ~117,600 stills (California 78,341; Hawaii/Pacific 28,079; Massachusetts 8,083; Rhode Island 1,793; Puget Sound 918;
#           old California 415), 1983-2016, total ~0.2-0.25 TB (California ~2.7 MB each, Massachusetts ~1.3 MB, Hawaii ~0.1 MB).
#           The default order is budget friendly (layers by sqrt(rows), windows spread over each table, <= 5 photos per album).
#
# Manual steps before running:
#   none for the stills (no token, no account). The VIDEOS exist only on YouTube (channel "CMG Video"): fetching them needs a
#   human decision about YouTube's terms and is NOT done here (option videos=true is rejected). Alternative: ask the USGS PCMSC
#   data coordinator for the original files. Not done: pixel filters (sled off bottom, water column, deck, burned-in overlay text,
#   laser dots) and the navigation speed check for single stills.
#
# Usage:
#   scripts/download/usgs_cmgp.sh                    # download (config budget, else everything the caps allow)
#   scripts/download/usgs_cmgp.sh --dry-run          # metadata only (WFS counts + a few 200-row pages), no images
#   scripts/download/usgs_cmgp.sh --budget 500       # stop after 500 selected samples
#   scripts/download/usgs_cmgp.sh --opt layers=california,puget_sound --opt max_per_album=0 --opt order=table
#   Options: layers (california,hawaii_pacific,massachusetts,rhode_island,puget_sound,california_old), order (spread|table),
#            seed, page_size, per_window, max_per_album, windows, geo_only (see the module docstring of
#            src/aquasource/adapters/usgs_cmgp.py).
#   The photo server ignores HTTP Range: an interrupted file restarts from zero. Re-runs read metadata/raw/wfs/.
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "usgs_cmgp: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download usgs_cmgp "$@"
