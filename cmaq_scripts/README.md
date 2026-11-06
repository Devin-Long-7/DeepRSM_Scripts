# CMAQ 实验脚本

[English](README_en.md)

本目录汇集 CMAQ v5.3.2 情景运行、初始条件重置、ISAM、历史贡献分析及后处理脚本。各模块保留原有配置方式；使用前应在工作副本配置外部模型、输入与输出路径。

## 目录与入口

以下模块位于仓库的 `cmaq_scripts/` 目录下。使用时保留各子目录的同级关系，以维持脚本中的相对依赖。

| 目录 | 用途与使用说明 |
|---|---|
| `IC-RB-UTC00_scripts/` | [UTC00 起跑的初始条件重置与情景运行](IC-RB-UTC00_scripts/README.md) |
| `IC-RB-CST00_scripts/` | [北京时间零点起跑与两段拼接](IC-RB-CST00_scripts/README.md) |
| `IC-RB-UTC00_isam_scripts/` | [UTC00 起跑的 ISAM 运行](IC-RB-UTC00_isam_scripts/README.md) |
| `IC-RB-CST00_isam_scripts/` | [CST00 起跑的 ISAM 运行](IC-RB-CST00_isam_scripts/README_ISAM_CST00.md) |
| `carryover_species_experiments/` | [按初始场物种组划分的 carryover 实验](carryover_species_experiments/README.md) |
| `lead-time_experiments/` | [不同提前减排时长的实验](lead-time_experiments/README.md) |
| `pr_cmaq_validation_scripts/` | [PR 情景的 CMAQ 校验运行及后处理](pr_cmaq_validation_scripts/README.md) |
| `shapley_attribution_scripts/` | [四格实验与 Shapley 同日/历史贡献计算](shapley_attribution_scripts/README.md) |
| `cctm_scripts_v5.3.2/` | [默认 IC_RB_MODE=N 的完整连续运行流程及共享 NML](cctm_scripts_v5.3.2/README.md) |
| `post_scripts_v5.3.2/` | [COMBINE、变量筛选、日统计与绘图](post_scripts_v5.3.2/README.md) |

## 开始使用

1. 按研究目的选择上表中的模块，阅读对应中英文说明中的文件结构和运行命令。
2. 准备外部 CMAQ v5.3.2、匹配的化学机理与网格、MPI/编译器运行环境、MCIP、排放、ICON/BCON、基准 CGRID/ACONC 及区域掩膜。具体需求以模块配置为准，目录不含这些大体积输入。
3. 在独立工作副本中修改模块配置里的路径、日期、情景、输出位置和清理开关，再按模块入口运行；有 `--dry-run` 的入口可先检查计划，但 dry-run 仍可能要求真实输入存在。
4. 核对每个任务的退出状态、CCTM/COMBINE 日志及输出时间、网格和变量，确认各日任务的运行结果。

UTC00 对应 CST08；CST00 对应前一 UTC 日16时，跨 UTC 日数据必须按模块要求拼接。不要将不同起跑时刻的结果混为同一天。

## 共享依赖与当前限制

`cctm_scripts_v5.3.2/` 和 `IC-RB-UTC00_scripts/` 分别保留完整运行代码，前者默认 `IC_RB_MODE=N`，用于常规连续运行；后者默认 `IC_RB_MODE=Y`，用于 UTC00 每日初始场重置。两套代码结构相近，分别保留便于选择实验，配置和修改不会自动同步。`cctm_scripts_v5.3.2/EmissCtrl_nml/` 也为其他模块提供共享 NML。

`post_scripts_v5.3.2/` 为共享后处理，其 Python 日统计和绘图依赖外部 `esil`，本目录未包含该库。

IC/BC 后处理专用入口引用两个未包含的 D3 辅助脚本，详见对应模块说明。相关流程需要补齐依赖后才能完整运行。

部分脚本具有覆盖或清理输出的功能，运行前须检查开关与目标目录。配置中的机器绝对路径需要按实际运行环境调整。
