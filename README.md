# PowerplanPVD

PowerplanPVD turns a desired through-thickness composition gradient into a practical multi-target
magnetron sputtering plan. It calculates target powers and coordinated ramp changes, predicts the
resulting composition, and produces an operator-readable report.

The tool was created for multilayer and compositionally graded metal-alloy thin films, including
high-entropy alloys. It supports any number of targets.

## What you provide

Every plan needs three things:

1. **A desired composition gradient** — a CSV, TSV, or Excel table containing deposited depth and
   the desired fraction or percentage of every target material.
2. **Linear sputtering calibrations** — one measured deposition-rate-per-watt value in nm/min/W
   for each target.
3. **Process limitations** — the total-power or fixed-target operating rule plus applicable off,
   minimum-stable-power, maximum-power, and ramp-rate limits.

PowerplanPVD assumes each target's deposition rate varies linearly with power. See the
[configuration reference](docs/configuration.md) for calibration requirements and every available
setting.

## How you use it

### Desktop GUI

The GUI lets you select a configuration, validate it, create a plan, review the run summary, and
open the finished report and output folder.

```powershell
sputterplan-gui
```

The GUI consumes a YAML or JSON configuration. You can write that file manually or generate a
starter configuration with the CLI.

### Configuration file and CLI

To create a starter configuration from a composition file:

```powershell
sputterplan inspect-profile .\gradient.xlsx
sputterplan init .\gradient.xlsx `
  --target Ni=0.1003 `
  --target Ti=0.0533 `
  --target Nb=0.0710 `
  --total-power 300
```

Review the generated YAML and add the limitations that apply to your equipment. Then validate and
create the plan:

```powershell
sputterplan validate .\gradient.yaml
sputterplan plan .\gradient.yaml --open-report
```

You can instead write a configuration manually, starting from one of the files in
[examples](examples/).

## Results

The primary result is `report.html`, which summarizes the plan, warnings, operator steps, and
plots. Each run also writes CSV tables containing the operating plan and full calculated profile,
plus machine-readable JSON and a copy of the resolved configuration.

## Installation

PowerplanPVD requires Python 3.11 or newer.

```powershell
cd "C:\path\to\Magnetron Sputtering Plan Creator Code"
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

## Documentation

- [Getting started](docs/getting_started.md) — installation, GUI and CLI walkthroughs, and outputs
- [Configuration reference](docs/configuration.md) — profiles, calibrations, limitations, operating
  strategies, and planner settings
- [Calculation model](docs/model.md) — equations, assumptions, and numerical approach
- [MATLAB equivalence](docs/matlab_equivalence.md) — comparison with the original MATLAB program
- [Operator review checklist](docs/operator_review.md) — required checks before using a plan

PowerplanPVD is a planning tool; it does not control deposition equipment or establish safe
equipment limits. Review every generated schedule using approved laboratory procedures.
