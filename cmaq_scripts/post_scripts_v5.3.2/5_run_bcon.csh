#!/bin/csh -f

# ======================= BCONv5.3.X Run Script ======================== 
# Usage: run.bcon.csh >&! bcon.log &                                
#
# To report problems or request help with this script/program:        
#             http://www.cmascenter.org
# ==================================================================== 

# ==================================================================
#> Runtime Environment Options
# ==================================================================

#> Choose compiler and set up CMAQ environment with correct 
#> libraries using config.cmaq. Options: intel | gcc | pgi
 setenv compiler intel 
 set compilerString = $compiler

#> Source the config_cmaq file to set the run environment
#  pushd ../../../
#  source ./config_cmaq.csh $compiler
#  popd

#获取参数
echo "APPL_NAME is ${APPL}"
echo "BEGIN_DATE is ${BEGIN_DATE}"
echo "END_DATE is ${END_DATE}"
echo "CASE_NAME is ${CASE_NAME}"
echo "INPDIR is ${INPDIR}"
echo "CMAQ_HOME is ${CMAQ_HOME}"
echo "DOMAIN is ${DOMAIN}"
echo "CCTMOUTDIR_ROOT is ${CCTMOUTDIR_ROOT}"

#提取当前层的结果作为下一层的输入
# 提取 DOMAIN 中的数字部分
#set num = `echo $DOMAIN | sed 's/[^0-9]//g'`
#set prefix = `echo $DOMAIN | sed 's/[0-9]*$//'`
# 数字加一
#@ new_num = $num + 1
#set SUB_DOMAIN = "${prefix}${new_num}"
echo "SUB_DOMAIN is ${SUB_DOMAIN}"

#BINDIR $CMAQ_HOME/POST/combine/scripts/BLD_combine_${VRSN}_${compilerString}
pushd ${CMAQ_HOME}/PREP/bcon/scripts
# set cwd = `pwd`
echo "Current working directory is $cwd" 
#> Check that CMAQ_DATA is set:
#  if ( ! -e $CMAQ_DATA ) then
#     echo "   $CMAQ_DATA path does not exist"
#     exit 1
#  endif
 echo " "; echo " Input data path, CMAQ_DATA set to $CMAQ_DATA"; echo " "

#> Set General Parameters for Configuring the Simulation
 set VRSN     = ${VRSN}                    #> Code Version
 set APPL     = ${APPL} #PRD # 2016_12SE1              #> Application Name
 set BCTYPE   = regrid                  #> Boundary condition type [profile|regrid]
 set CASE_NAME = ${CASE_NAME}  #cn2zero
 set DATA_DIR = ${INPDIR} #/bigdata/CMAQ_input/devin/PRD/2022
#> Set the build directory:

 set BLD      = $cwd/BLD_BCON_${VRSN}_${compilerString} #${CMAQ_HOME}/PREP/bcon/scripts/BLD_BCON_${VRSN}_${compilerString}
 set EXEC     = BCON_${VRSN}.exe  
 cat $BLD/BCON_${VRSN}.cfg; echo " "; set echo

#> Horizontal grid definition 
 setenv GRID_NAME SD_2013 # SE53BENCH               #> check GRIDDESC file for GRID_NAME options
#setenv GRIDDESC $CMAQ_DATA/$APPL/met/mcip/GRIDDESC #> grid description file 
 setenv GRIDDESC ${DATA_DIR}/mcip/${SUB_DOMAIN}/GRIDDESC #/work/MOD3DATA/SE53BENCH/met/mcip/GRIDDESC
 setenv IOAPI_ISPH 20                     #> GCTP spheroid, use 20 for WRF-based modeling

#> I/O Controls
 setenv IOAPI_LOG_WRITE F     #> turn on excess WRITE3 logging [ options: T | F ]
 setenv IOAPI_OFFSET_64 YES   #> support large timestep records (>2GB/timestep record) [ options: YES | NO ]
 setenv EXECUTION_ID $EXEC    #> define the model execution id

# =====================================================================
#> BCON Configuration Options
#
# BCON can be run in one of two modes:                                     
#     1) regrids CMAQ CTM concentration files (BC type = regrid)     
#     2) use default profile inputs (BC type = profile)
# =====================================================================

 setenv BCON_TYPE ` echo $BCTYPE | tr "[A-Z]" "[a-z]" `

# =====================================================================
#> Input/Output Directories
# =====================================================================

#added by devin
# 检查 BC_OUTPUT_DIR 是否未定义或为空
if ((! $?BC_OUTPUT_DIR) || ("${BC_OUTPUT_DIR}" == "")) then
   setenv OUTDIR $CMAQ_DATA/bcon/${SUB_DOMAIN}_${CASE_NAME}  #> output file directory, default:$CMAQ_HOME/data/bcon
else
   setenv OUTDIR  $BC_OUTPUT_DIR/
endif


# set OUTDIR   = $CMAQ_DATA/bcon/D2_${CASE_NAME}       #> output file directory, default:$CMAQ_HOME/data/bcon


