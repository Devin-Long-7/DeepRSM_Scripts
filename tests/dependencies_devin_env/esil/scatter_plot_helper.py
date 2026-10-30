import numpy as np
import matplotlib.pyplot as plt
import cmaps
import math
from scipy import stats
from sklearn.metrics import r2_score,mean_squared_error
from esil.panelayout_helper import get_layout_col_row
import string
from mpl_toolkits.axes_grid1 import ImageGrid
from scipy.interpolate import interp2d

def normalize_and_scale(data, scale_value):
    '''
    @description: 用于对数组data进行线性缩放的函数。它的目的是将输入数组 data 的值调整到一个新的范围 [0, scale_value]
    @param {data}: ndarray 数组，不能是数据框，数据框的话，需要调用to_numpy()转为数组
    @param {scale_value}: 缩放范围，即将数据归一化为0~scale_value之间的数
    @return {data}: 归一化后的数据
    '''
    min_value = np.min(data)
    normalized_data = data - min_value
    max_value = np.max(normalized_data)
    scaled_data = normalized_data / max_value * scale_value
    return scaled_data

def compute_density_percentages(x, y, fiSize):
    '''
    @description:将二维数据（x 和 y）进行归一化缩放，并计算每个点在一个网格中的密度。然后，它计算每个点的累积百分比
    '''
    denSta = np.zeros((fiSize, fiSize))#模拟了x*y=fiSize*fiSize的格子，待会要用来放统计每个格子里有几个点的结果
    xlength = len(x)
    xdenSta,ydenSta = normalize_and_scale(x, fiSize),normalize_and_scale(y, fiSize)  
    for count in range(xlength):
        m = int(xdenSta[count])
        n = int(ydenSta[count])
        if n >= fiSize:
            n = fiSize-1
        if m >= fiSize:
            m = fiSize-1
        denSta[m, n] = denSta[m, n] + 1
    z = np.zeros((x.shape[0], 1))
    for count in range(xlength):
        m = int(xdenSta[count])
        n = int(ydenSta[count])
        if n >= fiSize:
            n = fiSize-1
        if m >= fiSize:
            m = fiSize-1
        z[count, 0] = denSta[m, n]
    int_denSta=denSta.flatten().astype(int)
    #计算每个元素出现的频率，unique_elements为元素，tabulateDensta为元素对应下的出现频率
    unique_elements, tabulateDensta= np.unique(int_denSta, return_counts=True)
    #准备装累积百分比列表的矩阵
    percent = np.zeros(tabulateDensta.shape)
    percent[0] = 0 #把0的百分比归0
    sumPoint = x.shape[0]
    #装累积百分比查询表
    for count in range(1, tabulateDensta.shape[0]):
        percent[count] = percent[count - 1] + (unique_elements[count] * tabulateDensta[count] / sumPoint)
#傻瓜遍历找到原z值对应的百分比，更新z
    for count in range(z.shape[0]):
        for coutFindPercent in range(unique_elements.shape[0]):
            if z[count, 0] == unique_elements[coutFindPercent]:
                z[count, 0] = percent[coutFindPercent]
                break
    return z


def compute_density_percentage(x_coords, y_coords, grid_size):
    # Initialize a grid to count the number of points in each cell
    density_grid = np.zeros((grid_size, grid_size))
    num_points = len(x_coords)
    
    # Normalize and scale the coordinates to fit within the grid
    x_scaled = normalize_and_scale(x_coords, grid_size)
    y_scaled = normalize_and_scale(y_coords, grid_size)

    # Populate the density grid with point counts
    for i in range(num_points):
        x_index = int(x_scaled[i])
        y_index = int(y_scaled[i])
        x_index = min(x_index, grid_size - 1)
        y_index = min(y_index, grid_size - 1)
        density_grid[x_index, y_index] += 1

    # Initialize an array to store the density value for each point
    point_densities = np.zeros((num_points, 1))
    for i in range(num_points):
        x_index = int(x_scaled[i])
        y_index = int(y_scaled[i])
        x_index = min(x_index, grid_size - 1)
        y_index = min(y_index, grid_size - 1)
        point_densities[i, 0] = density_grid[x_index, y_index]

    # Flatten the density grid and calculate frequency of each density value
    flattened_density = density_grid.flatten().astype(int)
    unique_densities, density_counts = np.unique(flattened_density, return_counts=True)

    # Calculate cumulative percentages for each unique density value
    cumulative_percentages = np.zeros(density_counts.shape)
    cumulative_percentages[0] = 0  # Set percentage for zero density to 0
    total_points = num_points
    for i in range(1, density_counts.shape[0]):
        cumulative_percentages[i] = cumulative_percentages[i - 1] + (unique_densities[i] * density_counts[i] / total_points)

    # Update point densities with cumulative percentages
    for i in range(num_points):
        for j in range(unique_densities.shape[0]):
            if point_densities[i, 0] == unique_densities[j]:
                point_densities[i, 0] = cumulative_percentages[j]
                break

    return point_densities

