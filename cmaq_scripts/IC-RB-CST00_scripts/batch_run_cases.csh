#!/bin/csh -f
# ===================================================================
# CMAQ 批量运行脚本(多情景/多案例) - v5.3.2
# 用法: ./batch_run_cases.csh                        # 运行默认情景列表
#      ./batch_run_cases.csh oos1 oos2 oos3          # 直接按情景名批量跑
#      ./batch_run_cases.csh run_configs/run_config_X.csh   # 或指定配置文件(高级)
#      ./batch_run_cases.csh ... --dry-run           # 只生成+校验,不执行(可加在任意位置)
# 每个情景依次完成：每天两段模拟 → 整段后处理 → 校验后清理。
# 情景列表在本文件设置；日期、路径、资源、后处理开关在 cctm_config.csh 设置。
# --dry-run 只生成和校验，不启动 CMAQ 或后处理，不清理数据。
# ===================================================================

# 切到脚本所在目录,保证 run_manager/模板/相对路径正确
set SCRIPT_DIR = `dirname "$0"`
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
    set case_names = (prd2zero everywhere2zero)
endif

# 情景名模式:沿用 cctm_config.csh 默认,仅覆盖 CASE_NAME/CASE_TYPE
foreach c ($case_names)
    echo "=========================================="
    if ($DRY_RUN == 1) then
        echo "[dry-run] Scenario: $c  (default configuration; overrides CASE_NAME/CASE_TYPE)"
    else
        echo "Run scenario: $c  (default configuration; overrides CASE_NAME/CASE_TYPE)"
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
        echo "✓ Scenario completed: $c"
    else
        echo "✗ Scenario failed(exit code $rc): $c"
        set batch_status = 1
    endif
end

# 配置文件模式:完整走自定义配置(高级用法)
unsetenv CASE_NAME
unsetenv CASE_TYPE
foreach cfg ($case_configs)
    echo "=========================================="
    if ($DRY_RUN == 1) then
        echo "[dry-run] Configuration: $cfg"
    else
        echo "Run configuration: $cfg"
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
        echo "✓ Configuration completed: $cfg"
    else
        echo "✗ Configuration failed(exit code $rc): $cfg"
        set batch_status = 1
    endif
end

echo ""
echo "=========================================="
echo "Batch run completed"
echo "=========================================="
exit $batch_status
