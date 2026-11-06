# CMAQ v5.3.2 后处理

[English](README_en.md)

将 CCTM 小时输出合并、筛选变量、转换时间和日统计，并绘制日地图。运行需要外部 CMAQ 安装及模拟输出；本目录不包含模型数据或已编译程序。

## 目录与文件

```text
post_scripts_v5.3.2/
|-- README.md / README_en.md
|-- 0_run_post_script.csh                 # 常规后处理总入口
|-- 0_run_post_script_output_2_IC_BC.csh  # 附带下一级嵌套 IC/BC 的入口
|-- 1_run_combine_aconc.csh              # 合并浓度并按 SpecDef 计算变量
|-- 1_run_combine_dep.csh                # 合并沉降
|-- 2_extract_18species_by_nco.csh       # NCO 筛选；基础列表实际含 21 个变量
|-- 3_tolocaltime.csh                   # 调用 I/O API m3tshift 转换时间
|-- 4_convert2daily.py                  # esil 小时转日统计，取第 0 层
|-- 5_run_bcon.csh                      # 调用 BCON 生成嵌套边界场
|-- 6_run_icon_loop.csh                 # 逐日调用 ICON 生成嵌套初始场
|-- 7_plot_daily_map.py                 # 日浓度及相对基准响应地图
`-- spec_def_files/
    |-- SpecDef_cb6r3_ae7_aq.txt
    |-- SpecDef_cb6r3_ae7_aq_all_layers.txt
    |-- SpecDef_cb6r3_ae7_aq_carryover_all_layers.txt
    `-- README_carryover.md / README_carryover_en.md
```

物种扩展见 [Carryover 说明](spec_def_files/README_carryover.md)。

## 快速上手

1. 在独立工作副本中配置 `0_run_post_script.csh`：检查 `CCTM_WORKDIR`、`script_path`、日期、域、情景、`INPDIR`、`CCTMOUTDIR_ROOT`、`COMBINE_DIR`。`CMAQ_HOME` 从 CCTM 工作目录推导，须找到 `config_cmaq.csh`。
2. 检查 csh、GNU date、NCO、I/O API 的 `m3tshift`、CMAQ COMBINE 程序；使用 IC/BC 时还需 BCON/ICON。日统计和绘图需要作者的 `esil`，以及其依赖、`tqdm`、NumPy、pandas、xarray、cmaps 等。本共享目录未包含 `esil`；须另行安装对应版本。入口中的 Python 环境激活路径也需按部署环境配置。
3. 首次运行建议设置 `CLEANUP_CCTM_OUTPUT=F`、`KEEP_COMBINE_FILE=T`、`COPY_SPEC_DEF=F`，并按需要关闭绘图，核对输入时间覆盖后执行：

```bash
cd /path/to/cmaq_scripts/post_scripts_v5.3.2
csh 0_run_post_script.csh > post.log 2>&1
```

**此入口没有 dry-run，默认 `CLEANUP_CCTM_OUTPUT=T` 会清理 CCTM 输出。** `KEEP_COMBINE_FILE` 控制部分中间文件保留；运行时间转换等子脚本前也应检查其删除逻辑。`COPY_SPEC_DEF=T` 会覆盖复制定义文件到 CMAQ 安装树，默认 F 不复制。

子脚本 1、2、3、5、6 依赖总入口设置的环境变量，不能当作无配置的独立命令。COMBINE 实际从 CMAQ 安装树选择 SpecDef；把文件放在本地并不等于已启用。沉降定义 `SpecDef_Dep_*` 需由 CMAQ 安装提供。

IC/BC 专用入口还调用 `5_run_bcon_D3_155X122.csh`、`6_run_icon_loop_D3_155X122.csh`，这两个文件未包含；当前不能直接完成其全部默认步骤。应先提供所需脚本并核对 IC/BC 开关与实际调用。

## 单独使用 Python

在已安装 `esil` 的环境中，将下列占位路径替换为实际输入：

```bash
python 4_convert2daily.py /data/COMBINE.nc 2022-09-06 2022-09-06 8
python 7_plot_daily_map.py /data/Daily_COMBINE.nc /data/Daily_BASE.nc \
  2022-09-06 2022-09-06 O3_MDA8 D3 base /data/boundary.shp
```

转换器在输入同目录生成 `Daily_<原文件名>`；输出已存在时默认跳过。`8` 为传给 `esil` 的小时偏移，输入需覆盖所选本地日；不要对已经平移的时间重复加偏移。具体日指标由 `esil.netcdf_helper.convert_hr2daily_data` 实现，不能仅凭本脚本确认完整统计规则。绘图需时间、网格一致的基准文件及边界数据。

## 检查输出

查看 `post.log` 和 COMBINE 日志，核对输出 NetCDF 的时间范围、层数、变量、单位及缺失值；日统计使用第 0 层。通常产生 `COMBINE_*.nc`、可选 `_18species.nc`、`Daily_*.nc` 和地图，均为运行产物。Carryover 分析应保留扩展变量，不能继续用原筛选列表把它们删除。
