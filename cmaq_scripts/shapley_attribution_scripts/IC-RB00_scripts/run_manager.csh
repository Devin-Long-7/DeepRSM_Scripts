#!/bin/csh -f
# ===================================================================
# 复用 v5.3.2 管理流程：配置 → NML → 脚本 → 校验 → 逐段运行 → 后处理。
# 用法：csh run_manager.csh [配置文件] [--dry-run]
# ===================================================================
set SCRIPT_DIR = `dirname "$0"`
cd "$SCRIPT_DIR"
set SCRIPT_DIR = "$cwd"
set CONFIG_FILE = "$SCRIPT_DIR/cctm_config.csh"
set DRY_RUN = 0
foreach a ($argv)
    if ( "$a" == "--dry-run" ) then
        set DRY_RUN = 1
    else
        set CONFIG_FILE = "$a"
    endif
end
if ( ! -f "$CONFIG_FILE" ) then
    echo "Error: configuration file not found: $CONFIG_FILE"
    exit 1
endif

# ===== 步骤 0：读取一次配置，计算共用参数 =====
source "$CONFIG_FILE"
if ( $status != 0 ) exit 1
if ( ! $?RESET_MODE ) setenv RESET_MODE reset
if ( ! $?PROPAGATED_ROOT ) setenv PROPAGATED_ROOT ""
if ( ! -x "$PYTHON_CMD" ) then
    set python_fallback = `which python3`
    if ( $status != 0 ) then
        echo "Error: neither configured Python nor system python3 is available"
        exit 1
    endif
    setenv PYTHON_CMD "$python_fallback"
