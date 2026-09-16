"""Structured inputs and outputs returned by the public API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CompositionProfile:
    distance_nm: np.ndarray
    compositions: np.ndarray
    target_names: tuple[str, ...]

    @property
    def point_count(self) -> int:
        return int(self.distance_nm.size)

    @property
    def target_count(self) -> int:
        return len(self.target_names)


@dataclass(frozen=True)
class PhysicsResult:
    ideal_power_w: np.ndarray
    feasible_power_w: np.ndarray
    ideal_rate_nm_per_min: np.ndarray
    feasible_rate_nm_per_min: np.ndarray
    ideal_composition: np.ndarray
    feasible_composition: np.ndarray
    time_s: np.ndarray
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ScheduleResult:
    breakpoint_indices: np.ndarray
    scheduled_power_w: np.ndarray
    scheduled_rate_nm_per_min: np.ndarray
    scheduled_composition: np.ndarray
    ramp_rate_w_per_s: np.ndarray
    segment_power_error_w: np.ndarray
    segment_composition_error: np.ndarray
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class PlanResult:
    name: str
    target_names: tuple[str, ...]
    distance_nm: np.ndarray
    desired_composition: np.ndarray
    physics: PhysicsResult
    schedule: ScheduleResult
    calculation_mode: str
    operation_strategy: str
    target_rates_nm_per_min_per_watt: np.ndarray

    def summary(self) -> dict[str, Any]:
        composition_error = np.abs(self.schedule.scheduled_composition - self.desired_composition)
        power_error = np.abs(self.schedule.scheduled_power_w - self.physics.feasible_power_w)
        total_power = np.sum(self.schedule.scheduled_power_w, axis=1)
        max_ramps = (
            np.max(np.abs(self.schedule.ramp_rate_w_per_s), axis=0)
            if self.schedule.ramp_rate_w_per_s.size
            else np.zeros(len(self.target_names))
        )
        warnings = list(dict.fromkeys((*self.physics.warnings, *self.schedule.warnings)))
        return {
            "name": self.name,
            "calculation_mode": self.calculation_mode,
            "operation_strategy": self.operation_strategy,
            "target_names": list(self.target_names),
            "point_count": int(self.distance_nm.size),
            "breakpoint_count": int(self.schedule.breakpoint_indices.size),
            "total_thickness_nm": float(self.distance_nm[-1] - self.distance_nm[0]),
            "total_time_s": float(self.physics.time_s[-1]),
            "total_time_min": float(self.physics.time_s[-1] / 60.0),
            "total_power_w": {
                "minimum": float(np.min(total_power)),
                "maximum": float(np.max(total_power)),
                "mean": float(np.mean(total_power)),
            },
            "maximum_power_error_w": {
                name: float(value)
                for name, value in zip(self.target_names, np.max(power_error, axis=0))
            },
            "maximum_composition_error_fraction": {
                name: float(value)
                for name, value in zip(self.target_names, np.max(composition_error, axis=0))
            },
            "maximum_absolute_ramp_rate_w_per_s": {
                name: float(value) for name, value in zip(self.target_names, max_ramps)
            },
            "warnings": warnings,
        }
