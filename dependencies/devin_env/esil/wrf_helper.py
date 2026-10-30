'''
Author: Devin
Date: 2024-07-03 16:07:12
LastEditors: Devin
LastEditTime: 2024-10-09 11:08:40
Description: 

Copyright (c) 2024 by Devin, All Rights Reserved. 
'''
import os
import pickle
import netCDF4 as nc
import numpy as np
from tqdm.auto import tqdm
from netCDF4 import Dataset
from wrf import getvar, interplevel, to_np, latlon_coords,ALL_TIMES,extract_times
from wrf.g_rh import get_rh, get_rh_2m
from wrf.g_uvmet import get_uvmet_wspd,get_uvmet10_wspd,get_uvmet_wdir,get_uvmet10_wdir #,get_uvmet_wspd_wdir,get_uvmet10_wspd_wdir,get_uvmet,get_uvmet10
from netcdf_helper import combine_netcdf_files_with_mfdataset
#气象站点的气象变量和wrf输出文件中的变量对应关系
wrf_variables = {"Planetary_Boundary_Layer_Height":["PBLH"],
                 'Temperature_2m': ['T2'],#2m temperature,对应气象站点的温度
                 'Temperature': ['T'],
                 'Humidity': ["T","Q","PSFC"],
                 'Humidity_2m': ['T2',"Q2","PSFC"],#2m relative humidity,对应气象站点的相对湿度
                 'Pressure_Surface': ['PSFC'],
                 'Wind_Speed_10m': ['U10', 'V10'], # 10m wind speed,对应气象站点的风速
                 'Wind_Direction_10m': ['U10', 'V10'],# 10m wind direction,对应气象站点的风向
                 'Wind_Speed': ['U', 'V'], # 风速
                 'Wind_Direction': ['U', 'V'], # 风向
                 'Solar_Radiation': ['SWDOWN'],
                 'Precipitation': ['RAINC', 'RAINNC'],
                 'Cloud_Cover': ['CLDFRA']
                 }

def get_model_lat_lon_proj(model_lat_lon_file,variable_name="T2", model_pkl_file=None):
    dir=os.path.dirname(model_lat_lon_file)
    model_file=os.path.basename(model_lat_lon_file)
    model_pkl_file=os.path.join(dir,f'{model_file}.pkl') if model_pkl_file is None else model_pkl_file
    if os.path.exists(model_pkl_file):
        with open(model_pkl_file, 'rb') as file:
            cart_proj, model_lats, model_lons = pickle.load(file)
    else:       
        x,y,model_lons,model_lats,dx,dy,cart_proj=get_wrf_info(model_lat_lon_file,variable_name="T2")
        # model_lats, model_lons= to_np(lats), to_np(lons)
        with open(model_pkl_file, 'wb') as file:
            pickle.dump((cart_proj, model_lats, model_lons), file)
    return cart_proj,model_lats,model_lons

def get_wrf_info(wrf_out_file,variable_name="T2"):
    '''
    Get the x,y,lons,lats,dx,dy,cart_proj from wrf_out_file
    @param: wrf_out_file: the wrf output file
    @param: variable_name: the variable name to get the info
    @return: x,y,lons,lats,dx,dy,cart_proj: the x,y grid (lamber projection), lons,lats grid, dx,dy(grid size) and cartopy projection

    '''
    from wrf import (to_np, getvar, get_cartopy, cartopy_xlim,
                 cartopy_ylim, latlon_coords)
    import netCDF4 as nc
    dataset = nc.Dataset(wrf_out_file, 'r')
    t2 = getvar(dataset,variable_name)
    cart_proj = get_cartopy(t2)
    lats, lons =latlon_coords(t2)
    lons,lats =to_np(lons), to_np(lats)
    xlims,ylims= cartopy_xlim(t2),cartopy_ylim(t2)
    x_coords,y_coords=np.linspace(xlims[0],xlims[1],lons.shape[1]),np.linspace(ylims[0],ylims[1],lons.shape[0])   
    x,y=np.meshgrid(x_coords,y_coords) 
    dx, dy=dataset.DX,dataset.DY 
    return x,y,lons,lats,dx,dy,cart_proj 

