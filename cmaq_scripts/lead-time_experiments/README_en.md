# Lead-Time Control Experiments

[中文](README.md)

Compare target-day control P0 with controls beginning one, two or three local days earlier (A1/A2/A3). Local time is CST, UTC+8.

## Files

```text
lead-time_experiments/
|-- README.md / README_en.md
|-- batch_run_localday_controls.csh                  # September single-case entry
|-- batch_run_localday_controls_multicase.csh        # Multiple cases
|-- batch_run_localday_controls_multicase_batch1.csh # Alternative case/experiment list
|-- run_cctm_D3_202209_base_devin.csh                 # September template
|-- run_cctm_D3_202209_P0_Sep19_PRD_VOC30_NOX30.csh    # Historical single-case script
|-- EmissCtrl_nml/                                  # Baseline/control namelists
|-- post_scripts/                                   # See its bilingual README
`-- .gitignore
```

## Usage

Check templates, baseline UTC00 CGRID, namelists, `target_days`, `experiments`, `case_suffix` or `case_list`, model/MPI paths, `enable_post` and outputs near the selected entry's beginning. The multiple-case default `cleanup_raw=1` archives and then deletes raw segments; 0 retains them and 2 deletes directly. Review this policy before execution.

From this directory:

```bash
csh batch_run_localday_controls.csh --dry-run
csh batch_run_localday_controls.csh
csh batch_run_localday_controls_multicase.csh --dry-run
# For standalone post-processing, explicitly match the existing runs
csh post_scripts/run_post_localday_controls.csh --help
```

Dry-run generates scripts without simulation, post-processing or cleanup. Normal execution uses embedded settings; it does not implicitly accept date overrides.

## Timing and Outputs

A baseline preparation segment advances continuous baseline UTC00 CGRID to the control start at UTC16. P0 uses three segments including preparation. A1/A2/A3 normally use four, combining intervening full UTC days into one continuous segment. With `last_segment_full_day=N`, the final segment ends at target-day UTC16, or CST24.

Runtime creates `generated/` and logs. Raw, COMBINE and daily data use configured destinations. Automatic post-processing calls `post_scripts/run_post_localday_controls.csh`. External requirements include CMAQ/MPI, meteorology/emissions/IC/BC, csh, GNU tools, NCO, COMBINE and Python.
