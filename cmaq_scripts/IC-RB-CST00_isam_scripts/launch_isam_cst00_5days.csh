#!/bin/csh -f
# =====================================================================
# Launcher for the 5 target ISAM CST00 daily-restart days.
#
# Each target day is INDEPENDENT (physical IC from the baseline UTC16
# CGRID, ISAM tags reset at CST00), so days can run sequentially or in
# parallel (mind core count if parallel).
#
# Target CST days (MDA8 episode days):
#   2022-09-06, 2022-09-13, 2022-09-14, 2022-09-16, 2022-09-19
# Required baseline UTC16 CGRID (previous UTC day):
#   2022248, 2022255, 2022256, 2022258, 2022261
# =====================================================================

set DATES = ( 2022-09-06 2022-09-13 2022-09-14 2022-09-16 2022-09-19 )

foreach d ( $DATES )
   echo ""
   echo "==================== ISAM CST00 daily-restart for $d ===================="
   csh run_cctm_D3_ISAM_daily_restart_CST00.csh $d
   if ( $status != 0 ) then
      echo "**** ERROR: segments for $d failed; check LOGS_CST00/. Continuing. ****"
   endif
end

echo ""
echo "All 5 ISAM CST00 daily-restart days finished."
