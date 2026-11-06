#!/bin/csh -f

# ===================== CCTMv5.3 Run Script =========================
# Usage: run.cctm >&! cctm_2016_12US1.log &
#
# To report problems or request help with this script/program:
#             http://www.epa.gov/cmaq    (EPA CMAQ Website)
#             http://www.cmascenter.org  (CMAS Website)
# ===================================================================

#> Simple Linux Utility for Resource Management System
#> (SLURM) - The following specifications are recommended
#> for executing the runscript on the cluster at the
#> National Computing Center used primarily by EPA.
#SBATCH -n 128
#SBATCH --constraint=broadwell
##SBATCH --constraint=cascadelake
#SBATCH -J cmaq_2018_4.2
#SBATCH -p oar
#SBATCH -t 168:00:00
##SBATCH -p debug
##SBATCH -t 4:00:00
#SBATCH --gid=romo
#SBATCH -A romo
#SBATCH -o /work/ROMO/users/bkx/cmaq/o1422/task4.2/2018/cctm/run/cmaq_%j.txt
#SBATCH --no-requeue

#cat $0
uname -a
date

# use --constraint=broadwell   to use the 32-core nodes
# use --constraint=cascadelake to use the 48-core nodes

# note email from Ed Anderson Nov 2020:

# If you do not request the Cascade Lake nodes, your job will be
# scheduled on the older 32-core nodes if available, but may run on the
# new 48-core nodes if there are not enough 32-core nodes free.

# In testing, we found that executables using the 2019 version of Intel
# MPI (and, to a lesser extent, the 2018 version of Intel MPI) need to
# link in a newer version. We have changed the default version of Intel
# MPI from intelmpi/19.0.5 to intelmpi/19.0.8.  If you currently load an
# intelmpi module in your job script or startup file that is
# intelmpi/19.0.5 or older, we recommend you change that to load
# intelmpi/19.0.8 instead.

set echo

#set base0 = /work/ROMO/users/bkx/cmaq/o1422/task4.2/2018/cctm

#> The following commands output information from the SLURM
#> scheduler to the log files for traceability.
   ##if ( $?SLURM_JOB_ID ) then
      ##echo Job ID is $SLURM_JOB_ID
      ##echo "Running on nodes `printenv SLURM_JOB_NODELIST`"
      ##echo Host is $SLURM_SUBMIT_HOST
      #> Switch to the working directory. By default,
      #>   SLURM launches processes from your home directory.
      ##echo Working directory is $SLURM_SUBMIT_DIR
      ##cd $SLURM_SUBMIT_DIR
   ##endif

#> Configure the system environment and set up the module
#> capability
   limit stacksize unlimited
#

# ===================================================================
#> Runtime Environment Options
# ===================================================================

echo 'Start Model Run At ' `date`

#> Toggle Diagnostic Mode which will print verbose information to
#> standard output
 setenv CTM_DIAG_LVL 0

#> Choose compiler and set up CMAQ environment with correct
#> libraries using config.cmaq. Options: intel | gcc | pgi
 ##if ( ! $?compiler ) then
   ##setenv compiler intel
 ##endif
 ##if ( ! $?compilerVrsn ) then
   ##setenv compilerVrsn 18.0
 ##endif

# set up modules as needed
# /home/kappel/CMAQ_Code/PROJECTS/CMAQv5321_22Dec2020_EQUATES/CCTM/scripts/BLD_CCTM_v532_intel18.0_M3Dry/CCTM_v532.exe
##source /etc/profile.d/modules.csh
##module purge
##source /etc/profile.d/modules.csh
##module load modules
##echo 'before config:'
##module list
# from source /home/kappel/CMAQ_Code/PROJECTS/CMAQv5321_22Dec2020_EQUATES/config_cmaq.csh intel 18.0
# should be:
  # 1) modules                    3) netcdf-4.4.1/intel-18.0    5) pnetcdf-1.8.1/intel-18.0
  # 2) intel/18.0.1               4) intelmpi/2018.0.128        6) forge/20.0
##module load intel/18.0.1
##module load netcdf-4.4.1/intel-18.0
##module load intelmpi/2018.0.128
##module load pnetcdf-1.8.1/intel-18.0
##module load forge/20.0
##echo 'after config:'
##module list

setenv CMAQ_HOME /program/rain/Build_CMAQ/CMAQ_Project/CCTM/scripts

##set compilerString = intel18.0

# # warning: testing only alias
# alias time   echo
# alias mv     echo
# alias rm     echo
# alias qsub   echo
# alias sbatch echo
# alias chgrp  echo

#> Set General Parameters for Configuring the Simulation
 set VRSN      = v532              #> Code Version
 set PROC      = mpi               #> serial or mpi
 set MECH      = cb6r3_ae7_aq      #> Mechanism ID
 set EMIS      = na # set later    #> Emission Inventory Details
# set REGION      = hn # set later    #> Emission Inventory Details
 #set SCRIPTNAME = devin_region2zero_scripts #the dir name of run script
 set CASE_NAME   = prd2zero_iconly   #> Case Name (C10 IC-only)
 set C11_CASE    = prd2zero          #> C11 propagated run whose CGRID we borrow as IC
# e.g.           2018gc_MP_cb6ae7_18j.v532.12US1_35
# set APPL = 2032fj_16j_cb6r3_ae7_aq_nvpoa.v532_m3dry.12US2_35  # describe emis, model, grid
# set APPL = 2032fj_16j_cb6r3_ae7_aq_nvpoa_50ptegu.v532_m3dry.12US2_35
# set APPL  = 2032fj_16j_cb6r3_ae7_aq_nvpoa_50ptegunoxso2.v532_m3dry.12US2_35
# set APPL  = 2032fj_16j_cb6r3_ae7_aq_nvpoa_50pteguso2.v532_m3dry.12US2_35
 set APPL  = PRD

#> Define RUNID as any combination of parameters above or others. By default,
#> this information will be collected into this one string, $RUNID, for easy
#> referencing in output binaries and log files as well as in other scripts.
# setenv RUNID  ${VRSN}_${compilerString}_${APPL}
 setenv RUNID  $APPL

#> Set the build directory (this is where the CMAQ executable
#> is located by default).
# set BLD = /program/rain/Build_CMAQ/CMAQ_Project/CCTM/scripts/BLD_CCTM_v532_intel
 set BLD = ${CMAQ_HOME}/BLD_CCTM_v532_intel
# set EXEC = CCTM_${VRSN}.exe
 set EXEC = CCTM_${VRSN}.exe


#> Output Each line of Runscript to Log File
 if ( $CTM_DIAG_LVL != 0 ) set echo

#> Set Working, Input, and Output Directories
 setenv WORKDIR ${CMAQ_HOME}                 #> Working Directory. Where the runscript is.
 setenv OUTDIR  /home/devin/cmaq_output/${CASE_NAME}/D3/2022   #> Output Directory
 setenv INPDIR  /bigdata/CMAQ_input/devin/PRD/2022                         #Input Directory
 setenv LOGDIR  $cwd/LOGS  #> Log Directory Location
 setenv NMLpath ${BLD}             #> Location of Namelists. Common places are:
                                   #> ${WORKDIR} | ${CCTM_SRC}/MECHS/${MECH} | ${BLD}

 echo ""
 echo "Working Directory is $WORKDIR"
 echo "Build Directory is $BLD"
 echo "Output Directory is $OUTDIR"
 echo "Log Directory is $LOGDIR"
 echo "Executable Name is $EXEC"

