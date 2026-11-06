# CST00 初始场物种替换实验

[English](README_en.md)

在北京时间（CST，UTC+8）00:00，以连续控制场 C 和每日重置场 R 构造混合初始场，比较 NO2、其他氮组分、OVOC、O3 及剩余物种对目标日臭氧的影响。

## 目录与文件用途

```text
carryover_species_experiments/
|-- README.md / README_en.md
|-- batch_run.csh            # 批处理入口
|-- cctm_config.csh          # 日期、实验、物种组、资源和路径
|-- initial_fields.csv       # 各日期的 C/R 初始场与排放 NML
|-- prepare_plan.py          # 检查输入，生成分段运行计划
|-- prepare_ic.py            # 构造并逐字段核验混合初始场
|-- post_results.py          # 城市臭氧统计与有符号效应
|-- assets/
|   |-- run_cctm_template.csh
|   `-- guangdong_cities.json
`-- .gitignore
```

模板和九市边界随目录提供；CMAQ/MPI、气象、排放、BC 和初始场需在计算节点另行准备。依赖 csh、GNU date、bc，以及 Python、NumPy、netCDF4、pandas、pyproj、Shapely 2+、Matplotlib。

## 配置与使用

1. 在 `cctm_config.csh` 核对 `PYTHON_CMD`、模型路径、资源、`TARGET_DATES`、`EXPERIMENT_CASES`、`GROUP_*` 和后处理开关。
2. 在 `initial_fields.csv` 填写连续场、重置场、NML 的真实路径。输入必须是目标日前一日 UTC16 的单时次、全层瞬时 CGRID，不能用 ACONC 平均场替代。当前清单的 R 为 baseline CGRID，不能将其解释成 D2 插值 ICON。
3. 进入本目录，先检查单日计划，再运行：

```bash
csh batch_run.csh --dates 2022-09-16 --dry-run
csh batch_run.csh --dates 2022-09-16
# 按配置执行全部日期
csh batch_run.csh
# 只重做已有批次后处理；替换为实际 manifest
csh batch_run.csh --post-only /path/to/generated/batch_ID/manifest.json
```

`--dry-run` 会写入计划，但不构造混合 IC 或启动 CMAQ。默认五日为 9 月 6、13、14、16、19 日，每日 8 组：C、R、`C_NO2`、`R_without_NO2`、`C_other_N`、`C_OVOC`、`C_O3`、`C_rest`。

## 运行产物与解释

运行时新建 `generated/batch_ID/`，保存 manifest、配置快照、混合初始场、分段脚本和溯源信息；此目录不是随包输入。CMAQ 输出写入 `OUTDIR_BASE`。seg01 从前一 UTC 日 16:00 运行 8 小时，seg02 接续至目标日 UTC16，合计一个 CST 自然日。

后处理生成 `hourly_ozone.csv`、`daily_ozone.csv`、`signed_effects.csv`、城市掩膜和效应图。O3 单位 ppbv；MDA8 为逐格点求同一 CST 日内 17 个 8 小时窗口的最大值，再进行区域平均。日均为 00–23 CST，白天均值为 10–17 CST。

各组效应是相对 C/R 对照的浓度差；非加和量反映背景交互，不能直接解释为独立反应路径通量。替换覆盖整个 D3 域与全部层。此共享副本不含单元测试；文档核对不代表完成真实 CMAQ 模拟验证。
