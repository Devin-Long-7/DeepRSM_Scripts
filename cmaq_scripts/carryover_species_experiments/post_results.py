#!/usr/bin/env python3
"""选择性初始场实验的臭氧后处理。

直接读取两段原始 ACONC，按 CST 日计算城市 MDA8、日均和白天均值。
各组响应使用有符号 ppbv 绝对差值，不生成不稳定的归一化百分比。"""

# 延迟解析类型注解，兼容服务器Python 3.8/3.9。
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import json
import netCDF4 as nc
import numpy as np
import pandas as pd
import pyproj
import shapely
from shapely.geometry import shape
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

CITIES = dict(
    GZ=440100,
    SZ=440300,
    ZH=440400,
    FS=440600,
    HZ=441300,
    DG=441900,
    ZS=442000,
    JM=440700,
    ZQ=441200,
)


def masks_for(dataset: nc.Dataset, boundary_path: str) -> dict[str, np.ndarray]:
    """利用输出文件的真实投影参数建立九城市格点中心掩膜及 PRD 并集。

    采用行政边界包含判断，不使用人口或监测站权重。"""
    projection = pyproj.Proj(
        proj="lcc",
        lat_1=dataset.P_ALP,
        lat_2=dataset.P_BET,
        lat_0=dataset.YCENT,
        lon_0=dataset.XCENT,
        a=6370000,
        b=6370000,
    )
    grid_x, grid_y = np.meshgrid(
        dataset.XORIG
        + dataset.XCELL * (np.arange(len(dataset.dimensions["COL"])) + 0.5),
        dataset.YORIG
        + dataset.YCELL * (np.arange(len(dataset.dimensions["ROW"])) + 0.5),
    )
    longitude, latitude = projection(grid_x, grid_y, inverse=True)
    boundary_data = json.loads(Path(boundary_path).read_text())
    polygons = {
        feature["properties"]["adcode"]: shape(feature["geometry"])
        for feature in boundary_data["features"]
    }
    masks = {
        city: shapely.contains_xy(polygons[adcode], longitude, latitude)
        for city, adcode in CITIES.items()
    }
    masks["PRD"] = np.logical_or.reduce(list(masks.values()))
    if not all((mask.any() for mask in masks.values())):
        raise ValueError("Empty city mask; check boundary and grid")
    return masks


