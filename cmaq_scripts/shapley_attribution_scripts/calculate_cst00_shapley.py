#!/usr/bin/env python3
"""Calculate CST00 four-cell Shapley temporal attribution.

The four cells are C00 (baseline IC + baseline emissions), C01 (CST00-reset
control), C10 (propagated C11 IC + baseline emissions), and C11 (propagated
control).  Inputs may be a JSON scalar table or four CST daily NetCDF files
containing ``O3_MDA8``.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np


DEFAULT_DATES = ("Sep06", "Sep13", "Sep14", "Sep16", "Sep19")


def _date_labels(value: str | None) -> list[str]:
    return [x.strip() for x in (value or ",".join(DEFAULT_DATES)).split(",") if x.strip()]


def _load_json(path: Path, dates: list[str]) -> dict[tuple[str, str, str], float]:
    raw = json.loads(path.read_text())
    values: dict[tuple[str, str, str], float] = {}
    for key, value in raw.items():
        try:
            cell, date, region = key.split("|", 2)
            values[cell, date, region] = float(value)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid JSON key {key!r}; expected CELL|DATE|REGION") from exc
    missing = [(cell, date) for cell in ("C00", "C01", "C10", "C11") for date in dates
               if not any((cell, date, region) in values for region in {r for c, d, r in values if c == cell and d == date})]
    if missing:
        raise ValueError(f"JSON is missing cell/date values: {missing[:5]}")
    return values


def _read_netcdf(path: Path, dates: list[str], mask_paths: dict[str, Path] | None):
    import xarray as xr

    if not path.is_file():
        raise FileNotFoundError(path)
    with xr.open_dataset(path) as ds:
        if "O3_MDA8" not in ds:
            raise ValueError(f"{path}: O3_MDA8 variable is required")
        field = ds["O3_MDA8"]
        units = str(field.attrs.get("units", "")).strip().lower()
        if units and units not in {"ppbv", "ppb", "ppbvol", "ppb_v"}:
            raise ValueError(f"{path}: O3_MDA8 units must be ppbv, got {units!r}")
        if "LAY" in field.dims:
            field = field.isel(LAY=0)
        if field.dims[0] != "TSTEP":
            field = field.transpose("TSTEP", ...)
        values = np.asarray(field.values, dtype=float)
        if values.ndim != 3:
            raise ValueError(f"{path}: expected TSTEP, ROW, COL after LAY selection; got {field.dims}")
        start = int(ds.attrs.get("SDATE", 0))
        if not start:
            raise ValueError(f"{path}: SDATE attribute is required")
        # Target labels are mapped by YYYYJJJ in the file's daily sequence.
        years = start // 1000
        jday = start % 1000
        labels = {}
        import datetime as dt
        day = dt.date(years, 1, 1) + dt.timedelta(days=jday - 1)
        for i in range(values.shape[0]):
            labels[day.strftime("%b%d")] = i
            day += dt.timedelta(days=1)
        masks = {"DOMAIN": np.ones(values.shape[1:], dtype=bool)}
        if mask_paths:
            for name, mask_path in mask_paths.items():
                mask = np.asarray(np.load(mask_path), dtype=bool)
                if mask.shape != values.shape[1:]:
                    raise ValueError(f"{mask_path}: shape {mask.shape} != field shape {values.shape[1:]}")
                masks[name] = mask
        out = {}
        for date in dates:
            if date not in labels:
                raise ValueError(f"{path}: requested {date} is outside {start} + {values.shape[0]} days")
            field_day = values[labels[date]]
            if not np.isfinite(field_day).all():
                raise ValueError(f"{path}: non-finite O3_MDA8 values on {date}")
            for name, mask in masks.items():
                selected = field_day[mask]
                if selected.size == 0:
                    raise ValueError(f"{name}: empty mask on {date}")
                out[date, name] = float(selected.mean())
        return out


def _load_masks(value: str | None) -> dict[str, Path] | None:
    if not value:
        return None
    raw = json.loads(Path(value).read_text())
    if not isinstance(raw, dict) or not raw:
        raise ValueError("--mask-json must contain a non-empty {region: .npy path} object")
    return {str(name): Path(path) for name, path in raw.items()}


def _rows(values: dict[tuple[str, str, str], float], dates: list[str]):
    regions = sorted({region for cell, date, region in values if date in dates})
    rows = []
    for region in regions:
        for date in dates:
            c00, c01, c10, c11 = (values[cell, date, region] for cell in ("C00", "C01", "C10", "C11"))
            total = c00 - c11
            same = c00 - c01
            history = c00 - c10
            interaction = total - same - history
            same_shap = 0.5 * ((c00 - c01) + (c10 - c11))
            carry_shap = 0.5 * ((c00 - c10) + (c01 - c11))
            rows.append({
                "region": region, "date": date,
                "C00": c00, "C01": c01, "C10": c10, "C11": c11,
                "R_total": total, "R_same_day": same,
                "R_history_only": history, "R_interaction": interaction,
                "carryover_residual": total - same,
                "carryover_Shapley": carry_shap,
                "same_day_Shapley": same_shap,
                "HDF_residual_pct": 100.0 * (total - same) / total if total else float("nan"),
                "HDF_Shapley_pct": 100.0 * carry_shap / total if total else float("nan"),
                "closure_error": same_shap + carry_shap - total,
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", type=Path, help="Existing scalar table with CELL|DATE|REGION keys")
    parser.add_argument("--c00", type=Path)
    parser.add_argument("--c01", type=Path)
    parser.add_argument("--c10", type=Path)
    parser.add_argument("--c11", type=Path)
    parser.add_argument("--dates", help="Comma-separated labels, default: Sep06,Sep13,Sep14,Sep16,Sep19")
    parser.add_argument("--mask-json", type=Path, help="JSON mapping region names to boolean .npy masks")
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    dates = _date_labels(args.dates)
    netcdf_args = [getattr(args, x) for x in ("c00", "c01", "c10", "c11")]
    if args.input_json and any(netcdf_args):
        parser.error("provide either --input-json or all four --c00/--c01/--c10/--c11 files")
    if not args.input_json and not all(netcdf_args):
        parser.error("provide either --input-json or all four --c00/--c01/--c10/--c11 files")

    if args.input_json:
        values = _load_json(args.input_json, dates)
    else:
        paths = {cell: getattr(args, cell.lower()) for cell in ("C00", "C01", "C10", "C11")}
        masks = _load_masks(str(args.mask_json) if args.mask_json else None)
        per_cell = {cell: _read_netcdf(path, dates, masks) for cell, path in paths.items()}
        regions = sorted({region for cell in per_cell for date, region in per_cell[cell]})
        values = {(cell, date, region): per_cell[cell][date, region]
                  for cell in per_cell for date in dates for region in regions}

    rows = _rows(values, dates)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_prefix.with_suffix(".csv")
    json_path = args.output_prefix.with_suffix(".json")
    fields = list(rows[0]) if rows else []
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps({f"{r['region']}|{r['date']}": r for r in rows}, indent=2) + "\n")
    max_error = max((abs(r["closure_error"]) for r in rows), default=0.0)
    if max_error > 1e-8:
        raise RuntimeError(f"Shapley closure failed: max error {max_error:.3e}")
    print(f"Wrote {csv_path} and {json_path}; rows={len(rows)}, max closure={max_error:.3e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
