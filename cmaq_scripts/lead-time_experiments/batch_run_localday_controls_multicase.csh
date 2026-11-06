#!/bin/csh -f

# Multi-case batch generator/runner for strict local-day CMAQ control
# experiments on a standalone server. Derived from batch_run_localday_controls.csh
# (left untouched). Differences:
#   * case_list holds several scenario suffixes; the whole per-case workflow
#     (nml -> CMAQ segments -> post -> raw-output cleanup) runs inside
#     foreach case_suffix ( $case_list ), one case at a time.
#   * nml step: reuse EmissCtrl_nml/EmissCtrl_cb6r3_ae7_aq_${case_suffix}.nml
#     when present; otherwise generate it from a template case nml by parsing
#     the suffix (region + species-pct tokens, e.g. L-B_HZ_VOC30_NOX30 ->
#     HZ with NOX and VOC scaled by 0.7; region PRD scales all 9 PRD cities).
#   * post-processing runs per case as soon as that case's segments finish
#     (enable_post = "Y"), not once after the whole batch, so raw output can
#     be cleaned up case by case.
#   * cleanup_raw: 0 keep raw CCTM output, 1 tar.gz it then delete originals,
#     2 delete outright. Cleanup only runs when post exited 0 AND every
#     expected Daily_COMBINE_ACONC product exists; otherwise keep the scene.
#   * Any failing step aborts only its own case (scene kept, per-case log in
#     logs_multicase/); the batch continues with the next case.
# Usage: ./batch_run_localday_controls_multicase.csh [--dry-run]
# By default, generate and run each segment in order.
# With --dry-run, generate segment scripts (and missing nmls) without running
# CMAQ or post-processing. Segment scripts are written to generated/.
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
            echo "  --dry-run  Generate segment scripts (and missing nmls) without running CMAQ."
            echo "             Post-processing and cleanup are also skipped."
            echo "  Segment scripts are written to generated/."
            echo "  Default: generate and run each segment in order."
            echo '  Set enable_post = "Y" in User settings for per-case automatic post-processing.'
            echo "  Edit case_list below to select the scenarios to run."
            exit 0
        default:
            echo "ERROR: unknown argument: ${arg}"
            echo "Usage: $0 [--dry-run]"
            exit 1
    endsw
end

echo "Starting multi-case local-day CMAQ batch setup..."
date
set nonomatch
if ( ${dry_run} ) then
    echo "Mode: dry-run (generate scripts and missing nmls only)."
else
    echo "Mode: run (generate and run each segment in order, post per case)."
endif

# ---------------- User settings ----------------
set control_template_script = "./run_cctm_D3_202209_base_devin.csh"
set base_template_script    = "./run_cctm_D3_202209_base_devin.csh"
set baseline_dir    = "/mnt/167/devin/cmaq_output/CCTM_CGRID_base/202209_PRD_150X117_utc00"
set segment_root    = "/home/devin/cmaq_output"
set APPL            = "PRD"
# Space-separated scenario suffixes, run one at a time in this order.
set case_list       = ( "L-B_HZ_VOC30_NOX30" "L-B_JM_VOC30_NOX30" )
set base_emissctrl_nml    = "$cwd/EmissCtrl_nml/EmissCtrl_cb6r3_ae7_aq_base.nml"
# Template case nml used when a case nml must be generated: its region-rule
# factors are rewritten per the suffix; everything else is kept verbatim.
set nml_template_case      = "L-B_HZ_VOC30_NOX30"
set target_days     = ( "2022-09-06" "2022-09-13" "2022-09-14" "2022-09-16" "2022-09-19")
set experiments     = ( "P0:0" "A1:1" "A2:2" "A3:3" )
set last_segment_full_day = "N"   # Y: last control segment runs 24 h; N: runs 16 h
set enable_post = "Y"              # Y: post-process each case right after its segments
set post_script = "$cwd/post_scripts/run_post_localday_controls.csh"
# 0: keep raw CCTM output; 1: tar.gz then delete; 2: delete directly.
# Applied only if post exited 0 and all expected daily products exist.
set cleanup_raw = 1
set raw_archive_dir = "${segment_root}/raw_archive"
set logs_dir = "$cwd/logs_multicase"
set first_date = "$target_days[1]"
set year  = `date -ud "$first_date" +%Y`
set month = `date -ud "$first_date" +%m`
# Post-processing output root; each case writes to ${combine_root}/${case_suffix}
# and post products stay there (nothing is copied back).
set combine_root = "/mnt/167/devin/cmaq_output/D3_PRD_150X117/${year}${month}/Lead-time_control"
# ----------------------------------------------

