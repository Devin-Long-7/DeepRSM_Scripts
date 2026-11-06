# ISAM：CST00 每日重启

[English](README_ISAM_CST00_en.md)

在目标 CST 日 00:00 重置 ISAM 标签，以 baseline UTC16 CGRID 初始化物理化学状态；目标日期之间相互独立。

## 文件与职责

```text
IC-RB-CST00_isam_scripts/
|-- README_ISAM_CST00.md / README_ISAM_CST00_en.md
|-- launch_isam_cst00_5days.csh                 # 五日串行入口
|-- run_cctm_D3_ISAM_daily_restart_CST00.csh    # 单日两段 ISAM 模拟
|-- isam_control_PRD_O3.txt                    # 标签定义
`-- EmissCtrl_cb6r3_ae7_aq_isam_base.nml       # 基准排放配置
```

## 配置与运行

核对主脚本的 `CMAQ_HOME`、`BLD`、`EXEC`、MPI、气象、BC、排放、掩膜和 baseline CGRID 路径。可执行文件需真正启用 ISAM，不能仅凭目录名称判断。标签文件和 NML 已提供，从本目录启动。

baseline CGRID 应为目标日前一日 UTC16 全状态瞬时场。默认 2022-09-06、13、14、16、19 所需 Julian 日标签为 2022248、2022255、2022256、2022258、2022261，仍需检查内部 TFLAG。

```bash
# 直接运行 CMAQ，先验证单日
csh run_cctm_D3_ISAM_daily_restart_CST00.csh 2022-09-06
csh launch_isam_cst00_5days.csh
```

入口没有 `--dry-run`。五日启动器在单日失败后打印错误并继续，末尾完成提示不代表全部成功。

## 输出与校验

主脚本 `OUTDIR` 默认采用 `isam_daily_cst00` 输出树。seg01 为前日 UTC16 起 8 小时、标签新启动；seg02 为当日 UTC00 起 16 小时，通过 `ISAM_PREVDAY` 接续 seg01 的 SA_CGRID。

检查模型日志、CGRID/SA_CGRID、SA_ACONC 时间、标签总和与 bulk O3 一致性。按真实时间拼接后才可计算完整 CST 日指标。ISAM 标签份额与 IC-RB 浓度差不能直接等同。本目录不含独立后处理或测试集；本文档不声称重新完成模拟。
