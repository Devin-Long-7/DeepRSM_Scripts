import netCDF4 as nc
import pandas as pd
import numpy as np
import xarray as xr
from datetime import datetime
from tqdm.auto import tqdm
from esil.date_helper import format_date_to_year_day
import os

def validate_file_length(source_path,start_year_day, end_year_day,input_file_prefix):
    nc_files=[]
    not_exist_files=[]
    for runday in range(start_year_day, end_year_day + 1):
        if '12US' in input_file_prefix:
            runday_str = datetime.strptime(f"{runday}", "%Y%j").strftime("%Y%m%d")
            nc_file = os.path.join(source_path, f"{input_file_prefix}_{runday_str}.nc")
        else:
            nc_file = os.path.join(source_path, f"{input_file_prefix}_{runday}.nc")
        if not os.path.exists(nc_file):
            not_exist_files.append(nc_file)
        nc_files.append(nc_file)
    if len(nc_files)==0:
        print(f"No {input_file_prefix} files found in {source_path}")
        return False  
    if len(not_exist_files)>0:
        file_str=", ".join(not_exist_files)
        print(f"The following {input_file_prefix} files not exist: {file_str}")
        return False
    return True


def extract_monthly_data(
    source_path,
    output_path,
    start_date,
    end_date,  
    layer_index=0,
    input_file_prefix="CCTM_ACONC_PRD",
    output_file_name="ACONC.nc",
    output_file_with_parent_folder=False,
    output_file_format="NETCDF3_CLASSIC",
    cmaq_version="5.3.2"
):
    """
    @description: 将CMAQ模拟小时结果提取地表层（0层）的18种污染物（O3、NO2、NO、NOx、HNO3、H2O2、N2O5、 FORM、HONO、OH、ISOP、TERP、ASO4IJ、ANO3IJ、ANH4IJ、ASOCI、ASOCJ、ASOCIJ、PM25_TOT、SO2、NH3、VOC），并处理为日均数据，并写入NetCDF文件
    @param {str} source_path: 源数据路径，即CMAQ模拟结果所在的文件夹
    @param {str} output_path: 输出路径
    @param {int} layer_index: 层数索引，默认为0，即提取地表层的数据,如果指定为None，则提取所有层的数据
    @param {str, datetime.datetime, int} start_date: 开始日期,可以是datetime.datetime对象，也可以是字符串，格式为YYYYMMDD或YYYYJJJ
    @param {str, datetime.datetime, int} end_date: 结束日期，,可以是datetime.datetime对象，也可以是字符串，格式为YYYYMMDD或YYYYJJJ
    @param {str} input_file_prefix: 输入文件前缀,默认为CCTM_ACONC_PRD
    @param {str} output_file_name: 输出文件名，默认为ACONC.nc
    @param {bool} output_file_with_parent_folder: 输出文件是否包含父文件夹名称，默认为False; False: 输出文件名为output_file_prefix.output_file_suffix; True: 输出文件名为output_file_prefix.parent_folder_name.output_file_suffix
    @param {str} output_file_format: 输出文件格式，默认为NETCDF3_CLASSIC；
    @param {str} cmaq_version: CMAQ版本，默认为5.3.2
    @return: None
    @example:
    >>> extract_daily_data(
    >>>     source_path="/data/cmaq/20220101",
    >>>     output_path="/data/cmaq/daily_data",
    >>>     start_date="20220901",
    >>>     end_date="20220930",
    >>>     input_file_prefix="CCTM_ACONC_PRD",
    >>>     output_file_name="ACONC.nc",
    >>>     output_file_with_parent_folder=False,
    >>>     output_file_format="NETCDF3_CLASSIC",
    >>> )

    """
    start_year_day = format_date_to_year_day(
        start_date
    )  # 获取开始日期的年和年中的第几天,格式为YYYYJJJ
    end_year_day = format_date_to_year_day(
        end_date
    )  # 获取结束日期的年和年中的第几天,格式为YYYYJJJ
    # 验证文件长度是否一致
    is_pass=validate_file_length(source_path, start_year_day, end_year_day, input_file_prefix)
    if not is_pass:
        return
    parent_folder_name = os.path.basename(source_path)
 
    if '12US' in input_file_prefix:
        nc_file = os.path.join(source_path, f"{input_file_prefix}_{start_date}.nc")
    else:
        nc_file = os.path.join(source_path, f"{input_file_prefix}_{start_year_day}.nc")
    with nc.Dataset(nc_file, "r") as ds_temp:
        variable_name = "NO"
        if variable_name not in ds_temp.variables:
            variable_name = list(ds_temp.variables.keys())[-1]
        layer,row, col = ds_temp.variables[variable_name].shape[-3:]
        layer_count = layer if layer_index is None else 1
        data_shape = (end_year_day - start_year_day + 1, layer_count, row, col)

    row, col = data_shape[-2], data_shape[-1]
    layer_symbol = slice(None) if layer_index is None else layer_index
    # 定义变量
    O3 = np.zeros(data_shape, dtype=float)
    O3_d_avg = np.zeros(data_shape, dtype=float)
    O3d = np.zeros(data_shape, dtype=float)
    NO2 = np.zeros(data_shape, dtype=float)
    NO = np.zeros(data_shape, dtype=float)
    NOx = np.zeros(data_shape, dtype=float)
    HNO3 = np.zeros(data_shape, dtype=float)
    H2O2 = np.zeros(data_shape, dtype=float)
    N2O5 = np.zeros(data_shape, dtype=float)
    FORM = np.zeros(data_shape, dtype=float)
    HONO = np.zeros(data_shape, dtype=float)
    OH = np.zeros(data_shape, dtype=float)
    ISOP = np.zeros(data_shape, dtype=float)
    TERP = np.zeros(data_shape, dtype=float)
    ASO4IJ = np.zeros(data_shape, dtype=float)
    ANO3IJ = np.zeros(data_shape, dtype=float)
    ANH4IJ = np.zeros(data_shape, dtype=float)
    ASOCI = np.zeros(data_shape, dtype=float)
    ASOCJ = np.zeros(data_shape, dtype=float)
    ASOCIJ = np.zeros(data_shape, dtype=float)
    PM25_TOT = np.zeros(data_shape, dtype=float)
    PM25 = np.zeros((24, layer_count, row, col), dtype=float)
    SO2 = np.zeros(data_shape, dtype=float)
    NH3 = np.zeros(data_shape, dtype=float)
    VOC = np.zeros(data_shape, dtype=float)
    # suffix="nc"#scen_idx+1
    output_file_prefix = os.path.splitext(output_file_name)[0]
    output_file_suffix = os.path.splitext(output_file_name)[1]
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    output_file = os.path.join(
        output_path,
        (
            output_file_name
            if not output_file_with_parent_folder
            else f"{output_file_prefix}{'_'+parent_folder_name}{output_file_suffix}"
        ),
    )
    ds_output = nc.Dataset(
        output_file, "w", format=output_file_format
    )  # format='NETCDF4'
    # print(output_file)
    tqdm.write(f"Creating {os.path.basename(output_file)}...")
    
    # 定义维度
    # tqdm.write(f"start processing data from {source_path}...")
    for runday in tqdm(
        range(start_year_day, end_year_day + 1),
        leave=False,
        desc=f"Processing {parent_folder_name}",
    ):
        day_index = runday - start_year_day
        if '12US' in input_file_prefix:
            runday_str = datetime.strptime(f"{runday}", "%Y%j").strftime("%Y%m%d")
            nc_file = os.path.join(source_path, f"{input_file_prefix}_{runday_str}.nc")
        else:
            runday_str = runday
            nc_file = os.path.join(source_path, f"{input_file_prefix}_{runday}.nc")
        if not os.path.exists(nc_file):
            print(f"{nc_file} not exists")
        # print(f"Loading {nc_file}...")
        tqdm.write(f"Loading {parent_folder_name}/{os.path.basename(nc_file)}...")
        ds_aconc = nc.Dataset(nc_file, "r")
        if cmaq_version == "5.3.2":
            ds_apmdiag = nc.Dataset(
                f"{source_path}/{input_file_prefix.replace('CCTM_ACONC','CCTM_APMDIAG')}_{runday_str}.nc",
                "r",
            )  # 气溶胶CCTM_APMDIAG_PRD
        elif cmaq_version == "5.4":
            ds_apmdiag = nc.Dataset(
                f"{source_path}/{input_file_prefix.replace('CCTM_ACONC','CCTM_AELMO')}_{runday_str}.nc",
                "r",
            )
        
        SO2[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["SO2"][:, layer_symbol, :, :], axis=0) * 1000
        )
        NO2[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["NO2"][:, layer_symbol, :, :], axis=0) * 1000
        )
        NO[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["NO"][:, layer_symbol, :, :], axis=0) * 1000
        )
        NH3[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["NH3"][:, layer_symbol, :, :], axis=0) * 1000
        )
        HONO[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["HONO"][:, layer_symbol, :, :], axis=0) * 1000
        )
        HNO3[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["HNO3"][:, layer_symbol, :, :], axis=0) * 1000
        )
        H2O2[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["H2O2"][:, layer_symbol, :, :], axis=0) * 1000
        )
        N2O5[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["N2O5"][:, layer_symbol, :, :], axis=0) * 1000
        )
        FORM[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["FORM"][:, layer_symbol, :, :], axis=0) * 1000
        )
        OH[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["OH"][:, layer_symbol, :, :], axis=0) * 1000
        )
        ISOP[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["ISOP"][:, layer_symbol, :, :], axis=0) * 1000
        )
        TERP[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["TERP"][:, layer_symbol, :, :], axis=0) * 1000
        )
        O3_d_avg[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["O3"][:, layer_symbol, :, :], axis=0) * 1000
        )

        ASO4IJ[day_index, layer_symbol, :, :] = np.mean(
            ds_aconc.variables["ASO4I"][:, layer_symbol, :, :], axis=0
        ) + np.mean(ds_aconc.variables["ASO4J"][:, layer_symbol, :, :], axis=0)
        ANO3IJ[day_index, layer_symbol, :, :] = np.mean(
            ds_aconc.variables["ANO3I"][:, layer_symbol, :, :], axis=0
        ) + np.mean(ds_aconc.variables["ANO3J"][:, layer_symbol, :, :], axis=0)
        ANH4IJ[day_index, layer_symbol, :, :] = np.mean(
            ds_aconc.variables["ANH4I"][:, layer_symbol, :, :], axis=0
        ) + np.mean(ds_aconc.variables["ANH4J"][:, layer_symbol, :, :], axis=0)

        # 处理有机物
        ASOCI[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["ALVOO1I"][:, layer_symbol, :, :], axis=0) / 2.27
            + np.mean(ds_aconc.variables["ALVOO2I"][:, layer_symbol, :, :], axis=0) / 2.06
            + np.mean(ds_aconc.variables["ASVOO1I"][:, layer_symbol, :, :], axis=0) / 1.88
            + np.mean(ds_aconc.variables["ASVOO2I"][:, layer_symbol, :, :], axis=0) / 1.73
        )
        ASOCJ[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["AISO1J"][:, layer_symbol, :, :], axis=0) / 2.20
            + np.mean(ds_aconc.variables["AISO2J"][:, layer_symbol, :, :], axis=0) / 2.23
            + np.mean(ds_aconc.variables["AISO3J"][:, layer_symbol, :, :], axis=0) / 2.80
            + np.mean(ds_aconc.variables["AMT1J"][:, layer_symbol, :, :], axis=0) / 1.67
            + np.mean(ds_aconc.variables["AMT2J"][:, layer_symbol, :, :], axis=0) / 1.67
            + np.mean(ds_aconc.variables["AMT3J"][:, layer_symbol, :, :], axis=0) / 1.72
            + np.mean(ds_aconc.variables["AMT4J"][:, layer_symbol, :, :], axis=0) / 1.53
            + np.mean(ds_aconc.variables["AMT5J"][:, layer_symbol, :, :], axis=0) / 1.57
            + np.mean(ds_aconc.variables["AMT6J"][:, layer_symbol, :, :], axis=0) / 1.40
            + np.mean(ds_aconc.variables["AMTNO3J"][:, layer_symbol, :, :], axis=0) / 1.90
            + np.mean(ds_aconc.variables["AMTHYDJ"][:, layer_symbol, :, :], axis=0) / 1.54
            + np.mean(ds_aconc.variables["AGLYJ"][:, layer_symbol, :, :], axis=0) / 2.13
            + np.mean(ds_aconc.variables["ASQTJ"][:, layer_symbol, :, :], axis=0) / 1.52
            + np.mean(ds_aconc.variables["AORGCJ"][:, layer_symbol, :, :], axis=0) / 2.00
            + np.mean(ds_aconc.variables["AOLGBJ"][:, layer_symbol, :, :], axis=0) / 2.10
            + np.mean(ds_aconc.variables["AOLGAJ"][:, layer_symbol, :, :], axis=0) / 2.50
            + np.mean(ds_aconc.variables["ALVOO1J"][:, layer_symbol, :, :], axis=0) / 2.27
            + np.mean(ds_aconc.variables["ALVOO2J"][:, layer_symbol, :, :], axis=0) / 2.06
            + np.mean(ds_aconc.variables["ASVOO1J"][:, layer_symbol, :, :], axis=0) / 1.88
            + np.mean(ds_aconc.variables["ASVOO2J"][:, layer_symbol, :, :], axis=0) / 1.73
            + np.mean(ds_aconc.variables["ASVOO3J"][:, layer_symbol, :, :], axis=0) / 1.60
            + np.mean(ds_aconc.variables["APCSOJ"][:, layer_symbol, :, :], axis=0) / 2.00
            + np.mean(ds_aconc.variables["AAVB1J"][:, layer_symbol, :, :], axis=0) / 2.70
            + np.mean(ds_aconc.variables["AAVB2J"][:, layer_symbol, :, :], axis=0) / 2.35
            + np.mean(ds_aconc.variables["AAVB3J"][:, layer_symbol, :, :], axis=0) / 2.17
            + np.mean(ds_aconc.variables["AAVB4J"][:, layer_symbol, :, :], axis=0) / 1.99
        )
        # 计算ASOCIJ
        ASOCIJ[day_index, layer_symbol, :, :] = (
            ASOCI[day_index, layer_symbol, :, :] + ASOCJ[day_index, layer_symbol, :, :]
        )

        # 计算ATOTI（不求均值，直接相加）
        ATOTI = (
            ds_aconc.variables["ASO4I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANO3I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANH4I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANAI"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACLI"][:, layer_symbol, :, :]
            + ds_aconc.variables["AECI"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOTHRI"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVPO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO2I"][:, layer_symbol, :, :]
            + ds_aconc.variables["APOCI"][:, layer_symbol, :, :]
            + ds_aconc.variables["APNCOMI"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO2I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO2I"][:, layer_symbol, :, :]
        )
        # 计算ATOTJ（不求均值，直接相加）
        ATOTJ = (
            ds_aconc.variables["ASO4J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANH4J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANAJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACLJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AECJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOTHRJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AFEJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASIJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ATIJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACAJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMGJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMNJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AALJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AKJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVPO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["APOCJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AIVPO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["APNCOMJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AISO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AISO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AISO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT4J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT5J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT6J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMTNO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMTHYDJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AGLYJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASQTJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AORGCJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOLGBJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOLGAJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["APCSOJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB4J"][:, layer_symbol, :, :]
        )
        # 计算ATOTK
        ATOTK = (
            ds_aconc.variables["ASOIL"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACORS"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASEACAT"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACLK"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASO4K"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANO3K"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANH4K"][:, layer_symbol, :, :]
        )
        # ATOTI - 气溶胶的总浓度（以微克每立方米为单位）在**Aitken模式（Aitken mode）**的粒径范围内。Aitken模式通常表示非常细的颗粒物，粒径范围通常为0.01微米到0.1微米。
        # ATOTJ - 气溶胶的总浓度（以微克每立方米为单位）在**积聚模式（Accumulation mode）**的粒径范围内。积聚模式的颗粒物粒径通常在0.1微米到1微米之间。
        # ATOTK - 气溶胶的总浓度（以微克每立方米为单位）在**粗粒模式（Coarse mode）**的粒径范围内。粗粒模式的颗粒物粒径通常大于1微米。
        # 计算PM25
        PM25[:, layer_symbol, :, :] = (
            ATOTI[...] * ds_apmdiag.variables["PM25AT"][:, layer_symbol, :, :]  # Aitken 模态、
            + ATOTJ[...] * ds_apmdiag.variables["PM25AC"][:, layer_symbol, :, :]  # 积聚模态
            + ATOTK[...] * ds_apmdiag.variables["PM25CO"][:, layer_symbol, :, :]  # 粗颗粒模态
        )
        PM25_TOT[day_index, layer_symbol, :, :] = np.mean(PM25[:, layer_symbol, :, :], axis=0)
        # 计算VOC
        VOC[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["PAR"][:, layer_symbol, :, :], axis=0)
            + np.mean(ds_aconc.variables["ETHA"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["PRPA"][:, layer_symbol, :, :], axis=0) * 3
            + np.mean(ds_aconc.variables["MEOH"][:, layer_symbol, :, :], axis=0)
            + np.mean(ds_aconc.variables["ETH"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["ETOH"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["OLE"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["ACET"][:, layer_symbol, :, :], axis=0) * 3
            + np.mean(ds_aconc.variables["TOL"][:, layer_symbol, :, :], axis=0) * 7
            + np.mean(ds_aconc.variables["XYLMN"][:, layer_symbol, :, :], axis=0) * 8
            + np.mean(ds_aconc.variables["BENZENE"][:, layer_symbol, :, :], axis=0) * 6
            + np.mean(ds_aconc.variables["FORM"][:, layer_symbol, :, :], axis=0)
            + np.mean(ds_aconc.variables["GLY"][:, layer_symbol, :, :], axis=0) * 3
            + np.mean(ds_aconc.variables["KET"][:, layer_symbol, :, :], axis=0) * 4
            + np.mean(ds_aconc.variables["ETHY"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["ALD2"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["IOLE"][:, layer_symbol, :, :], axis=0) * 4
            + np.mean(ds_aconc.variables["ALDX"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["ISOP"][:, layer_symbol, :, :], axis=0) * 5
            + np.mean(ds_aconc.variables["TERP"][:, layer_symbol, :, :], axis=0) * 10
            + np.mean(ds_aconc.variables["NAPH"][:, layer_symbol, :, :], axis=0) * 10
            + np.mean(ds_aconc.variables["APIN"][:, layer_symbol, :, :], axis=0) * 10
        ) * 1000

        # 计算NOx
        NOx[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["NO2"][:, layer_symbol, :, :], axis=0)
            + np.mean(ds_aconc.variables["NO"][:, layer_symbol, :, :], axis=0)
        ) * 1000

        # 处理O3 8小时最大值
        O3_8h = np.zeros((17, layer_count,row, col), dtype=float)
        var = ds_aconc.variables["O3"][:, layer_symbol, :, :] * 1000
        for t in range(17):
            O3_8h[t,layer_symbol, :, :] = np.mean(var[t : t + 8, ...], axis=0)
        O3d[day_index, layer_symbol, :, :] = np.max(O3_8h, axis=0)

    # 将数据写入NetCDF文件
    # ds_output.createDimension("TSTEP", data_shape[0])
    ds_output.createDimension("TSTEP", 1)
    ds_output.createDimension("LAY", data_shape[1])
    ds_output.createDimension("ROW", data_shape[2])
    ds_output.createDimension("COL", data_shape[3])
    variables_data = {
        "SO2": np.mean(SO2, axis=0),
        "NO2": np.mean(NO2, axis=0),
        "NO": np.mean(NO, axis=0),
        "HNO3": np.mean(HNO3, axis=0),
        "H2O2": np.mean(H2O2, axis=0),
        "HONO": np.mean(HONO, axis=0),
        "N2O5": np.mean(N2O5, axis=0),
        "FORM": np.mean(FORM, axis=0),
        "O3_US": np.mean(O3d, axis=0),
        "O3_CN": np.mean(O3d * 48 / 24.45, axis=0),
        "OH": np.mean(OH, axis=0),
        "ISOP": np.mean(ISOP, axis=0),
        "TERP": np.mean(TERP, axis=0),
        "ASO4IJ": np.mean(ASO4IJ, axis=0),
        "ANO3IJ": np.mean(ANO3IJ, axis=0),
        "ANH4IJ": np.mean(ANH4IJ, axis=0),
        "ASOCIJ": np.mean(ASOCIJ, axis=0),
        "PM25_TOT": np.mean(PM25_TOT, axis=0),
        "NH3": np.mean(NH3, axis=0),
        "O3": np.mean(O3_d_avg, axis=0),
        "VOC": np.mean(VOC, axis=0),
        "NOx": np.mean(NOx, axis=0),
    }
    variables_units = {
        "SO2": "ppb",
        "NO2": "ppb",
        "NO": "ppb",
        "HNO3": "ppb",
        "H2O2": "ppb",
        "HONO": "ppb",
        "N2O5": "ppb",
        "FORM": "ppb",
        "O3_US": "ppb",
        "O3_CN": "μg/m3",
        "OH": "ppb",
        "ISOP": "ppb",
        "TERP": "ppb",
        "ASO4IJ": "μg/m3",
        "ANO3IJ": "μg/m3",
        "ANH4IJ": "μg/m3",
        "ASOCIJ": "μg/m3",
        "PM25_TOT": "μg/m3",
        "NH3": "ppb",
        "O3": "ppb",
        "VOC": "ppb",
        "NOx": "ppb",
    }
    # 写入变量
    for var_name, values in tqdm(
        variables_data.items(),
        leave=True,
        desc=f"Writing variables for {parent_folder_name}",
    ):
        nc_var = ds_output.createVariable(
            var_name, np.float32, ("TSTEP", "LAY", "ROW", "COL")
        )
        nc_var.units = variables_units[var_name]
        nc_var.long_name = var_name
        nc_var[:] = values
    # 读取所有全局属性
    global_attrs_template = {
        attr: getattr(ds_aconc, attr) for attr in ds_aconc.ncattrs()
    }
    # 写入全局属性
    for attr_name, attr_value in global_attrs_template.items():
        if attr_name == "TSTEP":
            attr_value = attr_value * 24  # 将小时转换为天
        setattr(ds_output, attr_name, attr_value)
    ds_output.close()
    print(f"finished processing {parent_folder_name}...")
    return output_file



def extract_daily_data(
    source_path,
    output_path,
    start_date,
    end_date,  
    layer_index=0,
    input_file_prefix="CCTM_ACONC_PRD",
    output_file_name="ACONC.nc",
    output_file_with_parent_folder=False,
    output_file_format="NETCDF3_CLASSIC",
    cmaq_version="5.3.2"
):
    """
    @description: 将CMAQ模拟小时结果提取地表层（0层）的18种污染物（O3、NO2、NO、NOx、HNO3、H2O2、N2O5、 FORM、HONO、OH、ISOP、TERP、ASO4IJ、ANO3IJ、ANH4IJ、ASOCI、ASOCJ、ASOCIJ、PM25_TOT、SO2、NH3、VOC），并处理为日均数据，并写入NetCDF文件
    @param {str} source_path: 源数据路径，即CMAQ模拟结果所在的文件夹
    @param {str} output_path: 输出路径
    @param {int} layer_index: 层数索引，默认为0，即提取地表层的数据,如果指定为None，则提取所有层的数据
    @param {str, datetime.datetime, int} start_date: 开始日期,可以是datetime.datetime对象，也可以是字符串，格式为YYYYMMDD或YYYYJJJ
    @param {str, datetime.datetime, int} end_date: 结束日期，,可以是datetime.datetime对象，也可以是字符串，格式为YYYYMMDD或YYYYJJJ
    @param {str} input_file_prefix: 输入文件前缀,默认为CCTM_ACONC_PRD
    @param {str} output_file_name: 输出文件名，默认为ACONC.nc
    @param {bool} output_file_with_parent_folder: 输出文件是否包含父文件夹名称，默认为False; False: 输出文件名为output_file_prefix.output_file_suffix; True: 输出文件名为output_file_prefix.parent_folder_name.output_file_suffix
    @param {str} output_file_format: 输出文件格式，默认为NETCDF3_CLASSIC；
    @param {str} cmaq_version: CMAQ版本，默认为5.3.2
    @return: None
    @example:
    >>> extract_daily_data(
    >>>     source_path="/data/cmaq/20220101",
    >>>     output_path="/data/cmaq/daily_data",
    >>>     start_date="20220901",
    >>>     end_date="20220930",
    >>>     input_file_prefix="CCTM_ACONC_PRD",
    >>>     output_file_name="ACONC.nc",
    >>>     output_file_with_parent_folder=False,
    >>>     output_file_format="NETCDF3_CLASSIC",
    >>> )

    """
    start_year_day = format_date_to_year_day(
        start_date
    )  # 获取开始日期的年和年中的第几天,格式为YYYYJJJ
    end_year_day = format_date_to_year_day(
        end_date
    )  # 获取结束日期的年和年中的第几天,格式为YYYYJJJ
    # 验证文件长度是否一致
    is_pass=validate_file_length(source_path, start_year_day, end_year_day, input_file_prefix)
    if not is_pass:
        return
    parent_folder_name = os.path.basename(source_path)
 
    if '12US' in input_file_prefix:
        nc_file = os.path.join(source_path, f"{input_file_prefix}_{start_date}.nc")
    else:
        nc_file = os.path.join(source_path, f"{input_file_prefix}_{start_year_day}.nc")
    with nc.Dataset(nc_file, "r") as ds_temp:
        variable_name = "NO"
        if variable_name not in ds_temp.variables:
            variable_name = list(ds_temp.variables.keys())[-1]
        layer,row, col = ds_temp.variables[variable_name].shape[-3:]
        layer_count = layer if layer_index is None else 1
        data_shape = (end_year_day - start_year_day + 1, layer_count, row, col)

    row, col = data_shape[-2], data_shape[-1]
    layer_symbol = slice(None) if layer_index is None else layer_index
    # 定义变量
    O3 = np.zeros(data_shape, dtype=float)
    O3_d_avg = np.zeros(data_shape, dtype=float)
    O3d = np.zeros(data_shape, dtype=float)
    NO2 = np.zeros(data_shape, dtype=float)
    NO = np.zeros(data_shape, dtype=float)
    NOx = np.zeros(data_shape, dtype=float)
    HNO3 = np.zeros(data_shape, dtype=float)
    H2O2 = np.zeros(data_shape, dtype=float)
    N2O5 = np.zeros(data_shape, dtype=float)
    FORM = np.zeros(data_shape, dtype=float)
    HONO = np.zeros(data_shape, dtype=float)
    OH = np.zeros(data_shape, dtype=float)
    ISOP = np.zeros(data_shape, dtype=float)
    TERP = np.zeros(data_shape, dtype=float)
    ASO4IJ = np.zeros(data_shape, dtype=float)
    ANO3IJ = np.zeros(data_shape, dtype=float)
    ANH4IJ = np.zeros(data_shape, dtype=float)
    ASOCI = np.zeros(data_shape, dtype=float)
    ASOCJ = np.zeros(data_shape, dtype=float)
    ASOCIJ = np.zeros(data_shape, dtype=float)
    PM25_TOT = np.zeros(data_shape, dtype=float)
    PM25 = np.zeros((24, layer_count, row, col), dtype=float)
    SO2 = np.zeros(data_shape, dtype=float)
    NH3 = np.zeros(data_shape, dtype=float)
    VOC = np.zeros(data_shape, dtype=float)
    # suffix="nc"#scen_idx+1
    output_file_prefix = os.path.splitext(output_file_name)[0]
    output_file_suffix = os.path.splitext(output_file_name)[1]
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    output_file = os.path.join(
        output_path,
        (
            output_file_name
            if not output_file_with_parent_folder
            else f"{output_file_prefix}{'_'+parent_folder_name}{output_file_suffix}"
        ),
    )
    ds_output = nc.Dataset(
        output_file, "w", format=output_file_format
    )  # format='NETCDF4'
    # print(output_file)
    tqdm.write(f"Creating {os.path.basename(output_file)}...")
    
    # 定义维度
    # tqdm.write(f"start processing data from {source_path}...")
    for runday in tqdm(
        range(start_year_day, end_year_day + 1),
        leave=False,
        desc=f"Processing {parent_folder_name}",
    ):
        day_index = runday - start_year_day
        if '12US' in input_file_prefix:
            runday_str = datetime.strptime(f"{runday}", "%Y%j").strftime("%Y%m%d")
            nc_file = os.path.join(source_path, f"{input_file_prefix}_{runday_str}.nc")
        else:
            runday_str = runday
            nc_file = os.path.join(source_path, f"{input_file_prefix}_{runday}.nc")
        if not os.path.exists(nc_file):
            print(f"{nc_file} not exists")
        # print(f"Loading {nc_file}...")
        tqdm.write(f"Loading {parent_folder_name}/{os.path.basename(nc_file)}...")
        ds_aconc = nc.Dataset(nc_file, "r")
        if cmaq_version == "5.3.2":
            ds_apmdiag = nc.Dataset(
                f"{source_path}/{input_file_prefix.replace('CCTM_ACONC','CCTM_APMDIAG')}_{runday_str}.nc",
                "r",
            )  # 气溶胶CCTM_APMDIAG_PRD
        elif cmaq_version == "5.4":
            ds_apmdiag = nc.Dataset(
                f"{source_path}/{input_file_prefix.replace('CCTM_ACONC','CCTM_AELMO')}_{runday_str}.nc",
                "r",
            )
        SO2[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["SO2"][:, layer_symbol, :, :], axis=0) * 1000
        )
        NO2[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["NO2"][:, layer_symbol, :, :], axis=0) * 1000
        )
        NO[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["NO"][:, layer_symbol, :, :], axis=0) * 1000
        )
        NH3[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["NH3"][:, layer_symbol, :, :], axis=0) * 1000
        )
        HONO[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["HONO"][:, layer_symbol, :, :], axis=0) * 1000
        )
        HNO3[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["HNO3"][:, layer_symbol, :, :], axis=0) * 1000
        )
        H2O2[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["H2O2"][:, layer_symbol, :, :], axis=0) * 1000
        )
        N2O5[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["N2O5"][:, layer_symbol, :, :], axis=0) * 1000
        )
        FORM[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["FORM"][:, layer_symbol, :, :], axis=0) * 1000
        )
        OH[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["OH"][:, layer_symbol, :, :], axis=0) * 1000
        )
        ISOP[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["ISOP"][:, layer_symbol, :, :], axis=0) * 1000
        )
        TERP[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["TERP"][:, layer_symbol, :, :], axis=0) * 1000
        )
        O3_d_avg[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["O3"][:, layer_symbol, :, :], axis=0) * 1000
        )

        ASO4IJ[day_index, layer_symbol, :, :] = np.mean(
            ds_aconc.variables["ASO4I"][:, layer_symbol, :, :], axis=0
        ) + np.mean(ds_aconc.variables["ASO4J"][:, layer_symbol, :, :], axis=0)
        ANO3IJ[day_index, layer_symbol, :, :] = np.mean(
            ds_aconc.variables["ANO3I"][:, layer_symbol, :, :], axis=0
        ) + np.mean(ds_aconc.variables["ANO3J"][:, layer_symbol, :, :], axis=0)
        ANH4IJ[day_index, layer_symbol, :, :] = np.mean(
            ds_aconc.variables["ANH4I"][:, layer_symbol, :, :], axis=0
        ) + np.mean(ds_aconc.variables["ANH4J"][:, layer_symbol, :, :], axis=0)

        # 处理有机物
        ASOCI[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["ALVOO1I"][:, layer_symbol, :, :], axis=0) / 2.27
            + np.mean(ds_aconc.variables["ALVOO2I"][:, layer_symbol, :, :], axis=0) / 2.06
            + np.mean(ds_aconc.variables["ASVOO1I"][:, layer_symbol, :, :], axis=0) / 1.88
            + np.mean(ds_aconc.variables["ASVOO2I"][:, layer_symbol, :, :], axis=0) / 1.73
        )
        ASOCJ[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["AISO1J"][:, layer_symbol, :, :], axis=0) / 2.20
            + np.mean(ds_aconc.variables["AISO2J"][:, layer_symbol, :, :], axis=0) / 2.23
            + np.mean(ds_aconc.variables["AISO3J"][:, layer_symbol, :, :], axis=0) / 2.80
            + np.mean(ds_aconc.variables["AMT1J"][:, layer_symbol, :, :], axis=0) / 1.67
            + np.mean(ds_aconc.variables["AMT2J"][:, layer_symbol, :, :], axis=0) / 1.67
            + np.mean(ds_aconc.variables["AMT3J"][:, layer_symbol, :, :], axis=0) / 1.72
            + np.mean(ds_aconc.variables["AMT4J"][:, layer_symbol, :, :], axis=0) / 1.53
            + np.mean(ds_aconc.variables["AMT5J"][:, layer_symbol, :, :], axis=0) / 1.57
            + np.mean(ds_aconc.variables["AMT6J"][:, layer_symbol, :, :], axis=0) / 1.40
            + np.mean(ds_aconc.variables["AMTNO3J"][:, layer_symbol, :, :], axis=0) / 1.90
            + np.mean(ds_aconc.variables["AMTHYDJ"][:, layer_symbol, :, :], axis=0) / 1.54
            + np.mean(ds_aconc.variables["AGLYJ"][:, layer_symbol, :, :], axis=0) / 2.13
            + np.mean(ds_aconc.variables["ASQTJ"][:, layer_symbol, :, :], axis=0) / 1.52
            + np.mean(ds_aconc.variables["AORGCJ"][:, layer_symbol, :, :], axis=0) / 2.00
            + np.mean(ds_aconc.variables["AOLGBJ"][:, layer_symbol, :, :], axis=0) / 2.10
            + np.mean(ds_aconc.variables["AOLGAJ"][:, layer_symbol, :, :], axis=0) / 2.50
            + np.mean(ds_aconc.variables["ALVOO1J"][:, layer_symbol, :, :], axis=0) / 2.27
            + np.mean(ds_aconc.variables["ALVOO2J"][:, layer_symbol, :, :], axis=0) / 2.06
            + np.mean(ds_aconc.variables["ASVOO1J"][:, layer_symbol, :, :], axis=0) / 1.88
            + np.mean(ds_aconc.variables["ASVOO2J"][:, layer_symbol, :, :], axis=0) / 1.73
            + np.mean(ds_aconc.variables["ASVOO3J"][:, layer_symbol, :, :], axis=0) / 1.60
            + np.mean(ds_aconc.variables["APCSOJ"][:, layer_symbol, :, :], axis=0) / 2.00
            + np.mean(ds_aconc.variables["AAVB1J"][:, layer_symbol, :, :], axis=0) / 2.70
            + np.mean(ds_aconc.variables["AAVB2J"][:, layer_symbol, :, :], axis=0) / 2.35
            + np.mean(ds_aconc.variables["AAVB3J"][:, layer_symbol, :, :], axis=0) / 2.17
            + np.mean(ds_aconc.variables["AAVB4J"][:, layer_symbol, :, :], axis=0) / 1.99
        )
        # 计算ASOCIJ
        ASOCIJ[day_index, layer_symbol, :, :] = (
            ASOCI[day_index, layer_symbol, :, :] + ASOCJ[day_index, layer_symbol, :, :]
        )

        # 计算ATOTI（不求均值，直接相加）
        ATOTI = (
            ds_aconc.variables["ASO4I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANO3I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANH4I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANAI"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACLI"][:, layer_symbol, :, :]
            + ds_aconc.variables["AECI"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOTHRI"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVPO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO2I"][:, layer_symbol, :, :]
            + ds_aconc.variables["APOCI"][:, layer_symbol, :, :]
            + ds_aconc.variables["APNCOMI"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO2I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO2I"][:, layer_symbol, :, :]
        )
        # 计算ATOTJ（不求均值，直接相加）
        ATOTJ = (
            ds_aconc.variables["ASO4J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANH4J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANAJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACLJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AECJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOTHRJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AFEJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASIJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ATIJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACAJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMGJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMNJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AALJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AKJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVPO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["APOCJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AIVPO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["APNCOMJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AISO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AISO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AISO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT4J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT5J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT6J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMTNO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMTHYDJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AGLYJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASQTJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AORGCJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOLGBJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOLGAJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["APCSOJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB4J"][:, layer_symbol, :, :]
        )
        # 计算ATOTK
        ATOTK = (
            ds_aconc.variables["ASOIL"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACORS"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASEACAT"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACLK"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASO4K"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANO3K"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANH4K"][:, layer_symbol, :, :]
        )
        # ATOTI - 气溶胶的总浓度（以微克每立方米为单位）在**Aitken模式（Aitken mode）**的粒径范围内。Aitken模式通常表示非常细的颗粒物，粒径范围通常为0.01微米到0.1微米。
        # ATOTJ - 气溶胶的总浓度（以微克每立方米为单位）在**积聚模式（Accumulation mode）**的粒径范围内。积聚模式的颗粒物粒径通常在0.1微米到1微米之间。
        # ATOTK - 气溶胶的总浓度（以微克每立方米为单位）在**粗粒模式（Coarse mode）**的粒径范围内。粗粒模式的颗粒物粒径通常大于1微米。
        # 计算PM25
        PM25[:, layer_symbol, :, :] = (
            ATOTI[...] * ds_apmdiag.variables["PM25AT"][:, layer_symbol, :, :]  # Aitken 模态、
            + ATOTJ[...] * ds_apmdiag.variables["PM25AC"][:, layer_symbol, :, :]  # 积聚模态
            + ATOTK[...] * ds_apmdiag.variables["PM25CO"][:, layer_symbol, :, :]  # 粗颗粒模态
        )
        PM25_TOT[day_index, layer_symbol, :, :] = np.mean(PM25[:, layer_symbol, :, :], axis=0)
        # 计算VOC
        VOC[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["PAR"][:, layer_symbol, :, :], axis=0)
            + np.mean(ds_aconc.variables["ETHA"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["PRPA"][:, layer_symbol, :, :], axis=0) * 3
            + np.mean(ds_aconc.variables["MEOH"][:, layer_symbol, :, :], axis=0)
            + np.mean(ds_aconc.variables["ETH"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["ETOH"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["OLE"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["ACET"][:, layer_symbol, :, :], axis=0) * 3
            + np.mean(ds_aconc.variables["TOL"][:, layer_symbol, :, :], axis=0) * 7
            + np.mean(ds_aconc.variables["XYLMN"][:, layer_symbol, :, :], axis=0) * 8
            + np.mean(ds_aconc.variables["BENZENE"][:, layer_symbol, :, :], axis=0) * 6
            + np.mean(ds_aconc.variables["FORM"][:, layer_symbol, :, :], axis=0)
            + np.mean(ds_aconc.variables["GLY"][:, layer_symbol, :, :], axis=0) * 3
            + np.mean(ds_aconc.variables["KET"][:, layer_symbol, :, :], axis=0) * 4
            + np.mean(ds_aconc.variables["ETHY"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["ALD2"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["IOLE"][:, layer_symbol, :, :], axis=0) * 4
            + np.mean(ds_aconc.variables["ALDX"][:, layer_symbol, :, :], axis=0) * 2
            + np.mean(ds_aconc.variables["ISOP"][:, layer_symbol, :, :], axis=0) * 5
            + np.mean(ds_aconc.variables["TERP"][:, layer_symbol, :, :], axis=0) * 10
            + np.mean(ds_aconc.variables["NAPH"][:, layer_symbol, :, :], axis=0) * 10
            + np.mean(ds_aconc.variables["APIN"][:, layer_symbol, :, :], axis=0) * 10
        ) * 1000

        # 计算NOx
        NOx[day_index, layer_symbol, :, :] = (
            np.mean(ds_aconc.variables["NO2"][:, layer_symbol, :, :], axis=0)
            + np.mean(ds_aconc.variables["NO"][:, layer_symbol, :, :], axis=0)
        ) * 1000

        # 处理O3 8小时最大值
        O3_8h = np.zeros((17, layer_count,row, col), dtype=float)
        var = ds_aconc.variables["O3"][:, layer_symbol, :, :] * 1000
        for t in range(17):
            O3_8h[t,layer_symbol, :, :] = np.mean(var[t : t + 8, ...], axis=0)
        O3d[day_index, layer_symbol, :, :] = np.max(O3_8h, axis=0)

    # 将数据写入NetCDF文件
    ds_output.createDimension("TSTEP", data_shape[0])
    ds_output.createDimension("LAY", data_shape[1])
    ds_output.createDimension("ROW", data_shape[2])
    ds_output.createDimension("COL", data_shape[3])
    variables_data = {
        "SO2": np.mean(SO2, axis=0),
        "NO2": np.mean(NO2, axis=0),
        "NO": np.mean(NO, axis=0),
        "HNO3": np.mean(HNO3, axis=0),
        "H2O2": np.mean(H2O2, axis=0),
        "HONO": np.mean(HONO, axis=0),
        "N2O5": np.mean(N2O5, axis=0),
        "FORM": np.mean(FORM, axis=0),
        "O3_US": np.mean(O3d, axis=0),
        "O3_CN": np.mean(O3d * 48 / 24.45, axis=0),
        "OH": np.mean(OH, axis=0),
        "ISOP": np.mean(ISOP, axis=0),
        "TERP": np.mean(TERP, axis=0),
        "ASO4IJ": np.mean(ASO4IJ, axis=0),
        "ANO3IJ": np.mean(ANO3IJ, axis=0),
        "ANH4IJ": np.mean(ANH4IJ, axis=0),
        "ASOCIJ": np.mean(ASOCIJ, axis=0),
        "PM25_TOT": np.mean(PM25_TOT, axis=0),
        "NH3": np.mean(NH3, axis=0),
        "O3": np.mean(O3_d_avg, axis=0),
        "VOC": np.mean(VOC, axis=0),
        "NOx": np.mean(NOx, axis=0),
    }
    variables_units = {
        "SO2": "ppb",
        "NO2": "ppb",
        "NO": "ppb",
        "HNO3": "ppb",
        "H2O2": "ppb",
        "HONO": "ppb",
        "N2O5": "ppb",
        "FORM": "ppb",
        "O3_US": "ppb",
        "O3_CN": "μg/m3",
        "OH": "ppb",
        "ISOP": "ppb",
        "TERP": "ppb",
        "ASO4IJ": "μg/m3",
        "ANO3IJ": "μg/m3",
        "ANH4IJ": "μg/m3",
        "ASOCIJ": "μg/m3",
        "PM25_TOT": "μg/m3",
        "NH3": "ppb",
        "O3": "ppb",
        "VOC": "ppb",
        "NOx": "ppb",
    }
    # 写入变量
    for var_name, values in tqdm(
        variables_data.items(),
        leave=True,
        desc=f"Writing variables for {parent_folder_name}",
    ):
        nc_var = ds_output.createVariable(
            var_name, np.float32, ("TSTEP", "LAY", "ROW", "COL")
        )
        nc_var.units = variables_units[var_name]
        nc_var.long_name = var_name
        nc_var[:] = values
    # 读取所有全局属性
    global_attrs_template = {
        attr: getattr(ds_aconc, attr) for attr in ds_aconc.ncattrs()
    }
    # 写入全局属性
    for attr_name, attr_value in global_attrs_template.items():
        if attr_name == "TSTEP":
            attr_value = attr_value * 24  # 将小时转换为天
        setattr(ds_output, attr_name, attr_value)
    ds_output.close()
    print(f"finished processing {parent_folder_name}...")
    return output_file


def extract_hourly_data(
    source_path,
    output_path,
    start_date,
    end_date,
    layer_index=0,
    # data_shape=None,
    input_file_prefix="CCTM_ACONC_PRD",
    output_file_name="ACONC.nc",
    output_file_with_parent_folder=False,
    output_file_format="NETCDF3_CLASSIC",
    cmaq_version="5.3.2"
):
    """
    @description: 将CMAQ模拟小时结果提取地表层（0层）的18种污染物(SO2,NO2,NO,HNO3,H2O2,HONO,N2O5,FORM,O3,OH,ISOP,TERP,ASO4IJ,ANO3IJ,ANH4IJ,ASOCIJ,PM25_TOT,NH3,VOC,NOx,O3_8hr_avg)的日均值数据，并处理为日均数据，并写入NetCDF文件
    @param {str} source_path: 源数据路径
    @param {str} output_path: 输出路径
    @param {layer_index} layer_index: 层数索引，默认为0，即提取地表层的数据,如果指定为None，则提取所有层的数据
    @param {str, datetime.datetime, int} start_date: 开始日期,可以是datetime.datetime对象，也可以是字符串，格式为YYYYMMDD或YYYYJJJ
    @param {str, datetime.datetime, int} end_date: 结束日期，,可以是datetime.datetime对象，也可以是字符串，格式为YYYYMMDD或YYYYJJJ
    @param {str} input_file_prefix: 输入文件前缀,默认为CCTM_ACONC_PRD
    @param {str} output_file_name: 输出文件名，默认为ACONC.nc
    @param {bool} output_file_with_parent_folder: 输出文件是否包含父文件夹名称，默认为False; False: 输出文件名为output_file_prefix.output_file_suffix; True: 输出文件名为output_file_prefix.parent_folder_name.output_file_suffix
    @param {str} output_file_format: 输出文件格式，默认为NETCDF3_CLASSIC
    @param {str} cmaq_version: CMAQ版本，默认为5.3.2
    @return: None
    """
    start_year_day = format_date_to_year_day(
        start_date
    )  # 获取开始日期的年和年中的第几天,格式为YYYYJJJ
    end_year_day = format_date_to_year_day(
        end_date
    )  # 获取结束日期的年和年中的第几天,格式为YYYYJJJ
    # 验证文件长度是否一致
    is_pass=validate_file_length(source_path, start_year_day, end_year_day, input_file_prefix)
    if not is_pass:
        return
    parent_folder_name = os.path.basename(source_path.strip("/"))
    
    if '12US' in input_file_prefix:
        nc_file = os.path.join(source_path, f"{input_file_prefix}_{start_date}.nc")
    else:
        nc_file = os.path.join(source_path, f"{input_file_prefix}_{start_year_day}.nc")
    with nc.Dataset(nc_file, "r") as ds_temp:
        variable_name = "NO"
        if variable_name not in ds_temp.variables:
            variable_name = list(ds_temp.variables.keys())[-1]
        layer, row, col = ds_temp.variables[variable_name].shape[-3:]
        layer_count= layer if layer_index is None else 1
        tstep = (end_year_day - start_year_day + 1) * 24
        data_shape = (tstep, layer_count, row, col)

    row, col = data_shape[-2], data_shape[-1]
    layer_symbol = slice(None) if layer_index is None else layer_index
    # region 定义变量
    O3 = np.zeros(data_shape, dtype=float)
    # O3_d_avg = np.zeros(data_shape, dtype=float)
    # O3d = np.zeros(data_shape, dtype=float)
    NO2 = np.zeros(data_shape, dtype=float)
    NO = np.zeros(data_shape, dtype=float)
    NOx = np.zeros(data_shape, dtype=float)
    HNO3 = np.zeros(data_shape, dtype=float)
    H2O2 = np.zeros(data_shape, dtype=float)
    N2O5 = np.zeros(data_shape, dtype=float)
    FORM = np.zeros(data_shape, dtype=float)
    HONO = np.zeros(data_shape, dtype=float)
    OH = np.zeros(data_shape, dtype=float)
    ISOP = np.zeros(data_shape, dtype=float)
    TERP = np.zeros(data_shape, dtype=float)
    ASO4IJ = np.zeros(data_shape, dtype=float)
    ANO3IJ = np.zeros(data_shape, dtype=float)
    ANH4IJ = np.zeros(data_shape, dtype=float)
    ASOCI = np.zeros(data_shape, dtype=float)
    ASOCJ = np.zeros(data_shape, dtype=float)
    ASOCIJ = np.zeros(data_shape, dtype=float)
    PM25_TOT = np.zeros(data_shape, dtype=float)
    PM25 = np.zeros((24, layer_count, row, col), dtype=float)
    SO2 = np.zeros(data_shape, dtype=float)
    NH3 = np.zeros(data_shape, dtype=float)
    VOC = np.zeros(data_shape, dtype=float)
    # endregion 定义变量

    # suffix="nc"#scen_idx+1
    output_file_prefix = os.path.splitext(output_file_name)[0]
    output_file_suffix = os.path.splitext(output_file_name)[1]
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    output_file = os.path.join(
        output_path,
        (
            output_file_name
            if not output_file_with_parent_folder
            else f"{output_file_prefix}{'_'+parent_folder_name}{output_file_suffix}"
        ),
    )
    ds_output = nc.Dataset(
        output_file, "w", format=output_file_format
    )  # format='NETCDF4'
    # print(output_file)
    tqdm.write(f"Creating {os.path.basename(output_file)}...")
    # tqdm.write(f"start processing data from {source_path}...")
    for runday in tqdm(
        range(start_year_day, end_year_day + 1),
        leave=False,
        desc=f"Processing {parent_folder_name}",
    ):
        day_index = runday - start_year_day
        if '12US' in input_file_prefix:
            runday_str = datetime.strptime(f"{runday}", "%Y%j").strftime("%Y%m%d")
            nc_file = os.path.join(source_path, f"{input_file_prefix}_{runday_str}.nc")
        else:
            runday_str = runday
            nc_file = os.path.join(source_path, f"{input_file_prefix}_{runday}.nc")
        if not os.path.exists(nc_file):
            print(f"{nc_file} not exists")
        # print(f"Loading {nc_file}...")
        tqdm.write(f"Loading {parent_folder_name}/{os.path.basename(nc_file)}...")
        ds_aconc = nc.Dataset(nc_file, "r")
        if cmaq_version == "5.3.2":
            ds_apmdiag = nc.Dataset(
                f"{source_path}/{input_file_prefix.replace('CCTM_ACONC','CCTM_APMDIAG')}_{runday_str}.nc",
                "r",
            )  # 气溶胶CCTM_APMDIAG_PRD
        elif cmaq_version == "5.4":
            ds_apmdiag = nc.Dataset(
                f"{source_path}/{input_file_prefix.replace('CCTM_ACONC','CCTM_AELMO')}_{runday_str}.nc",
                "r",
            )
        start_hour, end_hour = day_index * 24, day_index * 24 + 24
        SO2[start_hour:end_hour, layer_symbol, :, :] = ds_aconc.variables["SO2"][:, layer_symbol, :, :] * 1000
        NO2[start_hour:end_hour, layer_symbol, :, :] = ds_aconc.variables["NO2"][:, layer_symbol, :, :] * 1000
        NO[start_hour:end_hour, layer_symbol, :, :] = ds_aconc.variables["NO"][:, layer_symbol, :, :] * 1000
        NOx[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["NO2"][:, layer_symbol, :, :] + ds_aconc.variables["NO"][:, layer_symbol, :, :]
        ) * 1000  # 计算NOx
        NH3[start_hour:end_hour, layer_symbol, :, :] = ds_aconc.variables["NH3"][:, layer_symbol, :, :] * 1000
        HONO[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["HONO"][:, layer_symbol, :, :] * 1000
        )
        HNO3[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["HNO3"][:, layer_symbol, :, :] * 1000
        )
        H2O2[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["H2O2"][:, layer_symbol, :, :] * 1000
        )
        N2O5[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["N2O5"][:, layer_symbol, :, :] * 1000
        )
        FORM[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["FORM"][:, layer_symbol, :, :] * 1000
        )
        OH[start_hour:end_hour, layer_symbol, :, :] = ds_aconc.variables["OH"][:, layer_symbol, :, :] * 1000
        ISOP[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["ISOP"][:, layer_symbol, :, :] * 1000
        )
        TERP[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["TERP"][:, layer_symbol, :, :] * 1000
        )
        O3[start_hour:end_hour, layer_symbol, :, :] = ds_aconc.variables["O3"][:, layer_symbol, :, :] * 1000
        # O3_d_avg[day_index, layer_symbol, :, :] = (
        #     np.mean(ds_aconc.variables["O3"][:, layer_symbol, :, :], axis=0) * 1000
        # )

        ASO4IJ[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["ASO4I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASO4J"][:, layer_symbol, :, :]
        )
        ANO3IJ[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["ANO3I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANO3J"][:, layer_symbol, :, :]
        )
        ANH4IJ[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["ANH4I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANH4J"][:, layer_symbol, :, :]
        )

        # 处理有机物
        ASOCI[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["ALVOO1I"][:, layer_symbol, :, :] / 2.27
            + ds_aconc.variables["ALVOO2I"][:, layer_symbol, :, :] / 2.06
            + ds_aconc.variables["ASVOO1I"][:, layer_symbol, :, :] / 1.88
            + ds_aconc.variables["ASVOO2I"][:, layer_symbol, :, :] / 1.73
        )
        ASOCJ[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["AISO1J"][:, layer_symbol, :, :] / 2.20
            + ds_aconc.variables["AISO2J"][:, layer_symbol, :, :] / 2.23
            + ds_aconc.variables["AISO3J"][:, layer_symbol, :, :] / 2.80
            + ds_aconc.variables["AMT1J"][:, layer_symbol, :, :] / 1.67
            + ds_aconc.variables["AMT2J"][:, layer_symbol, :, :] / 1.67
            + ds_aconc.variables["AMT3J"][:, layer_symbol, :, :] / 1.72
            + ds_aconc.variables["AMT4J"][:, layer_symbol, :, :] / 1.53
            + ds_aconc.variables["AMT5J"][:, layer_symbol, :, :] / 1.57
            + ds_aconc.variables["AMT6J"][:, layer_symbol, :, :] / 1.40
            + ds_aconc.variables["AMTNO3J"][:, layer_symbol, :, :] / 1.90
            + ds_aconc.variables["AMTHYDJ"][:, layer_symbol, :, :] / 1.54
            + ds_aconc.variables["AGLYJ"][:, layer_symbol, :, :] / 2.13
            + ds_aconc.variables["ASQTJ"][:, layer_symbol, :, :] / 1.52
            + ds_aconc.variables["AORGCJ"][:, layer_symbol, :, :] / 2.00
            + ds_aconc.variables["AOLGBJ"][:, layer_symbol, :, :] / 2.10
            + ds_aconc.variables["AOLGAJ"][:, layer_symbol, :, :] / 2.50
            + ds_aconc.variables["ALVOO1J"][:, layer_symbol, :, :] / 2.27
            + ds_aconc.variables["ALVOO2J"][:, layer_symbol, :, :] / 2.06
            + ds_aconc.variables["ASVOO1J"][:, layer_symbol, :, :] / 1.88
            + ds_aconc.variables["ASVOO2J"][:, layer_symbol, :, :] / 1.73
            + ds_aconc.variables["ASVOO3J"][:, layer_symbol, :, :] / 1.60
            + ds_aconc.variables["APCSOJ"][:, layer_symbol, :, :] / 2.00
            + ds_aconc.variables["AAVB1J"][:, layer_symbol, :, :] / 2.70
            + ds_aconc.variables["AAVB2J"][:, layer_symbol, :, :] / 2.35
            + ds_aconc.variables["AAVB3J"][:, layer_symbol, :, :] / 2.17
            + ds_aconc.variables["AAVB4J"][:, layer_symbol, :, :] / 1.99
        )

        # 计算ASOCIJ
        ASOCIJ[start_hour:end_hour, layer_symbol, :, :] = (
            ASOCI[start_hour:end_hour, layer_symbol, :, :] + ASOCJ[start_hour:end_hour, layer_symbol, :, :]
        )
        # 计算ATOTI（不求均值，直接相加）
        ATOTI = (
            ds_aconc.variables["ASO4I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANO3I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANH4I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANAI"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACLI"][:, layer_symbol, :, :]
            + ds_aconc.variables["AECI"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOTHRI"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVPO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO2I"][:, layer_symbol, :, :]
            + ds_aconc.variables["APOCI"][:, layer_symbol, :, :]
            + ds_aconc.variables["APNCOMI"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO2I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO1I"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO2I"][:, layer_symbol, :, :]
        )
        # 计算ATOTJ（不求均值，直接相加）
        ATOTJ = (
            ds_aconc.variables["ASO4J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANH4J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANAJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACLJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AECJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOTHRJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AFEJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASIJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ATIJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACAJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMGJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMNJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AALJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AKJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVPO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["APOCJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVPO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AIVPO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["APNCOMJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AISO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AISO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AISO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT4J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT5J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMT6J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMTNO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AMTHYDJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AGLYJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASQTJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AORGCJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOLGBJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AOLGAJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ALVOO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASVOO3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["APCSOJ"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB1J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB2J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB3J"][:, layer_symbol, :, :]
            + ds_aconc.variables["AAVB4J"][:, layer_symbol, :, :]
        )
        # 计算ATOTK
        ATOTK = (
            ds_aconc.variables["ASOIL"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACORS"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASEACAT"][:, layer_symbol, :, :]
            + ds_aconc.variables["ACLK"][:, layer_symbol, :, :]
            + ds_aconc.variables["ASO4K"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANO3K"][:, layer_symbol, :, :]
            + ds_aconc.variables["ANH4K"][:, layer_symbol, :, :]
        )
        # ATOTI - 气溶胶的总浓度（以微克每立方米为单位）在**Aitken模式（Aitken mode）**的粒径范围内。Aitken模式通常表示非常细的颗粒物，粒径范围通常为0.01微米到0.1微米。
        # ATOTJ - 气溶胶的总浓度（以微克每立方米为单位）在**积聚模式（Accumulation mode）**的粒径范围内。积聚模式的颗粒物粒径通常在0.1微米到1微米之间。
        # ATOTK - 气溶胶的总浓度（以微克每立方米为单位）在**粗粒模式（Coarse mode）**的粒径范围内。粗粒模式的颗粒物粒径通常大于1微米。
        # 计算PM25
        PM25[:, layer_symbol, :, :] = (
            ATOTI[...] * ds_apmdiag.variables["PM25AT"][:, layer_symbol, :, :]  # Aitken 模态、
            + ATOTJ[...] * ds_apmdiag.variables["PM25AC"][:, layer_symbol, :, :]  # 积聚模态
            + ATOTK[...] * ds_apmdiag.variables["PM25CO"][:, layer_symbol, :, :]  # 粗颗粒模态
        )

        PM25_TOT[start_hour:end_hour, layer_symbol, :, :] = PM25[:, layer_symbol, :, :]
        # 计算VOC
        VOC[start_hour:end_hour, layer_symbol, :, :] = (
            ds_aconc.variables["PAR"][:, layer_symbol, :, :]
            + ds_aconc.variables["ETHA"][:, layer_symbol, :, :] * 2
            + ds_aconc.variables["PRPA"][:, layer_symbol, :, :] * 3
            + ds_aconc.variables["MEOH"][:, layer_symbol, :, :]
            + ds_aconc.variables["ETH"][:, layer_symbol, :, :] * 2
            + ds_aconc.variables["ETOH"][:, layer_symbol, :, :] * 2
            + ds_aconc.variables["OLE"][:, layer_symbol, :, :] * 2
            + ds_aconc.variables["ACET"][:, layer_symbol, :, :] * 3
            + ds_aconc.variables["TOL"][:, layer_symbol, :, :] * 7
            + ds_aconc.variables["XYLMN"][:, layer_symbol, :, :] * 8
            + ds_aconc.variables["BENZENE"][:, layer_symbol, :, :] * 6
            + ds_aconc.variables["FORM"][:, layer_symbol, :, :]
            + ds_aconc.variables["GLY"][:, layer_symbol, :, :] * 3
            + ds_aconc.variables["KET"][:, layer_symbol, :, :] * 4
            + ds_aconc.variables["ETHY"][:, layer_symbol, :, :] * 2
            + ds_aconc.variables["ALD2"][:, layer_symbol, :, :] * 2
            + ds_aconc.variables["IOLE"][:, layer_symbol, :, :] * 4
            + ds_aconc.variables["ALDX"][:, layer_symbol, :, :] * 2
            + ds_aconc.variables["ISOP"][:, layer_symbol, :, :] * 5
            + ds_aconc.variables["TERP"][:, layer_symbol, :, :] * 10
            + ds_aconc.variables["NAPH"][:, layer_symbol, :, :] * 10
            + ds_aconc.variables["APIN"][:, layer_symbol, :, :] * 10
        ) * 1000
    # 将O3数组转换为DataFrame O3.reshape(720, -1) 将把原始形状为 (720, 1, 112, 148) 的数组重新排列成一个形状为 (720, 16656) 的二维数组，其中每一行代表一个小时的数据;每一列代表一个网格
    df = pd.DataFrame(O3.reshape(O3.shape[0], -1))
    # 计算滑动8小时平均;# 按照时间维度滑动
    window_size, axis = 8, 0
    # 使用rolling方法计算滑动平均
    rolling_mean = df.rolling(window=window_size, min_periods=1, axis=axis).mean()
    # 将滑动平均数据转换回原始形状
    O3_8hr_mean = rolling_mean.values.reshape(O3.shape)

    # 将数据写入NetCDF文件
    ds_output.createDimension("TSTEP", data_shape[0])
    ds_output.createDimension("LAY", data_shape[1])
    ds_output.createDimension("ROW", data_shape[2])
    ds_output.createDimension("COL", data_shape[3])
    variables_data = {
        "SO2": SO2,
        "NO2": NO2,
        "NO": NO,
        "HNO3": HNO3,
        "H2O2": H2O2,
        "HONO": HONO,
        "N2O5": N2O5,
        "FORM": FORM,
        "O3_US": O3,
        "O3_CN": O3 * 48 / 24.45,
        "OH": OH,
        "ISOP": ISOP,
        "TERP": TERP,
        "ASO4IJ": ASO4IJ,
        "ANO3IJ": ANO3IJ,
        "ANH4IJ": ANH4IJ,
        "ASOCIJ": ASOCIJ,
        "PM25_TOT": PM25_TOT,
        "NH3": NH3,
        "VOC": VOC,
        "NOx": NOx,
        "O3_8hr_avg": O3_8hr_mean * 48 / 24.45,
    }
    variables_units = {
        "SO2": "ppb",
        "NO2": "ppb",
        "NO": "ppb",
        "HNO3": "ppb",
        "H2O2": "ppb",
        "HONO": "ppb",
        "N2O5": "ppb",
        "FORM": "ppb",
        "O3_US": "ppb",
        "O3_CN": "μg/m3",
        "OH": "ppb",
        "ISOP": "ppb",
        "TERP": "ppb",
        "ASO4IJ": "μg/m3",
        "ANO3IJ": "μg/m3",
        "ANH4IJ": "μg/m3",
        "ASOCIJ": "μg/m3",
        "PM25_TOT": "μg/m3",
        "NH3": "ppb",
        "VOC": "ppb",
        "NOx": "ppb",
        "O3_8hr_avg": "μg/m3",
    }
    # 读取所有全局属性
    global_attrs_template = {
        attr: getattr(ds_aconc, attr) for attr in ds_aconc.ncattrs()
    }
    # 写入全局属性
    for attr_name, attr_value in global_attrs_template.items():
        # if attr_name == "TSTEP":
        #     attr_value = attr_value # 将小时转换为天
        setattr(ds_output, attr_name, attr_value)
    # 创建变量
    for var_name in tqdm(
        variables_data.keys(),
        leave=True,
        desc=f"Creating variables for {parent_folder_name}",
    ):
        nc_var = ds_output.createVariable(
            var_name, np.float32, ("TSTEP", "LAY", "ROW", "COL")
        )
        try:
            nc_var.units = variables_units[var_name]
            nc_var.long_name = var_name
        except Exception as e:
            print(f"Error setting attributes for {var_name}: {e}")
    
    ds_output.sync()  # 手动同步数据到磁盘，退出定义模式

    # 写入变量数据
    for var_name, values in tqdm(
        variables_data.items(),
        leave=True,
        desc=f"Writing data for variables in {parent_folder_name}",
    ):
        try:
            ds_output.variables[var_name][:] = values
            ds_output.sync()  # 手动同步数据到磁盘
        except Exception as e:
            print(f"Error writing data for {var_name}: {e}")

    ds_output.close()
    print(f"finished processing {parent_folder_name}...")




def extract_variables_data(input_file, output_file, variables,dimension_name=None):
    '''
    @description: Extract variables data from input NetCDF file and save them to output NetCDF file.if dimension_name is not None, the specified dimension will be reduced to size 1.
    @param input_file: Input NetCDF file path.
    @param output_file: Output NetCDF file path.
    @param variables: List of variables to extract.
    @param dimension_name: Name of the dimension to reduce.
    '''
    # Open the input NetCDF file
    with nc.Dataset(input_file, 'r') as src:
        # Create the output NetCDF file
        with nc.Dataset(output_file, 'w') as dst:
            # Copy global attributes
            dst.setncatts(src.__dict__)            
            # Copy dimensions, except bottom_top which will be reduced to size 1
            for name, dimension in src.dimensions.items():
                if dimension_name is not None and name == dimension_name:                   
                    dst.createDimension(name, 1)
                else:
                    dst.createDimension(name, len(dimension) if not dimension.isunlimited() else None)               
            # Copy variables
            for name, variable in src.variables.items():
                if name in variables:
                    # Create the variable in the destination file
                    out_var = dst.createVariable(name, variable.datatype, variable.dimensions)
                    out_var.setncatts(variable.__dict__)                    
                    # Copy the data, slicing the first layer for bottom_top dimension
                    data = variable[:]
                    if dimension_name in variable.dimensions:
                        if dimension_name is not None:
                            index = variable.dimensions.index(dimension_name)
                            data = np.take(data, indices=0, axis=index)#indices=0: 获取索引为0的元素，即返回数组中索引为0的元素或子数组。                        
                    out_var[:] = data


def process_24hours_data_to_bj_time(date,output_folder,source_folder,layer_name,variables=[],input_file_prefix="",input_file_suffix="nc",output_file_suffix="CH4_ANFlux.bj.nc"): 
    '''
    @description: 将24小时数据(1个含24小时文件)合并到北京时间，并提取第一层数据
    @param {date: datetime.datetime, 日期}
    @param {output_folder: str, 输出文件夹}
    @param {source_folder: str, 数据源文件夹}
    @param {layer_name: str, 层名称}
    @param {variables: list, 需要提取的变量}
    @param {input_file_prefix: str, 文件前缀}
    @param {input_file_suffix: str, 文件后缀}
    @param {output_file_suffix: str, 输出文件后缀}
    @return: None
    '''
    import os
    import shutil
    from datetime import timedelta
    output_file = os.path.join(output_folder, f"{date.strftime('%Y%m%d%H')}.all_layers.{output_file_suffix}.nc") if len(variables) > 0 else os.path.join(output_folder, f"{date.strftime('%Y%m%d%H')}.{output_file_suffix}.nc")    
    current_date_file = os.path.join(source_folder, f"{input_file_prefix}.{date.strftime('%Y%m%d')}.{input_file_suffix}")
    if not  os.path.exists(current_date_file):
        print(f"File {current_date_file} not exists, skip it.")
        return
    shutil.copy(current_date_file,output_file)
    if date.strftime('%Y%m%d') != '20220101':#第一天不做处理
        previous_date = date - timedelta(days=1)
        previous_date_file=os.path.join(source_folder, f"{input_file_prefix}.{previous_date.strftime('%Y%m%d')}.{input_file_suffix}") 
        if not os.path.exists(previous_date_file):
            print(f"File {previous_date_file} not exists, skip it.{current_date_file} failed to process.")
            return       
        # shutil.copy(current_date_file,output_file)
        split_hours=8
        with nc.Dataset(output_file, 'r+') as src_dataset:
            for variable_name, variable in src_dataset.variables.items():
                if variable.dtype == 'S1':  # 字符串类型
                    continue
                previous_8h_data = nc.Dataset(previous_date_file, 'r')[variable_name][-split_hours:, :, :, :]  # 后一天的数据 
                current_16h_data =nc.Dataset(current_date_file, 'r')[variable_name][:(24-split_hours), :, :, :] # 当前文件的数据
                # 创建新的数据数组，长度为24小时
                new_data = np.zeros((24, *current_16h_data.shape[1:])) #*表示解包，即将一个可迭代对象（如列表、元组等）解包成单独的元素           
                # 填补前9小时数据
                new_data[:split_hours, :, :, :] = previous_8h_data            
                # 填补后面的15小时数据
                new_data[split_hours:, :, :, :] = current_16h_data            
                # 写回当前文件   
                variable[:] = new_data  
    if os.path.exists(output_file) and len(variables) > 0:     
        extract_variables_data(output_file, os.path.join(output_folder, f"{date.strftime('%Y%m%d%H')}.{output_file_suffix}"), variables,dimension_name=layer_name)
        os.remove(output_file)

def process_24files_data_to_bj_time(date,time_steps, output_folder,source_folder,layer_name,variables=[],input_file_prefix="",input_file_suffix="nc",input_date_str_format='%Y_%m_%d_%H',
                 output_file_suffix="ch4.conc.bj.nc", skip_file_length_validation=False):
    '''
    @description: 将24小时数据(24个小时文件)合并到北京时间，并提取第一层数据
    @param {date: datetime.datetime, 日期}
    @param {time_steps: list, 时间步长}
    @param {output_folder: str, 输出文件夹}
    @param {source_folder: str, 数据源文件夹}
    @param {layer_name: str, 层名称}
    @param {variables: list, 需要提取的变量}
    @param {input_file_prefix: str, 文件前缀}
    @param {input_file_suffix: str, 文件后缀}
    @param {input_date_str_format: str, 输入文件日期格式}
    @param {output_file_suffix: str, 输出文件后缀}
    @param {skip_file_length_validation: bool, 是否跳过文件长度验证}
    @return: None
    '''
    import os
    import subprocess
    from datetime import timedelta
    nccopy_command = 'nccopy'
    
    # 找到所有文件
    existing_files = []
    for time_step in time_steps:
        current_date = date + timedelta(hours=int(time_step))        
        file = os.path.join(source_folder, f"{input_file_prefix}{current_date.strftime(input_date_str_format)}.{input_file_suffix}")
        if os.path.exists(file) and os.path.getsize(file) > 0:            
            existing_files.append(file)
        else:
            print(f"File {file} not found or empty.")
    if not skip_file_length_validation:    
        if  len(existing_files) != 24:
            print(f"Not all 24 files found for date {date.strftime(input_date_str_format)}")
            if date.strftime('%Y-%m-%d') != '2022-01-01': 
                return
    
    existing_extracted_files=[]
    for source_file in existing_files:
        base_dir=os.path.dirname(source_file) 
        target_file_name=os.path.basename(source_file)     
        target_file = os.path.join(base_dir, f'{"extract"}.{target_file_name}')
        variable_names = ','.join(variables)
        command = [nccopy_command, '-V', variable_names, source_file, target_file]
        subprocess.run(command)
        if os.path.exists(target_file):
            target_file_1st_layer = os.path.join(output_folder, f'{target_file_name}.1layer')
            extract_variables_data(target_file, target_file_1st_layer, variables,dimension_name=layer_name)
            if os.path.exists(target_file_1st_layer):
                existing_extracted_files.append(target_file_1st_layer)
                os.remove(target_file)           
    # 打开多个文件并合并它们
    datasets = [xr.open_dataset(file) for file in existing_extracted_files]
    # 合并数据集
    combined_dataset = xr.concat(datasets, dim='Time')
    output_file = os.path.join(output_folder, f"{date.strftime('%Y%m%d%H')}.{output_file_suffix}")
    
    # 将合并后的数据集保存为一天 24 小时的 NetCDF 文件
    combined_dataset.to_netcdf(output_file)    
    # 关闭数据集
    combined_dataset.close()
    for file in existing_extracted_files:
        os.remove(file)        

     
def readNetCDF(nc_path, pollutant,timeStepIndex=0,layerStepIndex=0):
    '''
    :param nc_path: netcdf文件路径
    :param pollutant: 读取文件中变量
    :param timeStepIndex: 时间维度索引
    :param layerStepIndex: 层数维度索引
    :return: 读取 NetCDF 文件中的变量返回行列的数据框
    '''
    nc_data = nc.Dataset(nc_path)
    nc_data = nc_data.variables[pollutant][:][timeStepIndex,layerStepIndex]
    pd_data = pd.DataFrame(nc_data)
    # 关闭 NetCDF 文件
    #nc_data.close()
    return pd_data

def readNetCDFAsFlatten(nc_path, pollutant,timeStepIndex=0,layerStepIndex=0):
    '''
    :param nc_path: netcdf文件路径
    :param pollutant: 读取文件中变量
    :param timeStepIndex: 时间维度索引
    :param layerStepIndex: 层数维度索引
    :return: 读取 NetCDF 文件中的变量并将其展平成一维数组
    '''
    nc_data = nc.Dataset(nc_path)
    nc_data = nc_data.variables[pollutant][:][timeStepIndex, layerStepIndex]
    # 将多维数组展平成一维数组
    data_flattened = nc_data.flatten()
    # 关闭 NetCDF 文件
    #nc_data.close()
    return data_flattened

def createNETCDF(template_path,output_path,input_values,template_variable_index=0):
    '''
    :param template_path: netcdf模板文件路径
    :param output_path: 要生成的netcdf文件路径
    :param input_values:
    :param template_variable_index:
    :return:
    '''
    tempalate_dataset = nc.Dataset(template_path)  # 读取该ACONC文件基本信息
    col = tempalate_dataset.variables[template_variable_index].shape[0]  # 获取变量的列数量
    row = tempalate_dataset.variables[template_variable_index].shape[1]  # 获取变量的行数量
    variable_data = np.zeros((col, row))  # 创建与需要修改的变量同维度的全0矩阵
    k = 0  # 为保证CSV顺序与矩阵顺序相匹配，设定位置变量
    for i in range(row):
        for j in range(col):
            variable_data[j, i] = input_values[k]
            tip = f'第 {j} 列，第 {i} 行,第 {k} 个网格值'
            print(tip)
            k += 1
    with nc.Dataset(output_path, 'a') as ncfile:
        ncfile.variables[tempalate_dataset.variables[template_variable_index].name][:] = variable_data

def get_extent_data(nc_file,variable_name,x_name='lon',y_name='lat', extent=[]):
    '''
    :param nc_file: netcdf 文件路径
    :param variable_name: netcdf文件中要读取变量名称
    :param x_name: netcdf文件中x坐标方向的维度变量名称
    :param y_name: netcdf文件中y坐标方向的维度变量名称
    :param extent: 要提取的数据范围，默认为空，表示提取全域所有数据，如指定范围则按min_longitude，max_longitude，min_latitude，max_latitude顺序进行指定；
        如
        Guangdong Domain 的extent=[109.25,117.75,19,27]；
        China Domain的 extent = [70.25, 136.25, 4.75, 55.25];
        注意：截取后 data_subset.lon 和 data_subset.lat 是一维数组，data_subset 是对应的二维浓度数据
    :return: 返回提取后的数据
    '''

    # 打开NetCDF文件
    ds = xr.open_dataset(nc_file, decode_times=False)
    data = ds[variable_name]
    # 获取变量的单位信息
    unit = data.attrs.get('units')
    # Define the latitude and longitude ranges you want to display
    # min_longitude = ds[x_name].data.min()
    # max_longitude = ds[x_name].data.max()
    # min_latitude = ds[y_name].data.min()
    # max_latitude = ds[y_name].data.max()
    #考虑到有些数据经纬度并不一定是按数值大小进行排序，比如维度它是从90到-90，此时如果算最大值最小值的范围是-90,90，这个范围就会取不到任何数据。所以用维度的第一个数据和最后一个数值表示最小值和最大值
   
    min_longitude = ds[x_name].data[0]
    max_longitude = ds[x_name].data[-1]    
    min_latitude = ds[y_name].data[0]
    max_latitude = ds[y_name].data[-1]

    if extent:  # 不为空则用用户指定的范围       
        min_longitude = extent[0] if min_longitude<max_longitude else extent[1]
        max_longitude = extent[1] if min_longitude<max_longitude else extent[0]
        min_latitude = extent[2] if min_latitude<max_latitude else extent[3]
        max_latitude = extent[3] if min_latitude<max_latitude else extent[2]
        # min_longitude = extent[0] if(min_longitude<max_longitude and ds[x_name].data[0]<ds[x_name].data[1]) else extent[1]
        # max_longitude = extent[1] if min_longitude<max_longitude and ds[x_name].data[0]<ds[x_name].data[1] else extent[0]
        # min_latitude = extent[2] if min_latitude<max_latitude and ds[y_name].data[0]<ds[y_name].data[1] else extent[3]
        # max_latitude = extent[3] if min_latitude<max_latitude and ds[y_name].data[0]<ds[y_name].data[1] else extent[2]
    # 定义要显示的经纬度范围slice(min_longitude, max_longitude)和slice(min_latitude, max_latitude)
    # Use .sel() to select the specific latitude and longitude range
    # 根据维度名称获取维度变量    
    #data_subset = data.sel(x=slice(min_longitude, max_longitude), y=slice(min_latitude, max_latitude))
    data_subset = data.sel({x_name: slice(min_longitude, max_longitude), y_name: slice(min_latitude, max_latitude)})

    return data_subset,unit

def update_netcdf_file(nc_file):
    data = nc.Dataset(nc_file, mode='r+', format="NETCDF4")
    data.variables['PM25_TOT'].units = "μg/m3"    
    # data.TSTEP = 240000
    # data.SDATE  =  data.SDATE+1
    data.close()


def generate_date_array(start_date_str, num_days):
    from datetime import datetime, timedelta
    date_format = "%Y-%m-%d %H:%M:%S"
    start_date = datetime.strptime(start_date_str, date_format)
    date_array = [start_date + timedelta(days=i) for i in range(num_days)]
    date_strings = [date.strftime(date_format) for date in date_array]
    return date_strings

def update_netcdf_file_variable(nc_file,var_name,var_value,var_unit=''):
    data = nc.Dataset(nc_file, mode='r+', format="NETCDF3_CLASSIC")   
    data.variables[var_name][:] = var_value
    if var_unit:
        data.variables[var_name].units =var_unit
    data.close()

def create_netcdf_file(output_file, data, var_name, var_unit):
 
    # 创建NetCDF文件
    ncfile = nc.Dataset('example.nc', 'w')

    # 创建维度
    time_dim = ncfile.createDimension('time', None)
    lat_dim = ncfile.createDimension('lat', 10)
    lon_dim = ncfile.createDimension('lon', 20)

    # 创建变量
    time_var = ncfile.createVariable('time', 'f4', ('time',))
    lat_var = ncfile.createVariable('lat', 'f4', ('lat',))
    lon_var = ncfile.createVariable('lon', 'f4', ('lon',))
    data_var = ncfile.createVariable('data', 'f4', ('time', 'lat', 'lon'))

    # 设置变量的属性
    time_var.units = 'days since 2000-01-01'
    lat_var.units = 'degrees_north'
    lon_var.units = 'degrees_east'
    data_var.units = 'kg/m^2'

    # 设置变量的值
    time_var[:] = [0, 1, 2, 3, 4]
    lat_var[:] = range(10)
    lon_var[:] = range(20)
    data_var[:] = 1.0

    # 关闭NetCDF文件
    ncfile.close()

def create_netcdf_file_with_dims_update(files):    
    # 打开第一个文件以获取变量和维度信息
    with nc.Dataset(files[0], 'r') as src_dataset:      
        file_format=src_dataset.file_format  
        import os
        base_name=os.path.basename(files[0])   
        dir_name=os.path.dirname(files[0]) 
        date_time = datetime.strptime(os.path.basename(dir_name), "%Y%m%d%H")
        file_name = f"{date_time.strftime('%Y%m%d')}.{base_name}.nc"          
        new_file =os.path.join(os.path.dirname(dir_name),file_name)
        # 创建新的合并文件
        with nc.Dataset(new_file, 'w',format=file_format) as dst_dataset:
            # 复制全局属性
            dst_dataset.setncatts(src_dataset.__dict__)
            # 复制维度
            for name, dimension in src_dataset.dimensions.items():
                dst_dataset.createDimension(name, len(dimension) if not dimension.isunlimited() else None)
            # 复制变量
            for name, variable in src_dataset.variables.items():
                # 创建变量
                dst_variable = dst_dataset.createVariable(name, variable.dtype, variable.dimensions)
                # 复制变量属性
                dst_variable.setncatts(variable.__dict__)
                # 创建合并数据数组
                merged_data = np.zeros(variable.shape)   
                # 合并数据
                for file in files:
                    with nc.Dataset(file, 'r') as src_new_dataset:
                        src_variable = src_new_dataset.variables[name]
                        merged_data += src_variable[:]   
                # # 计算每天的平均值             
                daily_mean_data=merged_data/len(files)
                # 将数据写入新的合并文件
                dst_variable[:] = daily_mean_data
            print(f"成功创建{file_name}")    
    
def create_cmaq_mask(netcdf_template_file,boundary_json_file,output_file,region_names,region_mask_names,field_name="name",include_other_domain=True, include_outofselected_domain=True,plot_boundary_json_file=None):
    '''
    @description: 根据netcdf模板文件和边界json文件生成 CMAQ mask 文件；TODO: 需要根据boundary_json_file属性表，支持多个区域合并
    @param {str}: netcdf_template_file: netcdf模板文件,一般采用海洋文件 oceanfile
    @param {str}: boundary_json_file: 边界json文件,一般采用geojson文件或shp文件
    @param {str}: output_file: 输出文件名
    @param {list}: region_names: 区域名称列表
    @param {list}: region_mask_names: 区域mask名称列表
    @param {str}: field_name: 边界json文件或shp文件中包含的字段名,默认为name
    @param {bool}: include_other_domain: 是否包含其他域,默认为True;即扣除boundary_json_file所有区域外的domain;如果为False,则只保留region_names中定义的区域
    @param {bool}: include_outofselected_domain: 是否包含不在region_names中的domain,默认为True;即扣除region_names中定义的区域外的domain
    @param {str}: plot_boundary_json_file: 可选参数,用于绘制边界json文件,默认为None,即直接用boundary_json_file
    '''
    from esil.rsm_helper.model_property import model_attribute
    import pickle
    import sys
    # sys.path.append(r'/DeepLearning/mnt/Devin/code/esil')
    from esil.earth_helper import get_all_masks_by_intersection,get_grid_polygons
    import cmaps
    cmap_conc=cmaps.WhiteBlueGreenYellowRed             
    mp = model_attribute(netcdf_template_file)
    proj, longitudes, latitudes = mp.projection,mp.lons, mp.lats
    dx,dy = mp.x_resolution,mp.y_resolution
    x,y=np.meshgrid( mp.x_coords,mp.y_coords)
    save_path=os.path.dirname(output_file)
    template_file_name=os.path.basename(netcdf_template_file)
    json_file_name=os.path.basename(boundary_json_file).replace(".json","").replace(".shp","")
    pkl_file_name=os.path.join(save_path, f"{template_file_name}_{json_file_name}_mask.pkl")    
    grid_shape=x.shape#(len(latitudes),len(longitudes))      
    if os.path.exists(pkl_file_name):
        with open(pkl_file_name, "rb") as file:
            dict_masks_intersect = pickle.load(file)
    else:
        grid_polygons = get_grid_polygons(
            x.flatten(),
            y.flatten(),
            cell_width=dx,
            cell_height=dy,
            src_proj=proj,
            dst_proj="epsg:4326",
        )    
        dict_masks_intersect = get_all_masks_by_intersection(
                json_file=boundary_json_file,
                grid_polygons=grid_polygons,
                mask_shape=grid_shape,
                threshold=None,
                field_name=field_name,
                replaceFalseWithNan=True,            
            )
        # 将字典保存到文件
        with open(pkl_file_name, "wb") as file:
            pickle.dump(dict_masks_intersect, file)      
           
    dict_vars={}
    for city,mask_name in zip(region_names,region_mask_names):
        mask=np.nan_to_num(dict_masks_intersect[city], nan=0) #nan值替换为0#np.where(dict_masks_intersect[city] == np.nan, 0, dict_masks_intersect[city])
        extend_mask=np.reshape(mask, (1, 1)+ mask.shape)       
        dict_vars[mask_name]={"dtype":float,"data":extend_mask, "ncattrs":{ "units": "ratio", "var_desc": f"Mask for {mask_name}", "long_name": f"{mask_name}"},"dimensions":{"TSTEP":1,"LAY":1,"ROW":mask.shape[0],"COL":mask.shape[1]}}
    
    gd_oth_city_masks=[np.nan_to_num(dict_masks_intersect[name], nan=0) for name in dict_masks_intersect.keys() if name not in region_names]    
    if len(gd_oth_city_masks)!=0:
        gd_oth_city_mask_ratio =sum(gd_oth_city_masks)
        gd_oth_city_mask=np.nan_to_num(gd_oth_city_mask_ratio, nan=0) #np.where(gd_oth_city_mask_ratio == np.nan, 0, gd_oth_city_mask_ratio)   
        gd_oth_city_mask=np.where(gd_oth_city_mask >1, 1, gd_oth_city_mask) 
        mask_name="OTH_REGION" 
        extend_mask=np.reshape(gd_oth_city_mask, (1, 1)+ gd_oth_city_mask.shape)
        dict_vars[mask_name]={"dtype":float,"data":extend_mask, "ncattrs":{ "units": "ratio", "var_desc": f"Mask for {mask_name}", "long_name": f"{mask_name}"},"dimensions":{"TSTEP":1,"LAY":1,"ROW":mask.shape[0],"COL":mask.shape[1]}}   
    if include_other_domain:
        oth_domain_masks=[np.nan_to_num(dict_masks_intersect[name], nan=0) for name in dict_masks_intersect.keys()]
        oth_domain_mask_ratio =sum(oth_domain_masks)
        oth_domain_mask=1-np.nan_to_num(oth_domain_mask_ratio, nan=0) 
        oth_domain_mask=np.where(oth_domain_mask >1, 1, oth_domain_mask) 
        mask_name="OTH_DOMAIN" 
        extend_mask=np.reshape(oth_domain_mask, (1, 1)+ oth_domain_mask.shape)
        dict_vars[mask_name]={"dtype":float,"data":extend_mask, "ncattrs":{ "units": "ratio", "var_desc": f"Mask for {mask_name}", "long_name": f"{mask_name}"},"dimensions":{"TSTEP":1,"LAY":1,"ROW":mask.shape[0],"COL":mask.shape[1]}}   
    if include_outofselected_domain:
        selected_domain_masks=[np.nan_to_num(dict_masks_intersect[name], nan=0) for name in dict_masks_intersect.keys() if name in region_names]
        selected_domain_mask_ratio =sum(selected_domain_masks)
        outofselected_domain_mask=1-np.nan_to_num(selected_domain_mask_ratio, nan=0) 
        outofselected_domain_mask=np.where(outofselected_domain_mask >1, 1, outofselected_domain_mask) 
        mask_name="OTH_OUTOFSELECTED_DOMAIN" 
        extend_mask=np.reshape(outofselected_domain_mask, (1, 1)+ outofselected_domain_mask.shape)
        dict_vars[mask_name]={"dtype":float,"data":extend_mask, "ncattrs":{ "units": "ratio", "var_desc": f"Mask for {mask_name}", "long_name": f"{mask_name}"},"dimensions":{"TSTEP":1,"LAY":1,"ROW":mask.shape[0],"COL":mask.shape[1]}}  
                 
    with nc.Dataset(netcdf_template_file, "r") as dst:
        dict_attrs = {attr: getattr(dst, attr) for attr in dst.ncattrs()}
        var_length=len(dst.variables.keys())-1+len(dict_vars)    
        for var_name in dst.variables.keys():
            variable_dims={}
            for dim in dst.variables[var_name].dimensions:
                variable_dims[dim]= (dst.dimensions[dim].size if not dst.dimensions[dim].isunlimited() else None) if dim!="VAR" else var_length
            if var_name=="TFLAG":
                var_values=get_updated_tflag(dst.variables[var_name][:],var_length)
            else:
                var_values=dst.variables[var_name][:]
            dict_vars[var_name]={"dtype":dst.variables[var_name].dtype,"data":var_values, 
                                     "ncattrs":{ "units":getattr(dst.variables[var_name], "units") , "var_desc":getattr(dst.variables[var_name], "var_desc"), "long_name": getattr(dst.variables[var_name], "long_name")},
                                     "dimensions":variable_dims}

    save_netcdf_file(output_file,dict_vars,dict_attrs,output_file_format="NETCDF3_CLASSIC")  
    output_file1=os.path.join(save_path, f"cmaq_region_masks")
    append_variables_to_netcdf(netcdf_template_file,output_file1,dict_vars,output_file_format="NETCDF3_CLASSIC")
    # print("done")  
    from esil.map_helper import get_multiple_data,show_maps
    dict_data={}
    for var_name,var_dict in dict_vars.items():
        if var_name=="TFLAG" :#or var_name=="SURF" or var_name=="OPEN":
            continue
        get_multiple_data(dict_data,dataset_name=var_name,variable_name="mask",grid_x=longitudes,grid_y=latitudes,grid_concentration= np.squeeze(var_dict["data"])) 
    layout=(5,2) if len(dict_data)==10 else None   
    if plot_boundary_json_file:
        boundary_json_file=plot_boundary_json_file        
    fig=show_maps(dict_data,unit='',cmap=cmap_conc, show_lonlat=True,projection=proj, boundary_file=boundary_json_file,show_original_grid=True,panel_layout=layout,is_wrf_out_data=True)   
    mask_png_file=output_file+"_mask.png"#os.path.join(save_path, f"{template_file_name}_{json_file_name}_mask.png")   
    fig.savefig(mask_png_file, dpi=300)
    print("mask png file saved")
    
        
if __name__=="__main__":
    # nc_file=r'E:\CO2\data\emis\posterior emission\GD_9km\CONC_BG\2022010100\CONC.bg'
    # model_dir=r'E:\CO2\data\emis\posterior emission\GD_9km\CONC_BG'
    # dates=pd.date_range('2022-01-01',end='2022-12-31',freq='D')
    # from esil.file_helper import get_model_files_by_date
    # for date in dates:
    #     date_str=date.strftime('%Y%m%d')
    #     files=get_model_files_by_date(model_dir,date_str,date_str)
    #     create_netcdf_file_with_dims_update(files)        
      
    
    nc_file='E:/data/emis/CarbonMonitor_total_y2019_m06.nc'
    # start_date = "2019-06-01 00:00:00"
    # num_days = 30
    # date_array =generate_date_array(start_date, num_days)
    # date_array = np.linspace(0, 29, 30)
    # var_unit= f"days since {start_date}"   
    var_name='nday' 
    # update_netcdf_file_variable(nc_file,var_name,date_array,var_unit)
    # data = nc.Dataset(nc_file, mode='r', format="NETCDF3_CLASSIC")
    from esil.file_helper import get_files
     # 获取目录中的所有文件
    variable_name='emission'
    files = get_files(r'E:\data\emis\GRACED')
    all_data = []
    # 逐个打开每个文件并读取数据
    for file in files:
        dataset = nc.Dataset(file)
        variable_data = dataset.variables[variable_name][:]  # 替换为您要读取的变量名称
        all_data.append(variable_data)

    # 合并所有数据为一个大数组
    all_data = np.concatenate(all_data, axis=0)
    # 计算全年平均
    annual_mean = np.mean(all_data, axis=0)
    # 将结果保存到新的文件中
    new_file = "annual_mean.nc"
    new_dataset = nc.Dataset(new_file, mode="w", format="NETCDF4")
    new_dataset.createDimension("time", annual_mean.shape[0])   
    new_dataset.createVariable("annual_mean", "f4", ("time",))
    new_dataset.variables["annual_mean"] = annual_mean
    new_dataset.close()
    



    # 指定要合并的维度 
    # 使用 MFDataset 函数打开多个文件并指定要合并的维度
    # dataset =nc.MFDataset(files, aggdim=var_name)
    # f = nc.MFDataset(files)
    # var = f.variables[variable_name][:]

    nc_file=r'E:\new_CT2022.molefrac_components_glb3x2_2020-12-31.nc'
     
    from plot_map import plotmap
    nc_file= r'/NetcdfReader/CO2 Visualization/CO2-em-anthro_input4MIPs_emissions_CMIP_CEDS-2021-04-21_gn_200001-201912.nc'
    variable_name='CO2_em_anthro'
    data,unit = get_extent_data(nc_file, variable_name)
    #data=get_extent_data(nc_file,variable_name)
    # 对指定列进行求和，使用 axis 参数来指定列维度
    #sum_sector_data = np.sum(data, axis=1)
    sum_data=np.sum(data,axis=(0,1))
    x = sum_data.lon.values
    y = sum_data.lat.values
    data = sum_data.values
    grid_x, grid_y = np.meshgrid(x, y)
    fig=plotmap(grid_x, grid_y, grid_concentration=data, title=variable_name)
    if fig:
        fig.show()

