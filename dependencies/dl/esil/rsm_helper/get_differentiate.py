import sympy as sp

def O3_function(NOx,VOCs,SO2,NH3,k_values):
    '''
    :param NOx: 数值=Emission ratio-1
    :param VOCs: 数值=Emission ratio-1
    :param SO2: 数值=Emission ratio-1
    :param NH3: 数值=Emission ratio-1
    :param k_values: 顺序：[NOx^5	NOx^4	NOx^3	NOx^2	NOx	VOC	VOC^2	VOC^3	NOx*VOC	NOx*VOC^3	NOx^5*VOC	NOx^2*VOC	SO2	NH3	baseCase]
    :return:
    '''
    return   k_values[0] * NOx ** 5 + k_values[1] * NOx ** 4 + k_values[2] * NOx ** 3 + k_values[3] * NOx ** 2 + k_values[4] * NOx + k_values[5] * VOCs + k_values[6] * VOCs ** 2 + k_values[7] * VOCs ** 3 \
             + k_values[8] * NOx * VOCs + k_values[9] * NOx * VOCs ** 3+ k_values[10] * NOx ** 5 * VOCs + k_values[11] * NOx ** 2 * VOCs  + k_values[12] * SO2 + k_values[13] * NH3+ k_values[14]

def get_O3_PR_value(k_values,VOCs=1,SO2=1,NH3=1):
    '''
    :param k_values: 顺序：[NOx^5	NOx^4	NOx^3	NOx^2	NOx	VOC	VOC^2	VOC^3	NOx*VOC	NOx*VOC^3	NOx^5*VOC	NOx^2*VOC	SO2	NH3	baseCase]
    :param VOCs: Emission ratio
    :param SO2: Emission ratio
    :param NH3: Emission ratio
    :return:
    '''
    # 解方程并找到使得 O3 达到最大值的 NOx 值
    VOCs_symbol, NOx_symbol,SO2_symbol,NH3_symbol = sp.symbols('VOCs NOx SO2 NH3')
    O3_expression = O3_function(NOx_symbol,VOCs_symbol, SO2_symbol,NH3_symbol,k_values)
    dO3_dNOx = sp.diff(O3_expression, NOx_symbol)
    max_NOx_solution = sp.solve(dO3_dNOx, NOx_symbol)
    max_NOx_value=max_NOx_solution[0]
    max_NOx_value=max_NOx_value.subs(VOCs_symbol, VOCs - 1)

    # 要进行替换的多个变量和值
    substitutions = {NOx_symbol: max_NOx_value, SO2_symbol: SO2-1,NH3_symbol:NH3-1,VOCs_symbol:VOCs-1}  # 替换为 max_NOx_value 和 5
    # 对表达式进行多个变量的替换
    max_O3_result = O3_expression.subs(substitutions)
    NOx_emission_ratio=max_NOx_value+1# max_NOx_value=NOx_emission_ratio-1,其中1表示基准，所以换算回NOx_emission_ratio，需要将max_NOx_value+1.
    return NOx_emission_ratio, max_O3_result

def get_O3_VNr(k_values,VOCs,NOx):
    '''
    :param k_values:  顺序：[NOx^5	NOx^4	NOx^3	NOx^2	NOx	VOC	VOC^2	VOC^3	NOx*VOC	NOx*VOC^3	NOx^5*VOC	NOx^2*VOC	SO2	NH3	baseCase]
    :param VOCs: 数值=Emission ratio-1
    :param NOx: 数值=Emission ratio-1
    :return:
    '''
    expression=-(5*k_values[0]*NOx**4+4*k_values[1]*NOx**3+3*k_values[2]*NOx**2+2*k_values[3]*NOx+k_values[4]+5*k_values[10]*NOx**4*VOCs+2*k_values[11]*NOx*VOCs+k_values[8]*VOCs+k_values[9]*VOCs**3)/(k_values[10]*NOx**5+k_values[11]*NOx**2+k_values[8]*NOx+3*k_values[9]*NOx*VOCs**2+k_values[5]+2*k_values[6]*VOCs+3*k_values[7]*VOCs**2)
    return expression

if __name__=="__main__":

    # 示例参数
    import pandas as pd
    df=pd.read_csv(r'/NetcdfReader/O3_Monitor_Functions.csv')
    # 将第一列之后的所有列设定为 float 类型
    for col in df.columns[1:]:
        df[col] = df[col].astype(float)
    # 遍历每一行数据
    for index, row in df.iterrows():
        # 使用 iloc 来获取除第一列外的其他列的值，并转换为数组
        row_values = row.iloc[1:].values
        VOCs_value=1,
        #row_values = [-0.1018906, 0.06396596, 0.03682716, -0.1217417, 0.06571316, 0.3468532, -0.2358255, -0.08597394,                    0.6097692, -0.04344897, -0.06851652, 0.115323, -0.03890517, -0.08019463,99]
        result_NOx, result_O3 = get_O3_PR_value(row_values.tolist())

        #vnr=get_O3_VNr(row_values,-0.5,-0.5)
        #print(f"网格{row[0]},VNr(0.5,0.5)={vnr},NOx={result_NOx},O3浓度值最大({result_O3})")
        print(f"网格{row[0]},VNr(0,0)={-row_values[4]/row_values[5]},O3浓度值最大({result_O3})")


    # k_values=np.random.rand(14)
    # k_values = [0.1] * 14
    # k_values=[-0.1018906,0.06396596,0.03682716,-0.1217417,0.06571316,0.3468532,-0.2358255,-0.08597394,0.6097692,-0.04344897,-0.06851652,0.115323,-0.03890517,-0.08019463,99]
    # VOCs_value = 2.0  # 示例 VOCs 的数值
    # result_NOx, result_O3 = get_O3_PR_value(k_values)
    # SO2_symbol, NH3_symbol = sp.symbols('SO2 NH3')
    # result_O3 = result_O3.subs(SO2_symbol, 2)
    # O3_2 = result_O3.subs(NH3_symbol, 2)
    #

    # k1 = 0.1
    # k2 = 0.2
    # k3 = 0.15
    # # 将得到的最终表达式中的 VOCs 变量代入数值并计算结果
    # #O3_expression_specifiedVOCs = O3_expression.subs(VOCs_symbol, VOCs_value)
    #
    # # 调用函数并传入参数
    # result_NOx, result_O3 = get_differentiate(k1, k2, k3, VOCs_value)
    # print(f"使得 O3 达到最大值的 NOx 值为: {result_NOx}")
    # print(f"最终表达式结果为: {result_O3}")
    #
    #
    # a=get_differentiate(1)
    # # 定义符号变量
    # VOCs, NOx = sp.symbols('VOCs NOx')
    #
    #
    # # 计算当 VOCs = 1 时，使得 O3 数值最大的 NOx 数值
    # VOCs_value = 1
    # #
    # print(f'当 VOCs = {VOCs_value} 时，使得 O3 数值最大的 NOx 数值为 {max_O3_NOx}，对应的最大 O3 数值为 {max_O3_value}')
