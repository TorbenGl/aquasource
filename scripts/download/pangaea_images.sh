#!/usr/bin/env bash
# Download PANGAEA underwater images and videos into <data_root>/pangaea_images/{images,videos,metadata}
#
# Source:   PANGAEA (AWI / MARUM), https://www.pangaea.de/ ; seed series 10.1594/PANGAEA.989682 (MSM77 OFOS),
#           .994607 (SO295, moratorium until 2027-04-22: skipped until it opens), .935856 (SO268 OFOS),
#           .882349 (SO239/SO242 AUV ABYSS), .911904 (PS118 OFOBS), .936205 (PS124 OFOBS), plus the single
#           ROV video 10.1594/PANGAEA.898338 (HE153). Optional: --opt extras=true (curated extra series),
#           --opt discovery=true (Elasticsearch discovery of ~1,100 open CC BY / CC0 datasets).
# Licence:  read per child dataset at record level (table header "License:" / pan_md <md:license>): seeds are
#           CC-BY-4.0 (and CC-BY-3.0 for 882349), tier B. NC / ND children are never listed; a CC BY child under
#           an NC / ND series is tier U. Attribution = the child's PANGAEA citation + licence, stored per sample.
# Geo:      image precision from the table columns Latitude / Longitude (WGS84, ~99 % of the seed images) with
#           an outlier check; otherwise station precision from the Event(s) position of the dataset
#           (geo_inferred true, uncertainty 4000 m or half the start-end distance + 500 m); a video listed in a
#           table row is segment level. Depth from "Depth water [m]" (sign normalised) or the event ELEVATION
#           (never for under-ice cameras). Never invented.
# Dedupe:   exclude_overlap=true (default) skips whole series covered by other keys or copying seed images
#           (957274, 892623, OBSEA, German Bight videos ...); at most max_videos_per_series=2 videos per series.
# Size:     seeds ~437 k open images (~430 GB: AUV 140 GB, SO268 145 GB, PS118 65 GB, PS124 70 GB, MSM77 10 GB)
#           plus one 3.45 GB MPEG video. ALWAYS use --budget for sampling: the default order is spread over
#           series, children and time, so --budget N is a representative sample.
#
# Manual steps before running:
#   none for sampled runs (a few thousand files per day at <= 1 request/s per host).
#   A full-archive harvest (more than ~100 GB or many thousand files per day) needs PRIOR AUTHORISATION from
#   PANGAEA (terms of use section 5.5, contact via https://www.pangaea.de/contact/); then set
#   PANGAEA_BULK_AUTHORISED=1 to run without --budget. Files on tape answer HTTP 503 until staged (1-3 min per
#   file); the adapter waits, retries and never stores an HTML page. A failed file is listed in
#   metadata/failures.jsonl and is retried on the next run.
#
# Usage:
#   scripts/download/pangaea_images.sh --dry-run --budget 30      # metadata only, no media
#   scripts/download/pangaea_images.sh --budget 500               # 500 selected samples
#   scripts/download/pangaea_images.sh --budget 500 --opt extras=true
#   scripts/download/pangaea_images.sh --opt 'series=["989682"]' --opt max_per_child=20
#   scripts/download/pangaea_images.sh --opt order=table          # file order instead of the spread order
#   adapter options (--opt name=value): series, datasets, extras, discovery, discovery_max, exclude,
#   exclude_overlap, check_parent, order, max_per_child, max_per_series, max_videos_per_series, keep_flagged,
#   depth_filter, drop_sw_files, prefer_raw, max_table_mb, stage_batch, stage_timeout_s (see the module
#   docstring of src/aquasource/adapters/pangaea_images.py and research/pangaea_images.md)
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent so
#              PANGAEA can reach you; please set it); PANGAEA_BULK_AUTHORISED=1 (only after PANGAEA agreed to a
#              full harvest)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite check: refuse an unbounded harvest (~430 GB) unless PANGAEA agreed to it.
bounded=0
for arg in "$@"; do
  case "$arg" in
    --budget|--budget=*|--dry-run|-h|--help) bounded=1 ;;
  esac
done
if [ "$bounded" = 0 ] && [ "${PANGAEA_BULK_AUTHORISED:-}" != "1" ]; then
  echo "pangaea_images: refusing an unbounded run (about 430 GB). Pass --budget N or --dry-run." >&2
  echo "  A full harvest needs PANGAEA's prior authorisation (ToU 5.5); then export PANGAEA_BULK_AUTHORISED=1." >&2
  exit 2
fi
if [ -z "${AQUASOURCE_CONTACT:-}" ]; then
  echo "pangaea_images: note: AQUASOURCE_CONTACT is not set; PANGAEA cannot reach you if a request pattern worries them." >&2
fi

exec uv run aquasource download pangaea_images "$@"
