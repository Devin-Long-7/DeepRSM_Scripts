"""
Author: Devin
Date: 2024-05-01 12:13:42
LastEditors: Devin
LastEditTime: 2024-11-12 14:51:13
Description: 

Copyright (c) 2024 by Devin, All Rights Reserved. 
"""

import json
import numpy as np
import xarray as xr
from shapely.geometry import shape, Point, MultiPolygon
from shapely.prepared import prep
from tqdm.auto import tqdm  # 显示进度
import os
import pickle


# 解释aox函数
# func是一个函数，n是一个整数
# 返回一个新的函数，这个函数的作用是对输入的数组进行转置，然后对转置后的数组进行func操作
# 再对func操作后的数组进行转置
# perm是一个数组，这个数组的作用是对数组进行转置
def aox(func, n=0):
    def wrapper(x):
        perm = [n] + [0 if i == n else i for i in range(1, x.ndim)]
        tr = lambda arr: np.transpose(arr, perm)
        return tr(func(tr(x)))

    return wrapper


# 计算网格点的均值
mean = lambda arr: (arr[1:, ...] + arr[:-1, ...]) / 2
# 计算网格点的面积
ext = lambda arr: np.concatenate(
    [[2 * arr[0, ...] - arr[1, ...]], arr, 2 * arr[-1, ...] - [arr[-2, ...]]], axis=0
)
dup = lambda func: (lambda x: aox(func, 0)(aox(func, 1)(x)))
# 计算网格点的面积
stag = dup(lambda arr: mean(ext(arr)))
# 将角度转化为弧度
deg2rad = lambda deg: deg / 180 * np.pi


# 计算经纬度网格点的梯度
# axis=0时，计算纬度方向的梯度
# axis=1时，计算经度方向的梯度
def get_del_vect(lon, lat, axis=0):
    """
    @description: 计算经纬度网格点的梯度
    @param (np.array) lon: 经度坐标
    @param (np.array) lat: 纬度坐标
    @param (int) axis: 计算纬度方向的梯度时，axis=0；计算经度方向的梯度时，axis=1
    @return {np.array} dx, dy: 经度方向的梯度和纬度方向的梯度
    """
    a = 6371e3
    d = aox((lambda arr: arr[1:, ...] - arr[:-1, ...]), axis)
    h = aox((lambda arr: arr[:-1, ...]), 1 - axis)
    t = lambda arr: deg2rad(h(d(stag(arr))))
    dx = a * t(lon) * np.cos(deg2rad(lat))
    dy = a * t(lat)
    return dx, dy


def get_m2(lon, lat):
    """
    @description: 计算网格点的面积
    @param (np.array) lon: 经度坐标
    @param (np.array) lat: 纬度坐标
    @return {np.array} 面积（单位m2）
    """
    # 计算网格点的梯度
    v0_dx, v0_dy = get_del_vect(lon, lat, axis=0)
    # 将网格点的梯度转置
    v1_dx, v1_dy = get_del_vect(lon, lat, axis=1)
    # 计算网格点的面积,v1_dx*v0_dy - v1_dy*v0_dx 为什么是相减？
    return np.abs(v1_dx * v0_dy - v1_dy * v0_dx)


def get_mask(json_file, lon, lat, replaceFalseWithNan=False):
    """
    @description: 从geojson文件中获取mask
    @param (str) json_file: geojson文件路径
    @param (np.array) lon: 经度坐标
    @param (np.array) lat: 纬度坐标
    @return {np.array} mask: mask
    """
    with open(json_file, "r", encoding="utf-8") as f:
        poly = shape(json.load(f)["features"][0]["geometry"])
    poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
    # path = Path.make_compound_path(*geos_to_path(poly[:3]))
    poly = prep(MultiPolygon(poly[:3]))
    mask = list(map(lambda x, y: poly.contains(Point(x, y)), tqdm(lon.flat), lat.flat))
    mask = np.array(mask).reshape(lon.shape)
    if replaceFalseWithNan:
        # 将False替换为NAN
        mask = np.where(mask == False, np.nan, mask)
    return mask


