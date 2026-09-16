# Changelog

## 0.3.0 - 2026-09-16

- Renamed total-power operation to maximum-total-power operation and made the configured value a
  ceiling; individual target maxima now scale all target powers together to preserve composition.
- Hardened configuration and profile validation against non-finite values and incomplete rows.
- Added GitHub Actions checks for formatting, linting, tests, coverage, and wheel builds.
- Consolidated planning onto one hardware-aware calculation path.
- Simplified configurations by removing the calculation-mode setting.
- Reorganized and validated the bundled two-target and three-target examples.
- Focused the documentation on the current application and workflow.

## 0.2.0 - 2026-09-16

- Added guided profile inspection and starter-configuration commands.
- Added safe default output locations and explicit overwrite protection.
- Added a responsive desktop workflow with validation, progress, summaries, and report access.
- Added operator-oriented HTML reports, text summaries, and diagnostic plots.
- Improved configuration, worksheet, path, and column error messages.
- Added CSV header safety and comprehensive automated, packaging, and stress tests.

## 0.1.0 - 2026-09-16

- Added arbitrary target counts, named column mappings, and per-target calibrations and limits.
- Added fixed-total-power and fixed-target operating strategies.
- Added a shared-breakpoint planner with explicit power and composition error checks.
- Added CSV, TSV, and Excel profile input plus operator CSV, JSON, YAML, and plot outputs.
- Added a command-line interface, Python API, desktop GUI, and automated test suite.
