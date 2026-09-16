"""Shared-breakpoint piecewise-linear operating-plan construction."""

from __future__ import annotations

from itertools import pairwise

import numpy as np

from .configuration import PlanConfig
from .errors import PlanningError
from .results import CompositionProfile, PhysicsResult, ScheduleResult


def _composition(power: np.ndarray, calibration: np.ndarray) -> np.ndarray:
    rates = power * calibration[None, :]
    totals = np.sum(rates, axis=1)
    if np.any(totals <= 0):
        return np.full_like(rates, np.nan)
    return rates / totals[:, None]


def _segment_prediction(time_s: np.ndarray, power: np.ndarray, start: int, stop: int) -> np.ndarray:
    if stop <= start:
        raise ValueError("Segment stop must be greater than start.")
    fraction = (time_s[start : stop + 1] - time_s[start]) / (time_s[stop] - time_s[start])
    return power[start] + fraction[:, None] * (power[stop] - power[start])


def _segment_score(
    config: PlanConfig,
    profile: CompositionProfile,
    physics: PhysicsResult,
    calibration: np.ndarray,
    start: int,
    stop: int,
) -> tuple[float, int, float, float]:
    if stop - start <= 1:
        return 0.0, start, 0.0, 0.0
    predicted_power = _segment_prediction(physics.time_s, physics.feasible_power_w, start, stop)
    desired_power = physics.feasible_power_w[start : stop + 1]
    power_error = np.abs(predicted_power - desired_power)
    power_scale = config.planner.power_tolerance_abs_w + (
        config.planner.power_tolerance_rel * np.maximum(np.abs(desired_power), 1.0)
    )
    power_score_by_row = np.max(power_error / np.maximum(power_scale, 1e-12), axis=1)

    predicted_composition = _composition(predicted_power, calibration)
    desired_composition = physics.feasible_composition[start : stop + 1]
    composition_error = np.abs(predicted_composition - desired_composition)
    composition_score_by_row = np.max(
        composition_error / config.planner.composition_tolerance_abs, axis=1
    )
    row_score = np.maximum(power_score_by_row, composition_score_by_row)
    row_score[[0, -1]] = 0.0
    local_index = int(np.nanargmax(row_score))
    split = start + local_index
    return (
        float(row_score[local_index]),
        split,
        float(np.max(power_error)),
        float(np.nanmax(composition_error)),
    )


def _find_breakpoints(
    config: PlanConfig,
    profile: CompositionProfile,
    physics: PhysicsResult,
    calibration: np.ndarray,
) -> list[int]:
    count = profile.point_count
    breakpoints = {0, count - 1}
    pending = [(0, count - 1)]
    while pending:
        start, stop = pending.pop()
        score, split, _, _ = _segment_score(config, profile, physics, calibration, start, stop)
        if score <= 1.0 + 1e-12 or stop - start <= 1:
            continue
        if split <= start or split >= stop:
            split = start + (stop - start) // 2
        breakpoints.add(split)
        if len(breakpoints) > config.planner.max_breakpoints:
            raise PlanningError(
                "The requested tolerances require more than "
                f"planner.max_breakpoints={config.planner.max_breakpoints}. "
                "Increase the limit or relax a tolerance."
            )
        pending.append((start, split))
        pending.append((split, stop))

    points = sorted(breakpoints)
    changed = True
    while changed and len(points) > 2:
        changed = False
        for position in range(1, len(points) - 1):
            start, stop = points[position - 1], points[position + 1]
            score, _, _, _ = _segment_score(config, profile, physics, calibration, start, stop)
            if score <= 1.0 + 1e-12:
                points.pop(position)
                changed = True
                break
    return points


def create_schedule(
    config: PlanConfig, profile: CompositionProfile, physics: PhysicsResult
) -> ScheduleResult:
    calibration = np.asarray(
        [target.rate_nm_per_min_per_watt for target in config.targets], dtype=float
    )
    breakpoints = _find_breakpoints(config, profile, physics, calibration)
    scheduled_power = np.empty_like(physics.feasible_power_w)
    segment_power_error: list[float] = []
    segment_composition_error: list[float] = []
    for start, stop in pairwise(breakpoints):
        prediction = _segment_prediction(physics.time_s, physics.feasible_power_w, start, stop)
        scheduled_power[start : stop + 1] = prediction
        scheduled_composition_segment = _composition(prediction, calibration)
        segment_power_error.append(
            float(np.max(np.abs(prediction - physics.feasible_power_w[start : stop + 1])))
        )
        segment_composition_error.append(
            float(
                np.max(
                    np.abs(
                        scheduled_composition_segment
                        - physics.feasible_composition[start : stop + 1]
                    )
                )
            )
        )
    scheduled_rates = scheduled_power * calibration[None, :]
    scheduled_composition = _composition(scheduled_power, calibration)

    bp = np.asarray(breakpoints, dtype=int)
    duration = np.diff(physics.time_s[bp])
    ramp = np.diff(scheduled_power[bp], axis=0) / duration[:, None]
    resolution = config.planner.ramp_rate_resolution_w_per_s
    rounded_ramp = np.round(ramp / resolution) * resolution

    warnings: list[str] = []
    unavoidable_error = np.abs(physics.feasible_composition - profile.compositions)
    maximum_unavoidable = float(np.max(unavoidable_error))
    if maximum_unavoidable > config.planner.composition_tolerance_abs + 1e-12:
        message = (
            "Hardware limits alone cause a maximum composition error of "
            f"{maximum_unavoidable:.6g}, above planner.composition_tolerance_abs="
            f"{config.planner.composition_tolerance_abs:.6g}."
        )
        if config.operation.hardware_limit_policy == "error":
            raise PlanningError(message)
        warnings.append(message + " The plan is the bounded feasible approximation.")
    for index, target in enumerate(config.targets):
        if target.max_ramp_rate_w_per_s is None:
            continue
        violations = np.abs(rounded_ramp[:, index]) > target.max_ramp_rate_w_per_s + 1e-12
        if np.any(violations):
            warnings.append(
                f"Target {target.name} exceeds max_ramp_rate_w_per_s in "
                f"{int(np.count_nonzero(violations))} segment(s). The schedule is flagged, not "
                "silently time-stretched, because stretching changes deposited thickness."
            )

    return ScheduleResult(
        breakpoint_indices=bp,
        scheduled_power_w=scheduled_power,
        scheduled_rate_nm_per_min=scheduled_rates,
        scheduled_composition=scheduled_composition,
        ramp_rate_w_per_s=rounded_ramp,
        segment_power_error_w=np.asarray(segment_power_error),
        segment_composition_error=np.asarray(segment_composition_error),
        warnings=tuple(warnings),
    )
