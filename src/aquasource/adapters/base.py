"""Adapter interface shared by every dataset.

An adapter is a module ``aquasource/adapters/<key>.py`` with one class that
subclasses :class:`Adapter`, sets ``key`` (= folder name) and is decorated
with :func:`register`. The runner calls, per candidate::

    discover()  ->  resolve_licence()  ->  resolve_geo()  ->  resolve_media()  ->  fetch_media()

``discover`` must only read metadata. Media bytes are fetched by
``fetch_media`` and never during a dry run.
"""

from __future__ import annotations

import importlib
import json
import logging
import mimetypes
import os
import pkgutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Iterable
from urllib.parse import urlparse

from ..core.config import Config
from ..core.http import Http
from ..core.layout import DatasetLayout
from ..core.manifest import JsonlLog
from ..core.schema import Candidate, Geo, Licence

log = logging.getLogger(__name__)


@dataclass
class MediaRef:
    """How to fetch one media file."""

    url: str
    ext: str | None = None
    expected_bytes: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Context:
    """Everything an adapter needs at run time."""

    config: Config
    http: Http
    layout: DatasetLayout
    options: dict[str, Any]
    dry_run: bool
    failures: JsonlLog

    def save_raw(self, name: str, content: bytes | str) -> Path:
        """Store provider metadata under metadata/raw/<name> (overwrites)."""
        path = self.layout.raw / name
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        if isinstance(content, str):
            tmp.write_text(content, encoding="utf-8")
        else:
            tmp.write_bytes(content)
        os.replace(tmp, path)
        return path

    def cached_text(self, url: str, name: str, *, refresh: bool = False, **kwargs: Any) -> str:
        """GET a metadata document once and keep it in metadata/raw/<name>.

        Re-runs read the cached copy, so repeated dry runs do not hit the provider.
        """
        path = self.layout.raw / name
        if path.exists() and not refresh and not self.options.get("refresh_metadata"):
            return path.read_text(encoding="utf-8")
        text = self.http.get_text(url, **kwargs)
        self.save_raw(name, text)
        return text

    def cached_json(self, url: str, name: str, *, refresh: bool = False, **kwargs: Any) -> Any:
        return json.loads(self.cached_text(url, name, refresh=refresh, **kwargs))

    def fail(self, item_id: str, stage: str, reason: str, **extra: Any) -> None:
        self.failures.write({"source": self.layout.key, "item_id": item_id, "stage": stage, "reason": reason, **extra})


class Adapter(ABC):
    key: ClassVar[str]
    name: ClassVar[str] = ""
    homepage: ClassVar[str] = ""
    citation: ClassVar[str] = ""
    media_types: ClassVar[tuple[str, ...]] = ("image",)
    # Environment variables that must be set (e.g. API tokens).
    env_vars: ClassVar[tuple[str, ...]] = ()
    # Human steps the script cannot do (shown by `aquasource list` and the download script).
    manual_steps: ClassVar[str] = ""
    # Per-host request interval overrides, e.g. {"api.example.org": 2.0}.
    host_intervals: ClassVar[dict[str, float]] = {}

    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.http = ctx.http
        self.options = ctx.options

    # ---------------------------------------------------------------- required
    @abstractmethod
    def discover(self) -> Iterable[Candidate]:
        """Yield candidates from metadata only. Never download media here."""

    @abstractmethod
    def resolve_licence(self, cand: Candidate) -> Licence:
        """Licence at the most specific level available (file > record > collection)."""

    @abstractmethod
    def resolve_geo(self, cand: Candidate) -> Geo:
        """lat, lon, depth_m, geo_precision, geo_source, geo_inferred (+ uncertainty)."""

    # ---------------------------------------------------------------- optional
    def check_ready(self) -> list[str]:
        """Problems that stop this adapter from running (missing tokens etc.)."""
        return [f"environment variable {v} is not set" for v in self.env_vars if not os.environ.get(v)]

    def estimate(self) -> dict[str, Any]:
        """Optional cheap totals for the dry-run report (e.g. {'images': 1300000})."""
        return {}

    def resolve_media(self, cand: Candidate) -> MediaRef:
        return MediaRef(url=cand.media_url, ext=cand.ext or guess_ext(cand.media_url, cand.media_type))

    def fetch_media(self, cand: Candidate, ref: MediaRef, dest: Path) -> tuple[int, str]:
        """Download one media file to ``dest``. Override for tar members, APIs, CLIs."""
        return self.http.download(ref.url, dest, expected_bytes=ref.expected_bytes, headers=ref.headers or None)


def guess_ext(url: str, media_type: str) -> str:
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    if ext and len(ext) <= 5 and ext.isalnum():
        return ext
    guess = mimetypes.guess_extension(media_type) if "/" in media_type else None
    return (guess or "").lstrip(".") or ("mp4" if media_type == "video" else "jpg")


# ------------------------------------------------------------------ registry
_REGISTRY: dict[str, type[Adapter]] = {}


def register(cls: type[Adapter]) -> type[Adapter]:
    if not getattr(cls, "key", None):
        raise TypeError(f"{cls.__name__} has no key")
    _REGISTRY[cls.key] = cls
    return cls


def available_keys() -> list[str]:
    """Adapter module names in this package (one module per dataset)."""
    import aquasource.adapters as pkg

    return sorted(
        m.name for m in pkgutil.iter_modules(pkg.__path__) if not m.name.startswith("_") and m.name != "base"
    )


def get_adapter_class(key: str) -> type[Adapter]:
    if key not in _REGISTRY:
        try:
            importlib.import_module(f"aquasource.adapters.{key}")
        except ModuleNotFoundError as exc:
            if exc.name == f"aquasource.adapters.{key}":
                raise KeyError(f"no adapter for {key!r}; available: {', '.join(available_keys())}") from None
            raise
    if key not in _REGISTRY:
        raise KeyError(f"module aquasource.adapters.{key} does not register an adapter with key {key!r}")
    return _REGISTRY[key]
