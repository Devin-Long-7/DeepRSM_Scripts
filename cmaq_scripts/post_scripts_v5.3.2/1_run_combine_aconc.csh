#! /bin/csh -f

# ====================== COMBINE_v5.3.X Run Script =================== 
# Usage: run.combine.uncoupled.csh >&! combine.log &                                
#
# To report problems or request help with this script/program:     
#             http://www.epa.gov/cmaq    (EPA CMAQ Website)
#             http://www.cmascenter.org  (CMAS Website)
# ===================================================================  

# ==================================================================
#> Runtime Environment Options
# ==================================================================

#> Choose compiler and set up CMAQ environment with correct
#> libraries using config.cmaq. Options: intel | gcc | pgi
 #setenv compiler intel
 set compiler = intel
 set compilerString = $compiler
#> Source the CMAQ config file. This script is called from a deployed
#> devin_cmaq_scripts/post_scripts_v5.3.2 directory, so ../../.. is not CMAQ_HOME.
if ( ! $?CMAQ_HOME ) then
  if ( $?CCTM_WORKDIR ) then
    setenv CMAQ_HOME ${CCTM_WORKDIR}/../../
  else
    echo "Error: CCTM_WORKDIR and CMAQ_HOME are both unset"
    exit 1
  endif
endif
if ( ! -f "${CMAQ_HOME}/config_cmaq.csh" ) then
  echo "Error: CMAQ config not found: ${CMAQ_HOME}/config_cmaq.csh"
  exit 1
endif
cd "$CMAQ_HOME"
source ./config_cmaq.csh
if ( $status != 0 ) exit $status

# 判断全局变量CASE_NAME是否存在，不存在则表示是直接运行的
if ( ! $?CASE_NAME  ) then
  echo "直接运行或交互式调用"
 #> Set General Parameters for Configuring the Simulation
 set VRSN      = v532              #> Code Version
 set PROC      = mpi               #> serial or mpi
 set MECH      = cb6r3_ae7_aq      #> Mechanism ID
 set APPL      = PRD        #> Application Name (e.g. Gridname)
                                         
 set CASE_NAME  = sector_gd2zero_ic # Case name
 set DOMAIN    = D3   #Simulated Domain
 set LAYER       = -1  #Layer=-1,extact all layers
 set OUTPUT_BY_YEARMONTH = F  #是否按年月格式输出  
 setenv INPDIR  /bigdata/CMAQ_input/devin/PRD/2022
 setenv CCTMOUTDIR_ROOT /home/devin/cmaq_output/${CASE_NAME}
 set BEGIN_DATE = "2022-08-27"
 set END_DATE   = "2022-09-30"     #> ending date    (July 14, 2016)
 set COMBINE_DIR = '' #是否指定Combine后处理目录，为空或未定义则用默认

# set COMBINE_DIR = ''
else
  echo "被其他脚本调用"
endif

echo "VRSN is ${VRSN}" #> v532
echo "PROC is ${PROC}" #> mpi
echo "MECH is ${MECH}" #> cb6r3_ae7_aq
echo "APPL is ${APPL}" #> PRD
echo "CASE_NAME is ${CASE_NAME}" #> cn2zero
echo "OUTPUT_BY_YEARMONTH is ${OUTPUT_BY_YEARMONTH}" #> T
echo "INPDIR is ${INPDIR}" #> /bigdata/CMAQ_input/devin/PRD/2022
echo "CCTMOUTDIR_ROOT is ${CCTMOUTDIR_ROOT}" #> /home/devin/cmaq_output/cn2zero

echo "DOMAIN is ${DOMAIN}" #> D1
echo "LAYER is ${LAYER}" #> -1
echo "BEGIN_DATE is ${BEGIN_DATE}" #> 2022-08-27
echo "END_DATE is ${END_DATE}" #> 2022-09-30
set YEAR = `date -ud "${END_DATE}" +%Y`
set MONTH = `date -ud "${END_DATE}" +%m`
echo "YEAR is ${YEAR}" #> 22
echo "MONTH is ${MONTH}" #> 09
      

#> Define RUNID as any combination of parameters above or others. By default,
#> this information will be collected into this one string, $RUNID, for easy
#> referencing in output binaries and log files as well as in other scripts.
 setenv RUNID  ${VRSN}_${DOMAIN}_${CASE_NAME}_${APPL} #${VRSN}_${compilerString}_${APPL}
 
echo "RUNID is $RUNID"
#> Set the build directory if this was not set above 
#> (this is where the CMAQ executable is located by default).
 if ( ! $?BINDIR ) then
  setenv BINDIR $CMAQ_HOME/POST/combine/scripts/BLD_combine_${VRSN}_${compilerString}
 endif

#> Set the name of the executable.
 setenv EXEC combine_${VRSN}.exe

#> Set location of CMAQ repo.  This will be used to point to the correct species definition files.
 setenv REPO_HOME  $CMAQ_HOME  #${CMAQ_REPO}

#  setenv INPDIR  /bigdata/CMAQ_input/devin/PRD/2022
#  setenv OUTDIR_ROOT /home/devin/cmaq_output/${CASE_NAME}
#> Set working, input and output directories
# setenv CMAQ_DATA  ${OUTDIR_ROOT}/D1/2022/$MONTH
 setenv METDIR     ${INPDIR}/mcip/${DOMAIN}              #> Met Output Directory,default: #${CMAQ_DATA}/$APPL/met/mcip
 setenv CCTMOUTDIR ${CCTMOUTDIR_ROOT}/${DOMAIN}/${YEAR}/${MONTH}      #> CCTM Output Directory, default:${CMAQ_DATA}/output_CCTM_${RUNID}
 setenv POSTDIR    ${CCTMOUTDIR_ROOT}/post                      #> Location where combine file will be written

