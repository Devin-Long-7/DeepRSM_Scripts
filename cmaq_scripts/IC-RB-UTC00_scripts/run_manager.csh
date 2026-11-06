#!/bin/csh -f

# ===================================================================
# CMAQ v5.3.2 脚本管理器
# 用法: ./run_manager.csh
# 流程: 加载配置 → 生成NML → 生成脚本 → 验证 → 运行
# ===================================================================

echo "=========================================="
echo "CMAQ v5.3.2 Script manager"
echo "=========================================="

# 设置目录和文件
setenv CONFIG_FILE "cctm_config.csh"
# 参数解析:
#   ./run_manager.csh                                -> 默认 cctm_config.csh
#   ./run_manager.csh run_configs/run_config_X.csh   -> 用指定配置文件
#   ./run_manager.csh --dry-run [配置文件]           -> 只生成+校验,不执行/后处理(生成脚本保留供检查)
# --dry-run 与配置文件参数可任意顺序组合
set DRY_RUN = 0
set CONFIG_ARG = ""
foreach a ($argv)
    if ("$a" == "--dry-run") then
        set DRY_RUN = 1
    else
        set CONFIG_ARG = "$a"
    endif
end
if ("$CONFIG_ARG" != "") then
    setenv CONFIG_FILE "$CONFIG_ARG"
endif
setenv GENERATED_DIR "generated"

# 检查配置文件
if (! -f $CONFIG_FILE) then
    echo "Error: Configuration file '$CONFIG_FILE' does not exist"
    exit 1
endif

# ===================================================================
# 步骤0: 加载配置
# ===================================================================
echo "Step0: Loading Configuration file..."
source $CONFIG_FILE

# 检查模板文件(TEMPLATE_FILE 由 cctm_config.csh 定义,与 v5.4.0.4 保持一致)
if (! -f $TEMPLATE_FILE) then
    echo "Error: Template file '$TEMPLATE_FILE' does not exist"
    exit 1
endif

# 计算派生变量
setenv YEAR `date -ud "$END_DATE" +%Y`
setenv MONTH `date -ud "$END_DATE" +%m`
setenv NPROCS `expr $NPCOL \* $NPROW`
setenv OUTDIR "${OUTDIR_BASE}/${CASE_NAME}/${DOMAIN}/${YEAR}/${MONTH}"
# MECH 默认值;cctm_config.csh 若已定义则保留配置值
if ( ! $?MECH ) setenv MECH "cb6r3_ae7_aq"
if ( ! $?IC_RB_MODE ) setenv IC_RB_MODE "N"
set NML_CASE_NAME = "$CASE_NAME"
if ( "$IC_RB_MODE" == "Y" ) set NML_CASE_NAME = "${CASE_NAME:s/_ic//}"

# 创建generated目录
if (! -d $GENERATED_DIR) then
    mkdir -p $GENERATED_DIR
endif

echo "  Configuration: $CASE_NAME ($CASE_TYPE) $DOMAIN $START_DATE to $END_DATE"
echo ""

# ===================================================================
# 步骤1: 排放控制 NML 配置
# ===================================================================
# GENERATE_NML:Y=动态生成 per-case nml(默认,用 create_emissCtrl_nml.py 按 nml_config/ CSV 规则生成);
#               N=不重新生成,用 cctm_config.csh 里 NML_PATH 指定的已有 nml。
if ( ! $?GENERATE_NML ) setenv GENERATE_NML "Y"
if ( "$GENERATE_NML" == "Y" ) then
    echo "Step1: Generate emission-control NML file..."
    set NML_OUTPUT = "${GENERATED_DIR}/EmissCtrl_${MECH}_${CASE_NAME}.nml"
    # Prefer the devin_env Python runtime used by post-processing scripts.
    set DEVIN_PYTHON = "/program/software/devin_env/bin/python3"
    set PYTHON_CMD = ""
    if (-x "$DEVIN_PYTHON") then
        set PYTHON_CMD = "$DEVIN_PYTHON"
    else
        # Fall back to the system python3 when devin_env is unavailable.
        set SYSTEM_PYTHON = `which python3`
        if ($status == 0 && -x "$SYSTEM_PYTHON") then
            set PYTHON_CMD = "$SYSTEM_PYTHON"
        endif
    endif
    if ("$PYTHON_CMD" == "") then
        echo "Error: neither devin_env Python nor system python3 is available"
        exit 1
    endif
    "$PYTHON_CMD" create_emissCtrl_nml.py \
        --case-name $NML_CASE_NAME \
        --case-type $CASE_TYPE \
        --output $NML_OUTPUT
    if ($status != 0) then
        echo "  Error: NML generation failed"
        exit 1
    endif
    setenv EMISSCTRL_NML "$cwd/${NML_OUTPUT}"
    echo "  completed: $EMISSCTRL_NML"