# =====================================================================
#> CCTM Configuration Options
# =====================================================================

 set firstday  = "2022-08-27"

#> Set Start and End Days for looping
set START_DATE = "2022-08-27"    #> beginning date
#set START_DATE = "2018-08-25"    #> beginning date
set END_DATE   = "2022-09-30"    #> end date
set month = '09'
 setenv OUTDIR  $OUTDIR/$month   #> Output Directory
 echo "Output Directory is $OUTDIR"




 if ( $START_DATE == $firstday ) then
    setenv NEW_START TRUE
 else
    setenv NEW_START FALSE             #> Set to FALSE for model restart
 endif

#> Set Timestepping Parameters
 set STTIME     = 000000           #> beginning GMT time (HHMMSS)
 set NSTEPS     = 240000           #> time duration (HHMMSS) for this run
 set TSTEP      = 010000           #> output time step interval (HHMMSS)

#> Horizontal domain decomposition
if ( $PROC == serial ) then
   setenv NPCOL_NPROW "1 1"; set NPROCS   = 1 # single processor setting
else
   #@ NPCOL  =  2; @ NPROW =  64  # 128 proc
   @ NPCOL  =  8; @ NPROW = 4   # 128 proc
   @ NPROCS = $NPCOL * $NPROW
   setenv NPCOL_NPROW "$NPCOL $NPROW";
endif

#> Define Execution ID: e.g. [CMAQ-Version-Info]_[User]_[Date]_[Time]
setenv EXECUTION_ID "CMAQ_CCTM${VRSN}_`id -u -n`_`date -u +%Y%m%d_%H%M%S_%N`"    #> Inform IO/API of the Execution ID
echo ""
echo "---CMAQ EXECUTION ID: $EXECUTION_ID ---"

#> Keep or Delete Existing Output Files
set CLOBBER_DATA = TRUE

#> Logfile Options
#> Master Log File Name; uncomment to write standard output to a log, otherwise write to screen
#setenv LOGFILE $CMAQ_HOME/$RUNID.log
if (! -e $LOGDIR ) then
  mkdir -p $LOGDIR
endif
setenv PRINT_PROC_TIME Y           #> Print timing for all science subprocesses to Logfile
                                   #>   [ default: TRUE or Y ]
setenv STDOUT T                    #> Override I/O-API trying to write information to both the processor
                                   #>   logs and STDOUT [ options: T | F ]

setenv GRID_NAME SD_2013     #> check GRIDDESC file for GRID_NAME options
setenv GRIDDESC ${INPDIR}/mcip/D3/GRIDDESC   #> grid description file

#> Retrieve the number of columns, rows, and layers in this simulation
set NZ = 14  #previous20231014 NZ=14
set NX = `grep -A 1 ${GRID_NAME} ${GRIDDESC} | tail -1 | sed 's/  */ /g' | cut -d' ' -f6`
set NY = `grep -A 1 ${GRID_NAME} ${GRIDDESC} | tail -1 | sed 's/  */ /g' | cut -d' ' -f7`
set NCELLS = `echo "${NX} * ${NY} * ${NZ}" | bc -l`

setenv CTM_MGEMDIAG  N       # marine emissions diagnostic file [ default: N ]

#> Output Species and Layer Options
   #> CONC file species; comment or set to "ALL" to write all species to CONC
#   setenv CONC_SPCS "O3 NO ANO3I ANO3J NO2 FORM ISOP NH3 ANH4I ANH4J ASO4I ASO4J"
   setenv CONC_SPCS "ALL"
   #setenv CONC_BLEV_ELEV "1 1"
   setenv CONC_BLEV_ELEV "1 14" #> CONC file layer range; comment out to write all layers to CONC

   #> ACONC file species; comment or set to "ALL" to write all species to ACONC
   #setenv AVG_CONC_SPCS "O3 NO CO NO2 ASO4I ASO4J NH3"
   setenv AVG_CONC_SPCS "ALL"
   #setenv ACONC_BLEV_ELEV "1 1"
   setenv ACONC_BLEV_ELEV "1 14" #> ACONC file layer range; comment to write all layers to ACONC
   setenv AVG_FILE_ENDTIME N     #> override default beginning ACONC timestamp [ default: N ]

#> Synchronization Time Step and Tolerance Options
#setenv CTM_MAXSYNC 720       #> max sync time step (sec) [ default: 720 ]
setenv CTM_MAXSYNC 300       #> max sync time step (sec) [ default: 720 ]
setenv CTM_MINSYNC  60       #> min sync time step (sec) [ default: 60 ]
setenv SIGMA_SYNC_TOP 0.7    #> top sigma level thru which sync step determined [ default: 0.7 ]
#setenv ADV_HDIV_LIM 0.95    #> maximum horiz. div. limit for adv step adjust [ default: 0.9 ]
setenv CTM_ADV_CFL 0.95      #> max CFL [ default: 0.75]
#setenv RB_ATOL 1.0E-09      #> global ROS3 solver absolute tolerance [ default: 1.0E-07 ]

#> Science Options
setenv CTM_OCEAN_CHEM Y      #> Flag for ocean halogen chemistry and sea spray aerosol emissions [ default: Y ]

# no dust files avail confirmed email 24 sep 2020
setenv CTM_WB_DUST N         #> use inline windblown dust emissions [ default: Y ]
setenv CTM_WBDUST_BELD BELD3 #> landuse database for identifying dust source regions
                             #>    [ default: UNKNOWN ]; ignore if CTM_WB_DUST = N
# lightning data is not available.  confirmed email 24 sep 2020
setenv CTM_LTNG_NO N         #> turn on lightning NOx [ default: N ]
setenv CTM_WVEL Y            #> save derived vertical velocity component to conc
                             #>    file [ default: N ]
setenv KZMIN Y               #> use Min Kz option in edyintb [ default: Y ],
                             #>    otherwise revert to Kz0UT

setenv CTM_MOSAIC N          #> landuse specific deposition velocities [ default: N ]

setenv CTM_FST N             #> mosaic method to get land-use specific stomatal flux
                             #>    [ default: N ]

setenv PX_VERSION N          #> WRF PX LSM
setenv CLM_VERSION N         #> WRF CLM LSM
setenv NOAH_VERSION Y        #> WRF NOAH LSM
setenv CTM_ABFLUX N          #> ammonia bi-directional flux for in-line deposition
                             #>    velocities [ default: N ]
setenv CTM_BIDI_FERT_NH3 N   #> subtract fertilizer NH3 from emissions because it will be handled
                             #>    by the BiDi calculation [ default: Y ]
setenv CTM_HGBIDI N          #> mercury bi-directional flux for in-line deposition
                             #>    velocities [ default: N ]
setenv CTM_SFC_HONO Y        #> surface HONO interaction [ default: Y ]
setenv CTM_GRAV_SETL Y       #> vdiff aerosol gravitational sedimentation [ default: Y ]
#setenv CTM_ILDEPV Y          #> calculate in-line deposition velocities [ default: Y ]  # not in v532
setenv CTM_BIOGEMIS N        #> calculate in-line biogenic emissions [ default: N ]
setenv OPTICS_MIE_CALC N     #> Get flag to use fast optics for volume mixing model for aerosol optical properties
setenv CORE_SHELL_OPTICS N   #> Get flag to use core-shell mixing model for aerosol optical properties

#> Vertical Extraction Options
setenv VERTEXT N
setenv VERTEXT_COORD_PATH na

