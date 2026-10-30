import numpy as np
import os
import netCDF4 as nc
import time
import pandas as pd
from tqdm.auto import tqdm
from esil.date_helper import timer_decorator
from esil.map_helper import get_multiple_data,show_multi_maps,plot_cmaq_concentration_maps,show_delta_maps,show_maps
from esil.scatter_plot_helper import draw_density_plot
from esil.scatter_plot_helper import draw_multiple_density_plots,draw_density_plot_via_hist2d,draw_density_plot
from esil.panelayout_helper import get_layout_col_row
from esil.rsm_helper.model_property import model_attribute
import cmaps
import matplotlib.pyplot as plt
from esil.date_helper import get_hour_of_month
from datetime import datetime
from esil.map_helper import get_multiple_data,show_maps
from esil.rsm_helper.model_property import model_attribute
from b_input_data_helper import aconc_dir,aconc_file_prefix,all_aconc_files,boundary_file,output_dir,output_oos_dir,unit
from esil.earth_helper import get_all_masks,get_boundary_mask_data
import cmaps
cmap_conc=cmaps.WhiteBlueGreenYellowRed #cmaps.WhBlGrYeRe
cmap_delta=cmaps.ViBlGrWhYeOrRe#coolwarm
from b_input_data_helper import boundary_json_file

# from esil.scatter_plot_helper import plot_stack_bar as draw_stack_bar
############################iRSM的PM反算脚本##############################
# 编辑输入信息：------------------------------------------------------------
import sys
sys.path.append(r"/DeepLearning/mnt/Devin/01_deeprsm/03_create_rsm_scripts")
from b_input_data_helper import year,month,output_npy_dir,output_rsm_weights_dir,output_dir,output_oos_dir,target_pollutant,grid_path,species_num,\
    target_pollutant_idx,boundary_file,whole_region_full_control_case_name,base_case_name,receptor_file_txt,config_file,species_in_cmaq,project_name,unit
from b_input_data_helper import read_receptor_file_txt,get_oos_input_data
from e_rsm_helper import get_summary_metrics,GetOzoneGridValues,get_sector_weight,get_grid_values_by_precusors,get_region_precusor_contribution,get_grid_values,get_grid_values_by_precusors_indirect,get_ozone_grid_values
print(f"config_file:{config_file}")
# 使用列表推导式剔除包含特定字符串的元素
# region_zero_cases = [name for name in aconc_cases if 'base' not in name]
# region_zero_cases.insert(0, region_zero_cases.pop(region_zero_cases.index(whole_region_full_control_case_name)))
# base_case_name =base_case_name# next((name for name  in aconc_cases if 'base' in name), None)
_,dict_receptor=read_receptor_file_txt(receptor_file_txt)
region_zero_cases=[whole_region_full_control_case_name]+list(dict_receptor.values())
input_cmaq = output_npy_dir
input_rsm =output_rsm_weights_dir  
result_root = output_dir
#emissionCtrl = "[0.735567622,0.397729316,0.472624005,0.712778107,1.246305112,0.634373933,1.485183074,0.83218075,1.329670904,0.980588103,1.471367558,0.36977651,0.382697791,1.128701855,0.124860898,1.445407517,1.165567574,0.847978323,0.633747813,1.429583531,0.108826282,0.503911262,0.541970926,0.121063119]".strip("[").strip("]").split(",")
emissionCtrl = "[0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6,0.6]".strip("[").strip("]").split(",")
# targetPollutant = "PM"
targetPollutant = target_pollutant 
isContainPrimaryPM = 'true'
isContainPrimaryPM = 'false'
year = str(year)
months = [str(month)]
days = [str(x) for x in range(1, 31)]#['1','2','3', '32'] 

