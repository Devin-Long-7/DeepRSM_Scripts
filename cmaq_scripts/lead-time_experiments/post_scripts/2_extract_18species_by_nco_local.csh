#!/bin/csh -f

if ( ! $?KEEP_18SPECIES_ONLY ) setenv KEEP_18SPECIES_ONLY T
if ( ! $?INCLUDE_WRF ) setenv INCLUDE_WRF T
if ( ! $?KEEP_COMBINE_FILE ) setenv KEEP_COMBINE_FILE T
if ( ! $?OUTPUT_BY_YEARMONTH ) setenv OUTPUT_BY_YEARMONTH F

if ( ! $?POSTDIR || ! $?RUNID || ! $?LAYER_NAME || ! $?BEGIN_DATE || ! $?END_DATE ) then
    echo "ERROR: POSTDIR, RUNID, LAYER_NAME, BEGIN_DATE, and END_DATE must be set."
    exit 1
endif

if ( "${KEEP_18SPECIES_ONLY}" != "T" ) then
    echo "KEEP_18SPECIES_ONLY is not T; nothing to extract."
    exit 0
endif

set START_DATE = ${BEGIN_DATE}
set start_year = `echo ${BEGIN_DATE} | cut -c1-4`
set end_month = `echo ${END_DATE} | cut -c6-7`

if ( ${OUTPUT_BY_YEARMONTH} == F ) then
    set infile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${START_DATE}_${END_DATE}.nc
    set outfile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${START_DATE}_${END_DATE}_18species.nc
else
    set ym = "${start_year}${end_month}"
    set infile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${ym}.nc
    set outfile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${ym}_18species.nc
endif

if ( ! -f $infile ) then
    echo "ERROR: ${infile} not exist"
    exit 1
endif

set base_vars = (HNO3 H2O2 N2O5 NO2 FORM HONO NO O3 SO2 NH3 OH ISOP TERP ASO4IJ ANO3IJ ANH4IJ ASOCIJ PM25_TOT NOX VOC O3_UGM3)
set wrf_vars = (RH SFC_TMP PBLH SOL_RAD precip WSPD10 WDIR10 GLW PRSFC Q2)

set varlist = ($base_vars)
if ( "${INCLUDE_WRF}" == "T" ) then
    set varlist = ($varlist $wrf_vars)
endif

set varstr = "$varlist[1]"
@ i = 2
while ( $i <= $#varlist )
    set varstr = "${varstr},$varlist[$i]"
    @ i++
end

echo "Extract file: ${infile}"
echo "Variables: ${varstr}"
ncks -O -v "$varstr" "$infile" "$outfile"
if ( $status != 0 ) then
    echo "ERROR: ncks extraction failed."
    exit 1
endif

if ( -e $outfile && ${KEEP_COMBINE_FILE} != T ) then
    rm -f $infile
endif

echo $outfile
