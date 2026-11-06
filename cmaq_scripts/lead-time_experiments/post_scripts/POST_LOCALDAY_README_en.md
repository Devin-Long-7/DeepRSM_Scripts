# Local-Day Control Post-Processing

[中文](POST_LOCALDAY_README.md)

Assemble completed lead-time UTC segments, run COMBINE/extraction and calculate CST (UTC+8) daily statistics.

## Files

```text
post_scripts/
|-- POST_LOCALDAY_README.md / POST_LOCALDAY_README_en.md
|-- run_post_localday_controls.csh            # Main entry
|-- run_post_localday_controls_w_o_sep19.csh   # Default dates exclude September 19
|-- run_post_localday_controls.csh.bak         # Historical backup
|-- 1_run_combine_aconc_local.csh              # COMBINE variables
|-- 2_extract_18species_by_nco_local.csh        # NCO extraction
|-- 4_convert2daily_local.py                  # Local daily statistics/MDA8
`-- check_daily_o3.py                         # Daily ozone checks
```

## Usage

Parent batch `enable_post` controls automatic calls with that run's dates, experiments and case. Standalone defaults may differ from existing data; pass matching parameters explicitly:

```bash
# From lead-time_experiments
csh post_scripts/run_post_localday_controls.csh --help
csh post_scripts/run_post_localday_controls.csh \
  --target-days "2022-09-06 2022-09-13 2022-09-14 2022-09-16 2022-09-19" \
  --experiments "P0:0 A1:1 A2:2 A3:3" \
  --case-suffix "L-B_HZ_VOC30_NOX30" \
  --segment-root "/path/to/cmaq_output" --appl "PRD" \
  --combine-dir "/path/to/new_post_output"
```

Replace paths with completed segments and a new output location. This entry has no dry-run; it writes outputs and can replace intermediate files. Check COMBINE, NCO, Python, species definitions and options including `INCLUDE_WRF` and `KEEP_COMBINE_FILE`.

## Outputs

ACONC/APMDIAG segments are assembled by UTC day before COMBINE, extraction and daily conversion. Outputs include `COMBINE_ACONC_*.nc`, `*_18species.nc` and `Daily_*_18species.nc`; these are generated, not bundled inputs.

The historical “18species” name also covers derived NOX, VOC and O3_UGM3; inspect the actual variable list. Calculate MDA8 over complete target CST coverage, not a single 8/16-hour segment. `check_daily_o3.py` takes an existing daily file path to check the generated ozone data.