# base_name = "BaseCase"
# cases_without_base = "[PRD, DG, FS, GZ, HZ, JM, OTH, SZ, ZH, ZQ, ZS]".strip(
#     "[").strip(
#     "]").split(",")
region_zero_cases=[x.strip() for x in region_zero_cases]
# region_zero_cases=['PRD','GZ','SZ','FS','DG','HZ','JM','ZH','ZQ','ZS','OTH']
# hours=[x for x in range(0, 25)]
hours=[x for x in range(24, 25)]
# hours=[int(x) for x in hours]
# -----------------------------------------------------------------------
unit_conversion_factor=48/24.45 if species_in_cmaq[target_pollutant_idx]=="O3_US" else 1
if not os.path.exists(result_root):
    os.makedirs(result_root)
grid = np.load(grid_path)
row_num = grid.shape[0]
col_num = grid.shape[1]
region_num = len(region_zero_cases) - 1
monthCount = len(months)
dayCount = len(days)
print("初始化完成，开始读取数据...")
import os
from esil.rsm_helper.ekma_curve import plot_multiple_ekma_curves
from esil.map_helper import get_multiple_data,show_maps 
upper_value=2 #当PR值超过1.5时，认为是明显的NOx控制区，标注为*号
def plot_ekma_curve(days=[6,13,14,16,19],show_city_emka=True):     
    xx = np.arange(0, 1.51, 0.25)
    yy = np.arange(0, 1.51, 0.25)
    zz = np.zeros((len(xx), len(yy)))   
    x_p_idx,y_p_idx = 0,3    
    x_name = "NOx"
    y_name ="VOC"
    region_row, region_col=grid.shape  
    # project_name=os.path.basename(output_dir)
    save_path=os.path.join(output_oos_dir, f'ekma_curve')
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    case_num=len(xx)*len(yy)
    emis_matrix=np.ones((region_num,case_num, species_num))
    ctrl = np.ones((region_num, species_num)) 
    c_index=0    
    if show_city_emka:
        from esil.earth_helper import get_boundary_mask_data
        from esil.rsm_helper.model_property import model_attribute
        from b_input_data_helper import all_aconc_files,boundary_json_file          
        mp=model_attribute(all_aconc_files[0])
        model_lons, model_lats=mp.get_xy_coordinates(show_lonlat=True)    
        # model_lons, model_lats=np.meshgrid(x_coord,y_coord)
        dict_masks,_=get_boundary_mask_data(boundary_json_file,model_lats,model_lons,field_name='adcode',replaceFalseWithNan=True,pkl_file_name=f"PRD_Cities_{row_num}_{col_num}.pkl")    
    for j in range(len(yy)):
        for i in range(len(xx)):        
            ctrl[:, x_p_idx] = xx[i]
            ctrl[:, y_p_idx] = yy[j]
            emis_matrix[:,c_index,:]=ctrl.copy()
            c_index+=1  
    dict_data={}  
    for day in tqdm(days):  
        savefile=os.path.join(save_path, f'emka_curve_Whole_domain_Day{day}.png')  
        rsm_values=None
        for c_index in range(case_num):
            ctr=emis_matrix[:,c_index,:]  
            if rsm_values is None:
                rsm_values=np.zeros((case_num,region_row,region_col))
            rsm,bo3= GetOzoneGridValues(target_pollutant_idx, ctr, month, day, hour=None)    
            rsm_values[c_index,:,:]=rsm    
        c_index=0
        zz = np.zeros((len(xx), len(yy)))        
        for i in range(len(xx)):
            for j in range(len(yy)):                
                zz[i, j] =  np.mean(rsm_values[c_index,:,:])  
                c_index+=1
        dict_data[f'Day_{day}']=[xx,yy,zz.copy()]    
        if len(dict_data)%6==0:            
            fig=plot_multiple_ekma_curves(dict_data,x_title="NOx",y_title="VOC",legend_title="O3",value_format=".1f",\
                                          showplot=False)
            fig.savefig(savefile,dpi=300,bbox_inches='tight')            
            dict_data={}  
        if show_city_emka:   
            plot_city_ekma_curve(xx,yy,rsm_values,day,dict_masks,model_lats=model_lats,model_lons=model_lons)    
    if len(dict_data)>0:        
        fig=plot_multiple_ekma_curves(dict_data,x_title="NOx",y_title="VOC",legend_title="O3",value_format=".1f",\
                                      showplot=False)
        fig.savefig(savefile,dpi=300,bbox_inches='tight')   
    print("done")                        