def draw_density_plot(x, y, titleName, xName, yName, nbins=100,showMNE=True):
    # x = data[:, 0]  # RSM
    # y = data[:, 1]  # CMAQ

    denSta = np.zeros((nbins, nbins))#这里模拟了x*y=fiSize*fiSize的格子，待会要用来放统计每个格子里有几个点的结果
    xlength = len(x)
    xdenSta = normalize_and_scale(x, nbins)
    ydenSta = normalize_and_scale(y, nbins)

    for count in range(xlength):
        m = int(xdenSta[count])
        n = int(ydenSta[count])
        if n >= nbins:
            n = nbins-1
        if m >= nbins:
            m = nbins-1
        denSta[m, n] = denSta[m, n] + 1

    z = np.zeros((x.shape[0], 1))
    for count in range(xlength):
        m = int(xdenSta[count])
        n = int(ydenSta[count])
        if n >= nbins:
            n = nbins-1
        if m >= nbins:
            m = nbins-1
        z[count, 0] = denSta[m, n]

    int_denSta=denSta.flatten().astype(int)
    #tabulateDensta = np.bincount(int_denSta)
    #计算每个元素出现的频率，unique_elements为元素，tabulateDensta为元素对应下的出现频率
    unique_elements, tabulateDensta= np.unique(int_denSta, return_counts=True)
    #准备装累积百分比列表的矩阵
    percent = np.zeros(tabulateDensta.shape)
    percent[0] = 0 #把0的百分比归0

    sumPoint = x.shape[0]
    #unique_tabulateDensta = np.unique(int_denSta)

    #装累积百分比查询表
    for count in range(1, tabulateDensta.shape[0]):
        percent[count] = percent[count - 1] + (unique_elements[count] * tabulateDensta[count] / sumPoint)
#傻瓜遍历找到原z值对应的百分比，更新z
    for count in range(z.shape[0]):
        for coutFindPercent in range(unique_elements.shape[0]):
            if z[count, 0] == unique_elements[coutFindPercent]:
                z[count, 0] = percent[coutFindPercent]
                break

    fig = plt.figure(figsize=(11.5, 9.8))
    plt.scatter(y, x, s=26, c=z, marker='s', cmap='jet')#这里调换了一下顺序，使得x轴表示的是CMAQ，y轴表示的是RSM
    #拟合直线 + 拟合评价
    minAll = np.floor(np.min([np.min(x), np.min(y)]) / 20) * 20
    maxAll = (np.floor(np.max([np.max(x), np.max(y)]) / 20) + 1) * 20
    #2点确定一条直线 （参考线）
    plt.plot([minAll, maxAll], [minAll, maxAll], 'b-.')
    if np.min([np.min(x), np.min(y)]) < 0:
        plt.axhline(y=0, color='k', linestyle='--')
        plt.axvline(x=0, color='k', linestyle='--')
    #2点确定一条直线 (拟合线)
    PolyfitResult = np.polyfit(x, y, 1)
    plt.plot([minAll, maxAll], [PolyfitResult[0] * minAll + PolyfitResult[1], PolyfitResult[0] * maxAll + PolyfitResult[1]], 'r-')

    #评价拟合质量
    N = x.shape[0]
    R2 = 1 - np.sum((PolyfitResult[0] * x + PolyfitResult[1] - y) ** 2) / np.sum((y - np.mean(y)) ** 2)

    Ec = np.abs(x - y) / np.abs(y)
    ETc = Ec[Ec <= 1000]
    Fc = np.abs(x - y) / np.abs(x + y)
    FTc = Fc[Fc <= 1000]

    MNE = np.sum(ETc) / (N) * 100
    MFE = np.sum(FTc) / (N) * 100
    RMSE = np.sqrt(np.mean((y - x) ** 2))#计算均方根误差
    MAE = np.mean(np.abs(y - x))

    MaxNE = np.sort(ETc)* 100
    MaxNE_95 =np.percentile(MaxNE, 95) #percentileofscore(MaxNE, 95)
    MaxFE = np.sort(FTc)* 100
    MaxFE_95 =np.percentile(MaxFE, 95)# percentileofscore(MaxFE, 95)

    plt.xlabel(xName, fontname='Times New Roman', fontweight='bold', fontsize=10)
    plt.ylabel(yName, fontname='Times New Roman', fontweight='bold', fontsize=10)
    plt.title(titleName, fontname='Times New Roman', fontweight='bold', fontsize=10)
    str = ['Y = {:0.4f} + {:0.4f}X'.format(PolyfitResult[1], PolyfitResult[0]),
           'R^2 = {:0.4f}'.format(R2),
           'NME = {:0.2f}%'.format(MNE),
           '95th MaxNE = {:0.2f}%'.format(MaxNE_95),
           'RMSE = {:0.4f}'.format(RMSE),
           'MAE = {:0.4f}'.format(MAE)]
    if not showMNE:
        str = ['Y = {:0.4f} + {:0.4f}X'.format(PolyfitResult[1], PolyfitResult[0]),
               'R^2 = {:0.4f}'.format(R2),
               'RMSE = {:0.4f}'.format(RMSE),
               'MAE = {:0.4f}'.format(MAE)]
    plt.text(0.04, 0.95, '\n'.join(str), fontname='Times New Roman', verticalalignment='top', horizontalalignment='left', fontweight='bold',
             fontsize=10,transform=plt.gca().transAxes)

    plt.xlim(minAll, maxAll)#设置x轴的数据显示范围
    plt.ylim(minAll, maxAll)#设置y轴的数据显示范围
    plt.xticks(np.arange(minAll, maxAll, 10))
    plt.yticks(np.arange(minAll, maxAll, 10))
    plt.tight_layout()

    #plt.colorbar(label='Percent of data point', fontweight='bold', fontsize=35)
    cbar = plt.colorbar(label='Percent of data point', orientation='vertical')
    # Set font properties for the colorbar label
    #cbar.ax.yaxis.label.set_font_properties({'weight': 'bold', 'size': 35})
    cbar.ax.yaxis.label.set_family('Times New Roman')
    cbar.ax.yaxis.label.set_fontweight('bold')
    cbar.ax.yaxis.label.set_fontsize(14)
    # Set the locator and formatter for the colorbar
    from matplotlib.ticker import MultipleLocator, FormatStrFormatter
    # 方法1：Set the ticks for the colorbar
    #ticks=np.arange(0, 1.05, 0.1)# Set the interval between ticks
    #cbar.set_ticks(ticks)  # Set the desired ticks
    cbar.locator = MultipleLocator(0.1)  # Set the interval between ticks
    cbar.update_ticks()
    #方法2
    '''
    cbar.locator = MultipleLocator(0.1)  # Set the interval between ticks
    cbar.update_ticks()
    # Add 0 as a tick
    ticks = cbar.get_ticks().tolist()
    if 0 not in ticks:
        ticks.append(0)
        cbar.set_ticks(sorted(ticks))
    '''
    plt.box(True)
    #plt.axis('normal')
    plt.axis('auto')
    #plt.show()
    #plt.pause(2)#加上plt.pause(0.001)，这样程序就会暂停执行一段极短的时间，然后继续执行后面的代码，而绘图界面仍然保持打开状态。
    # 关闭窗口
    #plt.gcf().canvas.mpl_disconnect(plt.gcf().canvas.manager.key_press_handler_id)
    return (RMSE, MAE, fig, MNE, MaxNE_95, R2)

