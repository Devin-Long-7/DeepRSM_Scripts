#!/bin/csh -f

set script_path = `dirname $0`
set script_path = `cd $script_path && pwd`
set CMAQ_HOME = "/program/rain/Build_CMAQ/CMAQ_Project"
set project_root = `cd ${CMAQ_HOME} && pwd`

if ( ! $?compiler ) set compiler = intel
set compilerString = $compiler
source ${project_root}/config_cmaq.csh
echo "CMAQ_HOME: $CMAQ_HOME"
if ( ! $?VRSN ) setenv VRSN v532
if ( ! $?PROC ) setenv PROC mpi
if ( ! $?MECH ) setenv MECH cb6r3_ae7_aq
if ( ! $?APPL ) setenv APPL PRD
if ( ! $?DOMAIN ) setenv DOMAIN D3
if ( ! $?LAYER ) setenv LAYER -1
if ( ! $?OUTPUT_BY_YEARMONTH ) setenv OUTPUT_BY_YEARMONTH F
if ( ! $?INPDIR ) setenv INPDIR /bigdata/CMAQ_input/devin/PRD/2022
if ( ! $?COMBINE_DIR ) setenv COMBINE_DIR ""

if ( ! $?CASE_NAME || ! $?CCTMOUTDIR_ROOT || ! $?BEGIN_DATE || ! $?END_DATE ) then
    echo "ERROR: CASE_NAME, CCTMOUTDIR_ROOT, BEGIN_DATE, and END_DATE must be set."
    exit 1
endif

setenv RUNID ${VRSN}_${DOMAIN}_${CASE_NAME}_${APPL}

if ( ! $?BINDIR ) then
    setenv BINDIR $CMAQ_HOME/POST/combine/scripts/BLD_combine_${VRSN}_${compilerString}
endif
setenv EXEC combine_${VRSN}.exe
setenv REPO_HOME $CMAQ_HOME

setenv METDIR ${INPDIR}/mcip/${DOMAIN}

if ( "${COMBINE_DIR}" == "" ) then
    setenv POSTDIR ${CCTMOUTDIR_ROOT}/post
else
    setenv POSTDIR ${COMBINE_DIR}
endif

if ( ! -e $POSTDIR ) mkdir -p $POSTDIR

if ( $LAYER == -1 ) then
    setenv SPEC_CONC $REPO_HOME/POST/combine/scripts/spec_def_files/SpecDef_${MECH}_all_layers.txt
    setenv LAYER_NAME all_layers
else
    setenv SPEC_CONC $REPO_HOME/POST/combine/scripts/spec_def_files/SpecDef_${MECH}.txt
    setenv LAYER_NAME layer_${LAYER}
endif

setenv GENSPEC N
setenv SPECIES_DEF $SPEC_CONC

set START_DATE = ${BEGIN_DATE}
set TODAYG = ${START_DATE}
set TODAYJ = `date -ud "${START_DATE}" +%Y%j`
set STOP_DAY = `date -ud "${END_DATE}" +%Y%j`

if ( ${OUTPUT_BY_YEARMONTH} == F ) then
    setenv OUTFILE ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${START_DATE}_${END_DATE}.nc
endif

while ( $TODAYJ <= $STOP_DAY )
    set YYYY = `date -ud "${TODAYG}" +%Y`
    set MM = `date -ud "${TODAYG}" +%m`
    set YYYYJJJ = `date -ud "${TODAYG}" +%Y%j`
    # Merged segment files are stored under each UTC day's year/month.
    setenv CCTMOUTDIR ${CCTMOUTDIR_ROOT}/${DOMAIN}/${YYYY}/${MM}

    if ( ${OUTPUT_BY_YEARMONTH} == T ) then
        setenv OUTFILE ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${YYYY}${MM}.nc
    endif

    setenv INFILE1 $CCTMOUTDIR/CCTM_ACONC_${APPL}_${YYYYJJJ}.nc
    setenv INFILE2 $METDIR/METCRO3D_${YYYYJJJ}
    setenv INFILE3 $CCTMOUTDIR/CCTM_APMDIAG_${APPL}_${YYYYJJJ}.nc
    setenv INFILE4 $METDIR/METCRO2D_${YYYYJJJ}

    if ( ! -e $INFILE1 ) then
        echo "ERROR: missing INFILE1 $INFILE1"
        exit 1
    endif
    if ( ! -e $INFILE3 ) then
        echo "ERROR: missing INFILE3 $INFILE3"
        exit 1
    endif

    echo "COMBINE ACONC day ${TODAYG}: ${INFILE1}"
    ${BINDIR}/${EXEC}
    if ( $status != 0 ) then
        echo "ERROR: combine failed for ${TODAYG}"
        exit 1
    endif

    set TODAYG = `date -ud "${TODAYG}+1days" +%Y-%m-%d`
    set TODAYJ = `date -ud "${TODAYG}" +%Y%j`
end

echo $OUTFILE
