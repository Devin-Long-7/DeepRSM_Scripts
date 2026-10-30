'''
Author: Devin
Date: 2024-08-12 22:31:19
LastEditors: Devin
LastEditTime: 2024-09-03 23:52:30
Description: 

Copyright (c) 2024 by Devin, All Rights Reserved. 
'''
import os
import numpy as np
import pandas as pd
import netCDF4 as nc
from tqdm.auto import tqdm

from esil.date_helper import timer_decorator

import configparser
#使用 argparse 模块来解析命令行参数
import argparse
#将字符串转换为相应的Python对象
import ast
#获取配置文件的路径
parser = argparse.ArgumentParser()
parser.add_argument("--config", help="配置文件的路径")
# args = parser.parse_args()
args, unknown = parser.parse_known_args()  # 忽略未知参数
# 使用 args.config 获取配置文件的路径
config_file = args.config
# 使用 args.config 获取配置文件的路径
# config_file = args.config

def load_config(config_file):
    # 创建配置解析器对象
    config = configparser.ConfigParser()
    if config_file is None:
        # config_file='/DeepLearning/mnt/Devin/01_deeprsm/03_create_rsm_scripts/a_config_d3_2022_09_D.ini'
        # config_file='/DeepLearning/mnt/Devin/01_deeprsm/03_create_rsm_scripts/a_config_d3_202209_D_devin.ini'
        # config_file='/DeepLearning/mnt/Devin/01_deeprsm/03_create_rsm_scripts/a_config_d3_202209_M_devin_8_oos.ini'
        config_file='/DeepLearning/mnt/Devin/01_deeprsm/03_create_rsm_scripts/a_config_d3_202209_M_devin.ini'
        # config_file='/DeepLearning/mnt/Devin/01_deeprsm/03_create_rsm_scripts/a_config_d3_202209_M_PRD_TsingHua.ini'
        # config_file='/DeepLearning/mnt/Devin/01_deeprsm/03_create_rsm_scripts/a_config_d3_202209_M_devin_2021_PRD_TsingHua.ini'      
        # config_file='/DeepLearning/mnt/Devin/01_deeprsm/03_create_rsm_scripts/a_config_d3_2022_09_M.ini'   
        # config_file='/DeepLearning/mnt/Devin/rsm_vat_scripts/b1_config_prd_2022_09_base_ic.ini'   
        # return 
    # 读取配置文件
    config.read(config_file)
    #加载配置文件中的参数
    year=ast.literal_eval(config.get('input_parameters', 'year'))
    month=ast.literal_eval(config.get('input_parameters', 'month'))
    str_month = str(month).zfill(2)
    region_num = ast.literal_eval(config.get('input_parameters', 'region_num'))
    species_num = ast.literal_eval(config.get('input_parameters', 'species_num'))
    aconc_file_prefix = ast.literal_eval(config.get('input_parameters', 'aconc_file_prefix'))
    aconc_file_suffix =  ast.literal_eval(config.get('input_parameters', 'aconc_file_suffix'))
    species_in_cmaq= ast.literal_eval(config.get('input_parameters', 'species_in_cmaq'))#['HNO3', 'H2O2', 'N2O5', 'NO2', 'FORM', 'HONO','NO', 'O3_CN', 'SO2', 'NH3', 'OH', 'ISOP', 'TERP','ASO4IJ', 'ANO3IJ', 'ANH4IJ', 'ASOCIJ', 'PM25_TOT']
    base_case_name=ast.literal_eval(config.get('input_parameters', 'base_case_name')) #"base"
    target_pollutant_idx =ast.literal_eval(config.get('input_parameters', 'target_pollutant_idx'))# 7#O3_CN
    target_pollutant=species_in_cmaq[target_pollutant_idx]
    unit =ast.literal_eval(config.get('input_parameters', 'unit'))
    #加载配置文件中的路径
    aconc_dir =ast.literal_eval(config.get('input_files', 'aconc_dir')).replace("#month#",str_month)# f'/mnt/Devin/data/base_ic/{str_month}'
    oos_aconc_dir =ast.literal_eval(config.get('input_files', 'oos_aconc_dir')).replace("#month#",str_month)# f'/mnt/Devin/data/base_ic/{str_month}/oos'
    matrix_file =ast.literal_eval(config.get('input_files', 'matrix_file'))# r'/mnt/Devin/prd_config_files/Matrix_PRD_2022_deeprsm.csv'
    receptor_file_txt=ast.literal_eval(config.get('input_files', 'receptor_file_txt'))#r'/mnt/Devin/prd_config_files/PRD_2022_region_receptor.txt'
    # region_file_csv =ast.literal_eval(config.get('input_files', 'region_file_csv'))# r'/mnt/Devin/prd_config_files/PRD_2022_region_receptor.csv'
    oos_matrix_file = ast.literal_eval(config.get('input_files', 'oos_matrix_file'))#r'/mnt/Devin/prd_config_files/matrix_prd_2022_oos_287-291.csv'
    sector_aconc_dir=ast.literal_eval(config.get('input_files', 'sector_aconc_dir')).replace("#month#",str_month)#r"/mnt/Devin/data/base_ic/{str_month}/sectors"
    # sector_aconc_file_prefix=ast.literal_eval(config.get('input_files', 'sector_aconc_file_prefix'))
    grid_path =ast.literal_eval(config.get('input_files', 'grid_path'))# r'/mnt/Devin/prd_config_files/grid.npy'
    boundary_file=ast.literal_eval(config.get('input_files', 'boundary_file'))#r'/mnt/Devin/boundary/gd_cities.shp'
    trained_model_file=ast.literal_eval(config.get('input_files', 'trained_model_file'))#'/mnt/Devin/data/deeprsm_trained_model/Model_14710_O3_prd_2022.pth'
    boundary_json_file=ast.literal_eval(config.get('input_files', 'boundary_json_file'))# "/mnt/Devin/boundary/guangdong_cities.json"
    project_name=ast.literal_eval(config.get('input_parameters', 'project_name')).replace("#month#",str_month).replace("#year#",str(year))
    output_dir =ast.literal_eval(config.get('input_files', 'output_dir'))#.replace("#month#",str_month).replace("#year#",str(year))#f'/mnt/Devin/output/prd_{year}_{str_month}_daily_base_ic'
    output_dir=os.path.join(output_dir,project_name)
    output_npy_dir =os.path.join(output_dir,'preprocess_npy_data')
    output_rsm_weights_dir = os.path.join(output_dir,'rsm_weights')
    output_oos_dir = os.path.join(output_dir,'oos')
    if  not os.path.exists(output_dir):
        os.makedirs(output_dir)
    from esil.file_helper import get_files
    all_aconc_files=get_files(aconc_dir,recursive=False)
    whole_region_full_control_case_name=ast.literal_eval(config.get('input_parameters', 'whole_region_full_control_case_name')).upper()#"PRD"#全区域置零情景的名字everywhere2zero
    aconc_files=[os.path.basename(file) for file in all_aconc_files]
    aconc_cases=[os.path.basename(file).replace(aconc_file_prefix,'').replace(aconc_file_suffix,'').replace("2zero","").upper() for file in all_aconc_files]
    oos_aconc_file_prefix = ast.literal_eval(config.get('input_parameters', 'oos_aconc_file_prefix'))
    oos_aconc_file_suffix = ast.literal_eval(config.get('input_parameters', 'oos_aconc_file_suffix'))#'_Daily_ACONC_Sep_2022.nc'
    oth_region_name= ast.literal_eval(config.get('input_parameters', 'oth_region_name')).upper()
    return config_file,year,month,str_month,region_num,species_num,aconc_file_prefix,aconc_file_suffix,species_in_cmaq,base_case_name,target_pollutant_idx,target_pollutant,aconc_dir,oos_aconc_dir,\
           matrix_file,receptor_file_txt,oos_matrix_file,sector_aconc_dir,grid_path,boundary_file,trained_model_file,boundary_json_file,output_dir,output_npy_dir,output_rsm_weights_dir,\
           output_oos_dir,whole_region_full_control_case_name,aconc_files,aconc_cases,all_aconc_files,project_name,unit,oos_aconc_file_prefix,oos_aconc_file_suffix,oth_region_name
           