#> I/O Controls
setenv IOAPI_LOG_WRITE F     #> turn on excess WRITE3 logging [ options: T | F ]
setenv FL_ERR_STOP N         #> stop on inconsistent input files
setenv PROMPTFLAG F          #> turn on I/O-API PROMPT*FILE interactive mode [ options: T | F ]
setenv IOAPI_OFFSET_64 YES   #> support large timestep records (>2GB/timestep record) [ options: YES | NO ]
setenv IOAPI_CHECK_HEADERS N #> check file headers [ options: Y | N ]
setenv CTM_EMISCHK N         #> Abort CMAQ if missing surrogates from emissions Input files
setenv EMISDIAG_SUM F        #> Print Sum of Emission Rates to Gridded Diagnostic File
setenv EMISDIAG F            #> Print Emission Rates at the output time step after they have been
                             #>   scaled and modified by the user Rules [options: F | T or 2D | 3D | 2DSUM ]
                             #>   Individual streams can be modified using the variables:
                             #>       GR_EMIS_DIAG_## | STK_EMIS_DIAG_## | BIOG_EMIS_DIAG
                             #>       MG_EMIS_DIAG    | LTNG_EMIS_DIAG   | DUST_EMIS_DIAG
                             #>       SEASPRAY_EMIS_DIAG
                             #>   Note that these diagnostics are different than other emissions diagnostic
                             #>   output because they occur after scaling.

# not in v532
#setenv EMIS_DATE_OVRD N     #> Master switch for allowing CMAQ to use the date from each Emission file
                             #>   rather than checking the emissions date against the internal model date.
                             #>   [options: T | F or Y | N]. If false (F/N), then the date from CMAQ's internal
                             #>   time will be used and an error check will be performed (recommended). Users
                             #>   may switch the behavior for individual emission files below using the variables:
                             #>       GR_EM_DTOVRD_## | STK_EM_DTOVRD_##
#setenv EMIS_SYM_DATE N       #> Master switch for allowing CMAQ to use the date from each Emission file
                             #>   rather than checking the emissions date against the internal model date.
                             #>   [options: T | F or Y | N]. If false (F/N), then the date from CMAQ's internal
                             #>   time will be used and an error check will be performed (recommended). Users
                             #>   may switch the behavior for individual emission files below using the variables:
                             #>       GR_EM_SYM_DATE_## | STK_EM_SYM_DATE_## [default : N ]

#setenv CTM_PT3DEMIS Y        #> calculate in-line plume rise for elevated point emissions  # not in v532

#> Diagnostic Output Flags
setenv CTM_CKSUM Y           #> checksum report [ default: Y ]
setenv CLD_DIAG N            #> cloud diagnostic file [ default: N ]

setenv CTM_PHOTDIAG N        #> photolysis diagnostic file [ default: N ]
setenv NLAYS_PHOTDIAG "1"    #> Number of layers for PHOTDIAG2 and PHOTDIAG3 from
                             #>     Layer 1 to NLAYS_PHOTDIAG  [ default: all layers ]
#setenv NWAVE_PHOTDIAG "294 303 310 316 333 381 607"  #> Wavelengths written for variables
                                                      #>   in PHOTDIAG2 and PHOTDIAG3
                                                      #>   [ default: all wavelengths ]

setenv CTM_PMDIAG N          #> Instantaneous Aerosol Diagnostic File [ default: Y ]
setenv CTM_APMDIAG Y         #> Hourly-Average Aerosol Diagnostic File [ default: Y ]
setenv APMDIAG_BLEV_ELEV "1 14"
#setenv APMDIAG_BLEV_ELEV "1 1"  #> layer range for average pmdiag = NLAYS

setenv CTM_SSEMDIAG N        #> sea-spray emissions diagnostic file [ default: N ]
setenv CTM_DUSTEM_DIAG N     #> windblown dust emissions diagnostic file [ default: N ];
                             #>     Ignore if CTM_WB_DUST = N
setenv CTM_DEPV_FILE N       #> deposition velocities diagnostic file [ default: N ]
setenv VDIFF_DIAG_FILE N     #> vdiff & possibly aero grav. sedimentation diagnostic file [ default: N ]
setenv LTNGDIAG N            #> lightning diagnostic file [ default: N ]
setenv B3GTS_DIAG N          #> BEIS mass emissions diagnostic file [ default: N ]
setenv PT3DDIAG N            #> 3D point source emissions diagnostic file [ default: N];
setenv PT3DFRAC N            #> layer fractions diagnostic file(s) [ default: N];
setenv REP_LAYER_MIN -1      #> Minimum layer for reporting plume rise info [ default: -1 ]

#> MPI Optimization Flags
setenv MPI_SM_POOL 16000     #> increase shared memory pool in case many MPI_SEND headers
setenv MP_EAGER_LIMIT 65536  #> set MPI message passing buffer size to max
setenv MP_SINGLE_THREAD yes  #> optimize for single threaded applications [ default: no ]
setenv MP_STDOUTMODE ordered #> order output by the processor ID
setenv MP_LABELIO yes        #> label output by processor ID [ default: no ]
setenv MP_SHARED_MEMORY yes  #> force use of shared memory for tasks on same node [ default: no ]
setenv MP_ADAPTER_USE shared #> share the MP adapter with other jobs
setenv MP_CPU_USE multiple   #> share the node with multiple users/jobs
setenv MP_CSS_INTERRUPT yes  #> specify whether arriving packets generate interrupts [ default: no ]


# =====================================================================
#> Input Directories and Filenames
# =====================================================================
set icbc_root = /bigdata/CMAQ_input/devin/PRD
set ICpath    = ${icbc_root}/icon/D3_${C11_CASE}   #> C10: IC/BC belong to the C11 world (matches C11), not CASE_NAME
set BCpath    = ${icbc_root}/bcon/D3_${C11_CASE}

# set ICpath    = ${INPDIR}/icon/D3
# set BCpath    = ${INPDIR}/bcon/D3
set EMISpath  = na   # set later          #> surface emissions input directory
set IN_PTpath = na   # set later          #> elevated emissions input directory (in-line point only)
set IN_LTpath = na                        #> lightning NOx input directory
set METpath   = na   # set later          #> meteorology input directory
#set JVALpath  = $INPDIR/jproc            #> offline photolysis rate table directory
set OMIpath   = na # set later            #> ozone column data for the photolysis model
set LUpath    = na # set later            #> BELD landuse data for windblown dust model
set SZpath    = na # set later            #> surf zone file for in-line seaspray emissions

setenv OPTICS_DATA $BLD/PHOT_OPTICS.dat

# =====================================================================
#> Begin Loop Through Simulation Days
# =====================================================================
set rtarray = ""

#> IC-only: run only the 5 target episode days
set target_dates = ("2022-09-06" "2022-09-13" "2022-09-14" "2022-09-16" "2022-09-19")
set NDAYS = 0

foreach TODAYG ($target_dates)  #>C10 target days

  set NDAYS = `echo "${NDAYS} + 1" | bc -l`
  set TODAYJ = `date -ud "${TODAYG}" +%Y%j` #> Convert YYYY-MM-DD to YYYYJJJ

  #> Retrieve Calendar day Information
  set YYYYMMDD = `date -ud "${TODAYG}" +%Y%m%d` #> Convert YYYY-MM-DD to YYYYMMDD
  set YYYYMM = `date -ud "${TODAYG}" +%Y%m`     #> Convert YYYY-MM-DD to YYYYMM
  set YYYY = `date -ud "${TODAYG}" +%Y`         #> Convert YYYY-MM-DD to YYYY
  set YYMMDD = `date -ud "${TODAYG}" +%y%m%d`   #> Convert YYYY-MM-DD to YYMMDD
  set YYYYJJJ = $TODAYJ

  set mmdd = `echo $YYYYMMDD |cut -b5-`
  set mon  = `echo $YYYYMMDD |cut -b5-6`

  #> Calculate Yesterday's Date
  #set YESTERDAY = `date -ud "${TODAYG}-1days" +%Y%m%d` #> Convert YYYY-MM-DD to YYYYJJJ
  set YESTERDAY = `date -ud "${TODAYG}-1days" +%Y%j` #> Convert YYYY-MM-DD to YYYYJJJ

