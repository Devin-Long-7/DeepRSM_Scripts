# Emission-Control Namelists

[中文](README.md)

Existing `EmissCtrl_*.nml` files provide CB6R3/AE7/AQ scenario inputs through configuration `NML_PATH`. They are model inputs, not analysis outputs.

## File Groups

- `EmissCtrl_cb6r3_ae7_aq_base.nml`: baseline.
- `*2zero.nml` and `*2zero_ic.nml`: regional zero-out and IC-RB naming variants; inspect actual rules.
- `*oos1.nml` through `*oos5.nml` and `*run1.nml` through `*run31.nml`: existing validation/design cases; the actual inventory determines available IDs.
- `*local_only_CITY.nml`: retain the target PRD city, zero the other eight cities and `D3-PRD`.
- `*other_prd_only_CITY.nml`: retain the other eight cities, zero the target city and `D3-PRD`.
- `*oth_prd2zero_CITY.nml`, `*outside_prd2zero_prd.nml` and `*prd2zero.nml`: regional/family controls defined within each file.
- `README.md` and `README_en.md`: documentation.

`D3-PRD` means all D3 cells outside the nine cities, not merely the remainder of Guangdong. Inspect `EmissionScalingRules` for families and natural-source treatment; filenames do not define the complete scaling matrix.

## Usage

Set `GENERATE_NML=N` in the parent configuration and select `NML_PATH`. Check mask region names, streams, families, factors and mechanism. A multiplicative factor of 0.7 retains 70% of baseline emissions.

For CSV-driven generation, use the parent `create_emissCtrl_nml.py` and `nml_config/`; the generator does not automatically use these existing cases as templates. Other modules also reference `cctm_scripts_v5.3.2/EmissCtrl_nml/`. Its files and those in `IC-RB-UTC00_scripts/EmissCtrl_nml/` are maintained independently.
