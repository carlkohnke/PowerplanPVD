from pathlib import Path

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st

from sputterplan.configuration import (
    OperationConfig,
    PlanConfig,
    PlannerConfig,
    ProfileConfig,
    TargetConfig,
)
from sputterplan.pipeline import create_plan
from sputterplan.results import CompositionProfile


@settings(max_examples=35, deadline=None)
@given(
    target_count=st.integers(min_value=1, max_value=10),
    point_count=st.integers(min_value=2, max_value=35),
    total_power=st.floats(min_value=10, max_value=1000, allow_nan=False, allow_infinity=False),
    phase=st.floats(min_value=0, max_value=6.28, allow_nan=False, allow_infinity=False),
)
def test_random_smooth_profiles_preserve_core_invariants(
    target_count: int, point_count: int, total_power: float, phase: float
):
    placeholder = Path(__file__)
    targets = tuple(
        TargetConfig(f"T{index}", 0.02 + 0.013 * (index + 1)) for index in range(target_count)
    )
    config = PlanConfig(
        targets=targets,
        profile=ProfileConfig(path=placeholder),
        operation=OperationConfig(strategy="total_power", total_power_w=total_power),
        planner=PlannerConfig(
            power_tolerance_abs_w=0.5,
            power_tolerance_rel=0.02,
            composition_tolerance_abs=0.01,
            max_breakpoints=point_count,
        ),
    )
    distance = np.linspace(0, 1000, point_count)
    x = np.linspace(0, 1, point_count)
    raw = np.column_stack(
        [
            0.1 + (index + 1) / target_count + 0.08 * np.sin((index + 1) * np.pi * x + phase)
            for index in range(target_count)
        ]
    )
    composition = raw / raw.sum(axis=1, keepdims=True)
    profile = CompositionProfile(distance, composition, config.target_names)
    result = create_plan(config, profile)

    assert result.schedule.scheduled_power_w.shape == (point_count, target_count)
    assert np.all(np.isfinite(result.schedule.scheduled_power_w))
    assert np.all(np.diff(result.physics.time_s) > 0)
    np.testing.assert_allclose(result.physics.feasible_power_w.sum(axis=1), total_power, rtol=1e-10)
    np.testing.assert_allclose(result.schedule.scheduled_composition.sum(axis=1), 1.0, atol=1e-12)
    assert result.schedule.breakpoint_indices[0] == 0
    assert result.schedule.breakpoint_indices[-1] == point_count - 1
