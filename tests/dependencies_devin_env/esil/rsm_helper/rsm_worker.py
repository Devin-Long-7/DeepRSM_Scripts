import os.path
import numpy as np
import pandas as pd
import esil.log_helper as log
import sys
import fnmatch
import random

class rsm_helper:

    def create_grid_from_receptor_grid_file(self,file_path, output_path='grid.npy'):
        '''
        创建DeepRSM所需的grid.npy文件
        :param file_path: 基于Receptor grid file（RSM-VAT 中的网格受体文件）进行获取，对同个网格而言，只保留网格占比最大的记录
        :param output_path: 输出文件路径，默认在当前目录下的grid.npy,用户可以自行指定路径
        :return: 没有返回值
        '''
        # 读取文件
        max_ratios = {}
        with open(file_path, 'r') as file:
            for line in file:
                values = line.strip().split()
                id_val = int(values[0])  # ID
                col = int(values[1])  # Col
                row = int(values[2])  # Row
                ratio = float(values[3])  # Ratio
                current_max_ratio, current_id = max_ratios.get((col, row), (float('-inf'), None))
                if ratio > current_max_ratio:
                    max_ratios[(col, row)] = (ratio, id_val)

        # 输出结果
        print("ID Col Row Ratio Code City")
        # 获取 Col 和 Row 的最大 Ratio 记录的 ID，并存储到 NumPy 二维数组中
        max_col = max(col for col, _ in max_ratios.keys())
        max_row = max(row for _, row in max_ratios.keys())
        result_array = np.zeros((max_row, max_col), dtype=int)  # 为了和后面deeprsm脚本保持一致，这里改为先行后列
        for (col, row), (_, id_val) in max_ratios.items():
            result_array[row - 1][col - 1] = id_val
            # 保存为 .npy 文件
        np.save(output_path, result_array)

    #@staticmethod # Python 没有严格的静态类的概念，但可以通过在类中使用 @staticmethod 装饰器来模拟类级别的静态方法
    def normalize_pollutant(self,pollutant):
        '''
        规范化污染物书写，如NOX统一规范为NOx,PM25改为PM2.5
        :param pollutant:待处理的物种名称
        :return:
        '''
        result = ''
        pollutant = pollutant.upper()
        if pollutant == 'NOX':
            result = 'NOx'
        elif pollutant == 'SO2':
            result = 'SO2'
        elif pollutant == 'NH3':
            result = 'NH3'
        elif pollutant in ('VOCS', 'VOC'):
            result = 'VOC'
        elif pollutant == 'POA':
            result = 'POA'
        elif pollutant in ('PM2.5', 'PM', 'PM25'):
            result = 'PM2.5'
        else:
            result = pollutant
        return result

    #@staticmethod # Python 没有严格的静态类的概念，但可以通过在类中使用 @staticmethod 装饰器来模拟类级别的静态方法
    def get_mapping_data(self,emission_file,cmaq_name='ACONC'):
        '''
        根据RSM-VAT中 Emission matrix文件，获取每个case所对应的名称
        如{'BaseCase': 'ACONC.1', 'Ctrl_All': 'ACONC.21', 'Ctrl_A': 'ACONC.22', 'Ctrl_B': 'ACONC.23', 'Ctrl_C': 'ACONC.24', 'Ctrl_D': 'ACONC.25', 'Ctrl_E': 'ACONC.26', 'Ctrl_F': 'ACONC.27'}
        :param emission_file: Emission matrix文件
        :param cmaq_name: 用做RSM-VAT的模型结果文件名称，如ACONC
        :return: 返回字典，如{'BaseCase': 'ACONC.1', 'Ctrl_All': 'ACONC.21', 'Ctrl_A': 'ACONC.22', 'Ctrl_B': 'ACONC.23', 'Ctrl_C': 'ACONC.24', 'Ctrl_D': 'ACONC.25', 'Ctrl_E': 'ACONC.26', 'Ctrl_F': 'ACONC.27'}
        '''
        dic_mapping_data={}
        try:
            dt = pd.read_csv(emission_file)
            for rowIndex in range(len(dt.index)):
                columnIndex = 0
                factor_infos = []
                for column in dt.columns:
                    arr = column.split(')').pop().replace('\\', '/').replace('_', '/').split('/')
                    if len(arr) >= 3:
                        factor = {
                            "Region": arr[0],
                            "Pollutant": self.normalize_pollutant(arr[1]),
                            "Source": arr[2],
                            "BaseEmissionRatio": float(dt.iloc[rowIndex,columnIndex]),
                            "Index": columnIndex
                        }
                        factor_infos.append(factor)
                    columnIndex += 1
                case_num = f"{cmaq_name}.{dt.iloc[rowIndex,0]}"  # Defaulting to the first column as scenario number
                temp = [f for f in factor_infos if f['Pollutant'] != 'PM2.5']
                total = sum(m['BaseEmissionRatio'] for m in temp)
                if total == len(temp):  # Baseline
                    is_all_base_case = len([p for p in factor_infos if p['BaseEmissionRatio'] == 1]) == len(factor_infos)
                    if is_all_base_case:
                        dic_mapping_data["BaseCase"] = case_num
                elif total == 0:  # Shutdown in all regions
                    dic_mapping_data["Ctrl_All"] = case_num
                elif total == len(temp) - 4:  # Shutdown in a single region
                    # 使用字典来模拟LINQ中的GroupBy和Sum操作
                    grouped = {}
                    for item in temp:
                        region = item['Region']
                        ratio = item['BaseEmissionRatio']
                        if region not in grouped:
                            grouped[region] = {'Sum': 0}
                        grouped[region]['Sum'] += ratio
                    # 找到和为0的第一个Region
                    region = next((key for key, value in grouped.items() if value['Sum'] == 0), None)
                    if region and f"Ctrl_{region}" not in dic_mapping_data:
                            dic_mapping_data[f"Ctrl_{region}"] = case_num

        except Exception as ex:
            log.write(ex,sys._getframe())
        return (dic_mapping_data,factor_infos)

    def get_species_from_mapping_file(self,path):
        '''
        获取18种species（"HNO3", "H2O2", "N2O5", "NO2", "FORM", "HONO", "NO", "O3", "SO2", "NH3", "OH", "ISOP", "TERP", "ASO4IJ", "ANO3IJ", "ANH4IJ", "ASOCIJ", "PM25" ）在cmaq文件中对应的物种名称
        :param path:RSM-VAT中的Species Mapping file
        :return: 返回一一对应的物种字典
        '''
        try:
            if not os.path.exists(path):
                return None
            dic_species = {}  # 映射文件中的物种信息
            dt_species = pd.read_csv(path)
            species_num = len(dt_species.index)
            for i in range(species_num):  # 获取映射文件中的物种映射关系
                dic_species[dt_species.loc[i, "Species Name"]] = dt_species.loc[i, "Species Name In Model File"]
        except Exception as ex:
            log.write(ex, sys._getframe())
        return dic_species

    def reset_to_default_path(self,savepath):
        '''
        将经过处理的文件路径恢复回默认
        :return:
        '''
        path = savepath.replace("*", " ")
        return path

    def GetYear(self,date_str):
        '''
        从netcdf中的SDATE变量中提取模型数据年份
        :param date_str:
        :return:
        '''
        dateTime = str(date_str)
        year = ''
        if len(dateTime) >= 4:
            year = dateTime[:4]
        return year

    # 生成指定范围内的随机数组（允许重复值）
    def generate_random_array_with_duplicates(self, start, end, size):
        random_array = [random.uniform(start, end) for _ in range(size)]
        return random_array


    def combineNPY(self,inputFilePath, outputFileName='', filter='*data_species_zero.npy', isRemoveFile=False):
        '''
         多个npy文件合并成一个npy文件
         读取文件路径下的满足filter特征的文件，并进行合并生成文件名为key，value为data的字典
        :param inputFilePath:
        :param outputFileName:
        :param filter:
        :param isRemoveFile:
        :return:
        '''
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
            log.write(e, sys._getframe())

    def sperateNPY(self,inputFilePath, isRemoveFile=False):
        '''
        将字典中数据安装key值文件名进行输出
        :param inputFilePath:
        :param isRemoveFile:
        :return:
        '''
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
            log.write(e, sys._getframe())

    def read_oos_file(self,oos_emission_file,cmaq_name='ACONC'):
        '''
                根据RSM-VAT中 oos emission文件，获取每个case所对应的矩阵
                如{'BaseCase': 'ACONC.1', 'Ctrl_All': 'ACONC.21', 'Ctrl_A': 'ACONC.22', 'Ctrl_B': 'ACONC.23', 'Ctrl_C': 'ACONC.24', 'Ctrl_D': 'ACONC.25', 'Ctrl_E': 'ACONC.26', 'Ctrl_F': 'ACONC.27'}
                :param oos_file: oos文件
                :param cmaq_name: 用做RSM-VAT的模型结果文件名称，如ACONC
                :return: 返回tuple, item1=字典（key=case_name,value=emission_ctrl),item2=factors集合
                '''
        dic_case_emission = {}
        try:
            dt = pd.read_csv(oos_emission_file)
            for rowIndex in range(len(dt.index)):
                case_num = f"{cmaq_name}.{dt.iloc[rowIndex, 0]}"
                emission_ctrl=dt.iloc[rowIndex, 1:].values.astype(float)
                dic_case_emission[case_num]=emission_ctrl
            columnIndex = 0
            factor_infos = []
            for column in dt.columns:
                arr = column.split(')').pop().replace('\\', '/').replace('_', '/').split('/')
                if len(arr) >= 3:
                    factor = {
                        "Region": arr[0],
                        "Pollutant": self.normalize_pollutant(arr[1]),
                        "Source": arr[2],
                        "BaseEmissionRatio": 1,
                        "Index": columnIndex
                    }
                    factor_infos.append(factor)
                columnIndex += 1
        except Exception as ex:
            log.write(ex, sys._getframe())
        return (dic_case_emission, factor_infos)

if __name__=="__main__":
    helper=rsm_helper()
    dict,factors=helper.get_mapping_data(r'E:\paper_data\PRD_Daily_DeepRSM\Config Files\Matrix_PRD.csv')
    dict1 = helper.get_species_from_mapping_file(r'E:\paper_data\PRD_Daily_DeepRSM\Config Files\SpeciesMapping.csv')
    print(dict)