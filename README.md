# Daily DeepRSM

[中文](README_zh.md)

Use the trained Daily DeepRSM model to build daily response surfaces from baseline and regional zero-out CMAQ concentrations, calculate ozone PR, VNr and EKMA diagnostics, and validate predictions against independent CMAQ scenarios. The example covers the Pearl River Delta in September 2022. Ozone concentrations are in ppb.

## Public Release And License

The public release includes the trained model, preprocessing and RSM construction code, PR/VNr/EKMA diagnostic code, validation code, scenario configuration files and processed outputs. Training scripts and the training workflow are not included in the public release. The training scripts are available from the corresponding author upon reasonable request. The network definition needed to load the trained model is included in `create_rsm_struct/`.

The MIT License applies to the authors' released software, accompanying documentation, scenario configurations and trained model checkpoint; see `LICENSE` in the public repository. Training scripts retained privately are outside this public license grant. Processed numerical output data are provided under CC BY 4.0; see `LICENSE-DATA`. Third-party material retains its applicable original terms and notices; the repository license does not override those terms.

## Quick Start

**To inspect the study results**, open the PR CSV, EKMA workbook and OOS scatter tables in `results/`. No model execution is required. Large CSVs use `.csv.gz` compression; decompress them or read them directly with pandas.

**To run the bundled five-day example**, follow steps 1–2 below and the five-day command after step 2. It uses the supplied `.npy` inputs and checkpoint, without raw CMAQ files or training.

**To recalculate the full-month results**, follow steps 1–6. Large raw CMAQ inputs are not included and must be supplied separately. Commands below use a Linux shell.

### 1. Set Up The Environment

Clone the repository and enter its root directory:

```bash
git clone https://github.com/Devin-Long-7/DeepRSM_Scripts.git
cd DeepRSM_Scripts
export DEEPRSM_ROOT="$PWD"
export PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
PY_DL=python
PY_DATA=python
```

For the coefficient-prediction example, prepare a Python 3.8 environment with PyTorch 2.4.0, NumPy 1.24.4, pandas 2.0.3, netCDF4 1.7.1.post2, tqdm and pytz. For example:

```bash
conda create -n deeprsm-example python=3.8 -y
conda activate deeprsm-example
python -m pip install torch==2.4.0 numpy==1.24.4 pandas==2.0.3 netCDF4==1.7.1.post2 tqdm pytz
```

Coefficient prediction was tested with Python 3.8.19 and PyTorch 2.4.0. Full preprocessing, PR and validation were tested with Python 3.9.21. The versions used for the data-processing environment were NumPy 2.0.2, pandas 2.2.3, SciPy 1.13.1, Matplotlib 3.9.4, netCDF4 1.7.2, Cartopy 0.23.0, cmaps 2.0.1, scikit-learn 1.6.1 and openpyxl 3.1.5. Set `PY_DL` and `PY_DATA` to the Python executables for these environments when using separate environments. The two original `esil` versions are retained under `dependencies/dl/` and `dependencies/devin_env/`, selected through `PYTHONPATH` below. Installation into a fresh environment has not been tested.

### 2. Configure Inputs

| Configuration | Purpose |
| --- | --- |
| `a_config_example_five_days.ini` | Bundled five-day coefficient-prediction example; no raw CMAQ files required |
| `a_config_d3_202209_M_devin_0605.ini` | RSM construction, PR/EKMA and five LHS validation scenarios |
| `a_config_d3_202209_M_devin_8_oos.ini` | Eight specified validation scenarios used in the study OOS scatter table |

Start with:

```bash
CFG=a_config_d3_202209_M_devin_0605.ini
```

All `[input_files]` paths are resolved relative to the INI file, including the checkpoint and output directory. Moving the repository does not require editing these paths. The two full-month configurations expect raw CMAQ files in `inputs/CMAQ/create_rsm/` and `inputs/CMAQ/oos/`; these directories are not bundled. Set those paths to your own data when running preprocessing or validation.

