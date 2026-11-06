#!/usr/bin/env python3
"""复用原后处理；只适配 UTC 分段拼接、CST 日统计与校验后清理。

prepare WORK CASE_ROOT：保存配置、生成原版后处理脚本的本次副本。
run WORK：按保存的计划依次执行；出错时保留模型原始数据。
本文件没有用户配置默认值，全部读取管理器传入的 cctm_config.csh 设置。
"""
from datetime import datetime, timedelta
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np
from netCDF4 import Dataset


def io_time(day, clock):
    return datetime.strptime(str(int(day)), "%Y%j") + timedelta(
        hours=int(clock) // 10000, minutes=int(clock) // 100 % 100, seconds=int(clock) % 100)


def check_time(path, start, hours, flags_required=False):
    with Dataset(path) as ds:
        if len(ds.dimensions["TSTEP"]) != hours:
            raise ValueError(f"{path}: expected {hours} hourly records")
        if io_time(ds.SDATE, ds.STIME) != start or int(ds.TSTEP) != 10000:
            raise ValueError(f"{path}: incorrect hourly start/step")
        if "TFLAG" in ds.variables:
            flags = ds["TFLAG"][:]
            expected = np.array([[int((start + timedelta(hours=i)).strftime("%Y%j")),
                                  int((start + timedelta(hours=i)).strftime("%H%M%S"))]
                                 for i in range(hours)])[:, None, :]
            if np.ma.getmaskarray(flags).any() or not np.all(flags == expected):
                raise ValueError(f"{path}: missing/duplicate/misaligned timestamps")
        elif flags_required:
            raise ValueError(f"{path}: TFLAG is required on raw CMAQ output")


def complete(values):
    return (not np.ma.getmaskarray(values).any()
            and np.isfinite(values).all() and (np.abs(values) < 1e30).all())


def check_hourly(path, start, ndays, names):
    check_time(path, start, ndays * 24)
    with Dataset(path) as ds:
        for name in names:
            var = ds[name]
            if var.dimensions != ("TSTEP", "LAY", "ROW", "COL"):
                raise ValueError(f"{path}: unexpected dimensions for {name}")
            for i in range(ndays):
                if not complete(var[i * 24:(i + 1) * 24]):
                    raise ValueError(f"{path}: missing/nonfinite {name} on day {i + 1}")
        if str(ds["O3"].units).strip().lower() not in ("ppb", "ppbv"):
            raise ValueError("Expected COMBINE O3 in ppb/ppbv for the existing daily algorithm")


def check_daily(hourly, daily, start_cst, ndays, names):
    with Dataset(hourly) as src, Dataset(daily) as dst:
        if (len(dst.dimensions["TSTEP"]) != ndays or len(dst.dimensions["LAY"]) != 1
                or int(dst.SDATE) != int(start_cst.strftime("%Y%j"))
                or int(dst.STIME) != 0 or int(dst.TSTEP) != 240000):
            raise ValueError("Daily output must contain exactly the requested CST days")
        for name in names + ["O3_MDA8", "O3_MDA8_CN"]:
            if not complete(dst[name][:]):
                raise ValueError(f"Daily {name} has missing/nonfinite values")
        # Preserve the existing algorithm: 17 within-day 8-hour windows, surface layer.
        for i in range(ndays):
            ozone = src["O3"][i * 24:(i + 1) * 24, 0]
            expected = np.max([ozone[j:j + 8].mean(axis=0) for j in range(17)], axis=0)
            if not np.allclose(dst["O3_MDA8"][i, 0], expected, rtol=2e-6, atol=2e-5):
                raise ValueError(f"CST MDA8 time alignment failed on day {i + 1}")
            for name in names:
                mean = src[name][i * 24:(i + 1) * 24, 0].mean(axis=0)
                if not np.allclose(dst[name][i, 0], mean, rtol=2e-6, atol=2e-5):
                    raise ValueError(f"CST daily mean alignment failed: {name}, day {i + 1}")


def replace_setting(text, name, value):
    text, n = re.subn(r"^setenv " + name + r"\b[^\n]*$",
                      lambda _: f'setenv {name} "{value}"', text, flags=re.M)
    if n != 1:
        raise ValueError(f"Post template: expected one setting for {name}, found {n}")
    return text


def run(command, cwd, log):
    with log.open("x") as stream:
        subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, check=True)


