#!/bin/csh -f
source "$SCRIPT_DIR/cst00_config_common.csh"
setenv START_DATE "2022-09-06"
setenv FIRST_DATE "$START_DATE"
setenv CASE_NAME "prd2zero_cst00_ic_only"
setenv CASE_TYPE standard
setenv RESET_MODE ic_only
setenv PROPAGATED_ROOT "/home/devin/cmaq_output/shapley_cst00/prd2zero_cst00_propagated"
setenv NML_PATH "../../cctm_scripts_v5.3.2/EmissCtrl_nml/EmissCtrl_cb6r3_ae7_aq_base.nml"
setenv OUTDIR_BASE "/home/devin/cmaq_output/shapley_cst00/${CASE_NAME}"
