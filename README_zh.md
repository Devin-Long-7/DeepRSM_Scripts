# Daily DeepRSM

[English](README.md)

使用已训练的 Daily DeepRSM 模型，将 CMAQ 基准及区域置零日浓度转换为逐日响应面模型，计算臭氧 PR、VNr 和 EKMA，并与独立 CMAQ 情景进行 OOS 校验。示例对应 2022 年 9 月珠三角，臭氧单位为 ppb。

## 公开范围与许可证

公开发布内容包括已训练模型、预处理和 RSM 构建代码、PR/VNr/EKMA 诊断代码、校验代码、情景配置文件及处理后结果。训练脚本和训练流程不纳入公开发布。训练脚本可向通讯作者提出合理请求获取。加载已训练模型所需的网络结构定义保留在 `create_rsm_struct/`。

作者公开的软件代码、配套文档、情景配置及已训练模型权重采用 MIT License，见公开仓库中的 `LICENSE`。私下保留的训练脚本不属于本次公开许可的授权范围。处理后的数值输出数据采用 CC BY 4.0，见 `LICENSE-DATA`。第三方材料保留其适用的原许可和声明，仓库许可证不替代第三方条款。

## 快速开始

**只查看论文结果**：直接打开 `results/` 中的 PR CSV、EKMA Excel 和 OOS 散点表，无需运行模型。大型 CSV 已压缩为 `.csv.gz`，解压后即可读取，也可由 pandas 直接读取。

**运行随仓库提供的五日案例**：完成下方步骤 1–2 后，执行“五日案例”命令。案例直接使用已提供的 `.npy` 和模型，无需原始 CMAQ 文件或重新训练。

**复算完整月份结果**：依次执行步骤 1–6，需要另外准备未随仓库提供的大型原始 CMAQ 输入。下列命令使用 Linux shell。

### 1. 准备环境

克隆仓库并进入根目录：

```bash
git clone https://github.com/Devin-Long-7/DeepRSM_Scripts.git
cd DeepRSM_Scripts
export DEEPRSM_ROOT="$PWD"
export PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
PY_DL=python
PY_DATA=python
```

五日系数预测案例需要 Python 3.8 环境，以及 PyTorch 2.4.0、NumPy 1.24.4、pandas 2.0.3、netCDF4 1.7.1.post2、tqdm 和 pytz。例如：

```bash
conda create -n deeprsm-example python=3.8 -y
conda activate deeprsm-example
python -m pip install torch==2.4.0 numpy==1.24.4 pandas==2.0.3 netCDF4==1.7.1.post2 tqdm pytz
```

系数预测已测试 Python 3.8.19、PyTorch 2.4.0。完整预处理、PR 和校验已测试 Python 3.9.21；数据处理环境使用 NumPy 2.0.2、pandas 2.2.3、SciPy 1.13.1、Matplotlib 3.9.4、netCDF4 1.7.2、Cartopy 0.23.0、cmaps 2.0.1、scikit-learn 1.6.1 和 openpyxl 3.1.5。如使用两个独立环境，将 `PY_DL` 和 `PY_DATA` 分别设为对应环境的 Python 路径。两份原始 `esil` 版本分别保留在 `dependencies/dl/` 和 `dependencies/devin_env/`，通过下方 `PYTHONPATH` 选择。尚未验证全新环境安装。

### 2. 检查配置与输入

| 配置 | 用途 |
| --- | --- |
| `a_config_example_five_days.ini` | 随仓库提供的五日系数预测案例，无需原始 CMAQ 文件 |
| `a_config_d3_202209_M_devin_0605.ini` | 构建 RSM、计算 PR/EKMA、5 个 LHS 情景校验 |
| `a_config_d3_202209_M_devin_8_oos.ini` | 8 个指定情景校验，对应论文 OOS 散点数据 |

先使用 `0605.ini`：

```bash
CFG=a_config_d3_202209_M_devin_0605.ini
```

`[input_files]` 中所有相对路径均以 **INI 文件所在目录** 为基准解析，包括模型及输出路径。整体移动仓库无需修改这些路径。两份全月配置预期从 `inputs/CMAQ/create_rsm/`、`inputs/CMAQ/oos/` 读取原始 CMAQ 数据，这些目录未随仓库提供；运行预处理或独立校验时需自行放入数据或修改对应路径。

