import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm

def plot_ekma_curve(x, y, values, colors_num=10, title='', x_title='VOCs', y_title='NOx', legend_title='O3', cmap='jet',
                    figsize=None, showplot=True):
    '''
    :param x: numpy 1D array
    :param y: numpy 1D array
    :param values: numpy 2D array,shape[len(x), len(y)]
    :param colors_num: 颜色个数
    :param title: 标题，default：''
    :param x_title: x轴标题,default:'VOCs'
    :param y_title: y轴标题,default:'NOx'
    :param legend_title: 图例标题,default:'O3'
    :param cmap: `matplotlib.colors.Colormap` or str or None, default: jet
        If a `.Colormap` instance, it will be returned. Otherwise, the name of
        a colormap known to Matplotlib, which will be resampled by *lut*. The
        value of None, means :rc:`image.cmap`.
    :param figsize: (float, float), default: :rc:`figure.figsize`
        Width, height in inches.
    :param showplot: 是否绘图，默认绘图；False将返回fig,用于保存
    :return: showplot=True，直接绘图，没有返回值。showplot=False,返回图表数据变量，可直接调用fig.savefig(output_file, dpi=600)进行保存图片。
    '''
    # 创建网格点
    # x_grid, NOx_grid = np.meshgrid(x, y)
    # 设定颜色分界点
    cmap_jet = plt.cm.get_cmap(cmap, colors_num)
    ticks = np.linspace(values.min(), values.max(), colors_num + 1)
    # boundaries = np.linspace(values.min(), values.max(), colors_num + 1)
    norm = BoundaryNorm(ticks, cmap_jet.N)
    # 绘制Ekman曲线
    fig = plt.figure(figsize=figsize)
    contour = plt.contourf(x, y, values, levels=ticks, cmap=cmap_jet, norm=norm)
    contour_lines = plt.contour(x, y, values, levels=contour.levels, colors='black',
                                linestyles='solid', linewidths=1)
    plt.clabel(contour_lines, inline=True, fontsize=8)
    cbar = plt.colorbar(contour, label=legend_title, ticks=ticks, boundaries=ticks)
    plt.xlabel(x_title)
    plt.ylabel(y_title)
    plt.title(title)
    # plt.grid(True)
    if showplot:
        # 显示图形
        plt.show()
    else:
        return fig

