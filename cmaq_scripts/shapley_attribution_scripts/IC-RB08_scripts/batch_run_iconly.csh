#!/bin/csh -f
# Generate (+ optionally run/submit) C10 IC-only for all 10 PRD scenarios.
# Usage:
#   ./batch_run_iconly.csh gen     # generate all 10 scripts only (safe; no CMAQ)
#   ./batch_run_iconly.csh submit  # generate + sbatch each (parallel on cluster)
#   ./batch_run_iconly.csh run     # generate + run inline sequentially (default)

set regions = (prd gz sz zh fs jm zq hz dg zs)
set mode = "$1"
if ( "$mode" == "" ) set mode = run

foreach r ($regions)
   echo "=== C10 for $r ==="
   ./create_iconly_csh.csh $r
   if ( "$mode" == "gen" ) then
      continue
   else if ( "$mode" == "submit" ) then
      sbatch run_cctm_D3_202209_${r}2zero_iconly.csh
   else
      csh run_cctm_D3_202209_${r}2zero_iconly.csh
   endif
end
echo "Batch done (mode=$mode)."
