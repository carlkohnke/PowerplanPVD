# SputterPlan

SputterPlan converts a desired composition-versus-thickness profile into a practical multi-target magnetron sputtering schedule. It calculates ideal chamber powers, applies configured hardware limits, reduces the power curves to shared operator change times, predicts the deposited composition, and reports the resulting errors.

The calculation is agnostic to the number and names of targets. A profile can come from CSV, TSV, or Excel, and each target has its own measured deposition-rate calibration and hardware limits.

## What it produces

Each run writes:

- `operating_plan.csv`: the operator schedule, including time, thickness, target powers, and ramp rates.
- `detailed_profile.csv`: desired composition, ideal and feasible power, scheduled power, predicted composition, and deposition rate at every input point.
- `summary.json`: run statistics, maximum errors, maximum ramp rates, and warnings.
- `resolved_config.yaml`: the exact resolved settings used for the run.
- `run_summary.txt`: a compact human-readable run summary.
- `report.html`: an operator-friendly report with warnings, plan tables, plots, and a pre-run checklist.
- `plots/`: power, composition, and composition-error figures.

CSV outputs open directly in Excel while remaining easy to inspect with Python, MATLAB, or laboratory data systems.

## Installation

SputterPlan requires Python 3.11 or newer.

```powershell
cd "C:\path\to\Sputtering Plan Creator"
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

Install test dependencies for development:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
```

## 30-second first run

Inspect a composition profile before writing any configuration:

```powershell
sputterplan inspect-profile .\my_gradient.xlsx --sheet "Desired gradient" --header-row 2
```

Create a starter configuration. Repeat `--target` for every target and enter each measured
calibration in nm/min/W:

```powershell
sputterplan init .\my_gradient.xlsx `
  --sheet "Desired gradient" `
  --header-row 2 `
  --target Ni=0.1003 `
  --target Ti=0.0533 `
  --target Nb=0.0710
```

If headers are duplicated or differ from target names, map them explicitly with one-based column
numbers or Excel letters:

```powershell
sputterplan init .\my_gradient.xlsx `
  --target Ni=0.1003 --target Ti=0.0533 --target Nb=0.0710 `
  --distance-column A `
  --composition-column Ni=B --composition-column Ti=C --composition-column Nb=D
```

Rounded input rows are checked rather than silently changed. Use
`--composition-sum-tolerance 0.000002` when a known export has that rounding precision, or
`--normalize-compositions` only when row normalization is scientifically intended.

This creates `my_gradient.yaml` beside the profile. It refuses to replace an existing
configuration unless `--force` is supplied. Review the YAML, then validate and create the plan:

```powershell
sputterplan validate .\my_gradient.yaml
sputterplan plan .\my_gradient.yaml --open-report
```

By default, results go to `results\my_gradient` beside the configuration. SputterPlan also
protects existing output files; use `--force` only when you intend to replace a previous run.

## Run the included example

Validate the configuration and input profile:

```powershell
.\.venv\Scripts\python.exe -m sputterplan.cli validate .\examples\three_target_plan.yaml
```

Create the operating plan:

```powershell
.\.venv\Scripts\python.exe -m sputterplan.cli plan `
  .\examples\three_target_plan.yaml `
  --output .\results\three_target
```

Open the output folder:

```powershell
explorer .\results\three_target
```

The installed console command is equivalent:

```powershell
sputterplan plan .\examples\three_target_plan.yaml --output .\results\three_target
```

## Desktop launcher

Start the small desktop launcher with:

```powershell
.\.venv\Scripts\python.exe -m sputterplan.gui
```

Choose a YAML or JSON configuration and an output folder, then select **Create plan**. The same tested calculation engine is used by the GUI, CLI, and Python API.

The launcher validates by calculating the complete plan, stays responsive during longer runs,
shows the same human-readable summary as the CLI, suggests a run-specific output folder, protects
existing results by default, and provides one-click access to the report and output folder.
Keyboard shortcuts: `Ctrl+O` chooses a configuration and `Ctrl+Enter` creates the plan.

## Composition profile

A CSV profile has one distance column and one column per target:

```csv
distance_nm,Ni,Ti,Nb
0,0.10,0.80,0.10
100,0.15,0.72,0.13
200,0.20,0.64,0.16
```

Distances must be finite and strictly increasing. Compositions must be nonnegative and sum to one. Percentage inputs are supported with `composition_basis: percent`. SputterPlan does not silently normalize malformed profiles unless `normalize_compositions: true` is explicitly selected.

Excel input is selected by worksheet, header row, and either column names, one-based column numbers, or Excel column letters:

```yaml
profile:
  path: gradient.xlsx
  sheet: Desired gradient
  header_row: 2
  data_start_row: 3
  distance_column: A
  composition_columns:
    Ni: B
    Ti: C
    Nb: D
```

