'''
Author: Devin
Date: 2024-05-01 12:13:42
LastEditors: Devin
LastEditTime: 2024-05-01 12:36:32
Description: 

Copyright (c) 2024 by Devin, All Rights Reserved. 
'''
import json
import numpy as np
import xarray as xr
from shapely.geometry import shape, Point, MultiPolygon
from shapely.prepared import prep
from tqdm.auto import tqdm#显示进度
import os
import pickle
#解释aox函数    
#func是一个函数，n是一个整数
#返回一个新的函数，这个函数的作用是对输入的数组进行转置，然后对转置后的数组进行func操作 
#再对func操作后的数组进行转置
#perm是一个数组，这个数组的作用是对数组进行转置
def aox(func, n=0):
    def wrapper(x):
        perm = [n] + [0 if i==n else i for i in range(1,x.ndim)]
        tr = lambda arr: np.transpose(arr, perm)
        return tr(func(tr(x)))
    return wrapper
#计算网格点的均值
mean = lambda arr: (arr[1:,...] + arr[:-1,...]) / 2
#计算网格点的面积
ext = lambda arr: np.concatenate([[2*arr[0,...] - arr[1,...]], arr, 2*arr[-1,...] - [arr[-2,...]]  ], axis=0)
dup = lambda func: (lambda x: aox(func, 0)(aox(func, 1)(x)) )
#计算网格点的面积
stag = dup(lambda arr: mean(ext(arr)))
#将角度转化为弧度
deg2rad = lambda deg: deg/180*np.pi

#计算经纬度网格点的梯度
#axis=0时，计算纬度方向的梯度
#axis=1时，计算经度方向的梯度
def get_del_vect(lon, lat, axis=0):
    '''
    @description: 计算经纬度网格点的梯度
    @param (np.array) lon: 经度坐标
    @param (np.array) lat: 纬度坐标 
    @param (int) axis: 计算纬度方向的梯度时，axis=0；计算经度方向的梯度时，axis=1
    @return {np.array} dx, dy: 经度方向的梯度和纬度方向的梯度
    '''
    a = 6371e3
    d = aox((lambda arr: arr[1:,...] - arr[:-1,...]), axis)
    h = aox((lambda arr: arr[:-1,...]), 1-axis)
    t = lambda arr: deg2rad(h(d(stag(arr))))
    dx = a * t(lon) * np.cos(deg2rad(lat))
    dy = a * t(lat)
    return dx, dy

def get_m2(lon, lat):
    '''
    @description: 计算网格点的面积
    @param (np.array) lon: 经度坐标
    @param (np.array) lat: 纬度坐标
    @return {np.array} 面积（单位m2）
    '''
    #计算网格点的梯度
    v0_dx, v0_dy = get_del_vect(lon, lat, axis=0)
    #将网格点的梯度转置
    v1_dx, v1_dy = get_del_vect(lon, lat, axis=1)
    #计算网格点的面积,v1_dx*v0_dy - v1_dy*v0_dx 为什么是相减？
    return np.abs( v1_dx*v0_dy - v1_dy*v0_dx )

def get_mask(json_file, lon, lat,replaceFalseWithNan=False):
    '''
    @description: 从geojson文件中获取mask
    @param (str) json_file: geojson文件路径
    @param (np.array) lon: 经度坐标
    @param (np.array) lat: 纬度坐标
    @return {np.array} mask: mask
    '''
    with open(json_file, 'r', encoding='utf-8') as f:
        poly = shape(json.load(f)['features'][0]['geometry'])
    poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
    #path = Path.make_compound_path(*geos_to_path(poly[:3]))   
    poly = prep(MultiPolygon(poly[:3]))
    mask = list(map(lambda x, y: poly.contains(Point(x, y)), tqdm(lon.flat), lat.flat))
    mask = np.array(mask).reshape(lon.shape)
    if replaceFalseWithNan:       
        # 将False替换为NAN
        mask = np.where(mask == False, np.nan, mask) 
    return mask

def get_all_masks(json_file, lon, lat,replaceFalseWithNan=False):
    '''
    @description: 从geojson文件中获取所有mask
    @param (str) json_file: geojson文件路径
    @param (np.array) lon: 经度坐标
    @param (np.array) lat: 纬度坐标
    @return {dict_masks: dict}
    '''
    dict_masks={}
    with open(json_file, 'r', encoding='utf-8') as f:
        for i,feature in enumerate(json.load(f)['features']):
            poly = shape(feature['geometry'])
            poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
            poly = prep(MultiPolygon(poly[:3]))
            mask = list(map(lambda x, y: poly.contains(Point(x, y)), tqdm(lon.flat), lat.flat))
            mask = np.array(mask).reshape(lon.shape)
            if replaceFalseWithNan:       
                # 将False替换为NAN
                mask = np.where(mask == False, np.nan, mask)
            name=feature['properties']['name'] if 'name' in feature['properties'] else str(i)
            dict_masks[name]=mask        
    return dict_masks

