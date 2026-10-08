"""Ocean Networks Canada (Oceans 3.0) fixed camera video and stills, read through the Oceans 3.0 REST API.

Source: https://data.oceannetworks.ca (API guide https://oceannetworkscanada.github.io/Oceans3.0-API/API_Guide.html,
OpenAPI https://data.oceannetworks.ca/OpenAPI). Needs a free ONC account and an API token in ``ONC_TOKEN``
(https://data.oceannetworks.ca/Profile). Without the token every call is refused (HTTP 401, errorCode 128).

Licence: NOT resolved per file. The ONC Data Policy (https://www.oceannetworks.ca/data/data-policy/) says ONC-owned data
are CC BY 4.0, while partner-owned data "may be subject to alternative licensing such as CC BY-NC, or a more restrictive
license". The API does not state the owner of a file in what the client library exposes. Every sample is therefore tier
U (unknown), never B by default, and extra.licence_note says so. Ownership per device has to be checked with ONC before a
tier B is set for a device.

Geo: fixed camera. The coordinate is the device deployment position from ``/deployments`` (fields ``lat``, ``lon``,
``depth``) of the deployment whose ``begin`` <= file time <= ``end``. Precision ``fixed_site``, inferred (shared by every
file of the deployment), no uncertainty published. No deployment match -> geo ``none``. Mobile categories (ROV, AUV) are
not fixed sites: the default categories are VIDEOCAM and CAMERA only.

How it works
    * Discovery: ``GET /api/deployments`` (cached per location/category) and ``GET /api/archivefile/location`` per calendar
      month of the requested window, following ``next.parameters`` pages (cached as metadata/raw/onc/). Item id = archive
      file name (ONC file names carry the device code and the UTC start time: ``<DEVICE>_<yyyymmddTHHMMSS.fffZ>.<ext>``).
    * Media: ``GET /api/archivefile/download?filename=...`` streamed to disk. The token is sent as a query parameter of
      that request only (never in cached metadata, never in the item url, not in the cache file names).

Adapter options (``--opt name=value``; lists comma separated)
    locations           required: ONC location codes, e.g. a code from ``getLocations`` (listed by the client library).
    categories          device category codes, default ``VIDEOCAM,CAMERA``.
    from=YYYY-MM-DD     first day of the window (default: 30 days before ``to``). Full history: set from=2006-01-01.
    to=YYYY-MM-DD       last day of the window, inclusive (default: today, UTC).
    extension           file extension filter as the API expects it (``mp4``, ``jpg``); default all files.
    per_day=N           keep at most N files per device and calendar day (default all).
"""

from __future__ import annotations

import calendar
import hashlib
import json
import logging
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from ..core.geo import depth_from, to_float
from ..core.http import HttpError
from ..core.licence import make_licence
from ..core.schema import Candidate, Geo, Licence
from .base import Adapter, MediaRef, register

log = logging.getLogger(__name__)

API = "https://data.oceannetworks.ca/api"
DOWNLOAD_URL = f"{API}/archivefile/download"
POLICY = "https://www.oceannetworks.ca/data/data-policy/"
DATASEARCH = "https://data.oceannetworks.ca/DataSearch"
DEFAULT_CATEGORIES = ("VIDEOCAM", "CAMERA")
FIXED_CATEGORIES = ("VIDEOCAM", "CAMERA")
LICENCE_NAME = "not stated per file (ONC: CC BY 4.0 for ONC-owned data, partner data may be CC BY-NC or more restrictive)"
NAME_RE = re.compile(r"^(?P<dev>.+?)_(?P<ts>\d{8}T\d{6}(?:\.\d+)?Z)")


