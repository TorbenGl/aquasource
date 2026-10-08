#!/usr/bin/env bash
# LoVe Ocean Observatory (Norway, IMR): BLOCKED, nothing is downloaded.
# Reason: licence not read (Use constraint empty in the snippets seen), node metadata records return HTTP 401/404,
# no open media endpoint or API found. See research/love_observatory.md (HANDOFF).
echo "love_observatory: blocked. Licence unread and no accessible media endpoint (see research/love_observatory.md)." >&2
exit 1