else
    echo "Step1: Use existing NML file..."
    if ( "$NML_PATH" == "" ) then
        echo "  Error: GENERATE_NML=N but NML_PATH as empty(in cctm_config.csh set points to existing of per-case nml file)"
        exit 1
    endif
    if (! -f $NML_PATH) then
        echo "  Error: NML file does not exist: $NML_PATH"
        exit 1
    endif
    setenv EMISSCTRL_NML "$NML_PATH"
    echo "  Using: $EMISSCTRL_NML"
endif
echo ""

# ===================================================================
# 步骤2: 生成运行脚本
# ===================================================================
echo "Step2: generate Run script..."

# 生成脚本文件名
set TIMESTAMP = `date -u +%Y%m%d_%H%M%S`
set START_MMDD = `echo $START_DATE | cut -d'-' -f2,3 | tr -d '-'`
set END_MMDD = `echo $END_DATE | cut -d'-' -f2,3 | tr -d '-'`
set DATE_RANGE = "${START_MMDD}-${END_MMDD}"
set SCRIPT_NAME = "run_${CASE_NAME}_${DOMAIN}_${DATE_RANGE}_${TIMESTAMP}.csh"
set SCRIPT_PATH = "${GENERATED_DIR}/${SCRIPT_NAME}"

# 复制模板
cp $TEMPLATE_FILE $SCRIPT_PATH

# 模板变量替换(与 v5.4.0.4 同套机制:基于真实模板 复制 + sed 整行替换)
# 模板 run_cctm_template.csh 本身是可直接运行的脚本,值=cctm_config.csh 默认值;
# 每条 sed 按"行首关键字+正则"定位要改的那一行,把整行重写为配置值。
# 值内请避免字符 |(sed 分隔符)。

# 基本案例参数替换
sed -i 's/set CASE_NAME.*/set CASE_NAME   = '"$CASE_NAME"'/' $SCRIPT_PATH
sed -i 's/set START_DATE.*/set START_DATE = "'"$START_DATE"'"/' $SCRIPT_PATH
sed -i 's/set END_DATE.*/set END_DATE   = "'"$END_DATE"'"/' $SCRIPT_PATH
sed -i 's/set firstday.*/set firstday   = "'"$FIRST_DATE"'"/' $SCRIPT_PATH
sed -i 's/setenv IC_RB_MODE.*/setenv IC_RB_MODE '"$IC_RB_MODE"'/' $SCRIPT_PATH
sed -i 's/set APPL.*/set APPL   = '"$APPL"'/' $SCRIPT_PATH

# 计算资源参数替换
# 只替换 NPCOL/NPROW 的数值,避免 .* 把同一行里的 @ NPROW、注释等一起吃掉(会导致 NPROW 丢失)
sed -i 's/@ NPCOL[[:space:]]*=[[:space:]]*[0-9]*/@ NPCOL  =  '"$NPCOL"'/' $SCRIPT_PATH
sed -i 's/@ NPROW[[:space:]]*=[[:space:]]*[0-9]*/@ NPROW = '"$NPROW"'/' $SCRIPT_PATH

# 机理参数替换
# 锚定行首(set MECH 后须为空白),避免误改 "# set MECH..." 注释行;保留模板的 "set MECH  = " 写法
sed -i 's|^[[:space:]]*set MECH[[:space:]].*|set MECH      = '"$MECH"'|' $SCRIPT_PATH

# 域参数替换（按config文件顺序）
sed -i 's/setenv GRID_NAME.*/setenv GRID_NAME '"$GRID_NAME"'/' $SCRIPT_PATH
# DOMAIN 保持模板无引号写法(set DOMAIN = D3),与 MECH 同理锚定行首
sed -i 's|^[[:space:]]*set DOMAIN[[:space:]].*|set DOMAIN = '"$DOMAIN"'|' $SCRIPT_PATH

