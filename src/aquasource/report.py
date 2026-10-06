"""Reports: dry-run summary, merged samples.jsonl, samples.geojson, geo_report.md (+ map), failures."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .core.layout import REPORTS_DIR, SHAREALIKE_DIR
from .core.manifest import Manifest
from .core.schema import GEO_PRECISIONS, TIER_LABELS

# Coarse sea / basin boxes (lat_min, lat_max, lon_min, lon_max), checked in order.
_SEAS = [
    ("Baltic Sea", 53.0, 66.0, 9.5, 30.5),
    ("North Sea", 51.0, 61.0, -4.0, 9.5),
    ("Mediterranean Sea", 30.0, 46.0, -6.0, 36.5),
    ("Black Sea", 40.5, 47.0, 27.0, 42.0),
    ("Red Sea", 12.0, 30.0, 32.0, 44.0),
    ("Caribbean / Gulf of Mexico", 8.0, 31.0, -98.0, -60.0),
]


def region_of(lat: float, lon: float) -> str:
    """Approximate water body for summary tables (not for science)."""
    for name, la0, la1, lo0, lo1 in _SEAS:
        if la0 <= lat <= la1 and lo0 <= lon <= lo1:
            return name
    if lat >= 66.5:
        return "Arctic Ocean"
    if lat <= -60.0:
        return "Southern Ocean"
    if 20.0 <= lon <= 147.0 and lat <= 30.0 and not (lon > 100.0 and lat > 0.0):
        return "Indian Ocean"
    if lat > 8.0:
        atlantic = -100.0 < lon <= 20.0 and not (lon < -82.0 and lat < 50.0)
    else:
        atlantic = -70.0 <= lon <= 20.0
    return "Atlantic Ocean" if atlantic else "Pacific Ocean"


def climate_band(lat: float) -> str:
    a = abs(lat)
    if a < 23.5:
        return "tropical"
    if a < 35.0:
        return "subtropical"
    if a < 66.5:
        return "temperate"
    return "polar"


# ------------------------------------------------------------------ dry run
def write_dry_run_report(reports: Path, stats: list[dict[str, Any]]) -> Path:
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "dry_run.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    lines = [
        "# Dry run (metadata only)",
        "",
        "No media files were downloaded: the HTTP client refuses media requests in dry-run mode",
        "(`media requests blocked` must be 0 and the per-source request logs in `_reports/requests/` contain only metadata requests).",
        "",
        "| source | candidates | selected | image | segment | station | fixed_site | region | none | tiers (all candidates) | bbox (W,S,E,N) | notes |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for s in stats:
        n = max(s.get("candidates", 0), 1)
        prec = s.get("by_precision", {})
        shares = [f"{100 * prec.get(p, 0) / n:.0f}%" for p in GEO_PRECISIONS]
        tiers = ", ".join(f"{t}:{c}" for t, c in sorted(s.get("by_tier", {}).items())) or "-"
        bbox = s.get("bbox")
        bbox_s = ", ".join(f"{v:.2f}" for v in bbox) if bbox else "-"
        notes = []
        if s.get("capped_at"):
            notes.append(f"stopped after {s['capped_at']} candidates")
        if s.get("budget"):
            notes.append(f"budget {s['budget']}")
        if s.get("estimate"):
            notes.append("provider total: " + ", ".join(f"{k}={v}" for k, v in s["estimate"].items()))
        if s.get("error"):
            notes.append(f"ERROR: {s['error']}")
        if s.get("media_requests_blocked"):
            notes.append(f"media requests blocked: {s['media_requests_blocked']}")
        lines.append(
            f"| {s['source']} | {s.get('candidates', 0)} | {s.get('selected', 0)} | "
            + " | ".join(shares)
            + f" | {tiers} | {bbox_s} | {'; '.join(notes)} |"
        )
    lines += ["", "Shares are over all candidates seen; `selected` applies require_geo, min_geo_precision and the tier filter.", ""]
    drops: dict[str, Counter] = {s["source"]: Counter(s.get("dropped", {})) for s in stats}
    if any(drops.values()):
        lines += ["## Why candidates were dropped", ""]
        for src, c in drops.items():
            if c:
                lines.append(f"- **{src}**: " + "; ".join(f"{k} ({v})" for k, v in c.most_common()))
        lines.append("")
    lines += ["Tiers: " + "; ".join(f"{k} = {v}" for k, v in TIER_LABELS.items()), ""]
    path = reports / "dry_run.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# --------------------------------------------------------------- geo report
def _dataset_dirs(data_root: Path) -> Iterable[tuple[str, bool, Path]]:
    for base, sharealike in ((data_root, False), (data_root / SHAREALIKE_DIR, True)):
        if not base.exists():
            continue
        for d in sorted(base.iterdir()):
            if d.is_dir() and not d.name.startswith("_") and (d / "metadata" / "state.sqlite").exists():
                yield d.name, sharealike, d


def build_reports(data_root: Path) -> dict[str, Path]:
    data_root = Path(data_root)
    reports = data_root / REPORTS_DIR
    reports.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for key, sharealike, d in _dataset_dirs(data_root):
        with Manifest(d / "metadata" / "state.sqlite") as m:
            for r in m.rows("downloaded"):
                r["shard"] = "sharealike" if sharealike else "main"
                rows.append(r)
        fpath = d / "metadata" / "failures.jsonl"
        if fpath.exists():
            with open(fpath, encoding="utf-8") as fh:
                failures.extend(json.loads(line) for line in fh if line.strip())

    out: dict[str, Path] = {}
    out["samples"] = reports / "samples.jsonl"
    with open(out["samples"], "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    out["failures"] = reports / "failures.jsonl"
    with open(out["failures"], "w", encoding="utf-8") as fh:
        for f in failures:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")
    out["geojson"] = reports / "samples.geojson"
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": {
                k: r.get(k)
                for k in ("sample_id", "source", "media_type", "licence_tier", "geo_precision", "geo_inferred", "geo_uncertainty_m", "depth_m", "timestamp", "local_path", "shard")
            },
        }
        for r in rows
        if r.get("lat") is not None and r.get("lon") is not None
    ]
    out["geojson"].write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")
    map_path = _write_map(reports, rows)
    out["geo_report"] = _write_geo_report(reports, rows, failures, map_path)
    return out


def _table(title: str, counter: Counter, total: int) -> list[str]:
    lines = [f"### {title}", "", "| value | samples | share |", "|---|---:|---:|"]
    for k, v in counter.most_common():
        lines.append(f"| {k} | {v} | {100 * v / max(total, 1):.1f}% |")
    return lines + [""]


def _write_geo_report(reports: Path, rows: list[dict[str, Any]], failures: list[dict[str, Any]], map_path: Path | None) -> Path:
    total = len(rows)
    geo_rows = [r for r in rows if r.get("lat") is not None]
    by_source = Counter(r["source"] for r in rows)
    by_prec = Counter(r["geo_precision"] for r in rows)
    by_tier = Counter(r["licence_tier"] for r in rows)
    by_region = Counter(region_of(r["lat"], r["lon"]) for r in geo_rows)
    by_band = Counter(climate_band(r["lat"]) for r in geo_rows)
    by_media = Counter(r["media_type"] for r in rows)
    inferred = sum(1 for r in rows if r.get("geo_inferred"))
    per_source_prec: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        per_source_prec[r["source"]][r["geo_precision"]] += 1
    geo_fail = [f for f in failures if f.get("stage") == "geo_sanity"]

    lines = [
        "# Geo report",
        "",
        f"- Samples: **{total}** ({by_media.get('image', 0)} images, {by_media.get('video', 0)} videos)",
        f"- With coordinates: {len(geo_rows)}; coordinates inferred (station/site/nav/publication): {inferred}",
        f"- Rejected coordinates (sanity checks): {len(geo_fail)} — listed in `failures.jsonl`",
        "",
    ]
    if map_path is not None:
        lines += [f"![map]({map_path.name})", ""]
    lines += _table("By source", by_source, total)
    lines += ["### Precision by source", "", "| source | " + " | ".join(GEO_PRECISIONS) + " |", "|---|" + "---:|" * len(GEO_PRECISIONS)]
    for src, c in sorted(per_source_prec.items()):
        lines.append(f"| {src} | " + " | ".join(str(c.get(p, 0)) for p in GEO_PRECISIONS) + " |")
    lines.append("")
    lines += _table("By geo_precision", by_prec, total)
    lines += _table("By region (approximate water body)", by_region, len(geo_rows))
    lines += _table("By climate band", by_band, len(geo_rows))
    lines += _table("By licence tier", by_tier, total)
    path = reports / "geo_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _write_map(reports: Path, rows: list[dict[str, Any]]) -> Path | None:
    pts = [(r["lon"], r["lat"], r["source"]) for r in rows if r.get("lat") is not None]
    if not pts:
        return None
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return _write_svg_map(reports, pts)
    fig, ax = plt.subplots(figsize=(12, 6), dpi=120)
    sources = sorted({p[2] for p in pts})
    for s in sources:
        xs = [p[0] for p in pts if p[2] == s]
        ys = [p[1] for p in pts if p[2] == s]
        ax.scatter(xs, ys, s=6, label=f"{s} ({len(xs)})", alpha=0.7)
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.grid(True, linewidth=0.3)
    ax.legend(fontsize=7, markerscale=2, loc="lower left", ncol=2)
    ax.set_title("aquasource samples")
    path = reports / "map.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def _write_svg_map(reports: Path, pts: list[tuple[float, float, str]]) -> Path:
    """Dependency-free equirectangular scatter (no coastlines)."""
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    sources = sorted({p[2] for p in pts})
    color = {s: palette[i % len(palette)] for i, s in enumerate(sources)}
    w, h = 1080, 540
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h + 20 * len(sources)}" viewBox="0 0 {w} {h + 20 * len(sources)}">',
             f'<rect width="{w}" height="{h}" fill="#eef4f8" stroke="#999"/>']
    for lon in range(-180, 181, 30):
        x = (lon + 180) / 360 * w
        parts.append(f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{h}" stroke="#ccc" stroke-width="0.5"/>')
    for lat in range(-90, 91, 30):
        y = (90 - lat) / 180 * h
        parts.append(f'<line x1="0" y1="{y:.1f}" x2="{w}" y2="{y:.1f}" stroke="#ccc" stroke-width="0.5"/>')
    for lon, lat, s in pts:
        x = (lon + 180) / 360 * w
        y = (90 - lat) / 180 * h
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="{color[s]}" fill-opacity="0.7"/>')
    for i, s in enumerate(sources):
        y = h + 15 + 20 * i
        parts.append(f'<circle cx="10" cy="{y - 4}" r="5" fill="{color[s]}"/><text x="20" y="{y}" font-size="12" font-family="sans-serif">{s}</text>')
    parts.append("</svg>")
    path = reports / "map.svg"
    path.write_text("\n".join(parts), encoding="utf-8")
    return path
