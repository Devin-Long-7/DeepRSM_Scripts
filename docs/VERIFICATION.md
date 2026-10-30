# Verification

The original preprocessing, coefficient prediction, PR/EKMA and both OOS
validation entry points completed successfully on 29 October 2026.
No numerical implementation was rewritten for this release.

| Output | Comparison |
| --- | --- |
| Daily RSM coefficients | 330 arrays match the historical fine-tuned arrays exactly |
| PR, ozone maxima and VNr | 45 city-days, all six numerical fields match the paper source CSV exactly |
| EKMA | Five sheets of 49 scenarios and 12 columns match the paper workbook exactly |
| Eight-scenario OOS | All four numerical columns match for 1,493,040 rows |
| SI statistics | Both specified-scenario and LHS statistics match within 1e-9, including reference rounding |

Machine-readable comparisons are provided in tests/*comparison.json.
The five-day specified-scenario response subset has squared Pearson correlation
0.935919018109, RMSE 0.525882946275 ppb and MAE 0.207005473307 ppb.

Training scripts, training patches and training execution records are excluded
from this public release. The inference network definition is retained so the
released trained checkpoint can be loaded.

The public Python entry points retain their original implementations. The PR
entry point reads its boundary path from the supplied INI rather than a fixed
historical path. The INI copies redirect checkpoint, boundary and output paths.
Large raw inputs are not bundled. Existing scripts and data on the study server
were not modified.
