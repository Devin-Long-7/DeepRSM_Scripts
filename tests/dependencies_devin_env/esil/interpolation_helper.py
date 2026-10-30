import numpy as np


def inverse_distance_weighting(x, y, z, xi, yi, power=2):
    """
    @description:反距离平方 IDW 插值计算
    x,y为原数组一维长度
    z的长度是len(x)*len(y) 二维数组
    xi 为插值后二维数组，即meshgrid后
    yi 为插值后二维数组，即meshgrid后
    """

    from scipy.spatial.distance import cdist

    xx, yy = np.meshgrid(x, y)
    xy = np.column_stack([xx.flatten(), yy.flatten()])
    # xi, yi = np.meshgrid(xi, yi)
    xyi = np.column_stack([xi.flatten(), yi.flatten()])

    distances = cdist(xy, xyi)
    weights = 1 / (distances + 1e-10) ** power  # 避免除以零，加上一个很小的值
    weights /= np.sum(weights, axis=0)  # 在列方向上归一化权重

    # 将 z 展开成一维数组，方便后续计算
    z_flat = z.flatten()

    # 通过对每个点的权重进行加权求和得到插值结果
    zi = np.dot(weights.T, z_flat)
    zi = zi.reshape(xi.shape)
    return zi


def interpolate(x, y, data, interpolation_number, method="griddata-cubic"):
    """
    @description:对数据进行插值，返回插值后x,y坐标数组及插值结果

    Args:
        x (1D array): x坐标一维数组
        y (1D array): y坐标一维数组
        data (2D array):需要插值的数据，二维数组,长度x*y，其中x,y需要通过np.meshgrid方法将其变为二维数组，然后再用flatten将其转为一维数组，此时x和y的长度变为原始x*y的长度
            lon, lat = np.meshgrid(x, y)
            x = lon.flatten()
            y = lat.flatten()
        interpolation_number:插值个数，大于x和y的最大长度，否则取x和y中的最大长度
        method:插值方法;
                1."griddata-cubic":三次样条插值。使用三次样条函数在数据点之间进行插值。，默认采用此方法
                2."griddata-linear":线性插值。在三角网格中使用线性插值法计算点的值。
                3."griddata-cubic":最近邻插值。根据最近邻点的值来估计目标点的值。
                4."kriging-linear": variogram_models.linear_variogram_model,
                5."kriging-power": variogram_models.power_variogram_model,
                6."kriging-gaussian": variogram_models.gaussian_variogram_model,
                7."kriging-spherical": variogram_models.spherical_variogram_model,
                8."kriging-exponential": variogram_models.exponential_variogram_model,
                9."kriging-hole-effect": variogram_models.hole_effect_variogram_model,
                10."idw-power"：反距离权重方法，power是具体方次，默认是反距离平方，即idw-2；它使用距离的平方的倒数作为权重来估计未知位置的值。这种方法中，较远的点权重较小，而较近的点权重较大
    Returns:
        grid_x: 插值后x坐标:list of ndarrays
        grid_y:插值后y坐标:list of ndarrays
        grid_data:插值后data:list of ndarrays
    """

    interpolated_result = []
    ori_grid_x, ori_grid_y = np.meshgrid(x, y)  # 对原始数据中lon,lat两个维度进行网格化
    # 获取插值个数
    num = max(len(x), len(y))
    if interpolation_number < num:
        interpolation_number = num
    # num = num + interpolation_number
    interpolated_x = np.linspace(x.min(), x.max(), interpolation_number)
    interpolated_y = np.linspace(y.min(), y.max(), interpolation_number)
    grid_x, grid_y = np.meshgrid(interpolated_x, interpolated_y)

    if "griddata" in method:
        from scipy.interpolate import griddata

        sub_method = method.split("-")[-1]  # 取最后一个
        interpolated_result = griddata(
            (ori_grid_x.flatten(), ori_grid_y.flatten()),
            data.flatten(),
            (grid_x, grid_y),
            method=sub_method,
        )
    elif "kriging" in method:
        from pykrige.ok import OrdinaryKriging

        sub_method = method.split("-")[-1]  # 取最后一个
        # 创建一个克里金插值对象
        ok = OrdinaryKriging(
            ori_grid_x.flatten(),
            ori_grid_y.flatten(),
            data.flatten(),
            variogram_model=sub_method,
            verbose=False,
            enable_plotting=False,
        )
        interpolated_result, ss = ok.execute("grid", interpolated_x, interpolated_y)
    elif "idw" in method:
        power = (int)(method.split("-")[-1])  # 取最后一个
        # 进行反距离平方 IDW 插值
        interpolated_result = inverse_distance_weighting(
            x, y, data, grid_x, grid_y, power=power
        )
    else:
        print(f"Failed to found this method:{method}")
    return (grid_x, grid_y, interpolated_result)


