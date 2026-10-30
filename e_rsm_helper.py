import numpy as np
import os
import time
import pandas as pd
from tqdm.auto import tqdm
from esil.date_helper import timer_decorator
from b_input_data_helper import year,month,output_npy_dir,output_rsm_weights_dir,output_dir,target_pollutant,grid_path,species_num,\
    whole_region_full_control_case_name,base_case_name,receptor_file_txt,config_file,read_receptor_file_txt

print(f"config_file:{config_file}")
_,dict_receptor=read_receptor_file_txt(receptor_file_txt)
region_zero_cases=[whole_region_full_control_case_name]+list(dict_receptor.values())
input_cmaq = output_npy_dir
input_rsm =output_rsm_weights_dir  
result_root = output_dir
targetPollutant = target_pollutant 
year = str(year)
months = [str(month)]
days = [str(x) for x in range(1, 31)]#['1','2','3', '32'] 
region_zero_cases=[x.strip() for x in region_zero_cases]
hours=[x for x in range(24, 25)]
# -----------------------------------------------------------------------

if not os.path.exists(result_root):
    os.makedirs(result_root)
grid = np.load(grid_path)
row_num = grid.shape[0]
col_num = grid.shape[1]
region_num = len(region_zero_cases) - 1
monthCount = len(months)
dayCount = len(days)

