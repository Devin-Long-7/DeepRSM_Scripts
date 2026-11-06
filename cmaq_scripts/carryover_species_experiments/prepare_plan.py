#!/usr/bin/env python3
"""运行计划准备与NetCDF检查工具。

只负责读取已由CSH加载的配置、校验输入、渲染分段脚本及检查输出。
批次循环和CMAQ启动全部由batch_run.csh执行。"""

# 延迟解析类型注解，兼容服务器Python 3.8/3.9。
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta
import os
import argparse
import csv
import json
import re
import subprocess
import sys
import tempfile
import shutil
from prepare_ic import validate, prepare, CASES, digest, stamp
import netCDF4 as nc

HERE = Path(__file__).resolve().parent


def load_config(path: Path) -> dict:
    """读取CSH已经加载的环境参数，将相对路径按配置文件目录解析。"""
    config = {"config_source": str(path.resolve())}
    path_keys = {
        "template": "TEMPLATE_FILE",
        "output_root": "OUTDIR_BASE",
        "inputs_csv": "INPUT_FIELDS_FILE",
        "boundary_file": "BOUNDARY_FILE",
    }
    for key, environment_name in path_keys.items():
        configured_path = Path(os.environ[environment_name])
        config[key] = str(
            configured_path
            if configured_path.is_absolute()
            else (path.parent / configured_path).resolve()
        )
    numeric_keys = {
        "OMP_NUM_THREADS": int,
        "NPCOL": int,
        "NPROW": int,
        "NZ": int,
        "N_EMIS_GR": int,
        "CTM_MAXSYNC": int,
        "CTM_MINSYNC": int,
        "SIGMA_SYNC_TOP": float,
        "CTM_ADV_CFL": float,
    }
    aliases = {
        "BCpath": "BC_PATH",
        "METpath": "MET_PATH",
        "epath": "AV_EMIS_DIR",
        "epath2": "BV_EMIS_DIR",
        "OCEAN_1": "OCEAN_1_PATH",
    }
    config["cmaq"] = {}
    for key in [
        "CCTM_WORKDIR",
        "MPI_BIN",
        "I_MPI_FABRICS",
        "OMP_NUM_THREADS",
        "VRSN",
        "PROC",
        "MECH",
        "DOMAIN",
        "APPL",
        "BLD",
        "INPDIR",
        "NPCOL",
        "NPROW",
        "GRID_NAME",
        "GRIDDESC",
        "NZ",
        "CONC_SPCS",
        "AVG_CONC_SPCS",
        "CONC_BLEV_ELEV",
        "ACONC_BLEV_ELEV",
        "CTM_MAXSYNC",
        "CTM_MINSYNC",
        "SIGMA_SYNC_TOP",
        "CTM_ADV_CFL",
        "APMDIAG_BLEV_ELEV",
        "BCpath",
        "METpath",
        "CMAQ_MASKS",
        "OCEAN_1",
        "epath",
        "epath2",
        "N_EMIS_GR",
        "EMIS_MONTH",
        "EM_AV_PREFIX",
        "MEGAN_PREFIX",
        "MEGAN_SUFFIX",
    ]:
        value = os.environ[aliases.get(key, key)]
        config["cmaq"][key] = numeric_keys[key](value) if key in numeric_keys else value
    config["runs"] = os.environ["EXPERIMENT_CASES"].split()
    config["dates"] = os.environ["TARGET_DATES"].split()
    config["auto_post"] = os.environ["ENABLE_POST_PROCESS"].upper() == "Y"
    return config


def read_species_groups() -> dict[str, list[str]]:
    """从cctm_config.csh的环境变量读取物种分组，不另设分组配置文件。"""
    return {
        key: os.environ["GROUP_" + key.upper()].split()
        for key in ["NO2", "other_N", "OVOC", "O3"]
    }


def shell_quote(value: str | int | float) -> str:
    """为生成的 CSH 参数添加引号，拒绝不能安全表示的特殊字符。"""
    value = str(value)
    if re.search('[\\n\\r"`!\\\\]', value):
        raise ValueError(f"Unsupported CSH config value: {value}")
    return '"' + value + '"'


def emission_dates(month: str) -> dict[str, str]:
    """计算代表月的首个周五、周六和周日，沿用原 CMAQ 排放日期规则。"""
    first = datetime.strptime(month + "-01", "%Y-%m-%d")
    first_friday = first + timedelta(days=(4 - first.weekday()) % 7)
    return {
        key: (first_friday + timedelta(days=day_offset)).strftime("%Y%j")
        for key, day_offset in [("EMIS_OTH", 0), ("EMIS_SAT", 1), ("EMIS_SUN", 2)]
    }