| 参数 | 需要的输入或输出 |
| --- | --- |
| `aconc_dir` | CMAQ 基准、全域置零及各区域置零的日浓度 NetCDF，未打包 |
| `oos_aconc_dir` | 独立校验情景的日浓度 NetCDF，仅校验步骤需要，未打包 |
| `trained_model_file` | `inputs/Trained_model/2022_Sep_Fine-tuned_DeepRSM_model_O3.pth` |
| `matrix_file` | `inputs/Matrix_for_CreateRSM_D2_2022_deeprsm.csv` |
| `oos_matrix_file` | LHS 配置用 `Matrix_for_OOS_D2_2022_final_city.csv`，8 情景配置用 `Matrix_for_OOS_8_Specified_Runs.csv`，均在 `inputs/` |
| `receptor_file_txt` / `region_file_csv` | `inputs/d3_117150_prd_grid_receptor.txt` / `.csv` |
| `grid_path` | `inputs/d3_117150_prd_grid.npy` |
| `boundary_file` / `boundary_json_file` | `inputs/guangdong_cities.json`，同目录保留 `PRD_Cities_117_150.pkl` |
| `output_dir` | 本次计算的输出根目录，结果写入其下的 `project_name` 子目录 |

新计算结果写入 `outputs/<project_name>/`，随仓库发布的论文结果保留在 `results/`。可在 INI 中修改 `output_dir`。重复运行同一配置会替换该运行目录下的同名输出。

保留原配置中的物种顺序、区域顺序、文件前后缀和单位。原建模输入名形如 `D3_base_Daily_ACONC_Sep_2022.nc`，LHS 校验名形如 `D3_oos1_Daily_ACONC_Sep_2022.nc`，8 情景校验前缀为 `D3_S`；文件名必须与配置及矩阵情景对应。模型输入为 18 个物种的基准及置零浓度，共 36 通道。

### 运行随仓库提供的五日案例

完成环境设置后，在仓库根目录执行：

```bash
export PYTHONPATH="$DEEPRSM_ROOT/dependencies/dl"
"$PY_DL" -B d_get_equation_item_weight.py --config a_config_example_five_days.ini
```

无需复制输入或修改路径。配置直接读取 `inputs/Example_data/2022_Sep_target_days/`，预测 2022 年 9 月 6、13、14、16、19 日的系数，在 `outputs/example_2022_09_five_days/rsm_weights/` 生成 55 个 `*Weight_M9_D*.npy` 文件（5 日 × 11 区域）及 5 个间接项缓存。此案例用于构建 RSM 系数；与独立 CMAQ 情景进行校验仍需要额外的 NetCDF 输入。

该案例已在 Linux 的独立副本中实测，并从副本目录外启动。生成的 55 个系数数组及 5 个间接项缓存均与已有论文复算输出逐数组完全一致，最大绝对差为 0。

### 3. 预处理 CMAQ 输入（完整月份）

```bash
export PYTHONPATH="$DEEPRSM_ROOT/dependencies/devin_env"
"$PY_DATA" -B c_data_preprocess.py --config "$CFG"
```

输出到 `outputs/<project_name>/preprocess_npy_data/`。本示例全月生成 390 个 `.npy` 文件。运行随仓库提供的五日案例时跳过此步骤。

### 4. 使用已训练权重构建 RSM

```bash
export PYTHONPATH="$DEEPRSM_ROOT/dependencies/dl"
"$PY_DL" -B d_get_equation_item_weight.py --config "$CFG"
```

输出到 `outputs/<project_name>/rsm_weights/`。全月配置应生成 30 天 × 11 区域，共 330 个 `*Weight_M9_D*.npy` 系数文件，另有间接项缓存。脚本在 CPU 上执行系数预测，不要求 GPU。可选参数 `prediction_days` 用于选择日期；未设置时处理配置月份的全部日期。

### 5. 计算 PR、VNr 和 EKMA

```bash
export PYTHONPATH="$DEEPRSM_ROOT/dependencies/devin_env"
"$PY_DATA" -B g_rsm_vnr_pr.py --config "$CFG"
```

该入口计算 9 月 6、13、14、16、19 日，并生成：

- `outputs/<project_name>/<project_name>_PR_O3_Max_Sep_MRSM_20260506.csv`：45 个城市日的 Local/Whole PR、臭氧峰值和 VNr。
- `outputs/<project_name>/oos/ekma_curve/<project_name>_ekma_curve_data.xlsx`：每日 49 个 NOx/VOC 组合的臭氧浓度。
- 同目录及项目根目录下的 EKMA 图与 PR 热图。