# =====================================================================
#> Set Output String and Propagate Model Configuration Documentation
# =====================================================================
  echo ""
  echo "Set up input and output files for Day ${TODAYG}."

  #> set output file name extensions
  setenv CTM_APPL ${RUNID}_${TODAYJ}

  #> Copy Model Configuration To Output Folder
  if ( ! -d "$OUTDIR" ) mkdir -p $OUTDIR
  cp $BLD/CCTM_${VRSN}.cfg $OUTDIR/CCTM_${CTM_APPL}.cfg

# =====================================================================
#> Input Files (Some are Day-Dependent)
# =====================================================================

  #> Initial conditions — IC-only (C10): always borrow C11 propagated CGRID (yesterday), never own output
  setenv NEW_START FALSE
  set ICpath = /home/devin/cmaq_output/${C11_CASE}/D3/2022/${month}
  setenv ICFILE     CCTM_CGRID_${RUNID}_${YESTERDAY}.nc
  setenv INIT_MEDC_1 $ICpath/CCTM_MEDIA_CONC_${RUNID}_${YESTERDAY}.nc
  setenv INITIAL_RUN N
  echo "C10 borrowing C11 IC: $ICpath/$ICFILE"

  setenv OMI $BLD/OMI_1979_to_2019.dat

  #> Boundary conditions
  set BCFILE = BCON_${TODAYJ}

  #> Off-line photolysis rates
  #set JVALfile  = JTABLE_${YYYYJJJ}

  #> MCIP meteorology files

# /asm1/ROMO/met/MCIP/WRF_RAMBOLL_12US2_2018_35aL/v5.1.3
  set METpath = ${INPDIR}/mcip/D3
  setenv GRID_BDY_2D $METpath/GRIDBDY2D_${TODAYJ}
  setenv GRID_CRO_2D $METpath/GRIDCRO2D_${TODAYJ}
  setenv GRID_DOT_2D $METpath/GRIDDOT2D_${TODAYJ}
  setenv MET_BDY_3D  $METpath/METBDY3D_${TODAYJ}
  setenv MET_CRO_2D  $METpath/METCRO2D_${TODAYJ}
  setenv MET_CRO_3D  $METpath/METCRO3D_${TODAYJ}
  setenv MET_DOT_3D  $METpath/METDOT3D_${TODAYJ}
  setenv LUFRAC_CRO  ' '
  setenv GRID_CRO_3D ' '                     # not avail

    echo "current metcro3d for $YYYYMMDD"
    ls -lpF $MET_CRO_3D

  if ( ! -e $MET_CRO_2D ) then
    echo "mcip not avail for $YYYYMMDD - exit"
    exit
  endif

  setenv EMISSCTRL_NML /DeepLearning/mnt/Devin/devin/cmaq_scripts/cctm_scripts_v5.3.2/EmissCtrl_nml/EmissCtrl_${MECH}_base.nml  #> C10: baseline EM, no zeroing

  #setenv EMISSCTRL_NML ${CMAQ_HOME}/devin_region2zero_scripts/ctrl_D1_nml/base.nml
   #region2zero_${region}.nml

# in run_cctm_Bench_2016_12SE1.csh CMAQ_MASKS and OCEAN_1 are the same file.

  #> Spatial Masks For Emissions Scaling
  setenv CMAQ_MASKS ${INPDIR}/ocean/D3/D3_cmaq_masks
  echo "Using CMAQ_MASKS: $CMAQ_MASKS"

  #setenv CMAQ_MASKS ${INPDIR}/ocean/D3/regionfile_D3
  #> In-line sea spray emissions configuration
  setenv OCEAN_1 ${INPDIR}/ocean/D3/oceanfile

  #> Determine Representative Emission Days
     #> In-line emissions configuration
     #   set refdir = ${CMAQ_HOME}/smk_dates
     #   set reffile = $refdir/smk_merge_dates_$YYYYMM.txt

     #  set intable = `grep "^$YYYYMMDD" $reffile`

     #   set Date     = `echo $intable[1] | cut -d, -f1`
     #   set aveday_N = `echo $intable[2] | cut -d, -f1`
     #   set aveday_Y = `echo $intable[3] | cut -d, -f1`
     #   set mwdss_N  = `echo $intable[4] | cut -d, -f1`
     #   set mwdss_Y  = `echo $intable[5] | cut -d, -f1`
     #   set week_N   = `echo $intable[6] | cut -d, -f1`
     #   set week_Y   = `echo $intable[7] | cut -d, -f1`
     #   set all      = `echo $intable[8] | cut -d, -f1`
     #   echo $Date $aveday_N $aveday_Y $mwdss_N $mwdss_Y
     #   echo $week_N $week_Y $all

# from Chris Allen:

# The CMAQ-ready emissions for the 2018gg case, 36US3 domain, are available:
# /work/ROMO/pm_naaqs_2023/smoke_out/2018gg_18j/36US3/cmaq_cb6ae7/

# 2-D merged emissions with biogenics/RWC excluded are in the merged_nobeis_norwc/ directory.
# 2-D RWC emissions as a separate input are in the rwc/ directory.
# Inline point emissions exist for 10 sectors: cmv_c1c2_36, cmv_c3_36, othpt, pt_oilgas, ptagfire, ptegu, ptfire-rx, ptfir
# e-wild, ptfire_othna, ptnonipm. As usual, all are daily sectors except for othpt (mwdss_N, pt_oilgas (mwdss_Y), and ptno
# nipm (mwdss_Y).
# The inputs needed to run inline biogenics are in the beis_inline/ directory.
# The emissions do not include complete fertilizer, as we understand CMAQ will be run with bidirectional NH3.


# CMAQ-ready emissions are now also ready for the 12US2 domain:
# /work/ROMO/pm_naaqs_2023/smoke_out/2018gg_18j/12US2/cmaq_cb6ae7/

# The sector configuration is the same as 36US3, except the CMV sectors are named cmv_c1c2_12 and cmv_c3_12.

set epath  = ${INPDIR}/emis/D3
set epath2 = na  # $base0/emis
#set ecase = _2018gg_18j.ncf

setenv N_EMIS_GR 2  # below 2 sectors without ocean cl2 because it is already in file

# make sure if beis is in the sector list that CTM_BIOGEMIS = N

# the below '.' separated fields correspond to values for:
# sector number, sector name, repday, repday logical T/F, GRIDDED_sectorlabel

# check grid labels

#foreach sem (                             \
#1.merged_nobeis_norwc.$all.F.GRIDDED_EMIS \
#2.rwc.$all.F.GR_RES_FIRES                 )

#set nsem = `echo $sem |cut -d. -f1`  # sector number
#set tsem = `echo $sem |cut -d. -f2`  # sector name
#set dsem = `echo $sem |cut -d. -f3`  # repday
#set rsem = `echo $sem |cut -d. -f4`  # repday logical T/F GR_EM_DTOVRD_# or GR_EM_SYM_DATE_#
#set csem = `echo $sem |cut -d. -f5`  # GRIDDED_sectorlabel

