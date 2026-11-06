#!/bin/csh -f
# ===================================================================
# CMAQ 批量运行脚本(多情景/多案例) - v5.3.2
# 用法: ./batch_run_cases.csh                        # 运行默认情景列表
#      ./batch_run_cases.csh oos1 oos2 oos3          # 直接按情景名批量跑
#      ./batch_run_cases.csh run_configs/run_config_X.csh   # 或指定配置文件(高级)
#      ./batch_run_cases.csh ... --dry-run           # 只生成+校验,不执行(可加在任意位置)
# 说明:
#   - 按情景名时:覆盖 CASE_NAME,并按名字判定 CASE_TYPE(以 sector 开头→sector,否则
#     standard),其余参数沿用 cctm_config.csh 默认(输入数据/日期/域/资源相同,排放控制
#     nml 由 create_emissCtrl_nml.py 按情景自动生成到 generated/,输出目录按 CASE_NAME 自动区分),
#     无需准备 per-case 配置文件。
#     ⚠ IC_PATH/BC_PATH 沿用 cctm_config.csh 固定值(默认 ${DOMAIN}_base)。需要不同
#       初始/边界条件的情景(如 jx2zero→D3_jx2zero)请用配置文件模式,或在 cctm_config.csh
#       里改好后用 --dry-run 先核查生成脚本。
#   - 指定配置文件时:完整走该配置(用于日期/域/路径等与默认不同的案例)。
#   - --dry-run 透传给每个 run_manager.csh:只生成+校验脚本,不执行 CMAQ/后处理。
# 每个案例完整走 生成→校验→运行→后处理,串行执行。
# ===================================================================

# 切到脚本所在目录,保证 run_manager/模板/相对路径正确
set SCRIPT_DIR = ${0:h}
if ("$SCRIPT_DIR" != "." && "$SCRIPT_DIR" != "") then
    cd "$SCRIPT_DIR"
endif

# 参数分类:--dry-run → 透传标志;存在且为文件 → 配置文件模式;否则视为情景名
set DRY_RUN = 0
set batch_status = 0
set case_configs = ()
set case_names = ()
foreach a ($argv)
    if ("$a" == "--dry-run") then
        set DRY_RUN = 1
    else if (-f "$a") then
        set case_configs = ($case_configs $a)
    else
        set case_names = ($case_names $a)
    endif
end

# 无参数时使用默认情景列表(按需修改)
if ($#case_configs == 0 && $#case_names == 0) then
    set case_names = (oos3)
endif

# 情景名模式:沿用 cctm_config.csh 默认,仅覆盖 CASE_NAME/CASE_TYPE
foreach c ($case_names)
    echo "=========================================="
    if ($DRY_RUN == 1) then
        echo "[dry-run] Scenario: $c  (DefaultConfiguration,only overrides CASE_NAME/CASE_TYPE)"
    else
        echo "RunScenario: $c  (DefaultConfiguration,only overrides CASE_NAME/CASE_TYPE)"
    endif
    echo "Start time: `date`"

    setenv CASE_NAME $c
    # v5.3.2 排放控制 nml 按案例类型(standard/sector)生成:以 sector 开头的视为部门情景
    if ("$c" =~ sector*) then
        setenv CASE_TYPE sector
    else
        setenv CASE_TYPE standard
    endif
    if ($DRY_RUN == 1) then
        ./run_manager.csh --dry-run
        set rc = $status
    else
        ./run_manager.csh
        set rc = $status
    endif

    echo "End time: `date`"
    if ($rc == 0) then
        echo "✓ Scenariocompleted: $c"
    else
        echo "✗ Scenariofailed(exit code $rc): $c"
        set batch_status = 1
    endif
end

# 配置文件模式:完整走自定义配置(高级用法)
foreach cfg ($case_configs)
    echo "=========================================="
    if ($DRY_RUN == 1) then
        echo "[dry-run] Configuration: $cfg"
    else
        echo "RunConfiguration: $cfg"
    endif
    echo "Start time: `date`"

    if ($DRY_RUN == 1) then
        ./run_manager.csh "$cfg" --dry-run
        set rc = $status
    else
        ./run_manager.csh "$cfg"
        set rc = $status
    endif

    echo "End time: `date`"
    if ($rc == 0) then
        echo "✓ Configurationcompleted: $cfg"
    else
        echo "✗ Configurationfailed(exit code $rc): $cfg"
        set batch_status = 1
    endif
end

echo ""
echo "=========================================="
echo "Batch run completed"
echo "=========================================="
exit $batch_status