@timer_decorator
def get_grid_values(pollutantIndex, ctrs, month, day,hour=None,unit_conversion_factor=1):
    '''根据物种索引和减排情景，获取的网格浓度'''
    '''
    @param pollutantIndex: 物种索引
    @param ctrs: 减排情景, (region_num,case_num, species_num)
    '''
    start_time = time.time()    
    base_file=os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_D' + str(
        day) + '.data_species_base.npy') if hour is None else os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + '_H' + str(hour).zfill(2) + '.data_species_base.npy')   
    if not os.path.exists(base_file):
        print(f"File {base_file} does not exist")
    ## 2.读取基准O3浓度
    base = np.load(base_file)
    bo3 = base[:, :, pollutantIndex]
    case_num=ctrs.shape[-2] #shape=(region_num,case_num,species_num)
    ## 3.计算各单区域前体物对网格的直接贡献
    rC = np.zeros((row_num, col_num, region_num,case_num))  # 单区域贡献ΔO3
    trW = np.zeros((row_num, col_num, 14, region_num))  # 单区域RSM曲面的14项系数
    
    func = lambda nox_emis, so2_emis, nh3_emis, vocs_emis: (          
            np.array([nox_emis**5, nox_emis**4, nox_emis**3, nox_emis**2, nox_emis, vocs_emis, vocs_emis**2, vocs_emis**3, nox_emis * vocs_emis, nox_emis * vocs_emis**3, nox_emis**5 * vocs_emis, nox_emis**2 * vocs_emis, so2_emis, nh3_emis])
        )#返回数组大小为(14,case_num)
    for rr in range(1, region_num + 1):
        c = ctrs[rr - 1,:, :4] - 1.
        dt=func(c[:, 0], c[:, 1],  c[:, 2], c[:, 3])       
        # rW[..., np.newaxis] * dt[np.newaxis, np.newaxis, ...]      
        rw_file=os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(day) + '.npy') if hour is None \
            else os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(day) + '_H' + str(hour).zfill(2)  + '.npy')
        rW = np.load(rw_file)        
        # 通过广播机制进行逐元素相乘
        # A 的形状 (142, 178, 14) -> (142, 178, 14, 1)
        # B 的形状 (14, 5) -> (1, 1, 14, 5)
        # 输出 (142, 178, 14, 5)
        rC[:, :, rr - 1,:] = np.sum(rW[..., np.newaxis] * dt[np.newaxis, np.newaxis, ...], 2)#对第三维度进行求和，即对14项进行求和，得到(142, 178, case_num)
        trW[:, :, :, rr - 1] = rW #(142, 178, 14,region_num,case_num)
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' (1/3)')

    ## 4.计算各区域前体物对网格的间接贡献
    tw_file=os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(day) + '.npy') if hour is None \
        else os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(day) + '_H' + str(hour).zfill(2) + '.npy')
    tW = np.load(tw_file)#(142, 178, 14)
    iW = tW - np.sum(trW, 3)#对第三维度即region_num进行求和(142, 178, 14)
    iC = np.zeros((row_num, col_num,case_num))  # ①用全域和单区域的RSM得到各网格的间接效应贡献
    for rr in range(1, region_num + 1):
        c = ctrs[rr - 1,:, :4] - 1.   
        dt=func(c[:, 0], c[:, 1],  c[:, 2], c[:, 3])   
        iC += np.where((grid == rr)[..., np.newaxis], np.sum(iW[..., np.newaxis] * dt[np.newaxis, np.newaxis, ...], 2), 0)#对第三维度进行求和，即对14项进行求和#np.where 的三个参数（条件、True 分支、False 分支）必须具有相同的形状。(grid == rr)结果需要进行广播扩展为(row_num, col_num,1)

    rw12_path = os.path.join(input_rsm, base_case_name + '_' + '.O3ind_M' + str(month).zfill(2) + '_D' + str(
        day) + '.npy') if hour is None \
        else os.path.join(input_rsm, base_case_name + '_' + '.O3ind_M' + str(month).zfill(2) + '_D' + str(day) + '_H' + str(hour).zfill(2) + '.npy')
    rw12 = np.zeros((row_num, col_num, region_num, region_num))  # ②间接效应修正权重：单区域削减贡献相关
    if not os.path.exists(rw12_path):
        zconc = np.zeros((row_num, col_num, region_num))  # 单区域前体物100%削减情景的O3浓度
        for rr in range(1, region_num + 1):
            full_control_file=os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(2) + '_D' + str(day) + '.data_species_zero.npy') if hour is None \
                else os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + '_H' + str(hour).zfill(2) + '.data_species_zero.npy')
            rzero = np.load(full_control_file)[:, :, pollutantIndex]
            zconc[:, :, rr - 1] = np.abs(bo3 - rzero)

        w12 = np.zeros((row_num, col_num, region_num, region_num))
        for r1 in range(region_num - 1):
            for r2 in range(r1 + 1, region_num):
                w12[:, :, r1, r2] = zconc[:, :, r1] * zconc[:, :, r2]  # 间接效应权重初始计算值
        for r1 in range(region_num - 1):
            for r2 in range(r1 + 1, region_num):
                tmp1 = w12[:, :, r1, r2] / (np.sum(w12, (2, 3)) + 1e-9)
                rw12[:, :, r1, r2] = np.where(tmp1 > 1, 1, tmp1)  # 间接效应权重修正值
        np.save(rw12_path, rw12)
    else:
        rw12 = np.load(rw12_path)
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' (2/3)')
    riC = np.zeros((row_num, col_num,case_num))
    for r1 in range(region_num - 1):  # ③间接效应修正权重：两两配对
        c = ctrs[r1,:, :4] - 1.
        # dt = [c[0] ** 5, c[0] ** 4, c[0] ** 3, c[0] ** 2, c[0], c[3], c[3] ** 2, c[3] ** 3, c[0] * c[3],
        #       c[0] * c[3] ** 3, c[0] ** 5 * c[3], c[0] ** 2 * c[3], c[1], c[2]]
        dt=func(c[:, 0], c[:, 1],  c[:, 2], c[:, 3]) #(14,5)         
        for r2 in range(r1 + 1, region_num):
            rCr = np.sum(trW[:, :, :, r2, np.newaxis] * dt[np.newaxis, np.newaxis, ...], 2)#(142, 178, case_num)
            out1 = np.where(rCr * rC[:, :, r2,:] == 0, 0, np.abs(rCr / rC[:, :, r2,:]))
            out = np.where(rCr * rC[:, :, r2,:] == 0, 0, np.abs(rC[:, :, r2,:] / rCr))
            out = np.where(out > out1, out1, out)#(142, 178, case_num)
            riC += rw12[:, :, r1, r2, np.newaxis] * out * iC

    fout = np.sum(rC, 2) + riC  #np.sum(rC, 2)对第三维度即所有区域进行加和，最后叠加①②③获得的间接效应riC贡献的ΔO3
    iout = fout.copy()
    rsm_temp = iout + bo3[...,np.newaxis]
    rsm=np.transpose(rsm_temp,(2,0,1))
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' ' + (str(hour) if hour is not None else '')  + ' (3/3). Comsumes %.3f seconds' % (
    #         time.time() - start_time))
    return rsm*unit_conversion_factor,bo3*unit_conversion_factor

'''根据物种索引和减排情景，获取臭氧的网格浓度'''
@timer_decorator
def GetOzoneGridValues(pollutantIndex, ctr, month, day,hour=None,unit_conversion_factor=1):
    start_time = time.time()
    base_file=os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_D' + str(
        day) + '.data_species_base.npy') if hour is None else os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + '_H' + str(hour).zfill(2) + '.data_species_base.npy')   
    if not os.path.exists(base_file):
        print(f"File {base_file} does not exist")
    ## 2.读取基准O3浓度
    base = np.load(base_file)
    bo3 = base[:, :, pollutantIndex]

    ## 3.计算各单区域前体物对网格的直接贡献
    rC = np.zeros((row_num, col_num, region_num))  # 单区域贡献ΔO3
    trW = np.zeros((row_num, col_num, 14, region_num))  # 单区域RSM曲面的14项系数

    for rr in range(1, region_num + 1):
        c = ctr[rr - 1, :4] - 1.
        dt = [c[0] ** 5, c[0] ** 4, c[0] ** 3, c[0] ** 2, c[0], c[3], c[3] ** 2, c[3] ** 3, c[0] * c[3],
              c[0] * c[3] ** 3, c[0] ** 5 * c[3], c[0] ** 2 * c[3], c[1], c[2]]
        rw_file=os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(day) + '.npy') if hour is None \
            else os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(day) + '_H' + str(hour).zfill(2)  + '.npy')
        rW = np.load(rw_file)
        rC[:, :, rr - 1] = np.sum(rW * dt, 2)
        trW[:, :, :, rr - 1] = rW
    print(year + ' - ' + str(month) + ' - ' + str(day) + ' (1/3)')

    ## 4.计算各区域前体物对网格的间接贡献
    tw_file=os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(day) + '.npy') if hour is None \
        else os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(day) + '_H' + str(hour).zfill(2) + '.npy')
    tW = np.load(tw_file)
    iW = tW - np.sum(trW, 3)
    iC = np.zeros((row_num, col_num))  # ①用全域和单区域的RSM得到各网格的间接效应贡献
    for rr in range(1, region_num + 1):
        c = ctr[rr - 1, :4] - 1.
        dt = [c[0] ** 5, c[0] ** 4, c[0] ** 3, c[0] ** 2, c[0], c[3], c[3] ** 2, c[3] ** 3, c[0] * c[3],
              c[0] * c[3] ** 3, c[0] ** 5 * c[3], c[0] ** 2 * c[3], c[1], c[2]]
        iC += np.where(grid == rr, np.sum(iW * dt, 2), 0)

    rw12_path = os.path.join(input_rsm, base_case_name + '_' + '.O3ind_M' + str(month).zfill(2) + '_D' + str(
        day) + '.npy') if hour is None \
        else os.path.join(input_rsm, base_case_name + '_' + '.O3ind_M' + str(month).zfill(2) + '_D' + str(day) + '_H' + str(hour).zfill(2) + '.npy')
    rw12 = np.zeros((row_num, col_num, region_num, region_num))  # ②间接效应修正权重：单区域削减贡献相关
    if not os.path.exists(rw12_path):
        zconc = np.zeros((row_num, col_num, region_num))  # 单区域前体物100%削减情景的O3浓度
        for rr in range(1, region_num + 1):
            full_control_file=os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(2) + '_D' + str(day) + '.data_species_zero.npy') if hour is None \
                else os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + '_H' + str(hour).zfill(2) + '.data_species_zero.npy')
            rzero = np.load(full_control_file)[:, :, pollutantIndex]
            zconc[:, :, rr - 1] = np.abs(bo3 - rzero)

        w12 = np.zeros((row_num, col_num, region_num, region_num))
        for r1 in range(region_num - 1):
            for r2 in range(r1 + 1, region_num):
                w12[:, :, r1, r2] = zconc[:, :, r1] * zconc[:, :, r2]  # 间接效应权重初始计算值
        for r1 in range(region_num - 1):
            for r2 in range(r1 + 1, region_num):
                tmp1 = w12[:, :, r1, r2] / (np.sum(w12, (2, 3)) + 1e-9)
                rw12[:, :, r1, r2] = np.where(tmp1 > 1, 1, tmp1)  # 间接效应权重修正值
        np.save(rw12_path, rw12)
    else:
        rw12 = np.load(rw12_path)
    print(year + ' - ' + str(month) + ' - ' + str(day) + ' (2/3)')
    riC = np.zeros((row_num, col_num))
    for r1 in range(region_num - 1):  # ③间接效应修正权重：两两配对
        c = ctr[r1, :4] - 1.
        dt = [c[0] ** 5, c[0] ** 4, c[0] ** 3, c[0] ** 2, c[0], c[3], c[3] ** 2, c[3] ** 3, c[0] * c[3],
              c[0] * c[3] ** 3, c[0] ** 5 * c[3], c[0] ** 2 * c[3], c[1], c[2]]
        for r2 in range(r1 + 1, region_num):
            rCr = np.sum(trW[:, :, :, r2] * dt, 2)
            out1 = np.where(rCr * rC[:, :, r2] == 0, 0, np.abs(rCr / rC[:, :, r2]))
            out = np.where(rCr * rC[:, :, r2] == 0, 0, np.abs(rC[:, :, r2] / rCr))
            out = np.where(out > out1, out1, out)
            riC += rw12[:, :, r1, r2] * out * iC

    fout = np.sum(rC, 2) + riC  # 叠加①②③获得的间接效应riC贡献的ΔO3
    iout = fout.copy()
    rsm = iout + bo3
    print(year + ' - ' + str(month) + ' - ' + str(day) + ' ' + (str(hour) if hour is not None else '')  + ' (3/3). Comsumes %.3f seconds' % (
            time.time() - start_time))
    return rsm*unit_conversion_factor,bo3*unit_conversion_factor

