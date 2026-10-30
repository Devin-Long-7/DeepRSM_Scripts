import pyproj
import netCDF4 as nc


def get_proj4string(cmaq_file):
    '''
    根据CMAQ模拟结果获取该文件的投影信息
    :param cmaq_file:
    :return:
    '''
    nc_data = nc.Dataset(cmaq_file)
    center_lon = nc_data.getncattr('XCENT')
    center_lat = nc_data.getncattr('YCENT')
    lat_1= nc_data.getncattr('P_ALP')
    lat_2 = nc_data.getncattr('P_BET')
    proj4_string=''
    # Check conditions and set projection string accordingly
    if center_lat == 40 and center_lon == -97:
        proj4_string = f"+proj=lcc +lat_1={lat_1} +lat_2={lat_2} +lat_0={center_lat} +lon_0={center_lon} +a=6370000.0 +b=6370000.0"
    else:
        proj4_string = f"+x_0=0 +y_0=0 +lat_0={center_lat} +lon_0={center_lon} +lat_1={lat_1} +lat_2={lat_2} +proj=lcc +datum=wgs84 +no_defs"
    return proj4_string


def get_domain_corners_latlon(cmaq_file):
    '''
    根据CMAQ模拟结果获取模型域左下角和右上角的经纬度
    :param cmaq_file:CMAQ模拟结果文件路径
    :return:lon_start,lat_start,lon_end, lat_end
    '''
    nc_data = nc.Dataset(cmaq_file)
    center_lon = nc_data.getncattr('XCENT')
    center_lat = nc_data.getncattr('YCENT')
    lat_1= nc_data.getncattr('P_ALP')
    lat_2 = nc_data.getncattr('P_BET')
    proj4_string=''
    # Check conditions and set projection string accordingly
    if center_lat == 40 and center_lon == -97:
        proj4_string = f"+proj=lcc +lat_1={lat_1} +lat_2={lat_2} +lat_0={center_lat} +lon_0={center_lon} +a=6370000.0 +b=6370000.0"
    else:
        proj4_string = f"+x_0=0 +y_0=0 +lat_0={center_lat} +lon_0={center_lon} +lat_1={lat_1} +lat_2={lat_2} +proj=lcc +ellps=WGS84 +no_defs"
    projection=pyproj.Proj(proj4_string)
    x_orig= nc_data.getncattr('XORIG')
    y_orig = nc_data.getncattr('YORIG')

    x_resolution=nc_data.getncattr('XCELL')
    y_resolution = nc_data.getncattr('YCELL')
    cols= nc_data.getncattr('NCOLS')
    rows = nc_data.getncattr('NROWS')
    x_orig=x_orig+x_resolution/2
    y_orig = y_orig + y_resolution / 2
    x_end=x_orig+cols*x_resolution
    y_end=y_orig+rows*y_resolution
    lon_start,lat_start=projection(x_orig,y_orig, inverse=True)
    lon_end, lat_end = projection(x_end, y_end, inverse=True)
    return (lon_start,lat_start,lon_end, lat_end)



def transform_point(origin_x,origin_y,source_projection,target_projection):
    #投影坐标转换为经纬度坐标
    lon,lat=source_projection(origin_x,origin_y, inverse=True)
    #经纬度坐标转换为第二个投影坐标
    out_x,out_y=target_projection(lon,lat)
    return (out_x,out_y)
def transform_point_2_latlon(origin_x,origin_y,source_projection):
    # 投影坐标转换为经纬度坐标
    lon, lat = source_projection(origin_x, origin_y, inverse=True)
    return (lon, lat)
def transform_point_from_latlon(lon, lat,target_projection):
    # 经纬度坐标转换为第二个投影坐标
    out_x, out_y = target_projection(lon, lat)
    return (out_x, out_y)

def convert_cartopy_projection_2_pyproj(cartopy_projection):
    # 获取该投影对象的proj4字符串
    proj4_string = cartopy_projection.proj4_init
    # 创建对应的pyproj投影对象
    pyproj_projection = pyproj.Proj(proj4_string)
    return pyproj_projection

if __name__=="__main__":
    nc_file= r'/NetcdfReader/Paper preparation scripts/Concentration distribution/cmaq_data/ACONC_2019.1'
    proj4_string=get_proj4string(nc_file)
    lon_start,lat_start,lon_end, lat_end=get_domain_corners_latlon(nc_file)
    print(lon_start,lat_start,lon_end, lat_end)
    # 定义 proj4 字符串
    #proj4_string = '+proj=lcc +lat_1=33 +lat_2=45 +lat_0=40 +lon_0=-97 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'

    # 测试投影转换
    # 例如，转换一个经纬度坐标为投影坐标
   #longitude = -95.5  # 示例经度
    #latitude = 40.2  # 示例纬度

    # 将经纬度坐标转换为投影坐标
    #x, y = projection(longitude, latitude)