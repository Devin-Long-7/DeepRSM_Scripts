#!/bin/csh -f
# Verify the C11 propagated CGRID files needed by C10 (IC-only) exist.
# Usage: ./check_ic11_cgrid.csh [c11_case]   default: prd2zero
# Required prior-day Julian dates for the 5 target days (249/256/257/259/262):
#   248, 255, 256, 258, 261

set C11 = "$1"
if ( "$C11" == "" ) set C11 = prd2zero

set OUTDIR = /home/devin/cmaq_output/${C11}/D3/2022/09
set RUNID  = PRD
set need = ( 2022248 2022255 2022256 2022258 2022261 )

echo "Checking C11 CGRID in: $OUTDIR"
if ( ! -d "$OUTDIR" ) then
   echo "ERROR: OUTDIR does not exist: $OUTDIR"
   exit 1
endif

set missing = 0
foreach j ( $need )
   set f = "$OUTDIR/CCTM_CGRID_${RUNID}_${j}.nc"
   if ( -e "$f" ) then
      echo "  OK   $f"
   else
      echo "  MISS $f"
      @ missing = $missing + 1
   endif
end

if ( $missing > 0 ) then
   echo "ERROR: $missing required C11 CGRID file(s) missing."
   echo "       Run Phase A first:  csh run_cctm_D3_202209_prd2zero_sep19.csh"
   exit 1
else
   echo "All 5 required C11 CGRID files present. OK to run Phase B (C10)."
   exit 0
endif