def get_all_masks(json_file, lon, lat, replaceFalseWithNan=False):
    """
    @description: 从geojson文件中获取所有mask
    @param (str) json_file: geojson文件路径
    @param (np.array) lon: 经度坐标
    @param (np.array) lat: 纬度坐标
    @return {dict_masks: dict}
    """
    dict_masks = {}
    with open(json_file, "r", encoding="utf-8") as f:
        for i, feature in enumerate(json.load(f)["features"]):
            poly = shape(feature["geometry"])
            poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
            poly = prep(MultiPolygon(poly[:3]))
            mask = list(
                map(lambda x, y: poly.contains(Point(x, y)), tqdm(lon.flat), lat.flat)
            )
            mask = np.array(mask).reshape(lon.shape)
            if replaceFalseWithNan:
                # 将False替换为NAN
                mask = np.where(mask == False, np.nan, mask)
            name = (
                feature["properties"]["name"]
                if "name" in feature["properties"]
                else str(i)
            )
            dict_masks[name] = mask
    return dict_masks


def get_mask_with_name(
    json_file, lon, lat, field_name="adcode", replaceFalseWithNan=False
):
    """
    @description: 从geojson文件中获取mask，并返回mask的名称
    @param (str) json_file: geojson文件路径
    @param (np.array) lon: 经度坐标
    @param (np.array) lat: 纬度坐标
    @return {np.array} mask_name: mask的名称
    @return {np.array} mask: mask
    @return {dict} dict_data: 包含每个mask的名称的字典
    """
    # 创建一个空的 mask，初始化为 -1，表示没有匹配的 feature
    mask = np.full(lon.shape, -1, dtype=int)
    mask_name = np.full(
        lon.shape, "", dtype="U10"
    )  # 避免字符串被截取掉，需要设定一个字符串长度10，而不能用默认的str类型
    # mask_name = np.full(lon.shape, "", dtype='str')
    dict_data = {}
    with open(json_file, "r", encoding="utf-8") as f:
        for idx, feature in tqdm(enumerate(json.load(f)["features"])):
            poly = shape(feature["geometry"])
            poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
            poly = prep(MultiPolygon(poly[:3]))
            # mask = list(map(lambda x, y: poly.contains(Point(x, y)), tqdm(lon.flat), lat.flat))
            # mask = np.array(mask).reshape(lon.shape)
            contains_mask = np.array(
                list(map(lambda x, y: poly.contains(Point(x, y)), lon.flat, lat.flat))
            )
            contains_mask = contains_mask.reshape(lon.shape)
            mask[contains_mask] = (
                idx  # 将属于当前多边形的点的 mask 设置为该多边形的索引
            )
            # if replaceFalseWithNan:
            #     # 将False替换为NAN
            #     mask = np.where(mask == False, np.nan, mask)
            if field_name in feature["properties"]:
                name = feature["properties"][field_name]
            elif "adcode" in feature["properties"]:
                name = feature["properties"]["adcode"]
            else:
                name = str(idx)
            dict_data[idx] = name
            mask_name[contains_mask] = name
    if replaceFalseWithNan:
        # 将 -1 替换为 NaN
        mask = np.where(mask == -1, np.nan, mask)
    return mask_name, mask, dict_data


def get_boundary_mask_data(
    boundary_json_file,
    lats,
    lons,
    field_name="adcode",
    replaceFalseWithNan=True,
    pkl_file_name=None,
):
    """
    @description: 从geojson文件中获取边界mask数据
    @param (str) boundary_json_file: 边界geojson文件路径
    @param (np.array) lats: 纬度坐标
    @param (np.array) lons: 经度坐标
    @param (bool) replaceFalseWithNan: 是否将False替换为NAN
    @return {dict_masks: dict}
    @return {np.array} mask_name: mask的名称
    """
    dir = os.path.dirname(boundary_json_file)
    boundary_file_name = os.path.basename(boundary_json_file)
    boundary_mask_file = (
        os.path.join(dir, f"{boundary_file_name}.pkl")
        if pkl_file_name is None
        else os.path.join(dir, pkl_file_name)
    )
    if os.path.exists(boundary_mask_file):
        with open(boundary_mask_file, "rb") as file:
            dict_masks, mask_name = pickle.load(file)
    else:
        dict_masks = get_all_masks(
            json_file=boundary_json_file,
            lat=lats,
            lon=lons,
            replaceFalseWithNan=replaceFalseWithNan,
        )
        mask_name, _, _ = get_mask_with_name(
            json_file=boundary_json_file,
            lat=lats,
            lon=lons,
            field_name=field_name,
            replaceFalseWithNan=replaceFalseWithNan,
        )
        masks = (dict_masks, mask_name)
        # 将字典保存到文件
        with open(boundary_mask_file, "wb") as file:
            pickle.dump(masks, file)
    return dict_masks, mask_name


