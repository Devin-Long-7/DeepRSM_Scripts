# CMAQ v5.3.2 Continuous Runs

[中文](README.md)

This directory contains a complete CMAQ v5.3.2 configuration, generation, validation, execution and postprocessing workflow. It defaults to `IC_RB_MODE=N`, with daily IC-RB resets disabled. Initial startup uses the configured ICON; subsequent dates continue from the preceding day's scenario CGRID.

## Choosing a Workflow

| Directory | Default mode | Initial-state handling |
|---|---|---|
| `cctm_scripts_v5.3.2/` (this directory) | `IC_RB_MODE=N` | Continuous runs retaining the scenario's evolving state across days |
| [`IC-RB-UTC00_scripts/`](../IC-RB-UTC00_scripts/README_en.md) | `IC_RB_MODE=Y` | Reinitialize each UTC00 from configured baseline CGRID |

UTC00 corresponds to CST08. Both directories retain complete code and distinct default configurations to make continuous and daily-reset experiments easy to distinguish. Each uses its own configuration, template and manager; changes are not automatically synchronized.

## Files

```text
cctm_scripts_v5.3.2/
|-- README.md / README_en.md
|-- batch_run_cases.csh             # Scenario/configuration batch entry
|-- cctm_config.csh                 # Default continuous configuration, IC_RB_MODE=N
|-- cctm_config_D3_150X117_202209.csh # September continuous configuration with startup dates
|-- cctm_config_D3_150X117_202209_IC-RB_base_on_cgrid.csh # Alternative daily-reset configuration
|-- run_manager.csh                 # Generate, check, execute and post-process
|-- run_cctm_template.csh            # CMAQ template
|-- validate_script.csh             # Input/script checks
|-- create_emissCtrl_nml.py          # Template/CSV namelist generator
|-- EmissCtrl_nml/                  # Existing scenario namelists
`-- nml_config/
    |-- EmissCtrl_base.nml          # NML template
    |-- scaling_rules.csv          # Scenario scaling rules
    `-- stream_families.csv        # Stream-to-family mapping
```

Other modules also reference `EmissCtrl_nml/` by relative path. This directory additionally provides a complete independent CCTM workflow. The runtime `generated/` directory is not a bundled input.

## Quick Start

1. Provide CMAQ v5.3.2, compatible MPI/compiler runtime, meteorology, emissions, ICON, BCON and region masks. Postprocessing also requires COMBINE, NCO and the appropriate Python environment; see the [postprocessing guide](../post_scripts_v5.3.2/README_en.md).
2. Configure model, input, output, `NML_PATH` and postprocessing paths in a working copy of `cctm_config.csh`. Defaults are D3, August 27 to September 30, 2022, 32 processes, `IC_RB_MODE=N`, and surface-layer concentration output and postprocessing. The selected configuration determines dates; use `POST_BEGIN_DATE` and `POST_END_DATE` to extract a shorter analysis period.
3. Default `GENERATE_NML=N` reads the existing `NML_PATH`, which retains a deployment-specific absolute path and must match the actual location. With `GENERATE_NML=Y`, the generator reads the three files in local `nml_config/`. Each selected case needs a corresponding NML or CSV rule.
4. From this directory, generate and inspect the default baseline case:

```bash
cd /path/to/cmaq_scripts/cctm_scripts_v5.3.2
csh run_manager.csh cctm_config.csh --dry-run
# Run after checking generated scripts, inputs and output locations
csh run_manager.csh cctm_config.csh
```

Dry-run writes `generated/` and validates scripts; real inputs may still be required. It does not execute CMAQ or postprocessing. Configuration files are positional arguments, without `--config`.

For scenario batches:

```bash
csh batch_run_cases.csh oos3 --dry-run
csh batch_run_cases.csh oos3
```

The batch defaults to `oos3`, using `cctm_config.csh` while overriding case name/type. This differs from the manager's default `base` case. The alternative `*_IC-RB_base_on_cgrid.csh` enables Y; use the adjacent `IC-RB-UTC00_scripts/` for daily-reset experiments to keep the default workflows distinct.

## Outputs and Checks

Generated scripts, optional new namelists and logs use `generated/`. Model data use `OUTDIR_BASE/case/domain/year/month/`; postprocessing uses configured `COMBINE_DIR`. Check exit status, CCTM/COMBINE logs, the CGRID continuation chain and NetCDF time coverage, grid, variables and units.

Configure separate `OUTDIR_BASE` and `COMBINE_DIR` locations for continuous and daily-reset experiments to avoid collisions between identical case names. Check that `BASELINE_FILE` matches actual layers, filenames and dates. Default `CLEANUP_CCTM_OUTPUT=T` removes some raw outputs; set F in a working copy for an initial inspection. A single UTC day does not represent a complete CST calendar day.
