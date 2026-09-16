# MATLAB equivalence

## Baseline procedure

The original `Sputtering_Operation_Plan_Maker.m` and `Sputtering Rates and Plans.xlsx` were read from their original Hodge Lab directory. They were not edited, renamed, or moved.

MATLAB R2024b ran the unmodified script from the source directory. The repository wrapper in `tools/capture_matlab_baseline.m` suppressed interactive figure display and exported numerical workspace variables after the script completed. The wrapper does not alter the calculation.

The reference case uses:

- Worksheet: `Distance Optimized`
- Range: `A3:D603`
- Targets: Ni, Ti, Nb
- Calibrations: 0.1003, 0.0533, and 0.071 nm/min/W
- Total chamber power: 300 W
- Legacy low-power handling: below 1 W becomes 0 W; 1–2 W becomes 2 W

The source script SHA-256 before conversion was:

```text
016814302EDA16B63DB435B1E3BED2CF46E72C397BE3175DE8A6088E00EDBED0
```

`tools/build_reference_data.py` converts the exported MAT file into compact NumPy regression data and records source/workbook hashes and MATLAB runtime in `tests/reference_data/baseline_metadata.json`.

## Equivalence scope

The automated regression test compares the Python legacy-compatible calculation with MATLAB for:

- Distance
- Desired compositions
- Component deposition rates
- Post-threshold chamber powers
- Elapsed time at every profile point

Measured maximum absolute differences are:

- Component deposition rate: `3.56e-15 nm/min`
- Chamber power: `1.14e-13 W`
- Elapsed time: `0 s`

The direct Python equations are algebraically equivalent to MATLAB's symbolic linear solve. Array comparisons use near-machine-precision tolerances.

The measured MATLAB R2024b runtime was `23.745 s`. After configuration and profile loading, Python averaged `0.000186 s` for the physics calculation and `0.00583 s` for physics plus shared-breakpoint planning. Those measurements correspond to approximately `127,600×` and `4,076×` speedups, respectively. CLI startup, Excel parsing, plotting, and file writing are separate from these calculation timings; a no-plot end-to-end legacy CLI run completed in about `1.14 s` on the same machine.

The modern planner does not attempt to reproduce MATLAB's final `findchangepts` indices exactly. That function is proprietary, and the legacy routine does not guarantee the requested final error after its second reduction pass. SputterPlan instead uses one documented shared-breakpoint algorithm with pointwise power and composition checks. The MATLAB operator table is retained as baseline evidence, but exact change-index identity is not an acceptance criterion.

## Corrected behavior

The legacy script calculates interval time from ideal deposition rates and only afterward forces low powers to 0 W or 2 W. This makes the displayed achievable powers inconsistent with its time coordinate and predicted deposition after a threshold changes a target.

Corrected mode derives deposition rate, composition, and time from the same hardware-feasible powers. It also validates composition sums, strictly increasing distance, positive calibrations, fixed-target singularities, and explicit target maximum powers.

## Reproduce the baseline

Set the environment variables used by `tools/capture_matlab_baseline.m`, run it with MATLAB R2024b, install test dependencies, and run:

```powershell
.\.venv\Scripts\python.exe .\tools\build_reference_data.py `
  --mat .\tmp\matlab_baseline.mat `
  --source "C:\path\to\Sputtering_Operation_Plan_Maker.m" `
  --workbook "C:\path\to\Sputtering Rates and Plans.xlsx" `
  --output .\tests\reference_data

.\.venv\Scripts\python.exe -m pytest tests\test_matlab_equivalence.py
```