def get_mask_by_intersection(
    json_file,
    grid_polygons,
    mask_shape=None,
    threshold=0.1,
    top_x_features=3,
    replaceFalseWithNan=False,
):
    """
    @description: 通过计算行政区域与网格的交集面积占比方式，从geojson文件中获取mask
    @param (str) json_file: geojson文件路径
    @param (np.array) grid_polygons: 包含每个网格四个角的polygon列表
    @param (tuple) mask_shape: mask的形状，默认为None，表示mask的形状与grid_polygons相同；也可以指定最终返回的mask的形状
    @param (float) threshold: 面积占比阈值,默认为0.1，表示交集面积占比大于等于0.1的网格将被标记为1，否则为0，如果为None，则返回交集面积占比
    @param (bool) replaceFalseWithNan: 是否将False替换为NAN
    @return {np.array} mask: mask
    """
    with open(json_file, "r", encoding="utf-8") as f:
        poly = shape(json.load(f)["features"][0]["geometry"])
    # 如果是MultiPolygon，按面积排序并取前3个
    if isinstance(poly, MultiPolygon):
        poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
        poly = MultiPolygon(poly[:top_x_features])
    mask = calculated_mask_by_intersection(
        poly, grid_polygons, threshold, replaceFalseWithNan, mask_shape
    )
    return mask


def get_all_masks_by_intersection(
    json_file,
    grid_polygons,
    mask_shape=None,
    threshold=0.1,
    top_x_features=3,
    field_name="name",
    replaceFalseWithNan=False,
):
    """
    @description: 从geojson文件中获取行政区域，并计算交集面积占比，进而根据面积占比阈值生成mask
    @param (str) json_file: geojson文件路径
    @param (list) grid_polygons: 包含每个网格四个角的polygon列表
    @param (tuple) mask_shape: mask的形状，默认为None，表示mask的形状与grid_polygons相同；也可以指定最终返回的mask的形状
    @param (float) threshold: 面积占比阈值,默认为0.1，表示交集面积占比大于等于0.1的网格将被标记为1，否则为0，如果为None，则返回交集面积占比
    @param (bool) replaceFalseWithNan: 是否将False替换为NAN
    @param (int) top_x_features: 从geojson文件中获取前top_x_features个面积最大的feature，默认为3
    @return {dict_masks: dict},key:feature的名称，value:mask
    """
    if json_file.endswith(".shp"):
        return get_all_masks_by_intersection_from_shapefile(
            shp_file=json_file,
            grid_polygons=grid_polygons,
            mask_shape=mask_shape,
            threshold=threshold,
            top_x_features=top_x_features,
            field_name=field_name,
            replaceFalseWithNan=replaceFalseWithNan,
        )
    dict_masks = {}
    with open(json_file, "r", encoding="utf-8") as f:
        for i, feature in enumerate(json.load(f)["features"]):
            name = (
                feature["properties"][field_name]
                if field_name in feature["properties"]
                else str(i)
            )
            poly = shape(feature["geometry"])
            poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
            poly = MultiPolygon(poly[:top_x_features])
            mask = calculated_mask_by_intersection(
                poly, grid_polygons, threshold, replaceFalseWithNan, mask_shape, name
            )
            dict_masks[name] = mask
            
    return dict_masks