def plot_multiple_ekma_curves(dict_data,cmap='jet',x_title='VOCs', y_title='NOx',title='',legend_title='O3',colors_num=10,panel_layout=None,
                             show_minmax=True,fig_size=None,showplot=True,value_format=None,sharex=True,sharey=True,
                             need_interpolation=False,interpolation_number=100,interpolation_method='kriging-gaussian',default_min_value=None,default_max_value=None,show_sup_title=False,font_name=None):
    '''
    :param dict_data: dict, key: title, value: [x,y,z]
    :param cmap: `matplotlib.colors.Colormap` or str or None, default: jet
        If a `.Colormap` instance, it will be returned. Otherwise, the name of
        a colormap known to Matplotlib, which will be resampled by *lut*. The
        value of None, means :rc:`image.cmap`.
    :param x_title: x轴标题,default:'VOCs'
    :param y_title: y轴标题,default:'NOx'
    :param title: 标题，default：''
    :param legend_title: 图例标题,default:'O3'
    :param panel_layout: tuple, default:None
        (rows, cols)
    :param show_minmax: 是否显示最大最小值
    :param fig_size: (float, float), default: :rc:`figure.figsize`
        Width, height in inches.
    :param showplot: 是否绘图，默认绘图；False将返回fig,用于保存
    :param value_format: 数值显示格式，默认None，显示原始数值;示例'.2f'：保留两位小数
    ：param sharex: 是否共享x轴，默认True
    ：param sharey: 是否共享y轴，默认True
    ：param need_interpolation: 是否需要插值，默认False;如果x,y为1D数组，z为2D数组，则需要插值
    ：param interpolation_number: 插值点个数，默认100
    ：param interpolation_method: 插值方法，默认'kriging-gaussian'
    ：param default_min_value: 默认最小值，默认None
    ：param default_max_value: 默认最大值，默认None
    ：param show_sup_title: 是否显示上部标题，默认False
    :return: showplot=True，直接绘图。showplot=False,返回图表数据变量，可直接调用fig.savefig(output_file, dpi=600)进行保存图片。    
    '''
    from esil.panelayout_helper import get_layout_col_row
    import string
    
    if font_name!=None:
        # 设置中文字体为系统中已安装的字体，如SimSun（宋体）、SimHei（黑体）
        plt.rcParams['font.sans-serif'] = [font_name]  # 设置中文字体为宋体 
        plt.rcParams['axes.unicode_minus'] = False  # 用于正常显示负号   
    data_types=dict_data.keys()
    plot_count=len(data_types)  
    plot_columns,plot_rows=get_layout_col_row(plot_count, panel_layout=panel_layout)   
    width,height=plot_columns*4,plot_rows*4+0.2   
    if fig_size is not None:
        width,height=fig_size
    label_list = ["("+i+")" for i in list(string.ascii_lowercase)[:plot_count]]    
    fig, axs = plt.subplots(plot_rows, plot_columns, figsize=(width,height),sharex=sharex, sharey=sharey) 
    if show_sup_title==False and plot_rows>1:
        y_titles = [y_title] *plot_rows
        for ax, row in zip(axs[:,0], y_titles):
            ax.set_ylabel(row, rotation=90, size=8)

    for ax,data_type,fig_label in zip(axs.flat,data_types,label_list):
        x,y,z=dict_data[data_type]
        if x.ndim==1 and y.ndim==1 and z.ndim==2:
            need_interpolation=True       
        if need_interpolation:
            from esil.interpolation_helper import interpolate
            grid_x, grid_y, values = interpolate(x=x, y=y, data=z, interpolation_number=interpolation_number, method=interpolation_method)
        else:
            grid_x, grid_y, values=x,y,z
        ax.text(0.5, 1.07, fig_label+data_type, transform=ax.transAxes, fontsize=12, fontweight='bold',ha='center')
        # 设定颜色分界点
        cmap_jet = plt.cm.get_cmap(cmap, colors_num)
        ticks = np.linspace(values.min(), values.max(), colors_num + 1)
        ticks = np.round(ticks, 1) 
        norm = BoundaryNorm(ticks, cmap_jet.N)
        vmax = np.nanpercentile(values,99.5) if default_max_value == None else default_max_value #np.nanmax(grid_concentration)
        vmin =  np.nanpercentile(values,0.5)  if default_min_value == None else default_min_value#np.nanmin(grid_concentration)
        # 绘制Ekma曲线
        contour = ax.contourf(grid_x, grid_y, values, levels=ticks, cmap=cmap_jet, vmin=vmin, vmax=vmax, norm=norm)              
        contour_lines = ax.contour(grid_x, grid_y, values, levels=contour.levels, colors='black',
                                    linestyles='solid', linewidths=1)
        if value_format is not None:
            fmt=f"%{value_format}"
        else:
            fmt=None
        ax.clabel(contour_lines, inline=True, fontsize=10,fmt=fmt)#,fmt=value_format
        # ax.text(0.2, 0.15, fig_label+data_type, transform=ax.transAxes,fontsize=8, fontweight='bold', va='top')
        # 设置y轴范围
        x_min,x_max=np.min(grid_x),np.max(grid_x)
        ax.set_ylim(x_min,x_max)             
        # 设置 x 和 y 轴的 ticks 范围
        x_ticks,y_ticks = [],[]      
        interval =0.25
        x_ticks =np.arange(x_min, x_max+interval , interval)
        y_ticks=x_ticks
        ax.set_xticks(x_ticks)  # 设置 x 轴的 ticks 范围
        ax.set_yticks(y_ticks)  # 设置 y 轴的 ticks 范围
        if fig_label == "(a)":
            ax.set_ylabel(y_title)  # 设置 y 轴标签
        if show_minmax:      
            min_value, max_value,mean_value=np.min(values),np.max(values),np.mean(values)            
            if value_format is None:   
                value_format=".1e" if max_value>1e3 else ".2f" if max_value>1 else ".3f" if max_value>0.1 else ".4f" if max_value>0.01 else ".5f"              
            min_max_info='Min = {}, Max = {}, Mean = {}'.format(format(min_value, value_format),format(max_value, value_format),format(mean_value, value_format))
            ax.set_xlabel(f"{'' if show_sup_title else  x_title}\n"+min_max_info)
        else:
            ax.set_xlabel(f"{'' if show_sup_title else  x_title}")
        # 添加颜色条
        cbar = plt.colorbar(contour, label=f'{legend_title}', ax=ax, orientation='vertical', shrink=0.7,ticks=ticks)  # 设置图例高度与图像高度相同, orientation='vertical', shrink=0.7   
        # cbar = plt.colorbar(contour, fraction=0.02, pad=0.04, label=f'{legend_title}', ax=ax, orientation='vertical', shrink=0.7,ticks=ticks)  # 设置图例高度与图像高度相同, orientation='vertical', shrink=0.7   
    if show_sup_title:
        fig.supxlabel(f'{x_title}',y=0.08,fontsize=15,fontweight="normal")#标签相对于图形的x位置，范围为0到1，默认为0.01，距离底部的距离为0.01，表示留出一小段空白。1表示距离顶部的距离为0
        fig.supylabel(f'{y_title}',x=0.08,fontsize=15,fontweight="normal")  
    plt.subplots_adjust(hspace=0.3)  # 调整子图之间的垂直间距

    if showplot:       
        # 显示图形
        plt.show()   
    return fig   