# PowerplanPVD

Generate precise physical vapor deposition (PVD) sputtering plans for manufacturing metal alloy thin-films with desired z-direction compositional gradients. Created for optimization of multilayer, magnetron-sputtered high entropy alloy (HEA) films.

PowerplanPVD converts a desired composition-versus-thickness profile into a practical multi-target magnetron sputtering schedule. It calculates ideal chamber powers, applies configured hardware limits, reduces the power curves to shared operator change times, predicts the deposited composition, and reports the resulting errors.

The calculation is agnostic to the number and names of targets. Each target requires its own measured deposition-rate calibration and specified sputtering hardware limits.

## What you provide

Every plan needs three things:

1. **A desired composition gradient** — a CSV, TSV, or Excel table containing deposited depth and
   the desired fraction or percentage of every target material.
2. **Linear sputtering calibrations** — one measured deposition-rate-per-watt value in nm/min/W
   for each target.
3. **Process limitations** — the maximum-total-power or fixed-target operating rule plus applicable
   off, minimum-stable-power, maximum-power, and ramp-rate limits.

PowerplanPVD assumes each target's deposition rate varies linearly with power. See the
[configuration reference](docs/configuration.md) for calibration requirements and available
settings.

## How you use it

### Desktop GUI

The GUI lets you select a configuration, validate it, create a plan, review the run summary, and
open the finished report and output folder.

```powershell
sputterplan-gui
```

### Configuration file creation

To use the CLI to create a starter configuration from a composition file:

```powershell
sputterplan inspect-profile .\gradient.xlsx
sputterplan init .\gradient.xlsx `
  --target Ni=0.1003 `
  --target Ti=0.0533 `
  --target Nb=0.0710 `
  --max-total-power 300
```
where the --target command denotes the slope of the measured linear deposition-rate-versus-power
relationship in nm/min/W.

Then validate and create the plan:

```powershell
sputterplan validate .\gradient.yaml
sputterplan plan .\gradient.yaml --open-report
```

You can instead write a YAML or JSON configuration manually, starting from one of the files in
[examples](examples/)

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
- [Operator review checklist](docs/operator_review.md) — checks before using a plan

Development setup and the required pull-request checks are documented in
[CONTRIBUTING.md](CONTRIBUTING.md). GitHub Actions runs linting, formatting, tests, and a wheel
build on every push and pull request.

## License

PowerplanPVD is available under the [MIT License](LICENSE).

PowerplanPVD is a planning tool; it does not control deposition equipment or establish safe
equipment limits. Review every generated schedule using approved laboratory procedures.