PR 与 VNr 无量纲，臭氧峰值及 EKMA 浓度单位为 ppb。PR 搜索范围为 0.01 至 2。

### 6. 校验 RSM 与 CMAQ

```bash
export PYTHONPATH="$DEEPRSM_ROOT/dependencies/devin_env"
"$PY_DATA" -B f_rsm_performance.py --config "$CFG"
```

输出到 `outputs/<project_name>/oos/`，包括全月 `All Days_scatter_data_PRD.csv`、五日 `All Polluted Days_scatter_data_PRD.csv`、统计汇总及图件，文件名均带有 `<project_name>_` 前缀。散点表按 `Day, Run, Column, Row` 标识样本，数值列为 `CMAQ, RSM, CMAQ_Response, RSM_Response`。

**复算论文的 8 情景校验**：将 `CFG` 换为下列配置，然后重复步骤 3、4、6。两份配置的 `project_name` 不同，分别输出到不同子目录。

```bash
CFG=a_config_d3_202209_M_devin_8_oos.ini
```

完整 8 情景全月表应有 1,493,040 行。五日子集的响应 Pearson 相关系数平方约为 0.935919，RMSE 约为 0.525883 ppb。5 个 LHS 情景全月表应有 933,150 行，其对应指标约为 0.888092 和 1.543591 ppb。

### 五日案例数据

`inputs/Example_data/2022_Sep_target_days/` 包含 65 个预处理 `.npy` 数组：5 个目标日各包含 1 个基准和 12 个置零场，每个场含 18 个物种。案例 INI 通过 `preprocess_npy_dir` 直接指定该输入目录，通过 `prediction_days` 选择五个日期。建模入口仅增加输入路径和日期选择支持，网络及系数计算方法保持原样。

## 目录结构

```text
DeepRSM_Scripts/
|-- README.md / README_zh.md
|-- LICENSE                        # MIT：公开代码和已训练权重
|-- LICENSE-DATA                   # CC BY 4.0：处理后数值输出
|-- a_config_d3_202209_M_devin_0605.ini
|-- a_config_d3_202209_M_devin_8_oos.ini
|-- a_config_example_five_days.ini  # 随仓库提供的案例
|-- b_input_data_helper.py          # 配置及输入读取
|-- c_data_preprocess.py            # 预处理
|-- d_get_equation_item_weight.py   # CNN 预测 RSM 系数
|-- e_rsm_helper.py                # RSM 方程与统计
|-- f_rsm_performance.py            # OOS 校验
|-- g_rsm_vnr_pr.py                 # PR、VNr、EKMA
|-- run_pipeline.py                # 原批处理入口
|-- create_rsm_struct/             # 建模网络与数据类
|-- dependencies/
|   |-- dl/esil/                   # 原始推理依赖
|   `-- devin_env/esil/            # 原始预处理及诊断依赖
|-- inputs/
|   |-- Trained_model/             # 三个公开 O3 模型权重
|   |-- Example_data/              # 五个目标日的预处理数组
|   `-- Matrix_for_Training_Run1-21.csv
|-- results/                       # 随仓库发布的论文诊断结果
`-- outputs/                       # 运行后生成，不纳入 Git
```

## 常见问题

- **缺少 NetCDF 文件**：本目录包含权重和处理后结果，不包含大型原始 CMAQ 数据。重新计算前需取得数据并设置 INI 路径。
- **`No module named esil`**：检查 `PYTHONPATH`，并按步骤切换至当前 Python 环境对应的依赖副本。
- **结果写到了意外位置**：显式传入 `--config`。相对路径以 INI 所在目录为基准；未传配置时使用仓库内的 `0605.ini`。
- **全月汇总变成五日汇总**：原校验入口会覆盖同名汇总文件；全月分析使用 `All Days` 散点表，五日分析使用 `All Polluted Days`。
- **响应偏差符号与 SI 不同**：散点表响应采用“基准减情景”，SI 的有符号偏差和截距采用“情景减基准”，比较时需统一符号。

大型原始 WRF-CMAQ 输出因文件体积较大，可向通讯作者提出合理请求获取。公开仓库为 https://github.com/Devin-Long-7/DeepRSM_Scripts，目前尚未分配 Zenodo 存档 DOI。
