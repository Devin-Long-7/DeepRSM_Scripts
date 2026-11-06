# IC-RB：UTC00 模板运行系统

[English](README_en.md)

以配置文件驱动 CMAQ v5.3.2 模板生成与执行。UTC00 对应北京时间 CST08；普通连续运行与每日重置模式由配置区分。

本目录默认 `IC_RB_MODE=Y`，用于每日重置实验；常规连续运行使用默认 `IC_RB_MODE=N` 的 [`cctm_scripts_v5.3.2/`](../cctm_scripts_v5.3.2/README.md)。两目录分别保留完整代码及默认配置，便于区分实验；修改不会自动同步。

## 文件与职责

```text
IC-RB-UTC00_scripts/
|-- README.md / README_en.md
|-- batch_run_cases.csh             # 情景名或配置文件批处理
|-- cctm_config.csh                 # 默认配置
|-- cctm_config_D3_150X117_202209.csh
|-- cctm_config_D3_150X117_202209_IC-RB_base_on_cgrid.csh
|-- run_manager.csh                 # 生成、校验、执行和可选后处理
|-- run_cctm_template.csh            # CMAQ 运行模板
|-- validate_script.csh             # 文件与脚本检查
|-- create_emissCtrl_nml.py          # 从模板和 CSV 生成 NML
|-- EmissCtrl_nml/                  # 已有情景 NML，见内附说明
`-- nml_config/
    |-- EmissCtrl_base.nml
    |-- scaling_rules.csv
    `-- stream_families.csv
```

## 配置与使用

核对 `cctm_config.csh` 或所选配置中的模拟日期、网格、CMAQ/MPI、气象、IC/BC、掩膜、排放和输出路径。运行日期以所选配置内容为准，不能根据目录名推断。

默认 `cctm_config.csh` 与 `cctm_config_D3_150X117_202209_IC-RB_base_on_cgrid.csh` 内容一致：2022-09-01 至 2022-09-30、D3、`IC_RB_MODE=Y`，使用 baseline UTC00 CGRID 进行每日重置，浓度及后处理默认取地面层。`NML_PATH` 保留原配置的部署绝对路径，使用本共享目录时应在工作副本中改为实际的 `EmissCtrl_nml/` 路径。

`IC_RB_MODE=N` 为常规续跑，`Y` 为 UTC00 每日重置；具体初始场来源还需看所选配置与模板，不能把 ICON 与 baseline CGRID 重置混称。此默认配置只接受 N/Y，CST00 实验使用相邻的独立目录。

`GENERATE_NML=N` 使用 `NML_PATH` 指定的已有情景文件；设为 Y 时从 `nml_config/EmissCtrl_base.nml`、`scaling_rules.csv`、`stream_families.csv` 生成。

在本目录执行：

```bash
csh batch_run_cases.csh oos3 --dry-run
csh batch_run_cases.csh oos3
# 直接传配置路径，无 --config 选项
csh run_manager.csh cctm_config_D3_150X117_202209_IC-RB_base_on_cgrid.csh --dry-run
```

批处理无参数默认情景为 `oos3`；dry-run 生成和检查脚本，不执行模型。默认后处理引用同级 `../post_scripts_v5.3.2/`，现已随共享目录提供，但其中 CMAQ/COMBINE 程序与原始输入仍需另行安装和配置。

## 输出

`generated/` 在运行时创建，保存运行脚本、NML 和日志，不是已有输入目录。模型数据写入 `OUTDIR_BASE`，后处理写入所选输出路径。检查 `DELETE_AFTER_RUN` 和后处理清理选项，避免误删需保留的运行产物。本文档只做源码与路径核对，未执行生产模拟。