def plot_city_ekma_curve(xx,yy,rsm_values,day,dict_masks,model_lats=None,model_lons=None):    
    
    ts_idx=day-1
    dict_data,dict_map_data={},{}
    prd_cities=['广州市','深圳市','佛山市','东莞市','惠州市','江门市','珠海市','肇庆市','中山市']
    city_abbr={'广州市':'GZ','深圳市':'SZ','佛山市':'FS','东莞市':'DG',
               '惠州市':'HZ','江门市':'JM','珠海市':'ZH','肇庆市':'ZQ','中山市':'ZS'}

    save_path=os.path.join(output_oos_dir, f'ekma_curve')
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    for name,mask in dict_masks.items(): 
        if name not in prd_cities:
            continue    
        zz = np.zeros((len(xx), len(yy)))  
        c_index=0      
        for i in range(len(xx)):
            for j in range(len(yy)):                
                zz[i, j] =  np.nanmean(rsm_values[c_index,:,:]*mask)  
                c_index+=1
        abbr = city_abbr[name]
        dict_data[f'Day_{day}_{abbr}']=[xx,yy,zz.copy()]
        if ts_idx==0 and model_lats is not None:
            get_multiple_data(dict_map_data,dataset_name=f'Day_{day}_{abbr}',variable_name="O3",grid_x=model_lons, grid_y=model_lats,grid_concentration=rsm_values[32,:,:]*mask)
        if len(dict_data)%9==0:            
            fig=plot_multiple_ekma_curves(dict_data,x_title="NOx",y_title="VOC",legend_title="O3",value_format=".1f",\
                                          font_name='SimHei',showplot=False)
            savefile=os.path.join(save_path, f'{project_name}_ekma_curve_Day{day}_city_{name}.png') 
            fig.savefig(savefile,dpi=300,bbox_inches='tight')
            dict_data={}      
    if len(dict_data)>0:  
        savefile=os.path.join(save_path, f'{project_name}_ekma_curve_Day{day}_city_{name}.png')       
        fig=plot_multiple_ekma_curves(dict_data,x_title="NOx",y_title="VOC",legend_title="O3",value_format=".1f",\
                                      font_name='SimHei',showplot=False)
        fig.savefig(savefile,dpi=300,bbox_inches='tight')
    if len(dict_map_data)>0:
        import cmaps
        fig=show_maps(dict_map_data,unit=unit,cmap=cmaps.WhiteBlueGreenYellowRed,boundary_file=boundary_file,show_plot=False,show_minmax=True,show_original_grid=True,show_lonlat=True,show_dependenct_colorbar=True,
                            value_range=(None,None),value_format='.1f',font_name='SimHei') 
        file_name=os.path.join(save_path, f'{project_name}_Day{day}_concentration_city_map.png')
        fig.savefig(file_name,bbox_inches='tight',dpi=300)
    print(f"Day {day} city contour plot done")
      
#region计算PR值和VNR


