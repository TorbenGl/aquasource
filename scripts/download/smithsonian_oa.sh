#!/usr/bin/env bash
# Download Smithsonian Open Access CC0 images with a marine locality into <data_root>/smithsonian_oa/{images,metadata}
#
# Source:   Smithsonian Open Access, https://www.si.edu/openaccess. Metadata: public AWS bucket smithsonian-open-access
#           (line-delimited EDAN JSON, metadata/edan/<unit>/<NN>.txt, 256 shards per unit, 5-20 MB each). No key.
#           api.si.edu needs an api.data.gov key (API_KEY_MISSING without one) and is not used.
# Licence:  tier A (CC0), read at record level from descriptiveNonRepeating.online_media.media[].usage.access == "CC0".
#           Metadata licence: CC0 1.0, https://github.com/Smithsonian/OpenAccess/blob/master/LICENSE.
#           Other access values are not downloaded.
# Geo:      region precision, geo_inferred false: indexedStructured.geoLocation[].points.point (published collection
#           locality of the specimen, not the camera position); depth from freetext 'Depth (m)' (collection depth).
# Media:    'Screen Image' JPEG derivative from ids.si.edu (not the high-resolution TIFF / JPEG originals).
# Noise:    most records are specimen photographs. Kept, marked extra.maybe_not_underwater=true when no in-situ keyword.
#           Terrestrial records are not downloaded by default (marine_only=true).
# Defaults: units nmnhinv (Invertebrate Zoology) and nmnhfishes; shards are streamed, never stored.
#
# Usage:
#   scripts/download/smithsonian_oa.sh --dry-run                     # metadata only, no images
#   scripts/download/smithsonian_oa.sh --budget 100                   # stop after 100 selected samples
#   scripts/download/smithsonian_oa.sh --opt units=nmnhinv,nmnhfishes,nmnhmammals,nmnhherps
#   scripts/download/smithsonian_oa.sh --opt shards=1 --budget 3      # quick sample: first shard of the first unit
#   Options: units, shards (1..256 per unit), marine_only (true|false), require_coords (true|false).
#
# Manual steps before running: none.
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent).
set -euo pipefail
cd "$(dirname "$0")/../.."

command -v uv >/dev/null 2>&1 || { echo "smithsonian_oa: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

# Region-level geo (specimen collection locality) is below the default station minimum, so it is passed here.
exec uv run aquasource --min-geo-precision region download smithsonian_oa "$@"