'''
@descriptions:根据物种索引和减排情景，获取臭氧的网格浓度
@param pollutantIndex {int}: 物种索引
@param ctr {numpy.ndarray}: 减排情景, (region_num,4)
@param month {int}: 月
@param day {int}: 日
@param hour {int}: 小时，默认为None，表示获取日数据
@param unit_conversion_factor {float}: 单位转换系数，默认为1
'''
# @timer_decorator
def get_ozone_grid_values(pollutantIndex, ctr, month, day,hour=None,unit_conversion_factor=1):
    start_time = time.time()
    base_file=os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_D' + str(
        day) + '.data_species_base.npy') if hour is None else os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + '_H' + str(hour).zfill(2) + '.data_species_base.npy')   
    if not os.path.exists(base_file):
        print(f"File {base_file} does not exist")
    ## 2.读取基准O3浓度
    base = np.load(base_file)
    bo3 = base[:, :, pollutantIndex]

    ## 3.计算各单区域前体物对网格的直接贡献
    rC = np.zeros((row_num, col_num, region_num))  # 单区域贡献ΔO3
    trW = np.zeros((row_num, col_num, 14, region_num))  # 单区域RSM曲面的14项系数

    for rr in range(1, region_num + 1):
        c = ctr[rr - 1, :4] - 1.
        dt = [c[0] ** 5, c[0] ** 4, c[0] ** 3, c[0] ** 2, c[0], c[3], c[3] ** 2, c[3] ** 3, c[0] * c[3],
              c[0] * c[3] ** 3, c[0] ** 5 * c[3], c[0] ** 2 * c[3], c[1], c[2]]
        rw_file=os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(day) + '.npy') if hour is None \
            else os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(day) + '_H' + str(hour).zfill(2)  + '.npy')
        rW = np.load(rw_file)
        rC[:, :, rr - 1] = np.sum(rW * dt, 2)
        trW[:, :, :, rr - 1] = rW
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' (1/3)')

    ## 4.计算各区域前体物对网格的间接贡献
    tw_file=os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(day) + '.npy') if hour is None \
        else os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(day) + '_H' + str(hour).zfill(2) + '.npy')
    tW = np.load(tw_file)
    iW = tW - np.sum(trW, 3)
    iC = np.zeros((row_num, col_num))  # ①用全域和单区域的RSM得到各网格的间接效应贡献
    for rr in range(1, region_num + 1):
        c = ctr[rr - 1, :4] - 1.
        dt = [c[0] ** 5, c[0] ** 4, c[0] ** 3, c[0] ** 2, c[0], c[3], c[3] ** 2, c[3] ** 3, c[0] * c[3],
              c[0] * c[3] ** 3, c[0] ** 5 * c[3], c[0] ** 2 * c[3], c[1], c[2]]
        iC += np.where(grid == rr, np.sum(iW * dt, 2), 0)

    rw12_path = os.path.join(input_rsm, base_case_name + '_' + 'O3_new_ind_M' + str(month).zfill(2) + '_D' + str(
        day) + '.npy') if hour is None \
        else os.path.join(input_rsm, base_case_name + '_' + 'O3_new_ind_M' + str(month).zfill(2) + '_D' + str(day) + '_H' + str(hour).zfill(2) + '.npy')
    rw12 = np.zeros((row_num, col_num, region_num, region_num))  # ②间接效应修正权重：单区域削减贡献相关
    if not os.path.exists(rw12_path):
        zconc = np.zeros((row_num, col_num, region_num))  # 单区域前体物100%削减情景的O3浓度
        for rr in range(1, region_num + 1):
            full_control_file=os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(2) + '_D' + str(day) + '.data_species_zero.npy') if hour is None \
                else os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + '_H' + str(hour).zfill(2) + '.data_species_zero.npy')
            rzero = np.load(full_control_file)[:, :, pollutantIndex]
            zconc[:, :, rr - 1] = np.abs(bo3 - rzero)

        w12 = np.zeros((row_num, col_num, region_num, region_num))
        for r1 in range(region_num):
            for r2 in range(region_num):
                if r1==r2:
                    continue
                w12[:, :, r1, r2] = zconc[:, :, r1] * zconc[:, :, r2]  # 间接效应权重初始计算值
        for r1 in range(region_num):
            for r2 in range(region_num):
                if r1==r2:
                    continue
                tmp1 = w12[:, :, r1, r2] / (np.sum(w12, (2, 3)) + 1e-9)
                rw12[:, :, r1, r2] = np.where(tmp1 > 1, 1, tmp1)  # 间接效应权重修正值
        np.save(rw12_path, rw12)
    else:
        rw12 = np.load(rw12_path)
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' (2/3)')
    riC = np.zeros((row_num, col_num))
    for r1 in range(region_num):  # ③间接效应修正权重：两两配对
        c = ctr[r1, :4] - 1.
        dt = [c[0] ** 5, c[0] ** 4, c[0] ** 3, c[0] ** 2, c[0], c[3], c[3] ** 2, c[3] ** 3, c[0] * c[3],
              c[0] * c[3] ** 3, c[0] ** 5 * c[3], c[0] ** 2 * c[3], c[1], c[2]]
        for r2 in range(region_num):
            if r1==r2:
                continue
            rCr = np.sum(trW[:, :, :, r2] * dt, 2)
            out1 = np.where(rCr * rC[:, :, r2] == 0, 0, np.abs(rCr / rC[:, :, r2]))
            out = np.where(rCr * rC[:, :, r2] == 0, 0, np.abs(rC[:, :, r2] / rCr))
            out = np.where(out > out1, out1, out)
            riC += rw12[:, :, r1, r2] * out * iC

    fout = np.sum(rC, 2) + riC  # 叠加①②③获得的间接效应riC贡献的ΔO3
    iout = fout.copy()
    rsm = iout + bo3
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' ' + (str(hour) if hour is not None else '')  + ' (3/3). Comsumes %.3f seconds' % (
    #         time.time() - start_time))
    return rsm*unit_conversion_factor,bo3*unit_conversion_factor
      
'''根据物种索引和减排情景，获取PM2.5的网格浓度'''
@timer_decorator
def GetPM25GridValues(pollutantIndex, ctr, month, day):
    start_time = time.time()
    ## 2.读取基准PM浓度
    base = np.load(os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_D' + str(
        day) + '.data_species_base.npy'))
    bpm = base[:, :, pollutantIndex]

    ## 3.计算各单区域前体物对网格的直接贡献
    rC = np.zeros((row_num, col_num, region_num))  # 单区域贡献ΔPM
    trW = np.zeros((row_num, col_num, 14, region_num))  # 单区域RSM曲面的14项系数

    for rr in range(1, region_num + 1):
        c = ctr[rr - 1, :4] - 1.
        dt = [c[3], c[2], c[2] ** 2, c[2] ** 3, c[1], c[3] ** 2, c[0] * c[3], c[0] ** 2 * c[3],
              c[0] ** 4 * c[3], c[0] * c[2], c[0], c[0] ** 2, c[0] ** 3, c[0] ** 4]
        rW = np.load(
            os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(
                day) + '.npy'))
        rC[:, :, rr - 1] = np.sum(rW * dt, 2)
        trW[:, :, :, rr - 1] = rW
    print(year + ' - ' + month + ' - ' + day + ' (1/4)')

    ## 4.计算各区域前体物对网格的间接贡献
    tW = np.load(
        os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(
            day) + '.npy'))
    iW = tW - np.sum(trW, 3)
    iC = np.zeros((row_num, col_num))  # ①用全域和单区域的RSM得到各网格的间接效应贡献
    for rr in range(1, region_num + 1):
        c = ctr[rr - 1, :4] - 1.
        dt = [c[3], c[2], c[2] ** 2, c[2] ** 3, c[1], c[3] ** 2, c[0] * c[3], c[0] ** 2 * c[3],
              c[0] ** 4 * c[3], c[0] * c[2], c[0], c[0] ** 2, c[0] ** 3, c[0] ** 4]
        iC += np.where(grid == rr, np.sum(iW * dt, 2), 0)

    rw12_path = os.path.join(input_rsm, base_case_name + '_' + '.PMind_M' + str(month).zfill(2) + '_D' + str(
        day) + '.npy')
    rw12 = np.zeros((row_num, col_num, region_num, region_num))  # ②间接效应修正权重：单区域削减贡献相关
    if not os.path.exists(rw12_path):
        zconc = np.zeros((row_num, col_num, region_num))  # 单区域前体物100%削减情景的PM浓度
        for rr in range(1, region_num + 1):
            rzero = np.load(os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(
                2) + '_D' + str(day) + '.data_species_zero.npy'))[:, :, pollutantIndex]
            zconc[:, :, rr - 1] = np.abs(bpm - rzero)

        w12 = np.zeros((row_num, col_num, region_num, region_num))
        for r1 in range(region_num - 1):
            for r2 in range(r1 + 1, region_num):
                w12[:, :, r1, r2] = zconc[:, :, r1] * zconc[:, :, r2]  # 间接效应权重初始计算值
        for r1 in range(region_num - 1):
            for r2 in range(r1 + 1, region_num):
                tmp1 = w12[:, :, r1, r2] / (np.sum(w12, (2, 3)) + 1e-9)
                rw12[:, :, r1, r2] = np.where(tmp1 > 1, 1, tmp1)  # 间接效应权重修正值
        np.save(rw12_path, rw12)
    else:
        rw12 = np.load(rw12_path)

    riC = np.zeros((row_num, col_num))
    for r1 in range(region_num - 1):  # ③间接效应修正权重：两两配对
        c = ctr[r1, :4] - 1.
        dt = [c[3], c[2], c[2] ** 2, c[2] ** 3, c[1], c[3] ** 2, c[0] * c[3], c[0] ** 2 * c[3],
              c[0] ** 4 * c[3],
              c[0] * c[2], c[0], c[0] ** 2, c[0] ** 3, c[0] ** 4]
        for r2 in range(r1 + 1, region_num):
            rCr = np.sum(trW[:, :, :, r2] * dt, 2)
            out1 = np.where(rCr * rC[:, :, r2] == 0, 0, np.abs(rCr / rC[:, :, r2]))
            out = np.where(rCr * rC[:, :, r2] == 0, 0, np.abs(rC[:, :, r2] / rCr))
            out = np.where(out > out1, out1, out)
            riC += rw12[:, :, r1, r2] * out * iC

    fout = np.sum(rC, 2) + riC  # 叠加①②③获得的间接效应riC贡献的ΔPM
    iout = fout.copy()
    print(year + ' - ' + str(month) + ' - ' + day + ' (2/4)')
    isContainPrimaryPM = 'true'
    ## 5.计算各区域一次PM的贡献
    if isContainPrimaryPM == 'true':
            for r1 in range(region_num):
                ppmPath = os.path.join(input_cmaq, region_zero_cases[r1] + "_" + year + '_' + str(month).zfill(2) + '_D' + str(day) + '.data_species_zero_ppm.npy')
                if os.path.exists(ppmPath):
                    ppm = np.load(ppmPath)
                    iout += (bpm - ppm) * (ctr[r1, 4] - 1)
    print(year + ' - ' + str(month) + ' - ' + day + ' (3/4)')
    pout = iout.copy()
    rsm = pout + bpm
    print(year + ' - ' + month + ' - ' + day + ' (4/4). Comsumes %.3f seconds' % (
            time.time() - start_time))

    return rsm
            
