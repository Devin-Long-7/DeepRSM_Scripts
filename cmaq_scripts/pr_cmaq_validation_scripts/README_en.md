# Direct CMAQ Validation of PR

[中文](README.md)

Scan NOx emission factors while retaining VOC and other conditions, and compare the peak of receptor ozone curves with RSM PR.

## Files

```text
pr_cmaq_validation_scripts/
|-- README.md / README_en.md
|-- config_pr_validation.csh       # Dates, receptors, modes, factors and paths
|-- batch_run_pr_validation.csh    # Plan, execute and post-process
|-- generate_emissctrl.py          # NOx-control namelists
|-- render_cctm_segment.py         # Segment rendering
|-- post_pr_validation.py          # Assembly, daily statistics and summary
`-- .gitignore
```

Sibling `../lead-time_experiments/` supplies the September template, baseline namelist and `post_scripts/`. These are included in the shared package. External requirements include CMAQ/MPI, COMBINE, NCO, baseline UTC00 CGRID, meteorology/emissions/BC, and Python with NumPy, xarray, netCDF4 and their dependencies.

## Usage

Edit `config_pr_validation.csh`: `target_days`, `lead_days`, `target_regions`, `scan_modes`, `nox_factors` and input/output paths. Local changes target-city NOx only; Whole uses `EVERYWHERE`, the entire D3 domain. `D3-PRD` is a receptor excluding the nine cities, not the Whole control scope.

From this directory:

```bash
csh batch_run_pr_validation.csh --dry-run
csh batch_run_pr_validation.csh --run
csh batch_run_pr_validation.csh --post --manifest /path/to/generated/manifest.tsv
csh batch_run_pr_validation.csh --run-and-post
```

No arguments is equivalent to `--run` and executes the model. Dry-run only generates files; `--post` processes existing results. Start with one date, one receptor and a few factors by editing the configuration.

## Timing and Outputs

With `lead_days=0`, baseline preparation advances preceding-day UTC00 to UTC16; control segments continue to target-day UTC16, covering its CST calendar day. Earlier controls add intervening segments.

Execution creates `generated/` for namelists, scripts and a Tab-separated manifest. Raw data use `segment_root`; `post_root` receives COMBINE, extracted/daily NetCDF and `pr_validation_summary.csv`.

Compare receptor-mean O3 MDA8 (ppbv) curves using matching dates, receptors and spatial averaging. The sampled peak factor approximates PR. Expand the range if the peak occurs at an endpoint to determine whether an interior optimum exists.