| Parameter | Required input or output |
| --- | --- |
| `aconc_dir` | Daily CMAQ baseline, whole-domain zero-out and regional zero-out NetCDF files; not bundled |
| `oos_aconc_dir` | Daily independent CMAQ validation scenarios; needed only for validation, not bundled |
| `trained_model_file` | `inputs/Trained_model/2022_Sep_Fine-tuned_DeepRSM_model_O3.pth` |
| `matrix_file` | `inputs/Matrix_for_CreateRSM_D2_2022_deeprsm.csv` |
| `oos_matrix_file` | `Matrix_for_OOS_D2_2022_final_city.csv` for LHS, or `Matrix_for_OOS_8_Specified_Runs.csv` for eight scenarios; both in `inputs/` |
| `receptor_file_txt` / `region_file_csv` | `inputs/d3_117150_prd_grid_receptor.txt` / `.csv` |
| `grid_path` | `inputs/d3_117150_prd_grid.npy` |
| `boundary_file` / `boundary_json_file` | `inputs/guangdong_cities.json`; keep `PRD_Cities_117_150.pkl` beside it |
| `output_dir` | Output root; files are written under its `project_name` subdirectory |

New runs write to `outputs/<project_name>/`; bundled study outputs remain in `results/`. Set `output_dir` in the INI to another directory when needed. Repeating the same run replaces files under that run's output directory.

Retain the original species order, region order, filename patterns and units. Construction files include names such as `D3_base_Daily_ACONC_Sep_2022.nc`; LHS files use names such as `D3_oos1_Daily_ACONC_Sep_2022.nc`; eight-scenario files use the `D3_S` prefix. Names must match the INI and scenario matrices. Network inputs contain baseline and zero-out concentrations for 18 species, giving 36 channels.

### Run The Bundled Five-Day Example

After environment setup, run from the repository root:

```bash
export PYTHONPATH="$DEEPRSM_ROOT/dependencies/dl"
"$PY_DL" -B d_get_equation_item_weight.py --config a_config_example_five_days.ini
```

No input copying or path editing is needed. The configuration reads `inputs/Example_data/2022_Sep_target_days/` and predicts coefficients for 6, 13, 14, 16 and 19 September 2022. It generates 55 `*Weight_M9_D*.npy` files (5 days × 11 regions) and 5 indirect-term caches in `outputs/example_2022_09_five_days/rsm_weights/`. This example builds RSM coefficients; validation against independent CMAQ simulations requires the additional NetCDF inputs.

The example was tested on Linux in a separate package directory, launched from outside that directory. All 55 coefficient arrays and 5 indirect-term caches were exactly equal to the existing study reproduction outputs (maximum absolute difference: 0).

### 3. Preprocess CMAQ Inputs (Full Month)

```bash
export PYTHONPATH="$DEEPRSM_ROOT/dependencies/devin_env"
"$PY_DATA" -B c_data_preprocess.py --config "$CFG"
```

Outputs go to `outputs/<project_name>/preprocess_npy_data/`. The full-month example produces 390 `.npy` files. Skip this step for the bundled five-day example.

### 4. Build RSMs With The Trained Checkpoint

```bash
export PYTHONPATH="$DEEPRSM_ROOT/dependencies/dl"
"$PY_DL" -B d_get_equation_item_weight.py --config "$CFG"
```

Outputs go to `outputs/<project_name>/rsm_weights/`. The full-month configurations generate 330 `*Weight_M9_D*.npy` coefficient files: 30 days times 11 regions, plus indirect-term caches. The prediction script uses the CPU; this step does not require a GPU. Optional `prediction_days` selects specific dates; omitting it uses all days in the configured month.

### 5. Calculate PR, VNr And EKMA

```bash
export PYTHONPATH="$DEEPRSM_ROOT/dependencies/devin_env"
"$PY_DATA" -B g_rsm_vnr_pr.py --config "$CFG"
```

This entry point processes 6, 13, 14, 16 and 19 September and produces:

- `outputs/<project_name>/<project_name>_PR_O3_Max_Sep_MRSM_20260506.csv`: Local/Whole PR, peak ozone and VNr for 45 city-days.
- `outputs/<project_name>/oos/ekma_curve/<project_name>_ekma_curve_data.xlsx`: ozone concentrations for 49 NOx/VOC combinations per day.
- EKMA figures and PR heatmaps in the EKMA folder and project output directory.

