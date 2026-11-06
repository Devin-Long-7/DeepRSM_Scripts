# IC-RB：CST00 每日重置

[English](README_en.md)

每天北京时间 00:00（前一 UTC 日 16:00）重置为本域 baseline CGRID，以两段 CMAQ 模拟覆盖一个 CST 自然日。

## 目录与用途

```text
IC-RB-CST00_scripts/
|-- README.md / README_en.md
|-- batch_run_cases.csh                  # 多情景或配置文件批处理
|-- cctm_config.csh                      # 默认配置
|-- cctm_config_D3_150X117_202209.csh     # D3 九月配置副本
|-- run_configs/
|   `-- cctm_config_D3_150X117_202209.csh # 另一配置副本，按内容选用
|-- run_manager.csh                      # 生成、校验、执行和后处理
|-- run_cctm_template.csh                 # CMAQ 模板
|-- validate_script.csh                  # 输入与脚本校验
|-- post/
|   |-- check_restart.py                 # 重启时刻检查
|   |-- run_post.py                      # 后处理计划、执行与校验
|   |-- recover_post.py                  # 已有结果补处理
|   |-- run_post_all_layers.py           # 全层兼容入口
|   `-- run_post_layer1.py               # 第一层兼容入口
`-- .gitignore
```

## 运行前配置

检查日期、`BASELINE_CGRID_ROOT`、CMAQ/MPI、气象、BC、排放、掩膜、NML 和输出目录。baseline CGRID 内部时间必须为前一日 UTC16，不能仅凭文件名判定。

默认配置引用同级 `../cctm_scripts_v5.3.2/`（NML 与生成器）、`../post_scripts_v5.3.2/`（COMBINE 模板与物种定义），需保持相对层级。目录内的 `post/` 是调度及校验包装器。CMAQ/COMBINE 可执行程序及气象、排放等大数据需在计算节点配置；还需要 csh、GNU 工具、Python、NetCDF/NCO 和匹配的 MPI 环境。

## 使用方法

进入本目录：

```bash
csh batch_run_cases.csh prd2zero everywhere2zero --dry-run
csh batch_run_cases.csh prd2zero everywhere2zero
# 直接传入已有配置路径，不使用 --config
csh run_manager.csh run_configs/cctm_config_D3_150X117_202209.csh --dry-run
```

无参数批处理默认选择 `prd2zero` 和 `everywhere2zero`，其余参数来自默认配置。`--dry-run` 生成并检查计划，不运行 CMAQ 或后处理；仍可能要求外部输入存在。

## 输出与时间

运行时创建 `generated/` 保存脚本、清单和日志；CMAQ 结果写入 `OUTDIR_BASE`。seg01 为前日 UTC16–24，seg02 接续目标日 UTC00–16，不能将单个分段作为完整日。

后处理拼接小时与 CST 日产品，校验重启时刻和日覆盖。`CLEANUP_CCTM_OUTPUT` 等参数控制中间输出清理，运行前需核对。
