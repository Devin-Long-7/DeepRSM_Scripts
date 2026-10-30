import numpy as np
from sklearn.metrics import r2_score

class Metric:
    def __init__(self, predicted, observed):
        self.predicted = predicted
        self.observed = observed
    
    def get_percentiles(self, values, q_tiles,include_min_max=True):
        '''
        @description: 计算百分位数
        @param {values:list}: 待计算百分位数的列表
        @param {q_tiles:list}: 百分位数列表, 计算百分位数,数值在0-100之间，示例：[5,95]
        @return: list类型，返回最小值，平均值，最大值，如果q_tiles不为空,则在返回结果中追加百分位数
        '''
        res=[np.min(values),np.mean(values),np.max(values)] if include_min_max else [np.mean(values)]
        if q_tiles is not None:         
            for q in q_tiles:
                res.append(np.percentile(values, q))
        return res

    def bias(self,q_tiles=None,include_min_max=True):
        '''
        @description: 计算偏差
        @param {q_tiles:list}: 百分位数列表, 计算百分位数,数值在0-100之间，示例：[5,95]
        @return: tulple类型，默认返回最小偏差值，平均偏差，最大偏差，如果q_tiles不为空,则在返回结果中追加百分位数
        '''        
        bias_values = self.predicted - self.observed
        res = self.get_percentiles(bias_values,q_tiles,include_min_max) 
        return tuple(res)
    
    def error(self,q_tiles=None,include_min_max=True):
        '''
        @description: 计算误差
        @param {q_tiles:list}: 百分位数列表, 计算百分位数,数值在0-100之间，示例：[5,95]
        @return: tulple类型，默认返回最小误差值，平均误差，最大误差，如果q_tiles不为空,则在返回结果中追加百分位数
        '''        
        error_values = np.abs(self.predicted - self.observed)
        res = self.get_percentiles(error_values,q_tiles,include_min_max)        
        return tuple(res)

    def normalized_bias(self,q_tiles=None,include_min_max=True):
        '''
        @description: 计算归一化偏差
        @param {q_tiles:list}: 百分位数列表, 计算百分位数,数值在0-100之间，示例：[5,95]
        @return: tulple类型，默认返回最小归一化偏差值，平均归一化偏差，最大归一化偏差，如果q_tiles不为空,则在返回结果中追加百分位数
        '''        
       # 使用 np.errstate 忽略除以零的警告
        with np.errstate(divide='ignore', invalid='ignore'):
            normalized_bias_values = ((self.predicted - self.observed) / self.observed) * 100
            # 将除以零的结果设置为某个值，比如无穷大或零
            normalized_bias_values[np.isinf(normalized_bias_values)] = 0
        # normalized_bias_values = ((self.predicted - self.observed) / self.observed) * 100
        res = self.get_percentiles(normalized_bias_values,q_tiles,include_min_max)        
        return tuple(res)
    def normalized_error(self,q_tiles=None,include_min_max=True):
        '''
        @description: 计算归一化误差
        @param {q_tiles:list}: 百分位数列表, 计算百分位数,数值在0-100之间，示例：[5,95]
        @return: tulple类型，默认返回最小归一化误差值，平均归一化误差，最大归一化误差，如果q_tiles不为空,则在返回结果中追加百分位数
        '''        
        # 使用 np.errstate 忽略除以零的警告
        with np.errstate(divide='ignore', invalid='ignore'):
            normalized_error_values =(np.abs(self.predicted - self.observed) / self.observed) * 100
            # 将除以零的结果设置为某个值，比如无穷大或零
            normalized_error_values[np.isinf(normalized_error_values)] = 0
        # normalized_error_values = (np.abs(self.predicted - self.observed) / self.observed) * 100
        res = self.get_percentiles(normalized_error_values,q_tiles,include_min_max )        
        return tuple(res)
    
    def fractional_bias(self,q_tiles=None,include_min_max=True):
        '''
        @description: 计算分数偏差
        @param {q_tiles:list}: 百分位数列表, 计算百分位数,数值在0-100之间，示例：[5,95]
        @return: tulple类型，默认返回最小分数偏差值，平均分数偏差，最大分数偏差，如果q_tiles不为空,则在返回结果中追加百分位数
        '''        
        fractional_bias_values =( (self.predicted - self.observed) / ((self.observed + self.predicted) / 2))*100
        res = self.get_percentiles(fractional_bias_values,q_tiles,include_min_max )        
        return tuple(res)

    def fractional_error(self,q_tiles=None,include_min_max=True):
        '''
        @description: 计算分数误差
        @param {q_tiles:list}: 百分位数列表, 计算百分位数,数值在0-100之间，示例：[5,95]
        @return: tulple类型，默认返回最小分数误差值，平均分数误差，最大分数误差，如果q_tiles不为空,则在返回结果中追加百分位数
        '''        
        fractional_error_values = (np.abs(self.predicted - self.observed) / ((self.observed + self.predicted) / 2)) * 100
        res = self.get_percentiles(fractional_error_values,q_tiles,include_min_max)        
        return tuple(res)
    
    def r_squared(self):
        return r2_score(self.observed, self.predicted)
    
    def normalized_mean_bias(self):
         # 使用 np.errstate 忽略除以零的警告
        # with np.errstate(divide='ignore', invalid='ignore'):
        normalized_mean_bias_values =(np.sum(self.predicted - self.observed) / np.sum(self.observed)) * 100
            # 将除以零的结果设置为某个值，比如无穷大或零
            # normalized_mean_bias_values[np.isinf(normalized_mean_bias_values)] = 0
        return normalized_mean_bias_values

    def normalized_mean_error(self):
        # 使用 np.errstate 忽略除以零的警告
        # with np.errstate(divide='ignore', invalid='ignore'):
        normalized_mean_error_values =(np.sum(np.abs(self.predicted - self.observed)) / np.sum(self.observed)) * 100
            # 将除以零的结果设置为某个值，比如无穷大或零
            # normalized_mean_error_values[np.isinf(normalized_mean_error_values)] = 0
        return normalized_mean_error_values
    def rsme(self):
        return np.sqrt(np.mean((self.predicted - self.observed) ** 2))#计算均方根误差 
    
    def description(self,include_min_max=True):
        if include_min_max:
             return {
                'mean_bias': self.bias(),
                'mean_error': self.error(),
                'mean_normalized_bias': self.normalized_bias(),
                'mean_normalized_error': self.normalized_error(),
                'mean_fractional_bias': self.fractional_bias(),
                'mean_fractional_error': self.fractional_error(),
                'normalized_mean_bias': self.normalized_mean_bias(),
                'normalized_mean_error': self.normalized_mean_error(),
                'r_squared': self.r_squared(),
                'rsme': self.rsme()
            }    
        else:
             return {
                'mean_bias': self.bias()[1],
                'mean_error': self.error()[1],
                'mean_normalized_bias': self.normalized_bias()[1],
                'mean_normalized_error': self.normalized_error()[1],
                'mean_fractional_bias': self.fractional_bias()[1],
                'mean_fractional_error': self.fractional_error()[1],
                'normalized_mean_bias': self.normalized_mean_bias(),
                'normalized_mean_error': self.normalized_mean_error(),
                'r_squared': self.r_squared(),
                'rsme': self.rsme()
                }

if __name__=="__main__":
    predicted = np.array([1, 2, 3, 4, 5])
    observed = np.array([1.1, 1.9, 3.1, 4.1, 5.2])
    metric = Metric(predicted, observed)
    a=metric.bias(q_tiles=[5,50,95])
    print(a)
    print(metric.description())
    print("done")
 