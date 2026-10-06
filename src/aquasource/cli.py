"""Command line: aquasource list | check | dry-run | pilot | download | report."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

from .adapters.base import available_keys, get_adapter_class
from .core.config import load_config
from .core.layout import reports_dir
from .report import build_reports, write_dry_run_report
from .runner import run_source


def _parse_options(items: list[str] | None) -> dict[str, Any]:
    """--opt key=value (value parsed as JSON when possible)."""
    out: dict[str, Any] = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"--opt expects key=value, got {item!r}")
        k, v = item.split("=", 1)
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v
    return out


def _sources(cfg, arg: str | None, default: list[str]) -> list[str]:
    if arg:
        return [s.strip() for s in arg.split(",") if s.strip()]
    return default


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="aquasource", description=__doc__)
    p.add_argument("--config", type=Path, help="YAML merged on top of configs/default.yaml")
    p.add_argument("--data-root", type=Path, help="override data_root / AQUASOURCE_DATA_ROOT")
    p.add_argument("--no-require-geo", action="store_true", help="keep samples without geolocation")
    p.add_argument("--min-geo-precision", choices=["image", "segment", "station", "fixed_site", "region", "none"])
    p.add_argument("--include-sharealike", action="store_true", help="also select tier C into _sharealike/")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list adapters, manual steps and readiness")
    c = sub.add_parser("check", help="check adapters are ready (tokens, tools)")
    c.add_argument("--sources")

    d = sub.add_parser("dry-run", help="metadata only for every enabled source; no media")
    d.add_argument("--sources", help="comma-separated keys (default: enabled sources in config)")
    d.add_argument("--max-candidates", type=int, default=20000, help="stop enumerating a source after N candidates")

    pl = sub.add_parser("pilot", help="small download per source in pilot order")
    pl.add_argument("--sources")
    pl.add_argument("--budget", type=int)

    dl = sub.add_parser("download", help="download one dataset")
    dl.add_argument("key")
    dl.add_argument("--budget", type=int, help="max selected samples (default: source budget, else unlimited)")
    dl.add_argument("--opt", action="append", metavar="KEY=VALUE", help="adapter option, repeatable")
    dl.add_argument("--dry-run", action="store_true", help="metadata only for this dataset")

    sub.add_parser("report", help="build _reports/: samples.jsonl, samples.geojson, geo_report.md, failures.jsonl")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    overrides: dict[str, Any] = {"data_root": args.data_root}
    if args.no_require_geo:
        overrides["require_geo"] = False
    if args.min_geo_precision:
        overrides["min_geo_precision"] = args.min_geo_precision
    if args.include_sharealike:
        overrides["include_sharealike"] = True
    cfg = load_config(args.config, **overrides)

    if args.cmd == "list":
        for key in available_keys():
            try:
                cls = get_adapter_class(key)
            except Exception as exc:
                print(f"{key:22s} ERROR {exc}")
                continue
            src = cfg.source(key)
            flag = "enabled" if src.enabled and key in cfg.sources else "off"
            print(f"{key:22s} {flag:8s} {cls.name}")
            if cls.env_vars:
                print(f"{'':31s}needs env: {', '.join(cls.env_vars)}")
            if cls.manual_steps:
                print(f"{'':31s}manual: {cls.manual_steps}")
        return 0

    enabled = [k for k, s in cfg.sources.items() if s.enabled and k in available_keys()]

    if args.cmd == "check":
        bad = 0
        for key in _sources(cfg, args.sources, available_keys()):
            from .adapters.base import Context
            from .core.http import Http
            from .core.layout import DatasetLayout
            from .core.manifest import JsonlLog

            cls = get_adapter_class(key)
            lay = DatasetLayout(cfg.data_root, key)
            ctx = Context(cfg, Http(dry_run=True), lay, cfg.source(key).options, True, JsonlLog(cfg.data_root / ".check_failures.jsonl"))
            problems = cls(ctx).check_ready()
            print(f"{key:22s} {'OK' if not problems else 'NOT READY: ' + '; '.join(problems)}")
            bad += bool(problems)
        return 1 if bad else 0

    if args.cmd == "dry-run":
        stats = []
        for key in _sources(cfg, args.sources, enabled):
            logging.info("dry run: %s", key)
            s = run_source(cfg, key, "dry-run", max_candidates=args.max_candidates, budget=None)
            stats.append(s.to_dict())
        path = write_dry_run_report(reports_dir(cfg.data_root), stats)
        print(path.read_text(encoding="utf-8"))
        return 0

    if args.cmd == "pilot":
        order = _sources(cfg, args.sources, [k for k in cfg.pilot_order if k in available_keys()])
        budget = args.budget or cfg.pilot_budget
        for key in order:
            logging.info("pilot: %s (budget %d)", key, budget)
            s = run_source(cfg, key, "pilot", budget=budget)
            print(json.dumps({k: v for k, v in s.to_dict().items() if k in ("source", "selected", "downloaded", "already_done", "failed", "bytes", "error")}))
        build_reports(cfg.data_root)
        return 0

    if args.cmd == "download":
        budget = args.budget if args.budget is not None else cfg.source(args.key).budget
        mode = "dry-run" if args.dry_run else "download"
        s = run_source(cfg, args.key, mode, budget=budget, options=_parse_options(args.opt))
        print(json.dumps(s.to_dict(), indent=2))
        return 1 if s.error else 0

    if args.cmd == "report":
        out = build_reports(cfg.data_root)
        for k, v in out.items():
            print(f"{k}: {v}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
