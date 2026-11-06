# IC-RB00 and IC-RB08 Shapley Attribution

[中文](README.md)

This directory retains historical UTC00 (CST08) initial-state experiments and a CST00 four-cell design. Analyze their different time windows separately.

## Files

```text
shapley_attribution_scripts/
|-- README.md / README_en.md
|-- calculate_cst00_shapley.py                 # Four-cell attribution and closure
|-- IC-RB08_scripts/
|   |-- batch_run_iconly.csh                  # gen/run/submit batch entry
|   |-- create_iconly_csh.csh                 # Regional script generation
|   |-- check_ic11_cgrid.csh                  # C11 restart checks
|   |-- run_cctm_D3_202209_prd2zero_sep19.csh # Continuous C11
|   |-- run_cctm_D3_202209_prd2zero_iconly.csh # Initial-state-only C10
|   `-- CMAQ_ic_only_c10_files_description.md # Historical output description
|-- IC-RB00_scripts/
|   |-- run_cst00_shapley.csh                 # Seven cases in dependency order
|   |-- cst00_config_common.csh               # Shared settings
|   |-- config_C00.csh / config_C01.csh / config_C10.csh / config_C11.csh
|   |-- config_E01.csh / config_E10.csh / config_E11.csh
|   |-- run_manager.csh / run_cctm_template.csh / validate_script.csh
|   `-- post/
|       |-- check_restart.py / run_post.py / recover_post.py
|       `-- run_post_all_layers.py / run_post_layer1.py
`-- .gitignore
```

`IC-RB00_scripts/post/` provides restart-time checks and postprocessing entries. Shared namelists and COMBINE templates/definitions reside two levels above that script directory in `cctm_scripts_v5.3.2/` and `post_scripts_v5.3.2/`; retain this relative layout. `IC-RB08_scripts/CMAQ_ic_only_c10_files_description.md` describes UTC00 result naming and layout; the corresponding raw model outputs must be supplied separately.

## Simulation

C00 uses baseline initial states/emissions; C01 resets daily to baseline and uses controlled emissions; C10 uses propagated C11 initial states and baseline emissions; C11 continuously propagates controlled states with controlled emissions. C cases control PRD; E cases control the whole domain and share C00.

Check common and per-cell dates, baseline UTC16 CGRID, CMAQ/MPI, IC/BC, meteorology, namelists, output and cleanup settings. C10 `PROPAGATED_ROOT` must match its C11. Do not skip intervening continuous C00/C11 days.

```bash
cd IC-RB00_scripts
csh run_cst00_shapley.csh --dry-run
csh run_cst00_shapley.csh
```

Segment 1 covers preceding-day UTC16–24; segment 2 target-day UTC00–16. Runtime creates `generated/`; each case writes raw outputs and daily `post/` products to configured roots. Review external inputs and cleanup before use.

## Attribution

From this directory, provide four same-group daily NetCDF files with matching units and time coverage. Replace the paths:

```bash
python calculate_cst00_shapley.py \
  --c00 /path/to/C00_daily.nc --c01 /path/to/C01_daily.nc \
  --c10 /path/to/C10_daily.nc --c11 /path/to/C11_daily.nc \
  --dates Sep06,Sep13,Sep14,Sep16,Sep19 --output-prefix results_cst00/prd
```

Defaults use whole-grid spatial means. Optional `--mask-json` maps region names to boolean `.npy` mask paths matching the grid. CSV/JSON outputs retain input concentration units:

```text
total = C00 - C11
same_day_Shapley = 0.5 * ((C00 - C01) + (C10 - C11))
carryover_Shapley = 0.5 * ((C00 - C10) + (C01 - C11))
```

The components must sum to total. Zero total gives NaN HDF; interpret percentages cautiously for small totals.
