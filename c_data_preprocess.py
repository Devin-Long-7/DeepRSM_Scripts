import numpy as np
import netCDF4 as nc
import os
import sys
print(sys.executable)
import fnmatch
import esil.log_helper as log
from esil.date_helper import get_hour_of_month
from datetime import datetime
from tqdm.auto import tqdm
#logging.basicConfig(filename='python_log.txt',level=logging.DEBUG)
################ 将全域和单区域 100%削减情景的18种前体物由ACONC中提取至data_species_zero.npy ##############
import pandas

scrit_file=os.path.abspath(__file__)
from b_input_data_helper import aconc_dir,aconc_files,aconc_cases,month,output_npy_dir,species_in_cmaq,config_file,oth_region_name
print(f"config_file:{config_file}")

sys.argv = [f'{scrit_file}', aconc_dir, ",".join(aconc_files), 
            ",".join(aconc_cases),output_npy_dir,'data_species_zero','normal',f'[{month}]',",".join([str(x) for x in range(1, 31)]),
            ",".join(species_in_cmaq),",".join([str(x) for x in range(0, 25)])]
file_path = sys.argv[1].strip("'")  
lst_region_file = sys.argv[2].split(",")  
lst_region = sys.argv[3].split(",") 
save_path = sys.argv[4].strip("'")  
file_extension = sys.argv[5]  
mode = sys.argv[6]  # 'mean'  # 'normal'
mons = sys.argv[7].strip("'[").strip("]'").split(",")  # //将c#中传入的字符串参数，转化为python中的列表 # '6'  # 只支持单月份（注意和file_path路径中月份对应）
days = sys.argv[8].strip("'[").strip("]'").split(",")  # '32'  # '1-31', '32'
species_names = sys.argv[9].replace("'",'').strip("'[").strip("]'").split(",") #['HNO3', 'H2O2', 'N2O5', 'NO2', 'FORM', 'HONO','NO', 'O3', 'SO2', 'NH3', 'OH', 'ISOP', 'TERP','ASO4IJ', 'ANO3IJ', 'ANH4IJ', 'ASOCIJ', 'PM25']
species_names=[x.strip() for x in species_names]
hours=sys.argv[10].strip("'[").strip("]'").split(",") # '32'  # '1-31', '32'
hours=[int(x) for x in hours]


def ReplaceBlank(savepath):
    path = savepath.replace("*"," ")
    return  path
save_path = ReplaceBlank(save_path)
file_path = ReplaceBlank(file_path)#还原路径中的空格

if not os.path.exists(save_path):
    os.makedirs(save_path)
    
def ReadEveryday(region_index):
    try:
        # import netCDF4 as nc        
        file_extension= 'data_species_base' if "base" in lst_region[region_index].strip().lower() else 'data_species_zero'
        f = nc.Dataset(os.path.join(file_path, lst_region_file[region_index].strip()))
        row = f.NROWS
        col = f.NCOLS
        varCount = len(species_names)
        year = GetYear(f.SDATE)
        for mon in mons:            
            with tqdm(total=len(days)) as pbar:
                for dd in days:
                    if dd=='32':
                        ReadMean(region_index)
                    else:
                        # print(lst_region_file[region_index] + ': ' + mon + '-' + dd)
                        data = np.zeros((row, col, varCount))
                        for i in range(varCount):
                            var = species_names[i]
                            data[:, :, i] = f.variables[var][int(dd) - 1, 0, :, :]
                        # save_full_path = save_path1 + lst_region[region_index] + save_path2 + str(mon).zfill(2) + '/D' + str(dd) + '/'
                        if not os.path.exists(save_path):
                            os.makedirs(save_path)
                        region_name=lst_region[region_index].strip() if oth_region_name!=lst_region[region_index].strip() else "OTH"                        
                        np.save(os.path.join(save_path, region_name + '_' + year + '_' + str(mon).zfill(
                            2) + '_' + 'D' + str(dd) + '.' + file_extension + '.npy'), data)
                    pbar.set_description(f"Processing {region_name}:{lst_region_file[region_index].strip()}_{year}_{str(mon).zfill(2)}_{str(dd).zfill(2)}")                    
                    pbar.update(1)
    except Exception as e:
        log.write(e,sys._getframe())