def get_all_masks_by_intersection_from_shapefile(
    shp_file,
    grid_polygons,
    mask_shape=None,
    threshold=0.1,
    top_x_features=3,
    field_name="name",
    replaceFalseWithNan=False,
):
    """
    @description: 从shapefile文件中获取行政区域，并计算交集面积占比，进而根据面积占比阈值生成mask
    @param (str) shp_file: shapefile文件路径
    @param (list) grid_polygons: 包含每个网格四个角的polygon列表
    @param (tuple) mask_shape: mask的形状，默认为None，表示mask的形状与grid_polygons相同；也可以指定最终返回的mask的形状
    @param (float) threshold: 面积占比阈值,默认为0.1，表示交集面积占比大于等于0.1的网格将被标记为1，否则为0，如果为None，则返回交集面积占比
    @param (bool) replaceFalseWithNan: 是否将False替换为NAN
    @param (int) top_x_features: 从shapefile文件中获取前top_x_features个面积最大的feature，默认为3
    @return {dict_masks: dict},key:feature的名称，value:mask
    """
    import geopandas as gpd
    dict_masks = {}
    gdf = gpd.read_file(shp_file)

    for i, feature in gdf.iterrows():
        name = (
            feature[field_name]
            if field_name in feature
            else str(i)
        )
        poly = feature["geometry"]
        if poly.geom_type == 'MultiPolygon':
            poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
            poly = MultiPolygon(poly[:top_x_features])
        elif poly.geom_type == 'Polygon':
            poly = MultiPolygon([poly])
        else:
            continue  # Skip if the geometry type is not Polygon or MultiPolygon

        mask = calculated_mask_by_intersection(
            poly, grid_polygons, threshold, replaceFalseWithNan, mask_shape, name
        )
        dict_masks[name] = mask

    return dict_masks

def get_mask_with_name_by_intersection(
    json_file,
    grid_polygons,
    mask_shape,
    threshold=0.1,
    top_x_features=3,
    field_name="adcode",
    replaceFalseWithNan=False,
):
    """
    @description: 从geojson文件中获取mask，并返回mask的名称
    @param (str) json_file: geojson文件路径
    @param (list) grid_polygons: 包含每个网格四个角的polygon列表
    @param (tuple) mask_shape: mask的形状，默认为None，表示mask的形状与grid_polygons相同；也可以指定最终返回的mask的形状
    @param (float) threshold: 面积占比阈值,默认为0.1，表示交集面积占比大于等于0.1的网格将被标记为1，否则为0，如果为None，则返回交集面积占比
    @param (bool) replaceFalseWithNan: 是否将False替换为NAN
    @param (int) top_x_features: 从geojson文件中获取前top_x_features个面积最大的feature，默认为3
    @return {np.array} mask_name: mask的名称
    @return {np.array} mask: mask
    @return {dict} dict_data: 包含每个mask的名称的字典
    """
    # 创建一个空的 mask，初始化为 -1，表示没有匹配的 feature
    mask = np.full(mask_shape, False, dtype=int)
    mask_name = np.full(
        mask_shape, "", dtype="U10"
    )  # 避免字符串被截取掉，需要设定一个字符串长度10，而不能用默认的str类型
    # mask_name = np.full(lon.shape, "", dtype='str')
    dict_data = {}
    with open(json_file, "r", encoding="utf-8") as f:
        for idx, feature in tqdm(enumerate(json.load(f)["features"])):
            poly = shape(feature["geometry"])
            poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
            poly = MultiPolygon(poly[:top_x_features])
            contains_mask = calculated_mask_by_intersection(
                poly, grid_polygons, threshold, replaceFalseWithNan, mask_shape
            )
            mask[contains_mask] = (
                idx  # 将属于当前多边形的点的 mask 设置为该多边形的索引
            )
            if field_name in feature["properties"]:
                name = feature["properties"][field_name]
            elif "adcode" in feature["properties"]:
                name = feature["properties"]["adcode"]
            else:
                name = str(idx)
            dict_data[idx] = name
            mask_name[contains_mask] = name
    if replaceFalseWithNan:
        # 将 -1 替换为 NaN
        mask = np.where(mask == False, np.nan, mask)
    return mask_name, mask, dict_data


