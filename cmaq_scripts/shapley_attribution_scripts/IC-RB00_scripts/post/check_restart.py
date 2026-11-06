#!/usr/bin/env python3
"""核对生成脚本指定的 CGRID：必须是分段起点（或终点）的完整瞬时场。"""
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import re

import numpy as np
from netCDF4 import Dataset


def setting(script, name):
    match = re.search(r"^\s*set(?:env)?\s+" + name + r"\s+(?:=\s*)?([^\n#]+)", script, re.M)
    if not match:
        raise ValueError(f"Missing setting: {name}")
    return match[1].strip().strip('"')


def check_restart(path, instant, layers, reference=None):
    """CGRID 仅一条瞬时记录；同时核对所有物种时间及 MCIP 网格。"""
    with Dataset(path) as ds:
        expected = [int(instant.strftime("%Y%j")), int(instant.strftime("%H%M%S"))]
        flags = ds["TFLAG"][:]
        if (len(ds.dimensions["TSTEP"]) != 1 or np.ma.getmaskarray(flags).any()
                or not np.all(flags == expected)):
            raise ValueError(f"{path}: expected one complete CGRID at UTC {instant}")
        if len(ds.dimensions["LAY"]) != layers:
            raise ValueError(f"{path}: expected {layers} layers")
        species = [v for v in ds.variables.values() if v.dimensions == ("TSTEP", "LAY", "ROW", "COL")]
        if not species or len(species) != int(ds.NVARS):
            raise ValueError(f"{path}: incomplete species inventory")
        if reference:
            with Dataset(reference) as met:
                for name in ("NCOLS", "NROWS", "NLAYS", "GDTYP", "XORIG", "YORIG",
                             "XCELL", "YCELL", "P_ALP", "P_BET", "P_GAM", "XCENT", "YCENT", "VGTYP", "VGLVLS"):
                    if not np.allclose(ds.getncattr(name), met.getncattr(name)):
                        raise ValueError(f"{path}: {name} differs from {reference}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pending-restart", action="store_true")
    parser.add_argument("--output", action="store_true")
    parser.add_argument("script", type=Path)
    args = parser.parse_args()
    script = args.script.read_text()
    if re.search(r"@[A-Za-z_]+@", script):
        raise ValueError("Unfilled template parameter")
    start = datetime.strptime(setting(script, "START_DATE") + setting(script, "STTIME"), "%Y-%m-%d%H%M%S")
    path = Path(setting(script, "RESTART_FILE"))
    instant = start
    if args.output:
        path = Path(setting(script, "OUTDIR")) / f'CCTM_CGRID_{setting(script, "APPL")}_{start:%Y%j}.nc'
        duration = int(setting(script, "NSTEPS"))
        instant += timedelta(hours=duration // 10000, minutes=duration // 100 % 100)
    elif args.pending_restart and not path.exists():
        print(f"Pending seg01 output: {path}")
        return
    met = Path(setting(script, "METpath")) / f"METCRO3D_{start:%Y%j}"
    check_restart(path, instant, int(setting(script, "NZ")), met)
    print(f"CGRID verified: UTC {instant}; {path}")


if __name__ == "__main__":
    main()