#added by devin
if ((! $?COMBINE_DIR) || ("$COMBINE_DIR" == "")) then
   setenv POSTDIR    ${CCTMOUTDIR_ROOT}/post
else
   setenv POSTDIR $COMBINE_DIR
endif

if ( ! -e $POSTDIR ) then
	  mkdir -p $POSTDIR
endif

echo "CCTMOUTDIR is $CCTMOUTDIR"


# =====================================================================
#> COMBINE Configuration Options
# =====================================================================

#> Set Start and End Days for looping
#  set BEGIN_DATE = "2022-08-27"
 set START_DATE = ${BEGIN_DATE}     #> beginning date (July 1, 2016)
#  set END_DATE   = "2022-09-30"     #> ending date    (July 14, 2016)
 
#> Set location of species definition files for concentration and deposition species.

if ( $LAYER == -1 ) then
   setenv SPEC_CONC $REPO_HOME/POST/combine/scripts/spec_def_files/SpecDef_${MECH}_all_layers.txt
   setenv SPEC_DEP  $REPO_HOME/POST/combine/scripts/spec_def_files/SpecDef_Dep_${MECH}_all_layers.txt
   setenv LAYER_NAME all_layers
else
   setenv SPEC_CONC $REPO_HOME/POST/combine/scripts/spec_def_files/SpecDef_${MECH}.txt
   setenv SPEC_DEP  $REPO_HOME/POST/combine/scripts/spec_def_files/SpecDef_Dep_${MECH}.txt
   setenv LAYER_NAME layer_${LAYER}
endif
   
# setenv SPEC_CONC $REPO_HOME/POST/combine/scripts/spec_def_files/SpecDef_${MECH}.txt
# setenv SPEC_DEP  $REPO_HOME/POST/combine/scripts/spec_def_files/SpecDef_Dep_${MECH}.txt

#> Use GENSPEC switch to generate a new specdef file (does not generate output file).
 setenv GENSPEC N


# =====================================================================
#> Begin Loop Through Simulation Days to Create ACONC File
# =====================================================================

#> Set the species definition file for concentration species.
 setenv SPECIES_DEF $SPEC_CONC
 
#> Loop through all days between START_DAY and END_DAY
 set TODAYG = ${START_DATE}
 set TODAYJ = `date -ud "${START_DATE}" +%Y%j` #> Convert YYYY-MM-DD to YYYYJJJ
 set STOP_DAY = `date -ud "${END_DATE}" +%Y%j` #> Convert YYYY-MM-DD to YYYYJJJ

 if ( ${OUTPUT_BY_YEARMONTH} == F  ) then
    setenv OUTFILE ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${START_DATE}_${END_DATE}.nc
  endif


 while ($TODAYJ <= $STOP_DAY )  #>Compare dates in terms of YYYYJJJ
 
  #> Retrieve Calendar day Information
   set YYYY = `date -ud "${TODAYG}" +%Y`
   set YY = `date -ud "${TODAYG}" +%y`
   set MM = `date -ud "${TODAYG}" +%m`
   set DD = `date -ud "${TODAYG}" +%d`
  #> for files that are indexed with Julian day:
   set YYYYJJJ = `date -ud "${TODAYG}" +%Y%j` 

  #> Define name of combine output file to save hourly average concentration.
  #> A new file will be created for each month/year.
  if ( ${OUTPUT_BY_YEARMONTH} == T  ) then
   setenv OUTFILE ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_$YYYY${MM}.nc
  endif

#   setenv OUTFILE ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_$YYYY${MM}.nc

  #> Define name of input files needed for combine program.
  #> File [1]: CMAQ conc/aconc file
  #> File [2]: MCIP METCRO3D file
  #> File [3]: CMAQ APMDIAG file
  #> File [4]: MCIP METCRO2D file
   setenv INFILE1 $CCTMOUTDIR/CCTM_ACONC_${APPL}_$YYYYJJJ.nc  #default: $CCTMOUTDIR/CCTM_ACONC_${RUNID}_$YYYY$MM$DD.nc
   setenv INFILE2 $METDIR/METCRO3D_$YYYYJJJ
   setenv INFILE3 $CCTMOUTDIR/CCTM_APMDIAG_${APPL}_$YYYYJJJ.nc #default: $CCTMOUTDIR/CCTM_APMDIAG_${RUNID}_$YYYY$MM$DD.nc
   setenv INFILE4 $METDIR/METCRO2D_$YYYYJJJ

  #> Executable call:
   ${BINDIR}/${EXEC}
   if ( $status != 0 ) then
      echo "Error: combine failed for ${TODAYG}"
      exit 1
   endif

  #> Increment both Gregorian and Julian Days
   set TODAYG = `date -ud "${TODAYG}+1days" +%Y-%m-%d` #> Add a day for tomorrow
   set TODAYJ = `date -ud "${TODAYG}" +%Y%j` #> Convert YYYY-MM-DD to YYYYJJJ

 end #Loop to the next Simulation Day

 
exit 0
