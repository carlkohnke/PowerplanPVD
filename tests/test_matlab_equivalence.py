import json
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
from sputterplan.io import load_profile
from sputterplan.physics import compute_physics

REFERENCE = Path(__file__).parent / "reference_data"


@pytest.mark.skipif(
    not (REFERENCE / "matlab_baseline.npz").exists(), reason="reference data not built"
)
def test_legacy_physics_matches_matlab():
    metadata = json.loads((REFERENCE / "baseline_metadata.json").read_text(encoding="utf-8"))
    baseline = np.load(REFERENCE / "matlab_baseline.npz")
    config = PlanConfig(
        name="MATLAB regression",
        targets=(
            TargetConfig("Ni", 0.1003, 2.0, 1.0),
            TargetConfig("Ti", 0.0533, 2.0, 1.0),
            TargetConfig("Nb", 0.0710, 2.0, 1.0),
        ),
        profile=ProfileConfig(
            path=REFERENCE / "matlab_profile.csv",
            distance_column="distance_nm",
            composition_sum_tolerance=2e-6,
        ),
        operation=OperationConfig(
            strategy="total_power",
            total_power_w=300.0,
            calculation_mode="legacy_compatible",
            legacy_slack_target="Ti",
        ),
        planner=PlannerConfig(composition_tolerance_abs=0.03),
    )
    profile = load_profile(config)
    result = compute_physics(config, profile)
    np.testing.assert_allclose(
        result.ideal_rate_nm_per_min, baseline["k_solved"], rtol=2e-13, atol=2e-13
    )
    np.testing.assert_allclose(result.feasible_power_w, baseline["power"], rtol=2e-13, atol=2e-13)
    np.testing.assert_allclose(result.time_s, baseline["t"], rtol=2e-13, atol=2e-10)
    assert (
        metadata["source_sha256"].upper()
        == "016814302EDA16B63DB435B1E3BED2CF46E72C397BE3175DE8A6088E00EDBED0"
    )
