#!/bin/csh -f
source "$SCRIPT_DIR/cst00_config_common.csh"
setenv CASE_NAME "prd2zero_cst00_propagated"
setenv CASE_TYPE standard
setenv RESET_MODE propagate
setenv NML_PATH "../../cctm_scripts_v5.3.2/EmissCtrl_nml/EmissCtrl_cb6r3_ae7_aq_prd2zero.nml"
setenv OUTDIR_BASE "/home/devin/cmaq_output/shapley_cst00/${CASE_NAME}"
