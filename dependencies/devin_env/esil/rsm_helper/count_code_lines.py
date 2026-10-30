import os
from esil import log
import sys
import chardet

def detect_encoding(file_path):
    with open(file_path, 'rb') as f:
        rawdata = f.read()
        result = chardet.detect(rawdata)
        return result['encoding']

def count_CSharp_code_lines(directory, file_extension=".cs"):
    '''
    @description: 统计指定目录下指定后缀名的文件的行数（不包括注释）
    @param directory: 指定目录
    @param file_extension: 指定后缀名
    @return: 行数
    '''
    total_lines = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(file_extension):
                file_path = os.path.join(root, file)
                try:
                    encoding = detect_encoding(file_path)
                    with open(file_path, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                        non_comment_lines = [line.strip() for line in lines if not line.strip().startswith("//") and not line.strip().startswith("/*") and not line.strip().endswith("*/") and line.strip() != ""]
                        total_lines += len(non_comment_lines)
                except Exception as e:
                    print(file_path)               
                    log.write(e, sys._getframe())
    return total_lines

def count_python_code_lines(directory, file_extension=".py"):
    '''
    @description: 统计指定目录下指定后缀名的文件的行数（不包括注释）
    @param directory: 指定目录
    @param file_extension: 指定后缀名
    @return: 行数
    '''
    total_lines = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(file_extension):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    non_comment_lines = [line.strip() for line in lines if not line.strip().startswith("#") and line.strip() != ""]
                    total_lines += len(non_comment_lines)

    return total_lines

if __name__ == "__main__":
    project_directory = r"D:\Project\EPA\RSM-VAT\Code\ESIL.Kriging"  # 将路径替换为你的 C# 项目路径
    #project_directory = r"D:\Project\EPA\RSM-VAT\Code\RSM-VAT"  # 将路径替换为你的 C# 项目路径
    lines_of_code = count_CSharp_code_lines(project_directory)
    print(f"Total lines of code (excluding comments) in the C# project: {lines_of_code}")
    project_directory = r"D:\Project\EPA\RSM-VAT\Code\RSM-VAT\Script"  # 将路径替换为你的 C# 项目路径
    lines_of_code = count_python_code_lines(project_directory)
    print(f"Total lines of code (excluding comments) in the python scripts: {lines_of_code}")