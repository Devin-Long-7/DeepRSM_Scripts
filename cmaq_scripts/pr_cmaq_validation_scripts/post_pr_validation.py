#!/usr/bin/env python3
"""Merge CMAQ lead-time segments and make one UTC+8 daily result per scan.

The manifest is produced by ``batch_run_pr_validation.csh``.  For each row,
this program links all ACONC/APMDIAG files from the control start day through
the target day, reuses the validated local COMBINE/extraction scripts, converts
the result to the target Beijing-time day, and reports both domain and
selected-region O3_MDA8 values.
"""

from __future__ import annotations

import argparse
import csv
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import xarray as xr


@dataclass(frozen=True)
class Task:
    target_day: str
    lead_days: str
    target_region: str
    scan_mode: str
    control_scope: str
    nox_factor: str
    pre_case: str
    seg02_case: str
    seg03_case: str
    first_utc_day: str
    local_day: str

    @property
    def merged_case(self) -> str:
        suffix = "_seg02"
        if not self.seg02_case.endswith(suffix):
            raise ValueError(f"unexpected seg02 case name: {self.seg02_case}")
        return f"{self.seg02_case[:-len(suffix)]}_merged"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--post-script-dir", required=True, type=Path)
    parser.add_argument("--segment-root", required=True, type=Path)
    parser.add_argument("--post-root", required=True, type=Path)
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--appl", default="PRD")
    parser.add_argument("--domain", default="D3")
    parser.add_argument("--vrsn", default="v532")
    parser.add_argument("--mech", default="cb6r3_ae7_aq")
    parser.add_argument("--mask-file", type=Path)
    parser.add_argument("--python-bin", default=sys.executable)
    return parser.parse_args()


def command_prefix(value: str) -> list[str]:
    parts = shlex.split(value)
    if not parts:
        raise ValueError("python command is empty")
    return parts


def read_tasks(path: Path) -> list[Task]:
    if not path.is_file():
        raise FileNotFoundError(path)
    # Older generated manifests used the two-character string ``\\t`` in
    # the header while data rows used real tab characters.  Normalize the
    # complete file so those manifests remain usable after deployment.
    raw = path.read_text(encoding="utf-8-sig")
    normalized = raw.replace("\\t", "\t")
    rows = [
        row
        for row in csv.DictReader(normalized.splitlines(), delimiter="\t")
        if row.get("target_day")
    ]
    required = {
        "target_day",
        "lead_days",
        "target_region",
        "scan_mode",
        "control_scope",
        "nox_factor",
        "pre_case",
        "seg02_case",
        "seg03_case",
        "first_utc_day",
        "local_day",
    }
    if rows and "lead_days" not in rows[0]:
        for row in rows:
            row["lead_days"] = "0"
    if rows and not required.issubset(rows[0]):
        raise ValueError(f"manifest is missing columns: {sorted(required - set(rows[0]))}")
    if not rows:
        raise ValueError(
            f"manifest contains no tasks: {path}. "
            "Check that it has a tab-separated header and at least one data row."
        )
    return [Task(**{name: row[name] for name in required}) for row in rows]


def jday(day: str) -> str:
    return datetime.strptime(day, "%Y-%m-%d").strftime("%Y%j")


def month_dir(root: Path, case: str, day: str, domain: str) -> Path:
    parsed = datetime.strptime(day, "%Y-%m-%d")
    return root / case / domain / parsed.strftime("%Y") / parsed.strftime("%m")