### 1.5 计算PR值和VNr值
def get_o3_pr_value(pollutant_index, target_region_mask, target_region_idx, month, day, hour=None, pr_type="local"):
    '''
    @description: 计算O3的PR值(Peak Ratio)
        PR定义为: VOCs保持基准排放不变、只改变NOx排放率、O3浓度取到最大值时所对应的NOx排放率
        PR < 1 → VOC控制区; PR > 1 → NOx控制区
        参考Xingjia博士论文4.2节 / Dingdian博士论文3.1.1节式(3-1)
    @param {pollutant_index}: int, 目标污染物索引
    @param {target_region_mask}: np.array, 目标区域掩码
    @param {target_region_idx}: int, 目标区域索引
    @param {month}: int, 月份
    @param {day}: int, 日期
    @param {hour}: int, 小时
    @param {pr_type}: str, pr计算类型，local:只改变本地NOx, whole_region:全区域NOx同时变化
    @return {pr_value}: PR值 (NOx排放率)
    @return {o3_max_value}: O3最大值
    '''
    from scipy.optimize import minimize_scalar

    def objective(nox_emis):
        emis = np.ones((region_num, 1, species_num))
        if pr_type == "local":
            emis[target_region_idx, :, 0] = nox_emis
        elif pr_type == "whole_region":
            emis[:, :, 0] = nox_emis
        else:
            raise ValueError(f"未定义的pr_type: {pr_type}")
        rsm, bo3 = get_grid_values(pollutant_index, emis, month, day, hour=hour)
        region_avg_conc = np.nanmean(rsm * target_region_mask)
        return -region_avg_conc

    nox_lo, nox_hi = 0.01, upper_value
    result = minimize_scalar(objective, bounds=(nox_lo, nox_hi), method='bounded',
                             options={'xatol': 1e-4, 'maxiter': 200})
    pr_value = result.x
    o3_max_value = -result.fun
    if pr_value <= nox_lo + 0.02 or pr_value >= nox_hi - 0.02:
        print(f"Warning: PR={pr_value:.3f} hit boundary [{nox_lo}, {nox_hi}], "
              f"Day={day}, Region={target_region_idx}. True PR may be outside range.")
    return pr_value, o3_max_value


def get_o3_vnr_value(pollutant_index, target_region_mask, target_region_idx, month, day, hour=None, pr_type="local", delta=0.01):
    '''
    @description: 计算避免O3增加的VOCs与NOx最小减排比值VNr
        VNr = -(∂O3/∂NOx) / (∂O3/∂VOC) 在基准排放处
        当VOCs与NOx减排比例 >= VNr时，可避免O3不减反增
        参考Dingdian博士论文式(3-4)
    @param {pollutant_index}: int, 目标污染物索引
    @param {target_region_mask}: np.array, 目标区域掩码
    @param {target_region_idx}: int, 目标区域索引
    @param {month}: int, 月份
    @param {day}: int, 日期
    @param {hour}: int, 小时
    @param {pr_type}: str, 计算类型
    @param {delta}: float, 有限差分步长
    @return {vnr_value}: VNr值
    '''
    def get_conc(emis):
        rsm, bo3 = get_grid_values(pollutant_index, emis, month, day, hour=hour)
        return np.nanmean(rsm * target_region_mask)

    def build_emis(nox_delta=0, voc_delta=0):
        emis = np.ones((region_num, 1, species_num))
        if pr_type == "local":
            emis[target_region_idx, :, 0] = 1 + nox_delta
            emis[target_region_idx, :, 3] = 1 + voc_delta
        elif pr_type == "whole_region":
            emis[:, :, 0] = 1 + nox_delta
            emis[:, :, 3] = 1 + voc_delta
        return emis

    c0 = get_conc(build_emis())
    c_nox_plus = get_conc(build_emis(nox_delta=delta))
    c_nox_minus = get_conc(build_emis(nox_delta=-delta))
    c_voc_plus = get_conc(build_emis(voc_delta=delta))
    c_voc_minus = get_conc(build_emis(voc_delta=-delta))

    doc3_dnox = (c_nox_plus - c_nox_minus) / (2 * delta)
    doc3_dvoc = (c_voc_plus - c_voc_minus) / (2 * delta)

    if abs(doc3_dvoc) < 1e-10:
        return np.inf
    vnr_value = -doc3_dnox / doc3_dvoc
    return vnr_value