def render(
    config: dict,
    task: dict,
    segment_number: int,
    output_root: Path,
    emissctrl_path: Path,
) -> tuple[str, Path, Path, datetime]:
    """从 CST00 模板生成一个运行段，返回脚本文本、输出目录和重启路径。

    seg01 从前日 UTC16 开始8小时；seg02 接续自己的 seg01 再运行16小时。"""
    cmaq_config = config["cmaq"]
    cst_day = datetime.fromisoformat(task["cst_date"])
    utc_day = cst_day - timedelta(days=1) if segment_number == 1 else cst_day
    previous_julian_day = (cst_day - timedelta(days=1)).strftime("%Y%j")
    segment_output = (
        output_root
        / task["scenario"]
        / task["cst_date"]
        / task["case"]
        / f"seg{segment_number:02d}"
    )
    restart_path = (
        Path(task["mixed_ic"])
        if segment_number == 1
        else segment_output.parent
        / "seg01"
        / f"CCTM_CGRID_{cmaq_config['APPL']}_{previous_julian_day}.nc"
    )
    values = {token: value for token, value in cmaq_config.items()}
    values.update(emission_dates(cmaq_config["EMIS_MONTH"]))
    values.update(
        CASE_NAME=f"{task['scenario']}_{task['case']}",
        firstday=utc_day.date().isoformat(),
        START_DATE=utc_day.date().isoformat(),
        END_DATE=utc_day.date().isoformat(),
        OUTDIR=str(segment_output),
        RESTART_FILE=str(restart_path),
        STTIME="160000" if segment_number == 1 else "000000",
        NSTEPS="080000" if segment_number == 1 else "160000",
        EMISSCTRL_NML=str(emissctrl_path),
        GR_EMIS_001=cmaq_config["epath"]
        + "/"
        + cmaq_config["EM_AV_PREFIX"]
        + "${EMIS_DATE}",
        GR_EMIS_002=cmaq_config["epath2"]
        + "/"
        + cmaq_config["MEGAN_PREFIX"]
        + "${TODAYJ}"
        + cmaq_config["MEGAN_SUFFIX"],
    )
    text = Path(config["template"]).read_text()
    tokens = set(re.findall("@([A-Za-z0-9_]+)@", text))
    missing = tokens - values.keys()
    if missing:
        raise ValueError(f"Missing template values {missing}")
    for token in tokens:
        text = text.replace(
            "@" + token + "@",
            (
                str(values[token])
                if token in ["NPCOL", "NPROW", "NZ"]
                else shell_quote(values[token])
            ),
        )
    if re.search("@[A-Za-z0-9_]+@", text):
        raise ValueError("Unresolved template tokens")
    if not re.search("^\\s*setenv CTM_ABFLUX N", text, re.M) or not re.search(
        "^\\s*setenv CTM_BIOGEMIS N", text, re.M
    ):
        raise ValueError("Template must disable ABFLUX and inline BIOGEMIS")
    return (text, segment_output, restart_path, utc_day)


def required_inputs(cmaq_config: dict, utc_day: datetime) -> list[Path]:
    """列出一个 UTC 运行日需要的主要模型、排放、边界和气象输入文件。"""
    julian_day = utc_day.strftime("%Y%j")
    representative_dates = emission_dates(cmaq_config["EMIS_MONTH"])
    day_type = (
        "EMIS_SAT"
        if utc_day.weekday() == 5
        else "EMIS_SUN" if utc_day.weekday() == 6 else "EMIS_OTH"
    )
    paths = [
        Path(cmaq_config["BLD"]) / f"CCTM_{cmaq_config['VRSN']}.exe",
        Path(cmaq_config["BLD"]) / f"CCTM_{cmaq_config['VRSN']}.cfg",
        Path(cmaq_config["GRIDDESC"]),
        Path(cmaq_config["CMAQ_MASKS"]),
        Path(cmaq_config["OCEAN_1"]),
        Path(cmaq_config["BCpath"]) / f"BCON_{julian_day}",
        Path(cmaq_config["epath"])
        / (cmaq_config["EM_AV_PREFIX"] + representative_dates[day_type]),
        Path(cmaq_config["epath2"])
        / (cmaq_config["MEGAN_PREFIX"] + julian_day + cmaq_config["MEGAN_SUFFIX"]),
    ]
    paths += [
        Path(cmaq_config["METpath"]) / (name + "_" + julian_day)
        for name in [
            "GRIDBDY2D",
            "GRIDCRO2D",
            "GRIDDOT2D",
            "METBDY3D",
            "METCRO2D",
            "METCRO3D",
            "METDOT3D",
        ]
    ]
    paths += [
        Path(cmaq_config["BLD"]) / name
        for name in [
            f"GC_{cmaq_config['MECH']}.nml",
            f"AE_{cmaq_config['MECH']}.nml",
            f"NR_{cmaq_config['MECH']}.nml",
            f"CSQY_DATA_{cmaq_config['MECH']}",
            "PHOT_OPTICS.dat",
            "OMI_1979_to_2019.dat",
        ]
    ]
    return paths


