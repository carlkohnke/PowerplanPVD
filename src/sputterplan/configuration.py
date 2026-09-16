"""Configuration parsing and validation."""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from numbers import Real
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigurationError


def _finite_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(float(value))


def _positive_number(value: Any) -> bool:
    return _finite_number(value) and float(value) > 0


def _nonnegative_number(value: Any) -> bool:
    return _finite_number(value) and float(value) >= 0


def _one_based_row(value: Any, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ConfigurationError(f"{label} is one-based and must be a positive integer.")


def _column_spec(value: Any, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ConfigurationError(f"{label} must be a column name or one-based column number.")
    if isinstance(value, int) and value < 1:
        raise ConfigurationError(f"{label} column number must be at least 1.")
    if isinstance(value, str) and not value.strip():
        raise ConfigurationError(f"{label} column name cannot be empty.")


@dataclass(frozen=True)
class TargetConfig:
    name: str
    rate_nm_per_min_per_watt: float
    min_stable_power_w: float = 0.0
    off_below_power_w: float = 0.0
    max_power_w: float | None = None
    max_ramp_rate_w_per_s: float | None = None

    def validate(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ConfigurationError("Each target needs a non-empty name.")
        if not isinstance(self.rate_nm_per_min_per_watt, Real) or isinstance(
            self.rate_nm_per_min_per_watt, bool
        ):
            raise ConfigurationError(
                f"Target {self.name!r} rate_nm_per_min_per_watt has the wrong type; "
                "expected a number."
            )
        if not _positive_number(self.rate_nm_per_min_per_watt):
            raise ConfigurationError(
                f"Target {self.name!r} needs a finite, positive rate_nm_per_min_per_watt."
            )
        if not _nonnegative_number(self.off_below_power_w) or not _nonnegative_number(
            self.min_stable_power_w
        ):
            raise ConfigurationError(
                f"Target {self.name!r} power thresholds must be finite and non-negative."
            )
        if self.off_below_power_w > self.min_stable_power_w:
            raise ConfigurationError(
                f"Target {self.name!r}: off_below_power_w cannot exceed min_stable_power_w."
            )
        if self.max_power_w is not None and not _positive_number(self.max_power_w):
            raise ConfigurationError(
                f"Target {self.name!r} max_power_w must be finite and positive."
            )
        if self.max_power_w is not None and self.min_stable_power_w > self.max_power_w:
            raise ConfigurationError(
                f"Target {self.name!r}: min_stable_power_w exceeds max_power_w."
            )
        if self.max_ramp_rate_w_per_s is not None and not _positive_number(
            self.max_ramp_rate_w_per_s
        ):
            raise ConfigurationError(
                f"Target {self.name!r} max_ramp_rate_w_per_s must be finite and positive."
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
        if not isinstance(self.path, Path):
            raise ConfigurationError("profile.path must be a filesystem path.")
        if not self.path.is_file():
            raise ConfigurationError(
                f"Composition profile does not exist or is not a file: {self.path}"
            )
        _one_based_row(self.header_row, "profile.header_row")
        if self.data_start_row is not None:
            _one_based_row(self.data_start_row, "profile.data_start_row")
            if self.data_start_row <= self.header_row:
                raise ConfigurationError("profile.data_start_row must be after profile.header_row.")
        if self.data_end_row is not None:
            _one_based_row(self.data_end_row, "profile.data_end_row")
        start = self.data_start_row or self.header_row + 1
        if self.data_end_row is not None and self.data_end_row < start:
            raise ConfigurationError(
                "profile.data_end_row must be greater than or equal to the first data row."
            )
        if not isinstance(self.composition_basis, str) or self.composition_basis not in {
            "fraction",
            "percent",
        }:
            raise ConfigurationError("profile.composition_basis must be 'fraction' or 'percent'.")
        if not isinstance(self.normalize_compositions, bool):
            raise ConfigurationError("profile.normalize_compositions must be true or false.")
        if not _positive_number(self.composition_sum_tolerance):
            raise ConfigurationError(
                "profile.composition_sum_tolerance must be finite and positive."
            )
        _column_spec(self.distance_column, "profile.distance_column")
        if not isinstance(self.composition_columns, Mapping):
            raise ConfigurationError("profile.composition_columns must be a mapping.")
        for name, spec in self.composition_columns.items():
            if not isinstance(name, str) or not name.strip():
                raise ConfigurationError(
                    "profile.composition_columns target names must be non-empty text."
                )
            _column_spec(spec, f"profile.composition_columns[{name!r}]")
        if self.sheet is not None and (not isinstance(self.sheet, str) or not self.sheet.strip()):
            raise ConfigurationError("profile.sheet must be non-empty text when provided.")


@dataclass(frozen=True)
class OperationConfig:
    strategy: str = "max_total_power"
    max_total_power_w: float | None = None
    fixed_target: str | None = None
    fixed_power_w: float | None = None
    hardware_limit_policy: str = "clip"

    def validate(self, target_names: set[str]) -> None:
        if not isinstance(self.strategy, str) or self.strategy not in {
            "max_total_power",
            "fixed_target",
        }:
            raise ConfigurationError(
                "operation.strategy must be 'max_total_power' or 'fixed_target'."
            )
        if not isinstance(self.hardware_limit_policy, str) or self.hardware_limit_policy not in {
            "clip",
            "error",
        }:
            raise ConfigurationError("operation.hardware_limit_policy must be 'clip' or 'error'.")
        if self.max_total_power_w is not None and not _positive_number(self.max_total_power_w):
            raise ConfigurationError("operation.max_total_power_w must be finite and positive.")
        if self.fixed_power_w is not None and not _positive_number(self.fixed_power_w):
            raise ConfigurationError("operation.fixed_power_w must be finite and positive.")
        if self.fixed_target is not None and not isinstance(self.fixed_target, str):
            raise ConfigurationError("operation.fixed_target must be a target name.")
        if self.strategy == "max_total_power":
            if not _positive_number(self.max_total_power_w):
                raise ConfigurationError(
                    "max_total_power strategy requires finite, positive max_total_power_w."
                )
        else:
            if not isinstance(self.fixed_target, str) or self.fixed_target not in target_names:
                raise ConfigurationError(
                    f"fixed_target must name one configured target; got {self.fixed_target!r}."
                )
            if self.fixed_power_w is None:
                raise ConfigurationError(
                    "fixed_target strategy requires finite, positive fixed_power_w."
                )


@dataclass(frozen=True)
class PlannerConfig:
    power_tolerance_abs_w: float = 2.0
    power_tolerance_rel: float = 0.05
    composition_tolerance_abs: float = 0.02
    max_breakpoints: int = 100
    ramp_rate_resolution_w_per_s: float = 0.001

    def validate(self) -> None:
        if not _nonnegative_number(self.power_tolerance_abs_w) or not _nonnegative_number(
            self.power_tolerance_rel
        ):
            raise ConfigurationError("Planner power tolerances must be finite and non-negative.")
        if not _positive_number(self.composition_tolerance_abs):
            raise ConfigurationError(
                "planner.composition_tolerance_abs must be finite and positive."
            )
        if (
            not isinstance(self.max_breakpoints, int)
            or isinstance(self.max_breakpoints, bool)
            or self.max_breakpoints < 2
        ):
            raise ConfigurationError("planner.max_breakpoints must be at least 2.")
        if not _positive_number(self.ramp_rate_resolution_w_per_s):
            raise ConfigurationError(
                "planner.ramp_rate_resolution_w_per_s must be finite and positive."
            )


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
        if not isinstance(self.name, str) or not self.name.strip():
            raise ConfigurationError("Plan name must be non-empty text.")
        if len(self.targets) < 1:
            raise ConfigurationError("At least one target is required.")
        for target in self.targets:
            target.validate()
        names = self.target_names
        folded_names = [name.casefold() for name in names]
        if len(set(folded_names)) != len(folded_names):
            raise ConfigurationError("Target names must be unique, ignoring capitalization.")
        self.profile.validate()
        unknown = set(self.profile.composition_columns) - set(names)
        if unknown:
            raise ConfigurationError(
                "profile.composition_columns contains unknown targets: "
                + ", ".join(sorted(unknown))
            )
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
    unknown_root = set(root) - {"name", "targets", "profile", "operation", "planner"}
    if unknown_root:
        raise ConfigurationError(
            "Unknown top-level configuration field(s): "
            + ", ".join(sorted(repr(key) for key in unknown_root))
        )

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