#set zsem = $nsem
#if ( $nsem < 100 ) set zsem = 0$nsem
#if ( $nsem < 10  ) set zsem = 00$nsem

#if ( $tsem == merged_nobeis_norwc ) then
#setenv GR_EMIS_$zsem $epath/$tsem/emis_mole_all_${dsem}_12US2_nobeis_norwc$ecase

#else if ( $tsem == rwc ) then
#setenv GR_EMIS_$zsem $epath/$tsem/emis_mole_${tsem}_${dsem}_12US2_cmaq_cb6ae7$ecase
setenv m 9

set MONTHs =  (1 2 3 4 5 6 7 8 9 10 11 12)
set SDATEs =  ("2022-12-31" "2022-01-31" "2022-02-28" "2022-03-31" "2022-04-30" "2022-05-31" "2022-06-30" "2022-07-31" "2022-08-31" "2022-09-30" "2022-10-31" "2022-11-30")
set EDATEs =  ("2022-01-31" "2022-02-28" "2022-03-31" "2022-04-30" "2022-05-31" "2022-06-30" "2022-07-31" "2022-08-31" "2022-09-30" "2022-10-31" "2022-11-30" "2022-12-31")
set EM_Oth =  (2022007 2022035 2022063 2022091 2022126 2022154 2022182 2022217 2022245 2022280 2022308 2022336)
set EM_Sat =  (2022008 2022036 2022064 2022092 2022127 2022155 2022183 2022218 2022246 2022281 2022309 2022337)
set EM_Sun =  (2022009 2022037 2022065 2022093 2022128 2022156 2022184 2022219 2022247 2022282 2022310 2022338)
set CLDAY  =  4


@ weekday = ( 4 + ${TODAYJ} - 2022000 ) % 7 + 1
   if ( $weekday == 6 ) then
    setenv EMIS_DATE $EM_Sat[$m]
   else if ( $weekday == 7 ) then
    setenv EMIS_DATE $EM_Sun[$m]
   else
    setenv EMIS_DATE $EM_Oth[$m]
   endif
# normal default
#else
#setenv GR_EMIS_$zsem $epath/emis_mole_${tsem}_$dsem$ecase
#setenv GR_EMIS_001 $epath/only_NOx_emission_of_Guangdong_AV/EM_AV_${EMIS_DATE}
#setenv GR_EMIS_001 $epath/EM_AV_${EMIS_DATE}
setenv GR_EMIS_001 ${INPDIR}/emis/D3/comb_ArearateAB_cn03_${EMIS_DATE}
setenv GR_EMIS_002 $epath/MEGAN/MEGANv32.PRD_3km.${TODAYJ}.BDSNP.ncf #$epath/MEGAN/MEGANv32.PRD_27km.${TODAYJ}.BDSNP.ncf MEGANv32.PRD_9km.2021361.BDSNP.ncf
#endif

setenv GR_EMIS_LAB_001 GRIDDED_AV
setenv GR_EMIS_LAB_002 GRIDDED_BV

#setenv GR_EM_DTOVRD_$zsem   $rsem   # earlier versions
setenv GR_EM_SYM_DATE_001 T
setenv GR_EM_SYM_DATE_002 T

# no repdays used for merged_nobeis_norwc or rwc
# # 2015mmdd spinups are linked to 2016mmdd files.  repday logical is T here
# if ( $YYYY == 2015 ) then
# if ( $tsem == afdust_adj     || \
#      $tsem == ag             || \
#      $tsem == canada_ag      || \
#      $tsem == onroad         || \
#      $tsem == othafdust_adj  || \
#      $tsem == othptdust_adj  || \
#      $tsem == rwc            )  then
#      setenv GR_EM_DTOVRD_$zsem   T
#      setenv GR_EM_SYM_DATE_$zsem T
# endif # type
# endif # 2015

#end # gridded emissions list

# # ocean cl2: this appears to be in the emis file already for 2016, 2032, 2018 12US2
# set zsem = 20  # 19 sectors plus 1

# inline point emissions

# using another grid for inline pt does not matter as long as the grid
# is the same map projection and completely covers the model data
# needed for the model grid.  this is because inline pt is input by
# xloc and yloc and not by cmaq col and row.  cmaq calculates col and
# row from xloc and yloc.

# /work/ROMO/pm_naaqs_2023/smoke_out/2018gg_18j/12US2/cmaq_cb6ae7

set ptpath1 = $epath
set ptpath2 = na

set pcase = _12US1_cmaq_cb6ae7_2018gg_18j.ncf
set scase = _12US1_2018gg_18j.ncf

# sector list

# check point labels

setenv N_EMIS_PT 0

#foreach sect (                    \
#1.ptnonipm.$mwdss_Y.T.PT_NONEGU   \
#2.pt_oilgas.$mwdss_Y.T.PT_OILGAS  \
#3.ptegu.$all.T.PT_EGU       \
#4.ptfire-rx.$all.T.PT_RXFIRES     \
#5.ptfire-wild.$all.T.PT_FIRES     \
#6.ptfire_othna.$all.T.PT_OTHFIRES \
#7.ptagfire.$all.T.PT_AGFIRES      \
#8.othpt.$mwdss_N.T.PT_OTHER       \
#9.cmv_c1c2_12.$all.T.PT_CMV_C1C2  \
#10.cmv_c3_12.$all.T.PT_CMV_C3     )

#set nsect = `echo $sect |cut -d. -f1`  # sector number
#set tsect = `echo $sect |cut -d. -f2`  # sector name
#set dsect = `echo $sect |cut -d. -f3`  # repday
#set rsect = `echo $sect |cut -d. -f4`  # repday logical T/F STK_EM_DTOVRD_# or STK_EM_SYM_DATE_#
#set csect = `echo $sect |cut -d. -f5`  # GRIDDED_sectorlabel

#set zsect = $nsect
#if ( $nsect < 100 ) set zsect = 0$nsect
#if ( $nsect < 10  ) set zsect = 00$nsect

# daily stack_groups 12us1
#if ( $tsect == ptfire_othna || $tsect == ptagfire || $tsect == ptfire-rx || $tsect == ptfire-wild ) then
#setenv STK_EMIS_$zsect $ptpath1/$tsect/inln_mole_${tsect}_$dsect$pcase
#setenv STK_GRPS_$zsect $ptpath1/$tsect/stack_groups_${tsect}_$dsect$scase

# normal defaults
#else
#setenv STK_EMIS_$zsect $ptpath1/$tsect/inln_mole_${tsect}_$dsect$pcase
#setenv STK_GRPS_$zsect $ptpath1/$tsect/stack_groups_$tsect$scase

#endif

# Label Each Emissions Stream
#setenv STK_EMIS_LAB_$zsect $csect

# Allow CMAQ to Use Point Source files with dates that do not
# match the internal model date
#setenv STK_EM_DTOVRD_$zsect   $rsect
#setenv STK_EM_SYM_DATE_$zsect $rsect

