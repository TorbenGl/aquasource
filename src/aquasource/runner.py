"""Run one source in dry-run, pilot or download mode."""

from __future__ import annotations

import json
import logging
import time
from collections import Counter
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from .adapters.base import Adapter, Context, get_adapter_class
from .core.config import Config
from .core.geo import check_coordinate, on_land, precision_at_least
from .core.http import DryRunViolation, Http, HttpError
from .core.layout import DatasetLayout, reports_dir
from .core.manifest import JsonlLog, Manifest
from .core.schema import Candidate, Geo, Licence, sample_row

log = logging.getLogger(__name__)

MODES = ("dry-run", "pilot", "download")


@dataclass
class RunStats:
    source: str
    mode: str
    candidates: int = 0
    selected: int = 0
    downloaded: int = 0
    already_done: int = 0
    failed: int = 0
    bytes: int = 0
    by_precision: Counter = field(default_factory=Counter)  # all candidates
    by_tier: Counter = field(default_factory=Counter)  # all candidates
    selected_by_precision: Counter = field(default_factory=Counter)
    selected_by_tier: Counter = field(default_factory=Counter)
    media_types: Counter = field(default_factory=Counter)
    dropped: Counter = field(default_factory=Counter)
    bbox: list[float] | None = None  # [west, south, east, north] of selected samples
    capped_at: int | None = None
    budget: int | None = None
    estimate: dict[str, Any] = field(default_factory=dict)
    not_ready: list[str] = field(default_factory=list)
    error: str | None = None
    metadata_requests: int = 0
    media_requests_blocked: int = 0
    seconds: float = 0.0

    def add_bbox(self, lat: float, lon: float) -> None:
        if self.bbox is None:
            self.bbox = [lon, lat, lon, lat]
        else:
            self.bbox = [min(self.bbox[0], lon), min(self.bbox[1], lat), max(self.bbox[2], lon), max(self.bbox[3], lat)]

    def to_dict(self) -> dict[str, Any]:
        # Not dataclasses.asdict: it rebuilds Counters from (key, value) pairs and miscounts them.
        out: dict[str, Any] = {}
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, Counter):
                v = {k: n for k, n in v.items() if n}
            elif isinstance(v, (list, dict)):
                v = type(v)(v)
            out[f.name] = v
        return out


def make_http(cfg: Config, *, dry_run: bool, adapter_cls: type[Adapter] | None = None, request_log: Path | None = None) -> Http:
    hosts = dict(cfg.http.get("host_intervals") or {})
    if adapter_cls is not None:
        hosts = {**adapter_cls.host_intervals, **hosts}
    return Http(
        dry_run=dry_run,
        min_interval_s=float(cfg.http.get("min_interval_s", 1.0)),
        host_intervals=hosts,
        max_retries=int(cfg.http.get("max_retries", 5)),
        timeout_s=float(cfg.http.get("timeout_s", 60)),
        request_log=request_log,
    )


def _select_reason(cfg: Config, licence: Licence, geo: Geo) -> str | None:
    """Why a candidate is not selected, or None if it is selected."""
    if licence.tier == "X":
        return "licence excluded (NC/ND/research-only)"
    if licence.tier not in cfg.selected_tiers:
        return f"tier {licence.tier} not selected"
    if cfg.require_geo and geo.geo_precision == "none":
        return "no geolocation"
    if geo.geo_precision != "none" and not precision_at_least(geo.geo_precision, cfg.min_geo_precision):
        return f"geo_precision {geo.geo_precision} below {cfg.min_geo_precision}"
    return None


def run_source(
    cfg: Config,
    key: str,
    mode: str,
    *,
    budget: int | None = None,
    options: dict[str, Any] | None = None,
    max_candidates: int | None = None,
) -> RunStats:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    started = time.time()
    stats = RunStats(source=key, mode=mode, budget=budget)
    adapter_cls = get_adapter_class(key)
    dry_run = mode == "dry-run"
    layout = DatasetLayout(cfg.data_root, key).ensure()
    sa_layout = DatasetLayout(cfg.data_root, key, sharealike=True)
    req_log = reports_dir(cfg.data_root) / "requests" / f"{key}.{mode}.jsonl"
    http = make_http(cfg, dry_run=dry_run, adapter_cls=adapter_cls, request_log=req_log)
    opts = {**cfg.source(key).options, **(options or {})}
    ctx = Context(config=cfg, http=http, layout=layout, options=opts, dry_run=dry_run, failures=JsonlLog(layout.failures_jsonl))
    adapter = adapter_cls(ctx)

    stats.not_ready = adapter.check_ready()
    if stats.not_ready:
        stats.error = "not ready: " + "; ".join(stats.not_ready)
        log.warning("%s: %s", key, stats.error)
        stats.seconds = time.time() - started
        return stats
    try:
        stats.estimate = adapter.estimate() or {}
    except Exception as exc:  # estimates are optional
        log.info("%s: estimate failed: %s", key, exc)

    manifests: dict[bool, Manifest] = {}

    def manifest_for(sharealike: bool) -> Manifest:
        if sharealike not in manifests:
            lay = sa_layout.ensure() if sharealike else layout
            manifests[sharealike] = Manifest(lay.state_db)
        return manifests[sharealike]

    try:
        for cand in adapter.discover():
            stats.candidates += 1
            if max_candidates is not None and stats.candidates > max_candidates:
                stats.candidates -= 1
                stats.capped_at = max_candidates
                break
            if not _process(cfg, adapter, ctx, cand, stats, mode, layout, sa_layout, manifest_for):
                continue
            if budget is not None and stats.selected >= budget:
                break
    except DryRunViolation as exc:
        stats.media_requests_blocked += 1
        stats.error = f"adapter tried to download media during dry run: {exc}"
        log.error("%s: %s", key, stats.error)
    except Exception as exc:
        stats.error = f"{type(exc).__name__}: {exc}"
        log.exception("%s: run failed", key)
    finally:
        for sharealike, m in manifests.items():
            lay = sa_layout if sharealike else layout
            m.export(lay.samples_jsonl)
            m.close()
        stats.metadata_requests = http.metadata_requests
        stats.bytes = http.media_bytes
        stats.seconds = round(time.time() - started, 1)
        if not dry_run:
            _write_dataset_md(adapter_cls, layout, stats)
        runs = layout.metadata / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        (runs / f"{mode}.json").write_text(json.dumps(stats.to_dict(), indent=2), encoding="utf-8")
    return stats


