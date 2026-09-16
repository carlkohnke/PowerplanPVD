"""Run a deterministic large-profile smoke and timing check."""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from sputterplan.configuration import (
    OperationConfig,
    PlanConfig,
    PlannerConfig,
    ProfileConfig,
    TargetConfig,
)
from sputterplan.pipeline import create_plan
from sputterplan.results import CompositionProfile


def main() -> None:
    for target_count in (1, 2, 5, 12, 25):
        targets = tuple(
            TargetConfig(f"T{index + 1}", 0.03 + 0.002 * index) for index in range(target_count)
        )
        config = PlanConfig(
            name=f"{target_count}-target stress",
            targets=targets,
            profile=ProfileConfig(path=Path(__file__)),
            operation=OperationConfig(strategy="max_total_power", max_total_power_w=500.0),
            planner=PlannerConfig(
                power_tolerance_abs_w=0.5,
                power_tolerance_rel=0.02,
                composition_tolerance_abs=0.01,
                max_breakpoints=1000,
            ),
        )
        x = np.linspace(0, 1, 1000)
        raw = np.column_stack(
            [
                0.2 + (index + 1) / target_count + 0.1 * np.sin((index + 1) * np.pi * x + index / 3)
                for index in range(target_count)
            ]
        )
        composition = raw / raw.sum(axis=1, keepdims=True)
        profile = CompositionProfile(x * 5000, composition, config.target_names)
        start = time.perf_counter()
        result = create_plan(config, profile)
        elapsed = time.perf_counter() - start

        assert result.schedule.scheduled_power_w.shape == (1000, target_count)
        assert np.all(np.diff(result.physics.time_s) > 0)
        assert np.all(np.isfinite(result.schedule.scheduled_power_w))
        np.testing.assert_allclose(result.physics.feasible_power_w.sum(axis=1), 500.0, rtol=1e-10)
        print(
            f"{target_count:2d} targets | 1000 points | "
            f"{result.schedule.breakpoint_indices.size:3d} steps | {elapsed:.3f} s"
        )


if __name__ == "__main__":
    main()
