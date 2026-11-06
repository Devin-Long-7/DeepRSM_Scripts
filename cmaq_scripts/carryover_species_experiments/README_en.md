# CST00 Initial-State Species Replacement

[中文](README.md)

Construct mixed initial states from continuous-control state C and daily-reset state R at 00:00 China Standard Time (CST, UTC+8), and evaluate their effects on target-day ozone.

## Files

```text
carryover_species_experiments/
|-- README.md / README_en.md
|-- batch_run.csh            # Batch entry point
|-- cctm_config.csh          # Dates, cases, groups, resources and paths
|-- initial_fields.csv       # C/R initial states and emission namelists
|-- prepare_plan.py          # Input checks and segment planning
|-- prepare_ic.py            # Mixed-state construction and field checks
|-- post_results.py          # Ozone statistics and signed effects
|-- assets/
|   |-- run_cctm_template.csh
|   `-- guangdong_cities.json
`-- .gitignore
```

The template and city boundaries are included. CMAQ/MPI, meteorology, emissions, BC and initial states are external inputs. Requirements include csh, GNU date, bc, Python, NumPy, netCDF4, pandas, pyproj, Shapely 2+ and Matplotlib.

## Usage

Edit `cctm_config.csh`: check `PYTHON_CMD`, model paths, resources, `TARGET_DATES`, `EXPERIMENT_CASES`, `GROUP_*` and post-processing settings. Update C/R and namelist paths in `initial_fields.csv`. Inputs must be single-record, full-layer instantaneous CGRID at preceding-day UTC16. Averaged ACONC is unsuitable. Supplied R paths refer to baseline CGRID, not D2-interpolated ICON.

From this directory:

```bash
csh batch_run.csh --dates 2022-09-16 --dry-run
csh batch_run.csh --dates 2022-09-16
csh batch_run.csh
# Post-process an existing batch; replace the manifest path
csh batch_run.csh --post-only /path/to/generated/batch_ID/manifest.json
```

Dry-run writes plans without creating mixed ICs or running CMAQ. Defaults select September 6, 13, 14, 16 and 19, with eight cases per day: C, R, `C_NO2`, `R_without_NO2`, `C_other_N`, `C_OVOC`, `C_O3` and `C_rest`.

## Outputs

`generated/batch_ID/` is created at runtime for manifests, snapshots, mixed ICs, scripts and provenance. Raw outputs use `OUTDIR_BASE`. Segment 1 runs eight hours from preceding-day UTC16; segment 2 continues to target-day UTC16, covering one CST day.

Post-processing produces `hourly_ozone.csv`, `daily_ozone.csv`, `signed_effects.csv`, masks and plots. Ozone is in ppbv. MDA8 is calculated per cell using the 17 within-day eight-hour windows, then averaged spatially; daily mean uses 00–23 CST and daytime mean 10–17 CST.

Signed effects are relative to C/R controls. Nonadditivity indicates background interactions, not separately measured pathway fluxes. Replacements cover all D3 cells and layers. Unit tests are not included; documentation review does not establish production CMAQ execution.
