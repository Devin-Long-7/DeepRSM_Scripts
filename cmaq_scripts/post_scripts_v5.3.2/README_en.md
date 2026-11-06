# CMAQ v5.3.2 Postprocessing

[中文](README.md)

Combine hourly CCTM outputs, select variables, shift time, calculate daily metrics and plot daily maps. An external CMAQ installation, compiled utilities and simulation outputs are required.

## Files

```text
post_scripts_v5.3.2/
|-- README.md / README_en.md
|-- 0_run_post_script.csh                 # Main postprocessing entry
|-- 0_run_post_script_output_2_IC_BC.csh  # Entry including nested IC/BC generation
|-- 1_run_combine_aconc.csh              # Concentration COMBINE and SpecDef calculations
|-- 1_run_combine_dep.csh                # Deposition COMBINE
|-- 2_extract_18species_by_nco.csh       # NCO selection; actually 21 basic variables
|-- 3_tolocaltime.csh                   # I/O API m3tshift
|-- 4_convert2daily.py                  # esil daily conversion at layer index 0
|-- 5_run_bcon.csh                      # Nested boundary conditions using BCON
|-- 6_run_icon_loop.csh                 # Daily nested initial conditions using ICON
|-- 7_plot_daily_map.py                 # Daily concentration/response maps
`-- spec_def_files/
    |-- SpecDef_cb6r3_ae7_aq.txt
    |-- SpecDef_cb6r3_ae7_aq_all_layers.txt
    |-- SpecDef_cb6r3_ae7_aq_carryover_all_layers.txt
    `-- README_carryover.md / README_carryover_en.md
```

See the [carryover definitions](spec_def_files/README_carryover_en.md).

## Quick Start

1. Configure a separate working copy of `0_run_post_script.csh`: check `CCTM_WORKDIR`, `script_path`, dates, domain, case, `INPDIR`, `CCTMOUTDIR_ROOT` and `COMBINE_DIR`. The derived `CMAQ_HOME` must contain `config_cmaq.csh`.
2. Provide csh, GNU date, NCO, I/O API `m3tshift` and compiled CMAQ COMBINE; IC/BC generation also requires BCON/ICON. Daily conversion and plotting require the author's `esil` package and its dependencies, plus tqdm, NumPy, pandas, xarray, cmaps and plotting dependencies. This collection does not include `esil`; install the matching version separately. Configure the Python activation path in the entry script.
3. For an initial run set `CLEANUP_CCTM_OUTPUT=F`, `KEEP_COMBINE_FILE=T`, `COPY_SPEC_DEF=F`, disable plotting if unnecessary, and check input time coverage before running:

```bash
cd /path/to/cmaq_scripts/post_scripts_v5.3.2
csh 0_run_post_script.csh > post.log 2>&1
```

**There is no dry-run. The main entry defaults to `CLEANUP_CCTM_OUTPUT=T`, which removes CCTM output files.** `KEEP_COMBINE_FILE` controls retention of some intermediate files; also inspect removal logic before invoking time-shifting and other helpers. `COPY_SPEC_DEF=T` overwrites definitions in the CMAQ installation; its default F skips copying.

Helpers 1, 2, 3, 5 and 6 depend on environment variables supplied by the entry script. COMBINE selects SpecDef files from the CMAQ installation tree; local presence does not enable a definition. Deposition definitions `SpecDef_Dep_*` must be provided by the installation.

The IC/BC entry additionally calls `5_run_bcon_D3_155X122.csh` and `6_run_icon_loop_D3_155X122.csh`, neither of which is included. Its full default sequence therefore requires additional scripts and verification of the IC/BC switches and calls.

## Python Usage

With `esil` installed, replace these example paths with actual inputs:

```bash
python 4_convert2daily.py /data/COMBINE.nc 2022-09-06 2022-09-06 8
python 7_plot_daily_map.py /data/Daily_COMBINE.nc /data/Daily_BASE.nc \
  2022-09-06 2022-09-06 O3_MDA8 D3 base /data/boundary.shp
```

The converter writes `Daily_<input filename>` beside the input and skips existing output by default. The value `8` is the hour offset passed to `esil`; provide sufficient coverage for the selected local day and avoid applying the offset twice. Daily metric definitions are implemented in `esil.netcdf_helper.convert_hr2daily_data`, so this wrapper alone does not establish their complete statistical rules. Maps require compatible baseline dates, grids and boundary data.

## Output Checks

Inspect `post.log`, COMBINE logs and NetCDF time coverage, layers, variables, units and missing values. Daily conversion uses layer index 0. Generated products typically include `COMBINE_*.nc`, optional `_18species.nc`, `Daily_*.nc` and maps. Preserve extended variables for carryover analysis rather than discarding them with the original extraction list.