def draw_density_plot_via_hist2d(x, y, titleName, xName="Values", yName="Estimated Values", nbins=150,cmap='jet', density=True):
    
    # 计算统计变量
    slope, intercept, r_value, p_value, std_err = stats.linregress(x,y)
    rmse = np.sqrt(mean_squared_error(x,y))
    r2=r2_score(x,y)    
    normalized_bias = (x - y) / y   * 100
    normalized_bias_ordered = np.sort(normalized_bias)
    mean_normalized_bias =np.mean(normalized_bias)#「每个单点准不准」用 MNB，比如网格浓度
    max_normalized_bias_95 =np.percentile(normalized_bias_ordered, 95) 
    nmb = (y - x).sum() / x.sum() * 100 #关心「整体总量、总和准不准」用 NMB,比如排放总量
    H, xedges, yedges = np.histogram2d(x, y, bins=nbins,density=density)
    # H needs to be rotated and flipped
    H = np.rot90(H)
    H = np.flipud(H)
    # Mask zeros
    Hmasked = np.ma.masked_where(H==0,H) # Mask pixels with a value of zero
    #开始绘图
    fig,ax = plt.subplots(figsize=(8,8),facecolor="w")
    density_scatter = ax.pcolormesh(xedges, yedges, Hmasked, cmap=cmap,label="Data")
    linreg = ax.plot(x, intercept + slope*x, 'r', label='Fitted Line')

    colorbar = fig.colorbar(density_scatter,aspect=17,label="Density of Points")
    colorbar.ax.tick_params(left=True,direction="in",width=.4,labelsize=10)
    colorbar.ax.tick_params(which="minor",right=False)
    colorbar.outline.set_linewidth(.4)

    # 添加文本信息
    # fontdict = {"size":14,"fontstyle":"italic","weight":"bold"}
    intercept_symbol="+" if intercept>0 else "-"
    str = [f"$y = {slope:.2f}x {intercept_symbol} {intercept:.3f}$",#$ 符号是 LaTeX 数学模式的定界符，用于标识一段文本应当被解释为数学公式;$...$ 表示行内数学公式
           f'$R^2={r2:.2f}$',
           f'$MNB = {mean_normalized_bias:.2f}\\%$',
        #    f'$NMB = {nmb:.2f}\\%$',
           f'$RMSE = {rmse:.2f}$'
       ]
    ax.text(0.04, 0.95, '\n'.join(str), fontname='Times New Roman', verticalalignment='top', horizontalalignment='left', fontweight='bold',
             fontsize=10,transform=ax.transAxes)
  
    # ax.text(0.05,5.8,r'$y=$'+str(round(slope,2))+'$x$'+ str(round(intercept,3)),
    #         fontdict=fontdict)
    ax.set_xlabel(xName)
    ax.set_ylabel(yName)
    ax.set_title(titleName, fontname='Times New Roman', fontweight='bold', fontsize=10)
    min=np.floor(np.min([np.min(x)*0.95, np.min(y)*0.95]))#设置x轴和y轴的显示范围，使得图中的点能够更好地分布在图中，避免点过于集中在某个区域或者过于分散在整个图中。通过将最小值乘以0.95，可以将显示范围稍微扩大一些，以确保所有的点都能够被包含在图中。
    max=np.ceil(np.max([np.max(x)*1.05, np.max(y)*1.05]))
    ax.set_xlim(min, max)
    ax.set_ylim(min, max)
    ax.plot([min, max], [min, max], 'k-')
    ax.legend(loc="lower right",frameon=False,labelspacing=.4,handletextpad=.5,fontsize=10)
    plt.show()
    return fig,rmse,r_value,mean_normalized_bias,max_normalized_bias_95

