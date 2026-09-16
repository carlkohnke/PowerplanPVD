from pathlib import Path

import numpy as np
import pytest
from openpyxl import Workbook

from sputterplan.configuration import load_config, plan_config_from_dict
from sputterplan.errors import ConfigurationError, ProfileError
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


def test_tsv_profile_and_one_based_column_numbers(tmp_path: Path):
    profile_path = tmp_path / "profile.tsv"
    profile_path.write_text("x\tA\tB\n0\t0.2\t0.8\n1\t0.4\t0.6\n", encoding="utf-8")
    config = plan_config_from_dict(
        {
            "profile": {
                "path": str(profile_path),
                "distance_column": 1,
                "composition_columns": {"A": 2, "B": 3},
            },
            "targets": [
                {"name": "A", "rate_nm_per_min_per_watt": 0.1},
                {"name": "B", "rate_nm_per_min_per_watt": 0.2},
            ],
            "operation": {"strategy": "total_power", "total_power_w": 100},
        }
    )
    profile = load_profile(config)
    np.testing.assert_allclose(profile.distance_nm, [0, 1])
    np.testing.assert_allclose(profile.compositions, [[0.2, 0.8], [0.4, 0.6]])


def _write_workbook(path: Path, *, multiple_sheets: bool = False) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Gradient"
    sheet.append(["notes", None, None])
    sheet.append(["distance_nm", "Ni", "Ti"])
    sheet.append([0, 0.25, 0.75])
    sheet.append([100, 0.5, 0.5])
    if multiple_sheets:
        workbook.create_sheet("Notes").append(["text"])
    workbook.save(path)


def test_excel_profile_uses_element_headers_before_column_letters(tmp_path: Path):
    workbook_path = tmp_path / "profile.xlsx"
    _write_workbook(workbook_path)
    config = plan_config_from_dict(
        {
            "profile": {
                "path": str(workbook_path),
                "sheet": "Gradient",
                "header_row": 2,
                "distance_column": "distance_nm",
            },
            "targets": [
                {"name": "Ni", "rate_nm_per_min_per_watt": 0.1},
                {"name": "Ti", "rate_nm_per_min_per_watt": 0.2},
            ],
            "operation": {"strategy": "total_power", "total_power_w": 100},
        }
    )
    profile = load_profile(config)
    assert profile.target_names == ("Ni", "Ti")
    np.testing.assert_allclose(profile.compositions, [[0.25, 0.75], [0.5, 0.5]])


def test_excel_profile_supports_letters_and_requires_sheet_selection(tmp_path: Path):
    workbook_path = tmp_path / "profile.xlsx"
    _write_workbook(workbook_path, multiple_sheets=True)
    base = {
        "path": str(workbook_path),
        "header_row": 2,
        "distance_column": "A",
        "composition_columns": {"Ni": "B", "Ti": "C"},
    }
    root = {
        "profile": base,
        "targets": [
            {"name": "Ni", "rate_nm_per_min_per_watt": 0.1},
            {"name": "Ti", "rate_nm_per_min_per_watt": 0.2},
        ],
        "operation": {"strategy": "total_power", "total_power_w": 100},
    }
    with pytest.raises(ProfileError, match="profile.sheet is required"):
        load_profile(plan_config_from_dict(root))
    root["profile"] = {**base, "sheet": "Gradient"}
    np.testing.assert_allclose(load_profile(plan_config_from_dict(root)).distance_nm, [0, 100])


@pytest.mark.parametrize(
    "mutator, message",
    [
        (
            lambda data: data["targets"].append({"name": "a", "rate_nm_per_min_per_watt": 1}),
            "unique",
        ),
        (
            lambda data: data["profile"].update({"data_start_row": 4, "data_end_row": 3}),
            "data_end_row",
        ),
        (lambda data: data["targets"][0].update({"surprise": 1}), "Invalid target settings"),
        (lambda data: data["profile"].update({"surprise": 1}), "Invalid configuration field"),
    ],
)
def test_configuration_errors_are_actionable(tmp_path: Path, mutator, message):
    profile = tmp_path / "profile.csv"
    profile.write_text("distance_nm,A\n0,1\n1,1\n", encoding="utf-8")
    data = {
        "profile": {"path": str(profile)},
        "targets": [{"name": "A", "rate_nm_per_min_per_watt": 1}],
        "operation": {"strategy": "total_power", "total_power_w": 100},
    }
    mutator(data)
    with pytest.raises(ConfigurationError, match=message):
        plan_config_from_dict(data)


def test_unresolved_environment_variable_is_reported(monkeypatch):
    monkeypatch.delenv("SPUTTERPLAN_MISSING_FOR_TEST", raising=False)
    data = {
        "profile": {"path": "$SPUTTERPLAN_MISSING_FOR_TEST/profile.csv"},
        "targets": [{"name": "A", "rate_nm_per_min_per_watt": 1}],
        "operation": {"strategy": "total_power", "total_power_w": 100},
    }
    with pytest.raises(ConfigurationError, match="unresolved environment variable"):
        plan_config_from_dict(data)


def test_literal_percent_and_dollar_characters_are_allowed_in_paths(tmp_path: Path):
    profile = tmp_path / "price$-100%.csv"
    profile.write_text("distance_nm,A\n0,1\n1,1\n", encoding="utf-8")
    config = plan_config_from_dict(
        {
            "profile": {"path": str(profile)},
            "targets": [{"name": "A", "rate_nm_per_min_per_watt": 1}],
            "operation": {"strategy": "total_power", "total_power_w": 100},
        }
    )
    assert config.profile.path == profile


def test_wrong_configuration_value_type_is_actionable(tmp_path: Path):
    profile = tmp_path / "profile.csv"
    profile.write_text("distance_nm,A\n0,1\n1,1\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="wrong type"):
        plan_config_from_dict(
            {
                "profile": {"path": str(profile)},
                "targets": [{"name": "A", "rate_nm_per_min_per_watt": "fast"}],
                "operation": {"strategy": "total_power", "total_power_w": 100},
            }
        )


def test_profile_rejects_duplicate_header_and_nonincreasing_distance(tmp_path: Path):
    duplicate = tmp_path / "duplicate.csv"
    duplicate.write_text("distance_nm,A,A\n0,0.5,0.5\n1,0.5,0.5\n", encoding="utf-8")
    config = plan_config_from_dict(
        {
            "profile": {"path": str(duplicate)},
            "targets": [{"name": "A", "rate_nm_per_min_per_watt": 1}],
            "operation": {"strategy": "total_power", "total_power_w": 100},
        }
    )
    with pytest.raises(ProfileError, match="duplicated"):
        load_profile(config)

    decreasing = tmp_path / "decreasing.csv"
    decreasing.write_text("distance_nm,A\n1,1\n0,1\n", encoding="utf-8")
    config = plan_config_from_dict(
        {
            "profile": {"path": str(decreasing)},
            "targets": [{"name": "A", "rate_nm_per_min_per_watt": 1}],
            "operation": {"strategy": "total_power", "total_power_w": 100},
        }
    )
    with pytest.raises(ProfileError, match="increase strictly"):
        load_profile(config)
