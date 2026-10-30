# Daily DeepRSM

[中文](README_zh.md)

Use the trained Daily DeepRSM model to build daily response surfaces from baseline and regional zero-out CMAQ concentrations, calculate ozone PR, VNr and EKMA diagnostics, and validate predictions against independent CMAQ scenarios. The example covers the Pearl River Delta in September 2022. Ozone concentrations are in ppb.

## Public Release And License

The public release includes the trained model, preprocessing and RSM construction code, PR/VNr/EKMA diagnostic code, validation code, scenario configuration files and processed outputs. Training scripts and the training workflow are not included in the public release. The network definition needed to load the trained model is included in `create_rsm_struct/`.

The MIT License applies to the authors' released software, accompanying documentation, scenario configurations and trained model checkpoint; see `LICENSE` in the public repository. Training scripts retained privately are outside this public license grant. Processed numerical output data are provided under CC BY 4.0; see `LICENSE-DATA`. Third-party material retains its applicable original terms and notices; the repository license does not override those terms.

## Quick Start

**To inspect the study results**, open the PR CSV, EKMA workbook and OOS scatter tables in `results/`. No model execution is required. Large CSVs use `.csv.gz` compression; decompress them or read them directly with pandas.

**To recalculate results**, follow: environment setup → input configuration → preprocessing → RSM construction → PR or validation. Use the trained checkpoint in `inputs/`; no training is required. The commands below target the original Linux server. Large CMAQ inputs are not included in the public package.

### 1. Set Up The Environment

On the study server, enter the tested copy:

```bash
cd /DeepLearning/mnt/Devin/publication_exports/DeepRSM_original_scripts_20261029
export DEEPRSM_ROOT="$PWD"
export PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
PY_DL=/home/esil/anaconda3/envs/dl/bin/python
PY_DATA=/home/esil/anaconda3/envs/devin_env/bin/python
```

Coefficient prediction uses `dl`, tested with Python 3.8.19 and PyTorch 2.4.0. Preprocessing, PR and validation use `devin_env`, tested with Python 3.9.21. Main dependencies are NumPy, pandas, SciPy, netCDF4, Matplotlib, Cartopy, cmaps, scikit-learn, openpyxl and the bundled copies of `esil`.

Exact versions are recorded in `tests/environment_dl.txt` and `tests/environment_devin_env.txt`. On another machine, prepare equivalent environments and replace the two Python paths above. Execution has been verified in the existing study environments; installation into fresh environments has not been tested.

### 2. Configure Inputs

| Configuration | Purpose |
| --- | --- |
| `a_config_d3_202209_M_devin_0605.ini` | RSM construction, PR/EKMA and five LHS validation scenarios |
| `a_config_d3_202209_M_devin_8_oos.ini` | Eight specified validation scenarios used in the study OOS scatter table |

Start with:

```bash
CFG=a_config_d3_202209_M_devin_0605.ini
```

Check `[input_files]` in the INI. **Update paths when moving the package to another machine or directory. The tested server copy already has its paths configured.**

| Parameter | Required input or output |
| --- | --- |
| `aconc_dir` | Daily CMAQ baseline, whole-domain zero-out and regional zero-out NetCDF files; not bundled |
| `oos_aconc_dir` | Daily independent CMAQ validation scenarios; needed only for validation, not bundled |
| `trained_model_file` | `inputs/2022Sep_subregion_Model_14710_O3_Final.pth` |
| `matrix_file` | `inputs/Matrix_for_CreateRSM_D2_2022_deeprsm.csv` |
| `oos_matrix_file` | `Matrix_for_OOS_D2_2022_final_city.csv` for LHS, or `Matrix_for_OOS_8_Specified_Runs.csv` for eight scenarios; both in `inputs/` |
| `receptor_file_txt` / `region_file_csv` | `inputs/d3_117150_prd_grid_receptor.txt` / `.csv` |
| `grid_path` | `inputs/d3_117150_prd_grid.npy` |
| `boundary_file` / `boundary_json_file` | `inputs/guangdong_cities.json`; keep `PRD_Cities_117_150.pkl` beside it |
| `output_dir` | Output root; files are written under its `project_name` subdirectory |

To preserve existing generated results, set `output_dir` in the copied INI to a new run directory before executing. Substitute that directory for `results/` in the output paths below.

Retain the original species order, region order, filename patterns and units. Construction files include names such as `D3_base_Daily_ACONC_Sep_2022.nc`; LHS files use names such as `D3_oos1_Daily_ACONC_Sep_2022.nc`; eight-scenario files use the `D3_S` prefix. Names must match the INI and scenario matrices. Network inputs contain baseline and zero-out concentrations for 18 species, giving 36 channels.

### 3. Preprocess CMAQ Inputs

```bash
export PYTHONPATH="$DEEPRSM_ROOT/tests/dependencies_devin_env"
"$PY_DATA" -B c_data_preprocess.py --config "$CFG"
```