def calculated_mask_by_intersection(
    boundary_poly, grid_polygons, threshold, replaceFalseWithNan, mask_shape, name=None
):
    """
    @description: 通过计算行政区域与网格的交集面积占比方式，从geojson文件中获取mask。内部方法
    @param (MultiPolygon) boundary_poly: 行政区域的polygon
    @param (list) grid_polygons: 包含每个网格四个角的polygon列表
    @param (float) threshold: 面积占比阈值,如0.1，表示交集面积占比大于等于0.1的网格将被标记为1，否则为0，如果为None，则返回交集面积占比
    @param (bool) replaceFalseWithNan: 是否将False替换为NAN
    @param (tuple) mask_shape: mask的形状，默认为None，表示mask的形状与grid_polygons相同；也可以指定最终返回的mask的形状
    @param (str) name: 行政区域的名称
    @return {np.array} mask: mask
    """

    # prep 是 shapely 库中的一个工具，来自 shapely.prepared 模块。它的主要作用是将一个几何对象（如 Polygon、MultiPolygon 等）进行预处理，生成一个 PreparedGeometry 对象。
    # 这个对象经过优化，可以加速某些几何运算，特别是在进行空间查询时（如判断一个点是否在多边形内，或者两个几何体是否相交等）。为什么要使用 prep？
    # 在涉及大量几何操作时，比如进行空间查询或相交测试，直接使用未优化的几何对象可能会比较慢。prep 函数通过预处理几何对象，创建一个 PreparedGeometry，可以显著加快以下操作：
    # contains：判断一个几何对象是否包含另一个几何对象。
    # intersects：判断两个几何对象是否相交。
    # within：判断一个几何对象是否在另一个几何对象内。
    """
    如下图所示，这个行政区域就存在自相交问题，因为它的内部有一个小的孔洞，这个孔洞与行政区域的外部边界相交。这种情况下，我们可以使用 buffer(0) 方法来修复这个问题。
  +---------+
  |         |
  |    +----|----+
  |    |    |    |
  +----|----+    |
       |         |
       +---------+
    """
    prepared_poly = prep(boundary_poly)  # 准备优化的几何对象用于空间查询
    mask = np.zeros(len(grid_polygons), dtype=float)
    # 检查 boundary_poly 是否有效
    if not boundary_poly.is_valid:
        from shapely.validation import explain_validity

        print(f"Invalid boundary geometry: {explain_validity(boundary_poly)}")
        boundary_poly = boundary_poly.buffer(0)  # 尝试修复
    # 遍历每个grid_polygon，计算与poly的交集面积占比
    for i, grid_polygon in enumerate(
        tqdm(
            grid_polygons,
            desc=f'Calculating intersection area{"" if name is None else " for "+name}',
        )
    ):
        if prepared_poly.intersects(grid_polygon):
            # 使用原始的 poly 进行交集计算，而不是 prepared_poly
            intersection = boundary_poly.intersection(grid_polygon)
            intersection_area = intersection.area
            # 计算交集面积占比并与阈值比较
            if threshold is None:
                mask[i] = intersection_area / grid_polygon.area
            else:
                mask[i] = (intersection_area / grid_polygon.area) >= threshold
        else:
            mask[i] = False  # 如果没有交集，掩码为False
    if replaceFalseWithNan:
        # 将False替换为NAN
        mask = np.where(mask == False, np.nan, mask)
    if mask_shape is not None:
        mask = mask.reshape(mask_shape)
    return mask


