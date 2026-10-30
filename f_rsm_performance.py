'''
# Description: This script is for evaluating the performance of RSM by comparing its predictions with CMAQ observations. It includes functions for calculating performance metrics and visualizing the results through scatter plots and density plots.
# Author: Devin
# Date: 2024-06-20 17:00:00
'''
#region 1.1 RSM Worker：设置参数并读取相关数据

import numpy as np
import os
import pandas as pd
from datetime import datetime
from tqdm.auto import tqdm
import cmaps
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from esil.map_helper import get_multiple_data, show_maps
from esil.scatter_plot_helper import draw_multiple_density_plots
from esil.rsm_helper.model_property import model_attribute
from esil.earth_helper import get_all_masks

cmap_conc = cmaps.WhiteBlueGreenYellowRed
cmap_delta = cmaps.ViBlGrWhYeOrRe
boundary_json_file = "/DeepLearning/mnt/Devin/boundary/guangdong_cities.json"
PRD_CITIES = ['广州市', '深圳市', '珠海市', '佛山市', '肇庆市', '江门市', '惠州市', '东莞市', '中山市']

import sys
sys.path.append(r"/DeepLearning/mnt/Devin/01_deeprsm/03_create_rsm_scripts")
from b_input_data_helper import (year, month, output_npy_dir, output_rsm_weights_dir, output_dir,
    output_oos_dir, target_pollutant, grid_path, species_num, target_pollutant_idx,
    boundary_file, whole_region_full_control_case_name, receptor_file_txt, config_file,
    species_in_cmaq, project_name, unit, all_aconc_files, read_receptor_file_txt, get_oos_input_data)
from e_rsm_helper import get_summary_metrics, get_ozone_grid_values

print(f"config_file:{config_file}")
_, dict_receptor = read_receptor_file_txt(receptor_file_txt)
region_zero_cases = [whole_region_full_control_case_name] + list(dict_receptor.values())
result_root = output_dir

region_zero_cases = [x.strip() for x in region_zero_cases]
grid = np.load(grid_path)
region_num = len(region_zero_cases) - 1
if not os.path.exists(result_root):
    os.makedirs(result_root)
print("初始化完成，开始读取数据...")
#endregion 1.1 RSM Worker：设置参数并读取相关数据


#region 公共辅助函数
def _resolve_oos_data(oos_data, days):
    """
    统一解析 oos_data：如果已提供则直接返回，否则调用 get_oos_result 获取。

    @param {tuple | None} oos_data: 已有的 OOS 结果元组
    @param {list[int] | None} days: 要评估的天数列表
    @return {tuple}: (dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, case_ids)
    """
    if oos_data is not None:
        return oos_data
    return get_oos_result(days=days)


