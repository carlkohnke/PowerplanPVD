"""Configuration parsing and validation."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigurationError


@dataclass(frozen=True)
class TargetConfig:
    name: str
    rate_nm_per_min_per_watt: float
    min_stable_power_w: float = 0.0
    off_below_power_w: float = 0.0
    max_power_w: float | None = None
    max_ramp_rate_w_per_s: float | None = None

    def validate(self) -> None:
        if not self.name.strip():
            raise ConfigurationError("Each target needs a non-empty name.")
        if self.rate_nm_per_min_per_watt <= 0:
            raise ConfigurationError(
                f"Target {self.name!r} needs a positive rate_nm_per_min_per_watt."
            )
        if self.off_below_power_w < 0 or self.min_stable_power_w < 0:
            raise ConfigurationError(f"Target {self.name!r} power thresholds cannot be negative.")
        if self.off_below_power_w > self.min_stable_power_w:
            raise ConfigurationError(
                f"Target {self.name!r}: off_below_power_w cannot exceed min_stable_power_w."
            )
        if self.max_power_w is not None and self.max_power_w <= 0:
            raise ConfigurationError(f"Target {self.name!r} max_power_w must be positive.")
        if self.max_power_w is not None and self.min_stable_power_w > self.max_power_w:
            raise ConfigurationError(
                f"Target {self.name!r}: min_stable_power_w exceeds max_power_w."
            )
        if self.max_ramp_rate_w_per_s is not None and self.max_ramp_rate_w_per_s <= 0:
            raise ConfigurationError(
                f"Target {self.name!r} max_ramp_rate_w_per_s must be positive."
            )


@dataclass(frozen=True)
class ProfileConfig:
    path: Path
    distance_column: str | int = "distance_nm"
    composition_columns: Mapping[str, str | int] = field(default_factory=dict)
    sheet: str | None = None
    header_row: int = 1
    data_start_row: int | None = None
    data_end_row: int | None = None
    composition_basis: str = "fraction"
    normalize_compositions: bool = False
    composition_sum_tolerance: float = 1e-6

    def validate(self) -> None:
        if not self.path.exists():
            raise ConfigurationError(f"Composition profile does not exist: {self.path}")
        if self.header_row < 1:
            raise ConfigurationError("profile.header_row is one-based and must be at least 1.")
        if self.data_start_row is not None and self.data_start_row < 1:
            raise ConfigurationError("profile.data_start_row must be at least 1.")
        if self.data_end_row is not None and self.data_end_row < 1:
            raise ConfigurationError("profile.data_end_row must be at least 1.")
        start = self.data_start_row or self.header_row + 1
        if self.data_end_row is not None and self.data_end_row < start:
            raise ConfigurationError(
                "profile.data_end_row must be greater than or equal to the first data row."
            )
        if self.composition_basis not in {"fraction", "percent"}:
            raise ConfigurationError("profile.composition_basis must be 'fraction' or 'percent'.")
        if self.composition_sum_tolerance <= 0:
            raise ConfigurationError("profile.composition_sum_tolerance must be positive.")


@dataclass(frozen=True)
class OperationConfig:
    strategy: str = "total_power"
    total_power_w: float | None = None
    fixed_target: str | None = None
    fixed_power_w: float | None = None
    hardware_limit_policy: str = "clip"

    def validate(self, target_names: set[str]) -> None:
        if self.strategy not in {"total_power", "fixed_target"}:
            raise ConfigurationError("operation.strategy must be 'total_power' or 'fixed_target'.")
        if self.hardware_limit_policy not in {"clip", "error"}:
            raise ConfigurationError("operation.hardware_limit_policy must be 'clip' or 'error'.")
        if self.strategy == "total_power":
            if self.total_power_w is None or self.total_power_w <= 0:
                raise ConfigurationError("total_power strategy requires positive total_power_w.")
        else:
            if self.fixed_target not in target_names:
                raise ConfigurationError(
                    f"fixed_target must name one configured target; got {self.fixed_target!r}."
                )
            if self.fixed_power_w is None or self.fixed_power_w <= 0:
                raise ConfigurationError("fixed_target strategy requires positive fixed_power_w.")


@dataclass(frozen=True)
class PlannerConfig:
    power_tolerance_abs_w: float = 2.0
    power_tolerance_rel: float = 0.05
    composition_tolerance_abs: float = 0.02
    max_breakpoints: int = 100
    ramp_rate_resolution_w_per_s: float = 0.001

    def validate(self) -> None:
        if self.power_tolerance_abs_w < 0 or self.power_tolerance_rel < 0:
            raise ConfigurationError("Planner power tolerances cannot be negative.")
        if self.composition_tolerance_abs <= 0:
            raise ConfigurationError("planner.composition_tolerance_abs must be positive.")
        if self.max_breakpoints < 2:
            raise ConfigurationError("planner.max_breakpoints must be at least 2.")
        if self.ramp_rate_resolution_w_per_s <= 0:
            raise ConfigurationError("planner.ramp_rate_resolution_w_per_s must be positive.")


@dataclass(frozen=True)
class PlanConfig:
    targets: tuple[TargetConfig, ...]
    profile: ProfileConfig
    operation: OperationConfig
    planner: PlannerConfig = field(default_factory=PlannerConfig)
    name: str = "PowerplanPVD plan"

    @property
    def target_names(self) -> tuple[str, ...]:
        return tuple(target.name for target in self.targets)

    def validate(self) -> None:
        if len(self.targets) < 1:
            raise ConfigurationError("At least one target is required.")
        for target in self.targets:
            target.validate()
        names = self.target_names
        folded_names = [name.casefold() for name in names]
        if len(set(folded_names)) != len(folded_names):
            raise ConfigurationError("Target names must be unique, ignoring capitalization.")
        unknown = set(self.profile.composition_columns) - set(names)
        if unknown:
            raise ConfigurationError(
                "profile.composition_columns contains unknown targets: "
                + ", ".join(sorted(unknown))
            )
        self.profile.validate()
        self.operation.validate(set(names))
        self.planner.validate()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["profile"]["path"] = str(self.profile.path)
        return data


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{label} must be a mapping.")
    return value


def _resolve_path(raw: str, base_dir: Path) -> Path:
    expanded_text = os.path.expandvars(os.path.expanduser(raw))
    if re.search(r"\$(?:[A-Za-z_][A-Za-z0-9_]*|\{[^}]+\})|%[^%]+%", expanded_text):
        raise ConfigurationError(
            f"Profile path contains an unresolved environment variable: {raw!r}. "
            "Set the variable or replace it with a file path."
        )
    expanded = Path(expanded_text)
    return expanded if expanded.is_absolute() else (base_dir / expanded).resolve()


def plan_config_from_dict(data: Mapping[str, Any], base_dir: Path | None = None) -> PlanConfig:
    base_dir = (base_dir or Path.cwd()).resolve()
    root = _mapping(data, "configuration")

    targets_raw = root.get("targets")
    if not isinstance(targets_raw, list):
        raise ConfigurationError("targets must be a list.")
    try:
        targets = tuple(TargetConfig(**_mapping(item, "target")) for item in targets_raw)
    except TypeError as exc:
        raise ConfigurationError(f"Invalid target settings: {exc}") from exc

    profile_raw = dict(_mapping(root.get("profile"), "profile"))
    if "path" not in profile_raw:
        raise ConfigurationError("profile.path is required.")
    profile_raw["path"] = _resolve_path(str(profile_raw["path"]), base_dir)
    try:
        profile = ProfileConfig(**profile_raw)
        operation = OperationConfig(**dict(_mapping(root.get("operation", {}), "operation")))
        planner = PlannerConfig(**dict(_mapping(root.get("planner", {}), "planner")))
    except TypeError as exc:
        raise ConfigurationError(f"Invalid configuration field: {exc}") from exc
    config = PlanConfig(
        name=str(root.get("name", "PowerplanPVD plan")),
        targets=targets,
        profile=profile,
        operation=operation,
        planner=planner,
    )
    try:
        config.validate()
    except (AttributeError, TypeError) as exc:
        raise ConfigurationError(
            f"A configuration value has the wrong type: {exc}. "
            "Check that names are text and numeric settings are numbers."
        ) from exc
    return config


def load_config(path: str | Path) -> PlanConfig:
    config_path = Path(path).resolve()
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigurationError(f"Could not read configuration {config_path}: {exc}") from exc
    try:
        if config_path.suffix.lower() == ".json":
            data = json.loads(text)
        else:
            data = yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"Invalid configuration syntax in {config_path}: {exc}") from exc
    return plan_config_from_dict(data, config_path.parent)