Outputs go to `results/<project_name>/preprocess_npy_data/`. The full-month example produces 390 `.npy` files.

### 4. Build RSMs With The Trained Checkpoint

```bash
export PYTHONPATH="$DEEPRSM_ROOT/tests/dependencies_dl"
"$PY_DL" -B d_get_equation_item_weight.py --config "$CFG"
```

Outputs go to `results/<project_name>/rsm_weights/`. Expect 330 `*Weight_M9_D*.npy` coefficient files: 30 days times 11 regions, plus indirect-term caches. The original prediction script uses the CPU; this step does not require a GPU.

### 5. Calculate PR, VNr And EKMA

```bash
export PYTHONPATH="$DEEPRSM_ROOT/tests/dependencies_devin_env"
"$PY_DATA" -B g_rsm_vnr_pr.py --config "$CFG"
```

This entry point processes 6, 13, 14, 16 and 19 September and produces:

- `results/<project_name>/<project_name>_PR_O3_Max_Sep_MRSM_20260506.csv`: Local/Whole PR, peak ozone and VNr for 45 city-days.
- `results/<project_name>/oos/ekma_curve/<project_name>_ekma_curve_data.xlsx`: ozone concentrations for 49 NOx/VOC combinations per day.
- EKMA figures and PR heatmaps in the EKMA folder and project output directory.

PR and VNr are dimensionless; peak ozone and EKMA concentrations are in ppb. The PR search interval is 0.01 to 2.

### 6. Validate Against CMAQ

```bash
export PYTHONPATH="$DEEPRSM_ROOT/tests/dependencies_devin_env"
"$PY_DATA" -B f_rsm_performance.py --config "$CFG"
```

Outputs go to `results/<project_name>/oos/`, including `All Days_scatter_data_PRD.csv`, `All Polluted Days_scatter_data_PRD.csv`, summaries and figures. Filenames have the `<project_name>_` prefix. Scatter rows are identified by `Day, Run, Column, Row`; numerical columns are `CMAQ, RSM, CMAQ_Response, RSM_Response`.

**To reproduce the study's eight-scenario validation**, switch the configuration below and repeat steps 3, 4 and 6. The configurations use different `project_name` values and separate output subdirectories.

```bash
CFG=a_config_d3_202209_M_devin_8_oos.ini
```

The complete eight-scenario monthly table contains 1,493,040 rows. Its five-day response subset gives squared Pearson correlation approximately 0.935919 and RMSE 0.525883 ppb. The five LHS scenarios contain 933,150 monthly rows, with corresponding metrics of approximately 0.888092 and 1.543591 ppb.

## Directory Structure

```text
DeepRSM_original_scripts_20261029/
|-- README.md / README_zh.md
|-- LICENSE                        # MIT: released software and trained checkpoint
|-- LICENSE-DATA                   # CC BY 4.0: processed numerical outputs
|-- a_config_d3_202209_M_devin_0605.ini
|-- a_config_d3_202209_M_devin_8_oos.ini
|-- b_input_data_helper.py          # Configuration and input loading
|-- c_data_preprocess.py            # Preprocessing
|-- d_get_equation_item_weight.py   # CNN prediction of RSM coefficients
|-- e_rsm_helper.py                # RSM equations and statistics
|-- f_rsm_performance.py            # OOS validation
|-- g_rsm_vnr_pr.py                 # PR, VNr and EKMA
|-- run_pipeline.py                # Original batch entry point
|-- create_rsm_struct/             # Prediction network and data classes
|-- inputs/                        # Checkpoint, matrices, grid, boundaries and masks
|-- results/                       # Bundled diagnostics and new execution outputs
|-- tests/                         # Environments, esil copies, logs and reference data
`-- docs/                          # Verification and source provenance
```

## Troubleshooting

- **Missing NetCDF inputs:** the package includes the checkpoint and processed outputs, but not large raw CMAQ data. Obtain the inputs and configure their paths before recalculating.
- **`No module named esil`:** check `PYTHONPATH` and select the dependency copy corresponding to the current Python environment.
- **Outputs in an unexpected directory:** always pass `--config` to modeling, PR and validation scripts. The original default configuration still points to the historical project.
- **Monthly summary replaced by a five-day summary:** the original entry point overwrites the summary filenames. Use `All Days` scatter data for monthly analysis and `All Polluted Days` for the five-day subset.
- **Signed bias differs from SI:** scatter responses use baseline minus scenario; the SI signed bias and intercept use scenario minus baseline. Align the conventions before comparing.

Execution results and numerical comparisons are documented in the [verification record](docs/VERIFICATION.md). Large raw WRF-CMAQ output files are available from the corresponding author upon reasonable request due to their size. The public repository is https://github.com/Devin-Long-7/DeepRSM_Scripts. A Zenodo archival DOI has not yet been assigned.
