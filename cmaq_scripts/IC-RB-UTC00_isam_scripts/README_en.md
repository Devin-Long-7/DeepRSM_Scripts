# ISAM Daily Restart at UTC00

[中文](README.md)

Initialize physical/chemical states from baseline CGRID, reset tags at UTC00 (CST08, UTC+8), and run 24 hours. This is not a CST 00–24 calendar day.

## Files

```text
IC-RB-UTC00_isam_scripts/
|-- README.md / README_en.md
|-- launch_isam_5days.csh                      # Sequential five-day launcher
|-- run_cctm_D3_ISAM_daily_restart.csh         # Single-day YYYY-MM-DD entry
|-- run_cctm_D3_202209_base_ISAM_devin.csh     # Original continuous-run script
|-- isam_control_PRD_O3.txt                    # Tag definitions
`-- EmissCtrl_cb6r3_ae7_aq_isam_base.nml       # Baseline emission namelist
```

## Usage

Check executable/build paths, MPI, baseline CGRID, meteorology, emissions, BC, masks, tags and outputs. The daily entry reads a baseline CGRID named with the preceding Julian day; its internal time must match target-day UTC00. Confirm that the executable actually supports ISAM.

From this directory:

```bash
# Executes CMAQ directly; check one day first
csh run_cctm_D3_ISAM_daily_restart.csh 2022-09-06
# September 6, 13, 14, 16 and 19
csh launch_isam_5days.csh
```

There is no dry-run option. The launcher continues after a failed day; check each day's logs. Continuous-run dates are embedded in that separate script, not supplied through the daily interface. Execute it only when the continuous experiment is intended and configured.

## Outputs

Daily outputs default to configured `isam_daily/D3/2022/<month>/`. `ISAM_NEW_START=Y` and an unset `ISAM_PREVDAY` make daily tags independent. Check SA_ACONC, SA_CGRID, termination logs, units and tag sums.

UTC00–24 spans CST08 to the following CST08 and must not be treated as same-date CST calendar-day MDA8. No separate statistics program or test suite is included. Production runs require CMAQ/MPI and the external inputs on a compute node.
