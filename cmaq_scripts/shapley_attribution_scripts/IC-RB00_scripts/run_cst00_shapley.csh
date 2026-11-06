#!/bin/csh -f
# Run or validate the CST00 four-cell Shapley experiment.
# No flag executes; --dry-run only generates and validates segment plans.

set SCRIPT_DIR = `dirname "$0"`
cd "$SCRIPT_DIR"
set DRY = ""
foreach arg ($argv)
    if ( "$arg" == "--dry-run" ) set DRY = "--dry-run"
end

set configs = (config_C00.csh config_C01.csh config_C11.csh config_C10.csh config_E01.csh config_E11.csh config_E10.csh)
foreach cfg ($configs)
    echo "=== CST00 Shapley $cfg ==="
    if ( "$DRY" == "--dry-run" ) then
        csh run_manager.csh "$SCRIPT_DIR/$cfg" --dry-run
    else
        csh run_manager.csh "$SCRIPT_DIR/$cfg"
    endif
    if ( $status != 0 ) then
        echo "FAILED: $cfg"
        exit 1
    endif
end
echo "CST00 four-cell run complete."