endif
if ( "$MPI_BIN" != "" ) setenv PATH "${MPI_BIN}:${PATH}"
# 配置中的相对路径只在这里转换一次。
foreach key ( TEMPLATE_FILE NML_PATH NML_GENERATOR POST_TEMPLATE_FILE POST_SPEC_FILE CCTM_WORKDIR BLD INPDIR OUTDIR_BASE MET_PATH GRIDDESC BASELINE_CGRID_ROOT BC_PATH CMAQ_MASKS OCEAN_1_PATH AV_EMIS_DIR BV_EMIS_DIR COMBINE_DIR )
    set value = "`printenv $key`"
    if ( "$value" != "" && "$value" !~ /* ) setenv $key "${SCRIPT_DIR}/${value}"
end
set first_jday = `date -ud "$START_DATE" +%Y%j`
if ( $status != 0 ) exit 1
set last_jday = `date -ud "$END_DATE" +%Y%j`
if ( $status != 0 ) exit 1
if ( $first_jday > $last_jday ) then
    echo "Error: START_DATE is after END_DATE"
    exit 1
endif
# 原版使用该月第一组周五/六/日作为工作日/周六/周日代表日。
set month_weekday = `date -ud "${EMIS_MONTH}-01" +%u`
if ( $status != 0 ) exit 1
@ friday_offset = ( 5 - $month_weekday + 7 ) % 7
set friday = `date -ud "${EMIS_MONTH}-01 + ${friday_offset} days" +%F`
setenv EMIS_OTH `date -ud "$friday" +%Y%j`
setenv EMIS_SAT `date -ud "$friday + 1 day" +%Y%j`
setenv EMIS_SUN `date -ud "$friday + 2 days" +%Y%j`

# generated 与结果均按本次运行隔离；不覆盖已有目录。
mkdir -p "$SCRIPT_DIR/generated"
set GENERATED_DIR = `mktemp -d "${SCRIPT_DIR}/generated/${CASE_NAME}_XXXXXXXX"`
if ( $status != 0 ) exit 1
set run_id = `basename "$GENERATED_DIR"`
setenv CASE_ROOT "${OUTDIR_BASE}"
mkdir "$GENERATED_DIR/scripts" "$GENERATED_DIR/logs"
cp "$CONFIG_FILE" "$GENERATED_DIR/config_used.csh"
echo "Configuration: $CASE_NAME; CST $START_DATE to $END_DATE"
echo "Generated scripts: $GENERATED_DIR"
echo "Model output: $CASE_ROOT"

# ===== 步骤 1：复用原版 NML 文件/生成器，保存本次副本 =====
# CMAQ v5.3 has a fixed-size path buffer for this setting.  The generated
# directory already isolates scenarios, so the NML filename need not repeat
# the full case name.
setenv EMISSCTRL_NML "$GENERATED_DIR/EmissCtrl_${MECH}.nml"
if ( "$GENERATE_NML" == "Y" ) then
    "$PYTHON_CMD" "$NML_GENERATOR" --case-name "$CASE_NAME" --case-type "$CASE_TYPE" --output "$EMISSCTRL_NML"
else
    cp "$NML_PATH" "$EMISSCTRL_NML"
endif
if ( $status != 0 ) exit 1

# ===== 步骤 2：沿用原版 sed 替换共用设置，再生成每天两段 =====
set SCRIPT_PATH = "$GENERATED_DIR/common_template.csh"
setenv OUTDIR "@SEGMENT_OUTDIR@"
cp "$TEMPLATE_FILE" "$SCRIPT_PATH"
if ( $status != 0 ) exit 1
# 模板变量替换(与 v5.4.0.4 同套机制:基于真实模板 复制 + sed 整行替换)
# 模板保留原版变量位置，以占位符表示待填的配置值，不能直接运行；
# 每条 sed 按"行首关键字+正则"定位要改的那一行,把整行重写为配置值。
# 配置值不要含空格以外的 shell 特殊字符；路径不要含空格。

# 基本案例参数替换
sed -i 's/set CASE_NAME.*/set CASE_NAME   = '"$CASE_NAME"'/' $SCRIPT_PATH
sed -i 's/set START_DATE.*/set START_DATE = "'"$START_DATE"'"/' $SCRIPT_PATH
sed -i 's/set END_DATE.*/set END_DATE   = "'"$END_DATE"'"/' $SCRIPT_PATH
sed -i 's/set firstday.*/set firstday   = "'"$FIRST_DATE"'"/' $SCRIPT_PATH
sed -i 's/set APPL.*/set APPL   = '"$APPL"'/' $SCRIPT_PATH

# 计算资源参数替换
# 只替换 NPCOL/NPROW 的数值,避免 .* 把同一行里的 @ NPROW、注释等一起吃掉(会导致 NPROW 丢失)
sed -i 's/@ NPCOL[[:space:]]*=[[:space:]]*[^; ]*/@ NPCOL  =  '"$NPCOL"'/' $SCRIPT_PATH
sed -i 's/@ NPROW[[:space:]]*=[[:space:]]*[^; ]*/@ NPROW = '"$NPROW"'/' $SCRIPT_PATH

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

# CST00 新增的共用参数；MPIRUN 使用模板默认值，不做替换。
sed -i \
    -e 's|^setenv MPI_BIN .*|setenv MPI_BIN "'"$MPI_BIN"'"|' \
    -e 's|^setenv I_MPI_FABRICS .*|setenv I_MPI_FABRICS '"$I_MPI_FABRICS"'|' \
    -e 's|^setenv OMP_NUM_THREADS .*|setenv OMP_NUM_THREADS '"$OMP_NUM_THREADS"'|' \
    -e 's|^[[:space:]]*set VRSN[[:space:]].*|set VRSN = '"$VRSN"'|' \
    -e 's|^[[:space:]]*set PROC[[:space:]].*|set PROC = '"$PROC"'|' \
    -e 's|^[[:space:]]*set EMIS_OTH[[:space:]].*|set EMIS_OTH = '"$EMIS_OTH"'|' \
    -e 's|^[[:space:]]*set EMIS_SAT[[:space:]].*|set EMIS_SAT = '"$EMIS_SAT"'|' \
    -e 's|^[[:space:]]*set EMIS_SUN[[:space:]].*|set EMIS_SUN = '"$EMIS_SUN"'|' "$SCRIPT_PATH"
set common_template = "$SCRIPT_PATH"
set run_scripts = ()
set local_day = "$START_DATE"
set local_jday = $first_jday
printf 'CST_day\tsegment\tUTC_day\tstart\tduration\trestart\toutput\n' > "$GENERATED_DIR/segments.tsv"
while ( $local_jday <= $last_jday )
    set day_tag = `date -ud "$local_day" +%Y%m%d`
    set previous_day = `date -ud "$local_day - 1 day" +%F`
    set previous_day_tag = `date -ud "$previous_day" +%Y%m%d`
    set previous_jday = `date -ud "$previous_day" +%Y%j`
    set previous_month = `date -ud "$previous_day" +%Y/%m`

    foreach segment (seg01 seg02)
        set restart_pending = 0
        set generated_pending = 0
        if ( "$segment" == "seg01" ) then
            # CST 00–08。reset uses the UTC16 baseline; propagate continues
            # the previous local day's controlled segment; ic_only starts
            # from the previous local day's propagated C11 segment.
            set utc_day = "$previous_day"
            set start_time = 160000
            set run_length = 080000
            set restart_file = "$BASELINE_CGRID_ROOT/CCTM_CGRID_${APPL}_${previous_jday}.nc"
            if ( ! -f "$restart_file" ) then
                 set restart_file = "$BASELINE_CGRID_ROOT/ICON_${previous_jday}_UTC16"
            endif
            if ( "$RESET_MODE" == "propagate" ) then
                if ( "$local_day" != "$START_DATE" ) then
                    set restart_file = "$CASE_ROOT/$previous_day_tag/seg02/$DOMAIN/$previous_month/CCTM_CGRID_${APPL}_${previous_jday}.nc"
                endif
            else if ( "$RESET_MODE" == "ic_only" ) then
                if ( "$PROPAGATED_ROOT" == "" ) then
                    echo "Error: PROPAGATED_ROOT is required for RESET_MODE=ic_only"
                    exit 1
                endif
                set restart_file = "$PROPAGATED_ROOT/$previous_day_tag/seg02/$DOMAIN/$previous_month/CCTM_CGRID_${APPL}_${previous_jday}.nc"
            else if ( "$RESET_MODE" != "reset" ) then
                echo "Error: unsupported RESET_MODE=$RESET_MODE (reset|propagate|ic_only)"
                exit 1
            endif
            # The next day's propagated seg01 is produced by this scenario's
            # previous seg02.  It is unavailable while the full plan is being
            # generated, but will exist when execution reaches that segment.
            if ( "$RESET_MODE" == "propagate" && "$local_day" != "$START_DATE" ) then
                set generated_pending = 1
            endif
        else
            # seg02 always consumes the CGRID written by this day's seg01.
            set generated_pending = 1
            # CST 08–24：接续本日 seg01；这里绝不再次重置 baseline。
            set utc_day = "$local_day"
            set start_time = 000000
            set run_length = 160000
            set restart_file = "$CASE_ROOT/$day_tag/seg01/$DOMAIN/$previous_month/CCTM_CGRID_${APPL}_${previous_jday}.nc"
        endif
        if ( ! -f "$restart_file" && ! -e "$restart_file" ) then
            if ( $DRY_RUN == 1 || $generated_pending == 1 ) then
                echo "Pending restart (will be produced before execution): $restart_file"
                set restart_pending = 1
            else
                echo "Error: restart file not found: $restart_file"
                exit 1
            endif
        endif
        set utc_month = `date -ud "$utc_day" +%Y/%m`
        set segment_output = "$CASE_ROOT/$day_tag/$segment/$DOMAIN/$utc_month"
        set SCRIPT_PATH = "$GENERATED_DIR/scripts/${day_tag}_${segment}.csh"
        cp "$common_template" "$SCRIPT_PATH"
        sed -i \
            -e 's|^set START_DATE.*|set START_DATE = "'"$utc_day"'"|' \
            -e 's|^set END_DATE.*|set END_DATE = "'"$utc_day"'"|' \
            -e 's|^[[:space:]]*set STTIME[[:space:]].*|set STTIME = '"$start_time"'|' \
            -e 's|^[[:space:]]*set NSTEPS[[:space:]].*|set NSTEPS = '"$run_length"'|' \
            -e 's|^[[:space:]]*set RESTART_FILE[[:space:]].*|set RESTART_FILE = '"$restart_file"'|' \
            -e 's|^[[:space:]]*setenv OUTDIR[[:space:]].*|setenv OUTDIR '"$segment_output"'|' "$SCRIPT_PATH"
        chmod +x "$SCRIPT_PATH"
        printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$local_day" "$segment" "$utc_day" "$start_time" "$run_length" "$restart_file" "$segment_output" >> "$GENERATED_DIR/segments.tsv"
        set run_scripts = ($run_scripts "$SCRIPT_PATH")
        echo "Prepare CST $local_day $segment : UTC $utc_day $start_time + $run_length"
        # 尚未运行时 seg02 初始场应由 seg01 产生，允许暂不存在。
        set validate_args = ()
        if ( "$segment" == "seg02" || $restart_pending == 1 ) set validate_args = (--pending-restart)
        csh "$SCRIPT_DIR/validate_script.csh" "$SCRIPT_PATH" $validate_args >>& "$GENERATED_DIR/logs/validation.log"
        if ( $status != 0 ) then
            echo "Error: input validation failed; see $GENERATED_DIR/logs/validation.log"
            exit 1
        endif
    end
    set local_day = `date -ud "$local_day + 1 day" +%F`
    set local_jday = `date -ud "$local_day" +%Y%j`
end

# 后处理也先生成可检查的脚本和计划，确认依赖齐全后才启动模拟。
if ( "$ENABLE_POST_PROCESS" == "Y" ) then
    "$PYTHON_CMD" "$SCRIPT_DIR/post/run_post.py" prepare "$GENERATED_DIR/post" "$CASE_ROOT"
    if ( $status != 0 ) exit 1
endif
if ( $DRY_RUN == 1 ) then
    echo "Dry-run complete: $#run_scripts segments; see $GENERATED_DIR/segments.tsv"
    exit 0
endif

# ===== 步骤 3/4：逐段校验、运行，任一失败立即停止本情景 =====
mkdir -p "$OUTDIR_BASE"
mkdir -p "$CASE_ROOT"
if ( $status != 0 ) exit 1
printf '%s\n' "$CASE_ROOT" > "$CASE_ROOT/.icrb_run"
foreach SCRIPT_PATH ($run_scripts)
    set segment_name = `basename "$SCRIPT_PATH" .csh`
    csh "$SCRIPT_DIR/validate_script.csh" "$SCRIPT_PATH" >>& "$GENERATED_DIR/logs/validation.log"
    if ( $status != 0 ) exit 1
    # 单独工作目录隔离 CMAQ 日志、buff 和 cfg。
    set segment_work = "$GENERATED_DIR/logs/$segment_name"
    mkdir "$segment_work"
    cd "$segment_work"
    echo "Run: $segment_name"
    csh "$SCRIPT_PATH" >&! "$segment_work/run.log"
    set run_status = $status
    cd "$SCRIPT_DIR"
    if ( $run_status != 0 ) then
        echo "Error: simulation failed; see $segment_work/run.log"
        exit $run_status
    endif
    "$PYTHON_CMD" "$SCRIPT_DIR/post/check_restart.py" --output "$SCRIPT_PATH"
    if ( $status != 0 ) exit 1
end

# ===== 步骤 5/6：整情景后处理 → 结果校验 → 按配置清理 =====
if ( "$ENABLE_POST_PROCESS" == "Y" ) then
    "$PYTHON_CMD" "$SCRIPT_DIR/post/run_post.py" run "$GENERATED_DIR/post"
    if ( $status != 0 ) exit 1
endif
echo "Scenario complete: $CASE_NAME; output: $CASE_ROOT"
exit 0
