import numpy as np
import pytest

from sputterplan.configuration import OperationConfig, PlanConfig, ProfileConfig, TargetConfig
from sputterplan.errors import PlanningError
from sputterplan.physics import compute_physics
from sputterplan.results import CompositionProfile


def test_max_total_power_closed_form(three_target_case):
    config, profile = three_target_case
    result = compute_physics(config, profile)
    calibration = np.array([0.1, 0.05, 0.08])
    total_rate = 300.0 / (profile.compositions @ (1.0 / calibration))
    expected = profile.compositions * total_rate[:, None] / calibration
    np.testing.assert_allclose(result.ideal_power_w, expected, rtol=1e-13, atol=1e-13)
    np.testing.assert_allclose(result.ideal_power_w.sum(axis=1), 300.0)


def test_target_maximum_scales_all_powers_and_preserves_composition(tmp_path):
    placeholder = tmp_path / "profile.csv"
    placeholder.write_text("distance_nm,A,B\n", encoding="utf-8")
    config = PlanConfig(
        targets=(
            TargetConfig("A", 0.1, max_power_w=50.0),
            TargetConfig("B", 0.05, max_power_w=250.0),
        ),
        profile=ProfileConfig(path=placeholder),
        operation=OperationConfig(
            strategy="max_total_power",
            max_total_power_w=300.0,
            hardware_limit_policy="clip",
        ),
    )
    composition = np.full((2, 2), 0.5)
    profile = CompositionProfile(np.array([0.0, 1.0]), composition, config.target_names)

    result = compute_physics(config, profile)

    np.testing.assert_allclose(result.ideal_power_w, [[100.0, 200.0], [100.0, 200.0]])
    np.testing.assert_allclose(result.feasible_power_w, [[50.0, 100.0], [50.0, 100.0]])
    np.testing.assert_allclose(result.feasible_composition, composition)
    assert np.all(result.feasible_power_w.sum(axis=1) <= 300.0)
    assert any("power ratios were scaled together" in warning for warning in result.warnings)


def test_zero_desired_fraction_remains_off_when_minimum_power_is_configured(tmp_path):
    placeholder = tmp_path / "profile.csv"
    placeholder.write_text("distance_nm,A,B\n", encoding="utf-8")
    config = PlanConfig(
        targets=(
            TargetConfig("A", 0.1, min_stable_power_w=10.0),
            TargetConfig("B", 0.1, min_stable_power_w=10.0),
        ),
        profile=ProfileConfig(path=placeholder),
        operation=OperationConfig(strategy="max_total_power", max_total_power_w=100.0),
    )
    profile = CompositionProfile(
        np.array([0.0, 1.0]), np.array([[1.0, 0.0], [0.0, 1.0]]), config.target_names
    )

    result = compute_physics(config, profile)

    np.testing.assert_allclose(result.feasible_power_w, [[100.0, 0.0], [0.0, 100.0]])
    np.testing.assert_allclose(result.feasible_composition, profile.compositions)


def test_fixed_target_mode(three_target_case):
    config, profile = three_target_case
    config = PlanConfig(
        name=config.name,
        targets=config.targets,
        profile=config.profile,
        operation=OperationConfig(strategy="fixed_target", fixed_target="A", fixed_power_w=120),
        planner=config.planner,
    )
    result = compute_physics(config, profile)
    np.testing.assert_allclose(result.ideal_power_w[:, 0], 120.0)
    np.testing.assert_allclose(result.ideal_composition, profile.compositions)


def test_fixed_target_zero_fraction_fails(three_target_case):
    config, profile = three_target_case
    config = PlanConfig(
        name=config.name,
        targets=config.targets,
        profile=config.profile,
        operation=OperationConfig(strategy="fixed_target", fixed_target="C", fixed_power_w=100),
        planner=config.planner,
    )
    profile.compositions[0, 2] = 0
    profile.compositions[0, 0] += 0.2
    with pytest.raises(PlanningError, match="zero composition"):
        compute_physics(config, profile)


@pytest.mark.parametrize("target_count", [1, 2, 5, 12])
def test_arbitrary_target_count(tmp_path, target_count):
    from sputterplan.configuration import ProfileConfig, TargetConfig
    from sputterplan.results import CompositionProfile

    placeholder = tmp_path / "profile.csv"
    placeholder.write_text("x\n", encoding="utf-8")
    targets = tuple(TargetConfig(f"T{i}", 0.05 + 0.01 * i) for i in range(target_count))
    config = PlanConfig(
        targets=targets,
        profile=ProfileConfig(path=placeholder),
        operation=OperationConfig(strategy="max_total_power", max_total_power_w=200),
    )
    composition = np.full((5, target_count), 1.0 / target_count)
    profile = CompositionProfile(np.arange(5.0), composition, config.target_names)
    result = compute_physics(config, profile)
    assert result.ideal_power_w.shape == (5, target_count)
    np.testing.assert_allclose(result.ideal_power_w.sum(axis=1), 200.0)
