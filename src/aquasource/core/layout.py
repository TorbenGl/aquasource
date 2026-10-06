"""On-disk layout.

    <data_root>/<key>/images/              still images (sharded: images/<ab>/<sample_id>.<ext>)
    <data_root>/<key>/videos/              video files
    <data_root>/<key>/metadata/
        samples.jsonl                      one row per selected sample
        failures.jsonl                     errors and rejected coordinates
        raw/                               provider metadata exactly as downloaded
        licences/                          licence texts / records
        DATASET.md                         citation, attribution, licence, geo summary
        state.sqlite                       resumable state (internal)
    <data_root>/_sharealike/<key>/...      tier C (CC BY-SA) samples, same structure
    <data_root>/_reports/                  merged samples.jsonl, samples.geojson, geo_report.md, ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

SHAREALIKE_DIR = "_sharealike"
REPORTS_DIR = "_reports"

_EXT_RE = re.compile(r"^[a-z0-9]{1,6}$")


def safe_ext(ext: str | None, default: str) -> str:
    ext = (ext or "").lower().lstrip(".")
    return ext if _EXT_RE.match(ext) else default


@dataclass(frozen=True)
class DatasetLayout:
    data_root: Path
    key: str
    sharealike: bool = False

    @property
    def root(self) -> Path:
        base = self.data_root / SHAREALIKE_DIR if self.sharealike else self.data_root
        return base / self.key

    @property
    def images(self) -> Path:
        return self.root / "images"

    @property
    def videos(self) -> Path:
        return self.root / "videos"

    @property
    def metadata(self) -> Path:
        return self.root / "metadata"

    @property
    def raw(self) -> Path:
        return self.metadata / "raw"

    @property
    def licences(self) -> Path:
        return self.metadata / "licences"

    @property
    def samples_jsonl(self) -> Path:
        return self.metadata / "samples.jsonl"

    @property
    def failures_jsonl(self) -> Path:
        return self.metadata / "failures.jsonl"

    @property
    def state_db(self) -> Path:
        return self.metadata / "state.sqlite"

    @property
    def dataset_md(self) -> Path:
        return self.metadata / "DATASET.md"

    def ensure(self) -> "DatasetLayout":
        for p in (self.images, self.videos, self.raw, self.licences):
            p.mkdir(parents=True, exist_ok=True)
        return self

    def media_path(self, sample_id: str, media_type: str, ext: str | None) -> Path:
        """Where a sample's file goes. Sharded by 2 hex chars to keep directories small."""
        shard = sample_id.rsplit("-", 1)[-1][:2]
        if media_type == "video":
            return self.videos / shard / f"{sample_id}.{safe_ext(ext, 'mp4')}"
        return self.images / shard / f"{sample_id}.{safe_ext(ext, 'jpg')}"


def reports_dir(data_root: Path) -> Path:
    return data_root / REPORTS_DIR
