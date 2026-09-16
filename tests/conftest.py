from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from sputterplan.configuration import (
    OperationConfig,
    PlanConfig,
    PlannerConfig,
    ProfileConfig,
    TargetConfig,
)
from sputterplan.results import CompositionProfile


@pytest.fixture
def three_target_case(tmp_path: Path):
    placeholder = tmp_path / "profile.csv"
    placeholder.write_text("distance_nm,A,B,C\n", encoding="utf-8")
    config = PlanConfig(
        name="test",
        targets=(
            TargetConfig("A", 0.1),
            TargetConfig("B", 0.05),
            TargetConfig("C", 0.08),
        ),
        profile=ProfileConfig(path=placeholder),
        operation=OperationConfig(strategy="max_total_power", max_total_power_w=300),
        planner=PlannerConfig(
            power_tolerance_abs_w=0.5,
            power_tolerance_rel=0.02,
            composition_tolerance_abs=0.01,
            max_breakpoints=100,
        ),
    )
    distance = np.linspace(0, 1000, 51)
    s = distance / distance[-1]
    compositions = np.column_stack((0.6 - 0.4 * s, 0.2 + 0.2 * np.sin(np.pi * s), np.zeros_like(s)))
    compositions[:, 2] = 1.0 - compositions[:, 0] - compositions[:, 1]
    profile = CompositionProfile(distance, compositions, config.target_names)
    return config, profile