config_file,year,month,str_month,region_num,species_num,aconc_file_prefix,aconc_file_suffix,species_in_cmaq,base_case_name,target_pollutant_idx,target_pollutant,aconc_dir,oos_aconc_dir,\
           matrix_file,receptor_file_txt,oos_matrix_file,sector_aconc_dir,grid_path,boundary_file,trained_model_file,boundary_json_file,output_dir,output_npy_dir,output_rsm_weights_dir,\
           output_oos_dir,whole_region_full_control_case_name,aconc_files,aconc_cases,all_aconc_files,project_name,unit,oos_aconc_file_prefix,oos_aconc_file_suffix,oth_region_name=load_config(config_file)


def read_receptor_file(receptor_file,region_num):
    # Read region file data
    reg = np.loadtxt(receptor_file, delimiter=',')
    regionCell = [None] * region_num
    regRow, _ = reg.shape
    n = 0
    m = 0
    a = []

    p_index = 0
    while p_index < regRow:
        if reg[p_index, 0] == n + 1:
            a.append(reg[p_index, :])
            m += 1
        else:
            regionCell[n] = np.array(a)
            m = 0
            n += 1
            p_index -= 1
            a = []

        if p_index == regRow - 1:
            regionCell[n] = np.array(a)

        p_index += 1
    return regionCell

