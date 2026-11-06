# CMAQ D3 ic_only_c10 文件说明

> **IC-RB08 结果：UTC 00:00 起跑，对应北京时间 08:00 起跑。**
> 以下说明 UTC00 实验结果的命名与目录布局。CST00 实验流程见
> [README.md](../README.md) 和 `../IC-RB00_scripts/`。下列绝对路径为原部署位置，结果数据需另行获取。

> 路径：`/backupdata/devin/cmaq_output/d3/ic_only_c10/`
> 模型：CMAQ v5.3.2, cb6r3_ae7_aq, 网格 SD_2013, RUNID=PRD
> 日期：2022-08-27 ~ 2022-09-30（COMBINE 全程）或 5 目标日（ACONC）
> 5 目标日 Julian：2022249(Sep6), 2022256(Sep13), 2022257(Sep14), 2022259(Sep16), 2022262(Sep19)

---

## 一、逐城市置零 propagated（C₁₁）+ IC-only（C₁₀）

每个城市 X 有两个子目录：

| 子目录 | 角色 | 文件 | 含义 |
|---|---|---|---|
| `X2zero/` | **C₁₁ (Propagated control)** | `CCTM_ACONC_PRD_<julian>.nc` (×5) + COMBINE (部分城市) | 城市 X 排放连续置零、IC 传播 |
| `X2zero_ic_only/` | **C₁₀ (Carryover-only control)** | `CCTM_ACONC_PRD_<julian>.nc` (×5) | 传播（已减排净化的）IC + 当天基准排放 |

### 9 城市 C₁₁ + C₁₀ 完整清单

| 城市 | 代码 | C₁₁ propagated | C₁₀ IC-only | C₁₁ COMBINE |
|---|---|---|---|---|
| 广州 | GZ | `gz2zero/` | `gz2zero_ic_only/` | 旧 d3/ |
| 深圳 | SZ | `sz2zero/` | `sz2zero_ic_only/` | `COMBINE_..._sz2zero_...` |
| 珠海 | ZH | `zh2zero/` | `zh2zero_ic_only/` | `COMBINE_..._zh2zero_...` |
| 佛山 | FS | `fs2zero/` | `fs2zero_ic_only/` | `COMBINE_..._fs2zero_...` |
| 江门 | JM | `jm2zero/` | `jm2zero_ic_only/` | `COMBINE_..._jm2zero_...` |
| 肇庆 | ZQ | `zq2zero/` | `zq2zero_ic_only/` | `COMBINE_..._zq2zero_...` |
| 惠州 | HZ | `hz2zero/` | `hz2zero_ic_only/` | `COMBINE_..._hz2zero_...` |
| 东莞 | DG | `dg2zero/` | `dg2zero_ic_only/` | `dg2zero/COMBINE_..._dg2zero_...` |
| 中山 | ZS | `zs2zero/` | `zs2zero_ic_only/` | `COMBINE_..._zs2zero_...` |

### PRD 全域 + everywhere

| 情景 | C₁₁ propagated | C₁₀ IC-only |
|---|---|---|
| PRD 全域 | `prd2zero/` | `prd2zero_ic_only/` |
| everywhere2zero（全可控）| `everywhere2zero/` | `everywhere2zero_ic_only/` |

---

## 二、C₀₀ (Base) 和 C₀₁ (IC-RB) —— 在旧 d3/ 目录

| 格子 | 情景 | COMBINE 路径（旧 d3/）|
|---|---|---|
| C₀₀ | base | `/backupdata/devin/cmaq_output/d3/COMBINE_ACONC_v532_D3_base_PRD_..._18species.nc` |
| C₀₁ gz | gz2zero_ic | `..._gz2zero_ic_PRD_..._18species.nc` |
| C₀₁ sz | sz2zero_ic | `..._sz2zero_ic_PRD_..._18species.nc` |
| C₀₁ 其他城市 | 同理 | `..._X2zero_ic_PRD_..._18species.nc` |
| C₀₁ everywhere | everywhere2zero_ic | `..._everywhere2zero_ic_PRD_..._18species.nc` |

---

## 三、文件格式

- **COMBINE ACONC**：18 species, all 14 layers, ppbV, 全程 Aug27–Sep30, TSTEP=840
- **raw ACONC**（`CCTM_ACONC_PRD_<julian>.nc`）：CMAQ 内部物种, 14 layers, ppmV（需 ×1000 → ppbV）, 仅 5 目标日各 24h
- **Daily COMBINE**：逐日均值版（部分城市有）

---

## 四、数据验证

C₁₁（propagated）与参考 COMBINE 的逐城市逐日对比覆盖 9 城市 × 5 天：
**max |diff| = 0.0001 ppbv。**
