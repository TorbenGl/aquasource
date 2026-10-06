"""CKAN action API helpers (open.canada.ca, data.gov.au, data.gov.uk, ...)."""

from __future__ import annotations

from typing import Any, Iterator

from ..core.http import Http


def package_show(http: Http, base: str, package_id: str) -> dict[str, Any]:
    data = http.get_json(f"{base.rstrip('/')}/api/3/action/package_show", params={"id": package_id})
    if not data.get("success"):
        raise RuntimeError(f"CKAN package_show failed for {package_id}")
    return data["result"]


def package_search(http: Http, base: str, q: str, *, rows: int = 100, max_pages: int = 20, fq: str | None = None) -> Iterator[dict[str, Any]]:
    start = 0
    for _ in range(max_pages):
        params: dict[str, Any] = {"q": q, "rows": rows, "start": start}
        if fq:
            params["fq"] = fq
        data = http.get_json(f"{base.rstrip('/')}/api/3/action/package_search", params=params)
        results = (data.get("result") or {}).get("results") or []
        if not results:
            return
        yield from results
        start += rows
        if start >= (data.get("result") or {}).get("count", 0):
            return


def licence_name(package: dict[str, Any]) -> str | None:
    return package.get("license_title") or package.get("license_id")
