"""OOI CamHD (HD video camera CAMHDA301, ASHES vent field, Axial Seamount, Cabled Array RS03ASHS/PN03B), 2015 to now.

Source: OOI raw data server https://rawdata.oceanobservatories.org/files/RS03ASHS/PN03B/CAMHDA301/<yyyy>/<mm>/<dd>/
(Apache directory listings, anonymous). One ``.mov`` (about 13 GB) and one ``.mp4`` (about 852 MB, 1080p transcode) per
3-hour file start. Only the ``.mp4`` rendition is yielded: the ``.mov`` is too large for the sample budget.

Licence: NOT CONFIRMED. The OOI Data Use Policy (https://oceanobservatories.org/wp-content/uploads/2024/01/1102-00010_Data_Use_Policy_OOI.pdf)
and the data policy page answered HTTP 403 to every fetch (2026-10-08), so no licence string could be read. Tier U, level
``unknown``. Never upgraded. Default config tiers (A, B) therefore select nothing; opt in with ``tiers`` in the config
only after the policy has been read.

Geo: fixed camera. ``geo_precision`` region, ``geo_source`` = sites/ooi_camhd.csv (ASHES vent field position from the
Wikipedia article, depth 1552 m from the OOI site listing). The instrument's own OOI metadata position was not reachable.
Applied to every video, ``geo_inferred`` true.

How it works
    * Discovery walks the directory tree year -> month -> day (metadata only, cached per day under metadata/raw/).
      ``from`` / ``to`` (YYYY-MM-DD) narrow the walk; ``per_day`` keeps at most N videos per calendar day.
    * Item id = file name (``CAMHDA301-<UTC timestamp>.mp4``), stable across runs.
    * Media: plain HTTPS GET; expected size is parsed from the listing.

Adapter options (``--opt key=value``)
    from / to     first and last day to list, YYYY-MM-DD (default: the whole archive, oldest first)
    per_day       at most N videos per calendar day (default: all)
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from typing import Any, Iterable, Iterator

from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from ..core.sites import load_sites
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

ROOT = "https://rawdata.oceanobservatories.org/files/RS03ASHS/PN03B/CAMHDA301/"
POLICY_URL = "https://oceanobservatories.org/wp-content/uploads/2024/01/1102-00010_Data_Use_Policy_OOI.pdf"
SITE_ID = "ooi_camhd"
FIRST_YEAR = 2015

HREF_RE = re.compile(r'href="(CAMHDA301-(\d{8})T(\d{6})Z\.mp4)"')
SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([KMGT]?)\s*$")
UNIT = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
DIR_RE = re.compile(r'href="(\d{2,4})/"')


def parse_size(text: str) -> int | None:
    """Apache listing size such as ``852M`` or ``13G`` -> bytes (approximate, listing rounds)."""
    m = SIZE_RE.search(text.strip())
    if not m:
        return None
    return int(float(m.group(1)) * UNIT[m.group(2)])


def parse_day_listing(html: str, day_url: str, day: date) -> list[dict[str, Any]]:
    """Mp4 entries of one day folder. The size is the listing column after the ``.mp4`` name."""
    rows = []
    for m in re.finditer(r'href="(CAMHDA301-\d{8}T\d{6}Z\.mp4)".*?\s(\d+(?:\.\d+)?[KMGT]?)\s*\n', html):
        name = m.group(1)
        stamp = re.search(r"T(\d{6})Z", name).group(1)
        ts = datetime(day.year, day.month, day.day, int(stamp[:2]), int(stamp[2:4]), int(stamp[4:6]), tzinfo=timezone.utc)
        rows.append(
            {
                "name": name,
                "url": day_url + name,
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "size": parse_size(m.group(2)),
            }
        )
    return rows


def dir_links(html: str) -> list[str]:
    return DIR_RE.findall(html)


def _day_path(day: date) -> str:
    return f"{day.year:04d}/{day.month:02d}/{day.day:02d}/"


def _parse_day_opt(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()


@register
class OoiCamhdAdapter(Adapter):
    key = "ooi_camhd"
    name = "OOI CamHD (Axial Seamount ASHES, CAMHDA301)"
    homepage = "https://oceanobservatories.org/site/rs03ashs/"
    citation = "Ocean Observatories Initiative, CamHD, RS03ASHS-PN03B-06-CAMHDA301 (raw data, https://rawdata.oceanobservatories.org)"
    media_types = ("video",)
    host_intervals = {"rawdata.oceanobservatories.org": 1.0}

    def __init__(self, ctx):
        super().__init__(ctx)
        self._site = None

    def _years_months(self, lo: date, hi: date) -> Iterator[tuple[int, int]]:
        for y in range(lo.year, hi.year + 1):
            for mo in range(1, 13):
                if date(y, mo, 1) > hi or (y, mo) < (lo.year, lo.month):
                    continue
                yield y, mo

    def discover(self) -> Iterable[Candidate]:
        per_day = int(self.options.get("per_day") or 0) or None
        start = _parse_day_opt(self.options.get("from")) or date(FIRST_YEAR, 1, 1)
        end = _parse_day_opt(self.options.get("to")) or datetime.now(timezone.utc).date()
        for y, mo in self._years_months(start, end):
            month_url = f"{ROOT}{y:04d}/{mo:02d}/"
            try:
                month_html = self.ctx.cached_text(month_url, f"listing/{y:04d}-{mo:02d}.html")
            except Exception as exc:  # noqa: BLE001 - a missing month is logged and skipped
                self.ctx.fail(f"{y:04d}-{mo:02d}", "discover", f"month listing: {exc}")
                continue
            for dd in dir_links(month_html):
                if not dd.isdigit():
                    continue
                day = date(y, mo, int(dd)) if 1 <= int(dd) <= 31 else None
                if day is None or day < start or day > end:
                    continue
                day_url = f"{ROOT}{_day_path(day)}"
                try:
                    html = self.ctx.cached_text(day_url, f"listing/{_day_path(day).replace('/', '-').strip('-')}.html")
                except Exception as exc:  # noqa: BLE001
                    self.ctx.fail(day.isoformat(), "discover", f"day listing: {exc}")
                    continue
                rows = parse_day_listing(html, day_url, day)
                for row in rows[:per_day]:
                    yield Candidate(
                        source=self.key,
                        item_id=row["name"],
                        media_type="video",
                        media_url=row["url"],
                        origin_url=day_url,
                        timestamp=row["timestamp"],
                        ext="mp4",
                        raw={"size": row["size"], "day": day.isoformat()},
                    )

    def resolve_licence(self, cand: Candidate) -> Licence:
        return make_licence(
            "OOI data use policy (licence not stated; policy unreadable, HTTP 403)",
            level="unknown",
            url=POLICY_URL,
            attribution=(
                "OOI CamHD video, RS03ASHS-PN03B-06-CAMHDA301, Ocean Observatories Initiative, "
                "https://rawdata.oceanobservatories.org (licence not confirmed)"
            ),
            tier="U",
        )

    def resolve_geo(self, cand: Candidate) -> Geo:
        if self._site is None:
            self._site = load_sites(SITE_ID)[SITE_ID]
        return self._site.geo(
            precision="region",
            geo_source=f"{self._site.source}; fixed camera, applied to every video",
            inferred=True,
        )

    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(
            url=cand.media_url,
            ext="mp4",
            expected_bytes=cand.raw.get("size"),
        )
