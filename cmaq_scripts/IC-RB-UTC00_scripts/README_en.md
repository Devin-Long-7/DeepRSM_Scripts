# IC-RB UTC00 Template Workflow

[中文](README.md)

Generate and execute CMAQ v5.3.2 scripts from configurations. UTC00 corresponds to CST08 (UTC+8). Configurations distinguish continuous operation from daily resets.

This directory defaults to `IC_RB_MODE=Y` for daily-reset experiments. Use [`cctm_scripts_v5.3.2/`](../cctm_scripts_v5.3.2/README_en.md), which defaults to `IC_RB_MODE=N`, for continuous runs. Both retain complete code and distinct default configurations to clarify experiment selection; edits are not automatically synchronized.

## Files

```text
IC-RB-UTC00_scripts/
|-- README.md / README_en.md
|-- batch_run_cases.csh             # Scenario/configuration batch entry
|-- cctm_config.csh                 # Default configuration
|-- cctm_config_D3_150X117_202209.csh
|-- cctm_config_D3_150X117_202209_IC-RB_base_on_cgrid.csh
|-- run_manager.csh                 # Generate, check, execute and post-process
|-- run_cctm_template.csh            # CMAQ template
|-- validate_script.csh             # Input/script checks
|-- create_emissCtrl_nml.py          # Template/CSV namelist generator
|-- EmissCtrl_nml/                  # Existing scenario namelists
`-- nml_config/
    |-- EmissCtrl_base.nml
    |-- scaling_rules.csv
    `-- stream_families.csv
```

## Usage

Check dates, grid, CMAQ/MPI, meteorology, IC/BC, masks, emissions and outputs in the selected configuration. Run dates are determined by the selected configuration, not the directory name.

The default `cctm_config.csh` is identical to `cctm_config_D3_150X117_202209_IC-RB_base_on_cgrid.csh`: September 1–30, 2022, D3, `IC_RB_MODE=Y`, daily resets from baseline UTC00 CGRID, and surface-layer concentration output and postprocessing. `NML_PATH` retains the original deployment-specific absolute path; adapt it to the actual `EmissCtrl_nml/` location in a working copy.

`IC_RB_MODE=N` is continuous operation and `Y` resets at UTC00. Inspect the configuration/template for the actual initial-state source: ICON and baseline CGRID resets are distinct. The default accepts N/Y only; use the separate CST00 directory for that experiment.

`GENERATE_NML=N` selects an existing `NML_PATH`. With Y, the generator reads `nml_config/EmissCtrl_base.nml`, `scaling_rules.csv` and `stream_families.csv`.

From this directory:

```bash
csh batch_run_cases.csh oos3 --dry-run
csh batch_run_cases.csh oos3
# Configuration path is positional, without --config
csh run_manager.csh cctm_config_D3_150X117_202209_IC-RB_base_on_cgrid.csh --dry-run
```

The batch defaults to `oos3`. Dry-run generates/checks scripts without running CMAQ. Default postprocessing uses sibling `../post_scripts_v5.3.2/`; CMAQ/COMBINE executables and raw inputs must be configured separately.

## Outputs

`generated/` is created at runtime for scripts, namelists and logs. Raw data use `OUTDIR_BASE`; post-processing uses configured destinations. Review `DELETE_AFTER_RUN` and post-processing cleanup settings.
