# 直接 CMAQ PR 校验

[English](README_en.md)

固定 VOC 等其他条件，扫描 NOx 排放因子，计算目标受体的 O3 曲线，与 RSM 的 PR 峰值位置比较。

## 目录与用途

```text
pr_cmaq_validation_scripts/
|-- README.md / README_en.md
|-- config_pr_validation.csh       # 日期、受体、模式、因子和路径
|-- batch_run_pr_validation.csh    # 生成计划、执行与后处理入口
|-- generate_emissctrl.py          # 生成 NOx 控制 NML
|-- render_cctm_segment.py         # 渲染分段 CMAQ 脚本
|-- post_pr_validation.py          # 拼接、日统计与 CSV 汇总
`-- .gitignore
```

依赖同级 `../lead-time_experiments/` 中的九月模板、基准 NML 和 `post_scripts/`，这些现已包含于共享包。还需计算节点的 CMAQ/MPI、COMBINE、NCO、baseline UTC00 CGRID、气象/排放/BC，以及 Python、NumPy、xarray、netCDF4 等依赖。

## 配置与命令

修改 `config_pr_validation.csh` 的 `target_days`、`lead_days`、`target_regions`、`scan_modes`、`nox_factors` 及所有输入输出路径。Local 只控制目标城市；Whole 使用 `EVERYWHERE`（D3 全域）。`D3-PRD` 是九市之外的受体区域，不能与 Whole 控制范围混同。

进入本目录：

```bash
csh batch_run_pr_validation.csh --dry-run
csh batch_run_pr_validation.csh --run
csh batch_run_pr_validation.csh --post --manifest /path/to/generated/manifest.tsv
# 或在模型成功后立即后处理
csh batch_run_pr_validation.csh --run-and-post
```

无参数等同 `--run`，会直接运行模型；`--dry-run` 只生成，`--post` 只处理已有结果。默认有多日、多因子任务，首次应在配置中缩小至一个日期、一个受体和少量因子。

## 时间、输出与比较口径

`lead_days=0` 时，baseline-pre 从前日 UTC00 运行至 UTC16，控制段接续至目标日 UTC16，覆盖目标 CST 自然日；提前控制时自动增加中间段。

运行时创建 `generated/`，包含 NML、脚本和 Tab 分隔 manifest；原始输出写入 `segment_root`，后处理写入 `post_root`，生成 COMBINE、提取和 daily NetCDF，以及 `pr_validation_summary.csv`。

以相同日期、受体和空间平均口径比较区域平均 O3 MDA8（ppbv）随 NOx 因子的曲线。最大值对应离散扫描的 PR 近似；若峰值在端点应扩大范围，不能声称已找到内部最优值。本文档未重新运行直接 CMAQ 校验。
