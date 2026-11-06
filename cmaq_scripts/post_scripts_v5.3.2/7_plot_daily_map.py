import os
import sys
import numpy as np
import pandas as pd
from tqdm.auto import tqdm
import xarray as xr
import datetime

# 自定义库的导入
from esil.earth_helper import get_boundary_mask_data
from esil.rsm_helper.model_property import model_attribute
from esil.date_helper import format_date_to_year_day
from esil.netcdf_helper import get_attributes_from_netcdf_file
from esil.map_helper import get_multiple_data, show_maps
import cmaps

# 定义颜色映射
cmap_conc = cmaps.WhiteBlueGreenYellowRed
cmap_delta = cmaps.ViBlGrWhYeOrRe

def main():
    # 检查参数数量
    if len(sys.argv) < 9:
        print("Usage: python 7_plot_daily_map.py <OUTFILE> <BASELINE_CMAQ_FILE> <BEGIN_DATE> <END_DATE> <TARGET_POLLUTANT> <DOMAIN> <RUN_CASE_NAME> <BOUNDARY_FILE>")
        sys.exit(1)

    # 获取参数
    source_ncfile = sys.argv[1]  # 模型输出文件路径
    baseline_cmaq_file = sys.argv[2]  # 基线文件路径
    start_date_str = sys.argv[3]  # 开始日期字符串
    end_date_str = sys.argv[4]  # 结束日期字符串
    target_pollutant = sys.argv[5]  # 目标污染物
    domain = sys.argv[6]  # 域名
    run_case_name = sys.argv[7]  # 运行案例名称
    boundary_file = sys.argv[8]  # 边界文件路径
    maps_count= sys.argv[9] if len(sys.argv) > 9 else 16  # 每张图的子图数量
    # 设置默认边界文件
    if not boundary_file:
        boundary_file = "/DeepLearning/mnt/Devin/boundary/guangdong_cities.json"
    print("Boundary file:", boundary_file)
    # 检查文件是否存在
    if not os.path.exists(source_ncfile):
        print(f"Error: The source netCDF file '{source_ncfile}' does not exist.")
        sys.exit(1)
    has_baseline_cmaq_file=True
    if not (baseline_cmaq_file and os.path.exists(baseline_cmaq_file)):
        print(f"Error: The baseline netCDF file '{baseline_cmaq_file}' does not exist.")      
        has_baseline_cmaq_file=False    
        # sys.exit(0)#

    # 检查日期格式
    try:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError as e:
        print(f"Invalid date format: {e}. Please use YYYY-MM-DD.")
        sys.exit(1)

    # 确保开始日期小于等于结束日期
    if start_date > end_date:
        print("Error: The start date must be less than or equal to the end date.")
        sys.exit(1)

    # 获取脚本目录和输出目录
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.dirname(source_ncfile)
    output_dir = os.path.join(data_dir, f"{domain}_{run_case_name}")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 打开数据集
    source_dataset = xr.open_dataset(source_ncfile)
    if target_pollutant not in source_dataset.variables:
        print(f"Error: The target pollutant '{target_pollutant}' is not found in the source netCDF file.")
        sys.exit(1)

    grid_concentration = source_dataset.variables[target_pollutant][:, :, :, :]
    unit = source_dataset[target_pollutant].units if 'units' in source_dataset[target_pollutant].attrs else "ppbv"
    mp = model_attribute(source_ncfile)

    # 如果存在基线文件，打开基线数据集
    baseline_mda8_o3 = None
    if has_baseline_cmaq_file:
        baseline_dataset = xr.open_dataset(baseline_cmaq_file)
        if target_pollutant not in baseline_dataset.variables:
            print(f"Error: The target pollutant '{target_pollutant}' is not found in the baseline netCDF file.")
            sys.exit(1)
        baseline_mda8_o3 = baseline_dataset.variables[target_pollutant][:, :, :, :]

    # 获取日期范围
    start_year_day = format_date_to_year_day(start_date)  # 获取开始日期的年和年中的第几天, 格式为YYYYJJJ
    end_year_day = format_date_to_year_day(end_date)  # 获取结束日期的年和年中的第几天, 格式为YYYYJJJ
    days = np.arange(start_year_day, end_year_day + 1)
    sdate, edate, origin_data_shape = get_attributes_from_netcdf_file(source_ncfile)
    if sdate == 2022244 and "2022-08-27" in source_ncfile:
        sdate = 2022239
    start_day_idx = start_year_day - sdate
    if start_day_idx < 0:
        print(f"Error: The start date {start_date_str} is before the data start date {sdate} from {source_ncfile} file. Using start_day_idx=0 instead.")     
        start_day_idx=0   
        
    # 准备数据字典
    dict_data,dict_response_data = {},{}
    last_day = start_date.strftime('%Y%m%d')
    last_response_day = start_date.strftime('%Y%m%d')
    # map_type = "response map" if has_baseline_cmaq_file else "map"    
    
    # 遍历日期范围
    for idx, day in enumerate(tqdm(days)):
        day_str = (start_date + datetime.timedelta(days=idx)).strftime('%Y%m%d')      
        if has_baseline_cmaq_file and (baseline_cmaq_file != source_ncfile):
            # 计算浓度差值
            concentration_difference = baseline_mda8_o3[start_day_idx + idx, 0, ...] - grid_concentration[start_day_idx + idx, 0, ...]
            get_multiple_data(
                dict_response_data,
                dataset_name=f"{day_str}_{target_pollutant}_Response",
                variable_name="",
                grid_x=mp.lons,
                grid_y=mp.lats,
                grid_concentration=concentration_difference,
                file_name="",
                is_delta=True,
            )
        # else:
        # 获取浓度
        get_multiple_data(
            dict_data,
            dataset_name=f"{day_str}_{target_pollutant}",
            variable_name="",
            grid_x=mp.lons,
            grid_y=mp.lats,
            grid_concentration=grid_concentration[start_day_idx + idx, 0, ...],
            file_name="",
            is_delta=False,
        )
        # 如果数据字典达到12个，保存图像并重置数据字典
        if len(dict_data) == maps_count:
            fig = show_maps(
                dict_data,
                unit=unit,
                projection=mp.projection,
                cmap=cmap_conc,
                boundary_file=boundary_file,
                show_plot=False,
                show_minmax=True,
                show_original_grid=True,
                show_lonlat=True,
                show_dependenct_colorbar=True,
                value_format=".1f",
                is_wrf_out_data=True,
                panel_layout=0,
                delta_map_settings={'cmap': cmap_delta, 'value_range': (None, None), 'value_format': '.2f'}
            )
            fig.savefig(f"{output_dir}/{domain}_{run_case_name}_{last_day}-{day_str}_{target_pollutant}_map.png", dpi=300)
            dict_data = {}
            last_day = (start_date + datetime.timedelta(days=idx+1)).strftime('%Y%m%d')
         # 如果数据字典达到12个，保存图像并重置数据字典
        if len(dict_response_data) == maps_count:
            fig = show_maps(
                dict_response_data,
                unit=unit,
                projection=mp.projection,
                cmap=cmap_delta,
                boundary_file=boundary_file,
                show_plot=False,
                show_minmax=True,
                show_original_grid=True,
                show_lonlat=True,
                show_dependenct_colorbar=True,
                value_format=".1f",
                is_wrf_out_data=True,
                panel_layout=0,
                delta_map_settings={'cmap': cmap_delta, 'value_range': (None, None), 'value_format': '.2f'}
            )
            fig.savefig(f"{output_dir}/{domain}_{run_case_name}_{last_response_day}-{day_str}_{target_pollutant}_response_map.png", dpi=300)
            dict_response_data = {}
            last_response_day = (start_date + datetime.timedelta(days=idx+1)).strftime('%Y%m%d')
    # 保存剩余的图像
    if len(dict_data) > 0:
        fig = show_maps(
            dict_data,
            unit=unit,
            projection=mp.projection,
            cmap=cmap_conc,
            boundary_file=boundary_file,
            show_plot=False,
            show_minmax=True,
            show_original_grid=True,
            show_lonlat=True,
            show_dependenct_colorbar=True,
            value_format=".1f",
            is_wrf_out_data=True,
            panel_layout=0,
            delta_map_settings={'cmap': cmap_delta, 'value_range': (None, None), 'value_format': '.2f'}
        )
        fig.savefig(f"{output_dir}/{domain}_{run_case_name}_{last_day}-{day_str}_{target_pollutant}_map.png", dpi=300)
    if len(dict_response_data) > 0:
        fig = show_maps(
            dict_response_data,
            unit=unit,
            projection=mp.projection,
            cmap=cmap_delta,
            boundary_file=boundary_file,
            show_plot=False,
            show_minmax=True,
            show_original_grid=True,
            show_lonlat=True,
            show_dependenct_colorbar=True,
            value_format=".1f",
            is_wrf_out_data=True,
            panel_layout=0,
            delta_map_settings={'cmap': cmap_delta, 'value_range': (None, None), 'value_format': '.2f'}
        )
        fig.savefig(f"{output_dir}/{domain}_{run_case_name}_{last_response_day}-{day_str}_{target_pollutant}_response_map.png", dpi=300)
    print("Done!")