def get_o3_pr_vnr_value(days=days, file_name="PR_O3_Max_Sep.csv", calc_vnr=True):
    mp = model_attribute(all_aconc_files[0])
    model_lons, model_lats = mp.get_xy_coordinates(show_lonlat=True)
    dict_masks, _ = get_boundary_mask_data(boundary_json_file, model_lats, model_lons, field_name='adcode',
                                           replaceFalseWithNan=True,
                                           pkl_file_name=f"PRD_Cities_{row_num}_{col_num}.pkl")
    rows = []
    prd_cities = ['广州市', '深圳市', '佛山市', '东莞市', '惠州市', '江门市', '珠海市', '肇庆市', '中山市']
    for day in tqdm(days):
        for name, target_mask in dict_masks.items():
            if name not in prd_cities:
                continue
            target_region_idx = prd_cities.index(name)
            local_pr_value, local_o3_max_value = get_o3_pr_value(target_pollutant_idx, target_mask,
                                                                  target_region_idx, month, day,
                                                                  hour=None, pr_type="local")
            whole_region_pr_value, whole_region_o3_max_value = get_o3_pr_value(target_pollutant_idx, target_mask,
                                                                                target_region_idx, month, day,
                                                                                hour=None, pr_type="whole_region")
            row = [day, name, local_pr_value, local_o3_max_value, whole_region_pr_value, whole_region_o3_max_value]
            if calc_vnr:
                local_vnr = get_o3_vnr_value(target_pollutant_idx, target_mask, target_region_idx,
                                             month, day, hour=None, pr_type="local")
                whole_vnr = get_o3_vnr_value(target_pollutant_idx, target_mask, target_region_idx,
                                             month, day, hour=None, pr_type="whole_region")
                row += [local_vnr, whole_vnr]
            rows.append(row)
    cols = ["Day", "City", "Local_PR", "Local_O3_Max", "Whole_PR", "Whole_O3_Max"]
    if calc_vnr:
        cols += ["Local_VNr", "Whole_VNr"]
    df = pd.DataFrame(rows, columns=cols)
    df.to_csv(os.path.join(output_dir, f'{project_name}_{file_name}'), index=False, encoding='utf-8-sig')
    print(df.head(10))
    return df

def plot_pr_heatmap(csv_path=None):
    """Plot 9 cities × 5 days heatmap for Local PR and Whole PR"""
    city_abbr = {'广州市':'GZ','深圳市':'SZ','佛山市':'FS','东莞市':'DG',
                 '惠州市':'HZ','江门市':'JM','珠海市':'ZH','肇庆市':'ZQ','中山市':'ZS'}
    prd_cities = list(city_abbr.keys())
    if csv_path is None:
        csv_path = os.path.join(output_dir, f'{project_name}_PR_O3_Max_Sep_MRSM.csv')
    df = pd.read_csv(csv_path)
    days = sorted(df['Day'].unique())
    
    for pr_col, title_prefix in [("Local_PR", "Local PR"), ("Whole_PR", "Whole PR")]:
        pivot = df.pivot(index="City", columns="Day", values=pr_col)
        pivot = pivot.reindex(index=prd_cities, columns=days)
        data = pivot.values.astype(float)

        annot = np.array([["*" if v >= upper_value else f"{v:.2f}" for v in row] for row in data])
        city_labels = [city_abbr[c] for c in prd_cities]

        fig, ax = plt.subplots(figsize=(7, 6))
        im = ax.imshow(data, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=upper_value)
        ax.set_xticks(range(len(days)))
        ax.set_xticklabels([f"Day {d}" for d in days], fontsize=11)
        ax.set_yticks(range(len(prd_cities)))
        ax.set_yticklabels(city_labels, fontsize=11)

        for i in range(len(prd_cities)):
            for j in range(len(days)):
                color = "white" if data[i, j] > upper_value else "black"
                ax.text(j, i, annot[i, j], ha="center", va="center", fontsize=10, color=color)

        cbar = fig.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label("PR", fontsize=12)
        ax.set_title(title_prefix, fontsize=14, pad=10)
        plt.tight_layout()

        save_path = os.path.join(output_dir, f'{project_name}_{title_prefix.replace(" ", "_")}_heatmap.png')
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
        print(f"Saved: {save_path}")
        plt.close()

#endregion