def read_receptor_file_txt(receptor_file):
     # Define the column names
    column_names = ['region_id', 'row', 'col', 'ratio', 'region_code', 'region_name']
    # Read the data using pandas
    df = pd.read_csv(receptor_file, 
                    sep=' ',  # Space-separated values
                    header=None,  # No header in the file
                    names=column_names)  # Assign column names 
    df['row'], df['col'] = df['col']-1, df['row']-1#交换位置并减1 让其变为索引     
    grouped = df.groupby('region_id')
    # Create a list to store the numpy arrays
    region_cell = []
    # Iterate over each group and convert to a numpy array
    dict_region_mapping={}
    for _, group in grouped:
        # Select the first four columns and convert to numpy array
        array = group.iloc[:, 0:4].to_numpy()        
        region_cell.append(array)
        region_code,region_name=group.iloc[0,-2],group.iloc[0,-1]
        if dict_region_mapping.get(region_code) is None:
            dict_region_mapping[region_code]=region_name
    return region_cell,dict_region_mapping

class RegionCell:
    def __init__(self):
        self.Row = 0
        self.Col = 0
        self.Ratio = 0.0
        self.CityCode = ""
        self.CityName = ""
        self.Location = 0
        
def parse_region_def_file(region_def_file, col_count=0, is_serial=True):
    # from b0_region_cell import RegionCell
    reader = None
    try:
        region_cell_list={}
        index_row = 2
        index_col = 1
        index_ratio = 3
        index_name = 4
        if not os.path.exists(region_def_file):
            return False
               
        region_cells = None
        city_name = ""
        last_city_name = ""
        
        def get_text(reader):
            # Placeholder for the GetText function implementation
            line = reader.readline()
            return line.strip().split(' ') if line else []
        
        with open(region_def_file, 'r') as reader:
            vals = get_text(reader)
            while vals:
                try:
                    tmp = int(vals[index_col])
                except ValueError:
                    vals = get_text(reader)
                    continue

                for i in range(index_name, len(vals)):
                    if i == index_name:
                        city_name = vals[index_name]
                    elif is_serial:
                        city_name += " " + vals[i]

                if city_name != last_city_name:
                    if region_cells is not None:
                        region_cell_list[last_city_name] = region_cells
                    last_city_name = city_name
                    region_cells = []

                cell = RegionCell()
                cell.Row = int(vals[index_row])
                cell.Col = int(vals[index_col])
                cell.Ratio = float(vals[index_ratio])
                cell.CityCode = vals[index_name]
                if len(vals) > 5:
                    cell.CityName = vals[5]
                if col_count != 0:
                    cell.Location = col_count * (cell.Row - 1) + cell.Col - 1
                region_cells.append(cell)
                vals = get_text(reader)
            if region_cells is not None:
                region_cell_list[last_city_name] = region_cells

        return region_cell_list
    except Exception as ex:      
        return None  
               
@timer_decorator    
def get_oos_matrix_and_aconc(matrix_file,aconc_dir,region_num, species_num,target_pollutant):
    '''
    @description: 获取外部验证模型数据和排放控制矩阵
    @param {matrix_file}: matrix文件路径
    @param {aconc_dir}: aconc文件路径
    @param {region_num}: 区域数
    @param {target_pollutant}: 目标污染物，'O3_CN'或'PM25_TOT'
    @return {data,matrix_emission,base_case_cmaq_data,case_ids}: 模型数据、排放控制矩阵、基准CMAQ数据、case_id列表
    其中，
    data的shape为(species_num+1,case_num,time_step,grid_rows,grid_cols)、
    matrix_emission的shape为(region_num,case_num,species_num)、
    base_case_cmaq_data的shape为(time_step,layer,grid_rows,grid_cols)、
    case_ids为所有case的id列表
    '''
    df_matrix = pd.read_csv(matrix_file)    
    case_num=len(df_matrix)
    # Initialize the matrix with zeros
    matrix_emission = np.zeros((region_num, case_num, species_num))  
    base_case_file = os.path.join(aconc_dir, f"{aconc_file_prefix}{base_case_name}{aconc_file_suffix}")
    ds=nc.Dataset(base_case_file)
    base_case_cmaq_data=ds.variables[target_pollutant][:]
    data_shape=ds.variables[target_pollutant].shape
    time_step,grid_shape=data_shape[0],data_shape[-2:] 
    ds.close() 
    data = np.zeros((1,case_num,time_step)+grid_shape)#1表示只需记录目标污染物的浓度
    case_ids=[]   
    for c_index, row in df_matrix.iterrows():            
        case_id=c_index+1 
        case_ids.append(case_id)          
        aconc_file = os.path.join(oos_aconc_dir, f"{oos_aconc_file_prefix}{case_id}{oos_aconc_file_suffix}")        
        with nc.Dataset(aconc_file, 'r') as ds:          
            data[0, c_index, :,:, :] = ds.variables[target_pollutant][:,0,:,:]                  
        for r_index in range(region_num):
            start_col_index,end_col_index=r_index*species_num+1,(r_index+1)*species_num+1                      
            matrix_emission[r_index, c_index, :]=row.values[start_col_index:end_col_index]       
    return data,matrix_emission,base_case_cmaq_data,case_ids 
           
