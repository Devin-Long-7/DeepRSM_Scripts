#!/bin/csh -f

# ===================================================================
# CMAQ v5.3.2 运行配置文件
# 说明：编辑此文件设置CMAQ运行参数，然后运行 ./run_manager.csh
# ===================================================================

# ===== 基本案例配置 =====
# 案例/情景变量:已设则保留外部值(batch_run_cases.csh 按情景名批量跑时覆盖 CASE_NAME,
# 并按名字判定 CASE_TYPE),否则用下面的默认值。排放控制 nml(generated/EmissCtrl_*_<case>.nml)
# 与输出目录均按 CASE_NAME 自动区分。
if ( ! $?CASE_NAME  ) setenv CASE_NAME  "base"     # 案例名称（对应scaling_rules.csv中的case_name）
if ( ! $?CASE_TYPE  ) setenv CASE_TYPE  "standard" # 案例类型: standard | sector
if ( ! $?START_DATE ) setenv START_DATE "2022-09-01" # 开始日期 (YYYY-MM-DD)
if ( ! $?END_DATE   ) setenv END_DATE   "2022-09-30" # 结束日期 (YYYY-MM-DD)
setenv FIRST_DATE ${START_DATE}      # 用于判断是否用上一天的初始场
set YEAR  = `date -ud "$END_DATE" +%Y`
set month = `date -ud "$END_DATE" +%m`
#模拟初始日期+4天，即上个月最后一天；
#setenv POST_BEGIN_DATE `date -ud "${START_DATE} + 4 days" +%Y-%m-%d`
#setenv POST_END_DATE   "$END_DATE"
#echo "Post-processing date:$POST_BEGIN_DATE ~ $POST_END_DATE "

# ===== 计算资源配置 =====
setenv NPCOL 8                       # 进程列数
setenv NPROW 4                       # 进程行数

# ===== 机理配置（通常不需要修改）=====
setenv MECH "cb6r3_ae7_aq"           # 化学机制

# ===== 域配置 =====
setenv DOMAIN "D3"                   # 模拟域 (D1/D2/D3)
setenv GRID_NAME "SD_2013"           # 网格名称

# ===== 域相关参数（根据DOMAIN自动设置）=====
# 人为源排放文件前缀，用于构建 ${EM_AV_PREFIX}_${EMIS_DATE}
setenv EM_AV_PREFIX "comb_ArearateAB_cn03_"
#天然源排放文件前后缀，用于构建 ${MEGAN_PREFIX}${TODAYJ}${MEGAN_SUFFIX}
# 天然源排放文件后缀
setenv MEGAN_SUFFIX ".BDSNP.ncf"
if ("$DOMAIN" == "D1") then
    setenv EM_AV_PREFIX "comb_cn27_"
    setenv MEGAN_PREFIX "MEGANv32.BJ_27km."
else if ("$DOMAIN" == "D2") then
    setenv EM_AV_PREFIX "comb_cn09_AreaRate_"
    setenv MEGAN_PREFIX "MEGANv32.PRD_9km."
else if ("$DOMAIN" == "D3") then
    setenv EM_AV_PREFIX "comb_ArearateAB_cn03_"
    setenv MEGAN_PREFIX "MEGANv32.PRD_3km."
else
    echo "Error:Unsupported domain '$DOMAIN',Please choose D1、D2 or D3"
    exit 1
endif


# ===== 固定路径配置 =====
setenv CCTM_WORKDIR "/program/rain/Build_CMAQ/CMAQ_Project/CCTM/scripts"
setenv BLD "${CCTM_WORKDIR}/BLD_CCTM_v532_intel"
setenv INPDIR "/bigdata/CMAQ_input/devin/PRD/2022"
setenv OUTDIR_BASE "/home/devin/cmaq_output"

# ===== 气象、初始场、边界场路径 =====
setenv MET_PATH "${INPDIR}/mcip/${DOMAIN}"
setenv GRIDDESC "${MET_PATH}/GRIDDESC"

# ===== IC/BC路径与 IC-RB 模式 =====
setenv IC_RB_MODE "Y"
# IC_RB_MODE=Y: 使用 D3_devin 的 IC/BC，并在每个模拟日从 ICON 冷启动。
#               若 CASE_NAME 带 _ic，NML 规则和文件名自动使用去掉后缀的名称。
# IC_RB_MODE=N: 使用常规 IC/BC，并按模板原有逻辑续跑。
if ( ! $?IC_RB_MODE ) setenv IC_RB_MODE "N"
if ( "$IC_RB_MODE" == "Y" ) then
#    setenv IC_PATH "${INPDIR}/icon/devin/${DOMAIN}"
#    setenv BC_PATH "${INPDIR}/bcon/devin/${DOMAIN}"
    setenv IC_PATH "/mnt/167/devin/cmaq_output/CCTM_CGRID_base/202209_PRD_150X117_utc00"
    setenv BC_PATH "/bigdata/CMAQ_input/devin/PRD/bcon/${DOMAIN}_base"
