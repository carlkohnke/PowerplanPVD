"""Machine-readable and operator-readable output writers."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

from .configuration import PlanConfig
from .plotting import write_plots
from .results import PlanResult


def _clean_name(name: str) -> str:
    return "_".join(name.strip().lower().split())


def _format(value: float, decimals: int) -> str:
    return f"{float(value):.{decimals}f}"


def _write_schedule_csv(result: PlanResult, path: Path) -> None:
    indices = result.schedule.breakpoint_indices
    header = ["step", "profile_point", "time_s", "thickness_nm", "duration_to_next_s"]
    for name in result.target_names:
        slug = _clean_name(name)
        header.extend([f"{slug}_power_w", f"{slug}_ramp_to_next_w_per_s"])
    header.extend(["max_power_error_to_next_w", "max_composition_error_to_next_fraction"])

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for step, index in enumerate(indices):
            has_next = step < len(indices) - 1
            row: list[object] = [
                step + 1,
                int(index) + 1,
                _format(result.physics.time_s[index], 3),
                _format(result.distance_nm[index], 3),
                _format(result.physics.time_s[indices[step + 1]] - result.physics.time_s[index], 3)
                if has_next
                else "",
            ]
            for target_index in range(len(result.target_names)):
                row.extend(
                    [
                        _format(result.schedule.scheduled_power_w[index, target_index], 3),
                        _format(result.schedule.ramp_rate_w_per_s[step, target_index], 6)
                        if has_next
                        else "",
                    ]
                )
            row.extend(
                [
                    _format(result.schedule.segment_power_error_w[step], 6) if has_next else "",
                    _format(result.schedule.segment_composition_error[step], 8) if has_next else "",
                ]
            )
            writer.writerow(row)


def _write_profile_csv(result: PlanResult, path: Path) -> None:
    header = ["profile_index", "distance_nm", "time_s"]
    groups = [
        ("desired_fraction", result.desired_composition),
        ("ideal_power_w", result.physics.ideal_power_w),
        ("feasible_power_w", result.physics.feasible_power_w),
        ("scheduled_power_w", result.schedule.scheduled_power_w),
        ("predicted_fraction", result.schedule.scheduled_composition),
        ("scheduled_rate_nm_per_min", result.schedule.scheduled_rate_nm_per_min),
    ]
    for prefix, _ in groups:
        header.extend([f"{_clean_name(name)}_{prefix}" for name in result.target_names])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row_index in range(result.distance_nm.size):
            row: list[object] = [
                row_index,
                float(result.distance_nm[row_index]),
                float(result.physics.time_s[row_index]),
            ]
            for _, values in groups:
                row.extend(float(value) for value in values[row_index])
            writer.writerow(row)


def write_outputs(
    result: PlanResult,
    config: PlanConfig,
    output_dir: str | Path,
    include_plots: bool = True,
) -> list[Path]:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    schedule_path = output / "operating_plan.csv"
    profile_path = output / "detailed_profile.csv"
    summary_path = output / "summary.json"
    config_path = output / "resolved_config.yaml"

    _write_schedule_csv(result, schedule_path)
    _write_profile_csv(result, profile_path)
    summary_path.write_text(
        json.dumps(result.summary(), indent=2, sort_keys=True), encoding="utf-8"
    )
    config_path.write_text(yaml.safe_dump(config.to_dict(), sort_keys=False), encoding="utf-8")
    paths = [schedule_path, profile_path, summary_path, config_path]
    if include_plots:
        paths.extend(write_plots(result, output / "plots"))
    return paths