def extract_data_from_wrf_file(wrf_file,variables=["Planetary_Boundary_Layer_Height", "Temperature_2m", "Humidity_2m", "Pressure_Surface", "Wind_Speed_10m", "Wind_Direction_10m","Solar_Radiation","Precipitation","Cloud_Cover"],date_peroid=None,convert_to_beijing_time=False):
    '''
    Extract data from WRF output file
    @param {str}: wrf_file: the WRF output file
    @param {list}: variables: the variables to extract.see wrf_variables for details。Should be one or more of wrf_variables.keys()
    @param {pd.date_range}: date_peroid: the date period to extract data；示例 date_peroid=pd.date_range("2022-09-01 00:00:00", "2022-10-01 00:00:00", freq="H")或date_peroid=[start_time,end_time], like [start_time,end_time].If None, extract all data.
    @return: 
    {dict}: variables_data: the extracted variables data
    {dict}: variables_units: the units of extracted variables    
    {dict}: global_attrs_template: the global attributes of WRF output file
    {dict}: dict_dims: the dimensions of extracted variables
    {np.array}: lats: the latitudes of WRF output file
    {np.array}: lons: the longitudes of WRF output file
    {np.array}: times: the times of WRF output file
    示例：
    dict_variable_data,dict_variable_units,global_attrs_template,dict_dims,lats,lons,time=extract_wrf_data(wrf_file,variables=["Temperature_2m", "Humidity_2m", "Pressure_Surface", "Wind_Speed_10m", "Wind_Direction_10m"])
    '''
    # 打开 WRF 文件
    ds_input = Dataset(wrf_file) 
    dict_variable_data,dict_variable_units,dict_dims = {},{},{}         
    for variable in variables:                      
        if variable in ["Wind_Speed_10m","Wind_Direction_10m","Wind_Speed","Wind_Direction"]:
            if variable =="Wind_Speed_10m":
                var_obj=get_uvmet10_wspd(ds_input, timeidx=ALL_TIMES)
            if variable =="Wind_Direction_10m":
                var_obj=get_uvmet10_wdir(ds_input, timeidx=ALL_TIMES)
            if variable =="Wind_Speed":
                var_obj=get_uvmet_wspd(ds_input, timeidx=ALL_TIMES)
            if variable =="Wind_Direction":
                var_obj=get_uvmet_wdir(ds_input, timeidx=ALL_TIMES)                              
            # # 计算风速和风向       
            # wind_speed10, wind_direction10 = get_uvmet10_wspd_wdir(ds_input, timeidx=ALL_TIMES)               
        elif variable in ["Humidity_2m","Humidity"]:
            # 计算相对湿度
            var_obj=get_rh_2m(ds_input, timeidx=ALL_TIMES) if variable=="Humidity_2m" else get_rh(ds_input, timeidx=ALL_TIMES)              
        elif variable =="Precipitation":
            # 计算降水量
            rainc=getvar(ds_input, "RAINC",timeidx=ALL_TIMES)  # RAINC：累计对流降水量
            rainnc=getvar(ds_input, "RAINNC",timeidx=ALL_TIMES)  # RAINNC：累计非对流降水量。        
            var_obj = rainc + rainnc  # 总降水量             
        else:
            wrf_var=wrf_variables[variable][0]
            var_obj = getvar(ds_input, wrf_var,timeidx=ALL_TIMES)
        if date_peroid is not None:
            # times = extract_times(ds_input, timeidx=ALL_TIMES)  # 返回 datetime 对象列表
            # # 筛选指定时间段的数据
            if convert_to_beijing_time:
                hours_offset=8
            else:
                hours_offset=0
            start_time,end_time=date_peroid[0]-pd.Timedelta(hours=hours_offset),date_peroid[-1]-pd.Timedelta(hours=hours_offset)
            # time_mask = [(t >= start_time) & (t <= end_time) for t in times] 
            # filtered_var_obj1 = var_obj[time_mask,...]  # 根据时间掩码筛选数据            
            var_obj = var_obj.sel(Time=slice(start_time, end_time))
            # dict_variable_data[variable] = to_np(filtered_var_obj) if variable not in ["Temperature_2m","Temperature"] else to_np(filtered_var_obj)- 273.15 # 转换为摄氏度
            # dict_variable_units[variable] = (filtered_var_obj.units if variable !="Precipitation" else rainc.units) if variable not in ["Temperature_2m","Temperature"] else "°C"
            # dict_dims[variable] = filtered_var_obj.dims    
        # else:             
        dict_variable_data[variable] = to_np(var_obj) if variable not in ["Temperature_2m","Temperature"] else to_np(var_obj)- 273.15 # 转换为摄氏度       
        dict_variable_units[variable] = (var_obj.units if variable !="Precipitation" else rainc.units) if variable not in ["Temperature_2m","Temperature"] else "°C"
        dict_dims[variable] = var_obj.dims            
    # 读取所有全局属性
    global_attrs_template = {
        attr: getattr(ds_input, attr) for attr in ds_input.ncattrs()
    }     
    # 提取时间和经纬度
    # time = getvar(ds_input, "Times").values  # 时间,只获取第一个时间
    times = var_obj.Time.data#extract_times(ds_input, timeidx=ALL_TIMES)  # 返回 datetime 对象列表
    lats, lons = latlon_coords(var_obj)  # 经纬度
    return dict_variable_data,dict_variable_units,dict_dims,global_attrs_template,lats,lons,times
 
