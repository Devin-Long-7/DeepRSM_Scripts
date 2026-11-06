# ISAM Daily Restart at CST00

[中文](README_ISAM_CST00.md)

Reset tags at target-day 00:00 CST (UTC+8), using baseline UTC16 CGRID for the physical/chemical initial state. Target days are independent.

## Files

```text
IC-RB-CST00_isam_scripts/
|-- README_ISAM_CST00.md / README_ISAM_CST00_en.md
|-- launch_isam_cst00_5days.csh                 # Sequential five-day launcher
|-- run_cctm_D3_ISAM_daily_restart_CST00.csh    # Two-segment single-day run
|-- isam_control_PRD_O3.txt                    # Tag definitions
`-- EmissCtrl_cb6r3_ae7_aq_isam_base.nml       # Baseline emissions
```

## Usage

Check `CMAQ_HOME`, `BLD`, `EXEC`, MPI, meteorology, BC, emissions, masks and baseline CGRID paths. The executable must actually be compiled with ISAM. The tag file and namelist are included; launch from this directory.

Baseline files must contain full instantaneous states at preceding-day UTC16. September 6, 13, 14, 16 and 19, 2022 require Julian-date labels 2022248, 2022255, 2022256, 2022258 and 2022261. Verify internal TFLAG values.

```bash
# Executes CMAQ directly; check one day first
csh run_cctm_D3_ISAM_daily_restart_CST00.csh 2022-09-06
csh launch_isam_cst00_5days.csh
```

The entry runs CMAQ directly without a dry-run option. The launcher continues after a failed day; check each day's exit status and logs after execution.

## Outputs

Configured `OUTDIR` defaults to the `isam_daily_cst00` tree. Segment 1 runs eight hours from preceding-day UTC16 with new tags; segment 2 runs sixteen hours from target-day UTC00, resuming segment 1 SA_CGRID through `ISAM_PREVDAY`.

Check model logs, physical/tagged restart files, SA_ACONC timestamps and tag-sum consistency with bulk ozone. Assemble segments by actual time before calculating CST daily statistics. ISAM fractions and IC-RB concentration differences have different definitions. These run scripts do not include a standalone postprocessing program.