The original Hodge Lab workbook is not copied into this repository. [examples/legacy_workbook.yaml.example](examples/legacy_workbook.yaml.example) shows how to point SputterPlan at it locally.

## Configure any number of targets

Target order is defined by the `targets` list. Profile columns are matched by target name unless `composition_columns` supplies an explicit mapping.

```yaml
targets:
  - name: Ni
    rate_nm_per_min_per_watt: 0.1003
    off_below_power_w: 1.0
    min_stable_power_w: 2.0
    max_power_w: 250.0
    max_ramp_rate_w_per_s: 2.0
  - name: Ti
    rate_nm_per_min_per_watt: 0.0533
  - name: Nb
    rate_nm_per_min_per_watt: 0.0710
```

`rate_nm_per_min_per_watt` is the measured linear calibration between chamber power and deposition rate. Rates must use the same thickness and time units shown in the field name.

## Operating strategies

### Fixed total chamber power

```yaml
operation:
  strategy: total_power
  total_power_w: 300
  calculation_mode: corrected
```

At every profile point, SputterPlan solves

```text
total_rate = total_power / sum(composition_i / calibration_i)
power_i = composition_i * total_rate / calibration_i
```

Corrected mode projects powers onto configured on/off, minimum-stable, and maximum-power limits while preserving total power when the constraints are feasible.

### One fixed-power target

```yaml
operation:
  strategy: fixed_target
  fixed_target: Ti
  fixed_power_w: 150
  calculation_mode: corrected
```

The fixed target must have nonzero desired composition throughout the profile. Otherwise no finite solution exists and SputterPlan stops with the exact failing row.

## Planner tolerances

The planner uses shared breakpoints across every target so the operator changes ramp settings at one coordinated set of times.

```yaml
planner:
  power_tolerance_abs_w: 2.0
  power_tolerance_rel: 0.03
  composition_tolerance_abs: 0.015
  max_breakpoints: 50
  ramp_rate_resolution_w_per_s: 0.001
```

Each piecewise-linear segment must satisfy both the power tolerance and the composition tolerance relative to the hardware-feasible curve at every supplied profile point. The planner recursively adds the point with the largest normalized error, then removes redundant breakpoints. If target power limits alone make the requested composition exceed its tolerance, `hardware_limit_policy: error` stops; `clip` returns the bounded feasible plan with an explicit warning. If the schedule approximation itself needs too many changes, planning fails rather than silently degrading the result.

Configured maximum ramp rates are reported as violations. The program does not silently stretch time because doing so would alter deposited thickness and therefore invalidate the requested spatial gradient.

## Legacy-compatible and corrected calculations

`legacy_compatible` reproduces the MATLAB power solution, its 1 W off threshold, 2 W minimum power behavior when configured, and its right-endpoint time integration. The modern shared-breakpoint planner is still used; MATLAB's proprietary `findchangepts` selection is not reproduced exactly.

The original symbolic system omits one target's composition equation and lets that target close the rate balance. Set `operation.legacy_slack_target` to identify that target when reproducing rounded legacy inputs. If omitted, fixed-target mode uses its fixed target and total-power mode uses the last configured target.

`corrected` mode:

- Calculates deposition time from the hardware-feasible powers.
- Uses trapezoidal integration of reciprocal deposition rate.
- Preserves fixed total power when target limits permit it.
- Reports changes caused by target limits.
- Validates compositions, calibrations, distances, and infeasible fixed-target cases.

See [docs/matlab_equivalence.md](docs/matlab_equivalence.md) for measured regression results and [docs/model.md](docs/model.md) for the equations and assumptions.

## Python API

```python
from sputterplan import create_plan, load_config
from sputterplan.outputs import write_outputs

config = load_config("examples/three_target_plan.yaml")
result = create_plan(config)
write_outputs(result, config, "results/three_target")

print(result.summary())
```

Advanced users can construct `CompositionProfile` directly from NumPy arrays and pass it to `create_plan(config, profile)`.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

The suite covers configuration validation, profile parsing, closed-form power calculations, fixed-target behavior, one through twelve targets, planner error guarantees, output generation, and MATLAB regression data.

It also includes real XLSX fixtures, CLI onboarding and overwrite behavior, desktop-window smoke
tests, HTML/CSV safety checks, and randomized property tests across varying profile sizes and one
through ten targets.

## Operational limitations and safety

SputterPlan is a planning tool. It does not control sputtering hardware, verify plasma stability, model target poisoning, compensate for angular flux distributions, account for resputtering or substrate motion, or establish safe equipment limits. Target calibrations and power/ramp limits must come from the actual chamber and approved operating procedures. Review every generated schedule before use.

No public-release license has been selected. Keep the repository private until its source, data, documentation, and licensing are reviewed for release.