#end # point sector list

  setenv LAYP_STTIME $STTIME
  setenv LAYP_NSTEPS $NSTEPS
  setenv LAYP_STDATE $YYYYJJJ

  #setenv STK_EMIS_DIAG_001 2DSUM
  #setenv STK_EMIS_DIAG_002 2DSUM
  #setenv STK_EMIS_DIAG_003 2DSUM
  #setenv STK_EMIS_DIAG_004 2DSUM
  #setenv STK_EMIS_DIAG_005 2DSUM

  #> Lightning NOx configuration
  if ( $CTM_LTNG_NO == 'Y' ) then
     setenv LTNGNO "InLine"    #> set LTNGNO to "Inline" to activate in-line calculation

  #> In-line lightning NOx options
     setenv USE_NLDN  na        #> use hourly NLDN strike file [ default: Y ]
     if ( $USE_NLDN == Y ) then
        setenv NLDN_STRIKES na
     endif
     setenv LTNGPARMS_FILE na #> lightning parameter file; ignore if LTNGPARAM = N
  endif

# beis
# /work/ROMO/pm_naaqs_2023/smoke_out/2018gg_18j/12US2/cmaq_cb6ae7/beis_inline
# -rw-rw-r--. 1 callen05 romo      30034768 2022-06-16 08:46 b3grd.2016v3.2022Apr21.12US2.ncf
# -rw-rw-r--. 1 callen05 romo     146527860 2022-06-16 08:47 bioseason.cmaq.18j_12US2.ncf_full
# -rw-rw-r--. 1 callen05 emis-hpc     23102 2021-04-21 14:30 gspro_biogenics_28apr2020_v10.txt


  # #> In-line biogenic emissions configuration
  # if ( $CTM_BIOGEMIS == 'Y' ) then
  #    set IN_BEISpath = $base0/emis
  #    setenv GSPRO      $IN_BEISpath/gspro_biogenics_19nov2019_nf_v10.txt
  #    setenv B3GRD      $IN_BEISpath/b3grd_4NW2_WR403_2016fh_16j.ncf
  #    setenv BIOG_SPRO  BC6E7
  #    setenv BIOSW_YN   Y     #> use frost date switch [ default: Y ]
  #    setenv BIOSEASON  $IN_BEISpath/bioseason.cmaq.16j_4NW2.ncf_full
  #    setenv SUMMER_YN  Y     #> Use summer normalized emissions? [ default: Y ]
  #    setenv PX_VERSION Y     #> MCIP is PX version? [ default: N ]
  #    setenv SOILINP    $OUTDIR/CCTM_SOILOUT_${RUNID}_${YESTERDAY}.nc
  #                            #> Biogenic NO soil input file; ignore if INITIAL_RUN = Y
  # endif  # inline biogenics

  #> In-line biogenic emissions configuration
  if ( $CTM_BIOGEMIS == 'Y' ) then
     set IN_BEISpath = $epath/beis_inline
     setenv GSPRO      $IN_BEISpath/gspro_biogenics_28apr2020_v10.txt
     setenv B3GRD      $IN_BEISpath/b3grd.2016v3.2022Apr21.12US2.ncf
     setenv BIOG_SPRO  BC6E7
     setenv BIOSW_YN   Y   #> use frost date switch [ default: Y ]
     setenv BIOSEASON  $IN_BEISpath/bioseason.cmaq.18j_12US2.ncf_full
     setenv SUMMER_YN  Y   #> Use summer normalized emissions? [ default: Y ]
     setenv PX_VERSION Y   #> MCIP is PX version? [ default: N ]
     setenv SOILINP    $OUTDIR/CCTM_SOILOUT_${RUNID}_${YESTERDAY}.nc
                             #> Biogenic NO soil input file; ignore if INITIAL_RUN = Y
  endif  # inline biogenics

# dust files:

  #> Windblown dust emissions configuration
  if ( $CTM_WB_DUST == 'Y' ) then
     # Input variables for BELD3 Landuse option
     setenv DUST_LU_1  na
     setenv DUST_LU_2  na
     setenv MODIS_FPAR na  # MODIS_FPAR not in v532

# # this part may not be used anymore for v5.3 because CTM_ERODE_AGLAND is false in code
#      if ( $CTM_ERODE_AGLAND == 'Y' ) then
#         setenv CROPMAP01 $base0/calmap/EndPlanting_4NW2
#         setenv CROPMAP04 $base0/calmap/EndPlanting_4NW2
#         setenv CROPMAP08 $base0/calmap/EndHarvesting_4NW2
#      endif
  endif  # if CTM_WB_DUST

# originally from /work/MOD3DATA/2018_12US1/epic
# epic was originally 12US1 and was windowed to 12US2 by utility m3wndw

  #> Bidirectional ammonia configuration
  if ( $CTM_ABFLUX == 'Y' ) then
     set epicdir  = ${INPDIR}/EPIC
     setenv E2C_SOIL $epicdir/${YYYY}r1_EPIC0509_12US1to12US2_soil.nc
     setenv E2C_CHEM $epicdir/${YYYY}r1_EPIC0509_12US1to12US2_time$YYYYMMDD.nc
     # if ( $YESTERDAY == 20151221 ) then
     #    setenv E2C_CHEM_YEST $epicdir2/us2_2016_cmaq12km_time$YESTERDAY.nc  # copy of 20151222
     # else
     #    setenv E2C_CHEM_YEST  $epicdir/us2_2016_cmaq12km_time$YESTERDAY.nc
     # endif
     setenv E2C_LU $epicdir/beld4_12US1to12US2_2011.nc
  endif

#> Inline Process Analysis
  setenv CTM_PROCAN N        #> use process analysis [ default: N]
  if ( $?CTM_PROCAN ) then   # $CTM_PROCAN is defined
     if ( $CTM_PROCAN == 'Y' || $CTM_PROCAN == 'T' ) then
#> process analysis global column, row and layer ranges
#       setenv PA_BCOL_ECOL "10 90"  # default: all columns
#       setenv PA_BROW_EROW "10 80"  # default: all rows
#       setenv PA_BLEV_ELEV "1  4"   # default: all levels
        setenv PACM_INFILE ${NMLpath}/pa_${MECH}.ctl
        setenv PACM_REPORT $OUTDIR/"PA_REPORT".${YYYYMMDD}
     endif
  endif

#> Integrated Source Apportionment Method (ISAM) Options
 setenv CTM_ISAM N

#> Sulfur Tracking Model (STM)
 setenv STM_SO4TRACK N        #> sulfur tracking [ default: N ]
 if ( $?STM_SO4TRACK ) then
    if ( $STM_SO4TRACK == 'Y' || $STM_SO4TRACK == 'T' ) then

      #> option to normalize sulfate tracers [ default: Y ]
      setenv STM_ADJSO4 Y

    endif
 endif

# marine file if needed
setenv CTM_MGEM_1      "$OUTDIR/CCTM_MGEM_${CTM_APPL}.nc -v"       #> Marine Gas Emissions

#> CMAQ-DDM-3D
 setenv CTM_DDM3D N
 set NPMAX    = 1
 setenv SEN_INPUT ${WORKDIR}/sensinput.dat

 setenv DDM3D_HIGH N     # allow higher-order sensitivity parameters [ T | Y | F | N ] (default is N/F)

 if ($NEW_START == true || $NEW_START == TRUE ) then
    setenv DDM3D_RST N   # begins from sensitivities from a restart file [ T | Y | F | N ] (default is Y/T)
    set S_ICpath =
    set S_ICfile =
 else
    setenv DDM3D_RST Y
    set S_ICpath = $OUTDIR
    set S_ICfile = CCTM_SENGRID_${RUNID}_${YESTERDAY}.nc
 endif

 setenv DDM3D_BCS F      # use sensitivity bc file for nested runs [ T | Y | F | N ] (default is N/F)
 set S_BCpath =
 set S_BCfile =

 setenv CTM_NPMAX       $NPMAX
 setenv CTM_SENS_1      "$OUTDIR/CCTM_SENGRID_${CTM_APPL}.nc -v"
 setenv A_SENS_1        "$OUTDIR/CCTM_ASENS_${CTM_APPL}.nc -v"
 setenv CTM_SWETDEP_1   "$OUTDIR/CCTM_SENWDEP_${CTM_APPL}.nc -v"
 setenv CTM_SDRYDEP_1   "$OUTDIR/CCTM_SENDDEP_${CTM_APPL}.nc -v"
 setenv CTM_NPMAX       $NPMAX
 setenv INIT_SENS_1     $S_ICpath/$S_ICfile
 setenv BNDY_SENS_1     $S_BCpath/$S_BCfile

