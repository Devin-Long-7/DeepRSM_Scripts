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

set SCRIPT = "$argv[1]"
set SCRIPT_DIR = `dirname "$0"`
set pending_restart = ()
if ( $#argv == 2 ) then
    set pending_restart = ("$argv[2]")
endif
csh -n "$SCRIPT"
if ( $status != 0 ) exit 1
# Python 路径由管理器配置；独立校验时使用系统 python3。
if ( ! $?PYTHON_CMD ) setenv PYTHON_CMD python3
"$PYTHON_CMD" "$SCRIPT_DIR/post/check_restart.py" $pending_restart "$SCRIPT"
if ( $status != 0 ) exit 1
set ERRORS = 0

echo "  validation script: $SCRIPT"

# 从脚本中提取关键路径进行检查
# 检查CMAQ可执行文件
set VRSN = `awk '/^set VRSN / {print $4; exit}' "$SCRIPT"`
set BLD = `awk -F= '/set BLD[ \t]+=/ {sub(/#.*/, "", $2); gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' "$SCRIPT"`
if ("$BLD" != "") then
    set BLD_PREFIX = `echo "$BLD" | grep '^\\${CCTM_WORKDIR}'`
    if ("$BLD_PREFIX" != "" && $?CCTM_WORKDIR) then
        set BLD_SUFFIX = `echo "$BLD" | sed 's|^\\${CCTM_WORKDIR}||'`
        set BLD = "${CCTM_WORKDIR}${BLD_SUFFIX}"
    endif
endif
if (-f "${BLD}/CCTM_${VRSN}.exe") then
    echo "    OK: CCTM executable"
else
    echo "    Error: CCTM executable not found: ${BLD}/CCTM_${VRSN}.exe"
    @ ERRORS = $ERRORS + 1
endif

# 检查NML文件
set NML = `grep 'setenv EMISSCTRL_NML ' $SCRIPT | head -1 | awk '{print $3}'`
if ("$NML" != "" && -f "$NML") then
    echo "    OK: emission-control NML file"
else if ("$NML" != "") then
    echo "    Error: emission-control NML file does not exist: $NML"
    @ ERRORS = $ERRORS + 1
endif

# 检查GRIDDESC
set GRIDDESC = `grep 'setenv GRIDDESC ' $SCRIPT | head -1 | awk '{print $3}'`
if ("$GRIDDESC" != "" && -f "$GRIDDESC") then
    echo "    OK: Grid description file"
else if ("$GRIDDESC" != "") then
    echo "    Error: Grid description file does not exist: $GRIDDESC"
    @ ERRORS = $ERRORS + 1
endif

# 检查CMAQ_MASKS
set MASKS = `grep 'setenv CMAQ_MASKS ' $SCRIPT | head -1 | awk '{print $3}'`
if ("$MASKS" != "" && -f "$MASKS") then
    echo "    OK: mask file"
else if ("$MASKS" != "") then
    echo "    Error: mask file does not exist: $MASKS"
    @ ERRORS = $ERRORS + 1
endif

# 检查OCEAN文件
set OCEAN = `grep 'setenv OCEAN_1 ' $SCRIPT | head -1 | awk '{print $3}'`
if ("$OCEAN" != "" && -f "$OCEAN") then
    echo "    OK: oceanfile"
else if ("$OCEAN" != "") then
    echo "    Error: oceanfile does not exist: $OCEAN"
    @ ERRORS = $ERRORS + 1
endif

# 检查化学机理NML文件
set MECH = `awk '/^set MECH / {print $4; exit}' "$SCRIPT"`
set VRSN = `awk '/^set VRSN / {print $4; exit}' "$SCRIPT"`
set NMLpath = "${BLD}"
foreach nml_file (GC_${MECH}.nml AE_${MECH}.nml NR_${MECH}.nml CCTM_${VRSN}.cfg CSQY_DATA_${MECH} PHOT_OPTICS.dat OMI_1979_to_2019.dat)
    if (-f "${NMLpath}/${nml_file}") then
        echo "    OK: ${nml_file}"
    else
        echo "    Error: ${nml_file} not found"
        @ ERRORS = $ERRORS + 1
    endif
end

# ===================================================================
# BC / 排放清单：沿用原版路径解析，检查分段对应的 UTC 日期。
# ===================================================================
# 提取日期与路径
set START_DATE = `awk -F'"' '/^[[:space:]]*set START_DATE[ \t]+=/ {print $2; exit}' "${SCRIPT}"`
set END_DATE   = `awk -F'"' '/^[[:space:]]*set END_DATE[ \t]+=/ {print $2; exit}' "${SCRIPT}"`
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

# 初始场的时间、层数与网格由上方 check_restart.py 校验。

# 边界条件：目录和逐日文件必须存在。
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
                echo "    Error: BC file missing: BCON_${TODAYJ}"
                @ ERRORS = $ERRORS + 1
                set missing_bc = 1
            endif
            @ i++
        end
        if ($missing_bc == 0) then
            echo "    OK: BC files complete (`expr $DAY_CNT + 1` days)"
        else
            echo "    Warning: exists missing of BC file(boundary conditions as daily Run required condition,Please complete them)"
        endif
    endif
endif

set emis_oth = `awk '/^set EMIS_OTH / {print $4; exit}' "$SCRIPT"`
set emis_year = `echo "$emis_oth" | cut -c1-4`
set emis_day = `echo "$emis_oth" | cut -c5-7`
@ emis_offset = $emis_day - 1
set EMIS_MONTH = `date -ud "$emis_year-01-01 + $emis_offset days" +%Y-%m`

# 人为源排放：固定代表月的三类代表日文件必须存在。
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
            set e_year  = `date -ud "${EMIS_MONTH}-01" +%Y`
            set e_month = `date -ud "${EMIS_MONTH}-01" +%m`
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
                echo "    Error: anthropogenic emission files missing: $emis_missing"
                @ ERRORS = $ERRORS + 1
            endif
        endif
    endif
endif

# 天然源排放：按 UTC 日期核对配置中的实际文件名。
if ("$epath2" == "") then
    echo "    skip: Cannot extract from script epath2"
else
    if (! -d "$epath2") then
        echo "    Error: biogenic emission directory does not exist: $epath2 (when disabled MEGAN biogenic source when not required)"
        @ ERRORS = $ERRORS + 1
    else if ("$START_DATE" != "" && "$MEGAN_DIR" != "") then
        set missing_megan = 0
        set i = 0
        while ($i <= $DAY_CNT)
            set TODAYJ = `date -ud "${START_DATE} + ${i} day" +%Y%j`
            set MEGAN_F = `awk '/^[[:space:]]*setenv GR_EMIS_002[ \t]+/ {print $3; exit}' "$SCRIPT" | sed 's/${TODAYJ}/'"$TODAYJ"'/'`
            if ( ! -f "$MEGAN_F" ) then
                echo "    Error: biogenic source file missing: ${MEGAN_F}"
                @ ERRORS = $ERRORS + 1
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


# MCIP 每天按 UTC 日期读取；分段不会平移气象文件的时钟。
set METpath = `awk -F= '/^set METpath / {gsub(/ /, "", $2); print $2; exit}' "$SCRIPT"`
foreach prefix (GRIDBDY2D GRIDCRO2D GRIDDOT2D METBDY3D METCRO2D METCRO3D METDOT3D)
    if ( ! -f "$METpath/${prefix}_${START_TODAYJ}" ) then
        echo "    Error: missing $METpath/${prefix}_${START_TODAYJ}"
        @ ERRORS = $ERRORS + 1
    endif
end
if ( $ERRORS != 0 ) then
    echo "Validation failed: $ERRORS missing inputs"
    exit 1
endif
echo "Validation passed: $SCRIPT"
exit 0