def validate_output(
    cmaq_config: dict, output_directory: Path, utc_day: datetime, segment_number: int
) -> Path:
    """检查本段输出 CGRID 的内部终止时刻，确认接续场覆盖完整运行时长。"""
    start_time = utc_day.replace(hour=16 if segment_number == 1 else 0)
    end_time = start_time + timedelta(hours=8 if segment_number == 1 else 16)
    julian_day = utc_day.strftime("%Y%j")
    cgrid_path = output_directory / f"CCTM_CGRID_{cmaq_config['APPL']}_{julian_day}.nc"
    with nc.Dataset(cgrid_path) as dataset:
        if stamp(dataset) != end_time:
            raise ValueError(f"Wrong segment end CGRID timestamp: {cgrid_path}")
    return cgrid_path


def build_tasks(config: dict, groups: dict, args: argparse.Namespace) -> list[dict]:
    """读取输入清单，核对全部初始场，并展开为日期×实验配置任务。

    所有任务通过后才允许生成混合IC或启动模拟。"""
    with open(config["inputs_csv"], newline="") as stream:
        rows = list(csv.DictReader(stream))
    if args.dates:
        rows = [row for row in rows if row["cst_date"] in args.dates]
    if not rows:
        raise ValueError("No selected inputs")
    selected_cases = args.cases or config["runs"]
    if (
        not selected_cases
        or len(set(selected_cases)) != len(selected_cases)
        or set(selected_cases) - CASES.keys()
    ):
        raise ValueError("Invalid run list")
    tasks = []
    seen = set()
    errors = []
    for row in rows:
        scenario_date = (row["scenario"], row["cst_date"])
        if scenario_date in seen:
            raise ValueError(f"Duplicate input row {scenario_date}")
        seen.add(scenario_date)
        if not re.fullmatch("[A-Za-z0-9_-]+", row["scenario"]):
            raise ValueError("Unsafe scenario name")
        for field in ["continuous_ic", "reset_ic", "emissctrl_nml"]:
            if not row.get(field):
                errors.append(
                    f"{scenario_date}: fill {field} in {config['inputs_csv']}"
                )
            else:
                input_path = Path(row[field])
                row[field] = str(
                    input_path.resolve()
                    if input_path.is_absolute()
                    else (Path(config["inputs_csv"]).parent / input_path).resolve()
                )
                if not Path(row[field]).is_file():
                    errors.append(f"{scenario_date}: missing {field} {row[field]}")
        if any(
            (
                not row.get(k) or not Path(row[k]).is_file()
                for k in ["continuous_ic", "reset_ic", "emissctrl_nml"]
            )
        ):
            continue
        try:
            validation_info = validate(
                row["continuous_ic"], row["reset_ic"], row["cst_date"], groups
            )
        except Exception as error:
            errors.append(f"{scenario_date}: {error}")
            continue
        if config["cmaq"]["NZ"] != len(validation_info["grid"]["VGLVLS"]) - 1:
            errors.append(f"{scenario_date}: NZ mismatch")
        for case_name in selected_cases:
            tasks.append(dict(row, case=case_name, ic_groups=validation_info))
    if errors:
        raise ValueError("\n".join(errors))
    return tasks