# 固定路径替换
sed -i 's|setenv CCTM_WORKDIR.*|setenv CCTM_WORKDIR '"$CCTM_WORKDIR"'|' $SCRIPT_PATH
sed -i 's|set BLD.*|set BLD =  '"$BLD"'|' $SCRIPT_PATH
# INPDIR 锚定行首:模板底部内嵌后处理块里有 sed -i "s/setenv INPDIR ..." 嵌套行,
# 若不锚定会被误替换成损坏的半行
sed -i 's|^[[:space:]]*setenv INPDIR.*|setenv INPDIR '"$INPDIR"'|' $SCRIPT_PATH
sed -i 's|setenv OUTDIR.*|setenv OUTDIR '"$OUTDIR"'|' $SCRIPT_PATH

#气象、初始场、边界场路径配置
# METpath 模板里定义两处(初始 na + 每日循环内),整行替换后两处都用配置值,无副作用
sed -i 's|set METpath.*|set METpath = '"$MET_PATH"'|' $SCRIPT_PATH
sed -i 's|setenv GRIDDESC.*|setenv GRIDDESC '"$GRIDDESC"'|' $SCRIPT_PATH
#需要特别注意，ICpath有两个地方定义，仅需替换第一个位置(靠 4 空格写法区分,另一处为 "set ICpath = $OUTDIR")
sed -i 's|set ICpath    =.*|set ICpath    = '"$IC_PATH"'|' $SCRIPT_PATH
sed -i 's|set BCpath.*|set BCpath    = '"$BC_PATH"'|' $SCRIPT_PATH

#排放参数替换
sed -i 's/setenv N_EMIS_GR.*/setenv N_EMIS_GR '"$N_EMIS_GR"'/' $SCRIPT_PATH
#人为排放路径替换
# 注意:必须先替换 epath2(天然源)再替换 epath(人为源),且都锚定行首 + 要求后面是空白,
# 否则 "set epath" 会匹配到 "set epath2" 把天然源路径吃掉
sed -i 's|^[[:space:]]*set epath2[[:space:]].*|set epath2 = '"$BV_EMIS_DIR"'|' $SCRIPT_PATH
sed -i 's|^[[:space:]]*set epath[[:space:]].*|set epath  = '"$AV_EMIS_DIR"'|' $SCRIPT_PATH
# 排放文件整行替换(GR_EMIS_001/002 为唯一活动行,整行重写最稳妥;${EMIS_DATE}/${TODAYJ} 为模板运行时变量,保留)
sed -i 's|setenv GR_EMIS_001.*|setenv GR_EMIS_001 '"$AV_EMIS_DIR"'/'"$EM_AV_PREFIX"'${EMIS_DATE}|' $SCRIPT_PATH
sed -i 's|setenv GR_EMIS_002.*|setenv GR_EMIS_002 '"$BV_EMIS_DIR"'/'"$MEGAN_PREFIX"'${TODAYJ}'"$MEGAN_SUFFIX"'|' $SCRIPT_PATH

#排放空间掩膜文件及CMAQ控制文件路径替换
sed -i 's|setenv CMAQ_MASKS.*|setenv CMAQ_MASKS '"$CMAQ_MASKS"'|' $SCRIPT_PATH
sed -i 's|setenv OCEAN_1.*|setenv OCEAN_1 '"$OCEAN_1_PATH"'|' $SCRIPT_PATH
sed -i 's|setenv EMISSCTRL_NML.*|setenv EMISSCTRL_NML '"$EMISSCTRL_NML"'|' $SCRIPT_PATH

# 高级选项替换（按config文件顺序）
sed -i 's/set NZ.*/set NZ = '"$NZ"'/' $SCRIPT_PATH
sed -i 's/setenv CONC_SPCS.*/setenv CONC_SPCS "'"$CONC_SPCS"'"/' $SCRIPT_PATH
sed -i 's/setenv AVG_CONC_SPCS.*/setenv AVG_CONC_SPCS "'"$AVG_CONC_SPCS"'"/' $SCRIPT_PATH
sed -i 's/setenv CONC_BLEV_ELEV.*/setenv CONC_BLEV_ELEV "'"$CONC_BLEV_ELEV"'"/' $SCRIPT_PATH
sed -i 's/setenv ACONC_BLEV_ELEV.*/setenv ACONC_BLEV_ELEV "'"$ACONC_BLEV_ELEV"'"/' $SCRIPT_PATH

sed -i 's/setenv APMDIAG_BLEV_ELEV.*/setenv APMDIAG_BLEV_ELEV "'"$APMDIAG_BLEV_ELEV"'"/' $SCRIPT_PATH

