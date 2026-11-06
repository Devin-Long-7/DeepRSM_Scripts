#!/bin/csh -f
# Standalone settings below can be overridden by the batch runner's CLI options.

set nonomatch

set script_path = `dirname "$0"`
set script_path = `cd "$script_path" && pwd`

# ---------------- User settings ----------------
#set target_days = ("2022-09-19" "2022-09-16" "2022-09-14" "2022-09-13" "2022-09-06")
set target_days     = ( "2022-09-06" "2022-09-13" "2022-09-14" "2022-09-16" "2022-09-19")
set experiments = ( "P0:0" "A1:1" "A2:2" "A3:3" )
set case_suffix = "PRD_VOC75_NOX75"
set segment_root = "/home/devin/cmaq_output"
set VRSN = "v532"
set DOMAIN = "D3"
set APPL = "PRD"
set MECH = "cb6r3_ae7_aq"
set LAYER = "1"
set INPDIR = "/bigdata/CMAQ_input/devin/PRD/2022"
set OUTPUT_BY_YEARMONTH = "F"
set INCLUDE_WRF = "F"
set KEEP_COMBINE_FILE = "F"
set HOUR_OFFSET = "8"
set CONVERT2DAILY = "T"
set DAILY_BEGIN_MODE = "target"   # target | utc_window
#set COMBINE_DIR = "/mnt/167/devin/cmaq_output/${DOMAIN}_${APPL}_150X117/${year}${month}/Lead-time_control/${case_suffix}"             # Supplied by --combine-dir; otherwise use the standalone path below
set first_date = "$target_days[1]"
set year  = `date -ud "$first_date" +%Y`
set month = `date -ud "$first_date" +%m`
set COMBINE_DIR = "/mnt/167/devin/cmaq_output/${DOMAIN}_${APPL}_150X117/${year}${month}/Lead-time_control/${case_suffix}"             # Supplied by --combine-dir; otherwise use the standalone path below
# ----------------------------------------------

