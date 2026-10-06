"""Configuration: configs/default.yaml, optionally merged with a user file and CLI flags."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .schema import PRECISION_RANK, TIERS

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "default.yaml"


def _merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


@dataclass
class SourceConfig:
    enabled: bool = True
    budget: int | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class Config:
    data_root: Path
    require_geo: bool = True
    min_geo_precision: str = "station"
    tiers: tuple[str, ...] = ("A", "B")
    include_sharealike: bool = False
    coastline_check: str = "flag"
    pilot_budget: int = 500
    pilot_order: tuple[str, ...] = ()
    http: dict[str, Any] = field(default_factory=dict)
    sources: dict[str, SourceConfig] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.min_geo_precision not in PRECISION_RANK:
            raise ValueError(f"min_geo_precision must be one of {list(PRECISION_RANK)}")
        bad = [t for t in self.tiers if t not in TIERS or t == "X"]
        if bad:
            raise ValueError(f"invalid tiers {bad}; choose from A, B, C, U")
        if self.coastline_check not in ("off", "flag", "reject"):
            raise ValueError("coastline_check must be off, flag or reject")

    def source(self, key: str) -> SourceConfig:
        return self.sources.get(key, SourceConfig())

    @property
    def selected_tiers(self) -> set[str]:
        tiers = set(self.tiers)
        if self.include_sharealike:
            tiers.add("C")
        return tiers


def load_config(path: Path | None = None, **overrides: Any) -> Config:
    with open(DEFAULT_CONFIG, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if path is not None:
        with open(path, encoding="utf-8") as fh:
            data = _merge(data, yaml.safe_load(fh) or {})
    data = _merge(data, {k: v for k, v in overrides.items() if v is not None and k != "data_root"})
    # Precedence: --data-root > AQUASOURCE_DATA_ROOT > config file.
    data_root = Path(
        overrides.get("data_root") or os.environ.get("AQUASOURCE_DATA_ROOT") or data.get("data_root") or "./data"
    ).expanduser()
    sources = {
        k: SourceConfig(
            enabled=bool((v or {}).get("enabled", True)),
            budget=(v or {}).get("budget"),
            options=dict((v or {}).get("options") or {}),
        )
        for k, v in (data.get("sources") or {}).items()
    }
    return Config(
        data_root=data_root,
        require_geo=bool(data.get("require_geo", True)),
        min_geo_precision=str(data.get("min_geo_precision", "station")),
        tiers=tuple(data.get("tiers", ["A", "B"])),
        include_sharealike=bool(data.get("include_sharealike", False)),
        coastline_check=str(data.get("coastline_check", "flag")),
        pilot_budget=int(data.get("pilot_budget", 500)),
        pilot_order=tuple(data.get("pilot_order") or ()),
        http=dict(data.get("http") or {}),
        sources=sources,
    )
