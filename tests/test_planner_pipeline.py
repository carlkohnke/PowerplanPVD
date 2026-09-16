import json
from pathlib import Path

import numpy as np

from sputterplan.configuration import (
    OperationConfig,
    PlanConfig,
    PlannerConfig,
    ProfileConfig,
    TargetConfig,
    load_config,
)
from sputterplan.errors import PlanningError
from sputterplan.outputs import write_outputs
from sputterplan.pipeline import create_plan
from sputterplan.results import CompositionProfile


def test_planner_respects_tolerances(three_target_case):
    config, profile = three_target_case
    result = create_plan(config, profile)
    power_error = np.abs(result.schedule.scheduled_power_w - result.physics.feasible_power_w)
    allowed_power = (
        config.planner.power_tolerance_abs_w
        + config.planner.power_tolerance_rel
        * np.maximum(np.abs(result.physics.feasible_power_w), 1.0)
    )
    assert np.all(power_error <= allowed_power + 1e-9)
    composition_error = np.abs(result.schedule.scheduled_composition - profile.compositions)
    assert np.max(composition_error) <= config.planner.composition_tolerance_abs + 1e-9
    assert result.schedule.breakpoint_indices[0] == 0
    assert result.schedule.breakpoint_indices[-1] == profile.point_count - 1


def test_example_writes_complete_outputs(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "examples" / "three_target_plan.yaml")
    result = create_plan(config)
    paths = write_outputs(result, config, tmp_path)
    names = {path.name for path in paths}
    assert {
        "operating_plan.csv",
        "detailed_profile.csv",
        "summary.json",
        "resolved_config.yaml",
    } <= names
    assert {"power_vs_time.png", "composition_vs_thickness.png", "composition_error.png"} <= names
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["breakpoint_count"] >= 2
    assert summary["point_count"] == 11


def test_hardware_infeasibility_is_reported(tmp_path: Path):
    placeholder = tmp_path / "profile.csv"
    placeholder.write_text("distance_nm,A,B\n", encoding="utf-8")
    config = PlanConfig(
        targets=(
            TargetConfig("A", 0.1, min_stable_power_w=10.0, off_below_power_w=10.0),
            TargetConfig("B", 0.1, min_stable_power_w=10.0, off_below_power_w=10.0),
        ),
        profile=ProfileConfig(path=placeholder),
        operation=OperationConfig(
            strategy="total_power", total_power_w=100, hardware_limit_policy="clip"
        ),
        planner=PlannerConfig(composition_tolerance_abs=0.005),
    )
    profile = CompositionProfile(
        np.array([0.0, 1.0, 2.0]),
        np.array([[0.98, 0.02], [0.5, 0.5], [0.02, 0.98]]),
        config.target_names,
    )
    result = create_plan(config, profile)
    assert any("Hardware limits alone" in warning for warning in result.schedule.warnings)


def test_breakpoint_limit_fails_loudly(three_target_case):
    config, profile = three_target_case
    limited = PlanConfig(
        name=config.name,
        targets=config.targets,
        profile=config.profile,
        operation=config.operation,
        planner=PlannerConfig(
            power_tolerance_abs_w=0,
            power_tolerance_rel=0,
            composition_tolerance_abs=1e-12,
            max_breakpoints=2,
        ),
    )
    with np.testing.assert_raises(PlanningError):
        create_plan(limited, profile)
