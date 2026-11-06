#!/usr/bin/env python3
"""在隔离目录补提取已有 CST00 输出，复用 run_post.py 的算法，保留原始数据。"""

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from netCDF4 import Dataset

import run_post


class IncompleteCase(Exception):
    """所请求的 CST 日期尚缺少原始分段文件。"""


def write_result(work, **values):
    (work / "result.json").write_text(json.dumps(values, indent=2, ensure_ascii=False) + "\n")


def recovery_plan(work, case_root):
    # 原 prepare 只生成脚本和计划，不会创建原 merged/post，也不会修改原始数据。
    # 改写本次副本的输出路径，再交给同一套拼接、提取和日转换函数。
    requested_cleanup = os.environ.get("CLEANUP_CCTM_OUTPUT")
    os.environ["CLEANUP_CCTM_OUTPUT"] = "F"
    scripts = work / "post_scripts"
    run_post.prepare(scripts, case_root)
    plan = json.loads((scripts / "post_plan.json").read_text())
    products = Path(plan["post"]) / ("repost_" + work.name)
    plan.update(post=str(products), merged=str(work / "merged"), mode="recovery",
                original_cleanup_setting=requested_cleanup)
    for key in ("combined", "hourly", "daily"):
        plan[key] = str(products / Path(plan[key]).name)
    run_post.copy_post_scripts(scripts, plan)
    run_post.save_plan(scripts, plan)
    return scripts, plan


def require_readable(path):
    if not path.is_file():
        raise FileNotFoundError(f"Missing post input: {path}")
    with path.open("rb") as stream:
        stream.read(1)


def preflight(work, plan):
    cfg = plan["config"]
    root = Path(plan["case_root"])
    if work.resolve().is_relative_to(root.resolve()):
        raise ValueError("Recovery work directory must be outside the original case directory")
    first, last = [datetime.strptime(cfg[key], "%Y-%m-%d")
                   for key in ("POST_BEGIN_DATE", "POST_END_DATE")]
    inputs, missing, raw_layers = [], [], set()
    local = first
    while local <= last:
        for segment, start, hours in (("seg01", local - timedelta(hours=8), 8),
                                      ("seg02", local, 16)):
            folder = root / f"{local:%Y%m%d}/{segment}/{cfg['DOMAIN']}/{start:%Y/%m}"
            for prefix in ("CCTM_ACONC", "CCTM_APMDIAG"):
                path = folder / f"{prefix}_{cfg['APPL']}_{start:%Y%j}.nc"
                if not path.is_file():
                    missing.append(str(path))
                    continue
                if not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError(f"Segment input points outside the original case: {path}")
                run_post.check_time(path, start, hours, flags_required=True)
                with Dataset(path) as ds:
                    layers = len(ds.dimensions["LAY"])
                    if int(ds.NLAYS) != layers:
                        raise ValueError(f"{path}: NLAYS disagrees with the LAY dimension")
                    raw_layers.add(layers)
                inputs.append(str(path))
        local += timedelta(days=1)
    (work / "input_check.json").write_text(json.dumps(
        dict(first_cst=cfg["POST_BEGIN_DATE"], last_cst=cfg["POST_END_DATE"],
             checked_files=inputs, missing_files=missing, raw_layer_counts=sorted(raw_layers)), indent=2) + "\n")
    if missing:
        raise IncompleteCase(f"{len(missing)} ACONC/APMDIAG files missing; first: {missing[0]}. "
                             f"See {work / 'input_check.json'}")

    # COMBINE 会读取首尾两个不完整 UTC 日的气象文件，也要覆盖跨月日期。
    met_layers = set()
    utc_day = first - timedelta(days=1)
    while utc_day <= last:
        for prefix in ("METCRO3D", "METCRO2D"):
            require_readable(Path(cfg["MET_PATH"]) / f"{prefix}_{utc_day:%Y%j}")
        with Dataset(Path(cfg["MET_PATH"]) / f"METCRO3D_{utc_day:%Y%j}") as ds:
            met_layers.add(len(ds.dimensions["LAY"]))
        utc_day += timedelta(days=1)
    run_post.validate_layer_counts(cfg, raw_layers, met_layers)
    plan.update(raw_layer_counts=sorted(raw_layers), metcro3d_layer_counts=sorted(met_layers))
    project = Path(cfg["CCTM_WORKDIR"]).parent.parent
    require_readable(project / "config_cmaq.csh")
    executable = project / f"POST/combine/scripts/BLD_combine_{cfg['VRSN']}_intel/combine_{cfg['VRSN']}.exe"
    if not os.access(executable, os.X_OK):
        raise PermissionError(f"COMBINE is not executable: {executable}")
    for program in ("ncks", "ncrcat"):
        result = subprocess.run([program, "--version"], text=True, capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError(f"{program} cannot start: {(result.stderr or result.stdout).strip()}")

    for target in (Path(plan["post"]), Path(plan["merged"])):
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"Recovery target already exists: {target}")
        ancestor = target.parent
        while not ancestor.exists():
            ancestor = ancestor.parent
        if not ancestor.is_dir() or not os.access(ancestor, os.W_OK | os.X_OK):
            raise PermissionError(f"Recovery output parent is not writable/searchable: {ancestor}")
    print(f"Input check passed: {len(inputs)} segment files; CST {first:%Y-%m-%d} to {last:%Y-%m-%d}",
          flush=True)


