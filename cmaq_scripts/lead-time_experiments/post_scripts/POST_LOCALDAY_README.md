# 本地日控制实验后处理

[English](POST_LOCALDAY_README_en.md)

拼接 lead-time 模拟的 UTC 分段，运行 COMBINE、变量提取和 CST（UTC+8）日统计。原始模型分段必须先完成。

## 文件与职责

```text
post_scripts/
|-- POST_LOCALDAY_README.md / POST_LOCALDAY_README_en.md
|-- run_post_localday_controls.csh            # 常用入口
|-- run_post_localday_controls_w_o_sep19.csh   # 默认日期不含 9 月 19 日的版本
|-- run_post_localday_controls.csh.bak         # 历史备份，不作为当前入口
|-- 1_run_combine_aconc_local.csh              # COMBINE 化学/气象变量
|-- 2_extract_18species_by_nco_local.csh        # NCO 提取基础和派生变量
|-- 4_convert2daily_local.py                  # 本地日均值和 O3 MDA8
`-- check_daily_o3.py                         # 日臭氧文件检查
```

## 使用

自动调用由上级批处理的 `enable_post` 控制，传入该次日期、实验和情景。单独调用时默认值可能与已有结果不同，建议显式指定：

```bash
# 从 lead-time_experiments 目录运行
csh post_scripts/run_post_localday_controls.csh --help
csh post_scripts/run_post_localday_controls.csh \
  --target-days "2022-09-06 2022-09-13 2022-09-14 2022-09-16 2022-09-19" \
  --experiments "P0:0 A1:1 A2:2 A3:3" \
  --case-suffix "L-B_HZ_VOC30_NOX30" \
  --segment-root "/path/to/cmaq_output" --appl "PRD" \
  --combine-dir "/path/to/new_post_output"
```

路径替换为已有分段和新的输出位置。此入口没有 dry-run，运行会写出结果，可能替换同名中间文件。核对 COMBINE、NCO、Python、CMAQ 物种定义与 `INCLUDE_WRF`、`KEEP_COMBINE_FILE` 等选项。

## 输出

先按真实 UTC 日合并 ACONC/APMDIAG 分段，再 COMBINE、提取和转换为日文件。产物为 `COMBINE_ACONC_*.nc`、`*_18species.nc`、`Daily_*_18species.nc`；这些均是运行产物，不是随包输入。

“18species”是历史文件名，实际提取还含 NOX、VOC、O3_UGM3 等派生量，以脚本列表为准。MDA8 必须在完整目标 CST 时间窗上计算，不应把单个 8/16 小时分段当成完整日。`check_daily_o3.py` 接收一个已有日文件路径；没有提供生产结果或独立测试集。
