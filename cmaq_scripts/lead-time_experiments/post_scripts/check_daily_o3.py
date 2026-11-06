#!/usr/bin/env python3
from __future__ import annotations

import sys

import xarray as xr


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: check_daily_o3.py <daily_file>")
        return 1
    daily_file = sys.argv[1]
    ds = xr.open_dataset(daily_file, decode_times=False)
    max_o3 = float(ds["O3_MDA8"].max())
    mean_o3 = float(ds["O3_MDA8"].mean())
    ds.close()
    print(f"Daily QC: {daily_file} O3_MDA8 mean={mean_o3:.6f}, max={max_o3:.6f}")
    return 0 if max_o3 > 0.0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