sed -i 's/setenv CTM_MAXSYNC.*/setenv CTM_MAXSYNC '"$CTM_MAXSYNC"'/' $SCRIPT_PATH
sed -i 's/setenv CTM_MINSYNC.*/setenv CTM_MINSYNC '"$CTM_MINSYNC"'/' $SCRIPT_PATH
sed -i 's/setenv SIGMA_SYNC_TOP.*/setenv SIGMA_SYNC_TOP '"$SIGMA_SYNC_TOP"'/' $SCRIPT_PATH
sed -i 's/setenv CTM_ADV_CFL.*/setenv CTM_ADV_CFL '"$CTM_ADV_CFL"'/' $SCRIPT_PATH

chmod +x $SCRIPT_PATH
echo "  generate script: $SCRIPT_PATH"
echo ""

# ===================================================================
# 步骤3: 校验数据文件
# ===================================================================
echo "Step3: Validate data files..."

set VALIDATE_SCRIPT = "validate_script.csh"
if (-f $VALIDATE_SCRIPT) then
    ./$VALIDATE_SCRIPT $SCRIPT_PATH
    if ($status != 0) then
        echo "  validation failed"
        exit 1
    endif
    echo "  validation passed"
else
    echo "  Warning: validation script does not exist，skip validation"
endif
echo ""

# ===================================================================
# dry-run 模式:只生成+校验,不执行/后处理,生成脚本保留供检查
# ===================================================================
if ($DRY_RUN == 1) then
    echo "=========================================="
    echo "dry-run mode: skip Execute and Post-processing"
    echo "  generate script: $SCRIPT_PATH (kept)"
    echo "=========================================="
    exit 0
endif

# ===================================================================
# 步骤4: 执行
# ===================================================================
echo "Step4: Execute CCTM..."
echo "  Execution started: `date`"

./$SCRIPT_PATH
set run_status = $status

echo "  Execute completed: `date`"
if ($run_status == 0) then
    echo "  CMAQ Run succeeded"
else
    echo "  CMAQ Run failed (exit code: $run_status)"
    exit $run_status
endif
echo ""

