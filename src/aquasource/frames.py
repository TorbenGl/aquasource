"""Extract still frames from downloaded videos (optional, needs ffmpeg).

Frames go to ``<dataset>/images/frames/<video_sample_id>/t<seconds>.jpg`` and are
added to the same manifest as image samples with ``extra.from_video``. Each frame
gets its own geo: the adapter's ``frame_geo(video_row, t_s)`` if it implements one
(e.g. navigation interpolation -> ``segment``), otherwise the video's geo copied
over (station / fixed_site, ``geo_inferred: true``).
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .adapters.base import Context, get_adapter_class
from .core.config import Config
from .core.http import Http, sha256_file
from .core.layout import DatasetLayout
from .core.manifest import JsonlLog, Manifest
from .core.schema import Geo, make_sample_id

log = logging.getLogger(__name__)


def _duration_s(path: Path) -> float | None:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=120, check=True,
        )
        return float(json.loads(out.stdout)["format"]["duration"])
    except Exception:
        return None


def extract_frames(cfg: Config, key: str, *, every_s: float = 10.0, max_per_video: int = 30, sharealike: bool = False) -> dict[str, int]:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is not installed")
    layout = DatasetLayout(cfg.data_root, key, sharealike=sharealike)
    adapter_cls = get_adapter_class(key)
    ctx = Context(cfg, Http(dry_run=True), layout, cfg.source(key).options, True, JsonlLog(layout.failures_jsonl))
    adapter = adapter_cls(ctx)
    frame_geo = getattr(adapter, "frame_geo", None)
    counts = {"videos": 0, "frames": 0, "skipped": 0}
    with Manifest(layout.state_db) as m:
        videos = [r for r in m.rows("downloaded") if r["media_type"] == "video"]
        for row in videos:
            src = cfg.data_root / row["local_path"]
            if not src.exists():
                counts["skipped"] += 1
                continue
            dur = _duration_s(src)
            if not dur:
                ctx.fail(row["item_id"], "frames", "could not read video duration")
                counts["skipped"] += 1
                continue
            counts["videos"] += 1
            n = min(max_per_video, max(1, int(dur // every_s)))
            step = dur / n
            out_dir = layout.images / "frames" / row["sample_id"]
            out_dir.mkdir(parents=True, exist_ok=True)
            for i in range(n):
                t = round(step * (i + 0.5), 2)
                item_id = f"{row['item_id']}#t={t:.2f}"
                sid = make_sample_id(key, item_id)
                if m.is_complete(sid, cfg.data_root):
                    continue
                dest = out_dir / f"t{t:09.2f}.jpg"
                try:
                    subprocess.run(
                        ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", str(t), "-i", str(src), "-frames:v", "1", "-q:v", "2", str(dest)],
                        check=True, timeout=300,
                    )
                except Exception as exc:
                    ctx.fail(item_id, "frames", f"ffmpeg failed: {exc}")
                    continue
                geo = frame_geo(row, t) if callable(frame_geo) else None
                if geo is None:
                    geo = Geo(row["lat"], row["lon"], row["depth_m"], row["geo_precision"], row["geo_source"], True, row.get("geo_uncertainty_m")) if row["geo_precision"] != "none" else Geo.none(row["geo_source"])
                frame: dict[str, Any] = dict(row)
                frame.update(geo.to_dict())
                frame.update(
                    sample_id=sid,
                    item_id=item_id,
                    media_type="image",
                    local_path=dest.relative_to(cfg.data_root).as_posix(),
                    bytes=dest.stat().st_size,
                    sha256=sha256_file(dest),
                    status="downloaded",
                    extra={**(row.get("extra") or {}), "from_video": row["sample_id"], "t_s": t},
                )
                m.upsert(frame)
                counts["frames"] += 1
            m.commit()
        m.export(layout.samples_jsonl)
    return counts
