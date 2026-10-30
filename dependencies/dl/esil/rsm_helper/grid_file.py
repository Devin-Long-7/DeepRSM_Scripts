import numpy as np


def create_grid_from_receptor_grid_file(file_path, output_path='grid.npy'):
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
    result_array = np.zeros(( max_row,max_col), dtype=int)#为了和后面deeprsm脚本保持一致，这里改为先行后列
    for (col, row), (_, id_val) in max_ratios.items():
        result_array[row - 1][col - 1] = id_val
        # 保存为 .npy 文件
    np.save(output_path, result_array)


if __name__ == "__main__":
    file_path =r'E:\paper_data\PRD_Daily_DeepRSM\Config Files\Model_Grids_Info_PRD.txt'
    create_grid_from_receptor_grid_file(file_path,r'E:\paper_data\PRD_Daily_DeepRSM\Config Files\grid.npy')
    print("Success!")