def save_plan(work, plan):
    (work / "post_plan.json").write_text(json.dumps(plan, indent=2) + "\n")


def selected_species(template, include_wrf):
    """物种清单仍以原版提取脚本为准，避免两处维护。"""
    text = (template.parent / "2_extract_18species_by_nco.csh").read_text()
    names = []
    for group in (["base_vars", "wrf_vars"] if include_wrf else ["base_vars"]):
        match = re.search(r"^\s*set " + group + r"\s*=\s*\(([^)]+)\)", text, re.M)
        if not match:
            raise ValueError(f"Cannot read {group} from shared extraction script")
        names.extend(match[1].split())
    return names


def configured_layer(cfg):
    value = str(cfg.get("LAYER", ""))
    if not re.fullmatch(r"-1|[1-9][0-9]*", value):
        raise ValueError("Set LAYER in the configuration: -1 for all layers, or a positive layer number")
    return int(value)


def layer_label(cfg):
    layer = configured_layer(cfg)
    return "all_layers" if layer == -1 else f"layer_{layer}"


def validate_layer_counts(cfg, raw_layers, met_layers):
    layer = configured_layer(cfg)
    if layer == -1:
        if len(raw_layers) != 1 or raw_layers != met_layers:
            raise ValueError(f"LAYER=-1 requires matching ACONC/APMDIAG and METCRO3D layers; "
                             f"raw={sorted(raw_layers)}, METCRO3D={sorted(met_layers)}. "
                             "For surface-only output, set LAYER=1 in the configuration")
    elif any(count < layer for count in raw_layers | met_layers):
        raise ValueError(f"LAYER={layer} exceeds available layers: "
                         f"raw={sorted(raw_layers)}, METCRO3D={sorted(met_layers)}")


def validate_layer_inputs(plan):
    cfg = plan["config"]
    first, last = [datetime.strptime(cfg[key], "%Y-%m-%d") for key in ("POST_BEGIN_DATE", "POST_END_DATE")]
    raw_layers, met_layers = set(), set()
    day = first
    while day <= last:
        for segment, utc in (("seg01", day - timedelta(hours=8)), ("seg02", day)):
            folder = Path(plan["case_root"]) / f"{day:%Y%m%d}/{segment}/{cfg['DOMAIN']}/{utc:%Y/%m}"
            for prefix in ("CCTM_ACONC", "CCTM_APMDIAG"):
                with Dataset(folder / f"{prefix}_{cfg['APPL']}_{utc:%Y%j}.nc") as ds:
                    raw_layers.add(len(ds.dimensions["LAY"]))
        day += timedelta(days=1)
    day = first - timedelta(days=1)
    while day <= last:
        with Dataset(Path(cfg["MET_PATH"]) / f"METCRO3D_{day:%Y%j}") as ds:
            met_layers.add(len(ds.dimensions["LAY"]))
        day += timedelta(days=1)
    validate_layer_counts(cfg, raw_layers, met_layers)


def annotate_layer_products(plan):
    cfg = plan["config"]
    layer = configured_layer(cfg)
    day = datetime.strptime(cfg["POST_BEGIN_DATE"], "%Y-%m-%d")
    utc = day - timedelta(hours=8)
    source = Path(plan["case_root"]) / f"{day:%Y%m%d}/seg01/{cfg['DOMAIN']}/{utc:%Y/%m}/CCTM_ACONC_{cfg['APPL']}_{utc:%Y%j}.nc"
    with Dataset(source) as ds:
        levels = ds.VGLVLS[:]
    for filename in set(plan[key] for key in ("combined", "hourly")):
        with Dataset(filename, "r+") as ds:
            ds.post_layer = layer
            if layer > 0:
                ds.NLAYS = 1
                ds.VGLVLS = levels[layer - 1:layer + 1]