@timer_decorator
def get_grid_values_by_precusors(pollutantIndex, ctrs, month, day,hour=None,unit_conversion_factor=1):
    '''根据物种索引和减排情景，获取的网格浓度'''
    '''
    @param pollutantIndex: 物种索引
    @param ctrs: 减排情景, (region_num,5, species_num)
    '''
    start_time = time.time()    
    base_file=os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_D' + str(
        day) + '.data_species_base.npy') if hour is None else os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + '_H' + str(hour).zfill(2) + '.data_species_base.npy')   
    if not os.path.exists(base_file):
        print(f"File {base_file} does not exist")
    ## 2.读取基准O3浓度
    base = np.load(base_file)
    bo3 = base[:, :, pollutantIndex]
    case_num=ctrs.shape[-2] #shape=(region_num,case_num,species_num)
    ## 3.计算各单区域前体物对网格的直接贡献
    rC = np.zeros((row_num, col_num, region_num,case_num))  # 单区域贡献ΔO3
    rC_by_precusors = np.zeros((row_num, col_num, region_num,case_num,species_num))  # 单区域贡献ΔO3
    trW = np.zeros((row_num, col_num, 14, region_num))  # 单区域RSM曲面的14项系数
    
    func = lambda nox_emis, so2_emis, nh3_emis, vocs_emis: (          
            np.array([nox_emis**5, nox_emis**4, nox_emis**3, nox_emis**2, nox_emis, vocs_emis, vocs_emis**2, vocs_emis**3, nox_emis * vocs_emis, nox_emis * vocs_emis**3, nox_emis**5 * vocs_emis, nox_emis**2 * vocs_emis, so2_emis, nh3_emis])
        )#返回数组大小为(14,case_num)
    for rr in range(1, region_num + 1):
        c = ctrs[rr - 1,:, :4] - 1.
        dt=func(c[:, 0], c[:, 1],  c[:, 2], c[:, 3])       
        # rW[..., np.newaxis] * dt[np.newaxis, np.newaxis, ...]      
        rw_file=os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(day) + '.npy') if hour is None \
            else os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(day) + '_H' + str(hour).zfill(2)  + '.npy')
        rW = np.load(rw_file)        
        # 通过广播机制进行逐元素相乘：# A 的形状 (142, 178, 14) -> (142, 178, 14, 1)；# B 的形状 (14, 5) -> (1, 1, 14, 5)；# 输出 (142, 178, 14, 5)
        temp_rc = rW[..., np.newaxis] * dt[np.newaxis, np.newaxis, ...]#对第三维度进行求和，即对14项进行求和，得到(142, 178,14, case_num)
        rC_by_precusors[:, :, rr - 1,:,0] = temp_rc[:, :, 0,:]+temp_rc[:, :, 1,:]+temp_rc[:, :, 2,:]+temp_rc[:, :, 3,:]+temp_rc[:, :, 4,:]+temp_rc[:, :, 8,:]*0.5+temp_rc[:, :, 9,:]*(1.0/4.0)+temp_rc[:, :, 10,:]*(5.0/6.0)+temp_rc[:, :, 11,:]*(2.0/3.0)
        rC_by_precusors[:, :, rr - 1,:,1] = temp_rc[:, :, 12,:]
        rC_by_precusors[:, :, rr - 1,:,2] = temp_rc[:, :, 13,:]
        rC_by_precusors[:, :, rr - 1,:,3] = temp_rc[:, :, 5,:]+temp_rc[:, :, 6,:]+temp_rc[:, :, 7,:]+temp_rc[:, :, 8,:]*0.5+temp_rc[:, :, 9,:]*(3.0/4.0)+temp_rc[:, :, 10,:]*(1.0/6.0)+temp_rc[:, :, 11,:]*(1.0/3.0)        
        rC[:, :, rr - 1,:] = np.sum(temp_rc, 2)#对第三维度进行求和，即对14项进行求和，得到(142, 178, case_num)
        trW[:, :, :, rr - 1] = rW #(142, 178, 14,region_num,case_num)
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' (1/3)')

    ## 4.计算各区域前体物对网格的间接贡献
    tw_file=os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(day) + '.npy') if hour is None \
        else os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(day) + '_H' + str(hour).zfill(2) + '.npy')
    tW = np.load(tw_file)#(142, 178, 14)
    iW = tW - np.sum(trW, 3)#对第三维度即region_num进行求和(142, 178, 14)
    iC = np.zeros((row_num, col_num,case_num))  # ①用全域和单区域的RSM得到各网格的间接效应贡献
    iC_by_precusors = np.zeros((row_num, col_num,case_num,species_num))  # ①用全域和单区域的RSM得到各网格的间接效应贡献
    for rr in range(1, region_num + 1):
        c = ctrs[rr - 1,:, :4] - 1.   
        dt=func(c[:, 0], c[:, 1],  c[:, 2], c[:, 3])   
        temp_ic=iW[..., np.newaxis] * dt[np.newaxis, np.newaxis, ...] #(142, 178, 14,5)
        iC_by_precusors[...,0] += np.where((grid == rr)[..., np.newaxis], \
           temp_ic[...,0,:]+temp_ic[...,1,:]+temp_ic[...,2,:]+temp_ic[...,3,:]+temp_ic[...,4,:]+temp_ic[...,8,:]*0.5+temp_ic[...,9,:]*(1.0/4.0)+temp_ic[...,10,:]*(5.0/6.0)+temp_ic[...,11,:]*(2.0/3.0), 0)        
        iC_by_precusors[...,1] +=np.where((grid == rr)[..., np.newaxis],  temp_ic[...,12,:], 0)
        iC_by_precusors[...,2] += np.where((grid == rr)[..., np.newaxis], temp_ic[...,13,:],0)
        iC_by_precusors[...,3] +=np.where((grid == rr)[..., np.newaxis], \
            temp_ic[...,5,:]+temp_ic[...,6,:]+temp_ic[...,7,:]+temp_ic[...,8,:]*0.5+temp_ic[...,9,:]*(3.0/4.0)+temp_ic[...,10,:]*(1.0/6.0)+temp_ic[...,11,:]*(1.0/3.0) ,0)
        #对第三维度进行求和，即对14项进行求和#np.where 的三个参数（条件、True 分支、False 分支）必须具有相同的形状。(grid == rr)结果需要进行广播扩展为(row_num, col_num,1)
        iC += np.where((grid == rr)[..., np.newaxis], np.sum(temp_ic, 2), 0)

    rw12_path = os.path.join(input_rsm, base_case_name + '_' + '.O3ind_M' + str(month).zfill(2) + '_D' + str(
        day) + '.npy') if hour is None \
        else os.path.join(input_rsm, base_case_name + '_' + '.O3ind_M' + str(month).zfill(2) + '_D' + str(day) + '_H' + str(hour).zfill(2) + '.npy')
    rw12 = np.zeros((row_num, col_num, region_num, region_num))  # ②间接效应修正权重：单区域削减贡献相关
    if not os.path.exists(rw12_path):
        zconc = np.zeros((row_num, col_num, region_num))  # 单区域前体物100%削减情景的O3浓度
        for rr in range(1, region_num + 1):
            full_control_file=os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(2) + '_D' + str(day) + '.data_species_zero.npy') if hour is None \
                else os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + '_H' + str(hour).zfill(2) + '.data_species_zero.npy')
            rzero = np.load(full_control_file)[:, :, pollutantIndex]
            zconc[:, :, rr - 1] = np.abs(bo3 - rzero)

        w12 = np.zeros((row_num, col_num, region_num, region_num))
        for r1 in range(region_num - 1):
            for r2 in range(r1 + 1, region_num):
                w12[:, :, r1, r2] = zconc[:, :, r1] * zconc[:, :, r2]  # 间接效应权重初始计算值
        for r1 in range(region_num - 1):
            for r2 in range(r1 + 1, region_num):
                tmp1 = w12[:, :, r1, r2] / (np.sum(w12, (2, 3)) + 1e-9)
                rw12[:, :, r1, r2] = np.where(tmp1 > 1, 1, tmp1)  # 间接效应权重修正值
        np.save(rw12_path, rw12)
    else:
        rw12 = np.load(rw12_path)
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' (2/3)')
    riC = np.zeros((row_num, col_num,case_num))
    riC_by_precusors = np.zeros((region_num, region_num,row_num, col_num,case_num,species_num))
    
    for r1 in range(region_num - 1):  # ③间接效应修正权重：两两配对
        c = ctrs[r1,:, :4] - 1.
        dt=func(c[:, 0], c[:, 1],  c[:, 2], c[:, 3]) #(14,5)         
        for r2 in range(r1 + 1, region_num):
            temp_rcr=trW[:, :, :, r2, np.newaxis] * dt[np.newaxis, np.newaxis, ...]           
            rCr = np.sum(temp_rcr, 2)#(142, 178, case_num)
            weight1 = np.where(rCr * rC[:, :, r2,:] == 0, 0, np.abs(rCr / rC[:, :, r2,:]))
            weight = np.where(rCr * rC[:, :, r2,:] == 0, 0, np.abs(rC[:, :, r2,:] / rCr))
            weight = np.where(weight > weight1, weight1, weight)#(142, 178, case_num)
            riC += rw12[:, :, r1, r2, np.newaxis] * weight * iC
            riC_by_precusors[r1, r2,...,0]=rw12[:, :, r1, r2, np.newaxis] * weight* iC_by_precusors[...,0]
            riC_by_precusors[r1, r2,...,1]=rw12[:, :, r1, r2, np.newaxis] * weight* iC_by_precusors[...,1]
            riC_by_precusors[r1, r2,...,2]=rw12[:, :, r1, r2, np.newaxis] * weight* iC_by_precusors[...,2]
            riC_by_precusors[r1, r2,...,3]=rw12[:, :, r1, r2, np.newaxis] * weight* iC_by_precusors[...,3]
    
    fout = np.sum(rC, 2) + riC  #np.sum(rC, 2)对第三维度即所有区域进行加和，最后叠加①②③获得的间接效应riC贡献的ΔO3
    iout = fout.copy()
    rsm_temp = iout + bo3[...,np.newaxis]
    rsm=np.transpose(rsm_temp,(2,0,1))#shape=(case_num,row_num,col_num)
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' ' + (str(hour) if hour is not None else '')  + ' (3/3). Comsumes %.3f seconds' % (
    #         time.time() - start_time))
    
    rsm_regions=np.zeros((region_num,case_num,row_num,col_num))
    for rr in range(1, region_num + 1):
        rsm_regions[rr-1,...]=np.where((grid == rr)[np.newaxis,...], rsm, np.nan)  
          
    return rsm*unit_conversion_factor,bo3*unit_conversion_factor,rC_by_precusors*unit_conversion_factor,riC_by_precusors*unit_conversion_factor,rsm_regions*unit_conversion_factor

@timer_decorator
def get_grid_values_by_precusors_indirect(pollutantIndex, ctrs, month, day,hour=None,unit_conversion_factor=1):
    '''根据物种索引和减排情景，获取的网格浓度'''
    '''
    @param pollutantIndex: 物种索引
    @param ctrs: 减排情景, (region_num,5, species_num)
    '''
    start_time = time.time()    
    base_file=os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_D' + str(
        day) + '.data_species_base.npy') if hour is None else os.path.join(input_cmaq, base_case_name + "_" + year + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + '_H' + str(hour).zfill(2) + '.data_species_base.npy')   
    if not os.path.exists(base_file):
        print(f"File {base_file} does not exist")
    ## 2.读取基准O3浓度
    base = np.load(base_file)
    bo3 = base[:, :, pollutantIndex]
    case_num=ctrs.shape[-2] #shape=(region_num,case_num,species_num)
    ## 3.计算各单区域前体物对网格的直接贡献
    rC = np.zeros((row_num, col_num, region_num,case_num))  # 单区域贡献ΔO3
    rC_by_precusors = np.zeros((row_num, col_num, region_num,case_num,species_num))  # 单区域贡献ΔO3
    trW = np.zeros((row_num, col_num, 14, region_num))  # 单区域RSM曲面的14项系数
    
    func = lambda nox_emis, so2_emis, nh3_emis, vocs_emis: (          
            np.array([nox_emis**5, nox_emis**4, nox_emis**3, nox_emis**2, nox_emis, vocs_emis, vocs_emis**2, vocs_emis**3, nox_emis * vocs_emis, nox_emis * vocs_emis**3, nox_emis**5 * vocs_emis, nox_emis**2 * vocs_emis, so2_emis, nh3_emis])
        )#返回数组大小为(14,case_num)
    for rr in range(1, region_num + 1):
        c = ctrs[rr - 1,:, :4] - 1.
        dt=func(c[:, 0], c[:, 1],  c[:, 2], c[:, 3])       
        # rW[..., np.newaxis] * dt[np.newaxis, np.newaxis, ...]      
        rw_file=os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(day) + '.npy') if hour is None \
            else os.path.join(input_rsm, year + "_" + region_zero_cases[rr] + '.Weight_M' + str(month) + '_D' + str(day) + '_H' + str(hour).zfill(2)  + '.npy')
        rW = np.load(rw_file)        
        # 通过广播机制进行逐元素相乘：# A 的形状 (142, 178, 14) -> (142, 178, 14, 1)；# B 的形状 (14, 5) -> (1, 1, 14, 5)；# 输出 (142, 178, 14, 5)
        temp_rc = rW[..., np.newaxis] * dt[np.newaxis, np.newaxis, ...]#对第三维度进行求和，即对14项进行求和，得到(142, 178,14, case_num)
        rC_by_precusors[:, :, rr - 1,:,0] = temp_rc[:, :, 0,:]+temp_rc[:, :, 1,:]+temp_rc[:, :, 2,:]+temp_rc[:, :, 3,:]+temp_rc[:, :, 4,:]+temp_rc[:, :, 8,:]*0.5+temp_rc[:, :, 9,:]*(1.0/4.0)+temp_rc[:, :, 10,:]*(5.0/6.0)+temp_rc[:, :, 11,:]*(2.0/3.0)
        rC_by_precusors[:, :, rr - 1,:,1] = temp_rc[:, :, 12,:]
        rC_by_precusors[:, :, rr - 1,:,2] = temp_rc[:, :, 13,:]
        rC_by_precusors[:, :, rr - 1,:,3] = temp_rc[:, :, 5,:]+temp_rc[:, :, 6,:]+temp_rc[:, :, 7,:]+temp_rc[:, :, 8,:]*0.5+temp_rc[:, :, 9,:]*(3.0/4.0)+temp_rc[:, :, 10,:]*(1.0/6.0)+temp_rc[:, :, 11,:]*(1.0/3.0)        
        rC[:, :, rr - 1,:] = np.sum(temp_rc, 2)#对第三维度进行求和，即对14项进行求和，得到(142, 178, case_num)
        trW[:, :, :, rr - 1] = rW #(142, 178, 14,region_num,case_num)
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' (1/3)')

    ## 4.计算各区域前体物对网格的间接贡献
    tw_file=os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(day) + '.npy') if hour is None \
        else os.path.join(input_rsm, year + '_' + region_zero_cases[0] + '.Weight_M' + str(month) + '_D' + str(day) + '_H' + str(hour).zfill(2) + '.npy')
    tW = np.load(tw_file)#(142, 178, 14)
    iW = tW - np.sum(trW, 3)#对第三维度即region_num进行求和(142, 178, 14)
    iC = np.zeros((row_num, col_num,case_num))  # ①用全域和单区域的RSM得到各网格的间接效应贡献
    iC_by_precusors = np.zeros((row_num, col_num,case_num,species_num))  # ①用全域和单区域的RSM得到各网格的间接效应贡献
    for rr in range(1, region_num + 1):
        c = ctrs[rr - 1,:, :4] - 1.   
        dt=func(c[:, 0], c[:, 1],  c[:, 2], c[:, 3])   
        temp_ic=iW[..., np.newaxis] * dt[np.newaxis, np.newaxis, ...] #(142, 178, 14,5)
        iC_by_precusors[...,0] += np.where((grid == rr)[..., np.newaxis], \
           temp_ic[...,0,:]+temp_ic[...,1,:]+temp_ic[...,2,:]+temp_ic[...,3,:]+temp_ic[...,4,:]+temp_ic[...,8,:]*0.5+temp_ic[...,9,:]*(1.0/4.0)+temp_ic[...,10,:]*(5.0/6.0)+temp_ic[...,11,:]*(2.0/3.0), 0)        
        iC_by_precusors[...,1] +=np.where((grid == rr)[..., np.newaxis],  temp_ic[...,12,:], 0)
        iC_by_precusors[...,2] += np.where((grid == rr)[..., np.newaxis], temp_ic[...,13,:],0)
        iC_by_precusors[...,3] +=np.where((grid == rr)[..., np.newaxis], \
            temp_ic[...,5,:]+temp_ic[...,6,:]+temp_ic[...,7,:]+temp_ic[...,8,:]*0.5+temp_ic[...,9,:]*(3.0/4.0)+temp_ic[...,10,:]*(1.0/6.0)+temp_ic[...,11,:]*(1.0/3.0) ,0)
        #对第三维度进行求和，即对14项进行求和#np.where 的三个参数（条件、True 分支、False 分支）必须具有相同的形状。(grid == rr)结果需要进行广播扩展为(row_num, col_num,1)
        iC += np.where((grid == rr)[..., np.newaxis], np.sum(temp_ic, 2), 0)

    rw12_path = os.path.join(input_rsm, base_case_name + '_' + '.O3_new_ind_M' + str(month).zfill(2) + '_D' + str(
        day) + '.npy') if hour is None \
        else os.path.join(input_rsm, base_case_name + '_' + '.O3_new_ind_M' + str(month).zfill(2) + '_D' + str(day) + '_H' + str(hour).zfill(2) + '.npy')
    rw12 = np.zeros((row_num, col_num, region_num, region_num))  # ②间接效应修正权重：单区域削减贡献相关
    if not os.path.exists(rw12_path):
        zconc = np.zeros((row_num, col_num, region_num))  # 单区域前体物100%削减情景的O3浓度
        for rr in range(1, region_num + 1):
            full_control_file=os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(2) + '_D' + str(day) + '.data_species_zero.npy') if hour is None \
                else os.path.join(input_cmaq, region_zero_cases[rr] + '_' + year + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + '_H' + str(hour).zfill(2) + '.data_species_zero.npy')
            rzero = np.load(full_control_file)[:, :, pollutantIndex]
            zconc[:, :, rr - 1] = np.abs(bo3 - rzero)
        w12 = np.zeros((row_num, col_num, region_num, region_num))
        for r1 in range(region_num):
            for r2 in range(region_num):
                if r1==r2:
                    continue
                w12[:, :, r1, r2] = zconc[:, :, r1] * zconc[:, :, r2]  # 间接效应权重初始计算值
        for r1 in range(region_num):
            for r2 in range(region_num):
                if r1==r2:
                    continue
                tmp1 = w12[:, :, r1, r2] / (np.sum(w12, (2, 3)) + 1e-9)
                rw12[:, :, r1, r2] = np.where(tmp1 > 1, 1, tmp1)  # 间接效应权重修正值
        np.save(rw12_path, rw12)
    else:
        rw12 = np.load(rw12_path)
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' (2/3)')
    riC = np.zeros((row_num, col_num,case_num))
    riC_by_precusors = np.zeros((region_num, region_num,row_num, col_num,case_num,species_num))   
   
    for r1 in range(region_num):  # ③间接效应修正权重：两两配对
        c = ctrs[r1,:, :4] - 1.
        dt=func(c[:, 0], c[:, 1],  c[:, 2], c[:, 3]) #(14,5)         
        for r2 in range(region_num):
            if r1==r2:
                continue
            temp_rcr=trW[:, :, :, r2, np.newaxis] * dt[np.newaxis, np.newaxis, ...]           
            rCr_indirect = np.sum(temp_rcr, 2)
            weight1 = np.where(rCr_indirect * rC[:, :, r2,:] == 0, 0, np.abs(rCr_indirect / rC[:, :, r2,:]))
            weight = np.where(rCr_indirect * rC[:, :, r2,:] == 0, 0, np.abs(rC[:, :, r2,:] / rCr_indirect))
            weight = np.where(weight > weight1, weight1, weight)#(142, 178, case_num)
            riC += rw12[:, :, r1, r2, np.newaxis] * weight * iC
            riC_by_precusors[r1, r2,...,0]=rw12[:, :, r1, r2, np.newaxis] * weight* iC_by_precusors[...,0]
            riC_by_precusors[r1, r2,...,1]=rw12[:, :, r1, r2, np.newaxis] * weight* iC_by_precusors[...,1]
            riC_by_precusors[r1, r2,...,2]=rw12[:, :, r1, r2, np.newaxis] * weight* iC_by_precusors[...,2]
            riC_by_precusors[r1, r2,...,3]=rw12[:, :, r1, r2, np.newaxis] * weight* iC_by_precusors[...,3]   
    
    fout = np.sum(rC, 2) + riC  #np.sum(rC, 2)对第三维度即所有区域进行加和，最后叠加①②③获得的间接效应riC贡献的ΔO3
    iout = fout.copy()
    rsm_temp = iout + bo3[...,np.newaxis]
    rsm=np.transpose(rsm_temp,(2,0,1))#shape=(case_num,row_num,col_num)
    # print(year + ' - ' + str(month) + ' - ' + str(day) + ' ' + (str(hour) if hour is not None else '')  + ' (3/3). Comsumes %.3f seconds' % (
    #         time.time() - start_time))
    
    rsm_regions=np.zeros((region_num,case_num,row_num,col_num))
    for rr in range(1, region_num + 1):
        rsm_regions[rr-1,...]=np.where((grid == rr)[np.newaxis,...], rsm, np.nan)  
          
    return rsm*unit_conversion_factor,bo3*unit_conversion_factor,rC_by_precusors*unit_conversion_factor,riC_by_precusors*unit_conversion_factor,rsm_regions*unit_conversion_factor

