# ISAM：UTC00 每日重启

[English](README_en.md)

从基准 CGRID 初始化物理化学状态，在 UTC00（北京时间 CST08）重置标签并运行 24 小时。此时段不是 CST 00–24 自然日。

## 目录与用途

```text
IC-RB-UTC00_isam_scripts/
|-- README.md / README_en.md
|-- launch_isam_5days.csh                      # 五个目标日串行入口
|-- run_cctm_D3_ISAM_daily_restart.csh         # YYYY-MM-DD 单日入口
|-- run_cctm_D3_202209_base_ISAM_devin.csh     # 原连续 ISAM 运行脚本
|-- isam_control_PRD_O3.txt                    # 标签定义
`-- EmissCtrl_cb6r3_ae7_aq_isam_base.nml       # 基准排放 NML
```

## 配置与使用

核对 CMAQ 编译和可执行路径、MPI、baseline CGRID、气象、排放、BC、掩膜、标签和输出路径。单日入口读取前一 Julian 日命名的基准 CGRID，内部时间必须匹配目标 UTC00；文件名日期不能代替检查。确认实际可执行文件启用了 ISAM。

进入本目录：

```bash
# 直接启动 CMAQ，先运行单日
csh run_cctm_D3_ISAM_daily_restart.csh 2022-09-06
# 单日核对后运行 9 月 6、13、14、16、19 日
csh launch_isam_5days.csh
```

主脚本没有 `--dry-run`。启动器某日失败后仍继续，需逐日检查日志。连续脚本的日期写在脚本内，不接受单日入口的相同调用方式；只有需要连续实验且核对配置后才单独运行。

## 结果检查

单日输出默认写入配置的 `isam_daily/D3/2022/<month>/` 树。`ISAM_NEW_START=Y` 且清除 `ISAM_PREVDAY`，各日标签独立。检查 SA_ACONC、SA_CGRID、结束日志、浓度单位和标签总和。

UTC00–24 对应 CST08 至次日 CST08，不能当作同日期 CST 自然日 MDA8。本目录没有独立统计或测试程序，真实运行需在已有 CMAQ/MPI 与输入数据的计算节点执行。
