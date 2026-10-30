import numpy as np
import matplotlib.pyplot as plt

#对数据进行归一化
def changex(x, fiSize):
    xmin = np.min(x)
    x = x - xmin
    x = x / np.max(x) * fiSize
    return x
#拟合直线，绘制散点密度图
'''
data:ndarray 数组，不能是数据框，数据框的话，需要调用to_numpy()转为数组
titleName:标题
xName：x轴标题
yName：y轴标题
fiSize：数据归一化大小（如100，即将数据归一化为0~100之间的数）
'''
def draw_density_plot(x, y, titleName, xName, yName, fiSize=100,showMNE=True):
    # x = data[:, 0]  # RSM
    # y = data[:, 1]  # CMAQ

    denSta = np.zeros((fiSize, fiSize))#这里模拟了x*y=fiSize*fiSize的格子，待会要用来放统计每个格子里有几个点的结果
    xlength = len(x)
    xdenSta = changex(x, fiSize)
    ydenSta = changex(y, fiSize)

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