def _process(cfg, adapter, ctx, cand: Candidate, stats: RunStats, mode, layout, sa_layout, manifest_for) -> bool:
    """Handle one candidate. Returns True if it counts as selected."""
    try:
        licence = adapter.resolve_licence(cand)
    except DryRunViolation:
        raise
    except Exception as exc:
        ctx.fail(cand.item_id, "licence", f"{type(exc).__name__}: {exc}")
        stats.failed += 1
        return False
    try:
        geo = adapter.resolve_geo(cand)
    except DryRunViolation:
        raise
    except Exception as exc:
        ctx.fail(cand.item_id, "geo", f"{type(exc).__name__}: {exc}")
        geo = Geo.none(geo_source=f"resolve_geo failed: {type(exc).__name__}")

    reason = check_coordinate(geo.lat, geo.lon)
    if reason:
        ctx.fail(cand.item_id, "geo_sanity", reason, lat=geo.lat, lon=geo.lon, geo_source=geo.geo_source)
        geo = Geo.none(geo_source=f"rejected ({reason}): {geo.geo_source}", depth_m=geo.depth_m)
    elif geo.lat is not None and cfg.coastline_check != "off":
        land = on_land(geo.lat, geo.lon)
        if land:
            if cfg.coastline_check == "reject":
                ctx.fail(cand.item_id, "geo_sanity", "coordinate is on land", lat=geo.lat, lon=geo.lon, geo_source=geo.geo_source)
                geo = Geo.none(geo_source=f"rejected (on land): {geo.geo_source}", depth_m=geo.depth_m)
            else:
                cand.extra["on_land_flag"] = True

    stats.by_tier[licence.tier] += 1
    stats.by_precision[geo.geo_precision] += 1
    why = _select_reason(cfg, licence, geo)
    if why:
        stats.dropped[why] += 1
        return False

    stats.selected += 1
    stats.selected_by_tier[licence.tier] += 1
    stats.selected_by_precision[geo.geo_precision] += 1
    stats.media_types[cand.media_type] += 1
    if geo.lat is not None:
        stats.add_bbox(geo.lat, geo.lon)
    if mode == "dry-run":
        return True

    sharealike = licence.tier == "C"
    lay = sa_layout if sharealike else layout
    manifest = manifest_for(sharealike)
    sid = cand.sample_id
    if manifest.is_complete(sid, cfg.data_root):
        stats.already_done += 1
        return True
    try:
        ref = adapter.resolve_media(cand)
        dest = lay.media_path(sid, cand.media_type, ref.ext)
        nbytes, sha = adapter.fetch_media(cand, ref, dest)
    except (HttpError, OSError, RuntimeError) as exc:
        ctx.fail(cand.item_id, "download", f"{type(exc).__name__}: {exc}", media_url=cand.media_url)
        stats.failed += 1
        stats.selected -= 1
        stats.selected_by_tier[licence.tier] -= 1
        stats.selected_by_precision[geo.geo_precision] -= 1
        stats.media_types[cand.media_type] -= 1
        return False
    rel = dest.relative_to(cfg.data_root).as_posix()
    manifest.upsert(sample_row(cand, licence, geo, local_path=rel, nbytes=nbytes, sha256=sha, status="downloaded"))
    if stats.downloaded % 50 == 0:
        manifest.commit()
    stats.downloaded += 1
    return True


def _write_dataset_md(adapter_cls: type[Adapter], layout: DatasetLayout, stats: RunStats) -> None:
    lines = [
        f"# {adapter_cls.name or adapter_cls.key}",
        "",
        f"- Key: `{adapter_cls.key}`",
        f"- Homepage: {adapter_cls.homepage or 'n/a'}",
        f"- Citation: {adapter_cls.citation or 'see samples.jsonl attribution field'}",
        f"- Manual steps: {adapter_cls.manual_steps or 'none'}",
        "",
        f"## Last run ({stats.mode})",
        "",
        f"- Candidates seen: {stats.candidates}",
        f"- Selected: {stats.selected} (downloaded now: {stats.downloaded}, already present: {stats.already_done})",
        f"- Selected by tier: {dict(stats.selected_by_tier)}",
        f"- Selected by geo_precision: {dict(stats.selected_by_precision)}",
        f"- Dropped: {dict(stats.dropped)}",
        f"- Bounding box (W, S, E, N): {stats.bbox}",
        "",
        "Every row of samples.jsonl carries its own licence, tier and attribution text.",
        "",
    ]
    layout.dataset_md.write_text("\n".join(lines), encoding="utf-8")
