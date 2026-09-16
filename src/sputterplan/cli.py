"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .configuration import load_config
from .errors import SputterPlanError
from .io import load_profile
from .outputs import write_outputs
from .pipeline import create_plan


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sputterplan",
        description="Create a multi-target magnetron sputtering operation plan.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate configuration and profile data.")
    validate.add_argument("config", type=Path)
    plan = commands.add_parser("plan", help="Calculate and write an operating plan.")
    plan.add_argument("config", type=Path)
    plan.add_argument("--output", "-o", type=Path, required=True)
    plan.add_argument("--no-plots", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
        profile = load_profile(config)
        if args.command == "validate":
            print(
                f"Valid: {profile.point_count} points, {profile.target_count} targets "
                f"({', '.join(profile.target_names)})"
            )
            return 0
        result = create_plan(config, profile)
        paths = write_outputs(result, config, args.output, include_plots=not args.no_plots)
        summary = result.summary()
        print(json.dumps(summary, indent=2))
        print(f"Wrote {len(paths)} files to {Path(args.output).resolve()}")
        return 0
    except (SputterPlanError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
