# Operator review checklist

Before using a generated schedule:

1. Confirm every target name and deposition-rate calibration matches the installed target and current calibration conditions.
2. Confirm the composition profile uses fractions or percentages exactly as configured.
3. Review `summary.json` for hardware-limit and ramp-rate warnings.
4. Inspect `composition_error.png`, especially where a target turns on or off.
5. Confirm every power setpoint and ramp rate is within the chamber's approved operating envelope.
6. Confirm the indicated total deposition time is compatible with substrate motion and process timing.
7. Review the first run with the laboratory's normal witness-sample and composition-verification procedure.

The software does not connect to or command deposition equipment. It does not replace equipment interlocks, approved operating procedures, or operator judgment.
