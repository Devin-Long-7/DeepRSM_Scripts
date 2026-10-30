import numpy as np
import torch
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.utils.data
import os
from create_rsm_struct.sentiment_ESIL import Sentiment
from create_rsm_struct.PM25ResNet import PM25ResNet
import sys;
from tqdm.auto import tqdm
from esil.date_helper import get_hour_of_month
from b_input_data_helper import year,month,output_npy_dir,output_rsm_weights_dir,trained_model_file,target_pollutant,aconc_cases,whole_region_full_control_case_name,base_case_name,receptor_file_txt,read_receptor_file_txt,config_file
print(f"config_file:{config_file}")
# 使用列表推导式剔除包含特定字符串的元素
# cases_without_base = [name for name in aconc_cases if 'base' not in name]
# cases_without_base.insert(0, cases_without_base.pop(cases_without_base.index(whole_region_full_control_case_name)))#全区域同步变化的情景放在第一个
_,dict_receptor=read_receptor_file_txt(receptor_file_txt)
cases_without_base=[whole_region_full_control_case_name]+list(dict_receptor.values())
script_file=os.path.abspath(__file__)
sys.argv = [f'{script_file}', output_rsm_weights_dir, output_npy_dir, base_case_name,",".join(cases_without_base),
            target_pollutant,f'{year}',f'{month}',",".join([str(x) for x in range(1, 31)]),trained_model_file,",".join([str(x) for x in range(0, 25)])]

# 编辑输入信息：----------------------------------------------------------------------------------------
OutputPath = sys.argv[1]   #'E:/DeepRSM_PRD_CY/PRD/Project/O3/out/'
InputPath = sys.argv[2]  #'E:/DeepRSM_PRD_CY/PRD/Project/O3/pydata/'
BaseFileName = sys.argv[3]
RegionsFileName = sys.argv[4]
RegionsFileName = RegionsFileName.strip("'[").strip("]'").split(",") #让从c#中读取到的文本内容转换为后面这种列表['PRD', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9']
RegionsFileName=[x.strip() for x in RegionsFileName]

args_Target = sys.argv[5] #PM
TestYear = sys.argv[6]
TestMonths = sys.argv[7]
TestMonths = TestMonths.strip("'[").strip("]'").split(",")# //将c#中传入的字符串参数，转化为python中的列表
TestDays = sys.argv[8].strip("'[").strip("]'").split(",") #sys.argv[8]  # '1-31'
lstTestDays = TestDays
ModelPath = sys.argv[9]  # 'E:/DeepRSM_PRD_CY/models/train_cn27_cn9bj_cn9cy.pth'  # train_cn9bj_cn9xa_cn9cy.pth | train_cn27_cn9bj_cn9cy.pth | train_cn27_cn9bj_cn9xa.pth | train_cn27_cn9xa_cn9cy.pth

hours=sys.argv[10].strip("'[").strip("]'").split(",") # '32'  # '1-31', '32'
hours=[int(x) for x in hours]
# date_type='hourly' 
date_type='daily' 
args_j = 4  # number of workers 线程数？

# 固定配置---------------------------------------------------------------------------------------------
args_c = 128  # number of channel of network 128 第一个卷积层将输入的36通道数据经卷积计算转为128通道
args_l = 8  # number of layers 8
# args_mb = 8  # input batch size for training (default: 128)')
args_Net = 'resnet'
# CudaAvailable = torch.cuda.is_available() # 使用 CUDA 会报错 lijinying 2021.9.26 
CudaAvailable = False    # 强制不使用CUDA
#----------------------------------------------------------------------------------------------------

def ReplaceBlank(inipath):
    path = inipath.replace("*"," ")
    return  path
OutputPath = ReplaceBlank(OutputPath) #还原路径中的空格
InputPath = ReplaceBlank(InputPath)
ModelPath = ReplaceBlank(ModelPath)
#lstTestDays = read_testday(TestDays)