def draw_density_plot_via_gaussian_kde(x, y, titleName, xName="Values", yName="Estimated Values", cmap='jet'):
    #TODO：未经测试
    from scipy.stats import gaussian_kde
    # 计算统计变量
    slope, intercept, r_value, p_value, std_err = stats.linregress(x,y)
    rmse = np.sqrt(mean_squared_error(x,y))
    r2=r2_score(x,y)    
    normalized_bias = (x - y) / y   * 100
    normalized_bias_ordered = np.sort(normalized_bias)
    mean_normalized_bias =np.mean(normalized_bias)
    max_normalized_bias_95 =np.percentile(normalized_bias_ordered, 95) 
    
    # Calculate point density
    xy = np.vstack([x, y])
    z = gaussian_kde(xy)(xy)
    # Sort points by density
    idx = z.argsort()
    x1, y1, z1 = x[idx], y[idx], z[idx]
    max_x_value=np.max(np.abs(np.min(x)),np.abs(np.max(x)))   
    #绘制最佳拟合线
    best_line_x = np.linspace(-max_x_value,max_x_value)
    best_line_y=best_line_x
    fig,ax = plt.subplots(figsize=(4,3.5),dpi=100,facecolor="w")
    gass_desity = ax.scatter(x, y,edgecolors = 'none',c = z,s =6,marker="s",cmap=cmaps.jet)
    bestline = ax.plot(best_line_x,best_line_y,color='k',linewidth=1,linestyle='-',label="1:1 Line")
    linreg = ax.plot(x, intercept + slope*x, 'r', label='Fitted Line')

    colorbar = fig.colorbar(gass_desity,aspect=17,label="Density of Points")
    colorbar.ax.tick_params(left=True,direction="in",width=.4,labelsize=10)
    colorbar.ax.tick_params(which="minor",right=True)
    colorbar.outline.set_linewidth(.4)
    # 添加文本信息
    fontdict = {"size":14,"fontstyle":"italic","weight":"bold"}
    ax.text(-5,7.5,r'$R=$'+str(round(r_value,2)),fontdict=fontdict)
    ax.text(-5,5.8,r'$y=$'+str(round(slope,2))+'$x$'+ str(round(intercept,3)),
            fontdict=fontdict)
    ax.set_xlabel(xName)
    ax.set_ylabel(yName)
    ax.legend(loc="lower right",frameon=False,labelspacing=.4,handletextpad=.5,fontsize=10)
    plt.show()
    return fig,rmse,r_value,mean_normalized_bias,max_normalized_bias_95

