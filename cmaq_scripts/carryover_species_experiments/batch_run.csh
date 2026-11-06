#!/bin/csh -f
# 唯一批处理入口：读取配置 → 准备计划 → 逐任务两段运行 → 后处理。
# 不加参数默认执行；--dry-run只生成与校验，不启动CMAQ。

# ===== 1. 定位脚本和解析参数 =====
set original_dir = "$cwd"
set script_dir = `dirname "$0"`
cd "$script_dir"
set script_dir = "$cwd"
set config_file = "$script_dir/cctm_config.csh"
set dry_run = 0
set post_manifest = ""
set plan_arguments = ()

while ( $#argv > 0 )
    switch ( "$argv[1]" )
        case --config:
            if ( $#argv < 2 ) then
                echo "Error: --config requires a cctm_config.csh path"
                exit 1
            endif
            set config_file = "$argv[2]"
            if ( "$config_file" !~ /* ) set config_file = "$original_dir/$config_file"
            shift argv
            shift argv
            breaksw
        case --dry-run:
            set dry_run = 1
            set plan_arguments = ($plan_arguments --dry-run)
            shift argv
            breaksw
        case --post-only:
            if ( $#argv < 2 ) then
                echo "Error: --post-only requires a manifest.json path"
                exit 1
            endif
            set post_manifest = "$argv[2]"
            if ( "$post_manifest" !~ /* ) set post_manifest = "$original_dir/$post_manifest"
            shift argv
            shift argv
            breaksw
        default:
            # --dates和--cases及其值交给计划工具解析，CSH负责实际批量执行。
            set plan_arguments = ($plan_arguments "$argv[1]")
            shift argv
            breaksw
    endsw
end

# ===== 2. 只读取这一份日常配置 =====
if ( ! -f "$config_file" ) then
    echo "Error: configuration file not found: $config_file"
    exit 1
endif
source "$config_file"
if ( $status != 0 ) exit 1
set python_cmd = "$PYTHON_CMD"
if ( $?CARRYOVER_PYTHON ) then
    set python_cmd = "$CARRYOVER_PYTHON"
endif

if ( "$post_manifest" != "" ) then
    if ( $dry_run == 1 ) then
        echo "Error: --post-only cannot be combined with --dry-run"
        exit 1
    endif
    "$python_cmd" "$script_dir/post_results.py" --manifest "$post_manifest"
    exit $status
endif

# ===== 3. 核验全部输入并生成可审阅的两段计划 =====
# Python工具只检查数据与生成脚本，绝不执行CMAQ。
set plan_pointer = `mktemp "$script_dir/.plan_XXXXXXXX"`
if ( $status != 0 ) exit 1
"$python_cmd" "$script_dir/prepare_plan.py" --config "$config_file" --plan-pointer "$plan_pointer" $plan_arguments:q
set prepare_status = $status
if ( $prepare_status != 0 ) then
    rm -f "$plan_pointer"
    exit $prepare_status
endif
set plan_dir = `cat "$plan_pointer"`
rm -f "$plan_pointer"
source "$plan_dir/batch_plan.csh"
if ( $status != 0 ) exit 1

if ( $dry_run == 1 ) then
    echo "Dry-run passed: see $manifest_path; CMAQ was not launched."
    exit 0
endif

# ===== 4. CSH直接控制任务循环和CMAQ启动 =====
foreach task_id ($task_ids)
    source "$plan_dir/task_${task_id}.csh"
    if ( $status != 0 ) exit 1
    echo "Prepare IC: $CST_DATE $CASE_NAME"
    "$python_cmd" "$script_dir/prepare_ic.py" --continuous "$CONTINUOUS_IC" --reset "$RESET_IC" --date "$CST_DATE" --groups "$plan_dir/groups_used.json" --case "$CASE_NAME" --output "$MIXED_IC"
    if ( $status != 0 ) exit 1

    # seg02只接续本任务seg01，不能在UTC00再次使用原重置场。
    foreach segment (1 2)
        if ( $segment == 1 ) then
            set segment_script = "$SEG1_SCRIPT"
            set segment_work = "$SEG1_WORK"
        else
            set segment_script = "$SEG2_SCRIPT"
            set segment_work = "$SEG2_WORK"
        endif
        mkdir "$segment_work"
        if ( $status != 0 ) exit 1
        cd "$segment_work"
        echo "Run: $CST_DATE $CASE_NAME segment $segment"
        csh "$segment_script" >&! "$segment_work/run.log"
        set model_status = $status
        cd "$script_dir"
        if ( $model_status != 0 ) then
            echo "Error: simulation failed; see $segment_work/run.log"
            exit $model_status
        endif
        "$python_cmd" "$script_dir/prepare_plan.py" --check-output "$manifest_path" --task-id "$task_id" --segment "$segment"
        if ( $status != 0 ) exit 1
    end
end

# ===== 5. 整批成功后自动汇总臭氧响应 =====
if ( $auto_post == 1 ) then
    "$python_cmd" "$script_dir/post_results.py" --manifest "$manifest_path"
    if ( $status != 0 ) exit 1
endif
echo "Batch complete: $manifest_path"
exit 0
