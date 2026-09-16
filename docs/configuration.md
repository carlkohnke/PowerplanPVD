# Configuration reference

PowerplanPVD configurations are YAML or JSON files with four main sections: `profile`, `targets`,
`operation`, and `planner`.

## Composition profile

```yaml
profile:
  path: gradient.xlsx
  sheet: Desired gradient
  header_row: 2
  data_start_row: 3
  data_end_row: 603
  distance_column: A
  composition_columns:
    Ni: B
    Ti: C
    Nb: D
  composition_basis: fraction
  normalize_compositions: false
  composition_sum_tolerance: 0.000002
```

| Setting | Meaning |
|---|---|
| `path` | CSV, TSV, XLSX, or XLSM profile path; relative paths are resolved from the configuration |
| `sheet` | Excel worksheet; required when a workbook has multiple sheets |
| `header_row` | One-based row containing column headers |
| `data_start_row` | Optional one-based first data row |
| `data_end_row` | Optional one-based final data row |
| `distance_column` | Header, one-based column number, or Excel letter containing deposited depth |
| `composition_columns` | Optional mapping from each target name to its profile column |
| `composition_basis` | `fraction` or `percent` |
| `normalize_compositions` | Explicitly normalize each row; defaults to `false` |
| `composition_sum_tolerance` | Permitted difference between a row sum and one after basis conversion |

Distance must be finite and strictly increasing. Compositions must be finite and nonnegative. At
least two data rows are required.

PowerplanPVD does not silently normalize malformed compositions. Enable normalization only when it
is scientifically intended.

## Targets and linear calibrations

```yaml
targets:
  - name: Ni
    rate_nm_per_min_per_watt: 0.1003
    off_below_power_w: 1
    min_stable_power_w: 2
    max_power_w: 250
    max_ramp_rate_w_per_s: 2
```

Add one entry for every target. Names must be unique and correspond to the composition profile or
its explicit column mapping.

`rate_nm_per_min_per_watt` is the slope of the measured linear deposition-rate-versus-power
relationship:

```text
deposition rate (nm/min) = calibration (nm/min/W) × power (W)
```

For example, 100.3 nm deposited in 10 minutes at 100 W gives:

```text
rate = 100.3 / 10 = 10.03 nm/min
calibration = 10.03 / 100 = 0.1003 nm/min/W
```

The model assumes this relationship passes through zero. It does not currently accept an intercept,
piecewise calibration, or nonlinear calibration table.

Target limitation fields:

| Setting | Meaning | Behavior |
|---|---|---|
| `off_below_power_w` | Power below which the target is treated as off | Enforced |
| `min_stable_power_w` | Minimum stable power when the target is on | Enforced |
| `max_power_w` | Maximum target power | Enforced when provided |
| `max_ramp_rate_w_per_s` | Approved target ramp rate | Checked and reported as a warning |

Ramp-rate violations are not automatically corrected because stretching deposition time would
change the deposited thickness and composition.

## Operating strategy

### Fixed total chamber power

```yaml
operation:
  strategy: total_power
  total_power_w: 300
  calculation_mode: corrected
  hardware_limit_policy: error
```

The target powers are distributed so their sum equals `total_power_w` whenever the target bounds
make that possible.

### One target at fixed power

```yaml
operation:
  strategy: fixed_target
  fixed_target: Ti
  fixed_power_w: 150
  calculation_mode: corrected
  hardware_limit_policy: error
```

The named target stays at `fixed_power_w`; all other target powers vary. The desired fraction of the
fixed target must be greater than zero throughout the profile.

### Hardware-limit policy

- `error`: stop when the requested operating condition and target bounds are incompatible.
- `clip`: return the bounded feasible approximation and report the resulting warnings and errors.

Use `error` when a plan must never proceed with a degraded composition. Use `clip` to investigate
what the configured equipment limits can achieve.

## Calculation mode

- `corrected`: recommended for new plans. Time is calculated from hardware-feasible powers using
  trapezoidal integration, and total power is preserved when feasible.
- `legacy_compatible`: reproduces the original MATLAB power solution, low-power behavior, and
  right-endpoint time integration for regression and historical comparisons.

Legacy mode may also set:

```yaml
operation:
  legacy_slack_target: Ti
```

The slack target closes the composition balance omitted by the original symbolic MATLAB system.
See [MATLAB equivalence](matlab_equivalence.md) for the exact scope of compatibility.

## Planner settings

```yaml
planner:
  power_tolerance_abs_w: 2
  power_tolerance_rel: 0.03
  composition_tolerance_abs: 0.015
  max_breakpoints: 50
  ramp_rate_resolution_w_per_s: 0.001
```

| Setting | Meaning |
|---|---|
| `power_tolerance_abs_w` | Absolute permitted power approximation error |
| `power_tolerance_rel` | Relative permitted power approximation error; `0.03` means 3% |
| `composition_tolerance_abs` | Absolute fraction error; `0.015` means 1.5 atomic percentage points |
| `max_breakpoints` | Maximum coordinated operator settings |
| `ramp_rate_resolution_w_per_s` | Resolution used to round reported ramp rates |

The planner builds piecewise-linear target-power curves with shared breakpoints. Tighter tolerances
usually require more operator steps. Planning stops if satisfying the tolerances would exceed
`max_breakpoints`.

Tolerance guarantees apply at supplied profile points. Provide enough depth resolution to represent
sharp or nonlinear composition changes.

## Complete example

```yaml
name: Ni-Ti-Nb plan

profile:
  path: gradient.csv
  distance_column: distance_nm
  composition_basis: fraction

targets:
  - name: Ni
    rate_nm_per_min_per_watt: 0.1003
    off_below_power_w: 1
    min_stable_power_w: 2
    max_power_w: 250
    max_ramp_rate_w_per_s: 2
  - name: Ti
    rate_nm_per_min_per_watt: 0.0533
    off_below_power_w: 1
    min_stable_power_w: 2
    max_power_w: 250
    max_ramp_rate_w_per_s: 2
  - name: Nb
    rate_nm_per_min_per_watt: 0.0710
    off_below_power_w: 1
    min_stable_power_w: 2
    max_power_w: 250
    max_ramp_rate_w_per_s: 2

operation:
  strategy: total_power
  total_power_w: 300
  calculation_mode: corrected
  hardware_limit_policy: error

planner:
  power_tolerance_abs_w: 2
  power_tolerance_rel: 0.03
  composition_tolerance_abs: 0.015
  max_breakpoints: 50
  ramp_rate_resolution_w_per_s: 0.001
```

The numeric values above demonstrate the fields; use calibrations and limits measured or approved
for the actual equipment.