def draw_multiple_density_plot_with_hist2d(dict_data, xName="True Values", yName="Estimated Values", cmap='jet',panel_layout=None,density=True,nbins=150,show_plot=False):
    '''
    @description: 绘制多子图相关性散点图
    @param {dict_data}: 数据字典dict,包含了x和y的数据,数据格式为{data_type:{"x":x,"y":y}}
    '''
    plot_count=len(dict_data)
    plot_columns,plot_rows=get_layout_col_row(plot_count, panel_layout=panel_layout)   
    width,height=plot_columns*3,plot_rows*3+0.2
    fig = plt.figure(figsize=(width,height))  
    label_list = ["("+i+")" for i in list(string.ascii_lowercase)[:plot_count]]

    grid = ImageGrid(fig, 111,  # similar to subplot(111)
                    nrows_ncols=(plot_rows, plot_columns),  # creates 2x2 grid of axes
                    axes_pad=0.15,  # pad between axes in inch.
                    cbar_mode="single",
                    cbar_location="right")  
    data_types=dict_data.keys() 
    temp=np.array([[np.min(dict_data[data_type]["x"]),np.max(dict_data[data_type]["x"]),np.min(dict_data[data_type]["y"]),np.max(dict_data[data_type]["y"])]for data_type in data_types])
    min_x_value,max_x_value=np.min(temp),np.max(temp)
    for data_type,ax,label in zip(data_types,grid,label_list):        
        x = dict_data[data_type]["x"]
        y = dict_data[data_type]["y"]  
        # x = changex(x_origin, 100)
        # y = changex(y_origin, 100)    
        # 计算所需指标
        slope, intercept, r_value, p_value, std_err = stats.linregress(x,y)
        rmse = np.sqrt(mean_squared_error(x,y))
        # min_x_value,max_x_value=np.min(x),np.max(x)   
        min_y_value,max_y_value=np.min(y),np.max(y)   
        #绘制最佳拟合线
        best_line_x = np.linspace(min_x_value,max_x_value)
        best_line_y=best_line_x     
        # import matplotlib.colors as mcolors
        # # 设置归一化
        # norm = mcolors.Normalize(vmin=0, vmax=1)
        hist2d = ax.hist2d(x=x,y=y,bins=nbins,cmap=cmap,cmin=.0001,density=density)#cmin指定了颜色映射的最小值。小于这个值的计数或密度将被忽略，不会被绘制。图对象中其他部分被纯色填充. norm=norm
              
        ax.plot(best_line_x,best_line_y,color='k',linewidth=.8,alpha=.8,
                        linestyle='-',zorder=-1)
        ax.plot(x, intercept + slope*x, 'r',linewidth=.8)
        ax.grid(False)
        
        # 添加文本信息
        interval_x =round(float((max_x_value - min_x_value) / 5),2)
        interval_y =round(float((max_y_value - min_y_value) / 5),2)
        start_x=min_x_value+interval_x*0.5
        start_y=max_x_value-interval_x*0.5
        intercept_symbol="+" if intercept>0 else "-"
        ax.text(start_x,start_y,r'$y=$'+str(round(slope,3))+'$x$'+f" {intercept_symbol} "+str(abs(round(intercept,3))),fontsize=8)
        ax.text(start_x,start_y-0.5*interval_x,r'$R^2=$'+str(round(r_value**2,2)),fontsize=8)
        ax.text(start_x,start_y-interval_x,"RMSE="+str(round(rmse,2)),fontsize=8)
        ax.text(0.2, 0.15, label+data_type, transform=ax.transAxes,fontsize=8, fontweight='bold', va='top')
        
        x_ticks =np.round(np.arange(min_x_value, max_x_value, interval_x),0)
        # interval_y =round(float((max_latitude - min_latitude) / 7),2)
        # y_ticks =np.round(np.arange(min_latitude, max_latitude , interval_x),1)
        
        ax.set(xlim=(min_x_value,max_x_value),ylim=(min_x_value,max_x_value),xticks=x_ticks,
            yticks=x_ticks)
        
    fig.supxlabel(xName,y=0.05,fontsize=15,fontweight="normal")
    fig.supylabel(yName,x=.01,fontsize=15,fontweight="normal")
    # hist2d[3]： hist2d 是 ax.hist2d 函数的返回值，hist2d 是一个包含了直方图统计信息的对象。hist2d[3] 表示这个对象中的第四个元素，通常是用来表示颜色条的对象。
    # cax=grid.cbar_axes[0]：这里指定了颜色条的轴，即将颜色条放置在 grid.cbar_axes[0] 上。
    # orientation='vertical'：这个参数指定了颜色条的方向为垂直方向。
    # cbar = plt.colorbar(im, ax=ax)
    cbar = fig.colorbar(hist2d[3], cax=grid.cbar_axes[0], orientation='vertical')
    cbar.set_label(label="Number Of Point" if density==False else "Density Of Point",fontsize=11)
    cbar.ax.tick_params(left=True,labelright=True,direction="in",width=.4,labelsize=10)
    cbar.ax.tick_params(which="minor",right=False)
    cbar.ax.set_title("Counts" if density==False else "Density",fontsize=11)
    cbar.outline.set_linewidth(.4)
    if show_plot:
        plt.show()
    return fig