def get_region_precusor_contribution(day,target_region_idx,local_by_precusors,indirect_by_precusors,df_cities_sector_weights=None, contribution_type='total',case_names=None):
    '''
    @description: 获取各区域前体物对目标区域的贡献
    @param {day}:选定天,从1开始
    @param {target_region_idx}:目标区域索引，即受体区域索引,从0开始
    @param {local_by_precusors}:单区域贡献ΔO3,shape=(region_num,grid_row_num, grid_col_num,case_num,species_num);通过get_grid_values_by_precusors()函数获取
    @param {indirect_by_precusors}:间接效应贡献ΔO3，shape=(region_num,region_num,grid_row_num, grid_col_num,case_num,species_num)通过get_grid_values_by_precusors()函数获取
    @param {df_cities_sector_weights}:城市分部门权重系数，数据类型为DataFrame，包含列time_step,region,pollutant,sector,sector_contribution_weight
    @param {contribution_type}:total：不区分直接和间接贡献，将local+indirect合并到一起。local:只统计local的贡献，不计算indirect贡献；independent:分开统计indirect的贡献和local贡献
    @return {df_cities}:返回DataFrame，包含列region,sector,pollutant,contribution,target_region,case,type
    '''
    rows=[] 
    regions=region_zero_cases[1:]
    target_region_name=regions[target_region_idx]
    target_region_id=target_region_idx+1   
    pollutants = ['NOx', 'SO2', 'NH3', 'VOC'] 
    def append_row(rows,local, indirect,target_region_name, source_name, c_idx, s_idx,species_name,contribution_type,day, sector_weight=1,sector_name="All"):
        case_name=case_names[c_idx] if case_names is not None else f'case {c_idx+1}'
        if contribution_type=='total':
            # total=np.mean(local+indirect,axis=(0,1))
            total=local+indirect
            mean_contribution=np.nanmean(np.where((grid == target_region_id),total[...,c_idx,s_idx],np.nan))
            rows.append([day,source_name,sector_name,species_name,mean_contribution*sector_weight,target_region_name,case_name,'total'])
            # rows.append([day,source_name,sector_name,species_name,total[c_idx,s_idx]*sector_weight,target_region_name,f'case {c_idx+1}','total'])
        elif contribution_type=='local':      
            mean_local_contribution=np.nanmean(np.where((grid == target_region_id),local[...,c_idx,s_idx],np.nan)) 
            # mean_indirect_contribution=np.nanmean(np.where((grid == target_region_id),indirect[...,c_idx,s_idx],np.nan))             
            rows.append([day,source_name,sector_name,species_name,mean_local_contribution*sector_weight,target_region_name,case_name,'local'])     
            # rows.append([day,source_name,sector_name,species_name,mean_indirect_contribution*sector_weight,target_region_name,f'case {c_idx+1}','indirect'])
        else:      
            mean_local_contribution=np.nanmean(np.where((grid == target_region_id),local[...,c_idx,s_idx],np.nan)) 
            mean_indirect_contribution=np.nanmean(np.where((grid == target_region_id),indirect[...,c_idx,s_idx],np.nan))             
            rows.append([day,source_name,sector_name,species_name,mean_local_contribution*sector_weight,target_region_name,case_name,'local'])     
            rows.append([day,source_name,sector_name,species_name,mean_indirect_contribution*sector_weight,target_region_name,case_name,'indirect'])
            # rows.append([day,source_name,sector_name,species_name,np.mean(local,axis=(0,1))[c_idx,s_idx]*sector_weight,target_region_name,f'case {c_idx+1}','local'])     
            # rows.append([day,source_name,sector_name,species_name,np.mean(indirect,axis=(0,1))[c_idx,s_idx]*sector_weight,target_region_name,f'case {c_idx+1}','indirect'])
    
    for source_idx,source_name in enumerate(regions):                  
        # local=np.where((grid == target_region_id)[..., np.newaxis, np.newaxis], local_by_precusors[:,:,source_idx,:,:], np.nan)*(-1) #(142, 178, 5, 4) ；-1表示将削减值转为贡献值,如-1表示浓度减少了1，即贡献了1
        # indirect=np.where((grid == target_region_id)[..., np.newaxis, np.newaxis],indirect_by_precusors[source_idx,target_region_idx,...],np.nan)*(-1) #(142, 178, 5, 4) -1表示将削减值转为贡献值     
        local=local_by_precusors[:,:,source_idx,:,:]*(-1) # -1表示将削减值转为贡献值,如-1表示浓度减少了1，即贡献了1    
        indirect=np.sum(indirect_by_precusors[source_idx,...],axis=(0))*(-1)# -1表示将削减值转为贡献值,如-1表示浓度减少了1，即贡献了1  
        case_num,species_num=local.shape[-2:]         
        for c_idx in range(case_num):
            for s_idx,species_name in zip(range(species_num),pollutants): 
                if df_cities_sector_weights is not None:
                    filtered_df = df_cities_sector_weights[(df_cities_sector_weights[f"time_step"] ==f"D{day}") 
                                                                & (df_cities_sector_weights['region'] ==source_name)                                                                        
                                                                & (df_cities_sector_weights['pollutant'] ==species_name)]
                    if filtered_df.empty:
                        append_row(rows,local, indirect,target_region_name, source_name, c_idx, s_idx,species_name, contribution_type,sector_weight=1,sector_name="All",day=f"D{day}")                         
                    else:                               
                        # 使用apply()方法遍历DataFrame filtered_df.apply(lambda row: print(row['A'], row['B']), axis=1)
                        for index, row in filtered_df.iterrows():
                            sector_name=row['sector']
                            sector_weight=row['sector_contribution_weight']      
                            append_row(rows,local, indirect,target_region_name, source_name, c_idx, s_idx,species_name, contribution_type,sector_weight=sector_weight,sector_name=sector_name,day=f"D{day}")
                else:
                    append_row(rows,local, indirect,target_region_name, source_name, c_idx, s_idx,species_name, contribution_type,sector_weight=1,sector_name="All",day=f"D{day}")   
                                              
    df_cities=pd.DataFrame(rows,columns=['day','region', 'sector', 'pollutant', 'contribution','receptor_region','case','type'])  
    return df_cities

