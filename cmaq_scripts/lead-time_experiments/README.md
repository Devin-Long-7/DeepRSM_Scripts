# Lead-time 提前控制实验

[English](README_en.md)

比较目标北京时间自然日当天控制 P0，以及提前 1、2、3 个本地日开始控制的 A1/A2/A3。本地时区为 CST（UTC+8）。

## 目录与用途

```text
lead-time_experiments/
|-- README.md / README_en.md
|-- batch_run_localday_controls.csh                  # 九月单情景入口
|-- batch_run_localday_controls_multicase.csh        # 多情景入口
|-- batch_run_localday_controls_multicase_batch1.csh # 另一批情景及实验列表
|-- run_cctm_D3_202209_base_devin.csh                 # 九月模板
|-- run_cctm_D3_202209_P0_Sep19_PRD_VOC30_NOX30.csh    # 历史单例
|-- EmissCtrl_nml/                                  # baseline 与控制 NML
|-- post_scripts/                                   # 后处理，见内附双语说明
`-- .gitignore
```

## 配置与使用

先检查选定入口顶部的模板、baseline UTC00 CGRID、NML、`target_days`、`experiments`、`case_suffix` 或 `case_list`、MPI、模型路径、`enable_post` 和输出路径。多情景版 `cleanup_raw=1` 默认归档后删除原始分段输出，0 保留、2 直接删除；正式运行前需决定保留策略。

进入本目录执行：

```bash
csh batch_run_localday_controls.csh --dry-run
csh batch_run_localday_controls.csh
# 多情景入口；先检查其 case_list
csh batch_run_localday_controls_multicase.csh --dry-run
# 单独后处理：显式指定已有结果对应的日期与情景，参数见下级说明
csh post_scripts/run_post_localday_controls.csh --help
```

dry-run 生成脚本但不运行模型、后处理或清理。无参数正式运行会使用入口中已有配置，不会自动按命令行更换日期。

## 时间与输出

baseline 预备段先从连续基准 UTC00 CGRID 运行到控制开始日 UTC16。P0 再接两个控制段，共 3 段；A1/A2/A3 通常共 4 段，其中中间完整 UTC 日合成一个连续段。`last_segment_full_day=N` 时结束于目标 UTC16，即目标 CST 日 24:00。

运行时生成 `generated/` 和日志；原始结果、COMBINE 和 daily 产品按脚本配置写出。自动后处理使用本目录的 `post_scripts/run_post_localday_controls.csh`。需要 CMAQ/MPI、气象/排放/IC/BC、csh、GNU 工具、NCO、COMBINE 和 Python 环境。文档更新未执行任何生产模拟或清理。