def get_boundary_mask_data_by_intersection(
    boundary_json_file,
    grid_polygons,
    mask_shape=None,
    threshold=0.1,
    top_x_features=3,
    field_name="adcode",
    replaceFalseWithNan=True,
    pkl_file_name=None,
):
    """
    @description: 从geojson文件中获取边界mask数据
    @param (str) boundary_json_file: 边界geojson文件路径
    @param (np.array) lats: 纬度坐标
    @param (np.array) lons: 经度坐标
    @param (bool) replaceFalseWithNan: 是否将False替换为NAN
    @return {dict_masks: dict}
    @return {np.array} mask_name: mask的名称
    """
    dir = os.path.dirname(boundary_json_file)
    boundary_file_name = os.path.basename(boundary_json_file)
    boundary_mask_file = (
        os.path.join(dir, f"{boundary_file_name}.pkl")
        if pkl_file_name is None
        else os.path.join(dir, pkl_file_name)
    )
    if os.path.exists(boundary_mask_file):
        with open(boundary_mask_file, "rb") as file:
            dict_masks, mask_name = pickle.load(file)
    else:
        dict_masks = get_all_masks_by_intersection(
            json_file=boundary_json_file,
            grid_polygons=grid_polygons,
            mask_shape=mask_shape,
            threshold=threshold,
            top_x_features=top_x_features,
            replaceFalseWithNan=replaceFalseWithNan,
        )
        mask_name, _, _ = get_mask_with_name_by_intersection(
            json_file=boundary_json_file,
            grid_polygons=grid_polygons,
            mask_shape=mask_shape,
            threshold=threshold,
            top_x_features=top_x_features,
            field_name=field_name,
            replaceFalseWithNan=replaceFalseWithNan,
        )
        masks = (dict_masks, mask_name)
        # 将字典保存到文件
        with open(boundary_mask_file, "wb") as file:
            pickle.dump(masks, file)
    return dict_masks, mask_name


def get_wrf_info(wrf_out_file, variable_name="T2"):
    from wrf import (
        to_np,
        getvar,
        smooth2d,
        get_cartopy,
        cartopy_xlim,
        cartopy_ylim,
        latlon_coords,
        get_basemap,
    )
    import netCDF4 as nc

    dataset = nc.Dataset(wrf_out_file, "r")
    t2 = getvar(dataset, variable_name)
    cart_proj = get_cartopy(t2)
    lats, lons = latlon_coords(t2)
    lons, lats = to_np(lons), to_np(lats)
    xlims, ylims = cartopy_xlim(t2), cartopy_ylim(t2)
    x_coords, y_coords = np.linspace(xlims[0], xlims[1], lons.shape[1]), np.linspace(
        ylims[0], ylims[1], lons.shape[0]
    )
    x, y = np.meshgrid(x_coords, y_coords)
    dx, dy = dataset.DX, dataset.DY
    return x, y, lons, lats, dx, dy, cart_proj


def get_grid_polygons(
    center_x,
    center_y,
    cell_width=None,
    cell_height=None,
    src_proj="epsg:3857",
    dst_proj="epsg:4326",
):
    from pyproj import Proj, Transformer
    from shapely.geometry import Polygon

    """
    @description: 创建包含模型域每个网格四个角的polygon，并进行坐标转换
    @param (np.array) center_x: 每个网格中心点的x坐标（Lambert投影坐标）
    @param (np.array) center_y: 每个网格中心点的y坐标（Lambert投影坐标）
    @param (float) cell_width: 网格宽度
    @param (float) cell_height: 网格高度
    @param (str)或 src_proj: 源投影坐标系，默认为epsg:3857 (Lambert投影坐标系)
    @param (str) dst_proj: 目标投影坐标系，默认为epsg:4326 (经纬度坐标系)
    @return {list} grid_polygons: 包含每个网格四个角的polygon列表
    """
    src = Proj(init=src_proj) if type(src_proj) == str else Proj(src_proj.srs)
    dst = Proj(init=dst_proj)
    grid_polygons = []
    for i in range(len(center_x)):
        lon = center_x[i]
        lat = center_y[i]

        if cell_width is None:
            cell_width = (
                (center_x[i] - center_x[i - 1])
                if i > 0
                else (center_x[i + 1] - center_x[i])
            )
        if cell_height is None:
            cell_height = (
                (center_y[i] - center_y[i - 1])
                if i > 0
                else (center_y[i + 1] - center_y[i])
            )

        # 计算四个角的经纬度坐标
        top_left = (lon - cell_width / 2, lat + cell_height / 2)
        top_right = (lon + cell_width / 2, lat + cell_height / 2)
        bottom_right = (lon + cell_width / 2, lat - cell_height / 2)
        bottom_left = (lon - cell_width / 2, lat - cell_height / 2)

        # 创建网格的polygon
        grid_polygon = Polygon([top_left, top_right, bottom_right, bottom_left])
        grid_polygons.append(grid_polygon)
    try:
        # 定义一个Transformer对象，用于从原始投影转换为目标投影
        transformer = Transformer.from_proj(src, dst)
        # 将每个网格四个角的经纬度坐标转换为目标投影坐标系
        grid_polygons_final = []
        for grid_polygon in tqdm(grid_polygons):
            # 提取四个角的经纬度坐标
            coords = grid_polygon.exterior.coords
            transformed_coords = [
                transformer.transform(lon, lat) for lon, lat in coords
            ]
            # transformed_coords = [transformer.transform(lat, lon) for lon, lat in coords]
            # xy=[(lon, lat) for lat,lon in transformed_coords]
            cell_polygon = Polygon(transformed_coords)
            grid_polygons_final.append(cell_polygon)
    except Exception as e:
        print(e)
        grid_polygons_final = grid_polygons
    return grid_polygons_final


