# Carryover Species Definitions

[中文](README_carryover.md)

`SpecDef_cb6r3_ae7_aq_carryover_all_layers.txt` extends the standard all-layer definition while retaining its active outputs. `#layer -1` selects all available input layers.

The definition covers the 21 basic variables used by the existing extraction script and retains meteorological and particulate definitions. It adds 24 individual gas-phase outputs: PAN, PANX, OPAN, NTR1, NTR2, INTR, NO3, PNA, CRON, CLNO2, CLNO3, HO2, ALDX, ACET, KET, GLY, MGLY, GLYD, PACD, AACD, MEOH, ETOH, ROOH and MEO2. These additions multiply input ppmV by 1000 to obtain ppbV. Check that the source ACONC actually contains every required mechanism species.

Existing aggregate outputs include PANS=PAN+PANX+OPAN and NTR=NTR1+NTR2+INTR. Do not double-count aggregates and components; NOY also includes these components. Treat lumped OVOC species according to the chemical mechanism rather than as individual real compounds.

Explicitly select this definition for COMBINE. `1_run_combine_aconc.csh` sets `SPECIES_DEF` internally, so setting the variable only in an outer shell may be overridden. Configure the actual internal definition path in a working copy and verify mechanism, input units and output variables. Preserve complete COMBINE output or extend the extraction list; the original `2_extract_18species_by_nco.csh` discards the added species.

This documentation does not establish successful COMBINE execution on the target dataset.
