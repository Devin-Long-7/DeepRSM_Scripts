# Carryover 专用物种定义

[English](README_carryover_en.md)

文件：`SpecDef_cb6r3_ae7_aq_carryover_all_layers.txt`。基于原 all_layers 定义扩展，保留全部原有有效输出；`#layer -1` 输出输入文件可用的全部层。原两个 SpecDef 未修改。

覆盖现有 18species 提取脚本实际使用的 21 个基础变量，并保留气象和颗粒物定义。新增独立输出：PAN、PANX、OPAN、NTR1、NTR2、INTR、NO3、PNA、CRON、CLNO2、CLNO3、HO2、ALDX、ACET、KET、GLY、MGLY、GLYD、PACD、AACD、MEOH、ETOH、ROOH、MEO2。新增变量采用 1000 × 原始 ppmV 转为 ppbV。均已与本地 CMAQ v5.3.2 CB6R3_ae7_aq 气相物种表核对；实际原始 ACONC 是否保存全部变量，仍须在运行 COMBINE 前检查。

已有 PANS=PAN+PANX+OPAN、NTR=NTR1+NTR2+INTR，保留合计与分项用于两种分析口径，不能重复加和；NOY 也包含这些组分。OVOC 名称按机制物种使用，避免将集总物种等同于单一真实化合物。

使用时在 COMBINE 调用前，将 SPECIES_DEF 指向本文件完整路径。现有 1_run_combine_aconc.csh 会设置 SPECIES_DEF，因此仅在外层设置环境变量可能被覆盖；本次未修改运行脚本或默认配置。后续不要再用原 2_extract_18species_by_nco.csh 丢弃新增变量，应保留这份完整 COMBINE 输出或使用扩展提取列表。

运行前检查 ACONC 变量、单位和机理是否匹配；先在工作副本中明确设置 COMBINE 内部实际使用的定义文件路径，再检查输出是否保留新增变量。本说明不代表已在目标数据上完成 COMBINE 验证。
