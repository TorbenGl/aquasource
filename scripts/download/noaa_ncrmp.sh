#!/usr/bin/env bash
# Download NOAA NCRMP benthic photo-quadrats (US Pacific, PIFSC ESD) into <data_root>/noaa_ncrmp/{images,metadata}
#
# Source:   NCEI archive, 38 accessions 2013-2019 and 2022-2025 (InPort collections 71813 climate stations,
#           71814 stratified random sites, 59193 the 2019 bleaching event; the table is built into the adapter):
#             https://www.ncei.noaa.gov/data/oceans/archive/<arc>/<acc>/<ver>/data/0-data/   (Apache listings, Range supported)
#           Hawaii (main + Northwestern islands), Mariana Archipelago, American Samoa, Pacific Remote Island Areas.
#           Diver photo-quadrats shot straight down from a 1 m monopod, about 30 per site visit, 0-30 m depth. JPEG only.
# Licence:  tier A. The six 2024-2025 accessions (0317534, 0317535, 0317752, 0317753, 0317785, 0317786) carry an explicit
#           CC0 1.0 dedication in their NCEI record (read at record level from the ISO XML). All older accessions (2013-2023)
#           state no licence: NOAA / PIFSC (US federal) works, NCEI accessLevel "public", citation request only; their tier A
#           is read at collection level from the InPort XML of 71813 / 71814 / 59193 (data-access-constraints "None", citation
#           request, ESD "Data Sharing Recommendations"). Nothing NC / ND / research-only exists; if the record or the InPort
#           collection ever shows such a term the adapter makes it tier X (other access constraints: U; nothing read: U).
#           Attribution = the accession's "Cite as" text verbatim (author string varies by year; parent collection and DOI
#           kept, only the "[indicate subset used]" / "Accessed [date]" placeholders dropped) plus the ESD / CRCP acknowledgement.
# Geo:      station precision, geo_inferred=true, geo_uncertainty_m=50. LATITUDE / LONGITUDE of the per-accession site-info
#           CSV (handheld GPS of the boat over the divers' buoy, WGS 84), joined on SITE (OCC_SITEID for the 2019 NWHI and 2022
#           Marianas climate sets) = the site code that starts the file name SITE_YEAR[_REP]_NN.JPG; one position per site visit,
#           applied to every frame. The join is always inside the same accession (codes are reused / renamed across years).
#           A code missing from the CSV falls back to the cover table of NCEI 0317416 / 0317464 (16 sites of 0268773, one of
#           0317786), else geo none (dropped by the runner): OAH-B3096 of 0270550, 4 stray IMG_39xx.JPG of 0268773, and
#           KUR-50 of 0159172, whose row 28.37653, -178.37653 repeats the latitude decimals in the longitude (copy error).
#           Depth: mean(MIN_DEPTH, MAX_DEPTH) feet x 0.3048 from the cover tables (about 545 MB streamed once, reduced to a
#           ~0.5 MB table in metadata/raw/cover/); empty for about a fifth of the visits (the cover tables have no 2013-2014
#           rows, nor rows for 0276273, 0270550 and the NWHI half of 0240600).
#           0268773 also holds 1,422 oblique site / habitat photos (SITE_2015_SITE_A_NN.JPG): same station as their visit,
#           taken after its photo-quadrats (extra.image_kind = site_photo).
# Size:     whole archive: about 0.22 M images (20,068 climate + about 197 k StRS), about 1.57 TB (3-16 MB per image; Canon
#           PowerShot S100 4000x3000 in 2013-2015, G9 X / G7 X 5472x3648 later). The default takes 3 frames per site visit
#           (about 7,300 visits): about 22 k images, about 160 GB. Use --budget N for less: the order is spread over regions,
#           years and cruise tracks, one frame per visit first (distinct stations for N < 7,300). --opt frames_per_visit=all
#           is everything.
#
# Manual steps before running:
#   none. Anonymous HTTPS, no token. Optional: ask PIFSC ESD (InPort 71813 data steward) for the 2010-2012 RAMP photo-quadrats
#   (they exist, named in the cover tables, but are not at NCEI) or for an explicit licence statement for the pre-2024 accessions.
#   Politeness: 1 request per second to www.ncei.noaa.gov, one download at a time; the server sometimes resets TLS, the client
#   retries with back-off. Re-runs reuse metadata/raw/ and skip finished files.
#
# Usage:
#   scripts/download/noaa_ncrmp.sh                    # 3 frames per site visit, spread over regions / years / sites
#   scripts/download/noaa_ncrmp.sh --dry-run          # metadata only (listings, site-info CSVs, ISO + InPort records, cover tables)
#   scripts/download/noaa_ncrmp.sh --budget 500       # stop after 500 selected images (500 distinct stations)
#   scripts/download/noaa_ncrmp.sh --opt kind=climate --opt years=2024,2025          # fixed sites, recent years
#   scripts/download/noaa_ncrmp.sh --opt regions=marianas,samoa --opt frames_per_visit=1
#   scripts/download/noaa_ncrmp.sh --opt accessions=0317534,0317535                  # CC0 accessions of 2024
#   scripts/download/noaa_ncrmp.sh --opt frames_per_visit=all                        # the whole archive (1.57 TB)
#   scripts/download/noaa_ncrmp.sh --opt depth=off                                   # skip the 545 MB of cover tables
#                                                    (no depth, and no coordinate fallback: 17 visits get geo none)
#   Options: accessions, kind (all|climate|strs), regions (hawaii|marianas|samoa|pria), years, from, to, frames_per_visit
#            (N|all), order (spread|table), climate_share, depth (cover|off) (see the module docstring of
#            src/aquasource/adapters/noaa_ncrmp.py).
#   Re-runs read metadata/raw/ (listing/, siteinfo/, iso/, inport/, cover/); --opt refresh_metadata=true re-reads NCEI.
#   Not done: slate / hand and black-frame filters, EXIF Orientation (apply it downstream; extra.exif_note), cross-accession
#             site identity (permanent sites were renamed, e.g. JOH-07 -> OCC-JOH-004: split by extra.station_id per accession).
#
# Environment: AQUASOURCE_DATA_ROOT (default ./data); AQUASOURCE_CONTACT (optional, added to the User-Agent)
set -euo pipefail
cd "$(dirname "$0")/../.."

# Prerequisite checks: anonymous HTTPS only, so only uv is needed.
command -v uv >/dev/null 2>&1 || { echo "noaa_ncrmp: 'uv' is not installed (https://docs.astral.sh/uv/)" >&2; exit 1; }

exec uv run aquasource download noaa_ncrmp "$@"
