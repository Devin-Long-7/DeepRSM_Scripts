#!/bin/csh -f
# Shared CST00 settings for the four Shapley cells.
# Cell configs override case-specific settings after sourcing this file.

setenv START_DATE "2022-09-01"
setenv END_DATE "2022-09-19"
setenv FIRST_DATE "$START_DATE"
setenv POST_BEGIN_DATE "2022-09-06"
setenv POST_END_DATE "$END_DATE"

setenv RESET_MODE "reset"
setenv PROPAGATED_ROOT ""
setenv CASE_TYPE "standard"
setenv GENERATE_NML N

setenv NPCOL 8
setenv NPROW 4
setenv MPI_BIN "/opt/intel/impi/2019.0.117/intel64/bin"
setenv I_MPI_FABRICS shm
setenv OMP_NUM_THREADS 1
setenv PYTHON_CMD "/program/software/devin_env/bin/python3"

setenv VRSN v532
setenv PROC mpi
setenv MECH cb6r3_ae7_aq
setenv APPL PRD
setenv DOMAIN D3
setenv GRID_NAME SD_2013
setenv NZ 14

setenv CCTM_WORKDIR "/program/rain/Build_CMAQ/CMAQ_Project/CCTM/scripts"
setenv BLD "${CCTM_WORKDIR}/BLD_CCTM_${VRSN}_intel"
setenv INPDIR "/bigdata/CMAQ_input/devin/PRD/2022"
# Set BASELINE_CGRID_ROOT in the environment when the mount path differs.
if ( ! $?BASELINE_CGRID_ROOT ) then
    setenv BASELINE_CGRID_ROOT "/mnt/167/devin/cmaq_output/CCTM_CGRID_base/202209_PRD_150X117_utc16"
endif
setenv BC_PATH "/bigdata/CMAQ_input/devin/PRD/bcon/${DOMAIN}_base"
setenv MET_PATH "${INPDIR}/mcip/${DOMAIN}"
setenv GRIDDESC "${MET_PATH}/GRIDDESC"

setenv CMAQ_MASKS "${INPDIR}/ocean/${DOMAIN}/${DOMAIN}_cmaq_masks"
setenv OCEAN_1_PATH "${INPDIR}/ocean/${DOMAIN}/oceanfile"
setenv N_EMIS_GR 2
setenv AV_EMIS_DIR "${INPDIR}/emis/${DOMAIN}"
setenv BV_EMIS_DIR "${INPDIR}/emis/${DOMAIN}/MEGAN"
setenv EM_AV_PREFIX "comb_ArearateAB_cn03_"
setenv MEGAN_PREFIX "MEGANv32.PRD_3km."
setenv MEGAN_SUFFIX ".BDSNP.ncf"
setenv EMIS_MONTH "2022-09"

setenv TEMPLATE_FILE "run_cctm_template.csh"
setenv CCTM_WORKDIR "${CCTM_WORKDIR}"
setenv POST_TEMPLATE_FILE "../../post_scripts_v5.3.2/0_run_post_script.csh"
setenv POST_SPEC_FILE "../../post_scripts_v5.3.2/spec_def_files/SpecDef_${MECH}_all_layers.txt"
setenv LAYER -1
setenv COMBINE_DIR ""
setenv KEEP_18SPECIES_ONLY T
setenv INCLUDE_WRF F
setenv KEEP_COMBINE_FILE F
setenv CONVERT2DAILY T
setenv CLEANUP_CCTM_OUTPUT T
setenv ENABLE_POST_PROCESS Y

setenv CONC_SPCS "ALL"
setenv AVG_CONC_SPCS "ALL"
setenv CONC_BLEV_ELEV "1 14"
setenv ACONC_BLEV_ELEV "1 14"
setenv APMDIAG_BLEV_ELEV "1 14"
setenv CTM_MAXSYNC 300
setenv CTM_MINSYNC 60
setenv SIGMA_SYNC_TOP 0.7
setenv CTM_ADV_CFL 0.95
