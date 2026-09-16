import json
from pathlib import Path

import yaml

from sputterplan.cli import main


def test_cli_validate_and_plan(tmp_path: Path, capsys):
    root = Path(__file__).resolve().parents[1]
    config = root / "examples" / "Example Simple 3 Component" / "simple_three_target_plan.yaml"
    assert main(["validate", str(config)]) == 0
    validation = capsys.readouterr().out
    assert "Configuration and profile are valid" in validation
    assert "Profile points: 11" in validation
    assert "Targets: Alpha, Beta, Gamma" in validation

    output = tmp_path / "run"
    assert main(["plan", str(config), "--output", str(output), "--no-plots"]) == 0
    assert (output / "operating_plan.csv").exists()
    assert (output / "summary.json").exists()
    assert (output / "run_summary.txt").exists()
    assert (output / "report.html").exists()

    assert main(["plan", str(config), "--output", str(output), "--no-plots"]) == 2
    assert "enable overwrite" in capsys.readouterr().err
    assert main(["plan", str(config), "--output", str(output), "--no-plots", "--force"]) == 0


def test_cli_inspect_and_init_workflow(tmp_path: Path, capsys):
    profile = tmp_path / "gradient.csv"
    profile.write_text("distance_nm,Ni,Ti\n0,0.25,0.75\n100,0.50,0.50\n", encoding="utf-8")
    assert main(["inspect-profile", str(profile), "--preview", "1"]) == 0
    inspection = capsys.readouterr().out
    assert "1: distance_nm" in inspection
    assert "2: Ni" in inspection
    assert "0, 0.25, 0.75" in inspection

    config = tmp_path / "plan.yaml"
    assert (
        main(
            [
                "init",
                str(profile),
                "--output",
                str(config),
                "--target",
                "Ni=0.1",
                "--target",
                "Ti=0.05",
                "--max-total-power",
                "250",
            ]
        )
        == 0
    )
    created = yaml.safe_load(config.read_text(encoding="utf-8"))
    assert [item["name"] for item in created["targets"]] == ["Ni", "Ti"]
    assert created["operation"]["max_total_power_w"] == 250
    assert "Next: sputterplan validate" in capsys.readouterr().out


def test_cli_init_rejects_unknown_target_column(tmp_path: Path, capsys):
    profile = tmp_path / "gradient.csv"
    profile.write_text("distance_nm,Ni\n0,1\n1,1\n", encoding="utf-8")
    assert (
        main(
            [
                "init",
                str(profile),
                "--output",
                str(tmp_path / "plan.yaml"),
                "--target",
                "Ti=0.1",
            ]
        )
        == 2
    )
    assert "Target columns not found" in capsys.readouterr().err


def test_cli_init_defaults_beside_profile_and_protects_existing_file(tmp_path: Path, capsys):
    profile = tmp_path / "gradient.csv"
    profile.write_text("distance_nm,Ni\n0,1\n1,1\n", encoding="utf-8")
    args = ["init", str(profile), "--target", "Ni=0.1"]
    assert main(args) == 0
    config = profile.with_suffix(".yaml")
    assert config.exists()
    assert main(args) == 2
    assert "already exists" in capsys.readouterr().err
    assert main([*args, "--force"]) == 0


def test_cli_reports_missing_configuration(tmp_path: Path, capsys):
    assert main(["validate", str(tmp_path / "missing.yaml")]) == 2
    assert "Could not read configuration" in capsys.readouterr().err


def test_cli_json_output_is_machine_parseable(tmp_path: Path, capsys):
    root = Path(__file__).resolve().parents[1]
    config = root / "examples" / "Example Simple 3 Component" / "simple_three_target_plan.yaml"
    output = tmp_path / "json-run"

    assert (
        main(
            [
                "plan",
                str(config),
                "--output",
                str(output),
                "--no-plots",
                "--json",
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert summary["name"] == "Three-target demonstration"
    assert "Wrote 6 files" in captured.err
    assert "Report:" in captured.err
