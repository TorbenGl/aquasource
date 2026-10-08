#!/usr/bin/env bash
# Koster Seafloor Observatory (Sweden): BLOCKED, nothing is downloaded.
# Reason: no confirmed open deposit of the observatory video archive; the SND ROV series (snd1069-*) carries a CC BY 4.0
# URL but is marked WITHDRAWN while its access field says openAccess. See research/koster.md (HANDOFF).
echo "koster: blocked. No open, licence-clear deposit confirmed (see research/koster.md)." >&2
exit 1
