"""HODOR camera videos (PANGAEA.980001), Kiel Fjord underwater fish observatory (UFO).

One candidate per camera video: each row of the PANGAEA data table is one activity-selected sequence
with a stereo pair ``cam1_NNNN.mp4`` / ``cam2_NNNN.mp4`` (Binary columns hold bare file names served from
``https://download.pangaea.de/dataset/980001/files/``). Times are UTC (``sequenceStartUnix`` matches
``Date/time start``). Geolocation is the observatory position from the dataset's Coverage / Event line,
applied to every sequence (precision ``fixed_site``). The table has no depth column; depth stays null.

Adapter options (``--opt name=value``):
    cams=cam1            comma list of ``cam1``, ``cam2`` (default ``cam1``: one camera per sequence)
    from=YYYY-MM-DD      first sequence day to keep (inclusive)
    to=YYYY-MM-DD        last sequence day to keep (inclusive)
    per_day=N            keep at most N sequences per calendar day (default: all)

Licence: CC BY 4.0 read at record level (table header ``License:`` line), tier B.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from ..core.geo import to_float
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from ..providers import pangaea
from .base import Adapter, register

DATASET_ID = "980001"
DOWNLOAD = "https://download.pangaea.de/dataset/" + DATASET_ID + "/files/{name}"
CAMS = ("cam1", "cam2")
CAMERA_COVERAGE = re.compile(r"LATITUDE:\s*(-?[\d.]+)\s*\*\s*LONGITUDE:\s*(-?[\d.]+)")


def _cams(value: Any) -> list[str]:
    if value in (None, ""):
        return ["cam1"]
    items = value if isinstance(value, list) else str(value).strip().strip("[]").replace('"', "").split(",")
    out = [str(c).strip().lower() for c in items if str(c).strip()]
    bad = [c for c in out if c not in CAMS]
    if bad:
        raise ValueError(f"hodor option cams: unknown {bad}; use {list(CAMS)}")
    return out or ["cam1"]


@register
class HodorAdapter(Adapter):
    key = "hodor"
    name = "HODOR: Hydroacoustic and Optical Dataset for Oceanic Research (camera data)"
    homepage = "https://doi.org/10.1594/PANGAEA.980001"
    citation = (
        "Wilts, T., Böer, G., Winkler, J., Cisewski, B., Badri-Hoeher, S. (2025): HODOR: Hydroacoustic and Optical "
        "Dataset for Oceanic Research: camera data [dataset]. PANGAEA, https://doi.org/10.1594/PANGAEA.980001"
    )
    media_types = ("video",)
    host_intervals = {"doi.pangaea.de": 1.0, "download.pangaea.de": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._table: pangaea.PangaeaTable | None = None
        self._cams = _cams(self.options.get("cams"))

    # ------------------------------------------------------------------ helpers
    def table(self) -> pangaea.PangaeaTable:
        if self._table is None:
            text = self.ctx.cached_text(pangaea.textfile_url(DATASET_ID), f"pangaea_{DATASET_ID}.tab")
            self._table = pangaea.parse_textfile(text, DATASET_ID)
        return self._table

    def _int(self, name: str) -> int | None:
        v = to_float(self.options.get(name))
        return int(v) if v is not None and v >= 1 else None

    def _day(self, name: str) -> str | None:
        v = self.options.get(name)
        return str(v).strip()[:10] if v not in (None, "") else None

    def estimate(self) -> dict[str, Any]:
        n = len(self.table().rows)
        return {"sequences": n, "videos": n * len(self._cams)}

    # --------------------------------------------------------------- interface
    def discover(self) -> Iterable[Candidate]:
        t = self.table()
        lo, hi, per_day = self._day("from"), self._day("to"), self._int("per_day")
        counts: dict[str, int] = {}
        for row in t.rows:
            seq = row.get("SeqID", "").strip()
            start = row.get("Date/time start", "").strip()
            day = start[:10]
            if not seq or not day:
                self.ctx.fail(seq or "?", "discover", "row without SeqID or Date/time start")
                continue
            if (lo and day < lo) or (hi and day > hi):
                continue
            if per_day and counts.get(day, 0) >= per_day:
                continue
            counts[day] = counts.get(day, 0) + 1
            for cam in self._cams:
                name = row.get(f"Binary ({cam}FilePath)", "").strip()
                if not name:
                    self.ctx.fail(seq, "discover", f"no {cam} video file name")
                    continue
                other = "cam2" if cam == "cam1" else "cam1"
                ts_name = row.get(f"Binary ({cam}FileTimestampsPath)", "").strip()
                other_name = row.get(f"Binary ({other}FilePath)", "").strip()
                yield Candidate(
                    source=self.key,
                    item_id=f"PANGAEA.{DATASET_ID}/{seq}/{cam}",
                    media_type="video",
                    media_url=DOWNLOAD.format(name=name),
                    origin_url=pangaea.landing_url(DATASET_ID),
                    timestamp=f"{start}Z",
                    ext="mp4",
                    raw={"row": row, "cam": cam},
                    extra={
                        "pangaea_id": DATASET_ID,
                        "seq_id": seq,
                        "camera": cam,
                        "stereo_partner_url": DOWNLOAD.format(name=other_name) if other_name else None,
                        "timestamps_url": DOWNLOAD.format(name=ts_name) if ts_name else None,
                        "seq_end": row.get("Date/time end", "") + "Z",
                        "duration_s": _duration(row),
                    },
                )

    def resolve_licence(self, cand: Candidate) -> Licence:
        t = self.table()
        return make_licence(
            t.licence_name,
            level="record",
            url=t.licence_url or pangaea.landing_url(DATASET_ID),
            attribution=t.citation,
        )

    def resolve_geo(self, cand: Candidate) -> Geo:
        t = self.table()
        m = CAMERA_COVERAGE.search(" ".join(t.meta.get("Coverage", [])))
        if not m:
            return Geo.none(geo_source=f"PANGAEA.{DATASET_ID}: no LATITUDE/LONGITUDE in Coverage line")
        return Geo(
            lat=float(m.group(1)),
            lon=float(m.group(2)),
            depth_m=None,
            geo_precision="fixed_site",
            geo_source=f"PANGAEA.{DATASET_ID} Coverage LATITUDE/LONGITUDE (observatory position, all sequences)",
            geo_inferred=True,
            geo_uncertainty_m=None,
        )


def _duration(row: dict[str, str]) -> float | None:
    a = to_float(row.get("t (sequenceStartUnix)"))
    b = to_float(row.get("t (sequenceEndUnix)"))
    return round(b - a, 3) if a is not None and b is not None else None