###### Load Data ######
test_loaders = []
for month in TestMonths:
    with tqdm(total=len(lstTestDays) if date_type != 'hourly' else len(lstTestDays)*24, desc=f'Loading {month}',leave=True) as pbar:
        for day in lstTestDays:               
            if date_type == 'hourly':
                for hour in hours:
                    d_test_allRegion = Sentiment(BaseFileName, RegionsFileName, month, day, 'pm', InputPath, TestYear,
                                            mode='calculating',hour=hour)
                    tensor_docs_allRegion = torch.Tensor(d_test_allRegion.data_set)
                    testset = torch.utils.data.TensorDataset(tensor_docs_allRegion)
                    test_loader = torch.utils.data.DataLoader(testset, batch_size=1, shuffle=False, num_workers=args_j)
                    test_loaders.append(test_loader)
                    pbar.set_description(f'Finished loading {TestYear}-{month}-{day} {hour}')
                    pbar.update(1)
            else:
                d_test_allRegion = Sentiment(BaseFileName, RegionsFileName, month, day, 'pm', InputPath, TestYear,
                                            mode='calculating',hour=None)
                tensor_docs_allRegion = torch.Tensor(d_test_allRegion.data_set)
                testset = torch.utils.data.TensorDataset(tensor_docs_allRegion)
                test_loader = torch.utils.data.DataLoader(testset, batch_size=1, shuffle=False, num_workers=args_j)
                test_loaders.append(test_loader)
                pbar.set_description(f'Finished loading {TestYear}-{month}-{day}')
                pbar.update(1)

###### Model ######
if CudaAvailable:
    model = PM25ResNet(num_channel=args_c, num_block=args_l).cuda()
    cudnn.benchmark = True
else:
    model = PM25ResNet(num_channel=args_c, num_block=args_l)


def performance(out, m_index, d_index, h_index=None):
    try:
        for r_index in range(len(RegionsFileName)):
            Weight = out[r_index, :, :, :]
            save_full_path=OutputPath #
            if not os.path.exists(save_full_path):
                os.makedirs(save_full_path)
            save_file=os.path.join(save_full_path , TestYear + '_' + RegionsFileName[r_index] + '.'+ 'Weight_M' + str(TestMonths[m_index]) + '_D' + str(lstTestDays[d_index]) + '.npy') if h_index is None \
                else os.path.join(save_full_path , TestYear + '_' + RegionsFileName[r_index] + '.'+ 'Weight_M' + str(TestMonths[m_index]) + '_D' + str(lstTestDays[d_index]) + '_H' + str(h_index).zfill(2) + '.npy')
            np.save(save_file, Weight)
            print(f'{save_file} saved')
    except Exception as e:
        print(f'Error: {e}')
    return

def test(m_index, d_index, h_index=None):   
    try:
        model.eval()
        out_cat = torch.Tensor()    
        data_index = m_index * len(lstTestDays) + d_index*len(hours) + h_index if h_index is not None else m_index * len(lstTestDays) + d_index
        for batch_idx, data in enumerate(test_loaders[data_index]):
            if CudaAvailable:
                data = data.cuda()
            try:
                output = model(data[0])
            except:
                # 将模型移动到 CUDA 设备上
                model.to('cuda:0')
                # 将数据移动到 CUDA 设备上
                data = [d.to('cuda:0') for d in data]
                # 然后进行模型推理
                output = model(data[0])
                
            if out_cat.shape[0] == 0:
                out_cat = output.data
            else:
                out_cat = torch.cat((out_cat, output.data), 0)
        out = out_cat.view(len(RegionsFileName), out_cat.shape[1], out_cat.shape[2], out_cat.shape[3]).cpu().numpy().transpose((0, 2, 3, 1))
        calculateIndirectWeight(m_index, d_index,h_index)
    except Exception as e:
        print(f'Error: {e}')
    print('Calculation complete.')
    return performance(out, m_index, d_index,h_index)

