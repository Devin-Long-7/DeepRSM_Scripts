#!/bin/csh -f
# =====================================================================
# Launcher for the 5 target ISAM daily-restart segments.
#
# Each day is fully INDEPENDENT (physical IC comes from the base run's CGRID,
# ISAM tags are reset), so the 5 segments do not depend on each other.
#
# Default: run SEQUENTIALLY (safe for a single node/container: 32 procs each).
# To run them in PARALLEL instead, append " &" to the csh line inside the loop
# and add a `wait` after the foreach -- but mind the total core count
# (32 procs x N parallel jobs must fit on the node).
#
# Target days (the MDA8 days of interest):
#   2022-09-06, 2022-09-13, 2022-09-14, 2022-09-16, 2022-09-19
# IC (base CGRID, previous Julian day) needed for each:
#   2022248, 2022255, 2022256, 2022258, 2022261
# =====================================================================

set DATES = ( 2022-09-06 2022-09-13 2022-09-14 2022-09-16 2022-09-19 )

foreach d ( $DATES )
   echo ""
   echo "==================== ISAM daily-restart for $d ===================="
   csh run_cctm_D3_ISAM_daily_restart.csh $d
   if ( $status != 0 ) then
      echo "**** ERROR: segment for $d failed; check log. Continuing to next day. ****"
   endif
end

echo ""
echo "All 5 ISAM daily-restart segments finished."
