'''
Author: Devin
Date: 2024-06-18 23:40:30
LastEditors: Devin
LastEditTime: 2024-08-22 17:20:07
Description: 

Copyright (c) 2024 by Devin, All Rights Reserved. 
'''
class FactorInfo:
    # def __init__(self):
    #     self.Region = ""
    #     self.Pollutant = ""
    #     self.Source = ""
    #     self.Min = 0.0
    #     self.Max = 1.2
    #     self.Limit = 0.2
    #     self.BaseEmissionRatio = 0.0
    #     self.Index = 0
    def __init__(self, region, pollutant, source, value, index=None, min=None, max=None):
        self.Region = region
        self.Pollutant = pollutant
        self.Source = source
        self.Min = min if min is not None else 0.0
        self.Max = max if max is not None else 1.2      
        self.Value = value
        self.Index = index
       