# IC-RB Daily Reset at CST00

[中文](README.md)

Reset each day to domain baseline CGRID at 00:00 CST (UTC+8), or preceding-day UTC16. Two CMAQ segments cover one CST calendar day.

## Files

```text
IC-RB-CST00_scripts/
|-- README.md / README_en.md
|-- batch_run_cases.csh                  # Scenario/configuration batch entry
|-- cctm_config.csh                      # Default configuration
|-- cctm_config_D3_150X117_202209.csh     # September D3 configuration
|-- run_configs/
|   `-- cctm_config_D3_150X117_202209.csh # Additional configuration copy
|-- run_manager.csh                      # Generate, validate, run and post-process
|-- run_cctm_template.csh                 # CMAQ template
|-- validate_script.csh                  # Input/script checks
|-- post/
|   |-- check_restart.py                 # Restart-time checks
|   |-- run_post.py                      # Post-processing planning and execution
|   |-- recover_post.py                  # Recovery processing
|   |-- run_post_all_layers.py           # All-layer compatibility entry
|   `-- run_post_layer1.py               # First-layer compatibility entry
`-- .gitignore
```

## Configuration

Check dates, `BASELINE_CGRID_ROOT`, CMAQ/MPI, meteorology, BC, emissions, masks, namelists and outputs. Inspect internal CGRID timestamps: preceding-day UTC16 is required.

Defaults reference sibling `../cctm_scripts_v5.3.2/` for namelists/generator and `../post_scripts_v5.3.2/` for COMBINE templates/species definitions. Both are now bundled; retain their relative layout. Local `post/` wraps scheduling and checks. CMAQ/COMBINE executables and large input datasets remain external. Requirements include csh, GNU utilities, Python, NetCDF/NCO and compatible MPI.

## Usage

From this directory:

```bash
csh batch_run_cases.csh prd2zero everywhere2zero --dry-run
csh batch_run_cases.csh prd2zero everywhere2zero
# Pass the configuration directly, without --config
csh run_manager.csh run_configs/cctm_config_D3_150X117_202209.csh --dry-run
```

The no-argument batch selects `prd2zero` and `everywhere2zero`. Dry-run generates/checks plans without executing CMAQ or post-processing, but can still require external inputs.

## Outputs

Execution creates `generated/` for scripts, manifests and logs; model outputs use `OUTDIR_BASE`. Segment 1 covers preceding-day UTC16–24 and segment 2 target-day UTC00–16. Neither alone is a full day.

Post-processing assembles hourly/CST daily products and checks restart times and coverage. Review cleanup options such as `CLEANUP_CCTM_OUTPUT` before production execution. Additional CST40 batch scripts and tests are not bundled. Documentation/source review does not constitute a new CMAQ run.
