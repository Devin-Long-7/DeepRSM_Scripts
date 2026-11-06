#!/usr/bin/env python3
"""Convert hourly COMBINE output to local-day daily fields.

This local converter is intentionally small and explicit. It uses IOAPI global
attributes (SDATE/STIME/TSTEP) to build the hourly axis, averages all variables
over the requested local-day windows, and computes O3_MDA8 from O3.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import xarray as xr


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_ncfile")
    parser.add_argument("begin_date", help="YYYY-MM-DD")
    parser.add_argument("end_date", help="YYYY-MM-DD")
    parser.add_argument("hour_offset", type=int)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def jday_to_datetime(sdate: int, stime: int) -> datetime:
    year = sdate // 1000
    jday = sdate % 1000
    hour = stime // 10000
    minute = (stime % 10000) // 100
    second = stime % 100
    return datetime(year, 1, 1) + timedelta(days=jday - 1, hours=hour, minutes=minute, seconds=second)


def date_to_jday(day: datetime) -> int:
    return int(day.strftime("%Y%j"))


def hourly_times(ds: xr.Dataset) -> list[datetime]:
    sdate = int(ds.attrs["SDATE"])
    stime = int(ds.attrs.get("STIME", 0))
    tstep = int(ds.attrs.get("TSTEP", 10000))
    if tstep != 10000:
        raise ValueError(f"Only hourly TSTEP=10000 is supported, got {tstep}")
    start = jday_to_datetime(sdate, stime)
    return [start + timedelta(hours=i) for i in range(ds.sizes["TSTEP"])]


def mda8(day_o3: np.ndarray) -> np.ndarray:
    rolling = np.stack([day_o3[i : i + 8].mean(axis=0) for i in range(17)], axis=0)
    return np.nanmax(rolling, axis=0)


def main() -> None:
    args = parse_args()
    source = Path(args.source_ncfile)
    output = source.with_name(f"Daily_{source.name}")
    if output.exists() and not args.overwrite:
        print(f"Output file {output} already exists. Exiting...")
        return

    begin = datetime.strptime(args.begin_date, "%Y-%m-%d")
    end = datetime.strptime(args.end_date, "%Y-%m-%d")
    local_days = []
    day = begin
    while day <= end:
        local_days.append(day)
        day += timedelta(days=1)

    with xr.open_dataset(source, decode_times=False) as ds:
        times = hourly_times(ds)
        time_index = {time: i for i, time in enumerate(times)}
        rows = ds.sizes["ROW"]
        cols = ds.sizes["COL"]
        out_vars: dict[str, tuple[tuple[str, ...], np.ndarray, dict[str, str]]] = {}

        windows: list[list[int]] = []
        for local_day in local_days:
            utc_start = local_day - timedelta(hours=args.hour_offset)
            hours = [utc_start + timedelta(hours=i) for i in range(24)]
            missing = [h for h in hours if h not in time_index]
            if missing:
                raise ValueError(
                    f"{source} does not cover local day {local_day:%Y-%m-%d}; "
                    f"missing {missing[0]} to {missing[-1]}"
                )
            windows.append([time_index[h] for h in hours])

        for var_name, da in ds.data_vars.items():
            if "TSTEP" not in da.dims or "LAY" not in da.dims:
                continue
            attrs = dict(da.attrs)
            daily = np.zeros((len(local_days), 1, rows, cols), dtype=np.float32)
            for day_idx, indices in enumerate(windows):
                values = da.isel(TSTEP=indices, LAY=0).values.astype("float64")
                daily[day_idx, 0, :, :] = values.mean(axis=0).astype(np.float32)
            out_vars[var_name] = (("TSTEP", "LAY", "ROW", "COL"), daily, attrs)

        if "O3" not in ds:
            raise ValueError(f"O3 not found in {source}")
        o3_mda8 = np.zeros((len(local_days), 1, rows, cols), dtype=np.float32)
        for day_idx, indices in enumerate(windows):
            o3 = ds["O3"].isel(TSTEP=indices, LAY=0).values.astype("float64")
            o3_mda8[day_idx, 0, :, :] = mda8(o3).astype(np.float32)
        out_vars["O3_MDA8"] = (
            ("TSTEP", "LAY", "ROW", "COL"),
            o3_mda8,
            {"units": "ppbv", "long_name": "O3_MDA8"},
        )
        out_vars["O3_MDA8_CN"] = (
            ("TSTEP", "LAY", "ROW", "COL"),
            (o3_mda8 * 48.0 / 24.45).astype(np.float32),
            {"units": "ug/m3", "long_name": "O3_MDA8_CN"},
        )

        out = xr.Dataset()
        for name, (dims, values, attrs) in out_vars.items():
            out[name] = (dims, values)
            out[name].attrs.update(attrs)
        out = out.assign_coords(TSTEP=np.arange(len(local_days)), LAY=[1], ROW=np.arange(rows), COL=np.arange(cols))
        out.attrs.update(ds.attrs)
        out.attrs["SDATE"] = date_to_jday(begin)
        out.attrs["STIME"] = 0
        out.attrs["TSTEP"] = 240000

    encoding = {name: {"dtype": "float32"} for name in out.data_vars}
    out.to_netcdf(output, format="NETCDF3_CLASSIC", encoding=encoding)
    out.close()

    check = xr.open_dataset(output, decode_times=False)
    max_o3 = float(check["O3_MDA8"].max())
    mean_o3 = float(check["O3_MDA8"].mean())
    check.close()
    if max_o3 <= 0.0:
        raise ValueError(f"Daily conversion produced zero O3_MDA8: {output}")
    print(output)
    print(f"O3_MDA8 mean={mean_o3:.6f}, max={max_o3:.6f}")


if __name__ == "__main__":
    main()
