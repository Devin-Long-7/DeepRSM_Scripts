#!/usr/bin/env python3
"""选择性初始场替换。

读取连续置零场 I_C 和重置场 I_R，核验后生成8种实验的全层初始场。"""

# 延迟解析类型注解，兼容服务器Python 3.8/3.9。
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import hashlib
import json
import shutil
import netCDF4 as nc
import numpy as np

GRID = [
    "NROWS",
    "NCOLS",
    "NLAYS",
    "GDTYP",
    "P_ALP",
    "P_BET",
    "P_GAM",
    "XCENT",
    "YCENT",
    "XORIG",
    "YORIG",
    "XCELL",
    "YCELL",
    "VGTYP",
    "VGTOP",
    "VGLVLS",
]
CASES = {
    "C": ("C", None),
    "R": ("R", None),
    "C_NO2": ("C", "NO2"),
    "R_without_NO2": ("R", "NO2"),
    "C_other_N": ("C", "other_N"),
    "C_OVOC": ("C", "OVOC"),
    "C_O3": ("C", "O3"),
    "C_rest": ("C", "rest"),
}


def digest(path: Path | str) -> str:
    """分块计算文件 SHA256，用于确认初始场和排放控制文件的来源。

    分块读取避免把完整三维 NetCDF 一次性载入内存。"""
    hasher = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def stamp(dataset: nc.Dataset) -> datetime:
    """从 NetCDF 的 SDATE/STIME 属性解析 UTC 时刻；不依赖文件名日期。"""
    return datetime.strptime(str(int(dataset.SDATE)), "%Y%j") + timedelta(
        hours=int(dataset.STIME) // 10000,
        minutes=int(dataset.STIME) // 100 % 100,
        seconds=int(dataset.STIME) % 100,
    )


def get_state_variables(dataset: nc.Dataset) -> set[str]:
    """列出存储在 TSTEP×LAY×ROW×COL 上的完整状态变量。"""
    return {
        species_name
        for species_name, variable in dataset.variables.items()
        if variable.dimensions == ("TSTEP", "LAY", "ROW", "COL")
    }


def validate(
    continuous_path: Path | str,
    reset_path: Path | str,
    cst_date: str,
    groups: dict[str, list[str]],
) -> dict:
    """核对连续场与重置场是否可在同一 CST00 时刻逐物种替换。

    检查时间、网格、层界、变量、单位及有效值；返回实际分组和缺失候选。"""
    # 北京时间零点对应前一日UTC16；文件名日期不能代替内部时间。
    target = datetime.fromisoformat(cst_date) - timedelta(hours=8)
    with nc.Dataset(continuous_path) as continuous_dataset, nc.Dataset(
        reset_path
    ) as reset_dataset:
        for dataset in [continuous_dataset, reset_dataset]:
            if len(dataset.dimensions["TSTEP"]) != 1 or stamp(dataset) != target:
                raise ValueError(
                    f"IC must contain one state at {target} UTC: {dataset.filepath()}"
                )
            time_flags = np.asarray(dataset["TFLAG"][:])
            expected = [int(target.strftime("%Y%j")), target.hour * 10000]
            if not np.all(time_flags == expected):
                raise ValueError("IC TFLAG inconsistent with SDATE/STIME")
        for attribute in GRID:
            if (
                not hasattr(continuous_dataset, attribute)
                or not hasattr(reset_dataset, attribute)
                or (
                    not np.array_equal(
                        getattr(continuous_dataset, attribute),
                        getattr(reset_dataset, attribute),
                    )
                )
            ):
                raise ValueError(f"IC grid mismatch: {attribute}")
        species_names = get_state_variables(continuous_dataset)
        if species_names != get_state_variables(reset_dataset):
            raise ValueError(
                f"IC variables differ: only C={sorted(species_names - get_state_variables(reset_dataset))}; only R={sorted(get_state_variables(reset_dataset) - species_names)}"
            )
        if not species_names or not {"NO2", "O3"} <= species_names:
            raise ValueError("IC lacks NO2/O3 fields")
        assigned_species = []
        actual_groups = {}
        absent_species = {}
        for group_name, species_list in groups.items():
            if group_name not in ["NO2", "other_N", "OVOC", "O3"]:
                raise ValueError(f"Unexpected group {group_name}")
            if len(species_list) != len(set(species_list)):
                raise ValueError(f"Duplicate species within {group_name}")
            actual_groups[group_name] = sorted(set(species_list) & species_names)
            absent_species[group_name] = sorted(set(species_list) - species_names)
            assigned_species += species_list
        if len(assigned_species) != len(set(assigned_species)):
            raise ValueError("Species groups overlap")
        if set(actual_groups) != {"NO2", "other_N", "OVOC", "O3"} or any(
            (not variable for variable in actual_groups.values())
        ):
            raise ValueError("A required group is empty")
        # 未显式分组的所有状态变量统一放入rest，保证没有遗漏或重复。
        actual_groups["rest"] = sorted(species_names - set(assigned_species))
        for name in species_names:
            if (
                continuous_dataset[name].shape != reset_dataset[name].shape
                or continuous_dataset[name].units.strip()
                != reset_dataset[name].units.strip()
            ):
                raise ValueError(f"IC variable shape/unit mismatch: {name}")
            for dataset in [continuous_dataset, reset_dataset]:
                values = dataset[name][:]
                if np.ma.count_masked(values) or not np.isfinite(values).all():
                    raise ValueError(f"Invalid IC values: {name}")
        grid = {
            attribute: np.asarray(getattr(continuous_dataset, attribute)).tolist()
            for attribute in GRID
        }
    return dict(
        cst_date=cst_date,
        utc_start=target.isoformat(),
        groups=actual_groups,
        listed_but_absent=absent_species,
        variables=sorted(species_names),
        grid=grid,
    )


