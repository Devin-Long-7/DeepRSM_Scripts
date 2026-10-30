'''
Author: Devin
Date: 2024-07-16 16:48:53
LastEditors: Devin
LastEditTime: 2024-07-16 22:44:18
Description: 

Copyright (c) 2024 by Devin, All Rights Reserved. 
'''
import esmpy
from esil.rsm_helper.model_property import model_attribute
import numpy as np
import netCDF4 as nc
from esil.map_helper import get_multiple_data,show_maps

def initialize_grid(lons, lats, grid_data, field_name="CO2"):
    # Create a 2D grid from the model's lon and lat arrays
    sourcegrid = esmpy.Grid(np.array(lons.shape), staggerloc=esmpy.StaggerLoc.CENTER, coord_sys=esmpy.CoordSys.SPH_DEG)
    # Set the coordinates of the grid
    source_lon = sourcegrid.get_coords(0)
    source_lat = sourcegrid.get_coords(1)
    source_lon[...] = lons
    source_lat[...] = lats
    # Create a field on the grid
    sourcefield = esmpy.Field(sourcegrid, name=field_name)
    sourcefield.data[...] = grid_data
    return sourcegrid, sourcefield
    
def regrid(source_file,target_file,source_file_var_name="CO2",target_file_var_name="CO2"):
    
    ds_small = nc.Dataset(target_file, 'r')
    model_small=model_attribute(target_file)
    dest_grid, dest_field=initialize_grid(model_small.lons,model_small.lats,ds_small[target_file_var_name][0,0,:],field_name=target_file_var_name)
        
    #从文件中加载多个 numpy.ndarray 对象
    data = np.load(source_file, allow_pickle=True)#allow_pickle 参数是 True，允许 numpy 加载包含对象数组的文件。但是，当将其设置为 False 时，numpy 将禁止加载对象数组，以防止潜在的安全问题。
    lons_large, lats_large, x_large, y_large, proj_large, CO2_ANT = data['lons'], data['lats'], data['x'], data['y'], data['proj'], data['data']
    source_grid, source_field=initialize_grid(lons_large,lats_large,CO2_ANT[0,:],field_name=source_file_var_name)
    
    regrid = esmpy.Regrid(source_field, dest_field, regrid_method=esmpy.RegridMethod.BILINEAR,  
                     unmapped_action=esmpy.UnmappedAction.IGNORE)
    
    destfield = regrid(source_field, dest_field)
    return destfield,model_small.lons,model_small.lats,model_small.projection 

def regrid(source_lons,source_lats,source_data,target_lons,target_lats,target_data,source_file_var_name="CO2",target_file_var_name="CO2"):
    
    dest_grid, dest_field=initialize_grid(target_lons,target_lats,target_data,field_name=target_file_var_name)
    source_grid, source_field=initialize_grid(source_lons,source_lats,source_data,field_name=source_file_var_name)
    regrid = esmpy.Regrid(source_field, dest_field, regrid_method=esmpy.RegridMethod.BILINEAR,  
                     unmapped_action=esmpy.UnmappedAction.IGNORE)
    
    destfield = regrid(source_field, dest_field)
    return destfield,target_lons,target_lats

if __name__ == "__main__":
    
    file_small=r'E:\CO2\Least_squares_testing\Sources\PW\CCTM_ACONC_GuangDong_2022_2022001_CO2_only.nc'
    file_large=r'wrfinput_d01_data.npz'
    destfield,lons,lats,proj =regrid(file_large,file_small,source_file_var_name="CO2_ANT",target_file_var_name="CO2")    
    dict_data={}
    get_multiple_data(dict_data,"CO2",variable_name="CO2_ANT",grid_x=lons,grid_y=lats,grid_concentration=destfield.data)
    boundary_file='E:\\Docker\\CO2\\data\\boundary\\gd_cities.shp'
    # destfield.save(filename="E:\\Docker\\CO2\\data\\output\\regrid_output.nc", format='netcdf', variable_name='CO2', ignore_discard=False, ignore_expires=False)
    show_maps(dict_data,unit="ppm",show_lonlat=True,show_original_grid=True,projection=proj)
    print("done")