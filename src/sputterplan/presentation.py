"""Human-readable summaries shared by the CLI, GUI, and reports."""

from __future__ import annotations

from typing import Any


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes = seconds / 60.0
    if minutes < 60:
        return f"{minutes:.1f} min"
    hours = int(minutes // 60)
    remaining = minutes - 60 * hours
    return f"{hours} h {remaining:.1f} min"


def format_summary_text(summary: dict[str, Any]) -> str:
    lines = [
        str(summary["name"]),
        "=" * len(str(summary["name"])),
        f"Targets: {', '.join(summary['target_names'])}",
        f"Profile points: {summary['point_count']}",
        f"Operator steps: {summary['breakpoint_count']}",
        f"Thickness: {summary['total_thickness_nm']:.3f} nm",
        f"Estimated deposition time: {format_duration(summary['total_time_s'])}",
        f"Operating strategy: {summary['operation_strategy']}",
        "",
        "Maximum composition error",
    ]
    for name, value in summary["maximum_composition_error_fraction"].items():
        lines.append(f"  {name}: {100.0 * value:.3f} at.%")
    lines.extend(["", "Maximum ramp rate"])
    for name, value in summary["maximum_absolute_ramp_rate_w_per_s"].items():
        lines.append(f"  {name}: {value:.6g} W/s")
    warnings = summary.get("warnings", [])
    if warnings:
        lines.extend(["", f"Warnings ({len(warnings)})"])
        lines.extend(f"  - {warning}" for warning in warnings)
    else:
        lines.extend(["", "Warnings: none"])
    return "\n".join(lines)
