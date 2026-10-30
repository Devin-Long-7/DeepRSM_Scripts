import numpy as np
import time
import multiprocessing
import os;
from esil.date_helper import timer_decorator

def read(path):
    with np.load(path) as data:
        return data


def parallel_read(files):
    with multiprocessing.Pool(processes=5) as pool:
        data_list = pool.map(read, files)
    return data_list


class Sentiment(object):
    """NP_chunking data preparation"""

    def __init__(self, domain='cn27', lstRegions=[''], month='', day='32', target='PM', root='', year='',
                 mode='training',hour=None):
        self.domain = domain
        self.lstRegions = lstRegions
        self.year = year
        self.month = month
        self.day = day
        self.target = target
        self.root = root
        self.mode = mode
        self.hour = hour
        start_time = time.time()
        self.load_data()
        # print('Reading datasets comsumes %.3f seconds' % (time.time() - start_time))
    
    def deal_with_torch_data_calculate(self):
        feat_list = []
        
        label= '_'+self.year+ '_' + (self.month).zfill(2) + '_D' + str(self.day)+ '.' if self.hour==None else f"_{self.year}_{self.month.zfill(2)}_{str(self.day).zfill(2)}_H{str(self.hour).zfill(2)}."
        
        base_file = 'data_species_base.npy' #将文件后缀与映射文件里的相对应
        region_clean_file = 'data_species_zero.npy'

        base_path =os.path.join(self.root, self.domain + label + base_file)
        if not os.path.exists(base_path):
            print(f"File {base_path} does not exist")
        base_data = np.load(base_path)    # 加载 base Case Data

        for region in self.lstRegions:
            region_path = os.path.join(self.root, region + label + region_clean_file)
            if not os.path.exists(region_path):
                print(f"File {region_path} does not exist")
            region_clean_data = np.load(region_path)   # 加载 zeros Case Data
            feats = np.concatenate((base_data, region_clean_data), axis=2)
            feat_list.append(feats.transpose(2, 0, 1))
            # print('Dataset: {}, Load Month: {}, Day: {}{}'.format(region, self.month, self.day, ', Hour: '+str(self.hour) if self.hour!=None else ''))
        return feat_list
    # @timer_decorator
    def load_data(self):
        train_feat = self.deal_with_torch_data_calculate()
        self.data_set = np.asarray(train_feat)
