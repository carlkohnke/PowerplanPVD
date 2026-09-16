"""Deposition-rate, power, composition, and time calculations."""

from __future__ import annotations

import numpy as np

from .configuration import PlanConfig
from .errors import PlanningError
from .results import CompositionProfile, PhysicsResult


def _scale_to_target_maxima(desired: np.ndarray, maximum: np.ndarray) -> tuple[np.ndarray, float]:
    """Scale a power vector without changing its deposition composition."""
    powered = desired > 0
    if not np.any(powered):
        return desired.copy(), 1.0
    scale = min(1.0, float(np.min(maximum[powered] / desired[powered])))
    return desired * scale, scale


def _reduce_to_total_maximum(values: np.ndarray, lower: np.ndarray, max_total: float) -> np.ndarray:
    """Reduce powers without crossing active-target minimums; never add power."""
    excess = float(np.sum(values)) - max_total
    if excess <= 1e-10:
        return values
    reducible = np.maximum(values - lower, 0.0)
    available = float(np.sum(reducible))
    if available + 1e-10 < excess:
        raise PlanningError("Active target minimum powers exceed operation.max_total_power_w.")
    return values - reducible * (excess / available)


def _apply_individual_limits(ideal: np.ndarray, config: PlanConfig) -> tuple[np.ndarray, list[str]]:
    feasible = ideal.copy()
    warnings: list[str] = []
    for index, target in enumerate(config.targets):
        values = feasible[:, index]
        if target.off_below_power_w > 0:
            values[values < target.off_below_power_w] = 0.0
        if target.min_stable_power_w > 0:
            mask = (
                (values > 0)
                & (values >= target.off_below_power_w)
                & (values < target.min_stable_power_w)
            )
            values[mask] = target.min_stable_power_w
        if target.max_power_w is not None and np.any(values > target.max_power_w):
            if config.operation.hardware_limit_policy == "error":
                raise PlanningError(f"Ideal power exceeds max_power_w for target {target.name!r}.")
            count = int(np.count_nonzero(values > target.max_power_w))
            values[:] = np.minimum(values, target.max_power_w)
            warnings.append(f"Clipped {count} points to max_power_w for target {target.name}.")
    return feasible, warnings


def _apply_hardware_limits(ideal: np.ndarray, config: PlanConfig) -> tuple[np.ndarray, list[str]]:
    feasible = np.zeros_like(ideal)
    warnings: list[str] = []
    off = np.asarray([target.off_below_power_w for target in config.targets])
    minimum = np.asarray([target.min_stable_power_w for target in config.targets])
    maximum = np.asarray(
        [
            target.max_power_w if target.max_power_w is not None else np.inf
            for target in config.targets
        ]
    )

    if config.operation.strategy == "max_total_power":
        max_total = float(config.operation.max_total_power_w)
        scaled_rows = 0
        for row_index, desired in enumerate(ideal):
            bounded, scale = _scale_to_target_maxima(desired, maximum)
            if scale < 1.0 - 1e-12:
                if config.operation.hardware_limit_policy == "error":
                    target_index = int(np.argmax(desired / maximum))
                    raise PlanningError(
                        f"Ideal power exceeds max_power_w for target "
                        f"{config.targets[target_index].name!r} at profile row {row_index + 1}."
                    )
                scaled_rows += 1

            # A desired zero must remain off even when off_below_power_w is zero.
            active = (bounded > 0) & (bounded >= off)
            lower = np.where(active, minimum, 0.0)
            bounded[~active] = 0.0
            bounded[active & (bounded < minimum)] = minimum[active & (bounded < minimum)]
            feasible[row_index] = _reduce_to_total_maximum(bounded, lower, max_total)
        if scaled_rows:
            warnings.append(
                f"Target maximum powers reduced achievable total power at {scaled_rows} "
                "profile row(s); target power ratios were scaled together to preserve composition."
            )
    else:
        feasible, target_warnings = _apply_individual_limits(ideal, config)
        warnings.extend(target_warnings)
        fixed_index = config.target_names.index(str(config.operation.fixed_target))
        fixed_power = float(config.operation.fixed_power_w)
        fixed_target = config.targets[fixed_index]
        if fixed_target.max_power_w is not None and fixed_power > fixed_target.max_power_w:
            raise PlanningError("fixed_power_w exceeds the fixed target's max_power_w.")
        if 0 < fixed_power < fixed_target.min_stable_power_w:
            raise PlanningError("fixed_power_w is below the fixed target's min_stable_power_w.")
        feasible[:, fixed_index] = fixed_power
    return feasible, warnings


def _compositions_from_rates(rates: np.ndarray) -> np.ndarray:
    totals = np.sum(rates, axis=1)
    if np.any(totals <= 0):
        row = int(np.flatnonzero(totals <= 0)[0])
        raise PlanningError(f"Total deposition rate is zero at profile row {row + 1}.")
    return rates / totals[:, None]


def _time_grid(distance_nm: np.ndarray, total_rate_nm_per_min: np.ndarray) -> np.ndarray:
    if np.any(total_rate_nm_per_min <= 0):
        row = int(np.flatnonzero(total_rate_nm_per_min <= 0)[0])
        raise PlanningError(f"Total deposition rate is not positive at profile row {row + 1}.")
    delta_distance = np.diff(distance_nm)
    inverse_rate = 1.0 / total_rate_nm_per_min
    delta_time_s = delta_distance * 0.5 * (inverse_rate[:-1] + inverse_rate[1:]) * 60.0
    return np.concatenate(([0.0], np.cumsum(delta_time_s)))


def compute_physics(config: PlanConfig, profile: CompositionProfile) -> PhysicsResult:
    calibration = np.asarray(
        [target.rate_nm_per_min_per_watt for target in config.targets], dtype=float
    )
    composition = profile.compositions

    if config.operation.strategy == "max_total_power":
        denominator = composition @ (1.0 / calibration)
        total_rate = float(config.operation.max_total_power_w) / denominator
    else:
        fixed_index = config.target_names.index(str(config.operation.fixed_target))
        fixed_fraction = composition[:, fixed_index]
        if np.any(fixed_fraction <= 0):
            row = int(np.flatnonzero(fixed_fraction <= 0)[0])
            raise PlanningError(
                f"Fixed target {config.operation.fixed_target!r} has zero composition at "
                f"profile row {row + 1}; no finite fixed-target solution exists."
            )
        total_rate = (
            calibration[fixed_index] * float(config.operation.fixed_power_w) / fixed_fraction
        )
    ideal_rates = composition * total_rate[:, None]
    ideal_power = ideal_rates / calibration[None, :]

    feasible_power, warnings = _apply_hardware_limits(ideal_power, config)

    feasible_rates = feasible_power * calibration[None, :]
    feasible_composition = _compositions_from_rates(feasible_rates)
    time_rates = np.sum(feasible_rates, axis=1)
    time_s = _time_grid(profile.distance_nm, time_rates)

    changed = np.abs(feasible_power - ideal_power) > 1e-10
    if np.any(changed):
        warnings.append(
            f"Hardware power limits changed {int(np.count_nonzero(changed))} target-point values; "
            "review composition errors in the detailed profile."
        )

    return PhysicsResult(
        ideal_power_w=ideal_power,
        feasible_power_w=feasible_power,
        ideal_rate_nm_per_min=ideal_rates,
        feasible_rate_nm_per_min=feasible_rates,
        ideal_composition=composition.copy(),
        feasible_composition=feasible_composition,
        time_s=time_s,
        warnings=tuple(dict.fromkeys(warnings)),
    )
