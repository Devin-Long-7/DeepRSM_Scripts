#!/bin/csh -f
# ===================================================================
# IC-RB CST00 配置：除情景列表外，常用参数只在这里修改。
# 情景列表见 batch_run_cases.csh；START_DATE/END_DATE 均为 CST 日期，含首尾。
# 每天：前一 UTC 日 16–24 时重置 baseline；本 UTC 日 00–16 时接续。
# ===================================================================

# ===== 基本案例配置（batch 按情景覆盖 CASE_NAME/CASE_TYPE）=====
if ( ! $?CASE_NAME ) setenv CASE_NAME "base"
if ( ! $?CASE_TYPE ) setenv CASE_TYPE "standard"
if ( ! $?START_DATE ) setenv START_DATE "2022-09-01"
if ( ! $?END_DATE ) setenv END_DATE "2022-09-30"
setenv FIRST_DATE "$START_DATE"

# ===== 计算资源与运行环境 =====
setenv NPCOL 8
setenv NPROW 4
setenv MPI_BIN "/opt/intel/impi/2019.0.117/intel64/bin"
setenv I_MPI_FABRICS shm
setenv OMP_NUM_THREADS 1
setenv PYTHON_CMD "/program/software/devin_env/bin/python3"
# PYTHON_CMD 不存在时管理器自动寻找系统 python3。MPIRUN 沿用模板的 mpiexec。

# ===== 机理与域 =====
setenv VRSN v532
setenv PROC mpi
setenv MECH cb6r3_ae7_aq
setenv APPL PRD
setenv DOMAIN D3
setenv GRID_NAME SD_2013
setenv NZ 14

# ===== 固定路径 =====
# 相对路径均相对于本脚本目录；管理器会转换为绝对路径。
setenv CCTM_WORKDIR "/program/rain/Build_CMAQ/CMAQ_Project/CCTM/scripts"
setenv BLD "${CCTM_WORKDIR}/BLD_CCTM_${VRSN}_intel"
setenv INPDIR "/bigdata/CMAQ_input/devin/PRD/2022"
setenv OUTDIR_BASE "/home/devin/cmaq_output/${CASE_NAME}_icrb_cst00"
# 每次执行创建新目录，避免覆盖既有结果。
setenv TEMPLATE_FILE "run_cctm_template.csh"

# ===== 气象、baseline 初始场、边界场 =====
setenv MET_PATH "${INPDIR}/mcip/${DOMAIN}"
setenv GRIDDESC "${MET_PATH}/GRIDDESC"
setenv BASELINE_CGRID_ROOT "/mnt/167/devin/cmaq_output/CCTM_CGRID_base/202209_PRD_150X117_utc16"
# baseline 文件布局：根目录/DOMAIN/YYYY/MM/CCTM_CGRID_APPL_YYYYJJJ.nc
# 文件名日期为 UTC 日期；文件内部必须为该日 16:00（不是原 UTC00 CGRID）。
setenv BC_PATH "/bigdata/CMAQ_input/devin/PRD/bcon/${DOMAIN}_base"

# ===== 海洋、掩膜、排放 =====
setenv CMAQ_MASKS "${INPDIR}/ocean/${DOMAIN}/${DOMAIN}_cmaq_masks"
setenv OCEAN_1_PATH "${INPDIR}/ocean/${DOMAIN}/oceanfile"
setenv N_EMIS_GR 2
setenv AV_EMIS_DIR "${INPDIR}/emis/${DOMAIN}"
setenv BV_EMIS_DIR "${INPDIR}/emis/${DOMAIN}/MEGAN"
setenv EM_AV_PREFIX "comb_ArearateAB_cn03_"
setenv MEGAN_PREFIX "MEGANv32.PRD_3km."
setenv MEGAN_SUFFIX ".BDSNP.ncf"
# 固定整段实验使用的代表月，与 baseline 一致；跨到 8 月的分段仍用 9 月清单。
setenv EMIS_MONTH "2022-09"

# ===== 排放控制 NML：复用原目录的文件或生成器 =====
setenv GENERATE_NML N
setenv NML_PATH "../cctm_scripts_v5.3.2/EmissCtrl_nml/EmissCtrl_${MECH}_${CASE_NAME}.nml"
setenv NML_GENERATOR "../cctm_scripts_v5.3.2/create_emissCtrl_nml.py"

# ===== 浓度输出与时间步长：保持原版 ALL、14 层 =====
setenv CONC_SPCS "ALL"
setenv AVG_CONC_SPCS "ALL"
setenv CONC_BLEV_ELEV "1 14"
setenv ACONC_BLEV_ELEV "1 14"
setenv APMDIAG_BLEV_ELEV "1 14"
setenv CTM_MAXSYNC 300
setenv CTM_MINSYNC 60
setenv SIGMA_SYNC_TOP 0.7
setenv CTM_ADV_CFL 0.95

# ===== 后处理：沿用原 COMBINE、物种提取和日统计程序 =====
setenv ENABLE_POST_PROCESS Y
setenv POST_TEMPLATE_FILE "../post_scripts_v5.3.2/0_run_post_script.csh"
setenv POST_SPEC_FILE "../post_scripts_v5.3.2/spec_def_files/SpecDef_${MECH}_all_layers.txt"
setenv LAYER -1  # -1：提取所有层；正整数：提取指定层（从 1 开始）
# 空值：本次结果目录/post；非空：在指定目录下创建本次运行专用子目录。
setenv COMBINE_DIR ""
setenv KEEP_18SPECIES_ONLY T
setenv INCLUDE_WRF F
setenv KEEP_COMBINE_FILE F
setenv CONVERT2DAILY T
setenv CLEANUP_CCTM_OUTPUT T
# 小时文件保持 UTC；日文件按 CST 自然日统计地面层。
# 提取日期可跳过 spin-up，但必须落在模拟范围内。
if ( ! $?POST_BEGIN_DATE ) setenv POST_BEGIN_DATE "$START_DATE"
if ( ! $?POST_END_DATE ) setenv POST_END_DATE "$END_DATE"
# 清理仅在校验通过后执行：保留 CGRID、cfg、日志及最终小时/日文件。
# 此流程处理浓度；不执行沉降合并、IC/BC 提取或绘图。