def save_wrf_data(output_file,dict_dims,global_attrs_template,variables_data,variables_units=None,output_file_format="NETCDF3_CLASSIC"):
    '''
    @description: Save extracted data to a new WRF output file.
    @param {str}: output_file: the output file name
    @param {dict}: dict_dims: the dimensions of extracted variables
    @param {dict}: global_attrs_template: the global attributes of WRF output file
    @param {dict}: variables_data: the extracted variables data
    @param {dict}: variables_units: the units of extracted variables
    @param {str}: output_file_format: the output file format, default is NETCDF3_CLASSIC
    @return: None
    '''
    output_path = os.path.dirname(output_file)
    output_file_name = os.path.basename(output_file)
    if not os.path.exists(output_path):
        os.makedirs(output_path)    
    ds_output = nc.Dataset(
        output_file, "w", format=output_file_format
    )
    # 写入全局属性
    for attr_name, attr_value in global_attrs_template.items():    
        setattr(ds_output, attr_name, attr_value)
    # 创建变量
    for var_name, values in tqdm(variables_data.items(),leave=True,desc=f"Creating variables for {output_file_name}",):       
        # 写入变量属性
        dims=dict_dims[var_name]
        for idx,dim in enumerate(dims):
            if dim not in ds_output.dimensions:
                ds_output.createDimension(dim,values.shape[idx]) 
        # 创建变量       
        nc_var = ds_output.createVariable(var_name, np.float32, dims)      
        try:
            nc_var.units = variables_units[var_name] if variables_units is not None else ""
            nc_var.long_name = var_name             
            nc_var[:] = values
            ds_output.sync()  # 手动同步数据到磁盘
        except Exception as e:
            print(f"Error setting attributes for {var_name}: {e}")
    ds_output.close()
   
def extract_wrf_hourly_data(wrf_out_dir, output_wrf_file,variables=None,wrf_out_prefix="wrfout_d03_",output_wrf_file_format="NETCDF3_CLASSIC",date_peroid=None,convert_to_beijing_time=False,support_wrf_python=True):
    '''
    @description: 从 WRF 输出文件中提取指定date_peroid,变量variables的数据
    @param {str}: wrf_out_dir: WRF 输出文件所在目录
    @param {str}: output_wrf_file: 输出文件名
    @param {list}: variables: 需要提取的变量列表,如果为None，则提取所有变量,即仅仅提取文件。否则，提取指定变量,指定变量需在 wrf_variables 中定义
    @param {str}: wrf_out_prefix: WRF 输出文件名前缀，默认为 wrfout_d03_
    @param {str}: output_wrf_file_format: 输出文件格式，默认为 NETCDF3_CLASSIC
    @param {pd.date_range}: date_peroid: 日期范围，如果为None，则提取所有时间段的数据。否则，提取指定时间段的数据
    @param {bool}: convert_to_beijing_time: 是否将时间转换为北京时间，默认不转换
    @param {bool}: support_wrf_python: 是否支持 wrf-python 库，默认支持，会额外提取 XLAT , XLONG 和 Times 变量；如果不支持，则只提取variables中定义的变量
    @return: {dict}: dict_variable_data: 变量数据字典，key 为变量名,保持和variables中的顺序一致，value 为变量数据
    @return: {dict}: dict_variable_units: 变量单位字典,key 为变量名，value 为变量单位
    @return: {dict}: dict_dims: 变量维度字典,key 为变量名，value 为变量维度
    @return: {dict}: global_attrs_template: 全局属性字典
    示例：
    variables_data,variables_units,start_time=extract_wrf_hourly_data(wrf_out_dir, output_wrf_file,variables=variables,wrf_out_prefix="wrfout_d03_",output_wrf_file_format="NETCDF3_CLASSIC",date_peroid=date_peroid,convert_to_beijing_time=True)
    '''
    wrf_files = sorted(glob.glob(os.path.join(wrf_out_dir, f"{wrf_out_prefix}*")))
    extracted_wrf_variables =list(set([var for variable in variables for var in wrf_variables[variable]]) if variables is not None else [])
    combine_netcdf_files_with_mfdataset(wrf_files, output_wrf_file, extract_wrf_variables=extracted_wrf_variables, output_file_format=output_wrf_file_format, support_wrf_python=support_wrf_python)
    dict_variable_data,dict_variable_units,dict_dims,global_attrs_template,lats,lons,times=extract_data_from_wrf_file(output_wrf_file,variables=variables,date_peroid=date_peroid,convert_to_beijing_time=convert_to_beijing_time)
    return dict_variable_data,dict_variable_units,times