def create_plan(config: dict, groups: dict, tasks: list[dict], dry_run: bool) -> Path:
    """保存配置快照、生成两段脚本和清单，并检查运行依赖。

    干跑也执行本步骤，但不写混合IC、不创建模型结果。"""
    errors = []
    HERE.joinpath("generated").mkdir(exist_ok=True)
    plan_directory = Path(
        tempfile.mkdtemp(prefix="batch_", dir=HERE / "generated")
    ).resolve()
    output_root = Path(config["output_root"]) / plan_directory.name
    (plan_directory / "config_used.json").write_text(json.dumps(config, indent=2))
    shutil.copyfile(config["config_source"], plan_directory / "cctm_config_used.csh")
    (plan_directory / "groups_used.json").write_text(json.dumps(groups, indent=2))
    (plan_directory / "template_used.csh").write_text(
        Path(config["template"]).read_text()
    )
    for task in tasks:
        task_directory = (
            plan_directory / task["scenario"] / task["cst_date"] / task["case"]
        )
        task_directory.mkdir(parents=True)
        task["mixed_ic"] = str(task_directory / "initial.nc")
        emissctrl_path = task_directory / "EmissCtrl.nml"
        shutil.copyfile(task["emissctrl_nml"], emissctrl_path)
        task["emissctrl_sha256"] = digest(emissctrl_path)
        task["segments"] = []
        for segment_number in [1, 2]:
            text, segment_output, restart_path, utc_day = render(
                dict(config, template=str(plan_directory / "template_used.csh")),
                task,
                segment_number,
                output_root,
                emissctrl_path,
            )
            script_path = task_directory / f"seg{segment_number:02d}.csh"
            script_path.write_text(text)
            subprocess.run(
                ["csh", "-n", str(script_path)], check=True, capture_output=True
            )
            task["segments"].append(
                dict(
                    script=str(script_path),
                    output=str(segment_output),
                    restart=str(restart_path),
                    utc_day=utc_day.date().isoformat(),
                    segment=segment_number,
                )
            )
            for path in required_inputs(config["cmaq"], utc_day):
                if not path.is_file():
                    errors.append(f"Missing runtime input: {path}")
    manifest_data = dict(
        config=config,
        tasks=tasks,
        plan_dir=str(plan_directory),
        output_root=str(output_root),
        dry_run=dry_run,
        template_sha256=digest(Path(config["template"])),
    )
    manifest_path = plan_directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2))
    with open(plan_directory / "manifest_readable.tsv", "w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(
            [
                "scenario",
                "CST_date",
                "case",
                "segment",
                "UTC_day",
                "restart",
                "output",
                "script",
            ]
        )
        for task in tasks:
            for segment in task["segments"]:
                writer.writerow(
                    [
                        task["scenario"],
                        task["cst_date"],
                        task["case"],
                        segment["segment"],
                        segment["utc_day"],
                        segment["restart"],
                        segment["output"],
                        segment["script"],
                    ]
                )
    print(
        f"Plan: {manifest_path}\nTasks: {len(tasks)}; segments: {2 * len(tasks)}",
        flush=True,
    )
    if errors:
        raise ValueError(
            "\n".join(sorted(set(errors)))
            + "\nGenerated plan retained; CMAQ was not launched."
        )
    return manifest_path


def write_csh_task_files(manifest_path: Path) -> None:
    """将已核验清单导出为CSH可source的任务文件；不启动任何模拟。"""
    manifest = json.loads(manifest_path.read_text())
    plan_directory = manifest_path.parent
    task_ids = []
    for index, task in enumerate(manifest["tasks"]):
        task_id = str(index)
        task_ids.append(task_id)
        values = {
            "CONTINUOUS_IC": task["continuous_ic"],
            "RESET_IC": task["reset_ic"],
            "CST_DATE": task["cst_date"],
            "CASE_NAME": task["case"],
            "MIXED_IC": task["mixed_ic"],
        }
        for segment in task["segments"]:
            number = segment["segment"]
            values[f"SEG{number}_SCRIPT"] = segment["script"]
            values[f"SEG{number}_WORK"] = str(
                Path(segment["script"]).parent / f"work_seg{number:02d}"
            )
        task_file = plan_directory / f"task_{task_id}.csh"
        task_file.write_text(
            "\n".join(
                (f"set {key} = {shell_quote(value)}" for key, value in values.items())
            )
            + "\n"
        )
    instructions = [
        f"set manifest_path = {shell_quote(str(manifest_path))}",
        f"set task_ids = ({' '.join(task_ids)})",
        f"set auto_post = {(1 if manifest['config']['auto_post'] else 0)}",
    ]
    (plan_directory / "batch_plan.csh").write_text("\n".join(instructions) + "\n")


def main() -> None:
    """生成批次计划，或核验指定运行段的输出；无批量执行功能。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "cctm_config.csh")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dates", nargs="+")
    parser.add_argument("--cases", nargs="+", choices=CASES)
    parser.add_argument("--plan-pointer", type=Path)
    parser.add_argument("--check-output", type=Path)
    parser.add_argument("--task-id", type=int)
    parser.add_argument("--segment", type=int, choices=[1, 2])
    args = parser.parse_args()
    if args.check_output:
        manifest = json.loads(args.check_output.read_text())
        task = manifest["tasks"][args.task_id]
        segment = task["segments"][args.segment - 1]
        validate_output(
            manifest["config"]["cmaq"],
            Path(segment["output"]),
            datetime.fromisoformat(segment["utc_day"]),
            args.segment,
        )
        return
    config = load_config(args.config.resolve())
    groups = read_species_groups()
    if not args.dates:
        args.dates = config["dates"]
    tasks = build_tasks(config, groups, args)
    manifest_path = create_plan(config, groups, tasks, args.dry_run)
    write_csh_task_files(manifest_path)
    if args.plan_pointer:
        args.plan_pointer.write_text(str(manifest_path.parent) + "\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
