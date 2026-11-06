# IC-RB00 与 IC-RB08 Shapley 归因

[English](README_en.md)

保留 UTC00（CST08）历史初始场实验，以及 CST00 四格设计。两者时间窗口不同，应分开分析。

## 目录与用途

```text
shapley_attribution_scripts/
|-- README.md / README_en.md
|-- calculate_cst00_shapley.py                 # 四格日浓度计算归因及闭合
|-- IC-RB08_scripts/
|   |-- batch_run_iconly.csh                  # gen/run/submit 批量入口
|   |-- create_iconly_csh.csh                 # 从旧模板生成区域脚本
|   |-- check_ic11_cgrid.csh                  # 检查 C11 重启场
|   |-- run_cctm_D3_202209_prd2zero_sep19.csh # C11 连续控制
|   |-- run_cctm_D3_202209_prd2zero_iconly.csh # C10 初始场单因子
|   `-- CMAQ_ic_only_c10_files_description.md # 历史结果路径说明
|-- IC-RB00_scripts/
|   |-- run_cst00_shapley.csh                 # 七个情景按依赖执行
|   |-- cst00_config_common.csh               # 共用路径与资源
|   |-- config_C00.csh / config_C01.csh / config_C10.csh / config_C11.csh
|   |-- config_E01.csh / config_E10.csh / config_E11.csh
|   |-- run_manager.csh / run_cctm_template.csh / validate_script.csh
|   `-- post/
|       |-- check_restart.py / run_post.py / recover_post.py
|       `-- run_post_all_layers.py / run_post_layer1.py
`-- .gitignore
```

`IC-RB00_scripts/post/` 提供重启时刻检查及后处理入口。共用 NML 位于该脚本目录上两级的 `cctm_scripts_v5.3.2/`，COMBINE 模板及定义位于 `post_scripts_v5.3.2/`，需保持相对层级。`IC-RB08_scripts/CMAQ_ic_only_c10_files_description.md` 描述 UTC00 实验的结果命名与布局；对应原始模型输出需另行提供。

## 四格与模拟

C00：基准初始场和排放；C01：baseline 每日重置场和受控排放；C10：来自 C11 的传播场和基准排放；C11：受控场连续传播及受控排放。C 组控制 PRD，E 组控制全域，两组共用 C00。

检查 `cst00_config_common.csh` 及七份配置中的日期、baseline UTC16 CGRID、CMAQ/MPI、IC/BC、气象、NML、输出和清理参数。C10 的 `PROPAGATED_ROOT` 必须指向对应 C11。C00/C11 中间日不能跳过。

```bash
cd IC-RB00_scripts
csh run_cst00_shapley.csh --dry-run
csh run_cst00_shapley.csh
```

seg01 为前日 UTC16–24，seg02 为目标日 UTC00–16。运行时生成 `generated/`，模型结果写入各配置的输出根目录，后处理日产品位于对应 `post/`。运行前检查清理开关及外部输入。

## 归因计算

在本目录下，准备四份同组、同单位、同时间覆盖的 daily NetCDF，以下路径替换为真实文件：

```bash
python calculate_cst00_shapley.py \
  --c00 /path/to/C00_daily.nc --c01 /path/to/C01_daily.nc \
  --c10 /path/to/C10_daily.nc --c11 /path/to/C11_daily.nc \
  --dates Sep06,Sep13,Sep14,Sep16,Sep19 --output-prefix results_cst00/prd
```

默认取全域格点均值；按区域时加 `--mask-json`，内容为区域名到布尔 `.npy` 掩膜路径的映射，掩膜需匹配网格。输出 CSV/JSON，单位与输入浓度一致：

```text
total = C00 - C11
same_day_Shapley = 0.5 * ((C00 - C01) + (C10 - C11))
carryover_Shapley = 0.5 * ((C00 - C10) + (C01 - C11))
```

两分量之和应等于 total。输入 total 为零时 HDF 输出 NaN；小分母的百分比需谨慎解释。