def prepare(work, case_root):
    """先固化配置与脚本，不创建模型输出、不启动后处理。"""
    keys = ("CASE_NAME START_DATE END_DATE POST_BEGIN_DATE POST_END_DATE DOMAIN APPL VRSN PROC MECH "
            "CCTM_WORKDIR INPDIR MET_PATH POST_TEMPLATE_FILE POST_SPEC_FILE COMBINE_DIR KEEP_18SPECIES_ONLY "
            "INCLUDE_WRF KEEP_COMBINE_FILE CONVERT2DAILY CLEANUP_CCTM_OUTPUT PYTHON_CMD LAYER").split()
    if "LAYER" not in os.environ:
        configured_layer({})
    cfg = {key: os.environ[key] for key in keys}
    label = layer_label(cfg)
    for key in ("KEEP_18SPECIES_ONLY", "INCLUDE_WRF", "KEEP_COMBINE_FILE", "CONVERT2DAILY", "CLEANUP_CCTM_OUTPUT"):
        if cfg[key] not in ("T", "F"):
            raise ValueError(f"{key} must be T or F")
    first, last = [datetime.strptime(cfg[key], "%Y-%m-%d") for key in ("POST_BEGIN_DATE", "POST_END_DATE")]
    if not cfg["START_DATE"] <= cfg["POST_BEGIN_DATE"] <= cfg["POST_END_DATE"] <= cfg["END_DATE"]:
        raise ValueError("Post date range must lie within simulated CST dates")
    for key in ("CASE_NAME", "DOMAIN", "APPL", "VRSN", "MECH"):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", cfg[key]):
            raise ValueError(f"Invalid {key}: {cfg[key]}")
    for key in ("CCTM_WORKDIR", "INPDIR", "MET_PATH", "POST_TEMPLATE_FILE", "POST_SPEC_FILE", "COMBINE_DIR"):
        if cfg[key] and not re.fullmatch(r"[\w./+-]+", cfg[key]):
            raise ValueError(f"Shared CSH scripts require a path without spaces/metacharacters: {key}")
    for program in ("csh", "ncks", "ncrcat"):
        if not shutil.which(program):
            raise ValueError(f"Missing post dependency: {program}")
    if cfg["CONVERT2DAILY"] == "T" and not importlib.util.find_spec("esil"):
        raise ValueError("Daily conversion requires esil in PYTHON_CMD")
    project = Path(cfg["CCTM_WORKDIR"]).parent.parent
    combine = project / f'POST/combine/scripts/BLD_combine_{cfg["VRSN"]}_intel/combine_{cfg["VRSN"]}.exe'
    for path in (project / "config_cmaq.csh", combine, Path(cfg["POST_SPEC_FILE"])):
        if not path.is_file():
            raise ValueError(f"Missing shared post dependency: {path}")

    work.mkdir(parents=True, exist_ok=False)
    post = Path(cfg["COMBINE_DIR"]) / case_root.name if cfg["COMBINE_DIR"] else case_root / "post"
    merged = case_root / "merged"
    utc_first = first - timedelta(days=1)
    runid = f'{cfg["VRSN"]}_{cfg["DOMAIN"]}_{cfg["CASE_NAME"]}_icrb_cst00_{cfg["APPL"]}'
    stem = f"COMBINE_ACONC_{runid}_{label}_{utc_first:%Y-%m-%d}_{last:%Y-%m-%d}"
    suffix = "_18species" if cfg["KEEP_18SPECIES_ONLY"] == "T" else ""
    plan = dict(config=cfg, case_root=str(case_root), merged=str(merged), post=str(post),
                combined=str(post / (stem + ".nc")), hourly=str(post / (stem + suffix + ".nc")),
                daily=str(post / f"Daily_COMBINE_ACONC_{runid}_{label}_{first:%Y-%m-%d}_{last:%Y-%m-%d}{suffix}_CST.nc"),
                status="prepared")
    # METCRO2D 只有一层；指定更高层时先把三维输入裁成该层的副本，COMBINE 再读第 1 层。
    if configured_layer(cfg) > 1:
        plan.update(combine_inputs=str(work / "selected_inputs"), selected_met=str(work / "selected_met"))
    copy_post_scripts(work, plan)
    save_plan(work, plan)
    print(f"Post prepared: {work}/post_plan.json", flush=True)