def draw_multiple_density_plots(dict_data, xName="True Values", yName="Estimated Values", cmap='jet',panel_layout=None,density=True,nbins=150,show_plot=False,show_subplot_label=True,show_best_line=True,show_r2=True):
    '''
    @description: 绘制多子图相关性散点图
    @param {dict_data}: 数据字典dict,包含了x和y的数据,数据格式为{data_type:{"x":x,"y":y}}
    @param {xName}: x轴名称
    @param {yName}: y轴名称
    @param {cmap}: 颜色映射
    @param {panel_layout}: 子图布局,默认为None,即自动计算布局。如果指定了panel_layout,则按照panel_layout的布局进行绘图。示例：panel_layout=(3,2)表示3列2行的子图布局。
    @param {density}: 是否显示密度图还是密度数量图
    @param {nbins}: 直方图的bin数量(即分组数量)
    @param {show_plot}: 是否显示绘图结果
    @param {show_subplot_label}: 是否显示子图标签
    @param {show_best_line}: 是否显示对角线
    @return {fig}: 绘图对象
    '''   
    plot_count=len(dict_data)
    plot_columns,plot_rows=get_layout_col_row(plot_count, panel_layout=panel_layout)   
    width,height=plot_columns*3,plot_rows*3+0.2
    if width<6:
        width=6
    if height<6:
        height=6    
    fig = plt.figure(figsize=(width,height))  
    label_list = ["("+i+")" for i in list(string.ascii_lowercase)[:plot_count]]
    grid = ImageGrid(fig, 111,  # similar to subplot(111)
                    nrows_ncols=(plot_rows, plot_columns),  # creates 2x2 grid of axes
                    axes_pad=0.15,  # pad between axes in inch.
                    cbar_mode="single",
                    cbar_location="right")  
    data_types=dict_data.keys() 
    temp=np.array([[np.min(dict_data[data_type]["x"]),np.max(dict_data[data_type]["x"]),np.min(dict_data[data_type]["y"]),np.max(dict_data[data_type]["y"])]for data_type in data_types])
    min_x_value,max_x_value=np.min(temp),np.max(temp)
    for data_type,ax,label in zip(data_types,grid,label_list):        
        x = dict_data[data_type]["x"]
        y = dict_data[data_type]["y"]  
        z = compute_density_percentages(x, y, nbins)        
        # 计算所需指标
        slope, intercept, r_value, p_value, std_err = stats.linregress(x,y)
        rmse = np.sqrt(mean_squared_error(x,y))
        normalized_bias = (x - y) / y   * 100
        mean_normalized_bias =np.mean((x - y) / y   * 100)#「每个单点准不准」用 MNB，比如网格浓度
        # max_normalized_bias_95 =np.percentile(normalized_bias_ordered, 95) 
        nmb = (y - x).sum() / x.sum() * 100 #关心「整体总量、总和准不准」用 NMB,比如排放总量  
        r2=r2_score(x,y)       
        min_y_value,max_y_value=np.min(y),np.max(y)   
        #绘制最佳拟合线
        best_line_x = np.linspace(min_x_value,max_x_value)
        best_line_y=best_line_x             
        scatter_plots = ax.scatter(x, y, s=5, c=z, marker='o', cmap=cmap)
        # hist2d = ax.hist2d(x=x,y=y,bins=nbins,cmap=cmap,cmin=.0001,density=density)#cmin指定了颜色映射的最小值。小于这个值的计数或密度将被忽略，不会被绘制。图对象中其他部分被纯色填充. norm=norm
        if show_best_line:
            ax.plot(best_line_x,best_line_y,color='k',linewidth=.8,alpha=.8,
                            linestyle='-',zorder=-1)
        ax.plot(x, intercept + slope*x, 'r',linewidth=.8)
        ax.grid(False)        
        # 添加文本信息
        interval_x =round(float((max_x_value - min_x_value) / 5),2)
        interval_y =round(float((max_y_value - min_y_value) / 5),2)
        start_x=min_x_value+interval_x*0.5
        start_y=max_x_value-interval_x*0.5
        intercept_symbol="+" if intercept>0 else "-"
        ax.text(start_x,start_y,r'$y=$'+str(round(slope,3))+'$x$'+f" {intercept_symbol} "+str(abs(round(intercept,3))),fontsize=8)
        if show_r2:
            ax.text(start_x,start_y-0.5*interval_x,r'$R^2=$'+str(round(r2,2)),fontsize=8)
        else:
            ax.text(start_x,start_y-0.5*interval_x,r'$R=$'+str(round(r_value,2)),fontsize=8)
        ax.text(start_x,start_y-interval_x,"$RMSE=$"+str(round(rmse,2))+"ppbv",fontsize=8)
        ax.text(start_x,start_y-1.5*interval_x,"$NMB=$"+str(round(nmb,2))+"%",fontsize=8)
        if show_subplot_label:
            ax.text(0.2, 0.15, label+data_type, transform=ax.transAxes,fontsize=8, fontweight='bold', va='top')        
        x_ticks =np.round(np.arange(min_x_value, max_x_value, interval_x),0)                  
        ax.set(xlim=(min_x_value,max_x_value),ylim=(min_x_value,max_x_value),xticks=x_ticks,
            yticks=x_ticks)        
    fig.supxlabel(xName,y=0.05,fontsize=15,fontweight="normal")
    fig.supylabel(yName,x=.01,fontsize=15,fontweight="normal")  
    cbar = fig.colorbar(scatter_plots, cax=grid.cbar_axes[0], orientation='vertical')
    cbar.set_label(label="Number Of Point" if density==False else "Density Of Point",fontsize=11)
    cbar.ax.tick_params(left=True,labelright=True,direction="in",width=.4,labelsize=10)
    cbar.ax.tick_params(which="minor",right=False)
    cbar.ax.set_title("Counts" if density==False else "Density",fontsize=11)
    # Set the locator and formatter for the colorbar
    from matplotlib.ticker import MultipleLocator, FormatStrFormatter
    cbar.locator = MultipleLocator(0.1)  # Set the interval between ticks
    cbar.update_ticks()
    cbar.outline.set_linewidth(.4)
    plt.tight_layout()
    if show_plot:
        plt.show()        
    return fig