# Parse overrides before deriving any paths from case_suffix.
while ( $#argv > 0 )
    set option = "$argv[1]"
    shift argv
    switch ( "${option}" )
        case --help:
        case -h:
            echo "Usage: $0 [options]"
            echo '  --target-days "YYYY-MM-DD ..."  Target local dates.'
            echo '  --experiments "P0:0 A1:1 ..."   Experiment names and lead days.'
            echo "  --case-suffix NAME              Scenario suffix."
            echo "  --segment-root PATH             CMAQ segment output root."
            echo "  --appl NAME                     Application ID used in CCTM and post filenames."
            echo "  --combine-dir PATH              Post-processing output directory."
            echo "  Without options, use the standalone User settings above."
            exit 0
        case --target-days:
        case --experiments:
        case --case-suffix:
        case --segment-root:
        case --appl:
        case --combine-dir:
            if ( $#argv == 0 ) then
                echo "ERROR: missing value for ${option}"
                exit 1
            endif
            if ( "$argv[1]" == "" || "$argv[1]" =~ --* ) then
                echo "ERROR: missing value for ${option}"
                exit 1
            endif
            switch ( "${option}" )
                case --target-days:
                    set target_days = ( $argv[1] )
                    breaksw
                case --experiments:
                    set experiments = ( $argv[1] )
                    breaksw
                case --case-suffix:
                    set case_suffix = "$argv[1]"
                    breaksw
                case --segment-root:
                    set segment_root = "$argv[1]"
                    breaksw
                case --appl:
                    set APPL = "$argv[1]"
                    breaksw
                case --combine-dir:
                    set COMBINE_DIR = "$argv[1]"
                    breaksw
            endsw
            shift argv
            breaksw
        default:
            echo "ERROR: unknown argument: ${option}"
            exit 1
    endsw
end

if ( "${COMBINE_DIR}" == "" ) then
    set COMBINE_DIR = "/mnt/167/devin/cmaq_output/${DOMAIN}_${APPL}/${year}${month}/Lead-time_control/${case_suffix}"
endif

foreach target_day ( ${target_days} )
    set daytag = `date -ud "${target_day}" +%Y%m%d`

    foreach experiment ( ${experiments} )
        set exp_name = `echo ${experiment} | cut -d: -f1`
        set lead_days = `echo ${experiment} | cut -d: -f2`
        @ first_offset = ${lead_days} + 1
        set first_utc_day = `date -ud "${target_day} -${first_offset} day" +%Y-%m-%d`

        set merged_case = "${exp_name}_${daytag}_${case_suffix}_merged"
        set merged_root = "${segment_root}/${merged_case}"
        set postdir = "${COMBINE_DIR}"

        echo "============================================================"
        echo "Post-processing ${exp_name}, target_day=${target_day}"
        echo "UTC combine window: ${first_utc_day} to ${target_day}"
        echo "Merged case: ${merged_case}"

        set today = "${first_utc_day}"
        set todayj = `date -ud "${today}" +%Y%j`
        set stopj = `date -ud "${target_day}" +%Y%j`

        while ( $todayj <= $stopj )
            set year = `date -ud "${today}" +%Y`
            set month = `date -ud "${today}" +%m`
            set jday = `date -ud "${today}" +%Y%j`
            set merged_month_dir = "${merged_root}/${DOMAIN}/${year}/${month}"
            if ( ! -d ${merged_month_dir} ) mkdir -p ${merged_month_dir}

            foreach prefix ( CCTM_ACONC CCTM_APMDIAG )
                set outfile = "${merged_month_dir}/${prefix}_${APPL}_${jday}.nc"
                rm -f ${outfile}

                set files = ( ${segment_root}/${exp_name}_${daytag}_${case_suffix}_seg*/${DOMAIN}/${year}/${month}/${prefix}_${APPL}_${jday}.nc )
                if ( $#files == 1 && ! -e "$files[1]" ) then
                    set files = ()
                endif

                if ( $#files == 0 ) then
                    echo "ERROR: no ${prefix} file found for ${exp_name} ${today} (${jday})"
                    exit 1
                else if ( $#files == 1 ) then
                    ln -s "$files[1]" "$outfile"
                    echo "Linked ${prefix}_${APPL}_${jday}.nc from $files[1]"
                else
                    echo "Concatenating ${prefix}_${APPL}_${jday}.nc from $#files segment files"
                    ncrcat -O $files "$outfile"
                    if ( $status != 0 ) then
                        echo "ERROR: ncrcat failed for ${prefix}_${APPL}_${jday}.nc"
                        exit 1
                    endif
                endif
            end

            set today = `date -ud "${today}+1days" +%Y-%m-%d`
            set todayj = `date -ud "${today}" +%Y%j`
        end

        setenv VRSN ${VRSN}
        setenv DOMAIN ${DOMAIN}
        setenv APPL ${APPL}
        setenv MECH ${MECH}
        setenv LAYER ${LAYER}
        setenv CASE_NAME ${merged_case}
        setenv INPDIR ${INPDIR}
        setenv CCTMOUTDIR_ROOT ${merged_root}
        setenv BEGIN_DATE ${first_utc_day}
        setenv END_DATE ${target_day}
        setenv OUTPUT_BY_YEARMONTH ${OUTPUT_BY_YEARMONTH}
        setenv COMBINE_DIR ${postdir}
        setenv INCLUDE_WRF ${INCLUDE_WRF}
        setenv KEEP_18SPECIES_ONLY T
        setenv KEEP_COMBINE_FILE ${KEEP_COMBINE_FILE}

        csh ${script_path}/1_run_combine_aconc_local.csh
        if ( $status != 0 ) exit 1

        setenv POSTDIR ${postdir}
        setenv RUNID ${VRSN}_${DOMAIN}_${merged_case}_${APPL}
        if ( ${LAYER} == -1 ) then
            setenv LAYER_NAME all_layers
        else
            setenv LAYER_NAME layer_${LAYER}
        endif

        csh ${script_path}/2_extract_18species_by_nco_local.csh | tee ${postdir}/extract_18species.log
        if ( $status != 0 ) exit 1
        set extract_file = `tail -n 1 ${postdir}/extract_18species.log`

        if ( ! -e "${extract_file}" ) then
            echo "ERROR: extracted file not found: ${extract_file}"
            exit 1
        endif

        if ( "${CONVERT2DAILY}" == "T" ) then
            if ( "${DAILY_BEGIN_MODE}" == "target" ) then
                set daily_begin = "${target_day}"
                set daily_end = "${target_day}"
            else
                set daily_begin = "${first_utc_day}"
                set daily_end = "${target_day}"
            endif

            echo "Converting to local daily: ${extract_file}, ${daily_begin} to ${daily_end}, UTC+${HOUR_OFFSET}"
            bash -c "source /program/software/devin_env/bin/activate && python ${script_path}/4_convert2daily_local.py '${extract_file}' '${daily_begin}' '${daily_end}' '${HOUR_OFFSET}' --overwrite"
            if ( $status != 0 ) then
                echo "ERROR: daily conversion failed for ${extract_file}"
                exit 1
            endif

            set daily_file = "${postdir}/Daily_`basename ${extract_file}`"
            bash -c "source /program/software/devin_env/bin/activate && python ${script_path}/check_daily_o3.py '${daily_file}'"
            if ( $status != 0 ) then
                echo "ERROR: daily QC failed for ${daily_file}"
                exit 1
            endif
        endif
    end
end

echo "All local-day control post-processing finished."
