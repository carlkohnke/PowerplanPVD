# Calculation model

## Inputs and units

For target `i` at deposited thickness `z`:

- `x_i(z)` is the desired deposited atomic fraction.
- `K_i` is the measured deposition calibration in nm/min/W.
- `P_i(z)` is target power in W.
- `r_i(z) = K_i P_i(z)` is deposition rate in nm/min.

The model assumes target deposition rates add linearly and deposited composition is proportional to the target-specific rates:

```text
x_i = r_i / sum(r_j)
```

The model does not include transport geometry, sticking coefficients, target poisoning,
resputtering, density changes, or composition-dependent yield.

## Maximum-total-power solution

For maximum total power `P_max`, the unconstrained solution uses the available ceiling:

```text
r_total = P_max / sum(x_i / K_i)
r_i = x_i r_total
P_i = r_i / K_i
```

The Python implementation evaluates these equations directly for every target and profile point. No symbolic equation solver is required.

## Fixed-target solution

For target `c` fixed at `P_c`:

```text
r_total = K_c P_c / x_c
P_i = x_i r_total / K_i
```

`x_c` must be positive everywhere. A profile that requests zero fixed-target composition is mathematically incompatible with a positive fixed power.

## Hardware-feasible powers

For maximum-total-power operation, PowerplanPVD first calculates the desired-composition power
ratios at `P_max`. If an individual target would exceed `max_power_w`, clip mode scales every target
power by the same factor. This preserves composition while allowing the combined power to fall
below `P_max`. Off and minimum-stable thresholds are then applied. Error mode stops instead of
scaling when an individual maximum would be exceeded.

For fixed-target operation, it applies each target's on/off, minimum, and maximum constraints and
then holds the selected target at the configured fixed power.

## Deposition time

Deposition time is calculated from the hardware-feasible deposition rates by integrating reciprocal
rate with the trapezoidal rule:

```text
dt_j = (z_j - z_(j-1)) * (1/r_(j-1) + 1/r_j) / 2
```

Minutes are converted to seconds at the output boundary.

## Shared-breakpoint planner

The planner approximates every feasible target-power curve with piecewise-linear segments sharing the same breakpoints. For each candidate segment it reconstructs powers at all enclosed time samples, converts them back to deposition rates and compositions, and evaluates:

- Absolute plus relative power error for every target.
- Absolute deposited-composition error for every target.

The worst normalized error determines where a new breakpoint is inserted. A cleanup pass removes any breakpoint whose neighboring segment still satisfies every tolerance. The resulting operator table therefore has coordinated change times and explicit pointwise approximation bounds for the supplied profile samples. Desired-versus-achieved composition error caused by the configured hardware limits is reported separately; clip mode warns when that unavoidable error exceeds the requested composition tolerance.

The tolerance guarantee applies at input profile points. Users should provide sufficient spatial resolution to represent sharp or nonlinear gradients.
