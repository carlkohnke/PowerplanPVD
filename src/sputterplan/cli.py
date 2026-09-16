"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from .configuration import load_config
from .discovery import inspect_profile_file, parse_column_mapping, write_starter_config
from .errors import SputterPlanError
from .io import load_profile
from .outputs import write_outputs
from .pipeline import create_plan
from .presentation import format_summary_text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sputterplan",
        description="Create practical multi-target magnetron sputtering operation plans.",
        epilog=(
            "First time? Run 'sputterplan inspect-profile PROFILE.csv', then "
            "'sputterplan init PROFILE.csv --target NAME=RATE ...'."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)

    inspect = commands.add_parser(
        "inspect-profile", help="Show sheets, columns, and sample rows from a profile file."
    )
    inspect.add_argument("profile", type=Path)
    inspect.add_argument("--sheet")
    inspect.add_argument("--header-row", type=int, default=1)
    inspect.add_argument("--preview", type=int, default=5)

    initialize = commands.add_parser(
        "init", help="Create a starter YAML configuration from a profile file."
    )
    initialize.add_argument("profile", type=Path)
    initialize.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Configuration path. Default: PROFILE with a .yaml extension.",
    )
    initialize.add_argument(
        "--target",
        action="append",
        default=[],
        metavar="NAME=RATE",
        help="Target name and calibration in nm/min/W. Repeat for every target.",
    )
    initialize.add_argument("--sheet")
    initialize.add_argument("--header-row", type=int, default=1)
    initialize.add_argument("--distance-column")
    initialize.add_argument(
        "--composition-column",
        action="append",
        default=[],
        metavar="NAME=COLUMN",
        help="Map a target to a header, one-based number, or Excel letter. Repeat as needed.",
    )
    initialize.add_argument(
        "--composition-basis", choices=("fraction", "percent"), default="fraction"
    )
    initialize.add_argument("--composition-sum-tolerance", type=float, default=1e-6)
    initialize.add_argument(
        "--normalize-compositions",
        action="store_true",
        help="Explicitly normalize every composition row to sum to one.",
    )
    initialize.add_argument("--total-power", type=float, default=300.0)
    initialize.add_argument("--off-below", type=float, default=0.0)
    initialize.add_argument("--min-stable", type=float, default=0.0)
    initialize.add_argument("--force", action="store_true", help="Overwrite an existing config.")

    validate = commands.add_parser(
        "validate", help="Validate inputs and confirm that a complete plan can be calculated."
    )
    validate.add_argument("config", type=Path)

    plan = commands.add_parser("plan", help="Calculate and write an operating plan.")
    plan.add_argument("config", type=Path)
    plan.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output folder. Default: a results folder beside the configuration.",
    )
    plan.add_argument("--no-plots", action="store_true")
    plan.add_argument("--force", action="store_true", help="Overwrite existing SputterPlan files.")
    plan.add_argument("--json", action="store_true", help="Print the summary as JSON.")
    plan.add_argument("--open-report", action="store_true", help="Open report.html after success.")
    return parser


def _default_output(config_path: Path) -> Path:
    return config_path.resolve().parent / "results" / config_path.stem


def _print_inspection(args: argparse.Namespace) -> None:
    inspection = inspect_profile_file(
        args.profile,
        sheet=args.sheet,
        header_row=args.header_row,
        preview_count=args.preview,
    )
    print(f"Profile: {inspection.path}")
    print(f"Format: {inspection.format.upper()}")
    if inspection.sheet_names:
        print(f"Sheets: {', '.join(inspection.sheet_names)}")
        print(f"Selected sheet: {inspection.selected_sheet}")
    print(f"Header row: {inspection.header_row}")
    print("Columns:")
    for index, name in enumerate(inspection.headers, start=1):
        print(f"  {index}: {name}")
    if inspection.preview_rows:
        print("Preview:")
        for row in inspection.preview_rows:
            values = ", ".join("" if value is None else str(value) for value in row)
            print(f"  {values}")
    for warning in inspection.warnings:
        print(f"Warning: {warning}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "inspect-profile":
            _print_inspection(args)
            return 0
        if args.command == "init":
            destination_path = args.output or args.profile.with_suffix(".yaml")
            column_pairs = [parse_column_mapping(item) for item in args.composition_column]
            if len({name for name, _ in column_pairs}) != len(column_pairs):
                raise ValueError("Each --composition-column target may be mapped only once.")
            composition_columns = dict(column_pairs)
            distance_column = args.distance_column
            if distance_column is not None and distance_column.isdigit():
                distance_column = int(distance_column)
            destination = write_starter_config(
                args.profile,
                destination_path,
                args.target,
                sheet=args.sheet,
                header_row=args.header_row,
                distance_column=distance_column,
                composition_basis=args.composition_basis,
                composition_sum_tolerance=args.composition_sum_tolerance,
                normalize_compositions=args.normalize_compositions,
                total_power_w=args.total_power,
                off_below_power_w=args.off_below,
                min_stable_power_w=args.min_stable,
                composition_columns=composition_columns,
                overwrite=args.force,
            )
            config = load_config(destination)
            profile = load_profile(config)
            print(f"Created {destination}")
            print(
                f"Detected {profile.point_count} points and {profile.target_count} targets: "
                f"{', '.join(profile.target_names)}"
            )
            print(f'Next: sputterplan validate "{destination}"')
            return 0

        config = load_config(args.config)
        profile = load_profile(config)
        result = create_plan(config, profile)
        if args.command == "validate":
            print(
                "Configuration and profile are valid. A complete plan was calculated successfully.\n"
            )
            print(format_summary_text(result.summary()))
            return 0

        output = args.output or _default_output(args.config)
        paths = write_outputs(
            result,
            config,
            output,
            include_plots=not args.no_plots,
            overwrite=args.force,
        )
        summary = result.summary()
        print(json.dumps(summary, indent=2) if args.json else format_summary_text(summary))
        print(f"\nWrote {len(paths)} files to {Path(output).resolve()}")
        print(f"Report: {Path(output).resolve() / 'report.html'}")
        if args.open_report:
            webbrowser.open((Path(output).resolve() / "report.html").as_uri())
        return 0
    except (SputterPlanError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