if __name__ == "__main__":

    import pandas as pd

    # 文件路径
    file_path = r"D:\Devin\WetChat Files\WeChat Files\wxid_irdqh3429ls422\FileStorage\File\2024-11\eva.pz.co2.simda.txt"
    # 使用 pandas 读取 CSV 文件
    # df = pd.read_csv(file_path, header=None, names=['date', 'latitude', 'longitude', 'oco_monitor', 'model', 'delta', 'x1', 'x2'], index_col=False)
    # df = pd.read_csv(
    #     file_path,
    #     header=None,
    #     names=[
    #         "date_1",
    #         "latitude",
    #         "longitude",
    #         "oco_monitor",
    #         "model",
    #         "delta",
    #         "x1",
    #         "x2",
    #     ],
    #     index_col=False,
    # )

    json_file = (
        r"D:\Devin\MyTestDemo\PythonDemo\02 CO2\动态反演脚本\guangdong_cities.json"
    )
    # lons = df["longitude"].values
    # lats = df["latitude"].values
    dict_masks = {}
    # with open(json_file, "r", encoding="utf-8") as f:
    #     for i, feature in enumerate(json.load(f)["features"]):
    #         poly = shape(feature["geometry"])
    #         poly = sorted(poly.geoms, key=lambda p: p.area, reverse=True)
    #         poly = prep(MultiPolygon(poly[:3]))
    #         mask = list(
    #             map(lambda x, y: poly.contains(Point(x, y)), tqdm(lons.flat), lats.flat)
    #         )
    #         mask = np.array(mask)
    #         mask = np.where(mask == False, np.nan, mask)
    #         name = (
    #             feature["properties"]["name"]
    #             if "name" in feature["properties"]
    #             else str(i)
    #         )
    #         dict_masks[name] = mask
    # rows = []
    # for mask_name, mask in dict_masks.items():
    #     rows.append(
    #         [
    #             mask_name,
    #             np.nanmean(df["oco_monitor"].values * mask),
    #             np.nanmean(df["model"].values * mask),
    #             np.nansum(mask * df["delta"].values),
    #             np.nansum(mask),
    #         ]
    #     )
    # df_result = pd.DataFrame(
    #     rows,
    #     columns=[
    #         "mask_name",
    #         "oco_monitor_mean",
    #         "model_mean",
    #         "delta_sum",
    #         "mask_sum",
    #     ],
    # )
    # df_result.to_csv(
    #     r"D:\Devin\MyTestDemo\PythonDemo\02 CO2\动态反演脚本\guangdong_cities_mask.csv",
    #     index=False,
    #     encoding="utf-8-sig",
    # )

    from wrf import (
        to_np,
        getvar,
        smooth2d,
        get_cartopy,
        cartopy_xlim,
        cartopy_ylim,
        latlon_coords,
        get_basemap,
    )
    import netCDF4 as nc

    wrf_out_file = r"E:\Docker\CO2\data\wrfinput_d01.nc"
    x, y, lons, lats, dx, dy, cart_proj = get_wrf_info(wrf_out_file, variable_name="T2")

    wrf_file = r"D:\Devin\WetChat Files\WeChat Files\wxid_irdqh3429ls422\FileStorage\File\2024-10\wrfchemi_d01_diunal_01"
    ds = nc.Dataset(wrf_file, "r")
    emissions = ds.variables["E_CO2"][:, 0, :, :]
    import math

    grid_area = get_m2(lons, lats)
    molar_mass = 44
    emission_unit_conversion_factor = molar_mass / math.pow(10, 6)
    daily_emissions = (
        ds.variables["E_CO2"][:, 0, :, :]
        * emission_unit_conversion_factor
        * grid_area
        / math.pow(1000, 2)
        * 31
    )

    grid_polygons = get_grid_polygons(
        x.flatten(),
        y.flatten(),
        cell_width=dx,
        cell_height=dy,
        src_proj=cart_proj,
        dst_proj="epsg:4326",
    )
    boundary_json_file = r"D:\Devin\MyTestDemo\PythonDemo\02 CO2\Guangdong.json"
    boundary_shape_file=r"D:\D地图\广东省\广东省21城市.shp"
    # boundary_json_file = r"E:\Docker\CO2\data\boundary\guangdong_cities.json"

    # dict_masks_intersect, mask_name_intersect = get_boundary_mask_data_by_intersection(
    #     boundary_json_file=boundary_json_file,
    #     grid_polygons=grid_polygons,
    #     mask_shape=lons.shape,
    #     threshold=0,
    #     replaceFalseWithNan=True,
    #     pkl_file_name="gd_cities_intersect_mask.pkl",
    # )

    # mask = get_mask_by_intersection(
    #     json_file=boundary_json_file,
    #     grid_polygons=grid_polygons,
    #     mask_shape=lons.shape,
    #     threshold=None,
    #     replaceFalseWithNan=True,
    # )

    # dict_data = {}
    from esil.map_helper import get_multiple_data, show_maps

    # get_multiple_data(
    #     dict_data,
    #     dataset_name="mask",
    #     variable_name="",
    #     grid_x=lons,
    #     grid_y=lats,
    #     grid_concentration=mask * np.nansum(daily_emissions, axis=0),
    # )
    # fig = show_maps(
    #     dict_data,
    #     unit="",
    #     cmap="jet",
    #     show_lonlat=True,
    #     projection=cart_proj,
    #     boundary_file=r"E:\Docker\CO2\data\boundary\gd_cities.shp",
    #     show_original_grid=True,
    #     is_wrf_out_data=True,
    #     show_grid_line=True,
    #     value_format=".2f",
    #     show_domain_mean=False,
    # )
    # fig.savefig(r'D:\Devin\MyTestDemo\PythonDemo\02 CO2\mask.png')
    # dict_mask = get_all_masks_by_intersection(
    #     json_file=boundary_shape_file,
    #     grid_polygons=grid_polygons,
    #     mask_shape=lons.shape,
    #     threshold=None,
    #     field_name='User'
    #     replaceFalseWithNan=True,
    # )
    
    dict_mask = get_all_masks_by_intersection(
        json_file=boundary_json_file,
        grid_polygons=grid_polygons,
        mask_shape=lons.shape,
        threshold=None,
        replaceFalseWithNan=True,
    )
    
  
    dict_data = {}
    for name, mask in dict_mask.items():
        get_multiple_data(
            dict_data,
            dataset_name=f"{name}",
            variable_name="",
            grid_x=lons,
            grid_y=lats,
            grid_concentration=mask * np.nansum(daily_emissions, axis=0),
        )
    fig = show_maps(
        dict_data,
        unit="",
        cmap="jet",
        show_lonlat=True,
        projection=cart_proj,
        boundary_file=r"E:\Docker\CO2\data\boundary\gd_cities.shp",
        show_original_grid=True,
        font_name="SimHei",
        is_wrf_out_data=True,
        show_grid_line=True,
        value_format=".2f",
        show_domain_mean=False,
    )

    # exit()
    # boundary_json_file='/work/home/pengzhen/PRD9km_2/devin/python_project/code/co2_inversion/data/boundary/guangdong_cities.json'
    dict_mask, masknames = get_boundary_mask_data(boundary_json_file, lats, lons)
    print("done")
    # print(dict_masks1)
    # print(mask_name1)
    # 显示多个地图
