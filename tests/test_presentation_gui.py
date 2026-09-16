import tkinter as tk
from pathlib import Path

import pytest

from sputterplan import gui
from sputterplan.errors import ConfigurationError
from sputterplan.presentation import format_duration, format_summary_text


def test_duration_formatting():
    assert format_duration(12.34) == "12.3 s"
    assert format_duration(90) == "1.5 min"
    assert format_duration(3690) == "1 h 1.5 min"


def test_summary_text_is_operator_readable():
    summary = {
        "name": "Test plan",
        "target_names": ["Ni", "Ti"],
        "point_count": 21,
        "breakpoint_count": 4,
        "total_thickness_nm": 500.0,
        "total_time_s": 90.0,
        "operation_strategy": "total_power",
        "maximum_composition_error_fraction": {"Ni": 0.001, "Ti": 0.002},
        "maximum_absolute_ramp_rate_w_per_s": {"Ni": 0.5, "Ti": 0.25},
        "warnings": ["Review one limit."],
    }
    text = format_summary_text(summary)
    assert "Estimated deposition time: 1.5 min" in text
    assert "Ni: 0.100 at.%" in text
    assert "Warnings (1)" in text
    assert "Review one limit." in text


def test_summary_text_without_warnings():
    summary = {
        "name": "One",
        "target_names": ["A"],
        "point_count": 2,
        "breakpoint_count": 2,
        "total_thickness_nm": 1.0,
        "total_time_s": 1.0,
        "operation_strategy": "total_power",
        "maximum_composition_error_fraction": {"A": 0.0},
        "maximum_absolute_ramp_rate_w_per_s": {"A": 0.0},
        "warnings": [],
    }
    assert "Warnings: none" in format_summary_text(summary)


def test_suggested_output_path(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert gui.suggested_output_path("") == str(tmp_path / "results")
    config = tmp_path / "inputs" / "plan.yaml"
    assert gui.suggested_output_path(str(config)) == str(tmp_path / "inputs" / "results" / "plan")


def test_open_local_path_uses_platform_handler(tmp_path: Path, monkeypatch):
    opened = []
    if gui.os.name == "nt":
        monkeypatch.setattr(gui.os, "startfile", lambda path: opened.append(path))
    else:
        monkeypatch.setattr(gui.webbrowser, "open", lambda uri: opened.append(uri))
    gui.open_local_path(tmp_path)
    assert opened


def test_desktop_window_builds_and_exposes_primary_actions():
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is unavailable: {exc}")
    try:
        root.withdraw()
        window = gui.PlannerWindow(root)
        root.update_idletasks()
        assert window.validate_button.cget("text") == "Validate"
        assert window.create_button.cget("text") == "Create plan"
        assert window.report_button.instate(["disabled"])
        assert window.output_path.get().endswith("results")
    finally:
        root.destroy()


class _ImmediateParent:
    def after(self, _delay, callback):
        callback()


class _FakeResult:
    def summary(self):
        return {"name": "done"}


def test_gui_worker_handles_success_and_expected_error(tmp_path: Path, monkeypatch):
    window = object.__new__(gui.PlannerWindow)
    window.parent = _ImmediateParent()
    successes = []
    errors = []
    window._finish_success = lambda *args: successes.append(args)
    window._finish_error = lambda message: errors.append(message)

    monkeypatch.setattr(gui, "load_config", lambda _path: "config")
    monkeypatch.setattr(gui, "create_plan", lambda _config: _FakeResult())
    monkeypatch.setattr(gui, "write_outputs", lambda *_args, **_kwargs: [tmp_path / "report.html"])
    window._worker("plan", "config.yaml", str(tmp_path), True, False)
    assert successes == [("plan", {"name": "done"}, [tmp_path / "report.html"])]

    monkeypatch.setattr(
        gui,
        "load_config",
        lambda _path: (_ for _ in ()).throw(ConfigurationError("bad configuration")),
    )
    window._worker("validate", "bad.yaml", "", False, False)
    assert errors == ["bad configuration"]
