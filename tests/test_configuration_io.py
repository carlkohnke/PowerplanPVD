from pathlib import Path

import numpy as np
import pytest

from sputterplan.configuration import load_config
from sputterplan.errors import ProfileError
from sputterplan.io import load_profile


def test_example_configuration_and_csv_load():
    root = Path(__file__).resolve().parents[1]
    config = load_config(root / "examples" / "three_target_plan.yaml")
    profile = load_profile(config)
    assert profile.target_names == ("Alpha", "Beta", "Gamma")
    assert profile.compositions.shape == (11, 3)
    np.testing.assert_allclose(profile.compositions.sum(axis=1), 1.0)


def test_invalid_composition_sum_is_actionable(tmp_path: Path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text("distance_nm,A\n0,0.5\n1,0.5\n", encoding="utf-8")
    config_path = tmp_path / "bad.yaml"
    config_path.write_text(
        """
profile:
  path: bad.csv
targets:
  - name: A
    rate_nm_per_min_per_watt: 0.1
operation:
  strategy: total_power
  total_power_w: 100
""",
        encoding="utf-8",
    )
    with pytest.raises(ProfileError, match="not 1"):
        load_profile(load_config(config_path))


def test_explicit_normalization(tmp_path: Path):
    csv_path = tmp_path / "percent_like.csv"
    csv_path.write_text("distance_nm,A,B\n0,3,1\n1,1,3\n", encoding="utf-8")
    config_path = tmp_path / "normalize.yaml"
    config_path.write_text(
        """
profile:
  path: percent_like.csv
  normalize_compositions: true
targets:
  - {name: A, rate_nm_per_min_per_watt: 0.1}
  - {name: B, rate_nm_per_min_per_watt: 0.2}
operation: {strategy: total_power, total_power_w: 100}
""",
        encoding="utf-8",
    )
    profile = load_profile(load_config(config_path))
    np.testing.assert_allclose(profile.compositions, [[0.75, 0.25], [0.25, 0.75]])


def test_percent_compositions(tmp_path: Path):
    csv_path = tmp_path / "percent.csv"
    csv_path.write_text("distance_nm,A,B\n0,25,75\n1,50,50\n", encoding="utf-8")
    config_path = tmp_path / "percent.yaml"
    config_path.write_text(
        """
profile:
  path: percent.csv
  composition_basis: percent
targets:
  - {name: A, rate_nm_per_min_per_watt: 0.1}
  - {name: B, rate_nm_per_min_per_watt: 0.2}
operation: {strategy: total_power, total_power_w: 100}
""",
        encoding="utf-8",
    )
    profile = load_profile(load_config(config_path))
    np.testing.assert_allclose(profile.compositions, [[0.25, 0.75], [0.5, 0.5]])
