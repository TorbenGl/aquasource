#!/usr/bin/env bash
# Download geotagged underwater photos and videos from Wikimedia Commons into <data_root>/wikimedia_commons/{images,videos,metadata}
#
# Source:   Wikimedia Commons, https://commons.wikimedia.org (MediaWiki API https://commons.wikimedia.org/w/api.php).
#           Categories Underwater photographs and Underwater videos (options: categories=...).
# Licence:  per file, read at file level from imageinfo.extmetadata LicenseShortName / LicenseUrl on each description page.
#           Tier A (PD, CC0), B (CC BY 3.0/4.0), C (CC BY-SA, not selected by the default config). NC / ND / fair use and
#           anything unrecognised is tier X or U and is NOT downloaded. Tier is never upgraded. Attribution per file (author,
#           title, licence, page URL). Commons Terms of Use: https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
# Geo:      image precision, geo_source = GeoData prop=coordinates of the File page (EXIF GPS or {{Location}} template as
#           stored by Commons, not verified). Not inferred, no uncertainty. Files without coordinates are skipped.
# Size:     mixed. Photos 0.2-20 MB, videos 2 MB to several GB; files above 500 MB are skipped (option max_bytes).
#           Only about 1 file in 8 of these categories has coordinates: the budget run reads a few category pages.
#
# Manual steps before running:
#   none (anonymous API). Optional: set AQUASOURCE_CONTACT for the User-Agent.
#
# Usage:
#   scripts/download/wikimedia_commons.sh                    # download (config budget, else everything selected)
#   scripts/download/wikimedia_commons.sh --dry-run          # metadata only (category pages), no media
#   scripts/download/wikimedia_commons.sh --budget 500       # stop after 500 selected samples
#   scripts/download/wikimedia_commons.sh --opt categories="Underwater photographs,Coral reefs"
#   Options: categories, tiers (A,B,C), geo_only, max_bytes (see the module docstring of
#            src/aquasource/adapters/wikimedia_commons.py).
#   Re-runs read metadata/raw/categories/; --opt refresh_metadata=true re-reads the API.
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "wikimedia_commons: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download wikimedia_commons "$@"
