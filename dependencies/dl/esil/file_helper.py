'''
Author: Devin
Date: 2024-02-27 22:50:27
LastEditors: Devin
LastEditTime: 2024-04-14 11:02:47
FilePath: \PythonDemo\esil\file_helper.py
Description: 

Copyright (c) 2024 by Devin, All Rights Reserved. 
'''
import os

def get_files(root_directory, file_format='',recursive=True):
    '''
    @description: 获取指定文件夹下的所有文件路径
    @param {str} root_directory，需要获取的文件夹目录
    @param {str} file_format，需要获取的文件格式，如'.txt'
    @param {bool} recursive，是否递归遍历子文件夹
    @param {bool} is_include_dir，是否包含文件夹路径
    @return {list}
    @eg: get_files(root_directory='./', file_format='.txt', recursive=True, is_include_dir=False)
    @author: Devin
    @date: 2022-03-01 16:30:23
    '''
    all_files = []
    for root, dirs, files in os.walk(root_directory):       
        for file in files:
            if file_format == '':
                all_files.append(os.path.join(root, file))
            elif file.endswith(file_format):                
                all_files.append(os.path.join(root, file))    
        if not recursive:
            dirs.clear()  # 清空子目录列表，以便不进入子目录
    return all_files

def get_files_old(dir):
    '''
    @description: 获取指定文件夹下的所有文件路径;已废弃
    @param {str} dir，需要获取的文件夹目录
    @return {list}
    @eg: get_files_old(dir='./')   
    '''
    files = os.listdir(dir)
    file_list = []
    for file in files:
        file_path = os.path.join(dir, file)
        # 判断是否是文件夹
        if os.path.isdir(file_path):
            continue
        else:
            file_list.append(file_path)           
    return file_list


def get_files_by_format(directory, file_format='',is_include_dir=False):
    all_files = []
    import glob
    # # 递归遍历目录及其子目录
    # for file_path in glob.iglob(directory + '/**/*.' + file_format, recursive=True):
    #     if is_include_dir:
    #         all_files.append(file_path)
    #     else:
    #         if not os.path.isdir(file_path):
    #             # 排除目录，只添加文件路径
    #             all_files.append(file_path)        
    # 递归遍历目录及其子目录
    for root, dirs, files in os.walk(directory):
        for file in files: 
            if file.endswith(file_format):
                file_path = os.path.join(root, file)
                all_files.append(file_path)
    return all_files


def get_model_files_by_date(model_dir,start_date,end_date):
    '''
    @description: 根据日期获取指定日期范围内的模型文件
    @param {str} model_dir，模型文件夹路径
    @param {str} start_date，开始日期，如'20220301'
    @param {str} end_date，结束日期，如'20220301'
    @return {list} 模型文件路径列表
    @eg: get_model_files_by_date(model_path,'20220301','20220301')
    @author: Devin
    @date: 2022-03-01 16:30:23
    '''       
    from datetime import datetime,timedelta
    start_date = datetime.strptime(start_date, '%Y%m%d')
    end_date = datetime.strptime(end_date, '%Y%m%d')
    end_date=end_date+timedelta(hours=23)
    date_format = "%Y%m%d%H"
    res_files=[]
    for root, dirs, files in os.walk(model_dir):       
        for directory in dirs:
            date_time = datetime.strptime(directory, date_format)
            if date_time >= start_date and date_time <= end_date:
                sub_dir = os.path.join(root, directory)
                sub_files=get_files(sub_dir,recursive=False)
                res_files.append(sub_files[0])  
    return res_files 

