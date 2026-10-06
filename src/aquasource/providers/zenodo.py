"""Zenodo REST helpers (records, files, community search)."""

from __future__ import annotations

import re
from typing import Any, Iterator

from ..core.http import Http

API = "https://zenodo.org/api"

# Zenodo licence ids -> human-readable names that core.licence.classify understands.
LICENCE_NAMES = {
    "cc-zero": "CC0 1.0",
    "cc0-1.0": "CC0 1.0",
    "cc-by": "CC BY",
    "cc-by-4.0": "CC BY 4.0",
    "cc-by-3.0": "CC BY 3.0",
    "cc-by-sa-4.0": "CC BY-SA 4.0",
    "cc-by-nc-4.0": "CC BY-NC 4.0",
    "cc-by-nc-sa-4.0": "CC BY-NC-SA 4.0",
    "cc-by-nd-4.0": "CC BY-ND 4.0",
    "cc-by-nc-nd-4.0": "CC BY-NC-ND 4.0",
}


def record_id(doi_or_id: str | int) -> str:
    s = str(doi_or_id)
    m = re.search(r"zenodo\.(\d+)", s) or re.search(r"records?/(\d+)", s)
    return m.group(1) if m else re.sub(r"\D", "", s)


def get_record(http: Http, doi_or_id: str | int) -> dict[str, Any]:
    return http.get_json(f"{API}/records/{record_id(doi_or_id)}")


def licence_name(record: dict[str, Any]) -> str | None:
    lic = (record.get("metadata") or {}).get("license") or {}
    lid = lic.get("id") if isinstance(lic, dict) else str(lic)
    if not lid:
        return None
    return LICENCE_NAMES.get(lid.lower(), lid)


def is_open(record: dict[str, Any]) -> bool:
    return (record.get("metadata") or {}).get("access_right", "open") == "open"


def files(record: dict[str, Any]) -> list[dict[str, Any]]:
    """[{key, size, checksum, url}] for an open record."""
    out = []
    for f in record.get("files") or []:
        url = (f.get("links") or {}).get("self") or (f.get("links") or {}).get("download")
        out.append({"key": f.get("key") or f.get("filename"), "size": f.get("size") or f.get("filesize"), "checksum": f.get("checksum"), "url": url})
    return out


def search(http: Http, *, q: str = "", community: str | None = None, size: int = 100, max_pages: int = 100) -> Iterator[dict[str, Any]]:
    """Iterate records matching a query / community (newest first)."""
    page = 1
    while page <= max_pages:
        params: dict[str, Any] = {"q": q, "size": size, "page": page, "sort": "newest"}
        if community:
            params["communities"] = community
        data = http.get_json(f"{API}/records", params=params)
        hits = (data.get("hits") or {}).get("hits") or []
        if not hits:
            return
        yield from hits
        if len(hits) < size:
            return
        page += 1


def citation(record: dict[str, Any]) -> str:
    md = record.get("metadata") or {}
    creators = "; ".join(c.get("name", "") for c in md.get("creators", [])[:6])
    year = (md.get("publication_date") or "")[:4]
    doi = record.get("doi") or md.get("doi") or ""
    return f"{creators} ({year}): {md.get('title', '')}. Zenodo. https://doi.org/{doi}".strip()