def plot_line_with_error(save_file,df,x_column,y_columns,data_type_column="Metric",mean_column="Mean",min_column="Min",max_column="Max",**kwargs):       
    colors = ["#2FBE8F","#459DFF","#FF5B9B","#FFCC37"]   
    fig,ax = plt.subplots(figsize=(4,3.5),dpi=100,facecolor="w")
    for index,color in zip(y_columns,colors):
        data_selcet = df.loc[df[data_type_column]==index,:]
        # 计算误差
        y_err = [data_selcet[mean_column] - data_selcet[min_column], data_selcet[max_column] - data_selcet[mean_column]]
        ax.errorbar(x=data_selcet[x_column],y=data_selcet[mean_column],yerr=y_err,color="k",
                    linewidth=1.5,marker='o',ms=10,mew=2,mfc=color,mec='k',capsize=5,label=index)
    # ax.set_ylim(-8,30)
    # ax.set_xlim(-2,40)
    ax.set_xlabel("Day")
    ax.set_ylabel("Values Change")
    ax.legend(ncol=2,frameon=False)
    ax.set_axisbelow(True)

    fig.savefig(save_file,bbox_inches='tight',dpi=300)
    plt.show()

def plot_bar(save_file,df,data_columns,x_column,**kwargs):
    '''
    @description: 绘制柱状图
    @param {
        save_file: str, 保存图片的文件名，如'bar.png'
        df: pandas.DataFrame, 数据集
        data_columns: list, 包含需要绘制的数据列名称的列表，如['CO2','CH4','N2O']
        x_column: str, x轴数据列名，如'City'        
        x_title: str, x轴标题，默认为x_column
        y_title: str, y轴标题，默认为None
        title: str, 图形标题，默认为None
        bar_width: float, 柱形宽度，默认为0.25
        fig_size: tuple, 图形大小，如(8,6)
        cmap: matplotlib.colors.LinearSegmentedColormap, 颜色映射，默认为grads_default
        font_name: str, 字体名称，默认为'WenQuanYi Zen Hei'
        value_format: str, 数值格式，如'{:.2f}'
        value_range: tuple, Y轴刻度数值范围，如(0,100)
        y_ticks_digits: int, Y轴刻度值的小数位数，默认为1
    }
    示例：
    
    '''       
    x_title= kwargs.get('x_title', x_column)
    y_title= kwargs.get('y_title', None)
    title= kwargs.get('title', None)
    bar_width= kwargs.get('bar_width', 0.25)# 获取柱形的宽度
    fig_size=kwargs.get('fig_size',None)
    cmap=kwargs.get('cmap',cmaps.grads_default)
    font_name= kwargs.get('font_name', 'WenQuanYi Zen Hei') 
    if font_name!=None:
        # 设置中文字体为系统中已安装的字体，如SimSun（宋体）、SimHei（黑体）
        plt.rcParams['font.sans-serif'] = [font_name]  # 设置中文字体为宋体 ['WenQuanYi Zen Hei']
        plt.rcParams['axes.unicode_minus'] = False  # 用于正常显示负号 
    value_format= kwargs.get('value_format', None) 
    value_range= kwargs.get('value_range', (None,None)) 
    y_ticks_digits= kwargs.get('y_ticks_digits', 1)
    # 获取城市列表
    cities = df[x_column]
    if fig_size==None:
        length = len(cities)        
        if length >=8:
            fig_size=(math.ceil(length*0.85), 6)
        else:
            fig_size=(8, 6)                    
    # 设置图形大小
    plt.figure(figsize=fig_size)    
    # 设置柱形的位置
    r1 = range(len(cities))
    postions=[]
    postions.append(r1)    
    for i in range(len(data_columns)):
        r2 = [x + bar_width for x in postions[-1]]
        postions.append(r2)       
    bar_colors=cmap.colors#['b','g','r']
    min_values,max_values=[],[]
    # 绘制柱形图
    for column_name,r,color in zip(data_columns,postions,bar_colors):
        plt.bar(r,  df[column_name], color=color, width=bar_width, label=column_name)   #edgecolor='grey', 
        if not any(value_range):
            max_values.append(df[column_name].max())
            min_values.append(df[column_name].min())
    # 添加标签、标题和图例        
    plt.xlabel(x_title, fontweight='bold')
    plt.xticks([r + bar_width for r in range(len(cities))], cities)
    if y_title!=None:
        plt.ylabel(y_title)
    if title!=None:
        plt.title(title)
    plt.legend()
    min_value,max_value=value_range   
    if not any(value_range):
        min_value,max_value=min(min_values),max(max_values)
        scale_min_factor=0.95 if min_value>=0 else 1.05
        scale_max_factor=1.05 if max_value>=0 else 0.95
        min_value,max_value=min_value*scale_min_factor,max_value*scale_max_factor      
    plt.ylim(min_value,max_value)    
    if value_format is not None:
        interval_y =round(float((max_value - min_value) / 7),y_ticks_digits+1)
        # 设置y轴刻度值和标签
        y_ticks =np.round(np.arange(min_value, max_value, interval_y),y_ticks_digits)
        plt.yticks(y_ticks, [f'{format(value, value_format)}' for value in y_ticks])
    # 显示图形
    plt.show()   
    # 保存图像为图片文件
    plt.savefig(save_file,dpi=300,bbox_inches='tight')
    return save_file