else if ( "$IC_RB_MODE" == "N" ) then
    setenv IC_PATH "${INPDIR}/icon/${DOMAIN}"
    setenv BC_PATH "${INPDIR}/bcon/${DOMAIN}"
else
    echo "Error: IC_RB_MODE must be Y or N, got '$IC_RB_MODE'"
    exit 1
endif

# ===== 海洋和掩膜路径 =====
setenv CMAQ_MASKS "${INPDIR}/ocean/${DOMAIN}/${DOMAIN}_cmaq_masks"
setenv OCEAN_1_PATH "${INPDIR}/ocean/${DOMAIN}/oceanfile"

# ===== 排放路径 =====
setenv N_EMIS_GR 2
setenv AV_EMIS_DIR "${INPDIR}/emis/${DOMAIN}"
setenv BV_EMIS_DIR "${INPDIR}/emis/${DOMAIN}/MEGAN"

# ===== 排放控制 NML 配置 =====
# GENERATE_NML:Y=动态生成 per-case nml(默认,用 create_emissCtrl_nml.py 按 nml_config/ CSV 规则生成);
#               N=不重新生成,用 NML_PATH 指定的已有 nml(单 case 场景;批量多 case 请用 Y)。
setenv GENERATE_NML "N"
# GENERATE_NML=N 时使用:已有 per-case nml 文件全路径(相对本目录或绝对路径)
set NML_CASE_NAME = "$CASE_NAME"
if ( "$IC_RB_MODE" == "Y" ) set NML_CASE_NAME = "${CASE_NAME:s/_ic//}"
setenv NML_PATH "/program/rain/Build_CMAQ/CMAQ_Project/CCTM/devin_cmaq_scripts/cctm_scripts_v5.3.2/EmissCtrl_nml/EmissCtrl_${MECH}_${NML_CASE_NAME}.nml"

# ===== 高级选项（通常不需要修改）=====
setenv NZ 14                          # 垂直层数
setenv CONC_SPCS "ALL"                # 输出物种（ALL表示所有物种）
setenv AVG_CONC_SPCS "ALL"            # 平均浓度输出物种
setenv CONC_BLEV_ELEV "1 1"          # 浓度输出层范围
setenv ACONC_BLEV_ELEV "1 1"         # 平均浓度输出层范围
setenv APMDIAG_BLEV_ELEV "1 1"      #用来控制 CMAQ 气溶胶诊断文件 CCTM_APMDIAG 的垂直输出层范围

setenv CTM_MAXSYNC "300"              # 最大同步时间步长（秒）
setenv CTM_MINSYNC "60"               # 最小同步时间步长（秒）
setenv SIGMA_SYNC_TOP "0.7"           # 同步步长计算的顶层sigma值
setenv CTM_ADV_CFL "0.95"             # CFL数限制

# ===== 模板配置 =====
# cctm 运行脚本模板(run_manager 步骤2 基于它整行替换生成 per-case run_*.csh,相对本 cctm_scripts 目录)
setenv TEMPLATE_FILE "run_cctm_template.csh"

# ===== 运行选项 =====
setenv DELETE_AFTER_RUN "N"          # 运行后是否删除生成的脚本 (Y/N)

# ===== 后处理配置 =====
setenv ENABLE_POST_PROCESS "Y"       # 是否调用后处理脚本 (Y/N)

# 是否调用后处理脚本 (Y/N)：Y - 将调用后处理脚本(run_manager.csh 步骤5,与 v5.4.0.4 同套机制)
# 后处理脚本模板全路径(相对本 cctm_scripts_v5.3.2 目录):run_manager 步骤5 基于它生成 per-case
# 0_run_post_script_*.csh,目录与文件名由代码从该全路径拆出,当前表示post_scripts_v5.3.2需要和
# cctm_config.csh所在目录是同级目录
setenv POST_TEMPLATE_FILE "../post_scripts_v5.3.2/0_run_post_script.csh"

# ---- 以下为 0_run_post_script.csh 模板涉及的全部后处理变量(值=模板默认值)----
# run_manager 会把本配置文件中已定义的值替换进生成的 per-case 后处理脚本(未定义则用模板默认值),
# 需要覆盖时改这里即可。
# 注:DOMAIN/CASE_NAME/INPDIR 与上方 cctm 运行配置共用,不在此重复;
#    BEGIN_DATE/END_DATE 由 run_manager 从提取时间映射(见下方"后处理提取时间");
#    CCTMOUTDIR_ROOT 由 run_manager 派生为 ${OUTDIR_BASE}/${CASE_NAME}。
setenv APPL PRD                       #> Application Name (e.g. Gridname)
setenv VRSN v532                      #> Code Version
setenv PROC mpi                       #> serial or mpi
setenv LAYER 1                       #Layer=-1,extract all layers
setenv OUTPUT_COMBINE_ACONC_FILE T    #是否输出COMBINE ACONC文件(即浓度文件)
setenv OUTPUT_COMBINE_DEP_FILE F      #是否输出COMBINE DEP文件(即沉降文件)
# 后处理 COMBINE 合并文件输出目录(POSTDIR):为空时后处理脚本用默认 ${CCTMOUTDIR_ROOT}/post
setenv COMBINE_DIR "/mnt/167/devin/cmaq_output/${DOMAIN}_${APPL}_base_on_cgrid/${YEAR}${month}/${CASE_NAME}"
 #'/mnt/167/devin/cmaq_output/d3/202206'                 #是否指定Combine后处理目录,为空或未定义则用默认
