#!/bin/csh -f

# Generic batch generator/runner for strict local-day CMAQ control experiments
# on a standalone server.
# Usage: ./batch_run_localday_controls.csh [--dry-run]
# By default, generate and run each segment in order.
# With --dry-run, generate segment scripts without running CMAQ.
# Segment scripts are written to generated/ under the working directory.
# Set enable_post = "Y" below to post-process after the whole batch succeeds.
#
# Each experiment is split into:
#   seg01: baseline UTC (local_day - lead_days - 1) 00:00 -> 16:00
#          This creates the exact 16:00 restart from the daily baseline restart.
#   seg02: control UTC (local_day - lead_days - 1) 16:00 -> 24:00
#   seg03: one combined middle control segment for full UTC day(s), if needed
#   last control segment: 00:00 -> 16:00 by default for strict UTC+8 local day.

set dry_run = 0
foreach arg ( $argv:q )
    switch ( "${arg}" )
        case --dry-run:
            set dry_run = 1
            breaksw
        case --help:
        case -h:
            echo "Usage: $0 [--dry-run]"
            echo "  --dry-run  Generate segment scripts without running CMAQ."
            echo "             Post-processing is also skipped."
            echo "  Segment scripts are written to generated/."
            echo "  Default: generate and run each segment in order."
            echo '  Set enable_post = "Y" in User settings for automatic post-processing.'
            exit 0
        default:
            echo "ERROR: unknown argument: ${arg}"
            echo "Usage: $0 [--dry-run]"
            exit 1
    endsw
end

echo "Starting local-day CMAQ batch setup..."
date
set nonomatch
if ( ${dry_run} ) then
    echo "Mode: dry-run (generate scripts only)."
else
    echo "Mode: run (generate and run each segment in order)."
endif

# ---------------- User settings ----------------
set control_template_script = "./run_cctm_template_D3_155X122_202204.csh"
set base_template_script    = "./run_cctm_template_D3_155X122_202204.csh"
set baseline_dir    = "/mnt/167/devin/cmaq_output/CCTM_CGRID_base/202204_PRD_155X122_utc00"
set segment_root    = "/home/devin/cmaq_output"
set APPL            = "PRD_155X122"
set case_suffix     = "PRD_VOC45_NOX45"
set base_emissctrl_nml    = "$cwd/EmissCtrl_nml/EmissCtrl_cb6r3_ae7_aq_base.nml"
set control_emissctrl_nml = "$cwd/EmissCtrl_nml/EmissCtrl_cb6r3_ae7_aq_${case_suffix}.nml"
set target_days     = ( "2022-04-04" "2022-04-05" "2022-04-06" "2022-04-07" "2022-04-08" "2022-04-09" "2022-04-10")
set experiments     = ( "P0:0" "A1:1" "A2:2" "A3:3" )
set last_segment_full_day = "N"   # Y: last control segment runs 24 h; N: runs 16 h
set enable_post = "Y"              # Y: post-process once after all segments succeed
set post_script = "$cwd/post_scripts/run_post_localday_controls_D3_155X122_202204.csh"
set first_date = "$target_days[1]"
set year  = `date -ud "$first_date" +%Y`
set month = `date -ud "$first_date" +%m`
set COMBINE_DIR = "/mnt/167/devin/cmaq_output/D3_PRD_155X122/${year}${month}/Lead-time_control/${case_suffix}"
# ----------------------------------------------

if ( "${enable_post}" != "Y" && "${enable_post}" != "N" ) then
    echo "ERROR: enable_post must be Y or N."
    exit 1
endif
if ( "${enable_post}" == "Y" && ! ${dry_run} ) then
    if ( ! -f "${post_script}" ) then
        echo "ERROR: post-processing script not found: ${post_script}"
        exit 1
    endif
endif

if ( ! -f ${control_template_script} ) then
    echo "ERROR: control template script not found: ${control_template_script}"
    exit 1
endif

if ( ! -f ${base_template_script} ) then
    echo "ERROR: baseline template script not found: ${base_template_script}"
    exit 1
endif

if ( ! -f ${base_emissctrl_nml} ) then
    echo "ERROR: baseline EmissCtrl not found: ${base_emissctrl_nml}"
    exit 1
endif

if ( ! -f ${control_emissctrl_nml} ) then
    echo "ERROR: control EmissCtrl not found: ${control_emissctrl_nml}"
    exit 1