# =====================================================================
#> Output Files
# =====================================================================

  #> set output file names
  setenv S_CGRID         "$OUTDIR/CCTM_CGRID_${CTM_APPL}.nc"         #> 3D Inst. Concentrations
  setenv CTM_CONC_1      "$OUTDIR/CCTM_CONC_${CTM_APPL}.nc -v"       #> On-Hour Concentrations
  setenv A_CONC_1        "$OUTDIR/CCTM_ACONC_${CTM_APPL}.nc -v"      #> Hourly Avg. Concentrations
  setenv MEDIA_CONC      "$OUTDIR/CCTM_MEDIA_CONC_${CTM_APPL}.nc -v" #> NH3 Conc. in Media
  setenv CTM_DRY_DEP_1   "$OUTDIR/CCTM_DRYDEP_${CTM_APPL}.nc -v"     #> Hourly Dry Deposition
  setenv CTM_DEPV_DIAG   "$OUTDIR/CCTM_DEPV_${CTM_APPL}.nc -v"       #> Dry Deposition Velocities
  setenv CTM_PT3D_DIAG   "$OUTDIR/CCTM_PT3D_${CTM_APPL}.nc -v"       #> Point Source Emissions by Layer
  setenv B3GTS_S         "$OUTDIR/CCTM_B3GTS_S_${CTM_APPL}.nc -v"    #> Biogenic Emissions
  setenv SOILOUT         "$OUTDIR/CCTM_SOILOUT_${CTM_APPL}.nc"       #> Soil Emissions
  setenv CTM_WET_DEP_1   "$OUTDIR/CCTM_WETDEP1_${CTM_APPL}.nc -v"    #> Wet Dep From All Clouds
  setenv CTM_WET_DEP_2   "$OUTDIR/CCTM_WETDEP2_${CTM_APPL}.nc -v"    #> Wet Dep From SubGrid Clouds
  setenv CTM_PMDIAG_1    "$OUTDIR/CCTM_PMDIAG_${CTM_APPL}.nc -v"     #> On-Hour Particle Diagnostics
  setenv CTM_APMDIAG_1   "$OUTDIR/CCTM_APMDIAG_${CTM_APPL}.nc -v"    #> Hourly Avg. Particle Diagnostics
  setenv CTM_RJ_1        "$OUTDIR/CCTM_PHOTDIAG1_${CTM_APPL}.nc -v"  #> 2D Surface Summary from Inline Photolysis
  setenv CTM_RJ_2        "$OUTDIR/CCTM_PHOTDIAG2_${CTM_APPL}.nc -v"  #> 3D Photolysis Rates
  setenv CTM_RJ_3        "$OUTDIR/CCTM_PHOTDIAG3_${CTM_APPL}.nc -v"  #> 3D Optical and Radiative Results from Photolysis
  setenv CTM_SSEMIS_1    "$OUTDIR/CCTM_SSEMIS_${CTM_APPL}.nc -v"     #> Sea Spray Emissions
  setenv CTM_DUST_EMIS_1 "$OUTDIR/CCTM_DUSTEMIS_${CTM_APPL}.nc -v"   #> Dust Emissions
  setenv CTM_IPR_1       "$OUTDIR/CCTM_PA_1_${CTM_APPL}.nc -v"       #> Process Analysis
  setenv CTM_IPR_2       "$OUTDIR/CCTM_PA_2_${CTM_APPL}.nc -v"       #> Process Analysis
  setenv CTM_IPR_3       "$OUTDIR/CCTM_PA_3_${CTM_APPL}.nc -v"       #> Process Analysis
  setenv CTM_IRR_1       "$OUTDIR/CCTM_IRR_1_${CTM_APPL}.nc -v"      #> Chem Process Analysis
  setenv CTM_IRR_2       "$OUTDIR/CCTM_IRR_2_${CTM_APPL}.nc -v"      #> Chem Process Analysis
  setenv CTM_IRR_3       "$OUTDIR/CCTM_IRR_3_${CTM_APPL}.nc -v"      #> Chem Process Analysis
  setenv CTM_DRY_DEP_MOS "$OUTDIR/CCTM_DDMOS_${CTM_APPL}.nc -v"      #> Dry Dep
  setenv CTM_DRY_DEP_FST "$OUTDIR/CCTM_DDFST_${CTM_APPL}.nc -v"      #> Dry Dep
  setenv CTM_DEPV_MOS    "$OUTDIR/CCTM_DEPVMOS_${CTM_APPL}.nc -v"    #> Dry Dep Velocity
  setenv CTM_DEPV_FST    "$OUTDIR/CCTM_DEPVFST_${CTM_APPL}.nc -v"    #> Dry Dep Velocity
  setenv CTM_VDIFF_DIAG  "$OUTDIR/CCTM_VDIFF_DIAG_${CTM_APPL}.nc -v" #> Vertical Dispersion Diagnostic
  setenv CTM_VSED_DIAG   "$OUTDIR/CCTM_VSED_DIAG_${CTM_APPL}.nc -v"  #> Particle Grav. Settling Velocity
  setenv CTM_LTNGDIAG_1  "$OUTDIR/CCTM_LTNGHRLY_${CTM_APPL}.nc -v"   #> Hourly Avg Lightning NO
  setenv CTM_LTNGDIAG_2  "$OUTDIR/CCTM_LTNGCOL_${CTM_APPL}.nc -v"    #> Column Total Lightning NO
  setenv CTM_VEXT_1      "$OUTDIR/CCTM_VEXT_${CTM_APPL}.nc -v"       #> On-Hour 3D Concs at select sites


  #> set floor file (neg concs)
  setenv FLOOR_FILE ${OUTDIR}/FLOOR_${CTM_APPL}.txt

  #> look for existing log files and output files
  ( ls CTM_LOG_???.${CTM_APPL} > buff.txt ) >& /dev/null
  ( ls ${LOGDIR}/CTM_LOG_???.${CTM_APPL} >> buff.txt ) >& /dev/null
  set log_test = `cat buff.txt`; rm -f buff.txt

  set OUT_FILES = (${FLOOR_FILE} ${S_CGRID} ${CTM_CONC_1} ${A_CONC_1} ${MEDIA_CONC}         \
             ${CTM_DRY_DEP_1} $CTM_DEPV_DIAG $CTM_PT3D_DIAG $B3GTS_S $SOILOUT $CTM_WET_DEP_1\
             $CTM_WET_DEP_2 $CTM_PMDIAG_1 $CTM_APMDIAG_1             \
             $CTM_RJ_1 $CTM_RJ_2 $CTM_RJ_3 $CTM_SSEMIS_1 $CTM_DUST_EMIS_1 $CTM_IPR_1 $CTM_IPR_2       \
             $CTM_IPR_3 $CTM_IRR_1 $CTM_IRR_2 $CTM_IRR_3 $CTM_DRY_DEP_MOS                   \
             $CTM_DRY_DEP_FST $CTM_DEPV_MOS $CTM_DEPV_FST $CTM_VDIFF_DIAG $CTM_VSED_DIAG    \
             $CTM_LTNGDIAG_1 $CTM_LTNGDIAG_2 $CTM_VEXT_1 )
  set OUT_FILES = `echo $OUT_FILES | sed "s; -v;;g" `
  ( ls $OUT_FILES > buff.txt ) >& /dev/null
  set out_test = `cat buff.txt`; rm -f buff.txt

  #> delete previous output if requested
  if ( $CLOBBER_DATA == true || $CLOBBER_DATA == TRUE ) then
     echo
     echo "Existing Logs and Output Files for Day ${TODAYG} Will Be Deleted"

     #> remove previous log files
     foreach file ( ${log_test} )
        #echo "Deleting log file: $file"
