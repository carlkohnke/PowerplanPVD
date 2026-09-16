"""Machine-readable and operator-readable output writers."""

from __future__ import annotations

import csv
import html
import json
import re
from pathlib import Path

import yaml

from .configuration import PlanConfig
from .errors import OutputError
from .plotting import write_plots
from .presentation import format_summary_text
from .results import PlanResult


def _clean_name(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return cleaned or "target"


def _target_slugs(names: tuple[str, ...]) -> list[str]:
    """Create safe, unique CSV column prefixes in configured target order."""
    used: dict[str, int] = {}
    slugs: list[str] = []
    for name in names:
        base = _clean_name(name)
        used[base] = used.get(base, 0) + 1
        slugs.append(base if used[base] == 1 else f"{base}_{used[base]}")
    return slugs


def _format(value: float, decimals: int) -> str:
    return f"{float(value):.{decimals}f}"


def _write_schedule_csv(result: PlanResult, path: Path) -> None:
    indices = result.schedule.breakpoint_indices
    header = ["step", "profile_point", "time_s", "thickness_nm", "duration_to_next_s"]
    for slug in _target_slugs(result.target_names):
        header.extend([f"{slug}_power_w", f"{slug}_ramp_to_next_w_per_s"])
    header.extend(["max_power_error_to_next_w", "max_composition_error_to_next_fraction"])

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for step, index in enumerate(indices):
            has_next = step < len(indices) - 1
            row: list[object] = [
                step + 1,
                int(index) + 1,
                _format(result.physics.time_s[index], 3),
                _format(result.distance_nm[index], 3),
                _format(result.physics.time_s[indices[step + 1]] - result.physics.time_s[index], 3)
                if has_next
                else "",
            ]
            for target_index in range(len(result.target_names)):
                row.extend(
                    [
                        _format(result.schedule.scheduled_power_w[index, target_index], 3),
                        _format(result.schedule.ramp_rate_w_per_s[step, target_index], 6)
                        if has_next
                        else "",
                    ]
                )
            row.extend(
                [
                    _format(result.schedule.segment_power_error_w[step], 6) if has_next else "",
                    _format(result.schedule.segment_composition_error[step], 8) if has_next else "",
                ]
            )
            writer.writerow(row)


def _write_profile_csv(result: PlanResult, path: Path) -> None:
    header = ["profile_index", "distance_nm", "time_s"]
    groups = [
        ("desired_fraction", result.desired_composition),
        ("ideal_power_w", result.physics.ideal_power_w),
        ("feasible_power_w", result.physics.feasible_power_w),
        ("scheduled_power_w", result.schedule.scheduled_power_w),
        ("predicted_fraction", result.schedule.scheduled_composition),
        ("scheduled_rate_nm_per_min", result.schedule.scheduled_rate_nm_per_min),
    ]
    slugs = _target_slugs(result.target_names)
    for prefix, _ in groups:
        header.extend([f"{slug}_{prefix}" for slug in slugs])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row_index in range(result.distance_nm.size):
            row: list[object] = [
                row_index,
                float(result.distance_nm[row_index]),
                float(result.physics.time_s[row_index]),
            ]
            for _, values in groups:
                row.extend(float(value) for value in values[row_index])
            writer.writerow(row)


def _write_html_report(result: PlanResult, path: Path, include_plots: bool) -> None:
    summary = result.summary()
    warnings = summary["warnings"]
    warning_html = (
        "".join(f"<li>{html.escape(warning)}</li>" for warning in warnings)
        if warnings
        else "<li class='ok'>No calculation warnings.</li>"
    )
    metric_rows = "".join(
        "<tr>"
        f"<td>{html.escape(name)}</td>"
        f"<td>{100.0 * summary['maximum_composition_error_fraction'][name]:.3f} at.%</td>"
        f"<td>{summary['maximum_power_error_w'][name]:.3f} W</td>"
        f"<td>{summary['maximum_absolute_ramp_rate_w_per_s'][name]:.6g} W/s</td>"
        "</tr>"
        for name in result.target_names
    )
    header_cells = "".join(
        f"<th>{html.escape(name)} power (W)</th><th>{html.escape(name)} ramp (W/s)</th>"
        for name in result.target_names
    )
    plan_rows: list[str] = []
    indices = result.schedule.breakpoint_indices
    for step, index in enumerate(indices):
        has_next = step < len(indices) - 1
        cells = [
            f"<td>{step + 1}</td>",
            f"<td>{result.physics.time_s[index]:.3f}</td>",
            f"<td>{result.distance_nm[index]:.3f}</td>",
        ]
        for target_index in range(len(result.target_names)):
            cells.append(f"<td>{result.schedule.scheduled_power_w[index, target_index]:.3f}</td>")
            cells.append(
                f"<td>{result.schedule.ramp_rate_w_per_s[step, target_index]:.6f}</td>"
                if has_next
                else "<td></td>"
            )
        plan_rows.append("<tr>" + "".join(cells) + "</tr>")
    plot_html = ""
    if include_plots:
        plot_html = """
        <section>
          <h2>Plots</h2>
          <img src="plots/power_vs_time.png" alt="Chamber power schedule">
          <img src="plots/composition_vs_thickness.png" alt="Desired and predicted composition">
          <img src="plots/composition_error.png" alt="Absolute composition error">
        </section>
        """
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(result.name)} — PowerplanPVD report</title>
  <style>
    :root {{ color-scheme: light; --ink:#17202a; --muted:#5d6d7e; --line:#d5d8dc;
      --accent:#1f618d; --panel:#f7f9f9; --warn:#fff4e5; --warnline:#d68910; }}
    body {{ max-width:1200px; margin:32px auto; padding:0 24px; color:var(--ink);
      font:15px/1.45 Arial, sans-serif; }}
    h1 {{ margin-bottom:4px; }} h2 {{ margin-top:32px; }}
    .subtitle {{ color:var(--muted); margin-top:0; }}
    .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }}
    .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:14px; }}
    .card strong {{ display:block; font-size:1.25rem; color:var(--accent); }}
    .warnings {{ background:var(--warn); border-left:4px solid var(--warnline); padding:10px 16px; }}
    .ok {{ color:#196f3d; }}
    table {{ width:100%; border-collapse:collapse; margin:12px 0 24px; }}
    th,td {{ border-bottom:1px solid var(--line); padding:8px; text-align:right; white-space:nowrap; }}
    th:first-child,td:first-child {{ text-align:left; }} th {{ background:#eaf2f8; position:sticky; top:0; }}
    .scroll {{ overflow-x:auto; }} img {{ max-width:100%; height:auto; margin:8px 0 20px; }}
    .files a {{ margin-right:18px; }}
    @media print {{ body {{ margin:0; max-width:none; }} .files {{ display:none; }} th {{ position:static; }} }}
  </style>
</head>
<body>
  <h1>{html.escape(result.name)}</h1>
  <p class="subtitle">PowerplanPVD operating report</p>
  <div class="cards">
    <div class="card"><span>Targets</span><strong>{len(result.target_names)}</strong>{html.escape(", ".join(result.target_names))}</div>
    <div class="card"><span>Operator steps</span><strong>{summary["breakpoint_count"]}</strong>{summary["point_count"]} profile points</div>
    <div class="card"><span>Thickness</span><strong>{summary["total_thickness_nm"]:.3f} nm</strong></div>
    <div class="card"><span>Estimated time</span><strong>{summary["total_time_min"]:.1f} min</strong></div>
  </div>
  <h2>Warnings</h2><ul class="warnings">{warning_html}</ul>
  <h2>Maximum errors and ramp rates</h2>
  <div class="scroll"><table><thead><tr><th>Target</th><th>Composition error</th><th>Power approximation error</th><th>Ramp rate</th></tr></thead><tbody>{metric_rows}</tbody></table></div>
  <h2>Operator plan</h2>
  <p>At each step, set the listed power and apply the ramp shown until the next step.</p>
  <div class="scroll"><table><thead><tr><th>Step</th><th>Time (s)</th><th>Thickness (nm)</th>{header_cells}</tr></thead><tbody>{"".join(plan_rows)}</tbody></table></div>
  {plot_html}
  <section>
    <h2>Before running</h2>
    <ol><li>Confirm target names and calibrations match the installed targets.</li><li>Resolve every warning above.</li><li>Confirm powers and ramp rates are within approved equipment limits.</li><li>Review the first run using the laboratory's normal witness-sample procedure.</li></ol>
  </section>
  <p class="files"><a href="operating_plan.csv">Operating plan CSV</a><a href="detailed_profile.csv">Detailed profile CSV</a><a href="summary.json">Summary JSON</a><a href="resolved_config.yaml">Resolved configuration</a></p>
</body></html>
"""
    path.write_text(document, encoding="utf-8")


def write_outputs(
    result: PlanResult,
    config: PlanConfig,
    output_dir: str | Path,
    include_plots: bool = True,
    overwrite: bool = False,
) -> list[Path]:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    schedule_path = output / "operating_plan.csv"
    profile_path = output / "detailed_profile.csv"
    summary_path = output / "summary.json"
    config_path = output / "resolved_config.yaml"
    text_path = output / "run_summary.txt"
    report_path = output / "report.html"

    planned = [schedule_path, profile_path, summary_path, config_path, text_path, report_path]
    if include_plots:
        planned.extend(
            output / "plots" / name
            for name in (
                "power_vs_time.png",
                "composition_vs_thickness.png",
                "composition_error.png",
            )
        )
    existing = [candidate.name for candidate in planned if candidate.exists()]
    if existing and not overwrite:
        raise OutputError(
            f"Output folder already contains PowerplanPVD files: {', '.join(existing)}. "
            "Choose another folder or enable overwrite explicitly."
        )

    _write_schedule_csv(result, schedule_path)
    _write_profile_csv(result, profile_path)
    summary_path.write_text(
        json.dumps(result.summary(), indent=2, sort_keys=True), encoding="utf-8"
    )
    config_path.write_text(yaml.safe_dump(config.to_dict(), sort_keys=False), encoding="utf-8")
    text_path.write_text(format_summary_text(result.summary()) + "\n", encoding="utf-8")
    paths = [schedule_path, profile_path, summary_path, config_path, text_path]
    if include_plots:
        paths.extend(write_plots(result, output / "plots"))
    _write_html_report(result, report_path, include_plots)
    paths.append(report_path)
    return paths