def symlink_file(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"missing CMAQ output: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink() or destination.exists():
        destination.unlink()
    destination.symlink_to(source.resolve())


def date_range(begin: str, end: str) -> list[str]:
    current = datetime.strptime(begin, "%Y-%m-%d").date()
    stop = datetime.strptime(end, "%Y-%m-%d").date()
    days: list[str] = []
    while current <= stop:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def run_logged(command: list[str], env: dict[str, str], log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    print("RUN", " ".join(shlex.quote(part) for part in command))
    with log_file.open("w", encoding="utf-8") as handle:
        result = subprocess.run(
            command,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if result.returncode:
        tail = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            + "\n".join(tail)
        )


def factor_tag(factor: str) -> str:
    return factor.replace("-", "m").replace(".", "p")


def mask_average(values: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    valid = np.isfinite(values) & np.isfinite(mask) & (mask > 0)
    if not np.any(valid):
        raise ValueError("selected CMAQ mask has no positive grid cells")
    weighted = np.where(valid, values * mask, np.nan)
    denominator = float(np.nansum(np.where(valid, mask, np.nan)))
    mean = float(np.nansum(weighted) / denominator)
    return mean, float(np.nanmax(np.where(valid, values, np.nan)))


def read_o3_metrics(
    daily_file: Path, target_region: str, mask_file: Path | None
) -> tuple[float, float, float, float]:
    with xr.open_dataset(daily_file, decode_times=False) as ds:
        if "O3_MDA8" not in ds:
            raise ValueError(f"O3_MDA8 is missing from {daily_file}")
        values = ds["O3_MDA8"].isel(TSTEP=0, LAY=0).values.astype("float64")
        domain_mean = float(np.nanmean(values))
        domain_max = float(np.nanmax(values))

    if mask_file is None:
        return domain_mean, domain_max, float("nan"), float("nan")
    if not mask_file.is_file():
        raise FileNotFoundError(f"CMAQ mask file not found: {mask_file}")
    with xr.open_dataset(mask_file, decode_times=False) as masks:
        if target_region not in masks.variables:
            raise ValueError(
                f"target-region mask {target_region!r} not found in {mask_file}; "
                "GD-PRD and D3-PRD are distinct regions and are not interchangeable"
            )
        mask = masks[target_region].isel(TSTEP=0, LAY=0).values.astype("float64")
    scope_mean, scope_max = mask_average(values, mask)
    return domain_mean, domain_max, scope_mean, scope_max


def process_task(task: Task, args: argparse.Namespace, pycmd: list[str]) -> dict[str, str | float]:
    merged_case = task.merged_case
    merged_root = args.segment_root / merged_case
    post_dir = args.post_root / merged_case
    post_dir.mkdir(parents=True, exist_ok=True)

    # A lead-time run has seg02 (first partial local day), optional middle
    # full-day segments, and a final segment ending at target-day 16 UTC.
    # Locate every segment by the common scenario prefix and link each UTC day
    # into the layout expected by COMBINE.
    scenario_prefix = task.seg02_case.removesuffix("_seg02")
    segment_cases = sorted(
        path.name
        for path in args.segment_root.glob(f"{scenario_prefix}_seg*")
        if path.is_dir()
    )
    if not segment_cases:
        raise FileNotFoundError(
            f"no segment directories found for scenario prefix {scenario_prefix}"
        )
    for day in date_range(task.first_utc_day, task.target_day):
        destination_dir = month_dir(merged_root.parent, merged_case, day, args.domain)
        for prefix in ("CCTM_ACONC", "CCTM_APMDIAG"):
            filename = f"{prefix}_{args.appl}_{jday(day)}.nc"
            for case in segment_cases:
                source = month_dir(args.segment_root, case, day, args.domain) / filename
                if source.is_file():
                    symlink_file(source, destination_dir / filename)
                    break
            else:
                raise FileNotFoundError(
                    f"missing {filename} for {task.target_day}, "
                    f"lead_days={task.lead_days}, scenario={scenario_prefix}"
                )

    env = os.environ.copy()
    env.update(
        {
            "VRSN": args.vrsn,
            "DOMAIN": args.domain,
            "APPL": args.appl,
            "MECH": args.mech,
            "LAYER": "1",
            "INPDIR": str(args.input_root),
            "CCTMOUTDIR_ROOT": str(merged_root),
            "BEGIN_DATE": task.first_utc_day,
            "END_DATE": task.target_day,
            "OUTPUT_BY_YEARMONTH": "F",
            "COMBINE_DIR": str(post_dir),
            "INCLUDE_WRF": "F",
            "KEEP_18SPECIES_ONLY": "T",
            "KEEP_COMBINE_FILE": "T",
            "CASE_NAME": merged_case,
        }
    )

    combine = args.post_script_dir / "1_run_combine_aconc_local.csh"
    extract = args.post_script_dir / "2_extract_18species_by_nco_local.csh"
    converter = args.post_script_dir / "4_convert2daily_local.py"
    checker = args.post_script_dir / "check_daily_o3.py"
    for script in (combine, extract, converter, checker):
        if not script.is_file():
            raise FileNotFoundError(f"post-processing script not found: {script}")

    run_logged(["csh", str(combine)], env, post_dir / "combine.log")
    runid = f"{args.vrsn}_{args.domain}_{merged_case}_{args.appl}"
    layer_name = "all_layers" if env.get("LAYER")=="-1" else "layer_1"
    env.update(
        {
            "POSTDIR": str(post_dir),
            "RUNID": runid,
            "LAYER_NAME": layer_name,
        }
    )
    run_logged(["csh", str(extract)], env, post_dir / "extract.log")
    extracted = post_dir / (
        f"COMBINE_ACONC_{runid}_{layer_name}_{task.first_utc_day}_{task.target_day}_18species.nc"
    )
    if not extracted.is_file():
        raise FileNotFoundError(f"expected extracted file not found: {extracted}")

    run_logged(
        pycmd
        + [str(converter), str(extracted), task.target_day, task.target_day, "8", "--overwrite"],
        env,
        post_dir / "daily_conversion.log",
    )
    daily = post_dir / f"Daily_{extracted.name}"
    if not daily.is_file():
        raise FileNotFoundError(f"expected daily file not found: {daily}")
    run_logged(pycmd + [str(checker), str(daily)], env, post_dir / "daily_qc.log")

    mask = args.mask_file
    if mask is None:
        mask = args.input_root / "ocean" / args.domain / f"{args.domain}_cmaq_masks"
    domain_mean, domain_max, scope_mean, scope_max = read_o3_metrics(
        daily, task.target_region, mask
    )
    print(
        f"{task.target_day} {task.target_region} {task.scan_mode} "
        f"(control={task.control_scope}) NOx={task.nox_factor}: "
        f"target O3_MDA8 mean={scope_mean:.4f}, max={scope_max:.4f} ppbv"
    )
    return {
        "target_day": task.target_day,
        "lead_days": int(task.lead_days),
        "target_region": task.target_region,
        "scan_mode": task.scan_mode,
        "control_scope": task.control_scope,
        "nox_factor": float(task.nox_factor),
        "first_utc_day": task.first_utc_day,
        "merged_case": merged_case,
        "daily_file": str(daily),
        "domain_o3_mda8_mean_ppbv": domain_mean,
        "domain_o3_mda8_max_ppbv": domain_max,
        "target_o3_mda8_mean_ppbv": scope_mean,
        "target_o3_mda8_max_ppbv": scope_max,
    }


def main() -> int:
    args = parse_args()
    tasks = read_tasks(args.manifest)
    if not tasks:
        raise SystemExit("manifest contains no tasks")
    args.post_root.mkdir(parents=True, exist_ok=True)
    pycmd = command_prefix(args.python_bin)
    results: list[dict[str, str | float]] = []
    for index, task in enumerate(tasks, start=1):
        print(
            f"[{index}/{len(tasks)}] post-processing {task.target_day} "
            f"{task.target_region} {task.scan_mode} NOx={task.nox_factor}"
        )
        results.append(process_task(task, args, pycmd))

    summary = args.post_root / "pr_validation_summary.csv"
    fields = list(results[0])
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    print(f"Summary: {summary}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