def prepare(
    continuous_path: Path,
    reset_path: Path,
    cst_date: str,
    groups: dict[str, list[str]],
    output_path: Path,
    case: str,
) -> dict:
    """生成指定配置的混合初始场，并逐变量验证替换是否正确。

    原始文件只读；未替换变量保持底场值，结果及来源哈希另行保存。"""
    validation_info = validate(continuous_path, reset_path, cst_date, groups)
    base_case, replacement_group = CASES[case]
    base_path = continuous_path if base_case == "C" else reset_path
    donor_path = reset_path if base_case == "C" else continuous_path
    if output_path.exists():
        raise FileExistsError(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".partial")
    try:
        # 先完整复制底场，保留原始网格、时间和其他元数据。
        shutil.copyfile(base_path, temporary_path)
        replaced_species = (
            validation_info["groups"][replacement_group] if replacement_group else []
        )
        with nc.Dataset(temporary_path, "r+") as output_dataset, nc.Dataset(
            donor_path
        ) as donor_dataset:
            for name in replaced_species:
                output_dataset[name][:] = donor_dataset[name][:]
        # 不仅检查被替换的物种，也验证未替换物种仍与底场逐值一致。
        with nc.Dataset(temporary_path) as output_dataset, nc.Dataset(
            continuous_path
        ) as continuous_dataset, nc.Dataset(reset_path) as reset_dataset:
            for name in validation_info["variables"]:
                expected = (
                    (reset_dataset if base_case == "C" else continuous_dataset)
                    if name in replaced_species
                    else continuous_dataset if base_case == "C" else reset_dataset
                )
                if not np.array_equal(output_dataset[name][:], expected[name][:]):
                    raise ValueError(f"Mixed IC verification failed: {name}")
        temporary_path.rename(output_path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    validation_info.update(
        case=case,
        base_source=str(base_path),
        donor_source=str(donor_path),
        replaced_species=replaced_species,
        continuous_sha256=digest(continuous_path),
        reset_sha256=digest(reset_path),
        output_sha256=digest(output_path),
    )
    output_path.with_suffix(".json").write_text(
        json.dumps(validation_info, indent=2) + "\n"
    )
    return validation_info


def main() -> None:
    """解析单文件初始场生成参数并执行替换。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--continuous", type=Path, required=True)
    parser.add_argument("--reset", type=Path, required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(
        args.continuous,
        args.reset,
        args.date,
        json.loads(args.groups.read_text()),
        args.output,
        args.case,
    )


if __name__ == "__main__":
    main()