# ===================================================================
# 步骤5: 后处理
# ===================================================================
# 与 v5.4.0.4 同套机制:基于后处理模板 0_run_post_script.csh 复制 + sed 替换,
# 生成 per-case 脚本(generated/0_run_post_script_*.csh)再执行,便于事后核查每个 case 的后处理参数。
# 提取时间默认取模拟时间段;需要跳过 spin-up、或续跑时提取完整时段,可在 cctm_config.csh 配置
# POST_BEGIN_DATE/POST_END_DATE。
set manager_status = 0
if ("$ENABLE_POST_PROCESS" == "Y") then
    echo "Step5: Run post-processing..."

    # 后处理模板:全路径在 cctm_config.csh 配置(POST_TEMPLATE_FILE),这里拆出目录与文件
    set POST_TEMPLATE = "$POST_TEMPLATE_FILE"
    set POST_SCRIPT_DIR = `dirname "$POST_TEMPLATE_FILE"`

    if (-f $POST_TEMPLATE) then
        set POST_SCRIPT_NAME = "0_run_post_script_${CASE_NAME}_${DOMAIN}_${DATE_RANGE}_${TIMESTAMP}.csh"
        set POST_SCRIPT_PATH = "${GENERATED_DIR}/${POST_SCRIPT_NAME}"
        cp $POST_TEMPLATE $POST_SCRIPT_PATH

        # 固化 script_path 指向 post 目录绝对路径:生成脚本位于 generated/,
        # 若按 $0 推导,定位 config_cmaq.csh 与调用兄弟脚本都会失败。
        set POST_SCRIPT_DIR_ABS = `cd $POST_SCRIPT_DIR && pwd`
        sed -i 's|set script_path =.*|set script_path = '"$POST_SCRIPT_DIR_ABS"'|' $POST_SCRIPT_PATH
        # 明确写入 CCTM 工作目录，保证生成后的后处理脚本可独立重跑，
        # 不依赖 run_manager 进程导出的环境变量。
        sed -i '3i setenv CCTM_WORKDIR '"$CCTM_WORKDIR"'' $POST_SCRIPT_PATH

        # 后处理提取时间:默认取模拟时间段全部提取;配置了 POST_BEGIN_DATE/POST_END_DATE 则优先用配置值。
        # 模板里对应的是 BEGIN_DATE/END_DATE,这里映射好,供下方通用替换循环使用。
        if ( ! $?POST_BEGIN_DATE ) setenv POST_BEGIN_DATE $START_DATE
        if ( ! $?POST_END_DATE )   setenv POST_END_DATE   $END_DATE
        setenv BEGIN_DATE $POST_BEGIN_DATE
        setenv END_DATE   $POST_END_DATE
        setenv CCTMOUTDIR_ROOT ${OUTDIR_BASE}/${CASE_NAME}

        # 通用变量替换:遍历后处理模板全部 setenv 变量,cctm_config.csh(或上面的派生值)
        # 定义了哪个就替换哪个,未定义的后处理变量保留模板默认值。
        # 用词边界 \b(而非依赖空格)避免 "setenv LAYER" 误匹配 "setenv LAYER_NAME" 等,
        # .* 兜底,模板里多空格/少空格都能命中;统一加双引号写值(csh 对有无引号等价)。
        # 值内请避免字符 |(sed 分隔符)。
        set POST_VARS = ( VRSN PROC MECH LAYER APPL DOMAIN CASE_NAME INPDIR BEGIN_DATE END_DATE \
                          CCTMOUTDIR_ROOT COMBINE_DIR OUTPUT_COMBINE_ACONC_FILE OUTPUT_COMBINE_DEP_FILE \
                          KEEP_18SPECIES_ONLY INCLUDE_WRF OUTPUT_BY_YEARMONTH KEEP_COMBINE_FILE \
                          CLEANUP_CCTM_OUTPUT \
                          TSHIFT HOUR_OFFSET CONVERT2DAILY OUTPUT_DAILY_MAP \
                          BOUNDARY_FILE PLOT_POLLUTANT BASELINE_FILE OUTPUT_IC OUTPUT_BC \
                          IC_OUTPUT_DIR BC_OUTPUT_DIR COPY_SPEC_DEF )
        foreach v ($POST_VARS)
            set val = `printenv $v`
            if ($status == 0) then
                sed -i 's|^setenv '$v'\b.*|setenv '$v' "'"$val"'"|' $POST_SCRIPT_PATH
            endif
        end

        chmod +x $POST_SCRIPT_PATH
        echo "  generate Post-processing script: $POST_SCRIPT_PATH"
        echo "    CASE_NAME=$CASE_NAME  DOMAIN=$DOMAIN  Simulation ${START_DATE}~${END_DATE}, Extraction ${POST_BEGIN_DATE}~${POST_END_DATE}"
        echo "    INPDIR=$INPDIR"
        echo "    CCTMOUTDIR_ROOT=$CCTMOUTDIR_ROOT"
        ./$POST_SCRIPT_PATH
        set post_status = $status

        if ($post_status == 0) then
            echo "  ✓ Post-processing succeeded"
        else
            echo "  ⚠ Post-processing failed(exit code: $post_status)"
            set manager_status = $post_status
        endif
    else
        echo "  Warning: Post-processing Template does not exist: $POST_TEMPLATE"
        set manager_status = 1
    endif
else
    echo "Step5: Post-processing disabled"
endif

# 日志清扫:移除运行目录残留的 CTM_LOG_*,避免影响下一个 case
# (与 legacy/run_cctm_D3_202209.csh 末尾一致:按 case 归档到 LOGS/${CASE_NAME})
# 正常情况模板已按天把 CTM_LOG_???.${APPL} 移入 $cwd/LOGS;这里兜底清扫中途 break 等残留的日志
setenv LOGDIR_CASE  $cwd/LOGS/${CASE_NAME}
if (! -e ${LOGDIR_CASE} ) then
    mkdir -p ${LOGDIR_CASE}
endif
mv CTM_LOG_* ${LOGDIR_CASE} >& /dev/null

# ===================================================================
# 步骤6: 清理
# ===================================================================
if ("$DELETE_AFTER_RUN" == "Y") then
    echo "Clean generated scripts..."
    rm -f $SCRIPT_PATH
    if ($?POST_SCRIPT_PATH) then
        rm -f $POST_SCRIPT_PATH
    endif
    echo "  Script deleted"
else
    echo "Keep generated script: $SCRIPT_PATH"
    if ($?POST_SCRIPT_PATH) then
        echo "keep Post-processing script: $POST_SCRIPT_PATH"
    endif
endif

echo ""
echo "=========================================="
echo "CMAQ v5.3.2 Script manager finished"
echo "=========================================="
exit $manager_status
