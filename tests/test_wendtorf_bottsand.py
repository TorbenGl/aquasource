"""Offline checks on the saved Zenodo metadata for wendtorf_bottsand (no network, no adapter yet).

The record is CC BY 4.0 (tier B) but its files are restricted and the anonymous files list is empty,
so there is nothing to discover or download. These tests pin that state and the licence tier.
"""

import json
from pathlib import Path

from aquasource.core.licence import classify

FIX = Path(__file__).parent / "fixtures" / "wendtorf_bottsand"


def _load(name: str):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_record_licence_is_cc_by_tier_b():
    rec = _load("zenodo_16085852_record.json")
    licence_id = rec["metadata"]["license"]["id"]
    assert licence_id == "cc-by-4.0"
    assert classify(licence_id) == "B"


def test_record_files_are_restricted_so_no_media_is_listed():
    rec = _load("zenodo_16085852_record.json")
    assert rec["metadata"]["access_right"] == "restricted"
    files = _load("zenodo_16085852_files_anon.json")
    assert files.get("status") == 403
    assert "entries" not in files and not rec.get("files")