def command_failure(error, scripts):
    """把子进程日志带回批次日志，避免只看到外层退出码。"""
    names = {Path(str(arg)).name for arg in error.cmd} if isinstance(error.cmd, (list, tuple)) else set()
    logfile = None
    if "0_run_post_script.csh" in names:
        logfile = scripts / "combine_extract.log"
    elif "4_convert2daily.py" in names:
        logfile = scripts / "daily.log"
    if logfile is None or not logfile.is_file():
        return str(error), None
    with logfile.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - 16384))
        tail = "\n".join(stream.read().decode("utf-8", errors="replace").splitlines()[-60:])
    return f"{error}\nFull log: {logfile}\nLast log lines:\n{tail}", str(logfile)


def execute(scripts, plan):
    # 不调用原 execute 的旧计划/清理入口；这里仅操作本次补提取新建的目录。
    # 不依赖旧 .icrb_run 标记中的服务器路径，输入可读且完整即可补提取。
    cfg = plan["config"]
    if cfg["CLEANUP_CCTM_OUTPUT"] != "F" or plan["mode"] != "recovery":
        raise ValueError("Recovery must retain original CCTM files")
    Path(plan["post"]).mkdir(parents=True, exist_ok=False)
    plan["status"] = "running"
    run_post.save_plan(scripts, plan)
    print("Recovery 1/4: merge UTC segments", flush=True)
    _, merged_files = run_post.merge_utc_segments(plan)
    run_post.select_layer_inputs(scripts, plan, merged_files)
    print("Recovery 2/4: COMBINE and species extraction", flush=True)
    run_post.run(["csh", str(scripts / "0_run_post_script.csh")], scripts, scripts / "combine_extract.log")
    run_post.annotate_layer_products(plan)
    first, last = [datetime.strptime(cfg[key], "%Y-%m-%d")
                   for key in ("POST_BEGIN_DATE", "POST_END_DATE")]
    ndays = (last - first).days + 1
    if cfg["KEEP_18SPECIES_ONLY"] == "T":
        names = run_post.selected_species(Path(cfg["POST_TEMPLATE_FILE"]), cfg["INCLUDE_WRF"] == "T")
    else:
        with Dataset(plan["hourly"]) as ds:
            names = [name for name, var in ds.variables.items()
                     if var.dimensions == ("TSTEP", "LAY", "ROW", "COL")]
    run_post.check_hourly(plan["hourly"], first - timedelta(hours=8), ndays, names)
    print("Recovery 3/4: CST daily conversion and numeric validation", flush=True)
    view = run_post.convert_daily(scripts, plan, names) if cfg["CONVERT2DAILY"] == "T" else None
    plan.update(status="validated", hourly_records=ndays * 24, daily_records=ndays if view else 0)
    run_post.save_plan(scripts, plan)
    print("Recovery 4/4: remove newly generated intermediates", flush=True)
    count = run_post.cleanup_validated_outputs(scripts, plan, [], [], None)
    run_post.cleanup_layer_inputs(plan)
    shutil.rmtree(plan["merged"])
    if view:
        shutil.rmtree(view.parent)
    plan.update(status="complete", cleaned_files=count, original_cctm_files_retained=True)
    run_post.save_plan(scripts, plan)
    print(f"Recovery complete: {plan['post']}; {ndays} CST days; original CCTM files retained", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path, help="本次独立日志目录，由批量入口创建")
    parser.add_argument("case_root", type=Path, help="已有情景原始输出根目录")
    parser.add_argument("--dry-run", action="store_true", help="检查输入和依赖，生成计划，不执行后处理")
    args = parser.parse_args()
    work, root = args.work.absolute(), args.case_root.absolute()
    work.mkdir(parents=True, exist_ok=True)
    scripts, plan = None, None
    try:
        scripts, plan = recovery_plan(work, root)
        preflight(work, plan)
        run_post.save_plan(scripts, plan)
        print(f"Recovery layer: configured LAYER={plan['config']['LAYER']}; "
              f"raw={plan['raw_layer_counts']}; METCRO3D={plan['metcro3d_layer_counts']}", flush=True)
        if args.dry_run:
            plan["status"] = "checked"
            run_post.save_plan(scripts, plan)
            status = "checked"
            print(f"Dry-run complete. Planned results: {plan['post']}", flush=True)
        else:
            execute(scripts, plan)
            status = "complete"
        write_result(work, status=status, case_root=str(root), post=plan["post"],
                     hourly=plan["hourly"], daily=plan["daily"] if plan["config"]["CONVERT2DAILY"] == "T" else None)
        return 0
    except Exception as error:
        incomplete = isinstance(error, IncompleteCase)
        status = "skipped_incomplete" if incomplete else "failed"
        message, logfile = str(error), None
        if scripts is not None and isinstance(error, subprocess.CalledProcessError):
            message, logfile = command_failure(error, scripts)
        if plan is not None:
            plan.update(status=status, error=message, command_log=logfile)
            run_post.save_plan(scripts, plan)
        write_result(work, status=status, case_root=str(root), error=message, command_log=logfile,
                     post=plan["post"] if plan else None)
        print(f"{'SKIP' if incomplete else 'ERROR'}: {message}\nOriginal CCTM files retained.", file=sys.stderr)
        return 2 if incomplete else 1


if __name__ == "__main__":
    sys.exit(main())