def get_sector_weight(days):
    from b_input_data_helper import get_sector_concentration_data,all_aconc_files,boundary_json_file,get_oos_input_data
    dict_cmaq_data,dict_sectors=get_sector_concentration_data()
    if dict_cmaq_data is None:
        return None
    #base:(time_step,layer,grid_rows,grid_cols)
    oos_cmaq_data, region_cell, control_matrix,base_case_cmaq_data,case_ids=get_oos_input_data()
    from esil.earth_helper import get_boundary_mask_data
    from esil.rsm_helper.model_property import model_attribute    
    # from esil.rsm_helper.factor import FactorInfo as factor_info
    mp=model_attribute(all_aconc_files[0])
    model_lons, model_lats=mp.get_xy_coordinates(show_lonlat=True)      
    # model_lons, model_lats=np.meshgrid(x_coord,y_coord)
    dict_masks,_=get_boundary_mask_data(boundary_json_file,model_lats,model_lons,field_name='adcode',replaceFalseWithNan=True,pkl_file_name=f"PRD_Cities_{model_lons.shape[0]}{model_lons.shape[1]}.pkl")
    prd_cities=['广州市','深圳市','佛山市','东莞市','惠州市','江门市','珠海市','肇庆市','中山市','珠三角周边区域']
    prd_cities_en=region_zero_cases[1:]
    prd_cites_mapping=dict(zip(prd_cities,prd_cities_en))
    rows=[]
    for day in tqdm(days):      #for name,mask in dict_masks.items(): 
        ts_idx=day-1        
        for species, cmaq_data in dict_cmaq_data.items():
            sectors=dict_sectors[species]
            sector_contributions=np.zeros((len(sectors),)+base_case_cmaq_data.shape[-2:])                                    
            for sector_idx,sector_name in enumerate(sectors):
                #1.1.统计某区域、某部门对某前体物浓度贡献的总量:  
                sector_contributions[sector_idx,:,:]= base_case_cmaq_data[ts_idx,0,:,:]-cmaq_data[sector_idx,ts_idx, :, :]    
            for sector_idx,sector_name in enumerate(sectors):
                for name,mask in dict_masks.items():
                    if name not in prd_cities:
                        continue
                    city_sector_weight=np.nansum(sector_contributions[sector_idx,:,:]*mask)/ np.nansum(np.sum(sector_contributions,axis=0)*mask)
                    rows.append([f"D{ts_idx+1}",prd_cites_mapping[name],species,sector_name,city_sector_weight])
    df_cities_sector_contribution=pd.DataFrame(rows,columns=['time_step', 'region', 'pollutant', 'sector','sector_contribution_weight'])               
    return df_cities_sector_contribution  

def get_summary_metrics(rsm_values,cmaq_values):       
    oos_case_num = rsm_values.shape[0]
    #RSM-VAT的metrics是求每个case的metrics的平均值，然后从所有验证case中取最大最小值，并不是从所有case的网格中取最大最小值
    from create_rsm_struct.statistic_helper import Metric
    dict_oos_metrics_all = {}
    dict_oos_metrics={}
    for c_index in range(oos_case_num):    
        metric= Metric(rsm_values[c_index].flatten(), cmaq_values[c_index].flatten())
        dict_oos_metrics_all[c_index] = metric.description()
        dict_oos_one_case= metric.description(include_min_max=False)
        for key, value in dict_oos_one_case.items():
            if key not in dict_oos_metrics:
                dict_oos_metrics[key] = []
            dict_oos_metrics[key].append(value)  
    summary_table=[]    
    for key, value in dict_oos_metrics.items():
        summary_table.append([key,np.mean(value),np.std(value),np.min(value),np.max(value)])
    df=pd.DataFrame(summary_table,columns=['Metric','Mean','Std','Min','Max'])
    return df,dict_oos_metrics_all 