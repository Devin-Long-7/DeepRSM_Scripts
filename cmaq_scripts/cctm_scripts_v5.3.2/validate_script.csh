#!/bin/csh -f

# ===================================================================
# CMAQ v5.3.2 数据文件校验脚本
# 用法: ./validate_script.csh <生成的脚本路径>
# 检查关键输入文件是否存在
# ===================================================================

if ($#argv < 1) then
    echo "Usage: $0 <Script path>"
    exit 1
endif

set SCRIPT = $argv[1]
set ERRORS = 0

echo "  validation script: $SCRIPT"

# 从脚本中提取关键路径进行检查
# 检查CMAQ可执行文件
set BLD = `awk -F= '/set BLD[ \t]+=/ {sub(/#.*/, "", $2); gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' "$SCRIPT"`
if ("$BLD" != "") then
    set BLD_PREFIX = `echo "$BLD" | grep '^\\${CCTM_WORKDIR}'`
    if ("$BLD_PREFIX" != "" && $?CCTM_WORKDIR) then
        set BLD_SUFFIX = `echo "$BLD" | sed 's|^\\${CCTM_WORKDIR}||'`
        set BLD = "${CCTM_WORKDIR}${BLD_SUFFIX}"
    endif
endif
if (-f "${BLD}/CCTM_v532.exe") then
    echo "    OK: CCTM executable"
else
    echo "    Warning: CCTM executable not found: ${BLD}/CCTM_v532.exe"
endif

# 检查NML文件
set NML = `grep 'setenv EMISSCTRL_NML ' $SCRIPT | head -1 | awk '{print $3}'`
if ("$NML" != "" && -f "$NML") then
    echo "    OK: emission-control NML file"
else if ("$NML" != "") then
    echo "    Error: emission-control NML filedoes not exist: $NML"
    @ ERRORS = $ERRORS + 1
endif

# 检查GRIDDESC
set GRIDDESC = `grep 'setenv GRIDDESC ' $SCRIPT | head -1 | awk '{print $3}'`
if ("$GRIDDESC" != "" && -f "$GRIDDESC") then
    echo "    OK: Grid description file"
else if ("$GRIDDESC" != "") then
    echo "    Warning: Grid description file does not exist: $GRIDDESC"
endif

# 检查CMAQ_MASKS
set MASKS = `grep 'setenv CMAQ_MASKS ' $SCRIPT | head -1 | awk '{print $3}'`
if ("$MASKS" != "" && -f "$MASKS") then
    echo "    OK: mask file"
else if ("$MASKS" != "") then
    echo "    Warning: mask file does not exist: $MASKS"
endif

# 检查OCEAN文件
set OCEAN = `grep 'setenv OCEAN_1 ' $SCRIPT | head -1 | awk '{print $3}'`
if ("$OCEAN" != "" && -f "$OCEAN") then
    echo "    OK: oceanfile"
else if ("$OCEAN" != "") then
    echo "    Warning: oceanfile does not exist: $OCEAN"
endif

# 检查化学机理NML文件
set MECH = "cb6r3_ae7_aq"
set NMLpath = "${BLD}"
foreach nml_file (GC_${MECH}.nml AE_${MECH}.nml NR_${MECH}.nml CSQY_DATA_${MECH} PHOT_OPTICS.dat)
    if (-f "${NMLpath}/${nml_file}") then
        echo "    OK: ${nml_file}"
    else
        echo "    Warning: ${nml_file} not found"
    endif
end

# ===================================================================
# IC / BC / 排放清单路径校验(与 v5.4.0.4 同套机制,按 v5.3.2 脚本变量名/命名适配)
# 路径从生成脚本解析(ICpath/BCpath/epath/epath2 已被 run_manager 替换为实际绝对路径)。
# 错误级:BC目录 / 人为排放目录缺失(缺失则运行必失败);
# 警告级:IC(续跑用前一日输出作初始场)、天然源(可禁用)、逐日/逐月排放文件。
# ===================================================================
# 提取日期与路径
set START_DATE = `awk -F'"' '/^[[:space:]]*set START_DATE[ \t]+=/ {print $2; exit}' "${SCRIPT}"`
set END_DATE   = `awk -F'"' '/^[[:space:]]*set END_DATE[ \t]+=/ {print $2; exit}' "${SCRIPT}"`
set ICpath = `awk -F= '/^[[:space:]]*set ICpath[[:space:]]+=/ {sub(/#.*/, "", $2); gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' "${SCRIPT}"`
set BCpath = `awk -F= '/^[[:space:]]*set BCpath[[:space:]]+=/ {sub(/#.*/, "", $2); gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' "${SCRIPT}"`
set epath  = `awk -F= '/^[[:space:]]*set epath[[:space:]]+=/ {sub(/#.*/, "", $2); gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' "${SCRIPT}"`
set epath2 = `awk -F= '/^[[:space:]]*set epath2[[:space:]]+=/ {sub(/#.*/, "", $2); gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' "${SCRIPT}"`
# 排放文件基名/目录:awk 内剥离 ${EMIS_DATE}/${TODAYJ} 运行时变量,避免 csh 对 $ 二次展开
set EMIS_BASE = `awk '/^[[:space:]]*setenv GR_EMIS_001[ \t]+/ {sub(/^[[:space:]]*setenv GR_EMIS_001[ \t]+/, ""); sub(/#.*/, ""); sub(/\${EMIS_DATE}$/, ""); gsub(/[ \t]+$/, ""); print; exit}' "${SCRIPT}"`
set MEGAN_DIR = `awk '/^[[:space:]]*setenv GR_EMIS_002[ \t]+/ {sub(/^[[:space:]]*setenv GR_EMIS_002[ \t]+/, ""); sub(/[^/]*$/, ""); sub(/#.*/, ""); gsub(/[ \t]+$/, ""); print; exit}' "${SCRIPT}"`

# 模拟天数与起始日(用于逐日/逐月核对)
set DAY_CNT = 0
set START_TODAYJ = ""
if ("$START_DATE" != "" && "$END_DATE" != "") then
    set START_EPOCH = `date -ud "$START_DATE" +%s`
    set END_EPOCH   = `date -ud "$END_DATE" +%s`
    @ DAY_CNT = ( $END_EPOCH - $START_EPOCH ) / 86400
    set START_TODAYJ = `date -ud "$START_DATE" +%Y%j`
endif

echo ""
echo "  initial/boundary conditions and Emission inventory validation:"

# 初始条件(警告级:续跑情景用前一日输出作初始场,IC目录/文件可不要求)
if ("$ICpath" == "") then
    echo "    skip: Cannot extract from script ICpath"
else
    if (! -d "$ICpath") then
        echo "    Warning: IC directory does not exist: $ICpath (continuation run Scenario using previous day Output as initial fields,not required)"
    else if ("$START_TODAYJ" != "") then
        if (! -f "${ICpath}/ICON_${START_TODAYJ}") then
            if (${IC_RB_MODE} == "Y") then
               set YESTERDAY = `date -ud "${START_DATE}-1days" +%Y%j`
               set ICFILE = ${ICpath}/CCTM_CGRID_${APPL}_${YESTERDAY}.nc
               if (! -f "${ICFILE}") then
                  echo "    Warning: IC file does not exist: ${ICFILE} (cold start required;continuation run then not required)"
	       else
                  echo "    OK: IC file: ${ICFILE}"
               endif 
            else
               echo "    Warning: IC file does not exist: ${ICpath}/ICON_${START_TODAYJ} (cold start required;continuation run then not required)"
            endif
        else
            echo "    OK: IC file: ${ICpath}/ICON_${START_TODAYJ}"
        endif
    endif
endif

# 边界条件(目录缺失=错误,逐日文件缺失=警告)
if ("$BCpath" == "") then
    echo "    skip: Cannot extract from script BCpath"
else
    if (! -d "$BCpath") then
        echo "    Error: BC directory does not exist: $BCpath"
        @ ERRORS = $ERRORS + 1
    else if ("$START_DATE" != "") then
        set missing_bc = 0
        set i = 0
        while ($i <= $DAY_CNT)
            set TODAYJ = `date -ud "${START_DATE} + ${i} day" +%Y%j`
            if (! -f "${BCpath}/BCON_${TODAYJ}") then
                echo "    Warning: BCfile missing: BCON_${TODAYJ}"
                set missing_bc = 1
            endif
            @ i++
        end
        if ($missing_bc == 0) then
            echo "    OK: BCfiles complete (`expr $DAY_CNT + 1` days)"
        else
            echo "    Warning: exists missing of BCfile(boundary conditions as daily Run required condition,Please complete them)"
        endif
    endif
endif

# 人为源排放(目录缺失=错误;逐月文件缺失=警告,允许部署按日准备)
if ("$epath" == "") then
    echo "    skip: Cannot extract from script epath"
else
    if (! -d "$epath") then
        echo "    Error: anthropogenic emission directory does not exist: $epath"
        @ ERRORS = $ERRORS + 1
    else
        echo "    OK: anthropogenic emission directory: $epath"
        # 模板 EMIS_DATE 取 END_DATE 所在月"第一周五/六/日"三份文件(GR_EM_SYM_DATE=T 整月复用),
        # 校验这三份是否存在(仅警告:按日准备的部署三份皆在,不构成阻断)
        if ("$END_DATE" != "" && "$EMIS_BASE" != "") then
            set e_year  = `date -ud "$END_DATE" +%Y`
            set e_month = `date -ud "$END_DATE" +%m`
            set ff_dow  = `date -ud "$e_year-$e_month-01" +%u`
            @ ff_off = ( 5 - $ff_dow + 7 ) % 7
            set ff_iso = `date -ud "$e_year-$e_month-01 +$ff_off days" +%F`
            set ff_ddd = `date -ud "$ff_iso" +%Y%j`
            set sa_ddd = `date -ud "$ff_iso +1 day" +%Y%j`
            set su_ddd = `date -ud "$ff_iso +2 day" +%Y%j`
            set emis_missing = ""
            foreach ed ($ff_ddd $sa_ddd $su_ddd)
                if (! -f "${EMIS_BASE}${ed}") then
                    if ("$emis_missing" == "") then
                        set emis_missing = "${EMIS_BASE}${ed}"
                    else
                        set emis_missing = "${emis_missing}, ${EMIS_BASE}${ed}"
                    endif
                endif
            end
            if ("$emis_missing" == "") then
                echo "    OK: ${e_year}-${e_month} anthropogenic emission files (${ff_ddd}/${sa_ddd}/${su_ddd})"
            else
                echo "    Warning: anthropogenic emission files missing: $emis_missing"
            endif
        endif
    endif
endif

# 天然源排放(警告级:可禁用;按天命名的 MEGAN 文件逐日核对)
if ("$epath2" == "") then
    echo "    skip: Cannot extract from script epath2"
else
    if (! -d "$epath2") then
        echo "    Warning: biogenic emission directory does not exist: $epath2 (when disabled MEGAN biogenic source when not required)"
    else if ("$START_DATE" != "" && "$MEGAN_DIR" != "") then
        set missing_megan = 0
        set i = 0
        while ($i <= $DAY_CNT)
            set TODAYJ = `date -ud "${START_DATE} + ${i} day" +%Y%j`
            set MEGAN_F = `find "${MEGAN_DIR}" -maxdepth 1 -name "MEGANv32*${TODAYJ}*.ncf" | head -1`
            if ("$MEGAN_F" == "") then
                echo "    Warning: biogenic source file missing: MEGANv32*${TODAYJ}*.ncf"
                set missing_megan = 1
            endif
            @ i++
        end
        if ($missing_megan == 0) then
            echo "    OK: biogenic emission files complete"
        else
            echo "    Warning: exists missing of biogenic emission files"
        endif
    endif
endif

# ===================================================================
# 后处理相关校验:ENABLE_POST_PROCESS=Y 时,校验后处理脚本/环境依赖
# (run_manager 调用时,cctm_config.csh 的后处理 setenv 变量随环境继承到本进程;
#  独立运行未设置时整段跳过)
# ===================================================================
if ( $?ENABLE_POST_PROCESS ) then
    if ( "$ENABLE_POST_PROCESS" == "Y" ) then
        echo ""
        echo "  Post-processing validation(ENABLE_POST_PROCESS=Y):"
        if ( ! $?POST_TEMPLATE_FILE ) setenv POST_TEMPLATE_FILE ""
        if ( "$POST_TEMPLATE_FILE" == "" ) then
            echo "    Error: POST_TEMPLATE_FILE not set(cctm_config.csh should definition Post-processing Template)"
            @ ERRORS = $ERRORS + 1
        else
            set POST_DIR = `dirname "$POST_TEMPLATE_FILE"`
            if (-f "$POST_TEMPLATE_FILE") then
                echo "    OK: Post-processing Template: $POST_TEMPLATE_FILE"
            else
                echo "    Error: Post-processing Template does not exist: $POST_TEMPLATE_FILE"
                @ ERRORS = $ERRORS + 1
            endif

            # 兄弟脚本:对应开关=T 时校验存在(缺失则该后处理步骤必然失败)
            if ( ! $?OUTPUT_COMBINE_ACONC_FILE ) setenv OUTPUT_COMBINE_ACONC_FILE "F"
            if ( ! $?OUTPUT_COMBINE_DEP_FILE ) setenv OUTPUT_COMBINE_DEP_FILE "F"
            if ( ! $?KEEP_18SPECIES_ONLY ) setenv KEEP_18SPECIES_ONLY "F"
            if ( ! $?TSHIFT ) setenv TSHIFT "F"
            if ( ! $?CONVERT2DAILY ) setenv CONVERT2DAILY "F"
            if ( ! $?OUTPUT_DAILY_MAP ) setenv OUTPUT_DAILY_MAP "F"
            if ( ! $?OUTPUT_IC ) setenv OUTPUT_IC "F"
            if ( ! $?OUTPUT_BC ) setenv OUTPUT_BC "F"
            foreach pair ( "OUTPUT_COMBINE_ACONC_FILE 1_run_combine_aconc.csh" "OUTPUT_COMBINE_DEP_FILE 1_run_combine_dep.csh" "KEEP_18SPECIES_ONLY 2_extract_18species_by_nco.csh" "TSHIFT 3_tolocaltime.csh" "CONVERT2DAILY 4_convert2daily.py" "OUTPUT_DAILY_MAP 7_plot_daily_map.py" "OUTPUT_IC 6_run_icon_loop.csh" "OUTPUT_BC 5_run_bcon.csh" )
                set FLAG = `echo $pair | awk '{print $1}'`
                set SIB  = `echo $pair | awk '{print $2}'`
                set FVAL = `printenv $FLAG`
                if ( "$FVAL" == "T" ) then
                    if (! -f "${POST_DIR}/$SIB") then
                        echo "    Error: $FLAG=T but missing Post-processing script $SIB -> ${POST_DIR}/$SIB"
                        @ ERRORS = $ERRORS + 1
                    else
                        echo "    OK: $SIB"
                    endif
                endif
            end

            # config_cmaq.csh:由 CCTM 工作目录上溯两级定位 CMAQ 项目根目录。
            set CFG_F = ""
            if ( ! $?CCTM_WORKDIR ) then
                echo "    Error: CCTM_WORKDIR not set,Cannot locate config_cmaq.csh"
            else
                set CFG_F = "${CCTM_WORKDIR}/../../config_cmaq.csh"
            endif
            if ("$CFG_F" == "") then
                echo "    Error: config_cmaq.csh not found(Post-processing Template requires source it)"
                @ ERRORS = $ERRORS + 1
            else if (-f "$CFG_F") then
                echo "    OK: config_cmaq.csh: $CFG_F"
            else
                echo "    Error: config_cmaq.csh not found: $CFG_F"
                @ ERRORS = $ERRORS + 1
            endif

            # devin_env 激活路径(CONVERT2DAILY=T 时)
            if ( "$CONVERT2DAILY" == "T" ) then
                if (! -f "/program/software/devin_env/bin/activate") then
                    echo "    Error: devin_env activation script does not exist: /program/software/devin_env/bin/activate"
                    @ ERRORS = $ERRORS + 1
                else
                    echo "    OK: devin_env activation script"
                endif
            endif

            # 绘图数据文件(OUTPUT_DAILY_MAP=T 时,仅警告)
            if ( "$OUTPUT_DAILY_MAP" == "T" ) then
                if ( ! $?BASELINE_FILE ) setenv BASELINE_FILE ""
                if ( "$BASELINE_FILE" != "" && "$BASELINE_FILE" != "NAN" ) then
                    if (! -f "$BASELINE_FILE") then
                        echo "    Warning: baseline file does not exist: $BASELINE_FILE"
                    endif
                endif
                if ( ! $?BOUNDARY_FILE ) setenv BOUNDARY_FILE ""
                if ( "$BOUNDARY_FILE" != "" ) then
                    if (! -f "$BOUNDARY_FILE") then
                        echo "    Warning: boundary file does not exist: $BOUNDARY_FILE"
                    endif
                endif
            endif
        endif
    endif
endif

echo ""
if ($ERRORS > 0) then
    echo "  validation found $ERRORS  errors"
    exit 1
else
    echo "  validation passed"
    exit 0
endif