def copy_post_scripts(work, plan):
    """复用 0/1/2/4；只改生成副本中的路径、开关与跨月输入目录。"""
    cfg = plan["config"]
    template = Path(cfg["POST_TEMPLATE_FILE"])
    text = template.read_text()
    text = re.sub(r"^set script_path =.*$", lambda _: f'set script_path = "{work}"', text, flags=re.M)
    text = text.replace("set compiler = intel", f'setenv CCTM_WORKDIR "{cfg["CCTM_WORKDIR"]}"\nset compiler = intel', 1)
    settings = {key: cfg[key] for key in ("VRSN", "PROC", "MECH", "APPL", "DOMAIN", "INPDIR", "KEEP_18SPECIES_ONLY", "INCLUDE_WRF")}
    first = datetime.strptime(cfg["POST_BEGIN_DATE"], "%Y-%m-%d") - timedelta(days=1)
    settings.update(CASE_NAME=cfg["CASE_NAME"] + "_icrb_cst00", LAYER=str(configured_layer(cfg)),
                    BEGIN_DATE=f"{first:%Y-%m-%d}", END_DATE=cfg["POST_END_DATE"],
                    CCTMOUTDIR_ROOT=plan.get("combine_inputs", plan["merged"]), COMBINE_DIR=plan["post"],
                    OUTPUT_COMBINE_ACONC_FILE="T", OUTPUT_COMBINE_DEP_FILE="F",
                    OUTPUT_BY_YEARMONTH="F", KEEP_COMBINE_FILE="T", CLEANUP_CCTM_OUTPUT="F",
                    TSHIFT="F", CONVERT2DAILY="F", OUTPUT_DAILY_MAP="F", OUTPUT_IC="F", OUTPUT_BC="F", COPY_SPEC_DEF="F")
    # 原程序的提前删除和日转换在此关闭，由下方校验通过后统一执行。
    for key, value in settings.items():
        text = replace_setting(text, key, value)
    (work / "0_run_post_script.csh").write_text(text)
    for filename in ("1_run_combine_aconc.csh", "2_extract_18species_by_nco.csh", "4_convert2daily.py"):
        shutil.copy2(template.parent / filename, work / filename)
    combine = work / "1_run_combine_aconc.csh"
    # 使用共享仓库的物种定义副本，不向 CMAQ 安装目录覆盖任何文件。
    spec = work / Path(cfg["POST_SPEC_FILE"]).name
    shutil.copy2(cfg["POST_SPEC_FILE"], spec)
    spec_text, count = re.subn(r"(?mi)^[ \t]*#layer[ \t]+[-+]?\d+[^\n]*$",
                               f"#layer         {1 if configured_layer(cfg) > 0 else -1}", spec.read_text())
    if count > 1:
        raise ValueError(f"{spec}: multiple active #layer settings")
    if count == 0:
        spec_text = f"#layer         {1 if configured_layer(cfg) > 0 else -1}\n" + spec_text
    spec.write_text(spec_text)
    text = combine.read_text()
    text, count = re.subn(r"^(\s*set YYYYJJJ =[^\n]*)$", lambda m: m[1] +
                         '\n   setenv CCTMOUTDIR ${CCTMOUTDIR_ROOT}/${DOMAIN}/${YYYY}/${MM}', text, flags=re.M)
    if count != 1:
        raise ValueError("Cannot locate COMBINE daily path setting")
    text = re.sub(r"^\s*setenv METDIR\s+.*$", lambda _: f'setenv METDIR "{plan.get("selected_met", cfg["MET_PATH"])}"', text, flags=re.M)
    text = re.sub(r"^\s*setenv SPEC_CONC\s+.*$", lambda _: f'setenv SPEC_CONC "{spec}"', text, flags=re.M)
    combine.write_text(text)
    for path in work.glob("*.csh"):
        subprocess.run(["csh", "-n", str(path)], check=True)


def merge_utc_segments(plan):
    """每个 UTC 日依次接 seg02(00–16)、次个 CST 日的 seg01(16–24)。"""
    cfg = plan["config"]
    root, merged = Path(plan["case_root"]), Path(plan["merged"])
    first, last = [datetime.strptime(cfg[key], "%Y-%m-%d") for key in ("POST_BEGIN_DATE", "POST_END_DATE")]
    ndays = (last - first).days + 1
    raw_files, merged_files = set(), []
    merged.mkdir(exist_ok=False)
    for index in range(ndays + 1):
        utc_day = first - timedelta(days=1) + timedelta(days=index)
        pieces = []
        if index > 0:
            pieces.append((utc_day, "seg02", utc_day, 16))
        if index < ndays:
            pieces.append((utc_day + timedelta(days=1), "seg01", utc_day + timedelta(hours=16), 8))
        target_dir = merged / f'{cfg["DOMAIN"]}/{utc_day:%Y/%m}'
        target_dir.mkdir(parents=True, exist_ok=True)
        for prefix in ("CCTM_ACONC", "CCTM_APMDIAG"):
            sources = []
            for local_day, segment, start, hours in pieces:
                folder = root / f'{local_day:%Y%m%d}/{segment}/{cfg["DOMAIN"]}/{utc_day:%Y/%m}'
                path = folder / f'{prefix}_{cfg["APPL"]}_{utc_day:%Y%j}.nc'
                if not path.resolve().is_relative_to(root.resolve()):
                    raise ValueError(f"Segment input points outside this run: {path}")
                check_time(path, start, hours, flags_required=True)
                sources.append(path)
                raw_files.update(p for p in folder.iterdir() if p.is_file() and not p.is_symlink()
                                 and p.name.startswith("CCTM_") and p.suffix != ".cfg"
                                 and not p.name.startswith("CCTM_CGRID"))
            output = target_dir / sources[0].name
            if len(sources) == 1:
                output.symlink_to(sources[0])
            else:
                subprocess.run(["ncrcat", *map(str, sources), str(output)], check=True)
            check_time(output, pieces[0][2], sum(p[3] for p in pieces), flags_required=True)
            merged_files.append(output)
    return sorted(raw_files), merged_files