def extract_wrf_hourly_data_without_combining_files(wrf_out_dir, output_wrf_file,variables,wrf_out_prefix="wrfout_d03_",output_wrf_file_format="NETCDF3_CLASSIC",date_peroid=None,convert_to_beijing_time=False,support_wrf_python=True):
    '''
    Extract hourly data from WRF output files and save them to a new WRF output file.
    @param {str}: wrfout_dir: the directory of WRF output files
    @param {str}: output_wrf_file: extracted WRF output file
    @param {list}: variables: the variables to extract.see wrf_variables for details。Should be one or more of wrf_variables.keys()
    @param {str}: output_wrf_file_format: the output file format, default is NETCDF3_CLASSIC
    @param {str}: wrfout_prefix: the prefix of WRF output files, default is "wrfout_d03_";if wrfout_dir contains different domains, the prefix should be specified for each domain.like "wrfout_d01_" for domain 1.
    @return: 
    {dict}: variables_data: the extracted variables data
    {dict}: variables_units: the units of extracted variables
    {dates}: the dates of extracted data
    示例：
    dict_variable_data,dict_variable_units=extract_wrf_hourly_data(wrfout_dir, output_wrf_file,variables=["Temperature_2m", "Humidity_2m", "Pressure_Surface", "Wind_Speed_10m", "Wind_Direction_10m"],output_wrf_file_format="NETCDF3_CLASSIC",wrfout_prefix="wrfout_d03_")
    '''
    # 遍历所有 WRF 输出文件，提取数据
    wrf_files = sorted(glob.glob(os.path.join(wrf_out_dir, f"{wrf_out_prefix}*")))
    # combine_netcdf_files_with_mfdataset(wrf_files, output_wrf_file+".mfdataset.nc", variables, output_file_format=output_wrf_file_format)
    dict_variables_data = {} 
    dict_variables_dims,global_attrs_template,dates,latitudes,longitudes = {},{},None,None,None   
    for wrf_file in tqdm(wrf_files, desc="读取WRF输出文件"):#[0:3]:
        dict_data,variables_units,dims,global_attrs_template,lats,lons,times=extract_data_from_wrf_file(wrf_file,variables=variables)# extract_wrf_data_from_file(wrf_file,variables=variables)
        if len(dict_variables_dims)==0:
            dict_variables_dims,global_attrs_template,dates,latitudes,longitudes=dims.copy(),global_attrs_template,times,lats,lons          
        for name, data in dict_data.items():
            if dict_variables_data.get(name) is None:
                dict_variables_data[name] = []
            if len(dict_variables_data[name])>0 and  data.ndim!=dict_variables_data[name][-1].ndim:
                print(f"{wrf_file} 变量 {name} 维度不一致，跳过")
                continue
            dict_variables_data[name].append(data)
    variables_data = {}
    # 将所有数据沿时间维度拼接
    for var, data in dict_variables_data.items():        
        variables_data[var] = np.concatenate(data, axis=0)  # 沿时间维度拼接         
    save_wrf_data(output_wrf_file,dict_variables_dims,global_attrs_template,variables_data,variables_units=variables_units,output_file_format=output_wrf_file_format)
    # dates=pd.date_range(start_time,periods=len(variables_data[0]),freq="H")
    return variables_data,variables_units,dates

    