def _ensure_dir(path):
    """
    确保目录存在，不存在则创建。

    @param {str} path: 目录路径
    @return {str}: 目录路径（与输入相同）
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path


def _append_summary_df(df_all, df_new, ts_idx):
    """
    将单个时间步的 metrics DataFrame 拼接到汇总 DataFrame，并在第一列插入 time_step。

    @param {DataFrame | None} df_all: 已有的汇总 DataFrame
    @param {DataFrame} df_new: 当前时间步的 metrics DataFrame
    @param {int} ts_idx: 时间步索引
    @return {DataFrame}: 更新后的汇总 DataFrame
    """
    df_new["time_step"] = f"Day {ts_idx + 1}"
    cols = ['time_step'] + [c for c in df_new.columns if c != 'time_step']
    df_new = df_new[cols]
    return df_new if df_all is None else pd.concat([df_all, df_new], axis=0)


def _build_all_summaries(dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, prd_mask=None):
    """
    遍历所有时间步，构建原始值和响应值的汇总 metrics DataFrame。

    @param {dict} dict_rsm: RSM 预测值字典
    @param {dict} dict_cmaq: CMAQ 真实值字典
    @param {dict} dict_rsm_response: RSM 响应值字典
    @param {dict} dict_cmaq_response: CMAQ 响应值字典
    @param {ndarray | None} prd_mask: PRD 掩膜，形状 (rows, cols)。若提供则仅统计 PRD 区域。
    @return {tuple}: (df_summary, df_summary_response) 两个汇总 DataFrame
    """
    df_summary, df_summary_resp = None, None
    for ts_idx in tqdm(dict_rsm.keys(), desc="Building summary metrics"):
        if prd_mask is not None:
            valid_2d = ~np.isnan(prd_mask)
            rsm_data = dict_rsm[ts_idx][:, valid_2d]
            cmaq_data = dict_cmaq[ts_idx][:, valid_2d]
            rsm_resp_data = dict_rsm_response[ts_idx][:, valid_2d]
            cmaq_resp_data = dict_cmaq_response[ts_idx][:, valid_2d]
        else:
            rsm_data = dict_rsm[ts_idx]
            cmaq_data = dict_cmaq[ts_idx]
            rsm_resp_data = dict_rsm_response[ts_idx]
            cmaq_resp_data = dict_cmaq_response[ts_idx]

        df, _ = get_summary_metrics(rsm_data, cmaq_data)
        df.reset_index()
        df_summary = _append_summary_df(df_summary, df, ts_idx)

        df_resp, _ = get_summary_metrics(rsm_resp_data, cmaq_resp_data)
        df_resp.reset_index()
        df_summary_resp = _append_summary_df(df_summary_resp, df_resp, ts_idx)
    return df_summary, df_summary_resp


def _save_density_plot(dict_data, x_name, y_name, nbins, save_path, file_name,
                       density=True, panel_layout=None,show_subplot_label=True):
    """
    绘制密度散点图并保存为 PNG 文件。

    @param {dict} dict_data: 数据字典，格式 {label: {"x": array, "y": array}}
    @param {str} x_name: x 轴标签
    @param {str} y_name: y 轴标签
    @param {int} nbins: 直方图 bin 数量
    @param {str} save_path: 保存目录
    @param {str} file_name: 文件名
    @param {bool} density: 是否显示密度图
    @param {tuple | None} panel_layout: 面板布局，如 (5, 3)
    @param {bool} show_subplot_label: 是否显示子图标签
    @return {None}
    """
    fig = draw_multiple_density_plots(dict_data, xName=x_name, yName=y_name,
                                       nbins=nbins, density=density, panel_layout=panel_layout, show_subplot_label=show_subplot_label)
    fig.savefig(os.path.join(save_path, file_name), bbox_inches='tight', dpi=300)


def _get_lons_lats():
    """
    从 CMAQ 浓度文件获取经纬度坐标。

    @return {tuple}: (lons, lats) 经纬度二维数组
    """
    mp = model_attribute(all_aconc_files[0])
    return mp.get_xy_coordinates(show_lonlat=True)


def _get_prd_mask(lons, lats):
    """
    构建 PRD 9 市联合掩膜。

    @param {ndarray} lons: 经度二维数组
    @param {ndarray} lats: 纬度二维数组
    @return {ndarray}: PRD 掩膜，形状 (rows, cols)，PRD 区域内为 1，区域外为 NaN
    """
    dict_masks = get_all_masks(json_file=boundary_json_file, lat=lats, lon=lons, replaceFalseWithNan=True)
    prd_masks = [mask for name, mask in dict_masks.items() if name in PRD_CITIES]
    return np.where(np.all([np.isnan(m) for m in prd_masks], axis=0), np.nan, 1)


def _mask_and_flatten_paired(x, y, prd_mask):
    """
    对配对数据应用 PRD 掩膜，展平并去除 NaN，保持 x 和 y 索引对应。

    @param {ndarray} x: 数据数组（2D 或 3D）
    @param {ndarray} y: 数据数组（2D 或 3D），与 x 同形状
    @param {ndarray} prd_mask: PRD 掩膜，形状 (rows, cols)
    @return {tuple}: (x_filtered, y_filtered) 过滤后的一维数组
    """
    flat_x = (x * prd_mask).flatten()
    flat_y = (y * prd_mask).flatten()
    valid = ~np.isnan(flat_x) & ~np.isnan(flat_y)
    return flat_x[valid], flat_y[valid]
#endregion 公共辅助函数


def get_oos_result(days=None):
    """
    获取外部验证（Out-of-Sample）结果，通过 RSM 模型预测并与 CMAQ 真实值对比。

    @description:
        遍历指定天数，对每个 OOS case 调用 RSM 模型进行预测，计算预测值(rsm)、
        真实值(cmaq)、预测响应值(rsm_response = base - rsm)和真实响应值(cmaq_response = base - cmaq)。
        结果按时间步索引存储在字典中返回。

    @param {list[int] | None} days: 要评估的天数列表（如 [6, 13, 14, 16, 19]）。
        若为 None，则使用全部时间步 range(base_case_cmaq_data.shape[0])。

    @return {tuple}:
        - dict_rsm {dict[int, ndarray]}: RSM 预测值，key 为时间步索引，value shape=(oos_case_num, grid_rows, grid_cols)
        - dict_cmaq {dict[int, ndarray]}: CMAQ 真实值，结构同上
        - dict_rsm_response {dict[int, ndarray]}: RSM 响应值（base - rsm），结构同上
        - dict_cmaq_response {dict[int, ndarray]}: CMAQ 响应值（base - cmaq），结构同上
        - case_ids {list}: 所有 OOS case 的 ID 列表

    @调用示例:
        # 获取指定天数的 OOS 结果
        dict_rsm, dict_cmaq, dict_rsm_resp, dict_cmaq_resp, case_ids = get_oos_result(days=[6, 13, 14])
        # 获取全部时间步的结果
        dict_rsm, dict_cmaq, dict_rsm_resp, dict_cmaq_resp, case_ids = get_oos_result(days=None)
    """
    oos_cmaq_data, region_cell, control_matrix, base_case_cmaq_data, case_ids = get_oos_input_data()
    oos_case_num = control_matrix.shape[1]
    dict_cmaq, dict_rsm, dict_rsm_response, dict_cmaq_response = {}, {}, {}, {}
    time_steps = range(base_case_cmaq_data.shape[0]) if days is None else days
    for day in tqdm(time_steps):
        rsm = np.zeros((oos_case_num, *base_case_cmaq_data.shape[-2:]))
        x = np.zeros((region_num, species_num))
        for c_index in range(oos_case_num):
            for r_index in range(region_num):
                x[r_index, :] = control_matrix[r_index, c_index, :]
            rsm_values, _ = get_ozone_grid_values(target_pollutant_idx, x, month, day, hour=None)
            rsm[c_index, :, :] = rsm_values
        ts_idx = day - 1
        cmaq = oos_cmaq_data[0, :, ts_idx, :, :]
        dict_cmaq[ts_idx] = cmaq
        dict_rsm[ts_idx] = rsm
        dict_rsm_response[ts_idx] = base_case_cmaq_data[ts_idx, 0, :, :] - rsm
        dict_cmaq_response[ts_idx] = base_case_cmaq_data[ts_idx, 0, :, :] - cmaq
    return dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, case_ids


def draw_density_plot_by_all_days_all_runs(oos_data=None, key_name="All Days", days=None, skip_non_prd=False):
    """
    将所有天、所有 OOS runs 合并为一张密度散点图，并输出汇总统计 CSV。

    @description:
        遍历所有时间步，将 CMAQ 与 RSM 数据全部合并，绘制一张综合密度散点图。
        同时计算每个时间步的汇总指标（Mean、Min、Max 等），导出为 CSV 文件。
        分别绘制原始值（CMAQ vs RSM）和响应值（CMAQ Response vs RSM Response）的密度图。

    @param {tuple | None} oos_data: 已有的 OOS 结果元组 (dict_rsm, dict_cmaq, dict_rsm_response,
        dict_cmaq_response, case_ids)。若为 None，则调用 get_oos_result(days) 获取。
    @param {str} key_name: 图表标题关键词，用于文件命名（如 "All Days"、"All Polluted Days"）。
    @param {list[int] | None} days: 要评估的天数列表，仅在 oos_data 为 None 时使用。
    @param {bool} skip_non_prd: 是否剔除珠三角9市以外的网格。默认 False（全域）。

    @return {None}: 结果保存为 PNG 图片和 CSV 文件到 output_oos_dir 目录。

    @调用示例:
        # 使用已有数据绘制
        draw_density_plot_by_all_days_all_runs(oos_data=oos_data, key_name="All Days", days=days)
        # 直接指定天数（会自动获取 OOS 结果）
        draw_density_plot_by_all_days_all_runs(key_name="All Polluted Days", days=[6, 13, 14, 16, 19])
        # 仅统计珠三角9市
        draw_density_plot_by_all_days_all_runs(oos_data=oos_data, key_name="All Days PRD", days=days, skip_non_prd=True)
    """
    dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, _ = _resolve_oos_data(oos_data, days)
    save_path = _ensure_dir(os.path.join(output_oos_dir, 'scatter_plots'))

    prd_mask = None
    if skip_non_prd:
        lons, lats = _get_lons_lats()
        prd_mask = _get_prd_mask(lons, lats)

    df_summary_all, df_summary_all_response = _build_all_summaries(
        dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, prd_mask=prd_mask)

    all_x, all_y = np.array([]), np.array([])
    all_x_resp, all_y_resp = np.array([]), np.array([])
    records = []
    for ts_idx in dict_rsm:
        cmaq = dict_cmaq[ts_idx]
        rsm = dict_rsm[ts_idx]
        cmaq_resp = dict_cmaq_response[ts_idx]
        rsm_resp = dict_rsm_response[ts_idx]
        rows, cols = cmaq.shape[1], cmaq.shape[2]
        for run in range(cmaq.shape[0]):
            for r in range(rows):
                for c in range(cols):
                    if prd_mask is not None and np.isnan(prd_mask[r, c]):
                        continue
                    cmaq_val = cmaq[run, r, c]
                    rsm_val = rsm[run, r, c]
                    if np.isnan(cmaq_val) or np.isnan(rsm_val):
                        continue
                    records.append({
                        "Day": ts_idx + 1, "Run": run + 1,
                        "Column": c, "Row": r,
                        "CMAQ": cmaq_val, "RSM": rsm_val,
                        "CMAQ_Response": cmaq_resp[run, r, c],
                        "RSM_Response": rsm_resp[run, r, c],
                    })
        # 保留绘图所需的合并数据
        if prd_mask is not None:
            x, y = _mask_and_flatten_paired(cmaq, rsm, prd_mask)
            xr, yr = _mask_and_flatten_paired(cmaq_resp, rsm_resp, prd_mask)
        else:
            x, y = cmaq.flatten(), rsm.flatten()
            xr, yr = cmaq_resp.flatten(), rsm_resp.flatten()
        all_x = np.concatenate([all_x, x])
        all_y = np.concatenate([all_y, y])
        all_x_resp = np.concatenate([all_x_resp, xr])
        all_y_resp = np.concatenate([all_y_resp, yr])

    rsm_sample = dict_rsm[list(dict_rsm.keys())[0]]
    if prd_mask is not None:
        nbins = max(int(np.sum(~np.isnan(prd_mask))) // 100, 20)
    else:
        nbins = int(rsm_sample[0].shape[0] * rsm_sample[0].shape[1] / 100)
    safe_name = key_name.replace(" ", "_")
    if skip_non_prd:
        safe_name += "_PRD"

    _save_density_plot({key_name: {"x": all_x, "y": all_y}},
                       "CMAQ", "RSM", nbins, save_path,
                       f'{project_name}_density_plot_{safe_name}.png',show_subplot_label=False)
    _save_density_plot({f"{key_name} Response": {"x": all_x_resp, "y": all_y_resp}},
                       "CMAQ Response", "RSM Response", nbins, save_path,
                       f'{project_name}_density_plot_{safe_name}_response.png',show_subplot_label=False)   

    csv_suffix = "_PRD" if skip_non_prd else ""
    df_summary_all.to_csv(os.path.join(output_oos_dir, f'{project_name}_oos_summary{csv_suffix}.csv'))
    df_summary_all_response.to_csv(os.path.join(output_oos_dir, f'{project_name}_oos_summary_response{csv_suffix}.csv'))
    df_scatter = pd.DataFrame(records)
    df_scatter.to_csv(os.path.join(output_oos_dir, f'{project_name}_{key_name}_scatter_data{csv_suffix}.csv'), index=False)


def draw_density_plot_by_day(oos_data=None, key_name="by_day", days=None, skip_non_prd=False):
    """
    每天所有 OOS runs 合并，按天分面板绘制密度散点图。

    @description:
        遍历所有时间步，将每天的 CMAQ 和 RSM 数据合并为一个面板，
        使用 draw_multiple_density_plots 绘制多面板密度散点图。
        分别绘制原始值和响应值的按天分面板图。

    @param {tuple | None} oos_data: 已有的 OOS 结果元组 (dict_rsm, dict_cmaq, dict_rsm_response,
        dict_cmaq_response, case_ids)。若为 None，则调用 get_oos_result(days) 获取。
    @param {str} key_name: 图表标题关键词，用于文件命名。
    @param {list[int] | None} days: 要评估的天数列表，仅在 oos_data 为 None 时使用。
    @param {bool} skip_non_prd: 是否剔除珠三角9市以外的网格。默认 False（全域）。

    @return {None}: 结果保存为 PNG 图片到 output_oos_dir/scatter_plots/ 目录。

    @调用示例:
        draw_density_plot_by_day(oos_data=oos_data, key_name="by day", days=[6, 13, 14, 16, 19])
        draw_density_plot_by_day(oos_data=oos_data, key_name="by day", days=days, skip_non_prd=True)
    """
    dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, _ = _resolve_oos_data(oos_data, days)
    save_path = _ensure_dir(os.path.join(output_oos_dir, 'scatter_plots'))

    prd_mask = None
    if skip_non_prd:
        lons, lats = _get_lons_lats()
        prd_mask = _get_prd_mask(lons, lats)

    dict_data_by_day, dict_data_by_day_response = {}, {}
    nbins = None
    for ts_idx in tqdm(dict_rsm.keys()):
        rsm, cmaq = dict_rsm[ts_idx], dict_cmaq[ts_idx]
        if nbins is None:
            if prd_mask is not None:
                nbins = max(int(np.sum(~np.isnan(prd_mask))) // 100, 20)
            else:
                nbins = int(rsm[0].shape[0] * rsm[0].shape[1] / 100)
        if prd_mask is not None:
            x, y = _mask_and_flatten_paired(cmaq, rsm, prd_mask)
            xr, yr = _mask_and_flatten_paired(dict_cmaq_response[ts_idx], dict_rsm_response[ts_idx], prd_mask)
        else:
            x, y = cmaq.flatten(), rsm.flatten()
            xr, yr = dict_cmaq_response[ts_idx].flatten(), dict_rsm_response[ts_idx].flatten()
        dict_data_by_day[f"Day {ts_idx+1}"] = {"x": x, "y": y}
        dict_data_by_day_response[f"Day {ts_idx+1}"] = {"x": xr, "y": yr}

    safe_name = key_name.replace(" ", "_")
    if skip_non_prd:
        safe_name += "_PRD"
    if dict_data_by_day:
        _save_density_plot(dict_data_by_day, "CMAQ", "RSM", nbins, save_path,
                           f'{project_name}_density_plot_{safe_name}.png')
    if dict_data_by_day_response:
        _save_density_plot(dict_data_by_day_response, "CMAQ Response", "RSM Response", nbins, save_path,
                           f'{project_name}_density_plot_{safe_name}_response.png')


def draw_density_plot_by_day_by_run(oos_data=None, key_name="by_day_by_run", days=None, skip_non_prd=False):
    """
    按天、按单个 OOS run 分面板绘制密度散点图，并输出汇总统计 CSV。

    @description:
        遍历所有时间步和每个 OOS case，为每个 (天, run) 组合单独绘制一个密度散点面板。
        每 15 个面板保存为一张图片。同时计算汇总指标导出为 CSV 文件。
        分别处理原始值和响应值。

    @param {tuple | None} oos_data: 已有的 OOS 结果元组 (dict_rsm, dict_cmaq, dict_rsm_response,
        dict_cmaq_response, case_ids)。若为 None，则调用 get_oos_result(days) 获取。
    @param {str} key_name: 图表标题关键词，用于文件命名。
    @param {list[int] | None} days: 要评估的天数列表，仅在 oos_data 为 None 时使用。
    @param {bool} skip_non_prd: 是否剔除珠三角9市以外的网格。默认 False（全域）。

    @return {None}: 结果保存为 PNG 图片和 CSV 文件到 output_oos_dir 目录。

    @调用示例:
        draw_density_plot_by_day_by_run(oos_data=oos_data, key_name="by day by run", days=[6, 13, 14, 16, 19])
        draw_density_plot_by_day_by_run(oos_data=oos_data, key_name="by day by run", days=days, skip_non_prd=True)
    """
    dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, _ = _resolve_oos_data(oos_data, days)
    save_path = _ensure_dir(os.path.join(output_oos_dir, 'scatter_plots'))

    prd_mask = None
    if skip_non_prd:
        lons, lats = _get_lons_lats()
        prd_mask = _get_prd_mask(lons, lats)

    df_summary_all, df_summary_all_response = _build_all_summaries(
        dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, prd_mask=prd_mask)

    dict_data, dict_data_response = {}, {}
    safe_name = key_name.replace(" ", "_")
    if skip_non_prd:
        safe_name += "_PRD"
    batch_size = 15

    for idx, ts_idx in enumerate(tqdm(dict_rsm.keys())):
        rsm, cmaq = dict_rsm[ts_idx], dict_cmaq[ts_idx]
        rsm_resp, cmaq_resp = dict_rsm_response[ts_idx], dict_cmaq_response[ts_idx]
        if prd_mask is not None:
            nbins = max(int(np.sum(~np.isnan(prd_mask))) // 100, 20)
        else:
            nbins = int(rsm[0].shape[0] * rsm[0].shape[1] / 100)

        for c_index in range(rsm.shape[0]):
            if prd_mask is not None:
                x, y = _mask_and_flatten_paired(cmaq[c_index], rsm[c_index], prd_mask)
                xr, yr = _mask_and_flatten_paired(cmaq_resp[c_index], rsm_resp[c_index], prd_mask)
            else:
                x, y = cmaq[c_index].flatten(), rsm[c_index].flatten()
                xr, yr = cmaq_resp[c_index].flatten(), rsm_resp[c_index].flatten()
            dict_data[f"Day {ts_idx+1} Run #{c_index+1}"] = {"x": x, "y": y}
            dict_data_response[f"Day {ts_idx+1} Run #{c_index+1} response"] = {"x": xr, "y": yr}

        if len(dict_data) >= batch_size:
            _save_density_plot(dict_data, "CMAQ", "RSM", nbins, save_path,
                               f'{project_name}_density_plot_{safe_name}_{idx+1}.png',
                               panel_layout=(5, 3))
            dict_data = {}
        if len(dict_data_response) >= batch_size:
            _save_density_plot(dict_data_response, "CMAQ Response", "RSM Response", nbins, save_path,
                               f'{project_name}_density_plot_{safe_name}_response_{idx+1}.png',
                               panel_layout=(5, 3))
            dict_data_response = {}

    if dict_data:
        rows = max(int(len(dict_data) / 5), 1)
        _save_density_plot(dict_data, "CMAQ", "RSM", nbins, save_path,
                           f'{project_name}_density_plot_{safe_name}_remaining.png',
                           panel_layout=(5, rows))
    if dict_data_response:
        rows = max(int(len(dict_data_response) / 5), 1)
        _save_density_plot(dict_data_response, "CMAQ Response", "RSM Response", nbins, save_path,
                           f'{project_name}_density_plot_{safe_name}_response_remaining.png',
                           panel_layout=(5, rows))

    csv_suffix = "_PRD" if skip_non_prd else ""
    df_summary_all.to_csv(os.path.join(output_oos_dir, f'{project_name}_oos_summary{csv_suffix}.csv'))
    df_summary_all_response.to_csv(os.path.join(output_oos_dir, f'{project_name}_oos_summary_response{csv_suffix}.csv'))


def _build_2d_plot_data(dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response,
                        case_ids, lons, lats, mask=None):
    """
    构建 2D 浓度空间分布的绘图数据，按批次 yield 返回。

    @description:
        遍历所有时间步和每个 OOS case，生成 CMAQ Response、RSM Response 和 Delta 三组空间数据。
        可选地对数据应用掩膜。每累积满 batch_size 个子图时 yield 一次。
        最后 yield 汇总的跨天 Delta 数据。

    @param {dict} dict_rsm: RSM 预测值字典
    @param {dict} dict_cmaq: CMAQ 真实值字典
    @param {dict} dict_rsm_response: RSM 响应值字典
    @param {dict} dict_cmaq_response: CMAQ 响应值字典
    @param {list} case_ids: OOS case ID 列表
    @param {ndarray} lons: 经度坐标数组
    @param {ndarray} lats: 纬度坐标数组
    @param {ndarray | None} mask: 可选的空间掩膜，与 grid 同形状

    @return {generator}: 每次迭代返回 (dict_data, ts_idx, is_summary_batch)

    @调用示例:
        for dict_data, ts_idx, is_summary in _build_2d_plot_data(
                dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response,
                case_ids, lons, lats, mask=combined_mask_gd):
            # dict_data 为当前批次数据，ts_idx 为时间步索引
            pass
    """
    batch_size = 15
    dict_data = {}
    dict_data_days_delta = {}

    for ts_idx in tqdm(dict_rsm.keys()):
        for c_index in range(len(case_ids)):
            cmaq_resp = dict_cmaq_response[ts_idx][c_index, :, :]
            rsm_resp = dict_rsm_response[ts_idx][c_index, :, :]
            delta = dict_rsm[ts_idx][c_index, :, :] - dict_cmaq[ts_idx][c_index, :, :]

            if mask is not None:
                cmaq_resp = cmaq_resp * mask
                rsm_resp = rsm_resp * mask
                delta = delta * mask

            label = f"Day {ts_idx+1} Run#{case_ids[c_index]}"
            get_multiple_data(dict_data, dataset_name=f"{label} CMAQ Response", variable_name="O3",
                              grid_x=lons, grid_y=lats, grid_concentration=cmaq_resp, is_delta=True)
            get_multiple_data(dict_data, dataset_name=f"{label} RSM Response", variable_name="O3",
                              grid_x=lons, grid_y=lats, grid_concentration=rsm_resp, is_delta=True)
            get_multiple_data(dict_data, dataset_name=f"{label} Delta", variable_name="O3",
                              grid_x=lons, grid_y=lats, grid_concentration=delta, is_delta=True)

            get_multiple_data(dict_data_days_delta, dataset_name=f"Day {ts_idx+1} Delta Run#{case_ids[c_index]}",
                              variable_name="O3", grid_x=lons, grid_y=lats,
                              grid_concentration=delta, is_delta=True)

        if len(dict_data) >= batch_size:
            yield dict_data, ts_idx, False
            dict_data = {}

    if dict_data:
        yield dict_data, ts_idx, False
    if dict_data_days_delta:
        yield dict_data_days_delta, ts_idx, True


def plot_time_series(oos_data=None, days=None, skip_non_prd=False,
                     exceedance_days=None, key_name="time_series"):
    """
    绘制 CMAQ + DeepRSM 时间序列 + OOS 包络图（单 panel 宽图）。

    @description:
        展示时间维度上 DeepRSM 与 CMAQ 的高度一致性，8个 OOS runs 的包络带窄→模型稳健。
        CMAQ 线(蓝实线)：每天所有 OOS case 的 CMAQ 值域平均后取均值。
        DeepRSM 线(红实线)：每天所有 OOS case 的 RSM 预测值域平均后取均值。
        灰色包络带：RSM 预测的逐 case 域平均的 min/max。
        超标日在 x 轴日期旁标红色 *。

    @param {tuple | None} oos_data: 已有的 OOS 结果元组。若为 None，则调用 get_oos_result(days) 获取。
    @param {list[int] | None} days: 要评估的天数列表。
    @param {bool} skip_non_prd: 是否剔除珠三角9市以外的网格。默认 False（全域）。
    @param {list[int] | None} exceedance_days: 超标日列表，x 轴日期标红色 *。如 [6, 13, 14, 16, 19]。
    @param {str} key_name: 图表标题关键词，用于文件命名。

    @return {None}: 结果保存为 PNG 图片到 output_oos_dir/time_series/ 目录。

    @调用示例:
        plot_time_series(oos_data=oos_data, days=days,
                         exceedance_days=[6, 13, 14, 16, 19])
        plot_time_series(oos_data=oos_data, days=days, skip_non_prd=True,
                         exceedance_days=[6, 13, 14, 16, 19])
    """
    dict_rsm, dict_cmaq, _, _, _ = _resolve_oos_data(oos_data, days)

    prd_mask = None
    if skip_non_prd:
        lons, lats = _get_lons_lats()
        prd_mask = _get_prd_mask(lons, lats)

    valid_2d = ~np.isnan(prd_mask) if prd_mask is not None else None

    sorted_days = sorted(days if days is not None else dict_rsm.keys())
    dates = [datetime(year, month, d if d > 0 else d + 1) for d in sorted_days]

    cmaq_mean_series, rsm_mean_series = [], []
    rsm_min_series, rsm_max_series = [], []

    for day in sorted_days:
        ts_idx = day - 1
        rsm_data = dict_rsm[ts_idx]
        cmaq_data = dict_cmaq[ts_idx]

        if valid_2d is not None:
            rsm_case_means = [np.mean(rsm_data[c][valid_2d]) for c in range(rsm_data.shape[0])]
            cmaq_case_means = [np.mean(cmaq_data[c][valid_2d]) for c in range(cmaq_data.shape[0])]
        else:
            rsm_case_means = [np.mean(rsm_data[c]) for c in range(rsm_data.shape[0])]
            cmaq_case_means = [np.mean(cmaq_data[c]) for c in range(cmaq_data.shape[0])]

        cmaq_mean_series.append(np.mean(cmaq_case_means))
        rsm_mean_series.append(np.mean(rsm_case_means))
        rsm_min_series.append(np.min(rsm_case_means))
        rsm_max_series.append(np.max(rsm_case_means))

    fig, ax = plt.subplots(figsize=(16, 5))

    ax.fill_between(dates, rsm_min_series, rsm_max_series,
                    color='grey', alpha=0.25, label='OOS Envelope (RSM)', zorder=2)

    ax.plot(dates, cmaq_mean_series, 'b-', linewidth=1.5, label='CMAQ (mean)', zorder=3)
    ax.plot(dates, rsm_mean_series, 'r-', linewidth=1.5, label='DeepRSM (mean)', zorder=4)

    ax.set_xlabel('Date')
    ax.set_ylabel(f'MDA8 O3 ({unit})')
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 15)))

    if exceedance_days:
        exc_set = set(exceedance_days)
        labels = []
        for d in sorted_days:
            if d in exc_set:
                labels.append(f'{month}/{d}*')
            else:
                labels.append(f'{month}/{d}')
        ax.set_xticks(dates)
        ax.set_xticklabels(labels, rotation=0, ha='center')
        for i, d in enumerate(sorted_days):
            if d in exc_set:
                ax.get_xticklabels()[i].set_color('red')
    else:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        fig.autofmt_xdate(rotation=0, ha='center')

    ax.legend(loc='upper right')
    ax.set_xlim(dates[0], dates[-1])

    suffix = "_PRD" if skip_non_prd else ""
    save_path = _ensure_dir(os.path.join(output_oos_dir, 'time_series'))
    fig.savefig(os.path.join(save_path, f'{project_name}_{key_name}{suffix}.png'),
                bbox_inches='tight', dpi=300)
    plt.close(fig)


def plot_2d_concentration(oos_data=None, key_name="2d_concentration", days=None, skip_non_prd=False):
    """
    绘制 2D 浓度空间分布图，展示 CMAQ Response、RSM Response 及两者差异（Delta）。

    @description:
        对每个时间步和每个 OOS case，绘制三张空间分布图：
        CMAQ Response、RSM Response、以及 RSM-CMAQ 的差值图。
        每 15 个子图保存为一张图片（每个 case 3 张子图，即每 5 个 case 一张图）。
        当 skip_non_prd=True 时，应用广东省全域掩膜排除非PRD区域，使用 cmap_delta 配色。

    @param {tuple | None} oos_data: 已有的 OOS 结果元组 (dict_rsm, dict_cmaq, dict_rsm_response,
        dict_cmaq_response, case_ids)。若为 None，则调用 get_oos_result(days) 获取。
    @param {str} key_name: 图表标题关键词，用于文件命名。
    @param {list[int] | None} days: 要评估的天数列表，仅在 oos_data 为 None 时使用。
    @param {bool} skip_non_prd: 是否排除非PRD区域（仅展示广东省全域）。默认 False。

    @return {None}: 结果保存为 PNG 图片到 output_oos_dir/2d/ 目录。

    @调用示例:
        plot_2d_concentration(oos_data=oos_data, key_name="2d_concentration", days=[6, 13, 14, 16, 19])
        plot_2d_concentration(oos_data=oos_data, key_name="2d_concentration_not_include_oth", days=[6, 13, 14], skip_non_prd=True)
    """
    dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, case_ids = _resolve_oos_data(oos_data, days)
    lons, lats = _get_lons_lats()
    save_path = _ensure_dir(os.path.join(output_oos_dir, '2d'))

    mask = None
    if skip_non_prd:
        dict_masks = get_all_masks(json_file=boundary_json_file, lat=lats, lon=lons, replaceFalseWithNan=True)
        mask = np.where(
            np.all([np.isnan(m) for _, m in dict_masks.items()], axis=0), np.nan, 1)

    for dict_data, ts_idx, is_summary in _build_2d_plot_data(
            dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response,
            case_ids, lons, lats, mask=mask):
        if skip_non_prd:
            if is_summary:
                panel_layout, value_range = (5, 5), (80, 180)
            else:
                panel_layout = (3, 5) if len(dict_data) >= 15 else (3, max(int(len(dict_data) / 3), 1))
                value_range = (-20, 20)
            fig = show_maps(dict_data, unit=unit, cmap=cmap_delta, boundary_file=boundary_file,
                            show_plot=False, show_minmax=True, show_original_grid=True,
                            show_lonlat=True, show_dependenct_colorbar=True,
                            value_range=value_range, value_format='.1f', is_tight_layout=True,
                            delta_map_settings={'cmap': cmap_delta, 'value_range': (-6, 6),
                                                'value_format': '.1f'},
                            panel_layout=panel_layout)
        else:
            panel_layout = (3, 5) if len(dict_data) >= 15 else (3, max(int(len(dict_data) / 3), 1))
            delta_range = (-2, 2) if not is_summary else (-10, 10)
            fig = show_maps(dict_data, unit=unit, cmap=cmap_conc, boundary_file=boundary_file,
                            show_plot=False, show_minmax=True, show_original_grid=True,
                            show_lonlat=True, show_dependenct_colorbar=True,
                            value_range=(80, 180), value_format='.1f',
                            delta_map_settings={'cmap': cmap_delta, 'value_range': delta_range,
                                                'value_format': '.1f'},
                            panel_layout=panel_layout)
        fig.savefig(os.path.join(save_path, f'{project_name}_D{ts_idx+1}_{key_name}_oos_cases.png'),
                    bbox_inches='tight', dpi=300)


if __name__ == '__main__':
    days = [x for x in range(1, 31)]
    oos_data_all_days = get_oos_result(days=days)
    # draw_density_plot_by_all_days_all_runs(oos_data=oos_data_all_days, key_name="All Days", days=days)
    draw_density_plot_by_all_days_all_runs(oos_data=oos_data_all_days, key_name="All Days", days=days,skip_non_prd=True)
    polluted_days = [6, 13, 14, 16, 19]
    dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, case_ids = get_oos_result(days=polluted_days)
    oos_data = (dict_rsm, dict_cmaq, dict_rsm_response, dict_cmaq_response, case_ids)
    # draw_density_plot_by_all_days_all_runs(oos_data=oos_data, key_name="All Polluted Days", days=polluted_days)
    # draw_density_plot_by_day(oos_data=oos_data, key_name="by day", days=polluted_days)
    # draw_density_plot_by_day_by_run(oos_data=oos_data, key_name="by day by run", days=polluted_days)
    
    draw_density_plot_by_all_days_all_runs(oos_data=oos_data, key_name="All Polluted Days", days=polluted_days,skip_non_prd=True)
    draw_density_plot_by_day(oos_data=oos_data, key_name="by day", days=polluted_days,skip_non_prd=True)
    draw_density_plot_by_day_by_run(oos_data=oos_data, key_name="by day by run", days=polluted_days,skip_non_prd=True)
    # plot_2d_concentration(oos_data=oos_data, key_name="2d_concentration", days=polluted_days)
    plot_2d_concentration(oos_data=oos_data, key_name="2d_concentration_not_include_oth", days=polluted_days, skip_non_prd=True)

    plot_time_series(oos_data=oos_data_all_days, key_name="time_series", days=days,
                     exceedance_days=polluted_days)
    plot_time_series(oos_data=oos_data_all_days, key_name="time_series", days=days,
                     skip_non_prd=True, exceedance_days=polluted_days)