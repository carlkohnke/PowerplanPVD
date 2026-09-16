"""Plots for operator review and model diagnostics."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .results import PlanResult


def _colors(count: int):
    cmap = plt.get_cmap("tab20" if count > 10 else "tab10")
    return [cmap(index % cmap.N) for index in range(count)]


def write_plots(result: PlanResult, output_dir: str | Path) -> list[Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    colors = _colors(len(result.target_names))
    paths: list[Path] = []

    figure, axis = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for index, (name, color) in enumerate(zip(result.target_names, colors)):
        axis.plot(
            result.physics.time_s,
            result.physics.feasible_power_w[:, index],
            color=color,
            alpha=0.35,
            linewidth=1.2,
            label=f"{name} feasible",
        )
        axis.plot(
            result.physics.time_s,
            result.schedule.scheduled_power_w[:, index],
            color=color,
            linewidth=2,
            label=f"{name} scheduled",
        )
        bp = result.schedule.breakpoint_indices
        axis.scatter(
            result.physics.time_s[bp],
            result.schedule.scheduled_power_w[bp, index],
            color=color,
            marker="x",
            s=28,
        )
    axis.set(title="Chamber power schedule", xlabel="Time (s)", ylabel="Power (W)")
    axis.grid(alpha=0.2)
    axis.legend(ncol=2, fontsize=8)
    path = output / "power_vs_time.png"
    figure.savefig(path, dpi=180)
    plt.close(figure)
    paths.append(path)

    figure, axis = plt.subplots(figsize=(10, 6), constrained_layout=True)
    for index, (name, color) in enumerate(zip(result.target_names, colors)):
        axis.plot(
            result.distance_nm,
            result.desired_composition[:, index],
            color=color,
            alpha=0.45,
            linewidth=1.3,
            label=f"{name} desired",
        )
        axis.plot(
            result.distance_nm,
            result.schedule.scheduled_composition[:, index],
            color=color,
            linestyle="--",
            linewidth=2,
            label=f"{name} predicted",
        )
    axis.set(
        title="Desired and predicted composition",
        xlabel="Deposited thickness (nm)",
        ylabel="Atomic fraction",
        ylim=(-0.02, 1.02),
    )
    axis.grid(alpha=0.2)
    axis.legend(ncol=2, fontsize=8)
    path = output / "composition_vs_thickness.png"
    figure.savefig(path, dpi=180)
    plt.close(figure)
    paths.append(path)

    error = np.abs(result.schedule.scheduled_composition - result.desired_composition)
    figure, axis = plt.subplots(figsize=(10, 5), constrained_layout=True)
    for index, (name, color) in enumerate(zip(result.target_names, colors)):
        axis.plot(result.distance_nm, error[:, index], color=color, label=name)
    axis.set(
        title="Absolute composition error",
        xlabel="Deposited thickness (nm)",
        ylabel="Absolute fraction error",
    )
    axis.grid(alpha=0.2)
    axis.legend(ncol=2, fontsize=8)
    path = output / "composition_error.png"
    figure.savefig(path, dpi=180)
    plt.close(figure)
    paths.append(path)
    return paths
