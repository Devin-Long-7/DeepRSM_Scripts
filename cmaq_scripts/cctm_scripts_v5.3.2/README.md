# CMAQ v5.3.2 常规连续运行

[English](README_en.md)

本目录提供完整的 CMAQ v5.3.2 配置、脚本生成、校验、运行及后处理流程，默认 `IC_RB_MODE=N`，不启用 IC-RB 每日初始场重置。首次起跑使用配置的 ICON，后续日期接续本情景上一日的 CGRID。

## 两套代码如何选择

| 目录 | 默认模式 | 初始场处理 |
|---|---|---|
| `cctm_scripts_v5.3.2/`（本目录） | `IC_RB_MODE=N` | 常规连续运行，保留本情景的跨日状态 |
| [`IC-RB-UTC00_scripts/`](../IC-RB-UTC00_scripts/README.md) | `IC_RB_MODE=Y` | 每日 UTC00 从配置的 baseline CGRID 重新初始化 |

UTC00 对应 CST08。两目录的程序结构相近，但分别保留完整代码和默认配置，便于区分连续实验与每日重置实验。各目录使用各自的配置、模板和运行管理器；修改一套不会自动同步另一套。

## 文件与职责

```text
cctm_scripts_v5.3.2/
|-- README.md / README_en.md
|-- batch_run_cases.csh             # 情景名或配置文件批处理
|-- cctm_config.csh                 # 默认连续运行配置，IC_RB_MODE=N
|-- cctm_config_D3_150X117_202209.csh # 九月连续运行配置，含前期起跑日期
|-- cctm_config_D3_150X117_202209_IC-RB_base_on_cgrid.csh # 每日重置备选配置
|-- run_manager.csh                 # 生成、校验、执行和可选后处理
|-- run_cctm_template.csh            # CMAQ 运行模板
|-- validate_script.csh             # 文件与脚本检查
|-- create_emissCtrl_nml.py          # 从模板和 CSV 生成 NML
|-- EmissCtrl_nml/                  # 已有情景 NML，见内附说明
`-- nml_config/
    |-- EmissCtrl_base.nml          # NML 生成模板
    |-- scaling_rules.csv          # 情景缩放规则
    `-- stream_families.csv        # 排放流与化学家族映射
```

`EmissCtrl_nml/` 同时供其他模块按相对路径引用；本目录也包含独立的完整 CCTM 运行流程。运行时生成的 `generated/` 不属于预置输入。

## 快速上手

1. 准备 CMAQ v5.3.2、匹配的 MPI/编译器运行环境、气象、排放、ICON、BCON 和区域掩膜；后处理另需 COMBINE、NCO 及相应 Python 环境，见[后处理说明](../post_scripts_v5.3.2/README.md)。
2. 在工作副本的 `cctm_config.csh` 核对模型、输入、输出、`NML_PATH` 和后处理路径。默认 D3、2022-08-27 至 2022-09-30、32 个进程、`IC_RB_MODE=N`，浓度及后处理取地面层。日期以所选配置为准；单独分析正式时段时设置 `POST_BEGIN_DATE`、`POST_END_DATE`。
3. `GENERATE_NML=N` 默认读取已有 `NML_PATH`，该路径保留原部署绝对路径，需按实际位置配置；`GENERATE_NML=Y` 则由生成器读取本目录 `nml_config/` 中三个文件。选择的情景必须有对应 NML 或 CSV 规则。
4. 进入本目录，先生成并检查默认基准情景的脚本：

```bash
cd /path/to/cmaq_scripts/cctm_scripts_v5.3.2
csh run_manager.csh cctm_config.csh --dry-run
# 核对生成脚本、输入和输出位置后正式运行
csh run_manager.csh cctm_config.csh
```

dry-run 会写入 `generated/` 并检查脚本，仍可能要求真实输入存在，不执行 CMAQ 或后处理。配置文件是位置参数，不使用 `--config`。

按情景名批量运行时：

```bash
csh batch_run_cases.csh oos3 --dry-run
csh batch_run_cases.csh oos3
```

批处理无参数默认选择 `oos3`，沿用 `cctm_config.csh` 并覆盖情景名/类型；它与直接调用管理器的默认 `base` 情景不同。备选 `*_IC-RB_base_on_cgrid.csh` 会启用 `Y`；每日重置实验建议使用相邻的 `IC-RB-UTC00_scripts/`，避免混淆默认流程。

## 输出与检查

生成脚本、可选新 NML 和日志位于 `generated/`；模型输出位于 `OUTDIR_BASE/情景/域/年/月/`，后处理输出按 `COMBINE_DIR` 配置。运行后核对退出状态、CCTM/COMBINE 日志、CGRID 续跑链及 NetCDF 时间、网格、变量和单位。

两套实验应分别设置 `OUTDIR_BASE` 和 `COMBINE_DIR`，避免相同情景名写入同一路径。后处理的 `BASELINE_FILE` 应匹配实际层数、文件名和日期；`CLEANUP_CCTM_OUTPUT=T` 默认会清理部分原始输出，首次检查可在工作副本设为 F。不要直接把单个 UTC 日当作 CST 自然日统计。