def collect_ozone_tables(
    manifest_data: dict, output_directory: Path
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """拼接每个任务的两段ACONC，按格点计算MDA8后再平均城市。

    核验时间覆盖、网格和单位，返回逐小时表及每日指标表。"""
    config = manifest_data["config"]
    hourly = []
    daily = []
    city_masks = None
    grid = None
    for task in manifest_data["tasks"]:
        pieces = []
        date = datetime.fromisoformat(task["cst_date"])
        for segment in task["segments"]:
            julian_day = datetime.fromisoformat(segment["utc_day"]).strftime("%Y%j")
            aconc_path = (
                Path(segment["output"])
                / f"CCTM_ACONC_{config['cmaq']['APPL']}_{julian_day}.nc"
            )
            with nc.Dataset(aconc_path) as dataset:
                current = {
                    column: np.asarray(getattr(dataset, column)).tolist()
                    for column in [
                        "P_ALP",
                        "P_BET",
                        "XCENT",
                        "YCENT",
                        "XORIG",
                        "YORIG",
                        "XCELL",
                        "YCELL",
                        "NROWS",
                        "NCOLS",
                    ]
                }
                if grid is None:
                    grid = current
                    city_masks = masks_for(dataset, config["boundary_file"])
                    np.savez_compressed(
                        output_directory / "city_masks.npz", **city_masks
                    )
                elif grid != current:
                    raise ValueError("Output grid mismatch")
                offset = 0 if segment["segment"] == 1 else 8
                hours = 8 if segment["segment"] == 1 else 16
                time_flags = np.asarray(dataset["TFLAG"][:, 0, :])
                expected = [
                    date - timedelta(hours=8) + timedelta(hours=offset + window_start)
                    for window_start in range(hours)
                ]
                if len(time_flags) != hours or not all(
                    (
                        int(parser) == int(t.strftime("%Y%j"))
                        and int(b) == t.hour * 10000
                        for (parser, b), t in zip(time_flags, expected)
                    )
                ):
                    raise ValueError(f"Incomplete or wrong output time: {aconc_path}")
                unit = dataset["O3"].units.strip()
                factor = (
                    1000
                    if unit == "ppmV"
                    else 1 if unit in ["ppbV", "ppbv", "ppb"] else None
                )
                if factor is None:
                    raise ValueError(f"Unknown O3 units {unit}")
                values = (
                    np.ma.filled(dataset["O3"][:, 0], np.nan).astype(float) * factor
                )
                if not np.isfinite(values).all() or np.any(values < 0):
                    raise ValueError("Invalid O3 values")
                pieces.append(values)
        hourly_ozone = np.concatenate(pieces)
        for city, mask in city_masks.items():
            city_ozone = hourly_ozone[:, mask]
            hourly_city_mean = city_ozone.mean(axis=1)
            # 先在每个格点取17个完整8小时窗口的最大值，再对城市格点平均。
            # 这不同于先城市平均、再求城市曲线的最大8小时值。
            city_mda8 = (
                np.stack(
                    [
                        city_ozone[window_start : window_start + 8].mean(axis=0)
                        for window_start in range(17)
                    ]
                )
                .max(axis=0)
                .mean()
            )
            daily.append(
                dict(
                    scenario=task["scenario"],
                    date=task["cst_date"],
                    case=task["case"],
                    city=city,
                    O3_MDA8_ppbv=city_mda8,
                    O3_daily_ppbv=hourly_city_mean.mean(),
                    O3_daytime_ppbv=hourly_city_mean[10:18].mean(),
                    cells=int(mask.sum()),
                )
            )
            for hour, concentration in enumerate(hourly_city_mean):
                hourly.append(
                    dict(
                        scenario=task["scenario"],
                        date=task["cst_date"],
                        case=task["case"],
                        city=city,
                        hour_cst=hour,
                        O3_ppbv=concentration,
                    )
                )
    hourly_table = pd.DataFrame(hourly)
    daily_table = pd.DataFrame(daily)
    return (hourly_table, daily_table)


def calculate_signed_effects(daily_table: pd.DataFrame) -> pd.DataFrame:
    """按C/R对照计算各组有符号绝对效应及非加和量。

    NO2_on_C与NO2_on_R分别表示两种化学背景，不作为独立可加贡献。"""
    effects = []
    for metric in ["O3_MDA8_ppbv", "O3_daily_ppbv", "O3_daytime_ppbv"]:
        wide = daily_table.pivot(
            index=["scenario", "date", "city"], columns="case", values=metric
        )
        if not {"C", "R"} <= set(wide):
            continue
        effects_table = pd.DataFrame(index=wide.index)
        effects_table["all_state"] = wide.R - wide.C
        for case, label in [
            ("C_NO2", "NO2_on_C"),
            ("C_other_N", "other_N_on_C"),
            ("C_OVOC", "OVOC_on_C"),
            ("C_O3", "O3_on_C"),
            ("C_rest", "rest_on_C"),
        ]:
            if case in wide:
                effects_table[label] = wide[case] - wide.C
        if "R_without_NO2" in wide:
            effects_table["NO2_on_R"] = wide.R - wide.R_without_NO2
        if {"NO2_on_C", "NO2_on_R"} <= set(effects_table):
            effects_table["NO2_background_difference"] = (
                effects_table.NO2_on_R - effects_table.NO2_on_C
            )
        group_effect_columns = [
            "NO2_on_C",
            "other_N_on_C",
            "OVOC_on_C",
            "O3_on_C",
            "rest_on_C",
        ]
        if all((column in effects_table for column in group_effect_columns)):
            # 整体响应减去单组响应之和，反映非线性交互，不是数值误差。
            effects_table["nonadditivity"] = effects_table.all_state - effects_table[
                group_effect_columns
            ].sum(axis=1)
        effects_table["metric"] = metric
        effects.append(effects_table.reset_index())
    return pd.concat(effects, ignore_index=True) if effects else pd.DataFrame()


def plot_effects(effects_table: pd.DataFrame, output_directory: Path) -> None:
    """逐情景、逐日期绘制MDA8绝对效应；保留正负值，不堆叠百分比。"""
    for (scenario, date), scenario_results in effects_table[
        effects_table.metric == "O3_MDA8_ppbv"
    ].groupby(["scenario", "date"]):
        effect_columns = [
            column
            for column in [
                "all_state",
                "NO2_on_C",
                "NO2_on_R",
                "other_N_on_C",
                "OVOC_on_C",
                "O3_on_C",
                "rest_on_C",
            ]
            if column in scenario_results
        ]
        scenario_results.set_index("city")[effect_columns].plot.bar(figsize=(12, 5))
        plt.axhline(0, color="black", lw=0.6)
        plt.ylabel("Signed MDA8 O3 change (ppbv)")
        plt.title(scenario + " " + date)
        plt.tight_layout()
        plt.savefig(output_directory / f"effects_{scenario}_{date}.png", dpi=180)
        plt.close()


def main() -> None:
    """读取批次清单，核验完整24小时输出，并保存城市臭氧指标和对照效应。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    manifest_data = json.loads(args.manifest.read_text())
    output_directory = args.manifest.parent / "post"
    output_directory.mkdir(exist_ok=True)
    hourly_table, daily_table = collect_ozone_tables(manifest_data, output_directory)
    hourly_table.to_csv(output_directory / "hourly_ozone.csv", index=False)
    daily_table.to_csv(output_directory / "daily_ozone.csv", index=False)
    effects_table = calculate_signed_effects(daily_table)
    if not effects_table.empty:
        effects_table.to_csv(output_directory / "signed_effects.csv", index=False)
        plot_effects(effects_table, output_directory)
    print(
        f"Post complete: {output_directory}; same-day MDA8 uses 17 windows 00–07 through 16–23 CST."
    )


if __name__ == "__main__":
    main()
