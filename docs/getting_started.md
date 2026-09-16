# Getting started

This guide covers installation, creation of a configuration, GUI and CLI operation, and the output
files produced by PowerplanPVD. For every available setting, see the
[configuration reference](configuration.md).

## Install

PowerplanPVD requires Python 3.11 or newer. From PowerShell:

```powershell
cd "C:\path\to\Magnetron Sputtering Plan Creator Code"
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

The installed command names are `sputterplan` and `sputterplan-gui`.

For development and testing dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
```

## Prepare the inputs

A plan requires:

1. A composition-versus-deposited-depth table in CSV, TSV, XLSX, or XLSM format.
2. One linear deposition calibration in nm/min/W for each target.
3. An operating strategy and the limitations applicable to the chamber and targets.

A simple CSV profile looks like this:

```csv
distance_nm,Ni,Ti,Nb
0,0.10,0.80,0.10
100,0.15,0.72,0.13
200,0.20,0.64,0.16
```

Distances must be finite and strictly increasing. Compositions must be nonnegative and sum to one,
or to 100 when the configuration selects percentage input.

## Create a starter configuration with the CLI

Inspect an unfamiliar profile first:

```powershell
sputterplan inspect-profile .\gradient.xlsx --sheet "Desired gradient" --header-row 2
```

Create the starter YAML. Each `--target` value has the form
`TARGET_NAME=DEPOSITION_RATE_PER_WATT`:

```powershell
sputterplan init .\gradient.xlsx `
  --sheet "Desired gradient" `
  --header-row 2 `
  --target Ni=0.1003 `
  --target Ti=0.0533 `
  --target Nb=0.0710 `
  --total-power 300
```

`--target Ni=0.1003` means the Ni target has a calibration slope of 0.1003 nm/min/W. It does not
set Ni to a particular power. A single calibration number assumes the measured rate-versus-power
relationship is linear and passes through zero.

If a workbook contains duplicate headers or its headers do not match the target names, map the
columns explicitly:

```powershell
sputterplan init .\gradient.xlsx `
  --target Ni=0.1003 --target Ti=0.0533 --target Nb=0.0710 `
  --distance-column A `
  --composition-column Ni=B `
  --composition-column Ti=C `
  --composition-column Nb=D `
  --total-power 300
```

The generated YAML is a starting point. Review it and add the actual target and equipment limits
before using the plan.

## Write a configuration manually

Configurations may be YAML or JSON. The following is a compact total-power example:

```yaml
name: Ni-Ti-Nb gradient

profile:
  path: gradient.xlsx
  sheet: Desired gradient
  header_row: 2
  distance_column: A
  composition_columns: {Ni: B, Ti: C, Nb: D}

targets:
  - name: Ni
    rate_nm_per_min_per_watt: 0.1003
    off_below_power_w: 1
    min_stable_power_w: 2
    max_power_w: 250
  - name: Ti
    rate_nm_per_min_per_watt: 0.0533
    off_below_power_w: 1
    min_stable_power_w: 2
    max_power_w: 250
  - name: Nb
    rate_nm_per_min_per_watt: 0.0710
    off_below_power_w: 1
    min_stable_power_w: 2
    max_power_w: 250

operation:
  strategy: total_power
  total_power_w: 300
  hardware_limit_policy: error
```

See the [configuration reference](configuration.md) before choosing limits or planner tolerances.

## Validate and create a plan

Validation loads the entire profile and calculates a complete plan without writing result files:

```powershell
sputterplan validate .\gradient.yaml
```

Create the results:

```powershell
sputterplan plan .\gradient.yaml --open-report
```

By default, results are written to `results\CONFIGURATION_NAME` beside the configuration. Select a
different folder with `--output`. Existing PowerplanPVD files are protected unless `--force` is
specified deliberately.

## Use the desktop GUI

Start the GUI with:

```powershell
sputterplan-gui
```

Choose an existing YAML or JSON configuration and an output folder. **Validate** calculates the
plan and shows its summary without writing results. **Create plan** writes the results. After a
successful run, use **Open report** or **Open output folder**.

Keyboard shortcuts:

- `Ctrl+O`: choose a configuration
- `Ctrl+Enter`: create the plan

## Output files

Each run writes:

- `report.html`: operator-oriented summary, warnings, schedule table, plots, and checklist
- `operating_plan.csv`: time, thickness, target powers, ramp rates, and segment errors
- `detailed_profile.csv`: desired composition, calculated powers, predicted composition, and rates
  at every profile point
- `run_summary.txt`: concise human-readable summary
- `summary.json`: machine-readable statistics and warnings
- `resolved_config.yaml`: exact resolved settings used for the run
- `plots/`: power, composition, and composition-error figures

Review the [operator checklist](operator_review.md) before using any schedule.

## Python API

Advanced users can run the same pipeline directly:

```python
from sputterplan import create_plan, load_config
from sputterplan.outputs import write_outputs

config = load_config("gradient.yaml")
result = create_plan(config)
write_outputs(result, config, "results/gradient")
```

The CLI, GUI, and Python API use the same calculation engine.

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```
