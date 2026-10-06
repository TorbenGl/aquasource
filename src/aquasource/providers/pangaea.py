"""PANGAEA helpers: fetch and parse the tab-delimited "textfile" export.

``https://doi.pangaea.de/10.1594/PANGAEA.<id>?format=textfile`` returns a
``/* DATA DESCRIPTION: ... */`` header (Citation, License, Coverage, Event(s),
Parameter(s), Status, Size, ...) followed by a TSV table.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from typing import Any

DOI_PREFIX = "10.1594/PANGAEA."


def dataset_id(doi_or_id: str | int) -> str:
    s = str(doi_or_id).strip()
    m = re.search(r"PANGAEA\.(\d+)", s, re.I)
    return m.group(1) if m else re.sub(r"\D", "", s)


def landing_url(doi_or_id: str | int) -> str:
    return f"https://doi.pangaea.de/{DOI_PREFIX}{dataset_id(doi_or_id)}"


def textfile_url(doi_or_id: str | int) -> str:
    return landing_url(doi_or_id) + "?format=textfile"


@dataclass
class PangaeaTable:
    dataset_id: str
    meta: dict[str, list[str]] = field(default_factory=dict)
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, str]] = field(default_factory=list)

    def first(self, key: str) -> str | None:
        vals = self.meta.get(key)
        return vals[0] if vals else None

    @property
    def citation(self) -> str:
        return self.first("Citation") or f"PANGAEA dataset {DOI_PREFIX}{self.dataset_id}"

    @property
    def licence_text(self) -> str | None:
        return self.first("License")

    @property
    def licence_name(self) -> str | None:
        lic = self.licence_text
        if not lic:
            return None
        return re.sub(r"\s*\(URI:.*?\)\s*$", "", lic).strip()

    @property
    def licence_url(self) -> str | None:
        lic = self.licence_text or ""
        m = re.search(r"URI:\s*(\S+?)\)?$", lic)
        return m.group(1) if m else None

    @property
    def status(self) -> str | None:
        return self.first("Status")

    @property
    def moratorium_until(self) -> str | None:
        for v in self.meta.get("Status", []) + self.meta.get("Moratorium", []):
            m = re.search(r"(?:moratorium|embargo)[^0-9]*(\d{4}-\d{2}-\d{2})", v, re.I)
            if m:
                return m.group(1)
        return None

    def column(self, *prefixes: str) -> str | None:
        """First column whose name starts with one of ``prefixes`` (case-insensitive)."""
        for p in prefixes:
            for c in self.columns:
                if c.lower().startswith(p.lower()):
                    return c
        return None

    def columns_like(self, pattern: str) -> list[str]:
        rx = re.compile(pattern, re.I)
        return [c for c in self.columns if rx.search(c)]


def parse_textfile(text: str, ds_id: str | int = "") -> PangaeaTable:
    table = PangaeaTable(dataset_id=dataset_id(ds_id) if ds_id else "")
    body = text
    if text.startswith("/*"):
        end = text.find("\n*/")
        header, body = text[: end if end >= 0 else 0], text[end + 3 :] if end >= 0 else text
        key = None
        for line in header.splitlines()[1:]:
            if not line.strip():
                continue
            if line[0] in " \t":
                if key:
                    table.meta.setdefault(key, []).append(line.strip())
                continue
            k, _, v = line.partition(":\t")
            if not _:
                k, _, v = line.partition(":")
            key = k.strip()
            table.meta.setdefault(key, []).append(v.strip())
        if not table.dataset_id:
            m = re.search(r"PANGAEA\.(\d+)", table.first("Citation") or "")
            table.dataset_id = m.group(1) if m else ""
    body = body.lstrip("\r\n")
    reader = csv.reader(io.StringIO(body), delimiter="\t")
    try:
        table.columns = [c.strip() for c in next(reader)]
    except StopIteration:
        return table
    for raw in reader:
        if not raw or all(not x.strip() for x in raw):
            continue
        row = {c: (raw[i].strip() if i < len(raw) else "") for i, c in enumerate(table.columns)}
        table.rows.append(row)
    return table


def coverage(table: PangaeaTable) -> dict[str, Any]:
    """Parse the Coverage block (median/bounding lat/lon, dates)."""
    out: dict[str, Any] = {}
    for v in table.meta.get("Coverage", []):
        for part in v.split("*"):
            k, _, val = part.partition(":")
            k = k.strip().upper()
            val = val.strip()
            if not k:
                continue
            try:
                out[k] = float(val)
            except ValueError:
                out[k] = val
    return out