if ( "${enable_post}" != "Y" && "${enable_post}" != "N" ) then
    echo "ERROR: enable_post must be Y or N."
    exit 1
endif
if ( ${cleanup_raw} != 0 && ${cleanup_raw} != 1 && ${cleanup_raw} != 2 ) then
    echo "ERROR: cleanup_raw must be 0, 1 or 2."
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

set nml_template_file = "$cwd/EmissCtrl_nml/EmissCtrl_cb6r3_ae7_aq_${nml_template_case}.nml"
if ( ! -f ${nml_template_file} ) then
    echo "ERROR: nml generation template not found: ${nml_template_file}"
    exit 1
endif

if ( ${#case_list} == 0 ) then
    echo "ERROR: case_list is empty."
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
mkdir -p "${logs_dir}"
if ( $status != 0 ) then
    echo "ERROR: cannot create log directory: ${logs_dir}"
    exit 1
endif

# Valid region masks in the CUSTOM rule block of the case nmls.
set city_regions = ( GZ SZ FS DG HZ JM ZH ZQ ZS )
set n_ok = 0
set n_fail = 0

foreach case_suffix ( ${case_list} )
    set case_t0 = `date +%s`
    set case_log = "${logs_dir}/multicase_${case_suffix}_`date +%Y%m%d_%H%M%S`_$$.log"
    echo "============================================================" | tee -a ${case_log}
    echo "`date +%F_%T`  Case ${case_suffix} starting (log: ${case_log})"
    echo "`date +%F_%T`  Case ${case_suffix} starting" >> ${case_log}
    set case_failed = 0
    set control_emissctrl_nml = "$cwd/EmissCtrl_nml/EmissCtrl_cb6r3_ae7_aq_${case_suffix}.nml"
    set COMBINE_DIR = "${combine_root}/${case_suffix}"

    # ---- Step 1: EmissCtrl nml (reuse existing, else generate) ----
    if ( -e ${control_emissctrl_nml} ) then
        echo "  nml: reusing existing ${control_emissctrl_nml:t}" | tee -a ${case_log}
    else
        echo "  nml: not found, generating from template ${nml_template_case} ..." | tee -a ${case_log}
        # Parse suffix: <tag>_<REGION>_<SPECpct>[_<SPECpct>...]
        # e.g. L-B_HZ_VOC30_NOX30 -> region HZ, NOX 0.7 + VOC 0.7
        #      R-N_PRD_NOX30      -> region PRD (all 9 cities), NOX 0.7
        set parts = ( `echo "${case_suffix}" | tr '_' ' '` )
        set gen_region = ""
        set gen_rules = ()
        @ pi = 1
        while ( ${pi} <= ${#parts} )
            set tok = "${parts[${pi}]}"
            set is_spec = `echo "${tok}" | grep -cE '^(NOX|VOC|SO2|NH3)[0-9]+$'`
            if ( ${is_spec} == 1 ) then
                if ( "${gen_region}" == "" ) then
                    if ( ${pi} == 1 ) then
                        echo "ERROR: cannot parse case_suffix '${case_suffix}': no region token before species" | tee -a ${case_log}
                        set case_failed = 1
                        break
                    endif
                    @ ri = ${pi} - 1
                    set gen_region = "$parts[$ri]"
                endif
                set gen_rules = ( ${gen_rules} ${tok} )
            else if ( "${gen_region}" != "" ) then
                echo "ERROR: cannot parse case_suffix '${case_suffix}': token '${tok}' after species tokens" | tee -a ${case_log}
                set case_failed = 1
                break
            endif
            @ pi++
        end
        if ( ${case_failed} ) then
            echo "`date +%F_%T`  Case ${case_suffix} FAILED at nml step; continuing with next case." | tee -a ${case_log}
            @ n_fail++
            continue
        endif
        if ( "${gen_region}" == "" || ${#gen_rules} == 0 ) then
            echo "ERROR: cannot parse case_suffix '${case_suffix}': no SPEC<pct> token found" | tee -a ${case_log}
            echo "`date +%F_%T`  Case ${case_suffix} FAILED at nml step; continuing with next case." | tee -a ${case_log}
            @ n_fail++
            continue
        endif
        set is_city = 0
        foreach cr ( ${city_regions} )
            if ( "${gen_region}" == ${cr} ) set is_city = 1
        end
        if ( ! ${is_city} && "${gen_region}" != "PRD" ) then
            echo "ERROR: case_suffix '${case_suffix}': region '${gen_region}' not in city_regions/PRD; refusing to generate" | tee -a ${case_log}
            echo "`date +%F_%T`  Case ${case_suffix} FAILED at nml step; continuing with next case." | tee -a ${case_log}
            @ n_fail++
            continue
        endif
        if ( "${gen_region}" == "PRD" ) then
            set target_regions = ( ${city_regions} )
        else
            set target_regions = ( ${gen_region} )
        endif

        set tmp_nml = "${control_emissctrl_nml}.tmp.$$"
        cp "${nml_template_file}" "${tmp_nml}"
        # Reset every region-rule factor in the template to 1.0 first
        # (ALL_MM rule lines only; families/DMS lines do not match).
        sed -i "/', 'ALL_MM'/s/,'GAS'  *,[0-9.]*,'UNIT'/,'GAS'  ,1.0,'UNIT'/g" "${tmp_nml}"
        # Apply each SPEC<pct> rule to each target region.
        foreach rule ( ${gen_rules} )
            set r_spec = `echo "${rule}" | sed 's/[0-9]*$//'`
            set r_pct  = `echo "${rule}" | sed 's/^\(NOX\|VOC\|SO2\|NH3\)//'`
            if ( "${r_pct}" !~ [0-9]* || ${r_pct} <= 0 || ${r_pct} > 100 ) then
                echo "ERROR: case_suffix '${case_suffix}': invalid pct '${r_pct}' in token '${rule}'" | tee -a ${case_log}
                set case_failed = 1
                break
            endif
            @ r_rem = 100 - ${r_pct}
            set r_fac = `awk -v r=${r_rem} 'BEGIN{printf "%g", r/100}'`
            foreach reg ( ${target_regions} )
                sed -i "/^ *'${reg}', *'ALL_MM'.*,'${r_spec}'/s/,'GAS'  *,1[.]0,'UNIT'/,'GAS'  ,${r_fac},'UNIT'/" "${tmp_nml}"
            end
            echo "    rule: ${r_spec} -> ${r_fac} on region(s): ${target_regions}" >> ${case_log}
        end
        if ( ${case_failed} ) then
            rm -f "${tmp_nml}"
            echo "`date +%F_%T`  Case ${case_suffix} FAILED at nml step; continuing with next case." | tee -a ${case_log}
            @ n_fail++
            continue
        endif
        # Sanity: exactly (#regions x #rules) rule lines must be non-1.0 now.
        set n_rule_lines = `grep -c "', 'ALL_MM'" "${tmp_nml}"`
        set n_mod_lines = `grep "', 'ALL_MM'" "${tmp_nml}" | grep -vc ",1[.]0,'UNIT'"`
        @ n_expected = ${#target_regions} * ${#gen_rules}
        if ( ${n_rule_lines} != 40 || ${n_mod_lines} != ${n_expected} ) then
            echo "ERROR: generated nml sanity check failed: rule_lines=${n_rule_lines} (want 40), modified=${n_mod_lines} (want ${n_expected}); keeping scene" | tee -a ${case_log}
            rm -f "${tmp_nml}"
            echo "`date +%F_%T`  Case ${case_suffix} FAILED at nml step; continuing with next case." | tee -a ${case_log}
            @ n_fail++
            continue
        endif
        mv "${tmp_nml}" "${control_emissctrl_nml}"
        if ( $status != 0 ) then
            echo "ERROR: cannot move generated nml into place: ${control_emissctrl_nml}" | tee -a ${case_log}
            @ n_fail++
            continue
        endif
        echo "  nml: generated ${control_emissctrl_nml:t} (region=${gen_region}, rules: ${gen_rules})" | tee -a ${case_log}
    endif

    # ---- Step 2: CMAQ segments ----
    foreach target_day ( ${target_days} )
        if ( ${case_failed} ) break
        set daytag = `date -ud "${target_day}" +%Y%m%d`
        echo "Preparing target day ${target_day} (${daytag})" | tee -a ${case_log}

        foreach experiment ( ${experiments} )
            if ( ${case_failed} ) break
            set exp_name = `echo ${experiment} | cut -d: -f1`
            set lead_days = `echo ${experiment} | cut -d: -f2`
            @ first_offset = ${lead_days} + 1
            if ( ${lead_days} == 0 ) then
                @ seg_count = 3
            else
                @ seg_count = 4
            endif
            set first_utc_day = `date -ud "${target_day} -${first_offset} day" +%Y-%m-%d`

            echo "  Experiment ${exp_name}: lead_days=${lead_days}, segments=${seg_count} including baseline pre-segment" | tee -a ${case_log}
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
                sed -i "s|^ setenv OUTDIR  /.*| setenv OUTDIR  ${segment_root}/${case_name}/D3/2022|g" ${script_path}
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

                echo "    Generated seg${seg_tag}: ${case_name}" | tee -a ${case_log}
                echo "      role=${segment_role}, start_day=${seg_day}, end_day=${end_day}, sttime=${sttime}, nsteps=${nsteps}, restart=${restart_source}:${restart_jday}" >> ${case_log}

                if ( ! ${dry_run} ) then
                    echo "      running ${script_path} (`date +%F_%T`)" | tee -a ${case_log}
                    csh ${script_path} >>&! ${case_log}
                    if ( $status != 0 ) then
                        echo "ERROR: ${script_path} failed; last 30 log lines:" | tee -a ${case_log}
                        tail -30 ${case_log}
                        tail -30 ${case_log} >> ${case_log}
                        set case_failed = 1
                        break
                    endif
                    echo "      seg${seg_tag} done (`date +%F_%T`)" | tee -a ${case_log}
                endif

                set prev_outdir = "${outdir}"
                set prev_jday = "${seg_end_jday}"
            end
        end
    end

    if ( ${case_failed} ) then
        echo "ERROR: case ${case_suffix} failed during CMAQ segments; raw output kept, post/cleanup skipped." | tee -a ${case_log}
        echo "`date +%F_%T`  Case ${case_suffix} FAILED; continuing with next case." | tee -a ${case_log}
        @ n_fail++
        continue
    endif

    # ---- Step 3: post-processing for this case ----
    if ( "${enable_post}" == "Y" ) then
        if ( ${dry_run} ) then
            echo "Skipping automatic post-processing in dry-run mode." | tee -a ${case_log}
        else
            echo "`date +%F_%T`  Segments complete. Starting local-day post-processing for ${case_suffix}..." | tee -a ${case_log}
            mkdir -p "${COMBINE_DIR}"
            csh "${post_script}" --target-days "${target_days}" \
                --experiments "${experiments}" --case-suffix "${case_suffix}" \
                --segment-root "${segment_root}" --appl "${APPL}" \
                --combine-dir "${COMBINE_DIR}" >>&! ${case_log}
            if ( $status != 0 ) then
                echo "ERROR: local-day post-processing failed for ${case_suffix}; last 30 log lines:" | tee -a ${case_log}
                tail -30 ${case_log}
                tail -30 ${case_log} >> ${case_log}
                echo "`date +%F_%T`  Case ${case_suffix} FAILED at post; raw output kept; continuing with next case." | tee -a ${case_log}
                @ n_fail++
                continue
            endif
            echo "`date +%F_%T`  Post-processing finished for ${case_suffix}." | tee -a ${case_log}
        endif
    endif

    # ---- Step 4: verify expected products, then clean up raw output ----
    if ( ${cleanup_raw} != 0 ) then
        if ( ${dry_run} || "${enable_post}" != "Y" ) then
            echo "  cleanup: skipped (dry_run or enable_post != Y)" | tee -a ${case_log}
        else
            set products_ok = 1
            foreach target_day ( ${target_days} )
                set daytag = `date -ud "${target_day}" +%Y%m%d`
                foreach experiment ( ${experiments} )
                    set exp_name = `echo ${experiment} | cut -d: -f1`
                    set dfiles = ( ${COMBINE_DIR}/Daily_COMBINE_ACONC_*_${exp_name}_${daytag}_${case_suffix}_merged_*.nc )
                    if ( ${#dfiles} == 1 && ! -e "${dfiles[1]}" ) then
                        echo "  cleanup: expected daily product missing for ${exp_name} ${target_day} (${dfiles[1]:t}); keeping raw output" | tee -a ${case_log}
                        set products_ok = 0
                    else if ( -z "${dfiles[1]}" ) then
                        echo "  cleanup: expected daily product empty for ${exp_name} ${target_day} (${dfiles[1]:t}); keeping raw output" | tee -a ${case_log}
                        set products_ok = 0
                    endif
                end
            end
            if ( ! ${products_ok} ) then
                echo "ERROR: product verification failed for ${case_suffix}; raw output kept." | tee -a ${case_log}
            else
                echo "  cleanup: all expected daily products present for ${case_suffix}." | tee -a ${case_log}
                set raw_dirs = ( ${segment_root}/*_${case_suffix}_seg* )
                set merged_dirs = ( ${segment_root}/*_${case_suffix}_merged )
                if ( ! -d "${raw_dirs[1]}" ) then
                    echo "  cleanup: no raw segment output dirs found for ${case_suffix}; nothing to clean." | tee -a ${case_log}
                else
                    set raw_names = ""
                    foreach rd ( ${raw_dirs} )
                        set raw_names = "${raw_names} ${rd:t}"
                    end
                    if ( ${cleanup_raw} == 1 ) then
                        set tarfile = "${raw_archive_dir}/${case_suffix}_`date +%Y%m%d_%H%M%S`.tar.gz"
                        echo "  cleanup: archiving ${#raw_dirs} segment dirs -> ${tarfile}" | tee -a ${case_log}
                        mkdir -p "${raw_archive_dir}"
                        ( cd ${segment_root} && tar czf ${tarfile} ${raw_names} )
                        if ( $status == 0 && ! -z ${tarfile} ) then
                            rm -rf ${raw_dirs}
                            echo "  cleanup: archived OK, removed raw segment dirs: ${raw_names}" | tee -a ${case_log}
                        else
                            echo "ERROR: tar failed or archive empty (${tarfile}); raw output kept." | tee -a ${case_log}
                        endif
                    else
                        rm -rf ${raw_dirs}
                        echo "  cleanup: deleted raw segment dirs (cleanup_raw=2): ${raw_names}" | tee -a ${case_log}
                    endif
                    if ( -d "${merged_dirs[1]}" ) then
                        rm -rf ${merged_dirs}
                        echo "  cleanup: removed merged (post intermediate) dirs for ${case_suffix}" | tee -a ${case_log}
                    endif
                endif
            endif
        endif
    endif

    set case_t1 = `date +%s`
    @ case_dt = ( ${case_t1} - ${case_t0} ) / 60
    echo "`date +%F_%T`  Case ${case_suffix} done in ${case_dt} min." | tee -a ${case_log}
    @ n_ok++
end

echo "============================================================"
echo "Multi-case batch finished: ${n_ok} ok, ${n_fail} failed (of ${#case_list} cases)."
foreach f ( ${case_list} )
    echo "  case: ${f}"
end
echo "Per-case logs in ${logs_dir}/."
date
if ( ${n_fail} > 0 ) exit 1
exit 0