def get_oos_input_data():     
    '''
    @description: 获取外部验证模型输入数据,包括模型数据、区域单元、排放控制矩阵、基准CMAQ数据、case_id列表
    @return {oos_cmaq_data,region_cell,control_matrix,base_case_cmaq_data,case_ids}: 模型数据、区域单元、排放控制矩阵、基准CMAQ数据、case_id列表
    
    其中，
    oos_cmaq_data的shape为(species_num+1,case_num,time_step,grid_rows,grid_cols)、
    region_cell的shape为(region_num,4)
    control_matrix的shape为(region_num,case_num,species_num)、
    base_case_cmaq_data的shape为(time_step,layer,grid_rows,grid_cols)、
    case_ids为所有case的id列表
    '''
    oos_cmaq_data,control_matrix,base_case_cmaq_data,case_ids=get_oos_matrix_and_aconc(oos_matrix_file,aconc_dir,region_num,species_num,target_pollutant)   
    region_cell=read_receptor_file_txt(receptor_file_txt)
    return oos_cmaq_data, region_cell, control_matrix,base_case_cmaq_data,case_ids

def get_sector_concentration_data(species_sectors={"NOx":['DL','FDL','GC','GD','RJ','OT'],"VOC":['DL','FDL','GC','GD','RJ','OT']}):
    '''
    @description: 获取行业排放模型数据
    @param {aconc_dir}: aconc文件路径，分部门文件格式：ACONC.DL.nc
    @param {region_num}: 区域数
    @param {case_num}: 情景数
    @param {pollutants}: 污染物列表，示例：['NOx', 'SO2', 'NH3', 'VOC', 'O3_CN']
    @return {data}: 行业排放模型数据
    '''
    from esil.file_helper import get_files
    # aconc_dir=r"D:\case\RSM\PRD_Sector_DeepRSM\September"
    if not os.path.exists(sector_aconc_dir):
        return None,None
    aconc_files=get_files(sector_aconc_dir)
    # sectors=['On-Road','Non-Road','Industry_processing','Fixed_combustion','Other_NOx_sources','Solvant use','Other_VOC_sources']  
    # mapping={'DL':'On-Road','FDL':'Non-Road','GC':'Industry_processing','GD':'Fixed_combustion','NOT':'Other_NOx_sources','RJ':'Solvant use','VOT':'Other_VOC_sources'}  
    # data =None     
    sectors=[]
    species=species_sectors.keys()
    dict_data={}
    for idx,aconc_file in enumerate(aconc_files):
        ds=nc.Dataset(aconc_file)
        sector_name=os.path.basename(aconc_file).replace(aconc_file_prefix,"").replace(aconc_file_suffix,"").replace("sector_","").replace("2zero","").upper()       
        if "BASE" in sector_name:
            continue
        varid = species_in_cmaq[target_pollutant_idx]           
        for species,sectors in species_sectors.items():
            if dict_data.get(species) is None:
                dict_data[species]=None
            for sector_idx,sector in enumerate(sectors):
                if sector!=sector_name:
                    continue
                if dict_data[species] is None:
                    data_shape=ds.variables[varid].shape
                    time_step,grid_shape=data_shape[0],data_shape[-2:] 
                    dict_data[species] = np.zeros((len(sectors),time_step)+grid_shape)                               
                dict_data[species][sector_idx,:,:,:]=ds.variables[varid][:,0,:,:] 
        ds.close()   
    return dict_data,species_sectors

# Save to a .mat file
# sio.savemat('./Data/JN_OCT_PM_ALL.mat', {'data': data, 'regionCell': region_cell, 'controlmatrix': control_matrix})
if __name__ == '__main__':  
    data,sectors=get_sector_concentration_data()
    oos_cmaq_data,control_matrix,base_case_cmaq_data,case_ids=get_oos_matrix_and_aconc(oos_matrix_file,aconc_dir,region_num,species_num,target_pollutant)   
    dict_region_cell,dict_region_mapping=read_receptor_file_txt(receptor_file_txt)
    regions=list(dict_region_mapping.values())
   
    
    # data, regionCell, controlmatrix,base_data=get_input_data(is_save_to_pkl=True)
    # dict_region_cell=parse_region_def_file(receptor_file_txt,data.shape[-1])
    # print(data.shape,regionCell,controlmatrix.shape)
        
        
       