def contour_plot_func(savefile,X, Y, Z,x_name, y_name, cmap='jet'):
    """
    绘制二维等值线图
    """
    # 创建网格
    xx, yy = np.meshgrid(np.arange(0, 1.51, 0.01), np.arange(0, 1.51, 0.01))
    
    # 使用样条插值
    interp_func = interp2d(X, Y, Z, kind='cubic')
    zz = interp_func(xx[0, :], yy[:, 0])

    # 创建图形
    plt.figure(figsize=(10,9))  # 转换为英寸
    plt.title('Total')

    max_z = np.ceil(np.max(zz))
    min_z = np.floor(np.min(zz))    
    color_map_size = np.arange(min_z, max_z + 0.5, 0.5)
    # 找到合适的颜色映射范围
    first_num = max(np.where(min_z >= color_map_size)[0])
    end_num = min(np.where(max_z <= color_map_size)[0])
    v = color_map_size[first_num:end_num + 1]    
    # # 加载颜色映射    
    # 绘制等值线图
    contour = plt.contourf(xx, yy, zz, levels=v, cmap=cmap)
    plt.colorbar(contour)
    
    # 设置轴刻度和标签
    plt.xticks(np.arange(0, 1.51, 0.25))
    plt.yticks(np.arange(0, 1.51, 0.25))
    plt.tick_params(axis='both', which='major', labelsize=22, direction='out')
    
    plt.xlabel(x_name, fontsize=30, fontname='Times New Roman')
    plt.ylabel(y_name, fontsize=30, fontname='Times New Roman')

    # 添加虚线
    plt.plot([1, 1], [0, 1.5], 'k-.', linewidth=1)
    plt.plot([0, 1.5], [1, 1], 'k-.', linewidth=1)

    # 保存图形
    plt.savefig(savefile, bbox_inches='tight', dpi=300)
    plt.close()

if __name__=="__main__":
    print("hello world")    
    
    import pandas as pd
    import numpy as np
    df=pd.read_csv(r"D:\ZQZH.csv")
    # {data_type:{"x":x,"y":y}}
    dict_data={"ZQZH":{"x":df["Obeservation"],"y":df["Monitor"]}}
    draw_multiple_density_plots(dict_data, xName="True Values", yName="Estimated Values", cmap='jet',panel_layout=None,density=True,nbins=200,show_plot=True,show_best_line=False,show_r2=False)
    print("done")
    # 数据准备
    # file_name = 'SD_JAN_PM_ALL'
    # rsm_name = f'pf-ERSM_{file_name}'
    # savefile = 'SaveContourPicture'

    # # 加载数据文件
    # data = loadmat(file_name + '.mat')
    # ersm_data = loadmat(file_name + '_ersm.mat')

    # # 假设这些变量来自加载的数据文件
    # Lpma = ersm_data.get('Lpma')  # 示例
    # Rpma = ersm_data.get('Rpma')  # 示例
    # Ipma = ersm_data.get('Ipma')  # 示例
    # region_cell = ersm_data.get('regionCell')  # 示例

    # matrix_file = 'E:/文档/My RSM-VAT Files/Data/Example/PRD_SD_OCT_41_41/Config Files/Matrix_SD_2015_case358_387_PM.csv'
    # aconc_file = 'E:/文档/My RSM-VAT Files/Data/Example/PRD_SD_OCT_41_41/CMAQ/ACONC.'
    # region_file = 'E:/文档/My RSM-VAT Files/Data/Example/PRD_SD_July_41_41/Config Files/SD_Multi_region_include_other(MATLAB).csv'

    # region_num = 7
    # speces = 4
    # region_row = 148
    # region_col = 112

    #    # Out of Sample
    #     xx = np.arange(0, 1.51, 0.25)
    #     yy = np.arange(0, 1.51, 0.25)

    #     result = np.zeros((len(xx) * len(yy), 1))
    #     zz = np.zeros((len(xx), len(yy)))
    #     x = np.ones((region_num, speces))  # 默认全1基准矩阵
    #     n = 0
    #     x_name = 'SO2'
    #     y_name = 'NH3'
    
    #     for i in range(len(xx)):
    #         for j in range(len(yy)):
    #             x[:, 1] = xx[i]
    #             x[:, 2] = yy[j]
    #             pre_data = get_response_values_pm(Lpma, Rpma, Ipma, region_cell, x, region_row, region_col, region_num, data)       
    #             zz[i, j] =  np.mean(pre_data)
    #             n += 1

    #     contour_plot_func(rsm_name, xx, yy, zz, savefile, x_name, y_name)


    # # 保存结果为 CSV
    # os.makedirs('./SaveCSV', exist_ok=True)
    # np.savetxt(f'./SaveCSV/{rsm_name}_{x_name}{y_name}Total.csv', result, delimiter=',')