def file_time(name: str) -> datetime | None:
    """UTC start time from an ONC archive file name, e.g. ``X_20091231T235919.476Z-spect.png``."""
    m = NAME_RE.match(name)
    if not m:
        return None
    raw = m.group("ts")[:-1]  # drop Z
    base, _, frac = raw.partition(".")
    dt = datetime.strptime(base, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
    return dt.replace(microsecond=int(frac[:6].ljust(6, "0"))) if frac else dt


def device_of(name: str) -> str | None:
    m = NAME_RE.match(name)
    return m.group("dev") if m else None


def parse_iso(value: object) -> datetime | None:
    if not value:
        return None
    s = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def months(lo: date, hi: date) -> Iterable[tuple[date, date]]:
    """Calendar-month windows covering lo..hi (both inclusive)."""
    cur = lo.replace(day=1)
    while cur <= hi:
        last = cur.replace(day=calendar.monthrange(cur.year, cur.month)[1])
        yield max(cur, lo), min(last, hi)
        cur = last + timedelta(days=1)


def api_time(day: date, end: bool) -> str:
    return f"{day.isoformat()}T{'23:59:59.999' if end else '00:00:00.000'}Z"


def deployment_for(deployments: list[dict[str, Any]], device: str, when: datetime) -> dict[str, Any] | None:
    for d in deployments:
        if str(d.get("deviceCode") or "") != device:
            continue
        begin, end = parse_iso(d.get("begin")), parse_iso(d.get("end"))
        if begin and when < begin:
            continue
        if end and when > end:
            continue
        return d
    return None


@register
class OncAdapter(Adapter):
    key = "onc"
    name = "Ocean Networks Canada (Oceans 3.0) fixed cameras, video and stills"
    homepage = "https://data.oceannetworks.ca"
    citation = (
        "Ocean Networks Canada (year), Oceans 3.0 archive file <filename>, device <deviceCode>, retrieved <date>, "
        "https://data.oceannetworks.ca. Cite ONC and the partner where the data are partner-owned."
    )
    media_types = ("video", "image")
    env_vars = ("ONC_TOKEN",)
    manual_steps = "Free ONC account and API token: export ONC_TOKEN=... (https://data.oceannetworks.ca/Profile)"
    host_intervals = {"data.oceannetworks.ca": 1.0}

    # ------------------------------------------------------------------ helpers
    @property
    def token(self) -> str:
        return os.environ.get("ONC_TOKEN", "")

    def _get(self, endpoint: str, name: str, params: dict[str, Any]) -> Any:
        """Cached metadata call. The token is passed as a parameter, not stored in the cache or the URL name."""
        path = self.ctx.layout.raw / name
        if path.exists() and not self.options.get("refresh_metadata"):
            return json.loads(path.read_text(encoding="utf-8"))
        resp = self.http.get(f"{API}/{endpoint}", params={**params, "token": self.token})
        data = resp.json()
        if isinstance(data, dict) and data.get("errors"):
            raise HttpError(f"{API}/{endpoint}", None, str(data["errors"])[:300])
        self.ctx.save_raw(name, json.dumps(data))
        return data

    def _window(self) -> tuple[date, date]:
        hi = self._date("to") or datetime.now(timezone.utc).date()
        lo = self._date("from") or (hi - timedelta(days=30))
        if lo > hi:
            raise ValueError(f"from {lo} is after to {hi}")
        return lo, hi

    def _date(self, name: str) -> date | None:
        v = self.options.get(name)
        return date.fromisoformat(str(v).strip()[:10]) if v not in (None, "") else None

    def _list(self, name: str, default: tuple[str, ...]) -> list[str]:
        v = self.options.get(name)
        if v in (None, ""):
            return list(default)
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v if str(x).strip()]
        return [x.strip() for x in str(v).split(",") if x.strip()]

    def check_ready(self) -> list[str]:
        problems = super().check_ready()
        if not self._list("locations", ()):
            problems.append("option locations=<ONC location codes> is required (see getLocations in the API guide)")
        return problems

    # ---------------------------------------------------------------- discover
    def discover(self) -> Iterable[Candidate]:
        lo, hi = self._window()
        per_day = int(self.options["per_day"]) if self.options.get("per_day") else None
        ext = str(self.options.get("extension") or "").lstrip(".") or None
        counts: dict[tuple[str, str], int] = {}
        for loc in self._list("locations", ()):
            for cat in self._list("categories", DEFAULT_CATEGORIES):
                try:
                    deployments = self._get(
                        "deployments",
                        f"onc/deployments_{loc}_{cat}.json",
                        {"locationCode": loc, "deviceCategoryCode": cat},
                    )
                except (HttpError, ValueError, OSError) as exc:
                    self.ctx.fail(f"{loc}/{cat}", "discover", f"deployments not readable: {exc}")
                    continue
                if isinstance(deployments, dict):
                    deployments = deployments.get("deployments", [])
                for m_lo, m_hi in months(lo, hi):
                    for fname in self._archive_files(loc, cat, m_lo, m_hi, ext):
                        when = file_time(fname)
                        if when is None:
                            continue
                        dev = device_of(fname) or ""
                        day = when.date().isoformat()
                        if per_day:
                            if counts.get((dev, day), 0) >= per_day:
                                continue
                            counts[(dev, day)] = counts.get((dev, day), 0) + 1
                        yield self._candidate(loc, cat, fname, when, dev, deployments)

    def _archive_files(self, loc: str, cat: str, m_lo: date, m_hi: date, ext: str | None) -> list[str]:
        """All file names of one window; pages follow ``next.parameters`` (cached per page)."""
        params: dict[str, Any] = {
            "locationCode": loc,
            "deviceCategoryCode": cat,
            "dateFrom": api_time(m_lo, end=False),
            "dateTo": api_time(m_hi, end=True),
        }
        if ext:
            params["fileExtension"] = ext
        files: list[str] = []
        page = 0
        while True:
            name = f"onc/archivefile_{loc}_{cat}_{m_lo:%Y%m%d}_{m_hi:%Y%m%d}_{ext or 'all'}_p{page}.json"
            try:
                data = self._get("archivefile/location", name, params)
            except (HttpError, ValueError, OSError) as exc:
                self.ctx.fail(f"{loc}/{cat}/{m_lo}", "discover", f"archive list not readable: {exc}")
                return files
            for row in data.get("files", []):
                files.append(row.get("filename") if isinstance(row, dict) else str(row))
            nxt = data.get("next")
            if not nxt or not nxt.get("parameters"):
                return files
            params = {**nxt["parameters"]}
            params.pop("token", None)
            page += 1

    def _candidate(
        self, loc: str, cat: str, fname: str, when: datetime, dev: str, deployments: list[dict[str, Any]]
    ) -> Candidate:
        ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else None
        media_type = "image" if ext in ("jpg", "jpeg", "png") else "video"
        dep = deployment_for(deployments, dev, when)
        return Candidate(
            source=self.key,
            item_id=fname,
            media_type=media_type,
            media_url=DOWNLOAD_URL,
            origin_url=f"{DATASEARCH}?location={loc}",
            timestamp=when.isoformat().replace("+00:00", "Z"),
            ext=ext,
            raw={"location": loc, "category": cat, "device": dev, "filename": fname, "deployment": dep},
            extra={
                "onc_location": loc,
                "onc_category": cat,
                "onc_device": dev,
                "onc_filename": fname,
                "licence_note": "owner per device not resolved; ONC-owned data are CC BY 4.0, partner data vary",
            },
        )

    # ---------------------------------------------------------------- licence / geo
    def resolve_licence(self, cand: Candidate) -> Licence:
        # Tier U on purpose: owner (ONC or partner) of each device is not stated in the metadata we read.
        lic = make_licence(
            LICENCE_NAME,
            level="collection",
            url=POLICY,
            attribution=(
                f"Ocean Networks Canada, device {cand.raw['device']} ({cand.raw['location']}), file {cand.raw['filename']}, "
                f"{DATASEARCH}?location={cand.raw['location']}; check the data owner before use"
            ),
            tier="U",
        )
        return lic

    def resolve_geo(self, cand: Candidate) -> Geo:
        dep = cand.raw.get("deployment")
        if cand.raw.get("category") not in FIXED_CATEGORIES or not dep:
            return Geo.none(geo_source="ONC /deployments: no fixed deployment covers this file time")
        lat, lon = to_float(dep.get("lat")), to_float(dep.get("lon"))
        if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
            return Geo.none(geo_source="ONC /deployments lat/lon missing or invalid", depth_m=depth_from(dep.get("depth")))
        return Geo(
            lat=lat,
            lon=lon,
            depth_m=depth_from(dep.get("depth")),
            geo_precision="fixed_site",
            geo_source=(
                f"ONC /deployments fields lat, lon, depth for device {cand.raw['device']} "
                f"(deployment {dep.get('begin')} to {dep.get('end')})"
            ),
            geo_inferred=True,
            geo_uncertainty_m=None,
        )

    # ---------------------------------------------------------------- media
    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(url=DOWNLOAD_URL, ext=cand.ext or "mp4", extra={"filename": cand.raw["filename"]})

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        """Stream the archive file; the token goes in ``params`` so it never reaches the request log."""
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        resp = self.http.request(
            "GET", ref.url, kind="media", params={"filename": ref.extra["filename"], "token": self.token}, stream=True
        )
        if resp.status_code >= 400:
            text = resp.text[:200]
            resp.close()
            raise HttpError(f"{DOWNLOAD_URL}?filename={ref.extra['filename']}", resp.status_code, text)
        h = hashlib.sha256()
        total = 0
        try:
            with open(part, "wb") as fh:
                for chunk in resp.iter_content(1 << 20):
                    if chunk:
                        fh.write(chunk)
                        h.update(chunk)
                        total += len(chunk)
        finally:
            resp.close()
        if total == 0:
            part.unlink(missing_ok=True)
            raise HttpError(ref.url, 200, "empty download")
        os.replace(part, dest)
        self.http.media_bytes += total
        self.http.media_files += 1
        return total, h.hexdigest()