# =====================================================================
#> Input Files
#  
#  Regrid mode (BC = regrid) (includes nested domains, windowed domains,
#                             or general regridded domains)
#     CTM_CONC_1 = the CTM concentration file for the coarse domain          
#     MET_CRO_3D_CRS = the MET_CRO_3D met file for the coarse domain
#     MET_BDY_3D_FIN = the MET_BDY_3D met file for the target nested domain
#                                                                            
#  Profile mode (BC type = profile)
#     BC_PROFILE = static/default BC profiles 
#     MET_BDY_3D_FIN = the MET_BDY_3D met file for the target domain 
#
# NOTE: SDATE (yyyyddd), STIME (hhmmss) and RUNLEN (hhmmss) are only 
#       relevant to the regrid mode and if they are not set,  
#       these variables will be set from the input MET_BDY_3D_FIN file
# =====================================================================
#> Output File
#     BNDY_CONC_1 = gridded BC file for target domain
# =====================================================================
 
    set BEGIN_DATE = $BEGIN_DATE #"2022-08-27"
    set END_DATE   = $END_DATE #"2022-09-30"

    set TODAYG = ${BEGIN_DATE}
    set TODAYJ = `date -ud "${BEGIN_DATE}" +%Y%j` #> Convert YYYY-MM-DD to YYYYJJJ
    set STOP_DAY = `date -ud "${END_DATE}" +%Y%j` #> Convert YYYY-MM-DD to YYYYJJJ

    set YEAR = `date -ud "${END_DATE}" +%Y`
    set MONTH = `date -ud "${END_DATE}" +%m`
while ($TODAYJ <= $STOP_DAY )  #>Compare dates in terms of YYYYJJJ


    #> Retrieve Calendar day Information
    set YYYYMMDD = `date -ud "${TODAYG}" +%Y%m%d` #> Convert YYYY-MM-DD to YYYYMMDD
    set YYYYMM = `date -ud "${TODAYG}" +%Y%m`     #> Convert YYYY-MM-DD to YYYYMM
    set YYYY = `date -ud "${TODAYG}" +%Y`         #> Convert YYYY-MM-DD to YYYY
    set YYMMDD = `date -ud "${TODAYG}" +%y%m%d`   #> Convert YYYY-MM-DD to YYMMDD
    set YYYYJJJ = $TODAYJ

   # set YYYYJJJ  = `date -ud "${DATE}" +%Y%j`   #> Convert YYYY-MM-DD to YYYYJJJ
   # set YYMMDD   = `date -ud "${DATE}" +%y%m%d` #> Convert YYYY-MM-DD to YYMMDD
   # set YYYYMMDD = `date -ud "${DATE}" +%Y%m%d` #> Convert YYYY-MM-DD to YYYYMMDD

#   setenv SDATE           ${YYYYJJJ}
#   setenv STIME           000000
#   setenv RUNLEN          240000

 if ( $BCON_TYPE == regrid ) then 
    setenv CTM_CONC_1 ${CCTMOUTDIR_ROOT}/${DOMAIN}/${YEAR}/${MONTH}/CCTM_CONC_${APPL}_${YYYYJJJ}.nc #/work/MOD3EVAL/sjr/CCTM_CONC_v53_intel18.0_2016_CONUS_test_${YYYYMMDD}.nc
    setenv MET_CRO_3D_CRS ${DATA_DIR}/mcip/${DOMAIN}/METCRO3D_${YYYYJJJ}  #/work/MOD3DATA/2016_12US1/met/mcip_v43_wrf_v381_ltng/METCRO3D.12US1.35L.${YYMMDD}
    setenv MET_BDY_3D_FIN ${DATA_DIR}/mcip/${SUB_DOMAIN}/METBDY3D_${YYYYJJJ} #/work/MOD3DATA/SE53BENCH/met/mcip/METBDY3D_${YYMMDD}.nc
    setenv BNDY_CONC_1    "$OUTDIR/BCON_${YYYYJJJ} -v" #"$OUTDIR/BCON_${VRSN}_${APPL}_${BCON_TYPE}_${YYYYMMDD} -v"
 endif

 if ( $BCON_TYPE == profile ) then
    setenv BC_PROFILE $BLD/avprofile_cb6r3m_ae7_kmtbr_hemi2016_v53beta2_m3dry_col051_row068.csv
    setenv MET_BDY_3D_FIN ${DATA_DIR}/mcip/D1/METBDY3D_${YYYYJJJ} # /work/MOD3DATA/SE53BENCH/met/mcip/METBDY3D_${YYMMDD}.nc
    setenv BNDY_CONC_1    "$OUTDIR/BCON_${YYYYJJJ} -v" # "$OUTDIR/BCON_${VRSN}_${APPL}_${BCON_TYPE}_${YYYYMMDD} -v"
 endif

# =====================================================================
#> Output File
# =====================================================================
 
#>- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

 if ( ! -d "$OUTDIR" ) mkdir -p $OUTDIR

 ls -l $BLD/$EXEC; size $BLD/$EXEC
# unlimit
 limit

#> Executable call:
 time $BLD/$EXEC

  #> Increment both Gregorian and Julian Days
  set TODAYG = `date -ud "${TODAYG}+1days" +%Y-%m-%d` #> Add a day for tomorrow
  set TODAYJ = `date -ud "${TODAYG}" +%Y%j` #> Convert YYYY-MM-DD to YYYYJJJ

end  #Loop to the next Simulation Day
 exit() 