### 1.6 导出EKMA曲线数据到Excel
def export_ekma_data_to_excel(days=[6,13,14,16,19], show_city_emka=True):
    xx = np.arange(0, 1.51, 0.25)
    yy = np.arange(0, 1.51, 0.25)
    x_p_idx, y_p_idx = 0, 3
    case_num = len(xx) * len(yy)
    emis_matrix = np.ones((region_num, case_num, species_num))
    ctrl = np.ones((region_num, species_num))
    c_index = 0
    for j in range(len(yy)):
        for i in range(len(xx)):
            ctrl[:, x_p_idx] = xx[i]
            ctrl[:, y_p_idx] = yy[j]
            emis_matrix[:, c_index, :] = ctrl.copy()
            c_index += 1

    dict_masks_cache = None
    if show_city_emka:
        mp = model_attribute(all_aconc_files[0])
        model_lons, model_lats = mp.get_xy_coordinates(show_lonlat=True)
        dict_masks_cache, _ = get_boundary_mask_data(boundary_json_file, model_lats, model_lons,
                                                      field_name='adcode', replaceFalseWithNan=True,
                                                      pkl_file_name=f"PRD_Cities_{row_num}_{col_num}.pkl")

    save_path = os.path.join(output_oos_dir, 'ekma_curve')
    if not os.path.exists(save_path):
        os.makedirs(save_path)
    excel_path = os.path.join(save_path, f'{project_name}_ekma_curve_data.xlsx')

    prd_cities = ['广州市', '深圳市', '佛山市', '东莞市', '惠州市', '江门市', '珠海市', '肇庆市', '中山市']
    city_abbr = {'广州市': 'GZ', '深圳市': 'SZ', '佛山市': 'FS', '东莞市': 'DG',
                 '惠州市': 'HZ', '江门市': 'JM', '珠海市': 'ZH', '肇庆市': 'ZQ', '中山市': 'ZS'}

    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        for day in tqdm(days, desc="Exporting EKMA data"):
            rsm_values = None
            for c_idx in range(case_num):
                ctr = emis_matrix[:, c_idx, :]
                if rsm_values is None:
                    rsm_values = np.zeros((case_num, row_num, col_num))
                rsm, bo3 = GetOzoneGridValues(target_pollutant_idx, ctr, month, day, hour=None)
                rsm_values[c_idx, :, :] = rsm

            # Whole domain: zz[i,j] = mean O3 for NOx=xx[i], VOC=yy[j]
            rows = []
            for i, nox in enumerate(xx):
                for j, voc in enumerate(yy):
                    c_idx = i * len(yy) + j
                    rows.append({'NOx': nox, 'VOC': voc, 'O3_WholeDomain': np.mean(rsm_values[c_idx, :, :])})
                    # Append city data
                    if show_city_emka and dict_masks_cache is not None:
                        for city_name in prd_cities:
                            if city_name in dict_masks_cache:
                                mask = dict_masks_cache[city_name]
                                abbr = city_abbr[city_name]
                                rows[-1][f'O3_{abbr}'] = np.nanmean(rsm_values[c_idx, :, :] * mask)
            df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=f'Day_{day}', index=False)

    print(f"EKMA data exported to: {excel_path}")
    return excel_path

#endregion