def calculate_specified_level_metric(file,target_variable):
    '''
    TODO: 待验证
    @description: 计算指定高度的气象变量
    @param {str}: file: WRF 输出文件
    @param {str}: target_variable: 目标气象变量
    @return: {np.array}: 指定高度的气象变量    
    '''
    wrfin = Dataset(file)
    rh = getvar(wrfin, target_variable)
    height = getvar(wrfin, "height_agl")
    pblh = getvar(wrfin, "PBLH")
    rh_pblh = interplevel(rh, height, pblh)
    return rh_pblh

# 定义函数：计算相对湿度 (RH)
def calculate_relative_humidity(q2, psfc, t2):
    '''
    TODO: 待验证
    @description: 计算相对湿度 (RH)
    @param {np.array}: q2: 2m气压 (Pa)
    @param {np.array}: psfc: 地面气压 (Pa)
    @param {np.array}: t2: 2m温度 (K)
    '''
    # 常量定义
    epsilon = 0.622  # 水汽与干空气的比值
    e0 = 6.112  # hPa
    t2_celsius = t2 - 273.15  # 转换为摄氏度
    es = e0 * np.exp((17.67 * t2_celsius) / (t2_celsius + 243.5))  # 饱和水汽压 (hPa)
    e = (q2 * psfc) / (epsilon + (1 - epsilon) * q2)  # 水汽压 (hPa)
    rh = (e / es) * 100  # 相对湿度 (%)
    return rh

def calculate_rh2(q2, psfc, t2): 
    '''
    TODO: 待验证
    @description: 计算2m相对湿度 (RH2)；
    @param {np.array}: q2: 2m气压 (Pa)
    @param {np.array}: psfc: 地面气压 (Pa)
    @param {np.array}: t2: 2m温度 (K)
    '''
    rh2 = q2 / (0.6220 * (611 * np.exp(19.8644 - 5423 / t2) / (psfc - 611 * np.exp(19.8644 - 5423 / T2)))) * 100
    return rh2

# 定义函数：计算风速和风向
def calculate_wind_speed_direction(u10, v10):
    '''
    TODO: 待验证
    @description: 计算风速和风向
    @param {np.array}: u10: 10m风速 (m/s)
    @param {np.array}: v10: 10m风速 (m/s)
    @return: {np.array}: wind_speed: 风速 (m/s)
    @return: {np.array}: wind_direction: 风向 (度)
    '''
    wind_speed = np.sqrt(u10**2 + v10**2)  # 风速
    wind_direction = (270 - np.arctan2(v10, u10) * 180 / np.pi) % 360  # 风向
    return wind_speed, wind_direction   
        
def combine_wrf_files(wrf_files,output_file,variables=None,output_file_format="NETCDF3_CLASSIC"):
    '''
    TODO: 待验证
    @description: 合并多个 WRF 输出文件
    @param {list}: wrf_files: WRF 输出文件列表
    @param {str}: output_file: 输出文件名
    @param {list}: variables: 需要提取的变量列表
    @param {str}: output_file_format: 输出文件格式
    @return: None
    '''
    import xarray as xr
    try:
        # import xarray as xr
        # ds_input1 = xr.open_mfdataset(wrf_files, combine='Times')
         # 指定要合并的维度 
        # 使用 MFDataset 函数打开多个文件并指定要合并的维度 : 主要用于读取多个 NetCDF 文件的内容;它是只读的      
        f = nc.MFDataset(wrf_files) 
        dict_variable_data,dict_variable_units,dict_dims,global_attrs_template,lats,lons,time={},{},{},{},None,None,None 
        for variable_name in variables:
            wrf_var=wrf_variables[variable_name][0]
            dict_variable_data[variable_name] = f.variables[wrf_var][:]
            dict_variable_units[variable_name] = f.variables[wrf_var].units
            dict_dims[variable_name] = f.variables[wrf_var].dimensions            
            
        # 使用 xarray 打开并合并多个文件
        # ds = xr.open_mfdataset(wrf_files, parallel=True)
        # # 保存合并后的文件为新的 NetCDF 文件   
        # ds.to_netcdf(output_file+"_xarray.nc")
        # # 关闭数据集
        # ds.close()
        # # 打开多个文件并合并它们
        # datasets = [xr.open_dataset(file) for file in wrf_files]
        # # 合并数据集
        # combined_dataset = xr.concat(datasets, dim='Time')    
        # # 将合并后的数据集保存为一天 24 小时的 NetCDF 文件
        # combined_dataset.to_netcdf(output_file)    
        # # 关闭数据集
        # combined_dataset.close()        
        
    except Exception as e:
        print(f"Error combining WRF files: {e}")

