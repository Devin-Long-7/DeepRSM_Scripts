# User-editable configuration for batch_run_pr_validation.csh.
# This file is sourced by the batch script, so paths may use $script_path.

# Beijing-time local dates.  The final reported window is UTC(day-1) 16:00 to
# UTC(day) 16:00; lead_days extends the controlled segment before that window.
set target_days = ( "2022-09-06" "2022-09-13" "2022-09-14" "2022-09-16" "2022-09-19" )

# Number of local days before target_day when the control starts.  Use ( 0 )
# for same-day control; use ( 1 2 3 ) to generate separate A1/A2/A3-style
# lead-time experiments for every target day and scenario.
set lead_days = ( 0 )

# RSM receptor regions to report.  For each target region the workflow makes
# both a Local scan (only this region's NOx changes) and a Whole scan (all D3
# gridded NOx changes together, matching RSM's `everywhere` case).  Use
# "D3-PRD" for the RSM OTH receptor if it is needed.  D3-PRD is the
# full-D3 area outside the nine PRD cities, including sea and neighboring
# provinces.  GD-PRD is the smaller Guangdong-only complement.
set target_regions = ( "GZ" )
set scan_modes = ( "local" )

# Multipliers applied to NOx emissions.  1.00 is the unperturbed point.
# Add more values around the fitted maximum if a finer direct-CMAQ curve is
# needed, for example 0.90 0.95 1.00 1.05 1.10.
set nox_factors = ( "0.50" "0.75" "0.90" "1.00" "1.10" "1.25" "1.50" "2.00" )
#set nox_factors = (0.50 0.75 0.80 0.85 0.90 0.95 1.00 1.05 1.10 1.15 1.20 1.50 2.00)
set APPL = "PRD"
set DOMAIN = "D3"
set VRSN = "v532"

# The existing validated v5.3.2 template is rendered into generated/; it is
# never edited in place.
set template_script = "${script_path}/../lead-time_experiments/run_cctm_D3_202209_base_devin.csh"
set base_emissctrl = "${script_path}/../lead-time_experiments/EmissCtrl_nml/EmissCtrl_cb6r3_ae7_aq_base.nml"

# The directory must contain CCTM_CGRID_PRD_YYYYJJJ.nc from the previous UTC
# day (and, when available, CCTM_MEDIA_CONC_PRD_YYYYJJJ.nc).
set baseline_cgrid_dir = "/mnt/167/devin/cmaq_output/CCTM_CGRID_base/202209_PRD_150X117_utc00"

# Segment output and post-processing locations.  Change these on the target
# compute system if /home/devin or /mnt/167 is not the intended filesystem.
set segment_root = "/home/devin/cmaq_output/pr_cmaq_validation"
set post_root = "/mnt/167/devin/cmaq_output/D3_PRD_150X117/202209/pr_cmaq_validation"
set log_root = "${segment_root}/logs"
set generated_dir = "${script_path}/generated"
set nml_dir = "${script_path}/generated/EmissCtrl_nml"

# CMAQ input and executable paths used by the source template.
set input_root = "/bigdata/CMAQ_input/devin/PRD/2022"
set icbc_root = "/bigdata/CMAQ_input/devin/PRD"
set cmaq_home = "/program/rain/Build_CMAQ/CMAQ_Project/CCTM/scripts"
set bld = "/program/rain/Build_CMAQ/CMAQ_Project/CCTM/scripts/BLD_CCTM_v532_intel"

# Existing COMBINE/18-species/daily converter scripts are reused without
# changing lead-time_experiments.
set post_script_dir = "${script_path}/../lead-time_experiments/post_scripts"
# Use the same managed environment as lead-time_experiments.  An unqualified
# `python3` may not be on PATH on batch/compute nodes.
set python_bin = "/program/software/devin_env/bin/python3"
