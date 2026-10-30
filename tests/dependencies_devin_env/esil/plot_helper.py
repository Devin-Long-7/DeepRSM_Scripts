import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from esil.panelayout_helper import get_layout_col_row
import math
from tqdm.auto import tqdm
import os
import xarray as xr
from scipy.stats import pearsonr


def plot_time_series(
    dict_data,
    subplot_layout=None,
    subplot_figsize=None,
    sharex=False,
    sharey=False,
    save_path=None,
    show_plot=True,
    angle=45,
    y_title=None,
    x_title="Time",
    legend_loc="upper right",
    legend_bbox_to_anchor=(1, 0.98),
    legend_ncol=None,
    font_name=None,
    show_share_legend=False,
    line_colors=None,
    linestyles=None,
    show_metrics=False,
    adjust_rect=[0, 0, 1, 0.95],    
):
    """
    @description: This function is used to plot time series
    Parameters:
    @parameter:dict_data (dict): the dictionary containing the data for plot.
    {key: variable name,#str
    value:
        {'x': times, #list or numpy array
        'y': variable values,#list or numpy array；
        'variable_name': variable_names,#str or list
        'variable_unit': variable_unit #str
        }
    }
    example:dict_data[variable_name]={'x':df_station_single['TimeStep'].values, 'y': y_values,'variable_name':variable_names,'variable_unit':"ppm"}
    @parameter:subplot_layout (tuple): the layout of subplots, default is None, which means using the default layout.
    @parameter:subplot_figsize (tuple): the size of subplots, default is None, which means using the default size.
    @parameter:sharex (bool): whether to share x-axis, default is False.
    @parameter:sharey (bool): whether to share y-axis, default is False.
    @parameter:save_path (str): the path to save the plot, default is None, which means not saving the plot.
    @parameter:show_plot (bool): whether to show the plot, default is True.
    @parameter:angle (int): the angle of x-axis labels, default is 45.
    @parameter:y_title (str): the title of y-axis, default is None, which means using the default title.
    @parameter:x_title (str): the title of x-axis, default is "Time".
    @parameter:legend_loc (str): the location of legend, default is 'upper right'.
    @parameter:legend_bbox_to_anchor (tuple): the position of legend, default is (1, 0.98).
    @parameter:legend_ncol (int): the number of columns of legend, default is None, which means using the default number.
    @parameter:font_name (str): the name of font, default is None, which means using the default font.
    @parameter:show_share_legend (bool): whether to show the share legend, default is False.
    @parameter:adjust_rect (list): the rect of adjust_layout, default is [0, 0, 1, 0.95].
    @parameter:line_colors (list): the colors of lines for multiple y data, default is None, which means using the default colors.
    @parameter:linestyles (list): the styles of lines for multiple y data, default is None, which means using the default styles.
    @parameter:show_metrics (bool): whether to show the metrics, default is False.
    @return: Figure object.
    example:
    @multiple y data:
    y_values=[df['prior_concentration'].values,df['posterior_concentration'].values]
    variable_names=['prior_concentration','posterior_concentration']
    dict_data[variable_name]={'x':dates, 'y': y_values,'variable_name':variable_names,'variable_unit':"ppm"}
    @single y data:
    y_values=df['concentration'].values
    variable_names='concentration'
    dict_data[variable_name]={'x':dates, 'y': y_values,'variable_name':variable_names,'variable_unit':"ppm"}
    plot_time_series(dict_data,save_path=save_path,font_name='WenQuanYi Zen Hei',show_share_legend=True)
    plot_time_series(dict_data,save_path=save_path,show_share_legend=True,adjust_rect=[0, 0, 1, 0.75],legend_ncol=2)
    """
    if font_name != None:
        # 设置中文字体为系统中已安装的字体，如SimSun（宋体）、SimHei（黑体）
        plt.rcParams["font.sans-serif"] = [font_name]  # 设置中文字体为宋体
        plt.rcParams["axes.unicode_minus"] = False  # 用于正常显示负号
    plot_count = len(dict_data)
    plot_columns, plot_rows = get_layout_col_row(
        plot_count, panel_layout=subplot_layout
    )

    width, height = subplot_figsize if subplot_figsize is not None else (10, 6)

    fig, axs = plt.subplots(
        plot_rows,
        plot_columns,
        figsize=(width * plot_columns, height * plot_rows),
        sharex=sharex,
        sharey=sharey,
    )
    axes = axs.ravel() if plot_count > 1 else [axs]
       
    # 用字典来存储图例的句柄和标签，避免重复
    legend_dict = {}
    for ax, (data_type, dic_sub_data) in zip(axes, dict_data.items()):
        x, y, variable_name, variable_unit = (
            dic_sub_data["x"],
            dic_sub_data["y"],
            dic_sub_data["variable_name"],
            dic_sub_data["variable_unit"],
        )
        
        ax.set_title(
            f"{data_type} Time Series", fontsize=14, fontweight="bold", ha="center"
        )  # \n{variable_name} ({variable_unit})
        # ax.text(
        #     title_location_x,title_location_y,f"{data_type} Time Series", fontsize=14, fontweight="bold", ha="center"
        # ) 

        if isinstance(y, list):
            colors = (
                plt.cm.Paired(range(len(y))) if line_colors is None else line_colors
            )  # 使用配色方案
            linestyles = ["-"] * len(y) if linestyles is None else linestyles
            for sub_y, color, label, linestyle in zip(
                y, colors, variable_name, linestyles
            ):
                (line,) = ax.plot(
                    x, sub_y, color=color, linestyle=linestyle, label=label
                )
                # 使用字典存储图例句柄，避免重复
                legend_dict[label] = line
        else:
            (line,) = ax.plot(x, y)
        ax.set_xlabel(x_title)
        if y_title is not None:
            ax.set_ylabel(y_title)
        else:
            y_title = (
                f"{variable_name[0]} ({variable_unit})"
                if isinstance(variable_name, list)
                else f"{variable_name} ({variable_unit})"
            )
            ax.set_ylabel(y_title)
        ax.tick_params(axis="x", rotation=angle)
        if not show_share_legend:
            ax.legend(loc=legend_loc)
        if show_metrics and isinstance(y, list) and len(y) == 2:

            # 计算obs.avg和sim.avg
            obs_avg = np.mean(y[0])
            sim_avg = np.mean(y[1])
            # 计算NMB
            NMB = (np.sum(y[1] - y[0]) / np.sum(y[0])) * 100
            # 计算相关系数R
            R, _ = pearsonr(y[0], y[1])
            # 在图上显示 obs.avg, sim.avg, NMB, R
            textstr = f"{variable_name[0]}. avg = {obs_avg:.2f}   {variable_name[1]}. avg = {sim_avg:.2f}\nNMB = {NMB:.2f}%   R = {R:.2f}"
            metric_location_x,metric_location_y = 0.5,0.98
            # ax.text(
            #     metric_location_x,
            #     metric_location_y,
            #     textstr,
            #     transform=plt.gca().transAxes,
            #     fontsize=12,
            #     va="top",
            #     ha="center",
            # )
            ax.set_title(
            f"{data_type} Time Series\n{textstr}", fontsize=12, fontweight="bold", ha="center"
        ) 
    # save the plot if save_path is not None
    if show_share_legend:
        # 提取字典中的句柄和标签
        labels, handles = zip(*legend_dict.items())
        # 在图的顶部添加公共图例
        ncol = len(labels) if legend_ncol is None else legend_ncol
        fig.legend(
            handles=handles,
            labels=labels,
            loc=legend_loc,
            ncol=ncol,
            bbox_to_anchor=legend_bbox_to_anchor,
            fontsize=12,
            frameon=False,
            handlelength=2,
            columnspacing=1,
        )  # , fontsize=12, frameon=False, handlelength=2, columnspacing=1
        height = 2 - legend_bbox_to_anchor[1]
        # # 自动调整子图布局，避免重叠
        plt.tight_layout(rect=adjust_rect)  # 留出顶部空间给公共图例
    else:
        # ax.legend(loc=legend_loc)
        if show_metrics:
            plt.subplots_adjust(top=0.90)  # 留出顶部空间给公共图例和指标
        else:
            plt.tight_layout()
    if save_path is not None:
        dir = os.path.dirname(save_path)
        if not os.path.exists(dir):
            os.makedirs(dir)
        plt.savefig(save_path)
    if show_plot:
        # 显示图形
        plt.show()
    return fig