def plot_cities_ekma_curve(days=[6, 13, 14, 16, 19],cities=['深圳市','惠州市','广州市','珠海市']):
    """Plot EKMA curves for given cities across pollution days. Layout: cities(rows) × days(columns)."""
    from collections import OrderedDict
    from esil.rsm_helper.model_property import model_attribute
    from esil.earth_helper import get_boundary_mask_data
    from b_input_data_helper import all_aconc_files, boundary_json_file
    from esil.rsm_helper.ekma_curve import plot_multiple_ekma_curves

    city_abbr_map = {'广州市':'GZ','深圳市':'SZ','佛山市':'FS','东莞市':'DG',
                     '惠州市':'HZ','江门市':'JM','珠海市':'ZH','肇庆市':'ZQ','中山市':'ZS'}
    target_cities = OrderedDict([(c, city_abbr_map[c]) for c in cities])

    xx = np.arange(0, 1.51, 0.25)
    yy = np.arange(0, 1.51, 0.25)
    x_p_idx, y_p_idx = 0, 3
    case_num = len(xx) * len(yy)

    # Build emission control matrix
    emis_matrix = np.ones((region_num, case_num, species_num))
    ctrl = np.ones((region_num, species_num))
    c_index = 0
    for j in range(len(yy)):
        for i in range(len(xx)):
            ctrl[:, x_p_idx] = xx[i]
            ctrl[:, y_p_idx] = yy[j]
            emis_matrix[:, c_index, :] = ctrl.copy()
            c_index += 1

    # Get city masks
    mp = model_attribute(all_aconc_files[0])
    model_lons, model_lats = mp.get_xy_coordinates(show_lonlat=True)
    dict_masks, _ = get_boundary_mask_data(boundary_json_file, model_lats, model_lons,
                                           field_name='adcode', replaceFalseWithNan=True,
                                           pkl_file_name=f"PRD_Cities_{row_num}_{col_num}.pkl")

    save_path = os.path.join(output_oos_dir, 'ekma_curve')
    if not os.path.exists(save_path):
        os.makedirs(save_path)

    # Compute EKMA data for each day and city
    city_day_data = {}
    for day in tqdm(days, desc="Computing EKMA data"):
        rsm_values = np.zeros((case_num, row_num, col_num))
        for c_idx in range(case_num):
            ctr = emis_matrix[:, c_idx, :]
            rsm, bo3 = GetOzoneGridValues(target_pollutant_idx, ctr, month, day, hour=None)
            rsm_values[c_idx, :, :] = rsm

        for city_name, city_abbr in target_cities.items():
            if city_name not in dict_masks:
                continue
            mask = dict_masks[city_name]
            zz = np.zeros((len(xx), len(yy)))
            c_index = 0
            for i in range(len(xx)):
                for j in range(len(yy)):
                    zz[i, j] = np.nanmean(rsm_values[c_index, :, :] * mask)
                    c_index += 1
            city_day_data[(city_abbr, day)] = zz.copy()

    # Build ordered dict: city-by-city (rows), day-by-day (columns)
    dict_data = OrderedDict()
    for city_name, city_abbr in target_cities.items():
        for day in days:
            key = f'{city_abbr} - Sep {day}'
            dict_data[key] = [xx, yy, city_day_data[(city_abbr, day)]]

    n_rows, n_cols = len(target_cities), len(days)

    # Nature style: Arial/DejaVu Sans, 8 pt
    plt.rcParams['font.family'] = 'DejaVu Sans'
    plt.rcParams['font.size'] = 8
    plt.rcParams['axes.linewidth'] = 0.5
    plt.rcParams['xtick.labelsize'] = 8
    plt.rcParams['ytick.labelsize'] = 8

    fig = plot_multiple_ekma_curves(dict_data, cmap='jet', x_title='NOx', y_title='VOC',
                                    legend_title='O3 (ppb)', value_format='.1f',
                                    panel_layout=(n_cols, n_rows), show_minmax=True,
                                    fig_size=(n_cols * 5, n_rows * 5 + 2), showplot=False, show_sup_title=True)
    fig.subplots_adjust(bottom=0.12, hspace=0.35, right=0.88)

    city_labels = '_'.join(abbr for _, abbr in target_cities.items())
    savefile = os.path.join(save_path, f'{project_name}_ekma_curve_{city_labels}.png')
    fig.savefig(savefile, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    plt.rcParams.update(plt.rcParamsDefault)
    print(f"Saved: {savefile}")


if __name__ == '__main__':
    days=[x for x in range(1, 31) ]
    days=[6,13,14,16,19]
    plot_cities_ekma_curve(days=days, cities=['深圳市','惠州市','广州市','珠海市'])
    plot_ekma_curve(days=days,show_city_emka=True)
    export_ekma_data_to_excel(days=days, show_city_emka=True)
    file_name="PR_O3_Max_Sep_MRSM_20260506.csv"
    csv_path=os.path.join(output_dir, f'{project_name}_{file_name}')
    get_o3_pr_vnr_value(days=days,file_name=file_name)
    # csv_path = os.path.join(output_dir, f'{project_name}_PR_O3_Max_Sep_MRSM.csv')
    plot_pr_heatmap(csv_path=csv_path)
    print("done")