#计算间接效应权重系数
def calculateIndirectWeight(m_index, d_index, h_index=None):
    rw12_path =os.path.join( OutputPath, TestYear + '_' + BaseFileName + '.' + args_Target + 'ind_M' + str(TestMonths[m_index]).zfill(2) + '_D' + str(lstTestDays[d_index]) + '.npy')  if h_index is None \
        else os.path.join( OutputPath, TestYear + '_' + BaseFileName + '.' + args_Target + 'ind_M' + str(TestMonths[m_index]).zfill(2) + '_D' + str(lstTestDays[d_index]) + '_H' + str(h_index).zfill(2) + '.npy')
   
    if not os.path.exists(rw12_path):
        ## 2.读取基准浓度 ['HNO3', 'H2O2', 'N2O5', 'NO2', 'FORM', 'HONO','NO', 'O3_US', 'SO2', 'NH3', 'OH', 'ISOP', 'TERP','ASO4IJ', 'ANO3IJ', 'ANH4IJ', 'ASOCIJ', 'PM25_TOT']
        label = '_' + TestYear + '_' + str(TestMonths[m_index]).zfill(2) + '_D' + str(lstTestDays[d_index]) + '.' if h_index is None \
            else '_' + TestYear + '_' + str(TestMonths[m_index]).zfill(2) + '_' + str(lstTestDays[d_index]).zfill(2) + '_H' + str(h_index).zfill(2) + '.'
        base_path =os.path.join(InputPath, BaseFileName + label + 'data_species_base.npy')#将文件后缀与映射文件相对应
        base = np.load(base_path)
        pollutantIndex = 7#O3索引
        if ('PM' in args_Target):
            pollutantIndex = 17 #PM25_TOT索引
        bConcentration = base[:, :, pollutantIndex]#读取基准浓度
        row_num = base.shape[0]
        col_num = base.shape[1]
        region_num = len(RegionsFileName) - 1
        rw12 = np.zeros((row_num, col_num, region_num, region_num))  # ②间接效应修正权重：单区域削减贡献相关
        zconc = np.zeros((row_num, col_num, region_num))  # 单区域前体物100%削减情景的O3浓度
        for rr in range(1, region_num + 1):
            rzero = np.load(os.path.join(InputPath,  RegionsFileName[rr] + label + 'data_species_zero.npy'))[:, :, pollutantIndex] #'Ctrl_R' + str(rr)
            zconc[:, :, rr - 1] = np.abs(bConcentration - rzero)
        w12 = np.zeros((row_num, col_num, region_num, region_num))
        for r1 in range(region_num - 1):
            for r2 in range(r1 + 1, region_num):
                w12[:, :, r1, r2] = zconc[:, :, r1] * zconc[:, :, r2]  # 间接效应权重初始计算值
        for r1 in range(region_num - 1):
            for r2 in range(r1 + 1, region_num):
                tmp1 = w12[:, :, r1, r2] / (np.sum(w12, (2, 3)) + 1e-9)
                rw12[:, :, r1, r2] = np.where(tmp1 > 1, 1, tmp1)  # 间接效应权重修正值
        np.save(rw12_path, rw12)

if __name__ == '__main__':
    if not os.path.exists(OutputPath):
        os.makedirs(OutputPath)
    if ModelPath != '':
        if CudaAvailable:
            model_Value=torch.load(ModelPath)
        else:
            model_Value=torch.load(ModelPath, map_location='cpu') #清华提供的训练结果由GPU得到，为兼容无独显的本机测试
        for keys in model_Value.keys():         # 判断 model_Value 是否为多显卡训练得到
            if 'module' in keys:
                model = torch.nn.DataParallel(model)  # 运行时带有显卡并行
                break
        model.load_state_dict(model_Value)
    # for m_index in range(len(TestMonths)):
    #     for d_index in range(len(lstTestDays)):
    #         test(m_index, d_index)
    #处理天数据
    for m_index in range(len(TestMonths)):
        with tqdm(total=len(lstTestDays), desc=f'Calculating {TestYear}-{TestMonths[m_index]}',leave=True) as pbar:
            for d_index in range(len(lstTestDays)):              
                test(m_index, d_index)
                pbar.set_description(f'Finished calculating {TestYear}-{TestMonths[m_index]}-{lstTestDays[d_index]}')
                pbar.update(1)

    # #处理小时数据
    # for m_index in range(len(TestMonths)):
    #     with tqdm(total=len(lstTestDays)*len(hours), desc=f'Calculating {TestYear}-{TestMonths[m_index]}',leave=True) as pbar:
    #         for d_index in range(len(lstTestDays)):
    #             for h_index in hours:
    #                 test(m_index, d_index, h_index)
    #                 pbar.set_description(f'Finished calculating {TestYear}-{TestMonths[m_index]}-{lstTestDays[d_index]} {h_index}')
    #                 pbar.update(1)

