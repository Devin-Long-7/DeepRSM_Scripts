#!/bin/csh -f
source "$SCRIPT_DIR/cst00_config_common.csh"
setenv START_DATE "2022-09-06"
setenv FIRST_DATE "$START_DATE"
setenv CASE_NAME "everywhere2zero_icrb_cst00"
setenv CASE_TYPE standard
setenv RESET_MODE reset
setenv NML_PATH "../../cctm_scripts_v5.3.2/EmissCtrl_nml/EmissCtrl_cb6r3_ae7_aq_everywhere2zero.nml"
setenv OUTDIR_BASE "/home/devin/cmaq_output/shapley_cst00/${CASE_NAME}"