def ReadHour(region_index):
    try:
        file_extension= 'data_species_base' if "base" in lst_region[region_index].strip().tolower() else 'data_species_zero'
        # import netCDF4 as nc
        f = nc.Dataset(os.path.join(file_path, lst_region_file[region_index].strip()))
        row = f.NROWS
        col = f.NCOLS
        varCount = len(species_names)
        year = GetYear(f.SDATE)
        for mon in mons:
            with tqdm(total=len(days)*len(hours),desc=f"Processing {lst_region_file[region_index].strip()}_{year}_{str(mon).zfill(2)}") as pbar:
                for dd in days:
                    # with tqdm(total=24,leave=False,desc=f"Processing {lst_region_file[region_index].strip()}_{year}_{str(mon).zfill(2)}_{str(dd).zfill(2)}") as pbar:
                    if dd=='32':
                        ReadMean(region_index)
                    else:                   
                        if not os.path.exists(save_path):
                            os.makedirs(save_path)
                        data = np.zeros((row, col, varCount))
                        for hour in hours:     
                            if hour==24:#表示平均
                                current_date=datetime(int(year),int(mon),int(dd),0)
                                hour_index=get_hour_of_month(current_date) 
                                for i in range(varCount):
                                    var = species_names[i] 
                                    data[:, :, i] =np.mean(f.variables[var][hour_index:hour_index+hour, 0, :, :], axis=0)
                            else:                        
                                current_date=datetime(int(year),int(mon),int(dd),hour)
                                hour_index=get_hour_of_month(current_date)  
                                for i in range(varCount):
                                    var = species_names[i] 
                                    data[:, :, i] = f.variables[var][hour_index, 0, :, :]       
                            hourly_save_path=os.path.join(save_path, f"{lst_region[region_index].strip()}_{year}_{str(mon).zfill(2)}_{str(dd).zfill(2)}_H{str(hour).zfill(2)}.{file_extension}.npy")                    
                            np.save(hourly_save_path, data)
                            pbar.set_description(f"Finished {lst_region_file[region_index].strip()}_{year}_{str(mon).zfill(2)}_{str(dd).zfill(2)}")
                            pbar.update(1)
    except Exception as e:
        log.write(e,sys._getframe())
        
def ReadMean(region_index):
    try:
        file_extension= 'data_species_base' if "base" in lst_region[region_index].strip().tolower() else 'data_species_zero'
        # import netCDF4 as nc
        f = nc.Dataset(os.path.join(file_path, lst_region_file[region_index].strip()))
        row = f.NROWS
        col = f.NCOLS
        varCount = len(species_names)
        year = GetYear(f.SDATE)
        for mon in mons:
            data = np.zeros((row, col, varCount))
            for i in range(varCount):
                var = species_names[i]
                data[:, :, i] = np.mean(f.variables[var][:, 0, :, :], 0)
            # save_full_path = save_path1 + lst_region[region_index] + save_path2 + str(mon).zfill(2) + '/D' + str(32) + '/'
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            np.save(os.path.join(save_path, lst_region[region_index].strip() + '_' + year + '_' + str(mon).zfill(
                2) + '_' + 'D32' + '.' + file_extension + '.npy'), data)
    except Exception as e:
        log.write(e,sys._getframe())


# 从netcdf中的SDATE变量中提取模型数据年份
def GetYear(date_str):
    dateTime = str(date_str)
    year = ''
    if len(dateTime) >= 4:
        year = dateTime[:4]
    return year


# 多个npy文件合并成一个npy文件
'''读取文件路径下的满足filter特征的文件，并进行合并生成文件名为key，value为data的字典'''

def combineNPY(inputFilePath, outputFileName='', filter='*data_species_zero.npy', isRemoveFile=False):
    # temp = []
    try:
        dic = {}
        outputDir = ''
        if inputFilePath.find(':') < 0:  # ':' in inputFilePath
            inputFilePath = os.path.abspath(inputFilePath)
        for root, dirs, files in os.walk(inputFilePath):
            outputDir = root
            for filename in fnmatch.filter(files, filter):
                real_path = (os.path.join(root, filename))
                real_data = np.load(real_path, allow_pickle=True)  # 类型是numpy array
                dic[filename] = real_data
                if isRemoveFile:
                    os.remove(real_path)
                if len(outputFileName) == 0:
                    outputFileName = filename.replace('.npy', '_dict.npy')
                    '''
                    if filter.find('zero')>=0:
                        outputFileName = filename.replace('.npy' , 'dict')
                    #elif filter.find('base')>=0:
                    else:
                        outputFileName = filename.replace('.npy' , '_dict.npy')
                    '''
        np.save(os.path.join(outputDir, outputFileName), dic)
    except Exception as e:
        log.write(e,sys._getframe())


'''将字典中数据安装key值文件名进行输出'''


def sperateNPY(inputFilePath, isRemoveFile=False):
    try:
        data_dic = np.load(inputFilePath, allow_pickle=True).item()  # 字段读取
        dir = os.path.dirname(inputFilePath)  # 获取路径字符串中的目录
        # file=os.path.basename(path)#获取路径字符串中的文件名
        for key in data_dic:
            filepath = os.path.join(dir, key)
            np.save(filepath, data_dic[key])
        if isRemoveFile == True:
            os.remove(inputFilePath)
    except Exception as e:
        log.write(e,sys._getframe())


if __name__ == '__main__':
    
    try:         
        #如果数据是分小时的，则按小时读取 
        # for region_index in range(len(lst_region_file)):
        #         ReadHour(region_index)   
        #如果数据是按天的，则按天读取        
        for region_index in range(len(lst_region_file)):
                ReadEveryday(region_index)   
        print('Calculation complete.')
    except Exception as e:
        log.write(e,sys._getframe()) 