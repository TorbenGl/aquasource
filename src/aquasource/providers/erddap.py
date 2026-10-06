"""ERDDAP tabledap helpers."""

from __future__ import annotations

import csv
import io
from typing import Any
from urllib.parse import quote

from ..core.http import Http


def tabledap_csv_url(base: str, dataset: str, variables: list[str], constraints: list[str] | None = None) -> str:
    """``base`` like https://data.obsea.es/erddap ; constraints like ['time>=2020-01-01'].

    Constraint values are percent-encoded; ERDDAP rejects raw '>' and '"' in some setups.
    """
    query = ",".join(variables)
    for c in constraints or []:
        query += "&" + quote(c, safe="=")
    return f"{base.rstrip('/')}/tabledap/{dataset}.csv?{query}"


def parse_csv(text: str) -> list[dict[str, str]]:
    """ERDDAP .csv has a second header line with units; skip it."""
    reader = csv.reader(io.StringIO(text))
    try:
        names = next(reader)
        next(reader)  # units
    except StopIteration:
        return []
    return [dict(zip(names, row)) for row in reader if row]


def fetch(http: Http, base: str, dataset: str, variables: list[str], constraints: list[str] | None = None) -> list[dict[str, Any]]:
    return parse_csv(http.get_text(tabledap_csv_url(base, dataset, variables, constraints)))


def info_url(base: str, dataset: str) -> str:
    return f"{base.rstrip('/')}/info/{dataset}/index.csv"


def global_attributes(http: Http, base: str, dataset: str) -> dict[str, str]:
    """NC_GLOBAL attributes (license, title, citation, geospatial bounds...)."""
    rows = list(csv.reader(io.StringIO(http.get_text(info_url(base, dataset)))))
    out = {}
    for r in rows[1:]:
        if len(r) >= 5 and r[0] == "attribute" and r[1] == "NC_GLOBAL":
            out[r[2]] = r[4]
    return out
