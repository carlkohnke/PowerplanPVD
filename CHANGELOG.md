# Changelog

## 0.2.0 - 2026-09-16

- Added `inspect-profile` and `init` commands for a guided first-run workflow.
- Added safe default output locations and explicit overwrite protection for configurations,
  reports, tables, and plots.
- Added a responsive desktop workflow with validation, progress, readable results, keyboard
  shortcuts, and one-click report/folder access.
- Added an operator-oriented HTML report and plain-text run summary.
- Improved configuration, worksheet, path, and column error messages.
- Fixed Excel element headers such as `Ni` being mistaken for Excel column letters.
- Sanitized and de-duplicated CSV target column names and escaped report content.
- Expanded testing with real XLSX files, CLI workflows, GUI smoke tests, output safety tests,
  randomized multi-target property tests, packaging checks, and larger stress cases.

## 0.1.0 - 2026-09-16

- Rebuilt the legacy MATLAB sputtering-plan calculation as a configurable Python package.
- Added CSV, TSV, and Excel composition-profile input.
- Added arbitrary target counts, named target mappings, and per-target calibrations and limits.
- Added fixed-total-power and fixed-target operating strategies.
- Added legacy-compatible and corrected calculation modes.
- Added a shared-breakpoint planner with explicit power and composition error checks.
- Added operator CSV, detailed CSV, JSON, resolved YAML, and plot outputs.
- Added a command-line interface, Python API, and desktop launcher.
- Added MATLAB R2024b regression data and automated tests.
