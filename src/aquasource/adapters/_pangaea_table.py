"""Base class for datasets published as PANGAEA data tables with media URL columns.

Subclasses set ``dataset_ids`` and the column preferences; one candidate is
produced per table row (the first non-empty media column in ``media_columns``).
"""

from __future__ import annotations

import os
from datetime import date
from typing import ClassVar, Iterable
from urllib.parse import urlparse

from ..core.geo import depth_from, to_float
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from ..providers import pangaea
from .base import Adapter

VIDEO_EXT = {"avi", "mp4", "mov", "mkv", "mts", "m2ts", "mpg", "mpeg", "wmv", "lrv"}


class PangaeaTableAdapter(Adapter):
    # PANGAEA dataset ids (numbers after 10.1594/PANGAEA.)
    dataset_ids: ClassVar[tuple[str, ...]] = ()
    # Column-name prefixes tried in order to find the media URL of a row.
    media_columns: ClassVar[tuple[str, ...]] = ("URL image", "URL movie", "URL photo", "URL file")
    lat_columns: ClassVar[tuple[str, ...]] = ("Latitude",)
    lon_columns: ClassVar[tuple[str, ...]] = ("Longitude",)
    depth_columns: ClassVar[tuple[str, ...]] = ("Depth water [m]", "Bathy depth [m]", "Depth [m]", "Elevation [m]")
    time_columns: ClassVar[tuple[str, ...]] = ("Date/Time",)
    # "image" when each row is one photo at its own position, "station" when a
    # row is a video/station whose coordinate applies to all of its frames.
    row_precision: ClassVar[str] = "image"
    host_intervals = {"doi.pangaea.de": 1.0, "hs.pangaea.de": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._tables: dict[str, pangaea.PangaeaTable] = {}

    # ----------------------------------------------------------------- tables
    def ids(self) -> list[str]:
        ids = self.options.get("dataset_ids") or self.dataset_ids
        if isinstance(ids, (str, int)):
            ids = [ids]
        return [pangaea.dataset_id(i) for i in ids]

    def table(self, ds_id: str) -> pangaea.PangaeaTable:
        if ds_id not in self._tables:
            text = self.ctx.cached_text(pangaea.textfile_url(ds_id), f"pangaea_{ds_id}.tab")
            self._tables[ds_id] = pangaea.parse_textfile(text, ds_id)
        return self._tables[ds_id]

    def media_type_for(self, url: str) -> str:
        ext = os.path.splitext(urlparse(url).path)[1].lstrip(".").lower()
        return "video" if ext in VIDEO_EXT else "image"

    # -------------------------------------------------------------- interface
    def discover(self) -> Iterable[Candidate]:
        today = date.today().isoformat()
        for ds_id in self.ids():
            t = self.table(ds_id)
            until = t.moratorium_until
            if until and until > today:
                self.ctx.fail(f"PANGAEA.{ds_id}", "licence", f"moratorium until {until}")
                continue
            cols = [c for p in self.media_columns for c in t.columns if c.lower().startswith(p.lower())]
            if not cols:
                self.ctx.fail(f"PANGAEA.{ds_id}", "discover", f"no media URL column among {list(self.media_columns)}")
                continue
            seen: set[str] = set()
            for i, row in enumerate(t.rows):
                url = next((row[c] for c in cols if row.get(c, "").startswith("http")), None)
                if not url or url in seen:
                    continue
                seen.add(url)
                ts = next((row[c] for c in self.time_columns if row.get(c)), None)
                yield Candidate(
                    source=self.key,
                    item_id=f"PANGAEA.{ds_id}/{os.path.basename(urlparse(url).path) or i}",
                    media_type=self.media_type_for(url),
                    media_url=url,
                    origin_url=pangaea.landing_url(ds_id),
                    timestamp=ts,
                    raw={"dataset_id": ds_id, "row": row},
                    extra={"pangaea_id": ds_id, "row_index": i},
                )

    def resolve_licence(self, cand: Candidate) -> Licence:
        t = self.table(cand.raw["dataset_id"])
        return make_licence(t.licence_name, level="record", url=t.licence_url or pangaea.landing_url(t.dataset_id), attribution=t.citation)

    def _first(self, row: dict[str, str], prefixes: tuple[str, ...]) -> tuple[str | None, str | None]:
        for p in prefixes:
            for k, v in row.items():
                if k.lower().startswith(p.lower()) and v not in (None, ""):
                    return k, v
        return None, None

    def resolve_geo(self, cand: Candidate) -> Geo:
        row = cand.raw["row"]
        ds_id = cand.raw["dataset_id"]
        lat_col, lat = self._first(row, self.lat_columns)
        lon_col, lon = self._first(row, self.lon_columns)
        depth_col, depth = self._first(row, self.depth_columns)
        d = depth_from(depth)
        latf, lonf = to_float(lat), to_float(lon)
        if latf is None or lonf is None:
            return Geo.none(geo_source=f"PANGAEA.{ds_id}: no {self.lat_columns[0]}/{self.lon_columns[0]} in row", depth_m=d)
        src = f"PANGAEA.{ds_id} columns {lat_col}/{lon_col}"
        if depth_col:
            src += f", depth from {depth_col}"
        if self.row_precision == "station":
            src += " (station position applied to the whole video)"
        return Geo(
            lat=latf,
            lon=lonf,
            depth_m=d,
            geo_precision=self.row_precision,
            geo_source=src,
            geo_inferred=self.row_precision != "image",
            geo_uncertainty_m=None,
        )