endif

set workdir = `pwd`
set generated_dir = "${workdir}/generated"
mkdir -p "${generated_dir}"
if ( $status != 0 ) then
    echo "ERROR: cannot create generated script directory: ${generated_dir}"
    exit 1
endif
echo "Generated script directory: ${generated_dir}"

foreach target_day ( ${target_days} )
    set daytag = `date -ud "${target_day}" +%Y%m%d`
    echo "Preparing target day ${target_day} (${daytag})"

    foreach experiment ( ${experiments} )
        set exp_name = `echo ${experiment} | cut -d: -f1`
        set lead_days = `echo ${experiment} | cut -d: -f2`
        @ first_offset = ${lead_days} + 1
        if ( ${lead_days} == 0 ) then
            @ seg_count = 3
        else
            @ seg_count = 4
        endif
        set first_utc_day = `date -ud "${target_day} -${first_offset} day" +%Y-%m-%d`

        echo "  Experiment ${exp_name}: lead_days=${lead_days}, segments=${seg_count} including baseline pre-segment"
        set old_scripts = ( ${generated_dir}/run_cctm_${exp_name}_${daytag}_${case_suffix}_seg*.csh )
        if ( "${old_scripts}" != "${generated_dir}/run_cctm_${exp_name}_${daytag}_${case_suffix}_seg*.csh" ) then
            rm -f ${old_scripts}
        endif

        set prev_outdir = ""
        set prev_jday = ""
        foreach seg_idx ( `seq 1 ${seg_count}` )
            set seg_tag = `printf "%02d" ${seg_idx}`

            if ( ${seg_idx} == 1 ) then
                set seg_day = "${first_utc_day}"
                set end_day = "${seg_day}"
                set sttime = "000000"
                set nsteps = "160000"
                set restart_dir = "${baseline_dir}"
                set restart_jday = `date -ud "${seg_day} -1 day" +%Y%j`
                set restart_source = "baseline-previous-day"
                set emissctrl_nml = "${base_emissctrl_nml}"
                set template_script = "${base_template_script}"
                set segment_role = "baseline-pre"
            else
                set restart_dir = "${prev_outdir}"
                set restart_jday = "${prev_jday}"
                set restart_source = "previous-segment"
                set emissctrl_nml = "${control_emissctrl_nml}"
                set template_script = "${control_template_script}"

                if ( ${seg_idx} == 2 ) then
                    set seg_day = "${first_utc_day}"
                    set end_day = "${seg_day}"
                    set sttime = "160000"
                    set nsteps = "080000"
                    set segment_role = "control-first-local-day"
                else if ( ${lead_days} > 0 && ${seg_idx} == 3 ) then
                    set seg_day = `date -ud "${first_utc_day} +1 day" +%Y-%m-%d`
                    set end_day = `date -ud "${target_day} -1 day" +%Y-%m-%d`
                    set sttime = "000000"
                    set nsteps = "240000"
                    set segment_role = "control-middle-full-days"
                else
                    set seg_day = "${target_day}"
                    set end_day = "${target_day}"
                    set sttime = "000000"
                    if ( "${last_segment_full_day}" != "Y" ) then
                        set nsteps = "160000"
                        set segment_role = "control-last-local-day"
                    else
                        set nsteps = "240000"
                        set segment_role = "control"
                    endif
                endif
            endif

            set seg_jday = `date -ud "${seg_day}" +%Y%j`
            set seg_end_jday = `date -ud "${end_day}" +%Y%j`
            set seg_month = `date -ud "${seg_day}" +%m`
            set case_name = "${exp_name}_${daytag}_${case_suffix}_seg${seg_tag}"
            set script_path = "${generated_dir}/run_cctm_${case_name}.csh"
            set outdir = "${segment_root}/${case_name}/D3/2022/${seg_month}"

            cp ${template_script} ${script_path}
            chmod +x ${script_path}

            sed -i "s|^ set CASE_NAME   = .*| set CASE_NAME   = ${case_name}|g" ${script_path}
            sed -i "s|^[[:space:]]*set APPL[[:space:]]*=.*| set APPL  = ${APPL}|g" ${script_path}
            sed -i "s|^ setenv OUTDIR  .*| setenv OUTDIR  ${segment_root}/${case_name}/D3/2022|g" ${script_path}
            sed -i "s|^ set firstday  = .*| set firstday  = ${seg_day}|g" ${script_path}
            sed -i "s|^set START_DATE = .*|set START_DATE = ${seg_day}|g" ${script_path}
            sed -i "s|^set END_DATE   = .*|set END_DATE   = ${end_day}|g" ${script_path}
            sed -i "s|^set month = .*|set month = '${seg_month}'|g" ${script_path}
            sed -i "s|^ set STTIME     = .*| set STTIME     = ${sttime}|g" ${script_path}
            sed -i "s|^ set NSTEPS     = .*| set NSTEPS     = ${nsteps}|g" ${script_path}
            sed -i "s|^  setenv EMISSCTRL_NML .*|  setenv EMISSCTRL_NML ${emissctrl_nml}|g" ${script_path}

            env RESTART_DIR="${restart_dir}" RESTART_JDAY="${restart_jday}" START_JDAY="${seg_jday}" APPL="${APPL}" perl -0pi -e 'BEGIN { $rdir = $ENV{"RESTART_DIR"}; $rjday = $ENV{"RESTART_JDAY"}; $sjday = $ENV{"START_JDAY"}; $appl = $ENV{"APPL"}; } s@  setenv OMI \$BLD/OMI_1979_to_2019\.dat@"  if ( \${TODAYJ} == $sjday ) then\n    set ICpath = $rdir\n    setenv ICFILE CCTM_CGRID_${appl}_${rjday}.nc\n    if ( -e ${rdir}/CCTM_MEDIA_CONC_${appl}_${rjday}.nc ) then\n      setenv INIT_MEDC_1 ${rdir}/CCTM_MEDIA_CONC_${appl}_${rjday}.nc\n    else\n      setenv INIT_MEDC_1 notused\n    endif\n    setenv INITIAL_RUN N\n    setenv NEW_START FALSE\n  endif\n\n  setenv OMI \$BLD/OMI_1979_to_2019.dat"@es' ${script_path}
            perl -0pi -e 's@echo "Starting post-processing script\.\.\.".*\z@setenv LOGDIR_CASE  \$cwd/LOGS/\${CASE_NAME}\nif (! -e \${LOGDIR_CASE} ) then\n  mkdir -p \${LOGDIR_CASE}\nendif\nset nonomatch\nset log_files = ( CTM_LOG_* )\nif ( "\${log_files}" != "CTM_LOG_*" ) then\n  mv \${log_files} \${LOGDIR_CASE}\nendif\nexit 0\n@s' ${script_path}
            perl -0pi -e 's@\nexit\s*\z@\nsetenv LOGDIR_CASE  \$cwd/LOGS/\${CASE_NAME}\nif (! -e \${LOGDIR_CASE} ) then\n  mkdir -p \${LOGDIR_CASE}\nendif\nset nonomatch\nset log_files = ( CTM_LOG_* )\nif ( "\${log_files}" != "CTM_LOG_*" ) then\n  mv \${log_files} \${LOGDIR_CASE}\nendif\nexit 0\n@s' ${script_path}

            echo "    Generated seg${seg_tag}: ${case_name}"
            echo "      role=${segment_role}, start_day=${seg_day}, end_day=${end_day}, sttime=${sttime}, nsteps=${nsteps}, restart=${restart_source}:${restart_jday}"

            if ( ! ${dry_run} ) then
                echo "      running ${script_path}"
                csh ${script_path}
                if ( $status != 0 ) then
                    echo "ERROR: ${script_path} failed"
                    exit 1
                endif
            endif

            set prev_outdir = "${outdir}"
            set prev_jday = "${seg_end_jday}"
        end
    end
end

if ( "${enable_post}" == "Y" ) then
    if ( ${dry_run} ) then
        echo "Skipping automatic post-processing in dry-run mode."
    else
        echo "All segment scripts completed. Starting local-day post-processing..."
        csh "${post_script}" --target-days "${target_days}" \
            --experiments "${experiments}" --case-suffix "${case_suffix}" \
            --segment-root "${segment_root}" --appl "${APPL}" \
            --combine-dir "${COMBINE_DIR}"
        set post_status = $status
        if ( ${post_status} != 0 ) then
            echo "ERROR: local-day post-processing failed (status=${post_status})."
            exit ${post_status}
        endif
    endif
endif

echo "Local-day CMAQ batch setup completed."
date