def select_layer_inputs(work, plan, merged_files):
    """指定层大于 1 时，三维输入先裁成单层副本，保留 METCRO2D 的地面值。"""
    cfg = plan["config"]
    layer = configured_layer(cfg)
    if layer <= 1:
        return
    selected = Path(plan["combine_inputs"])
    met = Path(plan["selected_met"])
    selected.mkdir(exist_ok=False)
    met.mkdir(exist_ok=False)

    def crop(source, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ncks", "-d", f"LAY,{layer - 1},{layer - 1}", str(source), str(target)], check=True)
        with Dataset(source) as src:
            levels = src.VGLVLS[layer - 1:layer + 1]
        with Dataset(target, "r+") as dst:
            dst.NLAYS = 1
            dst.VGLVLS = levels
            dst.post_layer = layer

    for source in merged_files:
        crop(source, selected / source.relative_to(Path(plan["merged"])))
    first, last = [datetime.strptime(cfg[key], "%Y-%m-%d") for key in ("POST_BEGIN_DATE", "POST_END_DATE")]
    day = first - timedelta(days=1)
    while day <= last:
        filename = f"METCRO3D_{day:%Y%j}"
        crop(Path(cfg["MET_PATH"]) / filename, met / filename)
        filename = f"METCRO2D_{day:%Y%j}"
        (met / filename).symlink_to(Path(cfg["MET_PATH"]) / filename)
        day += timedelta(days=1)


def cleanup_layer_inputs(plan):
    for key in ("combine_inputs", "selected_met"):
        if key in plan:
            shutil.rmtree(plan[key])


def convert_daily(work, plan, names):
    """按 CST00 对齐日统计；全层产品取地面层，单层产品取配置指定的层。"""
    cfg = plan["config"]
    hourly = Path(plan["hourly"])
    first, last = [datetime.strptime(cfg[key], "%Y-%m-%d") for key in ("POST_BEGIN_DATE", "POST_END_DATE")]
    ndays = (last - first).days + 1
    view_dir = work / "daily_input_cst"
    view_dir.mkdir()
    view = view_dir / hourly.name
    subprocess.run(["ncks", "-d", "LAY,0,0", str(hourly), str(view)], check=True)
    with Dataset(view, "r+") as ds:
        ds.SDATE, ds.STIME, ds.NLAYS = int(first.strftime("%Y%j")), 0, 1
        ds.VGLVLS = ds.VGLVLS[:2]
        ds.time_zone = "CST (UTC+08:00); temporary daily-conversion view"
        if "TFLAG" in ds.variables:
            for i in range(ndays * 24):
                instant = first + timedelta(hours=i)
                ds["TFLAG"][i] = [int(instant.strftime("%Y%j")), int(instant.strftime("%H%M%S"))]
    run([cfg["PYTHON_CMD"], str(work / "4_convert2daily.py"), str(view),
         cfg["POST_BEGIN_DATE"], cfg["POST_END_DATE"], "0"], work, work / "daily.log")
    daily_view = view_dir / ("Daily_" + hourly.name)
    with Dataset(daily_view, "r+") as ds:
        ds.SDATE, ds.STIME, ds.TSTEP, ds.NLAYS = int(first.strftime("%Y%j")), 0, 240000, 1
        ds.VGLVLS = ds.VGLVLS[:2]
        ds.NVARS = len(ds.variables)
        ds.setncattr("VAR-LIST", "".join(f"{name:<16}" for name in ds.variables))
        ds.time_zone = "CST (UTC+08:00)"
        ds.source_hourly_file = str(hourly)
        ds.source_layer = max(1, configured_layer(cfg))
    check_daily(hourly, daily_view, first, ndays, names)
    shutil.move(str(daily_view), plan["daily"])
    return view


def cleanup_validated_outputs(work, plan, raw_files, merged_files, view):
    """所有结果验证通过后，才按两个清理开关逐文件删除并记录清单。"""
    cfg = plan["config"]
    candidates = []
    if cfg["CLEANUP_CCTM_OUTPUT"] == "T":
        candidates.extend(raw_files + merged_files)
        if view:
            candidates.append(view)
    if cfg["KEEP_COMBINE_FILE"] == "F" and plan["combined"] != plan["hourly"]:
        candidates.append(Path(plan["combined"]))
    # 目录必须属于本次新建的结果或生成目录；不对父目录或其它情景执行清理。
    roots = [Path(plan[key]).resolve() for key in ("case_root", "post")] + [work.resolve()]
    for path in candidates:
        if not any(path.parent.resolve().is_relative_to(root) for root in roots):
            raise ValueError(f"Refusing cleanup outside this run: {path}")
    for path in candidates:
        path.unlink()
    (work / "cleaned_files.json").write_text(json.dumps(list(map(str, candidates)), indent=2) + "\n")
    return len(candidates)


def execute(work):
    plan = json.loads((work / "post_plan.json").read_text())
    if plan["status"] != "prepared":
        raise ValueError("This post plan has already been started; inspect its logs before retrying")
    cfg = plan["config"]
    root = Path(plan["case_root"])
    marker = root / ".icrb_run"
    if root.is_symlink() or not marker.is_file() or marker.read_text().strip() != str(root):
        raise ValueError("Missing current-run marker; refusing post/cleanup")
    validate_layer_inputs(plan)
    Path(plan["post"]).mkdir(parents=True, exist_ok=False)
    plan["status"] = "running"
    save_plan(work, plan)

    print("Post 1/4: merge UTC segments", flush=True)
    raw_files, merged_files = merge_utc_segments(plan)
    select_layer_inputs(work, plan, merged_files)
    (work / "raw_cleanup_candidates.json").write_text(json.dumps(list(map(str, raw_files)), indent=2) + "\n")
    print("Post 2/4: run shared COMBINE and species extraction", flush=True)
    run(["csh", str(work / "0_run_post_script.csh")], work, work / "combine_extract.log")
    annotate_layer_products(plan)
    first, last = [datetime.strptime(cfg[key], "%Y-%m-%d") for key in ("POST_BEGIN_DATE", "POST_END_DATE")]
    ndays = (last - first).days + 1
    if cfg["KEEP_18SPECIES_ONLY"] == "T":
        names = selected_species(Path(cfg["POST_TEMPLATE_FILE"]), cfg["INCLUDE_WRF"] == "T")
    else:
        with Dataset(plan["hourly"]) as ds:
            names = [name for name, var in ds.variables.items() if var.dimensions == ("TSTEP", "LAY", "ROW", "COL")]
    check_hourly(plan["hourly"], first - timedelta(hours=8), ndays, names)
    print("Post 3/4: CST daily conversion and numeric validation", flush=True)
    view = convert_daily(work, plan, names) if cfg["CONVERT2DAILY"] == "T" else None
    plan.update(status="validated", hourly_records=ndays * 24, daily_records=ndays if view else 0)
    save_plan(work, plan)
    print("Post 4/4: configured cleanup", flush=True)
    count = cleanup_validated_outputs(work, plan, raw_files, merged_files, view)
    cleanup_layer_inputs(plan)
    plan.update(status="complete", cleaned_files=count)
    save_plan(work, plan)
    print(f'Post complete: {plan["post"]}; {ndays} CST days; cleaned {count} files', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("work", type=Path)
    prep.add_argument("case_root", type=Path)
    commands.add_parser("run").add_argument("work", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.work.absolute(), args.case_root.absolute())
    else:
        execute(args.work.absolute())


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}. Raw model data are retained unless validation completed.", file=sys.stderr)
        sys.exit(1)
