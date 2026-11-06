# 排放控制 NML

[English](README_en.md)

本目录保存 CMAQ CB6R3/AE7/AQ 已有情景的 `EmissCtrl_*.nml`，用于运行配置的 `NML_PATH`。NML 是模型输入，不是分析结果。

## 文件分类

- `EmissCtrl_cb6r3_ae7_aq_base.nml`：基准。
- `*2zero.nml`、`*2zero_ic.nml`：区域置零及 IC-RB 命名版本，具体规则以文件内容为准。
- `*oos1.nml` 至 `*oos5.nml`、`*run1.nml` 至 `*run31.nml`：现有校验/设计情景；实际编号以目录内容为准。
- `*local_only_CITY.nml`：保留目标 PRD 城市，置零其他八市及 `D3-PRD`。
- `*other_prd_only_CITY.nml`：保留其他八市，置零目标城市及 `D3-PRD`。
- `*oth_prd2zero_CITY.nml`、`*outside_prd2zero_prd.nml`、`*prd2zero.nml`：按文件内区域和家族规则控制。
- `README.md`、`README_en.md`：双语说明。

`D3-PRD` 是整个 D3 域中九市之外的格点，不等同广东省内其余区域。控制家族及自然源是否保留应读实际 `EmissionScalingRules`；不能只根据文件名推断完整缩放矩阵。

## 使用

在上级配置中设置 `GENERATE_NML=N`，将 `NML_PATH` 指向所需文件。运行前核对 `CMAQ_MASKS` 的区域名、排放流、化学家族、缩放因子和机理是否匹配。乘法因子 0.7 表示保留基准排放的 70%。

如需按 CSV 动态生成，使用上级 `create_emissCtrl_nml.py` 和 `nml_config/`；生成器不自动读取目录中的既有情景作为模板。`cctm_scripts_v5.3.2/EmissCtrl_nml/` 也供其他模块引用；它与 `IC-RB-UTC00_scripts/EmissCtrl_nml/` 中的文件各自独立维护。
