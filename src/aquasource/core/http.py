"""Polite HTTP client shared by all adapters.

* identifying User-Agent (contact from ``AQUASOURCE_CONTACT`` if set)
* per-host minimum interval between requests
* back-off on 429 / 5xx, honouring ``Retry-After``
* resumable, atomic media downloads with sha256
* a request log, and a dry-run guard that refuses media downloads
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

import requests

from .. import __version__

log = logging.getLogger(__name__)

RETRY_STATUS = {429, 500, 502, 503, 504}
PROJECT_URL = "https://github.com/torbengl/aquasource"


class DryRunViolation(RuntimeError):
    """Raised when something tries to download media during a dry run."""


class HttpError(RuntimeError):
    def __init__(self, url: str, status: int | None, message: str):
        super().__init__(f"{status} {url}: {message}")
        self.url = url
        self.status = status


def user_agent(contact: str | None = None) -> str:
    contact = contact if contact is not None else os.environ.get("AQUASOURCE_CONTACT", "")
    ua = f"aquasource/{__version__} (+{PROJECT_URL}"
    if contact:
        ua += f"; {contact}"
    return ua + ")"


class Http:
    def __init__(
        self,
        *,
        dry_run: bool = False,
        min_interval_s: float = 1.0,
        host_intervals: dict[str, float] | None = None,
        max_retries: int = 5,
        timeout_s: float = 60.0,
        request_log: Path | None = None,
        contact: str | None = None,
        session: requests.Session | None = None,
    ):
        self.dry_run = dry_run
        self.min_interval_s = min_interval_s
        self.host_intervals = dict(host_intervals or {})
        self.max_retries = max_retries
        self.timeout_s = timeout_s
        self.request_log = request_log
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = user_agent(contact)
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()
        self.media_bytes = 0
        self.media_files = 0
        self.metadata_requests = 0

    # ------------------------------------------------------------------ basics
    def _throttle(self, url: str) -> None:
        host = urlparse(url).netloc
        interval = self.host_intervals.get(host, self.min_interval_s)
        with self._lock:
            now = time.monotonic()
            wait = self._last.get(host, 0.0) + interval - now
            if wait > 0:
                time.sleep(wait)
            self._last[host] = time.monotonic()

    def _log(self, **entry: Any) -> None:
        if self.request_log is None:
            return
        self.request_log.parent.mkdir(parents=True, exist_ok=True)
        entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with self._lock, open(self.request_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    @staticmethod
    def _retry_after(resp: requests.Response, attempt: int) -> float:
        value = resp.headers.get("Retry-After")
        if value:
            try:
                return min(float(value), 600.0)
            except ValueError:
                try:
                    return max(0.0, min(parsedate_to_datetime(value).timestamp() - time.time(), 600.0))
                except Exception:
                    pass
        return min(2.0 ** attempt, 120.0)

    def request(self, method: str, url: str, *, kind: str = "metadata", **kwargs: Any) -> requests.Response:
        """Send a request with throttling and retries. ``kind`` is metadata or media."""
        if kind == "media" and self.dry_run:
            raise DryRunViolation(f"dry run: refusing media request {url}")
        kwargs.setdefault("timeout", self.timeout_s)
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._throttle(url)
            try:
                resp = self.session.request(method, url, **kwargs)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                delay = min(2.0 ** attempt, 60.0)
                log.warning("%s %s failed (%s); retry in %.0fs", method, url, exc, delay)
                time.sleep(delay)
                continue
            self._log(method=method, url=url, status=resp.status_code, kind=kind)
            if kind == "metadata":
                self.metadata_requests += 1
            if resp.status_code in RETRY_STATUS and attempt < self.max_retries:
                delay = self._retry_after(resp, attempt)
                log.warning("%s %s -> %s; backing off %.0fs", method, url, resp.status_code, delay)
                resp.close()
                time.sleep(delay)
                continue
            return resp
        raise HttpError(url, None, f"gave up after {self.max_retries + 1} attempts: {last_exc}")

    # ---------------------------------------------------------------- metadata
    def get(self, url: str, **kwargs: Any) -> requests.Response:
        resp = self.request("GET", url, **kwargs)
        if resp.status_code >= 400:
            raise HttpError(url, resp.status_code, resp.text[:300])
        return resp

    def get_text(self, url: str, **kwargs: Any) -> str:
        resp = self.get(url, **kwargs)
        if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
            resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text

    def get_json(self, url: str, **kwargs: Any) -> Any:
        return self.get(url, **kwargs).json()

    def head(self, url: str, **kwargs: Any) -> requests.Response:
        kwargs.setdefault("allow_redirects", True)
        return self.request("HEAD", url, **kwargs)

    def get_range(self, url: str, start: int, end: int, *, kind: str = "metadata") -> bytes:
        """Fetch bytes ``start..end`` (inclusive). Use kind='media' when the bytes are media."""
        resp = self.request("GET", url, kind=kind, headers={"Range": f"bytes={start}-{end}"}, stream=True)
        if resp.status_code not in (200, 206):
            raise HttpError(url, resp.status_code, "range request failed")
        if resp.status_code == 200:
            # Server ignored Range: read only what we asked for, then drop the connection.
            data = b""
            for chunk in resp.iter_content(65536):
                data += chunk
                if len(data) > end:
                    break
            resp.close()
            return data[start : end + 1]
        return resp.content

    # ------------------------------------------------------------------- media
    def download(
        self,
        url: str,
        dest: Path,
        *,
        expected_bytes: int | None = None,
        max_bytes: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, str]:
        """Download ``url`` to ``dest`` atomically, resuming a ``.part`` file if present.

        Returns ``(bytes, sha256)``. Raises :class:`DryRunViolation` in dry-run mode.
        """
        if self.dry_run:
            raise DryRunViolation(f"dry run: refusing to download {url}")
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        have = part.stat().st_size if part.exists() else 0
        hdrs = dict(headers or {})
        if have:
            hdrs["Range"] = f"bytes={have}-"
        resp = self.request("GET", url, kind="media", headers=hdrs, stream=True)
        if resp.status_code == 416 and have:
            # .part already complete (or server confused): start over.
            part.unlink(missing_ok=True)
            return self.download(url, dest, expected_bytes=expected_bytes, max_bytes=max_bytes, headers=headers)
        if resp.status_code >= 400:
            raise HttpError(url, resp.status_code, "download failed")
        mode = "ab" if (have and resp.status_code == 206) else "wb"
        if mode == "wb":
            have = 0
        total = have
        try:
            with open(part, mode) as fh:
                for chunk in resp.iter_content(1 << 20):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    total += len(chunk)
                    if max_bytes is not None and total > max_bytes:
                        raise HttpError(url, resp.status_code, f"exceeds max_bytes={max_bytes}")
        finally:
            resp.close()
        if expected_bytes is not None and total != expected_bytes:
            raise HttpError(url, resp.status_code, f"size {total} != expected {expected_bytes}")
        sha = sha256_file(part)
        os.replace(part, dest)
        self.media_bytes += total
        self.media_files += 1
        return total, sha


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def iter_lines(resp: requests.Response) -> Iterator[str]:
    for line in resp.iter_lines(decode_unicode=True):
        if line is not None:
            yield line
