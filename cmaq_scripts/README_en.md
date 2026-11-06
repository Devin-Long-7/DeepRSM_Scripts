# CMAQ Experiment Scripts

[中文](README.md)

Scripts for CMAQ v5.3.2 scenarios, initial-condition resets, ISAM, historical attribution and postprocessing. Each module retains its existing configuration interface. Configure external model, input and output paths in a working copy.

## Directory Guide

The modules below are located under `cmaq_scripts/` in the repository. Keep these directories alongside one another to preserve relative dependencies.

| Directory | Purpose and instructions |
|---|---|
| `IC-RB-UTC00_scripts/` | [UTC00 initial-condition reset and scenario runs](IC-RB-UTC00_scripts/README_en.md) |
| `IC-RB-CST00_scripts/` | [CST00 runs and two-segment concatenation](IC-RB-CST00_scripts/README_en.md) |
| `IC-RB-UTC00_isam_scripts/` | [UTC00 ISAM runs](IC-RB-UTC00_isam_scripts/README_en.md) |
| `IC-RB-CST00_isam_scripts/` | [CST00 ISAM runs](IC-RB-CST00_isam_scripts/README_ISAM_CST00_en.md) |
| `carryover_species_experiments/` | [Initial-condition species-group carryover experiments](carryover_species_experiments/README_en.md) |
| `lead-time_experiments/` | [Emission-control lead-time experiments](lead-time_experiments/README_en.md) |
| `pr_cmaq_validation_scripts/` | [CMAQ validation runs for PR scenarios](pr_cmaq_validation_scripts/README_en.md) |
| `shapley_attribution_scripts/` | [Four-cell experiments and same-day/history Shapley attribution](shapley_attribution_scripts/README_en.md) |
| `cctm_scripts_v5.3.2/` | [Complete continuous workflow, default IC_RB_MODE=N, and shared NML](cctm_scripts_v5.3.2/README_en.md) |
| `post_scripts_v5.3.2/` | [COMBINE, variable extraction, daily conversion and maps](post_scripts_v5.3.2/README_en.md) |

## Getting Started

1. Select a module and read its file guide, configuration requirements and invocation examples.
2. Provide CMAQ v5.3.2 with compatible mechanism/grid, MPI/compiler runtime, MCIP, emissions, ICON/BCON, baseline CGRID/ACONC and region masks as required by the module. Large model inputs are external.
3. Configure paths, dates, cases, output locations and cleanup switches in a separate working copy. Where supported, use `--dry-run` to inspect the plan; some dry-runs still require real inputs.
4. Check each task's exit status, CCTM/COMBINE logs, output time coverage, grid and variables to confirm the results for every day.

UTC00 corresponds to CST08. CST00 starts at UTC16 on the preceding day and requires the prescribed cross-UTC-day concatenation. Keep results with different initialization times distinct.

## Shared Dependencies and Limitations

`cctm_scripts_v5.3.2/` and `IC-RB-UTC00_scripts/` each retain complete run code. The former defaults to `IC_RB_MODE=N` for continuous runs; the latter defaults to `IC_RB_MODE=Y` for daily UTC00 initial-state resets. Their similar code is retained separately to make experiment selection clear; configurations and edits are not automatically synchronized. `cctm_scripts_v5.3.2/EmissCtrl_nml/` also provides shared namelists for other modules.

Shared postprocessing in `post_scripts_v5.3.2/` requires an external `esil` package for daily conversion and maps; this collection does not include it.

The IC/BC postprocessing entry references two absent D3 helpers. See module documentation and supply these dependencies before running the full affected workflow.

Some scripts overwrite or remove outputs; inspect switches and target directories before execution. Adapt machine-specific absolute paths to the deployment environment.