def smooth_processing_data(data, method="gaussian", sigma=1, size=3):
    """
    对数据进行平滑处理

    Args:
        data (2D array):需要平滑处理的数据，二维数组
        method:平滑方法;
                1."gaussian":高斯滤波
                2."uniform":均值滤波
                3."median":中值滤波
        sigma:高斯滤波的标准差，用于控制平滑程度;sigma 值越大，平滑效果越明显，但也可能导致数据的细节丢失
        小 sigma 值：适用于需要保留更多细节的情况。常见取值范围是 0.5 到 1.5。
        中等 sigma 值：适用于需要适度平滑的情况。常见取值范围是 1.5 到 3。
        大 sigma 值：适用于需要强烈平滑的情况。常见取值范围是 3 到 5 或更大
        size:均值滤波和中值滤波的窗口大小，用于控制平滑程度;窗口大小越大，平滑效果越明显，但也可能导致数据的细节丢失
    调用示例：smooth_processing_data(data,method='gaussian',sigma=1,size=3)
    Returns:
        smoothed_data:平滑后的数据
    """
    if "gaussian" in method:
        from scipy.ndimage import gaussian_filter

        smoothed_data = gaussian_filter(data, sigma=sigma)
    elif "uniform" in method:
        from scipy.ndimage import uniform_filter

        smoothed_data = uniform_filter(data, size=size)
    elif "median" in method:
        from scipy.ndimage import median_filter

        smoothed_data = median_filter(data, size=size)
    else:
        print(f"Failed to found this method:{method}")
    return smoothed_data


if __name__ == "__main__":
    from map_helper import show_single_map
    from netcdf_helper import get_extent_data

    nc_file = r"D:\Project\G广东省主要温室气体排放反演与大气污染精准溯源服务项目\090数据\ENKF 全球反演结果\NJU.GLOBAL.FLUX.1x1.202201.nc"
    variable_name = "bio_prio"
    extent = [70.25, 136.25, 4.75, 55.25]
    data, unit = get_extent_data(nc_file, variable_name)
    # data=get_extent_data(nc_file,variable_name,extent=extent)
    x = data.lon.values
    y = data.lat.values
    data = data.values
    grid_x, grid_y = np.meshgrid(x, y)

    # data[:] = np.nan
    show_single_map(
        grid_x,
        grid_y,
        grid_concentration=data,
        title=variable_name + " origin data",
        cmap="gray",
    )

    # grid_x,grid_y,interpolated_result=interpolate(x,y,data,100)
    # plotmap(grid_x,grid_y,grid_concentration=interpolated_result,title=variable_name+ " with griddata-cubic")
    # #grid_x, grid_y, interpolated_result = interpolate(x=x, y=y, data=data,interpolation_number= 100,method='griddata-linear')
    # grid_x, grid_y, interpolated_result = interpolate(x=x, y=y, data=data,interpolation_number= 100,method='kriging-gaussian')
    # plotmap(grid_x, grid_y, grid_concentration=interpolated_result, title=variable_name + " with kriging-gaussian")
    # grid_x, grid_y, interpolated_result = interpolate(x=x, y=y, data=data, interpolation_number=100, method='idw-2')
    # plotmap(grid_x, grid_y, grid_concentration=interpolated_result, title=variable_name+" with idw-2")
    print("success")