def plot_pie(
    df,
    x_column_name,
    group_column_name,
    y_column_names,
    output_file,
    title="",
    dict_skip_values=None,
    layout=None,
    font_name="WenQuanYi Zen Hei",
    colors=None,
    show_shared_legend=True,
    legend_loc="upper left",
    legend_bbox_to_anchor=(0.05, 1.05),
    legend_title="",
    show_percent=True,
    title_fontsize=14,
    pie_label_fontsize=16,
    pie_label_color="black",
    pie_label_threshold=5,
):
    """
    @description: 绘制饼图
    @param {
        df: pandas.DataFrame, 数据集
        x_column_name: str, x轴数据列名，如'day'
        group_column_name: str, 分组列名，如'receptor_region'
        y_column_names: list, 包含需要绘制的数据列名称的列表，如['CO2','CH4','N2O']
        output_file: str, 保存图片的文件名，如'bar.png'
        title: str, 图形标题，默认为''
        x_title: str, x轴标题，默认为''
        y_title: str, y轴标题，默认为''
        colors: list, 颜色列表，如['#BC3C29FF', '#0072B5FF', '#E18727FF']
        show_shared_legend: bool, 是否显示共享图例，默认为True
        legend_loc: str, 图例位置，默认为'upper left'
        legend_bbox_to_anchor: tuple, 图例位置偏移，默认为(0.05, 1.05)
        xy_title_fontsize: int, x,y轴标题字体大小, default=10；使用示例：xy_title_fontsize=10
        title_fontsize：int, 标题字体大小, default=14；使用示例：title_fontsize=14
        dict_skip_values: dict, 过滤列名和对应值的字典，如{'day': 1}，表示过滤day列中值为1的数据
        layout: tuple, 图形布局，如(2,3),先列后行
    }
    """
    from esil.panelayout_helper import get_layout_col_row
    import os
    import numpy as np

    if output_file:
        output_dir = os.path.dirname(output_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    if font_name != None:
        # 设置中文字体为系统中已安装的字体，如SimSun（宋体）、SimHei（黑体）
        plt.rcParams["font.sans-serif"] = [
            font_name
        ]  # 设置中文字体为宋体 ['WenQuanYi Zen Hei']
        plt.rcParams["axes.unicode_minus"] = False  # 用于正常显示负号
    # 绘制堆积柱状图
    # plot_counts=len(y_column_names)
    if dict_skip_values is not None:
        for column, value in dict_skip_values.items():
            if type(value) == list:
                for v in value:
                    df = df[df[column] != v]
            else:
                df = df[df[column] != value]
    cities = df[x_column_name].unique()
    plot_counts = len(y_column_names) * len(cities)
    cols, rows = (
        layout if layout is not None else get_layout_col_row(plot_counts)
    )  # 1,1#get_layout_col_row(plot_counts) if plot_counts!=10 else (5,2)
    padding_height = 2 if show_shared_legend else 0
    fig, axes_origin = plt.subplots(
        rows, cols, figsize=(cols * 4, 4 * rows + padding_height)
    )
    axes = axes_origin.ravel()
    # 用于收集所有的 wedges（扇区）和 labels（标签）
    wedges_list = []
    labels_list = []
    idx = 0

    # 自定义 autopct 函数
    def autopct_format(pct, threshold=5):
        if threshold is None:
            return "%1.1f%%" % pct
        else:
            return ("%1.1f%%" % pct) if pct > threshold else ""

    for y_column_name in y_column_names:
        for city in cities:
            ax = axes[idx]
            selected_data = df[df[x_column_name] == city]
            # selected_data = df.groupby([x_column_name,group_column_name])[y_column_name].sum().reset_index()
            # 只删除 '广州_NOx' 和 '深圳_VOCs' 列中包含NaN的行
            df_pollutant = selected_data.dropna(
                subset=[group_column_name, y_column_name], how="any"
            )

            if colors is None:
                colors_count = len(df_pollutant[group_column_name].unique())
                colors = (
                    plt.cm.Paired(range(colors_count))
                    if colors_count <= 10
                    else plt.cm.get_cmap("jet", colors_count)(
                        np.linspace(0, 1, colors_count)
                    )
                )  # 使用配色方案 sorted(my_list)
            # 绘制 NOx 的饼图
            wedges, texts, autotexts = ax.pie(
                df_pollutant[y_column_name],
                autopct=lambda pct: autopct_format(pct, threshold=pie_label_threshold),
                startangle=140,
                pctdistance=0.85,
                colors=colors,
                textprops=dict(color=pie_label_color, fontsize=pie_label_fontsize),
            )  # 只显示大于 5% 的百分比 # pctdistance=0.85, autopct='%1.1f%%', startangle=140, colors=colors, textprops=dict(color="w",fontsize=12)
            # 将所有文本标签（包括百分比标签）放入一个列表
            texts_to_adjust = texts + autotexts
            ax.set_title(
                f'{city}{y_column_name}{title if title else ""}',
                fontsize=title_fontsize,
            )
            # 添加图例
            # 收集 NOx 饼图的 wedges 和 labels
            wedges_list.extend(wedges)
            labels_list.extend(df_pollutant[group_column_name])
            idx += 1
    # 去重 wedges 和 labels
    unique_labels, unique_wedges = zip(*dict(zip(labels_list, wedges_list)).items())
    # 在图的顶部中央添加一行显示的图例，去掉重复项
    fig.legend(
        unique_wedges,
        unique_labels,
        title=legend_title,
        loc=legend_loc,
        bbox_to_anchor=legend_bbox_to_anchor,
        ncol=len(unique_labels),
        fontsize=title_fontsize - 2,
        title_fontsize=title_fontsize,
    )
    # from adjustText import adjust_text
    # # 调整标签的位置以避免重叠
    # adjust_text(texts_to_adjust, arrowprops=dict(arrowstyle='-', color='gray'))

    # 调整布局
    # plt.tight_layout(rect=[0, 0, 1, 0.90])  # 调整布局以给图例腾出空间
    plt.tight_layout()
    plt.show()
    if output_file:
        fig.savefig(output_file, dpi=300, bbox_inches="tight")


def plot_stack_bar(
    df,
    x_column_name,
    group_column_name,
    y_column_names,
    output_file,
    title="",
    x_title="",
    y_title="",
    dict_skip_values=None,
    layout=None,
    font_name="WenQuanYi Zen Hei",
    colors=None,
    show_shared_legend=True,
    legend_loc="upper left",
    legend_bbox_to_anchor=(0.05, 1.05),
    show_percent_bar=False,
    xy_title_fontsize=10,
    title_fontsize=14,
    threshold=0.05,
    order_by=None,
):
    """
    @description: 绘制堆积柱状图This code is used to plot stack bar chart of pollutant emissions from different sources
    @param {
        df: pandas.DataFrame, 数据集
        x_column_name: str, x轴数据列名，如'day'
        group_column_name: str, 分组列名，如'receptor_region'
        y_column_names: list, 包含需要绘制的数据列名称的列表，如['CO2','CH4','N2O']
        output_file: str, 保存图片的文件名，如'bar.png'
        title: str, 图形标题，默认为''
        x_title: str, x轴标题，默认为''
        y_title: str, y轴标题，默认为''
        colors: list, 颜色列表，如['#BC3C29FF', '#0072B5FF', '#E18727FF']
        show_shared_legend: bool, 是否显示共享图例，默认为True
        legend_loc: str, 图例位置，默认为'upper left'
        legend_bbox_to_anchor: tuple, 图例位置偏移，默认为(0.05, 1.05)
        xy_title_fontsize: int, x,y轴标题字体大小, default=10；使用示例：xy_title_fontsize=10
        title_fontsize：int, 标题字体大小, default=14；使用示例：title_fontsize=14
        dict_skip_values: dict, 过滤列名和对应值的字典，如{'day': 1}，表示过滤day列中值为1的数据
        layout: tuple, 图形布局，如(2,3),先列后行
    }
    """
    from esil.panelayout_helper import get_layout_col_row
    import os

    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    # receptors=df['receptor_region'].unique()
    # days=df[x_column_name].unique()
    if font_name != None:
        # 设置中文字体为系统中已安装的字体，如SimSun（宋体）、SimHei（黑体）
        plt.rcParams["font.sans-serif"] = [
            font_name
        ]  # 设置中文字体为宋体 ['WenQuanYi Zen Hei']
        plt.rcParams["axes.unicode_minus"] = False  # 用于正常显示负号
    # 绘制堆积柱状图
    plot_counts = len(y_column_names)
    cols, rows = (
        layout if layout is not None else get_layout_col_row(plot_counts)
    )  # 1,1#get_layout_col_row(plot_counts) if plot_counts!=10 else (5,2)
    padding_height = 2 if show_shared_legend else 0
    fig, axes_origin = plt.subplots(
        rows, cols, figsize=(cols * 8, 6 * rows + padding_height)
    )
    axes = axes_origin.ravel()
    # 用于存储所有图例的句柄和标签
    legend_dict = {}

    for y_column_name, ax in zip(y_column_names, axes):
        if dict_skip_values is not None:
            for column, value in dict_skip_values.items():
                if type(value) == list:
                    for v in value:
                        df = df[df[column] != v]
                else:
                    df = df[df[column] != value]
        selected_data_origin = (
            df.groupby([x_column_name, group_column_name])[y_column_name]
            .sum()
            .reset_index()
        )
        if order_by is not None:
            # if order_by == 'desc':
            #     selected_data = selected_data_origin.sort_values(by=[y_column_name], ascending=False).copy()
            # elif order_by == 'asc':
            #     selected_data = selected_data_origin.sort_values(by=[y_column_name], ascending=True).copy()

            # Step 1: 计算每个 x_column_name 的 y_column_name 总和
            x_sum = (
                selected_data_origin.groupby(x_column_name)[y_column_name]
                .sum()
                .reset_index()
            )
            # Step 2: 根据总和进行排序
            if order_by is not None:
                if order_by == "desc":
                    x_sum_sorted = x_sum.sort_values(
                        by=y_column_name, ascending=False
                    ).copy()
                elif order_by == "asc":
                    x_sum_sorted = x_sum.sort_values(
                        by=y_column_name, ascending=True
                    ).copy()
            else:
                x_sum_sorted = x_sum.copy()
            # Step 3: 将排序后的 x_column_name 顺序应用到原始数据
            # 通过 merge 保持原始结构，并根据排序后的 x_column_name 顺序重新排序
            selected_data = selected_data_origin.merge(
                x_sum_sorted[[x_column_name]], on=x_column_name, how="left"
            )
            # Step 4: 按照排序后的 x_column_name 顺序排列
            selected_data = (
                selected_data.set_index(x_column_name)
                .loc[x_sum_sorted[x_column_name]]
                .reset_index()
            )
        else:
            selected_data = selected_data_origin
        # 绘图
        # 设置图形大小和标题
        ax.set_title(
            f'{y_column_name} {(title) if title else ""}',
            fontsize=title_fontsize,
            fontweight="bold",
        )
        # 设置x轴标签
        x_labels = selected_data[x_column_name].unique()
        x = range(len(x_labels))
        if show_percent_bar:
            # 计算百分比堆积图所需的数据
            total_contributions_per_day = (
                selected_data.groupby(x_column_name)[y_column_name].sum().reset_index()
            )
            selected_data = pd.merge(
                selected_data,
                total_contributions_per_day,
                on=x_column_name,
                suffixes=("", "_total"),
            )
            selected_data["percentage"] = (
                selected_data[y_column_name] / selected_data[f"{y_column_name}_total"]
            ) * 100
            y_column_name = "percentage"
        # 绘制堆积柱形图
        bar_width = 0.5
        bottom = 0
        if colors is None:
            colors_count = len(selected_data[group_column_name].unique())
            colors = (
                plt.cm.Paired(range(colors_count))
                if colors_count <= 10
                else plt.cm.get_cmap("jet", colors_count)(
                    np.linspace(0, 1, colors_count)
                )
            )  # 使用配色方案 sorted(my_list)
        # colors = ["#BC3C29FF", "#0072B5FF","#E18727FF"]
        # 初始化 bottom 为一个零列表，长度与 x_labels 相同
        bottom = [0] * len(x_labels)
        regions = sorted(selected_data[group_column_name].unique())
        all_pollutants_contributions = []  # 用于存储每个region的最终累计值
        for i, region in enumerate(regions):
            subset = selected_data[selected_data[group_column_name] == region]

            y = [
                np.sum(subset.loc[subset[x_column_name] == label][y_column_name].values)
                for label in x_labels
            ]
            bars = ax.bar(x, y, bar_width, bottom=bottom, label=region, color=colors[i])

            # 更新 bottom 列表为下一个条形图的底部位置
            bottom = [bottom[i] + y[i] for i in range(len(x_labels))]
            # 存储当前pollutant对每个region的贡献（用于最终累计值的计算）
            current_pollutant_contributions = y.copy()
            all_pollutants_contributions.append(current_pollutant_contributions)
            if show_shared_legend:
                # 将图例句柄和标签存储在字典中，确保每个标签只添加一次
                handle, label = ax.get_legend_handles_labels()
                legend_dict[region] = (handle[i], region)
            if show_percent_bar:
                # 在每个堆积的柱子中间添加百分比文本
                for j, (rect, height) in enumerate(zip(bars, y)):
                    if height > 0:  # 确保有高度的柱子
                        percentage = height  # 这里height已经是百分比
                        if percentage > threshold * 100:  # 只显示超过阈值的百分比
                            # 获取矩形的 x 和 y 坐标
                            x_pos = (
                                rect.get_x() + rect.get_width() / 2
                            )  # 柱子的中心位置
                            y_pos = (
                                rect.get_y() + rect.get_height() / 2
                            )  # 柱子的中间位置

                            # 在柱子中间显示百分比文本
                            ax.text(
                                x_pos,
                                y_pos,
                                f"{percentage:.0f}%",
                                ha="center",
                                va="center",
                                color="white",
                                fontsize=14,
                                fontweight="bold",
                            )
        if not show_percent_bar:
            # 在所有层绘制完成后，计算每个柱子的最终累计值
            final_cumulative_values = bottom.copy()
            # 在每个柱子的顶部添加累计值文本
            for rect, label in zip(
                bars, final_cumulative_values
            ):  # 注意：这里bars是最后一次迭代的bar对象集合
                # 由于bars集合包含了所有层的矩形，我们需要选择最后一个（顶部）矩形的高度（实际上是bottom列表中的值）
                # 但是，由于我们是逐层绘制的，并且bottom列表已经更新为累计值，我们可以直接使用label（即final_cumulative_values中的值）
                # 然而，rect对象本身并不代表整个堆叠的柱子，而是最后一次迭代的单个层。因此，我们不能直接从rect获取高度。
                # 我们需要知道x的位置来正确地对齐文本。
                x_pos = rect.get_x() + rect.get_width() / 2  # 矩形中心的x位置
                y_pos = label  # 使用bottom列表中的累计值作为y位置（注意：这可能需要稍微向下偏移以避免重叠）
                # plt.text(x_pos, y_pos, f'{label:.2f}', ha='center', va='bottom', fontsize=8)  # 格式化标签并添加到图中
                ax.text(
                    x_pos, y_pos, f"{label:.1f}", ha="center", va="bottom", fontsize=12
                )
                # 如果需要，可以添加一个小偏移量来避免文本与条形重叠
                # y_pos -= 1  # 例如，向下偏移1个单位（根据具体情况调整）

        ax.set_xlabel(x_title, fontsize=xy_title_fontsize, fontweight="bold")
        ax.set_ylabel(y_title, fontsize=xy_title_fontsize, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(x_labels, rotation=45, fontsize=12, fontweight="bold")
        if not show_shared_legend:
            ax.legend()

    # 在 plt.subplots() 之后使用 fig.legend()：来创建一个全局图例。
    # 调整图例的位置：使用 bbox_to_anchor 参数将图例放置在右上角。
    # 设置全局图例，放置在右上角
    # 从字典中提取唯一的图例句柄和标签
    unique_handles = [v[0] for v in legend_dict.values()]
    unique_labels = [v[1] for v in legend_dict.values()]

    # 设置全局图例，放置在右上角bbox_to_anchor用来设置图例的位置，先根据loc参数确定位置，再根据bbox_to_anchor参数调整位置，x轴为0.05，y轴为1.05，即在loc位置基础上沿x轴向右移动0.05，向上移动0.05
    fig.legend(
        handles=unique_handles,
        labels=unique_labels,
        loc=legend_loc,
        ncol=len(unique_handles),
        bbox_to_anchor=legend_bbox_to_anchor,
        bbox_transform=fig.transFigure,
    )

    # fig.legend(handles=handles.unique(), labels=labels.unique(), ncol=len(handles.unique()), fontsize=10, loc='upper right', bbox_to_anchor=(1.1, 1), bbox_transform=fig.transFigure)
    # 显示图形
    plt.tight_layout()
    plt.show()
    # fig.savefig (output_file,dpi=300,bbox_inches='tight')