def extract_wrf_data_within_start_end_time(wrf_file,start_time,end_time,variables=None):
    '''
    TODO: 待验证
    @description: 从 WRF 输出文件中提取指定时间段的数据
    @param {str}: wrf_file: WRF 输出文件
    @param {datetime}: start_time: 开始时间
    @param {datetime}: end_time: 结束时间
    '''
    from wrf import getvar, extract_times, ALL_TIMES
    nc_dataset = Dataset(wrf_file)
    times = extract_times(nc_dataset, timeidx=ALL_TIMES)  # 返回 datetime 对象列表peroid
    # 筛选指定时间段的数据
    time_mask = [(t >= start_time) & (t <= end_time) for t in times]
    # 提取变量（例如 2 米温度 T2）
    t2 = getvar(nc_dataset, "T2", timeidx=ALL_TIMES)  # 提取所有时间的 T2 数据
    filtered_t2 = t2[time_mask, :, :]  # 根据时间掩码筛选数据 
    return filtered_t2

if __name__ == '__main__':
    import os
    import glob
    import numpy as np
    import pandas as pd
    
  
    # 定义文件路径和变量
    wrf_out_dir = "/bigdata/wrf_output_file/liuziyi/PRDNEW"  # WRF 输出文件的目录
    output_wrf_file = "/DeepLearning/mnt/Devin/data/wrf_out/2022082600-2022100200_wrf_data.nc"  # 输出文件名
    variables=["Planetary_Boundary_Layer_Height", "Temperature_2m", "Humidity_2m", "Pressure_Surface", "Wind_Speed_10m", "Wind_Direction_10m","Solar_Radiation","Precipitation","Cloud_Cover"]
    # variables=["Temperature_2m", "Humidity_2m", "Wind_Speed_10m", "Wind_Direction_10m"]

    wrf_out_prefix="wrfout_d03_"
    output_wrf_file_format="NETCDF3_CLASSIC"
    wrf_files = sorted(glob.glob(os.path.join(wrf_out_dir, f"{wrf_out_prefix}*")))    
    extracted_wrf_variables =list(set([var for variable in variables for var in wrf_variables[variable]]) if variables is not None else [])
    # extracted_wrf_variables=["T2","PBLH",]#,'XLAT', 'XLONG'
    # combine_netcdf_files_with_mfdataset(wrf_files, output_wrf_file+".mfdataset3.nc", extract_wrf_variables=extracted_wrf_variables, output_file_format=output_wrf_file_format, support_wrf_python=True)
    wrf_file=output_wrf_file+".mfdataset3.nc"
    x,y,lons,lats,dx,dy,cart_proj=get_wrf_info(wrf_file,variable_name=extracted_wrf_variables[0])
    date_peroid=pd.date_range("2022-09-01 00:00:00", "2022-10-01 00:00:00", freq="H")
    #方法1：直接提取
    dict_variable_data,dict_variable_units,dict_dims,global_attrs_template,lats,lons,times=extract_data_from_wrf_file(wrf_file,variables=variables,date_peroid=date_peroid,convert_to_beijing_time=True)
    #方法2：提取指定时间段的数据
    #region 方法1：使用 extract_data_from_wrf_file和extract_wrf_hourly_data_without_combining_files 函数提取数据
    # extract_wrf_data_from_file(wrf_file,variables=variables)
    # dates=pd.date_range(start_time,periods=len(dict_variable_data.pop(0)),freq="H")    
    variables_data,variables_units,start_time=extract_wrf_hourly_data_without_combining_files(wrf_out_dir, output_wrf_file,variables=variables,wrf_out_prefix="wrfout_d03_",output_wrf_file_format="NETCDF3_CLASSIC")
    #endregion 方法1：使用 extract_data_from_wrf_file和extract_wrf_hourly_data_without_combining_files 函数提取数据
    output_wrf_file = f"/DeepLearning/mnt/Devin/data/wrf_out/{date_peroid[0].strftime('%Y%m%d%H')}-{date_peroid[-1].strftime('%Y%m%d%H')}_wrf_data.nc"  # 输出文件名
    variables_data,variables_units,start_time=extract_wrf_hourly_data(wrf_out_dir, output_wrf_file,variables=variables,wrf_out_prefix="wrfout_d03_",output_wrf_file_format="NETCDF3_CLASSIC",date_peroid=date_peroid,convert_to_beijing_time=True)
    print(f"数据已保存到 {output_wrf_file}")