if __name__ == "__main__":
     # 直接给 sys.argv 赋值进行调试
    # sys.argv = [
    #     "8_plot_daily_map.py",
    #     "/backupdata/devin/cmaq_output/Daily_COMBINE_ACONC_v532_D1_cn2zero_PRD_all_layers_2022-08-27_2022-09-30_18species.nc",
    #     "/backupdata/devin/cmaq_output/Daily_COMBINE_ACONC_v532_D1_base_PRD_all_layers_2022-08-27_2022-09-30_18species.nc",
    #     "2022-08-30",
    #     "2022-09-24",
    #     "O3_MDA8",
    #     "D1",
    #     "cn2zero",
    #     # "/DeepLearning/mnt/Devin/boundary/guangdong_cities.json"
    #      "/DeepLearning/mnt/Devin/boundary/China.json"
    # ]
    # 添加调试信息
    print("Starting the script...")
    print(f"Source netCDF file: {sys.argv[1]}")
    print(f"Baseline netCDF file: {sys.argv[2]}")
    print(f"Start date: {sys.argv[3]}")
    print(f"End date: {sys.argv[4]}")
    print(f"Target pollutant: {sys.argv[5]}")
    print(f"Domain: {sys.argv[6]}")
    print(f"Run case name: {sys.argv[7]}")
    print(f"Boundary file: {sys.argv[8]}")    
    main()
    print("Script completed successfully.")

    