#        /bin/rm -f $file
     end

     #> remove previous output files
     foreach file ( ${out_test} )
        #echo "Deleting output file: $file"
#        /bin/rm -f $file
     end
#     /bin/rm -f ${OUTDIR}/CCTM_EMDIAG*${RUNID}_${YYYYMMDD}.nc

  else
     #> error if previous log files exist
     if ( "$log_test" != "" ) then
       echo "*** Logs exist - run ABORTED ***"
       echo "*** To overide, set CLOBBER_DATA = TRUE in run_cctm.csh ***"
       echo "*** and these files will be automatically deleted. ***"
       exit 1
     endif

     #> error if previous output files exist
     if ( "$out_test" != "" ) then
       echo "*** Output Files Exist - run will be ABORTED ***"
       foreach file ( $out_test )
          echo " cannot delete $file"
       end
       echo "*** To overide, set CLOBBER_DATA = TRUE in run_cctm.csh ***"
       echo "*** and these files will be automatically deleted. ***"
       exit 1
     endif
  endif

  #> for the run control ...
  setenv CTM_STDATE      $YYYYJJJ
  setenv CTM_STTIME      $STTIME
  setenv CTM_RUNLEN      $NSTEPS
  setenv CTM_TSTEP       $TSTEP
  setenv INIT_CONC_1     $ICpath/$ICFILE
  setenv BNDY_CONC_1     $BCpath/$BCFILE

  # setenv OMI $OMIpath/$OMIfile          # set earlier
  # setenv OPTICS_DATA $OMIpath/$OPTfile  # set earlier
  #setenv XJ_DATA $JVALpath/$JVALfile  # na
  set TR_DVpath = $METpath
  set TR_DVfile = $MET_CRO_2D

  #> species defn & photolysis
  setenv gc_matrix_nml ${NMLpath}/GC_$MECH.nml
  setenv ae_matrix_nml ${NMLpath}/AE_$MECH.nml
  setenv nr_matrix_nml ${NMLpath}/NR_$MECH.nml
  setenv tr_matrix_nml ${NMLpath}/Species_Table_TR_0.nml

  #> check for photolysis input data
  setenv CSQY_DATA ${NMLpath}/CSQY_DATA_$MECH

  if (! (-e $CSQY_DATA ) ) then
     echo " $CSQY_DATA  not found "
     exit 1
  endif
  if (! (-e $OPTICS_DATA ) ) then
     echo " $OPTICS_DATA  not found "
     exit 1
  endif

  if ( ! -e $INIT_CONC_1 ) then
    echo 'no initial condition file, program aborting'
    exit
  endif

# ===================================================================
#> Execution Portion
# ===================================================================

  #> Print attributes of the executable
  if ( $CTM_DIAG_LVL != 0 ) then
     ls -l $BLD/$EXEC
     size $BLD/$EXEC
     unlimit
     limit
  endif

  #> Print Startup Dialogue Information to Standard Out
  echo
  echo "CMAQ Processing of Day $YYYYMMDD Began at `date`"
  echo

  #> Executable call for single PE, uncomment to invoke
  #( /usr/bin/time -p $BLD/$EXEC ) |& tee buff_${EXECUTION_ID}.txt

  #> Executable call for multi PE, configure for your system
  # set MPI = /usr/local/intel/impi/3.2.2.006/bin64
   set MPIRUN = mpiexec
  ##ls -lpF --time-style=long-iso $BLD/$EXEC
  ${MPIRUN} -np $NPROCS $BLD/$EXEC |& tee buff_${EXECUTION_ID}.txt # comment out for testing

  #> Harvest Timing Output so that it may be reported below
  set rtarray = "${rtarray} `tail -3 buff_${EXECUTION_ID}.txt | grep -Eo '[+-]?[0-9]+([.][0-9]+)?' | head -1` "
  rm -rf buff_${EXECUTION_ID}.txt

  #> Abort script if abnormal termination
  if ( ! -e $S_CGRID ) then
    echo ""
    echo "**************************************************************"
    echo "** Runscript Detected an Error: CGRID file was not written. **"
    echo "**   This indicates that CMAQ was interrupted or an issue   **"
    echo "**   exists with writing output. The runscript will now     **"
    echo "**   abort rather than proceeding to subsequent days.       **"
    echo "**************************************************************"
    break
  endif

  #> Print Concluding Text
  echo
  echo "CMAQ Processing of Day $YYYYMMDD Finished at `date`"
  echo
  echo "\\\\\=====\\\\\=====\\\\\=====\\\\\=====/////=====/////=====/////=====/////"
  echo

# ===================================================================
#> Finalize Run for This Day and Loop to Next Day
# ===================================================================

  #> Save Log Files and Move on to Next Simulation Day
  mv CTM_LOG_???.${CTM_APPL} $LOGDIR
  if ( $CTM_DIAG_LVL != 0 ) then
    mv CTM_DIAG_???.${CTM_APPL} $LOGDIR
  endif

end  #Loop to the next target day (IC-only)

# ===================================================================
#> Generate Timing Report
# ===================================================================
set RTMTOT = 0
foreach it ( `seq ${NDAYS}` )
    set rt = `echo ${rtarray} | cut -d' ' -f${it}`
    set RTMTOT = `echo "${RTMTOT} + ${rt}" | bc -l`
end

set RTMAVG = `echo "scale=2; ${RTMTOT} / ${NDAYS}" | bc -l`
set RTMTOT = `echo "scale=2; ${RTMTOT} / 1" | bc -l`

echo
echo "=================================="
echo "  ***** CMAQ TIMING REPORT *****"
echo "=================================="
echo "Start Day: ${START_DATE}"
echo "End Day:   ${END_DATE}"
echo "Number of Simulation Days: ${NDAYS}"
echo "Domain Name:               ${GRID_NAME}"
echo "Number of Grid Cells:      ${NCELLS}  (ROW x COL x LAY)"
echo "Number of Layers:          ${NZ}"
echo "Number of Processes:       ${NPROCS}"
echo "   All times are in seconds."
echo
echo "Num  Day        Wall Time"
set d = 0
set day = ${START_DATE}
foreach it ( `seq ${NDAYS}` )
    # Set the right day and format it
    set d = `echo "${d} + 1"  | bc -l`
    set n = `printf "%02d" ${d}`

    # Choose the correct time variables
    set rt = `echo ${rtarray} | cut -d' ' -f${it}`

    # Write out row of timing data
    echo "${n}   ${day}   ${rt}"

    # Increment day for next loop
    set day = `date -ud "${day}+1days" +%Y-%m-%d`
end
echo "     Total Time = ${RTMTOT}"
echo "      Avg. Time = ${RTMAVG}"

exit