setenv KEEP_18SPECIES_ONLY T          #是否仅保持18种物种
setenv INCLUDE_WRF F                  #是否包含 WRF 变量(设为 "T" 或 "F")
setenv OUTPUT_BY_YEARMONTH F          #是否按年月格式输出
setenv KEEP_COMBINE_FILE T            #是否保留提取前的文件(COMBINE 生成的原始文件)
setenv CLEANUP_CCTM_OUTPUT T          #combine后是否清理CCTM逐日输出(保留 *.cfg 与 CCTM_CGRID*)
setenv TSHIFT F                       #是否调整UTC时间为local时间
setenv HOUR_OFFSET 8                  #转为local时间的时区偏移小时数(仅 TSHIFT=T 生效)
setenv CONVERT2DAILY T                #是否转为daily
setenv OUTPUT_DAILY_MAP T             #是否输出daily map
setenv BOUNDARY_FILE '/program/software/PanoplyJ/boundary/gd_cities.shp' #边界文件
setenv PLOT_POLLUTANT 'O3_MDA8'       #绘图目标物种

if ( ! $?POST_BEGIN_DATE ) setenv POST_BEGIN_DATE  ${FIRST_DATE}
if ( ! $?POST_END_DATE ) setenv POST_END_DATE ${END_DATE}

if ( $LAYER == -1 ) then
   setenv LAYER_NAME all_layers
else
   setenv LAYER_NAME layer_${LAYER}
endif

setenv BASELINE_FILE "/mnt/167/devin/cmaq_output/d3/${YEAR}${month}/Daily_COMBINE_ACONC_${VRSN}_${DOMAIN}_base_${APPL}_${LAYER_NAME}_${POST_BEGIN_DATE}_${POST_END_DATE}_18species.nc"
#setenv BASELINE_FILE "/mnt/167/devin/cmaq_output/d3/${YEAR}${month}/Daily_COMBINE_ACONC_${VRSN}_${DOMAIN}_base_${APPL}_all_layers_${POST_BEGIN_DATE}_${POST_END_DATE}_18species.nc"
# 基线文件(模板默认值,为空或未定义则用默认)
#setenv BASELINE_FILE '/mnt/167/devin/cmaq_output/d3/202206/daily/Daily_COMBINE_ACONC_v532_D3_base_PRD_all_layers_2022-05-27_2022-06-30_18species.nc'
setenv OUTPUT_IC F                    #是否输出初始场
setenv OUTPUT_BC F                    #是否输出边界场
setenv IC_OUTPUT_DIR ''               #IC输出目录,空则用默认
setenv BC_OUTPUT_DIR ''               #BC输出目录,空则用默认
# ENABLE_POST_PROCESS=Y 时,后处理模板会校验 $CMAQ_HOME/POST/combine/scripts/
# BLD_combine_${VRSN}_${compilerString}/combine_${VRSN}.exe 是否存在,缺失仅告警不中断
# COPY_SPEC_DEF:是否把 0_run_post_script.csh 同级 spec_def_files/SpecDef_${MECH}_all_layers.txt
#               覆盖拷贝到 $CMAQ_HOME/POST/combine/scripts/spec_def_files/ 下(F=不拷贝,T=覆盖替换)
setenv COPY_SPEC_DEF F

# ===== 后处理提取时间(可选)=====
# 后处理提取的开始/结束时间:默认取模拟时间段(START_DATE~END_DATE)全部提取。
# 适用场景:跳过 spin-up(模拟提前起跑,只提取正式时段)、模拟中途续跑(续跑段起始晚于
#           原开始时间,但需提取完整时段而非仅续跑段)。
# 需要时取消注释并设置;不设置则用模拟时间段。
# setenv POST_BEGIN_DATE "2022-08-27"
# setenv POST_END_DATE   "2022-09-30"

echo "Configuration fileLoadingcompleted："
echo "  Case name: $CASE_NAME ($CASE_TYPE)"
echo "  Domain: $DOMAIN"
echo "  Date range: $START_DATE to $END_DATE"
echo "  ProcessConfiguration: ${NPCOL} × ${NPROW} = `expr $NPCOL \* $NPROW`"
echo "  Input data directory: $INPDIR"
echo "  Output data directory: $OUTDIR_BASE"
echo "  Emission prefix: $EM_AV_PREFIX"
echo "  MEGAN prefix: $MEGAN_PREFIX"
echo "  ICPath: $IC_PATH"
echo "  BCPath: $BC_PATH"
echo "  CMAQ_MASKS: $CMAQ_MASKS"
echo "  OCEAN_1_PATH: $OCEAN_1_PATH"
echo "  MET_PATH: $MET_PATH"
echo "  IC_RB_MODE: $IC_RB_MODE"