def get_mask_with_name(json_file, lon, lat,field_name='adcode',replaceFalseWithNan=False): 
    '''
    @description: 从geojson文件中获取mask，并返回mask的名称
    @param (str) json_file: geojson文件路径
    @param (np.array) lon: 经度坐标
    @param (np.array) lat: 纬度坐标
    @return {np.array} mask_name: mask的名称
    @return {np.array} mask: mask    
    @return {dict} dict_data: 包含每个mask的名称的字典
    '''   
    # 创建一个空的 mask，初始化为 -1，表示没有匹配的 feature
    mask = np.full(lon.shape, -1, dtype=int)  
    mask_name = np.full(lon.shape, "", dtype='U10')#避免字符串被截取掉，需要设定一个字符串长度10，而不能用默认的str类型
    #mask_name = np.full(lon.shape, "", dtype='str')
    dict_data={}  
    with open(json_file, 'r', encoding='utf-8') as f:
        for idx,feature in tqdm(enumerate(json.load(f)['features'])):
            poly = shape(feature['geometry'])
            poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
            poly = prep(MultiPolygon(poly[:3]))
            # mask = list(map(lambda x, y: poly.contains(Point(x, y)), tqdm(lon.flat), lat.flat))
            # mask = np.array(mask).reshape(lon.shape)            
            contains_mask = np.array(list(map(lambda x, y: poly.contains(Point(x, y)), lon.flat, lat.flat)))
            contains_mask = contains_mask.reshape(lon.shape)
            mask[contains_mask] = idx  # 将属于当前多边形的点的 mask 设置为该多边形的索引            
            # if replaceFalseWithNan:       
            #     # 将False替换为NAN
            #     mask = np.where(mask == False, np.nan, mask) 
            if field_name in feature['properties']:
                name=feature['properties'][field_name]
            elif 'adcode' in feature['properties']:
                name=feature['properties']['adcode']
            else:
                name=str(idx)            
            dict_data[idx]=name
            mask_name[contains_mask] = name   
    if replaceFalseWithNan:
        # 将 -1 替换为 NaN
        mask = np.where(mask == -1, np.nan, mask)         
    return mask_name,mask,dict_data

def get_boundary_mask_data(boundary_json_file,lats, lons,field_name='adcode',replaceFalseWithNan=True,pkl_file_name=None):  
    '''
    @description: 从geojson文件中获取边界mask数据
    @param (str) boundary_json_file: 边界geojson文件路径
    @param (np.array) lats: 纬度坐标
    @param (np.array) lons: 经度坐标
    @param (bool) replaceFalseWithNan: 是否将False替换为NAN
    @return {dict_masks: dict}
    @return {np.array} mask_name: mask的名称
    '''  
    dir=os.path.dirname(boundary_json_file)
    boundary_file_name=os.path.basename(boundary_json_file)
    boundary_mask_file=os.path.join(dir,f'{boundary_file_name}.pkl') if pkl_file_name is None else os.path.join(dir,pkl_file_name)
    if os.path.exists(boundary_mask_file):
        with open(boundary_mask_file, 'rb') as file:
            dict_masks,mask_name = pickle.load(file)
    else:        
        dict_masks=get_all_masks(json_file=boundary_json_file,lat=lats,lon=lons,replaceFalseWithNan=replaceFalseWithNan)
        mask_name,_,_=get_mask_with_name(json_file=boundary_json_file,lat=lats,lon=lons,field_name=field_name,replaceFalseWithNan=replaceFalseWithNan) 
        masks=(dict_masks,mask_name)
        # 将字典保存到文件
        with open(boundary_mask_file, 'wb') as file:
            pickle.dump(masks, file)
    return dict_masks,mask_name

if __name__ == '__main__':
    from wrf import (to_np, getvar, smooth2d, get_cartopy, cartopy_xlim,
                 cartopy_ylim, latlon_coords,get_basemap)
    import netCDF4 as nc 
    
    
    wrf_out_file=r'/work/home/pengzhen/PRD9km_2/devin/python_project/code/co2_inversion/data/wrfinput_d01.nc'
    dataset = nc.Dataset(wrf_out_file, 'r') 
    t2 = getvar(dataset, "T2")
    # Get the cartopy mapping object
    cart_proj = get_cartopy(t2)
    # Get the latitude and longitude points
    lats, lons =latlon_coords(t2)# latlon_coords(t2)  
    lons,lats =to_np(lons), to_np(lats)  
    boundary_json_file='/work/home/pengzhen/PRD9km_2/devin/python_project/code/co2_inversion/data/boundary/guangdong_cities.json'
    dict_mask,masknames=get_boundary_mask_data(boundary_json_file,lats, lons)   
    print('done')
    # print(dict_masks1)
    # print(mask_name1)
    # 显示多个地图