PR and VNr are dimensionless; peak ozone and EKMA concentrations are in ppb. The PR search interval is 0.01 to 2.

### 6. Validate Against CMAQ

```bash
export PYTHONPATH="$DEEPRSM_ROOT/dependencies/devin_env"
"$PY_DATA" -B f_rsm_performance.py --config "$CFG"
```

Outputs go to `outputs/<project_name>/oos/`, including `All Days_scatter_data_PRD.csv`, `All Polluted Days_scatter_data_PRD.csv`, summaries and figures. Filenames have the `<project_name>_` prefix. Scatter rows are identified by `Day, Run, Column, Row`; numerical columns are `CMAQ, RSM, CMAQ_Response, RSM_Response`.

**To reproduce the study's eight-scenario validation**, switch the configuration below and repeat steps 3, 4 and 6. The configurations use different `project_name` values and separate output subdirectories.

```bash
CFG=a_config_d3_202209_M_devin_8_oos.ini
```

The complete eight-scenario monthly table contains 1,493,040 rows. Its five-day response subset gives squared Pearson correlation approximately 0.935919 and RMSE 0.525883 ppb. The five LHS scenarios contain 933,150 monthly rows, with corresponding metrics of approximately 0.888092 and 1.543591 ppb.

### Example Five-Day Model Inputs

`inputs/Example_data/2022_Sep_target_days/` contains 65 preprocessed `.npy` arrays: one baseline and 12 zero-out fields for each of five days, with 18 species per field. The example INI reads this directory directly through `preprocess_npy_dir` and selects the five dates through `prediction_days`. The only modeling entry changes are configurable input paths and date selection; the network and coefficient calculations are unchanged.

## Directory Structure

```text
DeepRSM_Scripts/
|-- README.md / README_zh.md
|-- LICENSE                        # MIT: released software and trained checkpoint
|-- LICENSE-DATA                   # CC BY 4.0: processed numerical outputs
|-- a_config_d3_202209_M_devin_0605.ini
|-- a_config_d3_202209_M_devin_8_oos.ini
|-- a_config_example_five_days.ini  # Bundled example
|-- b_input_data_helper.py          # Configuration and input loading
|-- c_data_preprocess.py            # Preprocessing
|-- d_get_equation_item_weight.py   # CNN prediction of RSM coefficients
|-- e_rsm_helper.py                # RSM equations and statistics
|-- f_rsm_performance.py            # OOS validation
|-- g_rsm_vnr_pr.py                 # PR, VNr and EKMA
|-- run_pipeline.py                # Original batch entry point
|-- create_rsm_struct/             # Prediction network and data classes
|-- dependencies/
|   |-- dl/esil/                   # Original inference dependency
|   `-- devin_env/esil/            # Original preprocessing and diagnostics dependency
|-- inputs/
|   |-- Trained_model/            # Three released O3 checkpoints
|   |-- Example_data/              # Five target-day preprocessed arrays
|   `-- Matrix_for_Training_Run1-21.csv
|-- results/                       # Bundled study diagnostics
`-- outputs/                       # Generated on execution; excluded from Git
```

## Troubleshooting

- **Missing NetCDF inputs:** the package includes the checkpoint and processed outputs, but not large raw CMAQ data. Obtain the inputs and configure their paths before recalculating.
- **`No module named esil`:** check `PYTHONPATH` and select the dependency copy corresponding to the current Python environment.
- **Outputs in an unexpected directory:** pass `--config` explicitly. Relative paths resolve against the INI directory; without `--config`, the bundled `0605.ini` is used.
- **Monthly summary replaced by a five-day summary:** the original entry point overwrites the summary filenames. Use `All Days` scatter data for monthly analysis and `All Polluted Days` for the five-day subset.
- **Signed bias differs from SI:** scatter responses use baseline minus scenario; the SI signed bias and intercept use scenario minus baseline. Align the conventions before comparing.

Large raw WRF-CMAQ output files are available from the corresponding author upon reasonable request due to their size. The public repository is https://github.com/Devin-Long-7/DeepRSM_Scripts. A Zenodo archival DOI has not yet been assigned.
