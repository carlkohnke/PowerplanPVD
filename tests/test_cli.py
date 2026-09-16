from pathlib import Path

from sputterplan.cli import main


def test_cli_validate_and_plan(tmp_path: Path, capsys):
    root = Path(__file__).resolve().parents[1]
    config = root / "examples" / "three_target_plan.yaml"
    assert main(["validate", str(config)]) == 0
    assert "Valid: 11 points, 3 targets" in capsys.readouterr().out

    output = tmp_path / "run"
    assert main(["plan", str(config), "--output", str(output), "--no-plots"]) == 0
    assert (output / "operating_plan.csv").exists()
    assert (output / "summary.json").exists()


def test_cli_reports_missing_configuration(tmp_path: Path, capsys):
    assert main(["validate", str(tmp_path / "missing.yaml")]) == 2
    assert "Could not read configuration" in capsys.readouterr().err
