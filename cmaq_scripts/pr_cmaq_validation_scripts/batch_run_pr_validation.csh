#!/bin/csh -f

# Generate and run CMAQ NOx-scan experiments for selected local (UTC+8) dates
# and RSM regions.  The default mode executes CMAQ; --dry-run only generates
# files for inspection.
#
#   csh batch_run_pr_validation.csh                  # generate and run CMAQ
#   csh batch_run_pr_validation.csh --dry-run        # generate only
#   csh batch_run_pr_validation.csh --post           # post-process existing run
#   csh batch_run_pr_validation.csh --run-and-post   # run CMAQ and post-process

set nonomatch
set script_path = `dirname "$0"`
set script_path = `cd "$script_path" && pwd`
set config_file = "${script_path}/config_pr_validation.csh"
if ( $?PR_VALIDATION_CONFIG ) set config_file = `printenv PR_VALIDATION_CONFIG`

if ( ! -f "${config_file}" ) then
    echo "ERROR: configuration not found: ${config_file}"
    exit 1
endif
source "${config_file}"

set mode = "run"
set post_after = "N"
set manifest_override = ""

while ( $#argv > 0 )
    set option = "$argv[1]"
    shift argv
    switch ( "${option}" )
        case --dry-run:
            set mode = "dry-run"
            breaksw
        case --run:
            set mode = "run"
            breaksw
        case --post:
            set mode = "post"
            set post_after = "Y"
            breaksw
        case --manifest:
            if ( $#argv == 0 ) then
                echo "ERROR: --manifest requires a file path."
                exit 1
            endif
            set manifest_override = "$argv[1]"
            shift argv
            breaksw
        case --run-and-post:
            set mode = "run"
            set post_after = "Y"
            breaksw
        case --help:
        case -h:
            echo "Usage: csh batch_run_pr_validation.csh [--dry-run|--run|--post|--run-and-post]"
            echo "  (no option)     Generate and execute CMAQ segments in sequence."
            echo "  --dry-run       Generate NMLs and CCTM scripts only."
            echo "  --run           Same as the default execution mode."
            echo "  --post          Post-process existing manifest/CMAQ outputs only."
            echo "  --manifest FILE Use FILE instead of generated/manifest.tsv with --post."
            echo "  --run-and-post  Execute CMAQ, then run post-processing."
            echo "Edit config_pr_validation.csh for dates, lead_days, target regions, modes, factors and paths."
            exit 0
        default:
            echo "ERROR: unknown option: ${option}"
            exit 1
    endsw
end

if ( "${mode}" != "run" ) then
    if ( "${mode}" != "dry-run" ) then
        if ( "${mode}" != "post" ) then
            echo "ERROR: invalid execution mode: ${mode}"
            exit 1
        endif
    endif
endif

if ( ! -x "${python_bin}" ) then
    echo "ERROR: configured Python executable is not available: ${python_bin}"
    echo "Edit python_bin in ${config_file} to an executable Python with xarray, netCDF4 and numpy."
    exit 1
endif

set manifest = "${generated_dir}/manifest.tsv"
if ( "${manifest_override}" != "" ) set manifest = "${manifest_override}"
if ( "${mode}" == "post" ) then
    if ( "${manifest_override}" == "" && -f "${manifest}" ) then
        set manifest_has_rows = `grep -E -c '^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][[:space:]]' "${manifest}"`
        if ( ${manifest_has_rows} == 0 ) then
            foreach fallback_manifest ( \
                "${script_path}/../cctm_scripts_v5.3.2/manifest_readable.tsv" \
                "${script_path}/../cctm_scripts_v5.3.2/manifest.tsv" )
                if ( -f "${fallback_manifest}" ) then
                    set fallback_rows = `grep -E -c '^[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][[:space:]]' "${fallback_manifest}"`
                    if ( ${fallback_rows} > 0 ) then
                        echo "Default manifest has no task rows; using fallback: ${fallback_manifest}"
                        set manifest = "${fallback_manifest}"
                        break
                    endif
                endif
            end
        endif
    endif
    if ( ! -f "${manifest}" ) then
        echo "ERROR: existing manifest not found: ${manifest}"
        echo "Run the workflow first, or use --dry-run to generate a new manifest."
        exit 1
    endif
    echo "Post-only mode: CMAQ will not be started."
    "${python_bin}" "${script_path}/post_pr_validation.py" \
        --manifest "${manifest}" \
        --post-script-dir "${post_script_dir}" \
        --segment-root "${segment_root}" \
        --post-root "${post_root}" \
        --input-root "${input_root}" --appl "${APPL}" \
        --python-bin "${python_bin}"
    if ( $status != 0 ) then
        echo "ERROR: post-processing failed."
        exit 1
    endif
    echo "Post-processing finished."
    exit 0
endif

foreach required ( "${template_script}" "${base_emissctrl}" )
    if ( ! -f "${required}" ) then
        echo "ERROR: required file not found: ${required}"
        exit 1
    endif
end

mkdir -p "${generated_dir}" "${nml_dir}"
if ( $status != 0 ) then
    echo "ERROR: cannot create output directories."
    exit 1
endif
if ( "${mode}" == "run" ) then
    mkdir -p "${segment_root}" "${log_root}"
    if ( $status != 0 ) then
        echo "ERROR: cannot create CMAQ output directories."
        exit 1
    endif
endif
find "${generated_dir}" -maxdepth 1 -type f -name 'run_cctm_*.csh' -delete
find "${nml_dir}" -maxdepth 1 -type f -name 'EmissCtrl_*.nml' -delete
printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
    "target_day" "lead_days" "target_region" "scan_mode" "control_scope" "nox_factor" \
    "pre_case" "seg02_case" "seg03_case" "first_utc_day" "local_day" > "${manifest}"

echo "Mode: ${mode}"
echo "Template: ${template_script}"
echo "Baseline CGRID directory: ${baseline_cgrid_dir}"
echo "Manifest: ${manifest}"

# Generate one EmissCtrl file per (control scope, factor).  Local uses the
# selected target-region label (including D3-PRD when the RSM OTH receptor is
# selected); Whole always uses CMAQ's built-in EVERYWHERE region, which is the
# direct-CMAQ equivalent of the RSM `everywhere` control case.
foreach target_region_raw ( ${target_regions} )
    set target_region = `echo "${target_region_raw}" | tr '[:lower:]' '[:upper:]'`
    foreach scan_mode_raw ( ${scan_modes} )
        set scan_mode = `echo "${scan_mode_raw}" | tr '[:upper:]' '[:lower:]'`
        if ( "${scan_mode}" == "local" ) then
            set control_scope = "${target_region}"
        else if ( "${scan_mode}" == "whole" ) then
            set control_scope = "EVERYWHERE"
        else
            echo "ERROR: scan mode must be local or whole: ${scan_mode}"
            exit 1
        endif
        foreach factor ( ${nox_factors} )
            set factor_tag = `echo "${factor}" | sed 's/-/m/g; s/\./p/g'`
            set nml_path = "${nml_dir}/EmissCtrl_${control_scope}_NOX${factor_tag}.nml"
            "${python_bin}" "${script_path}/generate_emissctrl.py" \
                --base "${base_emissctrl}" --output "${nml_path}" \
                --scope "${control_scope}" --nox-factor "${factor}"
            if ( $status != 0 ) then
                echo "ERROR: failed to generate EmissCtrl for ${control_scope}, factor=${factor}"
                exit 1
            endif
        end
    end
end

# Render one baseline-pre segment and the control chain for each target day
# and requested lead time.  lead_days=0 gives seg02/seg03; lead_days>0 adds
# seg03 for middle full UTC days and uses seg04 as the final target-day segment.
foreach target_day ( ${target_days} )
    set daytag = `date -ud "${target_day}" +%Y%m%d`
    foreach lead_day ( ${lead_days} )
        set control_start_day = `date -ud "${target_day} -${lead_day} day -1 day" +%Y-%m-%d`
        set first_jday = `date -ud "${control_start_day}" +%Y%j`
        set baseline_jday = `date -ud "${control_start_day} -1 day" +%Y%j`
        set control_year = `date -ud "${control_start_day}" +%Y`
        set control_month = `date -ud "${control_start_day}" +%m`
        set target_year = `date -ud "${target_day}" +%Y`
        set pre_case = "PRV_${daytag}_L${lead_day}_BASEPRE"

        if ( "${mode}" == "run" ) then
            set baseline_cgrid = "${baseline_cgrid_dir}/CCTM_CGRID_${APPL}_${baseline_jday}.nc"
            if ( ! -f "${baseline_cgrid}" ) then
                echo "ERROR: baseline CGRID not found for ${target_day}, lead_days=${lead_day}: ${baseline_cgrid}"
                exit 1
            endif
        endif
        set pre_out_root = "${segment_root}/${pre_case}/D3/${control_year}"
        set pre_restart_dir = "${pre_out_root}/${control_month}"
        set pre_script = "${generated_dir}/run_cctm_${pre_case}.csh"
        "${python_bin}" "${script_path}/render_cctm_segment.py" \
            --template "${template_script}" --output "${pre_script}" \
            --case-name "${pre_case}" --appl "${APPL}" \
            --out-root "${pre_out_root}" \
            --start-date "${control_start_day}" --end-date "${control_start_day}" \
            --sttime 000000 --nsteps 160000 \
            --emissctrl "${base_emissctrl}" \
            --restart-dir "${baseline_cgrid_dir}" --restart-jday "${baseline_jday}" \
            --input-root "${input_root}" --icbc-root "${icbc_root}" \
            --cmaq-home "${cmaq_home}" --bld "${bld}" \
            --log-dir "${log_root}/${pre_case}"
        if ( $status != 0 ) then
            echo "ERROR: failed to render baseline-pre script for ${target_day}, lead_days=${lead_day}"
            exit 1
        endif

        foreach target_region_raw ( ${target_regions} )
            set target_region = `echo "${target_region_raw}" | tr '[:lower:]' '[:upper:]'`
            foreach scan_mode_raw ( ${scan_modes} )
                set scan_mode = `echo "${scan_mode_raw}" | tr '[:upper:]' '[:lower:]'`
                if ( "${scan_mode}" == "local" ) then
                    set control_scope = "${target_region}"
                else if ( "${scan_mode}" == "whole" ) then
                    set control_scope = "EVERYWHERE"
                else
                    echo "ERROR: scan mode must be local or whole: ${scan_mode}"
                    exit 1
                endif
                foreach factor ( ${nox_factors} )
                    set factor_tag = `echo "${factor}" | sed 's/-/m/g; s/\./p/g'`
                    set nml_path = "${nml_dir}/EmissCtrl_${control_scope}_NOX${factor_tag}.nml"
                    set scenario_tag = "L${lead_day}_${target_region}_${scan_mode}_NOX${factor_tag}"
                    set seg02_case = "PRV_${daytag}_${scenario_tag}_seg02"
                    set seg02_out_root = "${segment_root}/${seg02_case}/D3/${control_year}"
                    set seg02_restart_dir = "${seg02_out_root}/${control_month}"

                    "${python_bin}" "${script_path}/render_cctm_segment.py" \
                        --template "${template_script}" --output "${generated_dir}/run_cctm_${seg02_case}.csh" \
                        --case-name "${seg02_case}" --appl "${APPL}" \
                        --out-root "${seg02_out_root}" \
                        --start-date "${control_start_day}" --end-date "${control_start_day}" \
                        --sttime 160000 --nsteps 080000 \
                        --emissctrl "${nml_path}" \
                        --restart-dir "${pre_restart_dir}" --restart-jday "${first_jday}" \
                        --input-root "${input_root}" --icbc-root "${icbc_root}" \
                        --cmaq-home "${cmaq_home}" --bld "${bld}" \
                        --log-dir "${log_root}/${seg02_case}"
                    if ( $status != 0 ) then
                        echo "ERROR: failed to render seg02 for ${target_day}, lead_days=${lead_day}, ${target_region}, ${scan_mode}, ${factor}"
                        exit 1
                    endif

                    if ( ${lead_day} > 0 ) then
                        set middle_start_day = `date -ud "${control_start_day} +1 day" +%Y-%m-%d`
                        set middle_end_day = `date -ud "${target_day} -1 day" +%Y-%m-%d`
                        set middle_jday = `date -ud "${middle_end_day}" +%Y%j`
                        set seg03_case = "PRV_${daytag}_${scenario_tag}_seg03"
                        set seg03_out_root = "${segment_root}/${seg03_case}/D3/${control_year}"
                        "${python_bin}" "${script_path}/render_cctm_segment.py" \
                            --template "${template_script}" --output "${generated_dir}/run_cctm_${seg03_case}.csh" \
                            --case-name "${seg03_case}" --appl "${APPL}" \
                            --out-root "${seg03_out_root}" \
                            --start-date "${middle_start_day}" --end-date "${middle_end_day}" \
                            --sttime 000000 --nsteps 240000 \
                            --emissctrl "${nml_path}" \
                            --restart-dir "${seg02_restart_dir}" --restart-jday "${first_jday}" \
                            --input-root "${input_root}" --icbc-root "${icbc_root}" \
                            --cmaq-home "${cmaq_home}" --bld "${bld}" \
                            --log-dir "${log_root}/${seg03_case}"
                        if ( $status != 0 ) then
                            echo "ERROR: failed to render seg03 for ${target_day}, lead_days=${lead_day}, ${target_region}, ${scan_mode}, ${factor}"
                            exit 1
                        endif
                        set final_restart_dir = "${seg03_out_root}/${control_month}"
                        set final_restart_jday = "${middle_jday}"
                        set final_seg = "04"
                    else
                        set seg03_case = "PRV_${daytag}_${scenario_tag}_seg03"
                        set final_restart_dir = "${seg02_restart_dir}"
                        set final_restart_jday = "${first_jday}"
                        set final_seg = "03"
                    endif

                    set final_case = "PRV_${daytag}_${scenario_tag}_seg${final_seg}"
                    set final_out_root = "${segment_root}/${final_case}/D3/${target_year}"
                    "${python_bin}" "${script_path}/render_cctm_segment.py" \
                        --template "${template_script}" --output "${generated_dir}/run_cctm_${final_case}.csh" \
                        --case-name "${final_case}" --appl "${APPL}" \
                        --out-root "${final_out_root}" \
                        --start-date "${target_day}" --end-date "${target_day}" \
                        --sttime 000000 --nsteps 160000 \
                        --emissctrl "${nml_path}" \
                        --restart-dir "${final_restart_dir}" --restart-jday "${final_restart_jday}" \
                        --input-root "${input_root}" --icbc-root "${icbc_root}" \
                        --cmaq-home "${cmaq_home}" --bld "${bld}" \
                        --log-dir "${log_root}/${final_case}"
                    if ( $status != 0 ) then
                        echo "ERROR: failed to render final segment for ${target_day}, lead_days=${lead_day}, ${target_region}, ${scan_mode}, ${factor}"
                        exit 1
                    endif

                    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
                        "${target_day}" "${lead_day}" "${target_region}" "${scan_mode}" "${control_scope}" \
                        "${factor}" "${pre_case}" "${seg02_case}" "${final_case}" \
                        "${control_start_day}" "${target_day}" >> "${manifest}"
                end
            end
        end
    end
end

set manifest_lines = `wc -l < "${manifest}"`
echo "Generated ${manifest_lines} manifest lines including header."

if ( "${mode}" == "run" ) then
    echo "Starting CMAQ segments in dependency order..."
    foreach target_day ( ${target_days} )
        set daytag = `date -ud "${target_day}" +%Y%m%d`
        foreach lead_day ( ${lead_days} )
            set pre_case = "PRV_${daytag}_L${lead_day}_BASEPRE"
            set pre_script = "${generated_dir}/run_cctm_${pre_case}.csh"
            echo "Running baseline-pre ${pre_case}"
            csh "${pre_script}"
            if ( $status != 0 ) then
                echo "ERROR: baseline-pre failed: ${pre_script}"
                exit 1
            endif

            foreach target_region_raw ( ${target_regions} )
                set target_region = `echo "${target_region_raw}" | tr '[:lower:]' '[:upper:]'`
                foreach scan_mode_raw ( ${scan_modes} )
                    set scan_mode = `echo "${scan_mode_raw}" | tr '[:upper:]' '[:lower:]'`
                    foreach factor ( ${nox_factors} )
                        set factor_tag = `echo "${factor}" | sed 's/-/m/g; s/\./p/g'`
                        set scenario_tag = "L${lead_day}_${target_region}_${scan_mode}_NOX${factor_tag}"
                        if ( ${lead_day} > 0 ) then
                            set run_cases = ( "PRV_${daytag}_${scenario_tag}_seg02" "PRV_${daytag}_${scenario_tag}_seg03" "PRV_${daytag}_${scenario_tag}_seg04" )
                        else
                            set run_cases = ( "PRV_${daytag}_${scenario_tag}_seg02" "PRV_${daytag}_${scenario_tag}_seg03" )
                        endif
                        foreach seg_case ( ${run_cases} )
                            set seg_script = "${generated_dir}/run_cctm_${seg_case}.csh"
                            echo "Running ${seg_case}"
                            csh "${seg_script}"
                            if ( $status != 0 ) then
                                echo "ERROR: CMAQ segment failed: ${seg_script}"
                                exit 1
                            endif
                        end
                    end
                end
            end
        end
    end
    echo "All CMAQ segments completed."
else
    echo "Dry-run mode: CMAQ was not started."
endif

if ( "${post_after}" == "Y" ) then
    echo "Starting post-processing from ${manifest}"
    "${python_bin}" "${script_path}/post_pr_validation.py" \
        --manifest "${manifest}" \
        --post-script-dir "${post_script_dir}" \
        --segment-root "${segment_root}" \
        --post-root "${post_root}" \
        --input-root "${input_root}" --appl "${APPL}" \
        --python-bin "${python_bin}"
    if ( $status != 0 ) then
        echo "ERROR: post-processing failed."
        exit 1
    endif
else
    echo "Post-processing not requested. Use --post after successful CMAQ output."
endif

echo "PR validation workflow finished."
